from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from database.db import db
from models.performance_model import Feedback, PerformanceReview, EmployeeMetric
from ai_engines.sentiment_model import analyze_sentiment
from ai_engines.summarizer import extractive_summary, llm_summary
from ai_engines.perf_predictor import predict_risk
from datetime import date, datetime
import json

perf_bp = Blueprint("perf", __name__, template_folder="../templates", static_folder="../static")

# Submit feedback (public/internal)
@perf_bp.route("/feedback/submit", methods=["GET","POST"])
def submit_feedback():
    if request.method == "POST":
        author_id = request.form.get("author_id") or None
        employee_id = int(request.form.get("employee_id"))
        text = request.form.get("text","").strip()
        if not text:
            flash("Feedback text required.", "warning")
            return redirect(request.url)
        s = analyze_sentiment(text)
        tags = request.form.get("tags")
        tags_list = [t.strip() for t in tags.split(",")] if tags else []
        fb = Feedback(author_id=author_id, employee_id=employee_id, text=text,
                      vader_compound=s["vader_compound"], polarity=s["polarity"],
                      subjectivity=s["subjectivity"], tags=tags_list)
        db.session.add(fb)
        db.session.commit()
        flash("Feedback submitted. Thank you.", "success")
        return redirect(url_for("perf.list_feedbacks", employee_id=employee_id))
    # GET - simple form
    return render_template("performance/submit_feedback.html")

# List feedbacks for an employee
@perf_bp.route("/feedbacks/<int:employee_id>")
def list_feedbacks(employee_id):
    items = Feedback.query.filter_by(employee_id=employee_id).order_by(Feedback.created_at.desc()).all()
    return render_template("performance/feedback_list.html", feedbacks=items, employee_id=employee_id)

# View one feedback
@perf_bp.route("/feedback/<int:fb_id>")
def view_feedback(fb_id):
    fb = Feedback.query.get_or_404(fb_id)
    return render_template("performance/feedback_detail.html", feedback=fb)

# Create performance review (manual)
@perf_bp.route("/review/create", methods=["GET","POST"])
def create_review():
    if request.method == "POST":
        employee_id = int(request.form.get("employee_id"))
        period_start = request.form.get("period_start")
        period_end = request.form.get("period_end")
        # parse dates
        try:
            ps = datetime.strptime(period_start, "%Y-%m-%d").date()
            pe = datetime.strptime(period_end, "%Y-%m-%d").date()
        except Exception:
            flash("Invalid dates.", "warning")
            return redirect(request.url)
        scores = request.form.get("scores_json") or "{}"
        try:
            scores_obj = json.loads(scores)
        except Exception:
            scores_obj = {}
        overall = request.form.get("overall_score")
        overall_score = float(overall) if overall else None
        review = PerformanceReview(employee_id=employee_id, period_start=ps, period_end=pe, scores=scores_obj, overall_score=overall_score)
        db.session.add(review)
        db.session.commit()
        flash("Review created.", "success")
        return redirect(url_for("perf.view_review", review_id=review.id))
    return render_template("performance/create_review.html")

@perf_bp.route("/review/<int:review_id>")
def view_review(review_id):
    r = PerformanceReview.query.get_or_404(review_id)
    return render_template("performance/review_detail.html", review=r)

# Generate AI summary for a review from feedbacks within period
@perf_bp.route("/review/<int:review_id>/generate_summary", methods=["POST"])
def generate_summary(review_id):
    r = PerformanceReview.query.get_or_404(review_id)
    # collect feedback text in the period
    feedbacks = Feedback.query.filter(Feedback.employee_id == r.employee_id).filter(
        Feedback.created_at >= datetime.combine(r.period_start, datetime.min.time()),
        Feedback.created_at <= datetime.combine(r.period_end, datetime.max.time())
    ).all()
    joined = "\n\n".join([f.text for f in feedbacks])
    use_llm = request.form.get("use_llm", "false") == "true"
    summary = ""
    try:
        if use_llm:
            summary = llm_summary(joined)
        else:
            summary = extractive_summary(joined, max_sentences=4)
    except Exception as e:
        current_app.logger.exception("Summary failed")
        summary = extractive_summary(joined, max_sentences=4)
    r.summary = summary
    db.session.add(r)
    db.session.commit()
    flash("Summary generated.", "success")
    return redirect(url_for("perf.view_review", review_id=review_id))

# Dashboard: employee performance snapshot and risk prediction
@perf_bp.route("/dashboard/employee/<int:employee_id>")
def employee_dashboard(employee_id):
    # get latest metrics (e.g., last 30 days aggregated)
    latest_metrics = EmployeeMetric.query.filter_by(employee_id=employee_id).order_by(EmployeeMetric.date.desc()).limit(30).all()
    # compute aggregates for risk features
    if latest_metrics:
        avg_polarity = sum([m.avg_feedback_polarity or 0.0 for m in latest_metrics]) / len(latest_metrics)
        avg_hours = sum([m.hours_worked or 0.0 for m in latest_metrics]) / len(latest_metrics)
        avg_leaves = sum([m.leaves_taken or 0 for m in latest_metrics]) / len(latest_metrics)
        avg_tasks = sum([m.tasks_completed or 0 for m in latest_metrics]) / len(latest_metrics)
    else:
        avg_polarity = avg_hours = avg_leaves = avg_tasks = 0.0
    features = {
        "avg_polarity": avg_polarity,
        "hours_worked_avg": avg_hours,
        "leaves_per_month": avg_leaves,
        "tasks_completed_avg": avg_tasks
    }
    risks = predict_risk(features)
    # list recent feedbacks and reviews
    feedbacks = Feedback.query.filter_by(employee_id=employee_id).order_by(Feedback.created_at.desc()).limit(20).all()
    reviews = PerformanceReview.query.filter_by(employee_id=employee_id).order_by(PerformanceReview.created_at.desc()).limit(10).all()
    return render_template("performance/employee_dashboard.html", employee_id=employee_id,
                           metrics=latest_metrics, risks=risks, feedbacks=feedbacks, reviews=reviews, features=features)

# Simple endpoint to aggregate daily metrics (callable as cron or Celery job)
@perf_bp.route("/metrics/aggregate/<int:employee_id>", methods=["POST"])
def aggregate_metrics(employee_id):
    """
    POST with JSON body: {date: 'YYYY-MM-DD', hours_worked: float, leaves_taken: int, avg_feedback_polarity: float, tasks_completed: int}
    Stores/updates EmployeeMetric record for date.
    """
    payload = request.get_json()
    d = payload.get("date")
    try:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"ok": False, "error": "invalid date"}), 400
    em = EmployeeMetric.query.filter_by(employee_id=employee_id, date=dt).first()
    if not em:
        em = EmployeeMetric(employee_id=employee_id, date=dt)
    em.hours_worked = float(payload.get("hours_worked", 0.0))
    em.leaves_taken = int(payload.get("leaves_taken", 0))
    em.avg_feedback_polarity = float(payload.get("avg_feedback_polarity", 0.0))
    em.tasks_completed = int(payload.get("tasks_completed", 0))
    em.meta = payload.get("meta", {})
    db.session.add(em)
    db.session.commit()
    return jsonify({"ok": True}), 200
