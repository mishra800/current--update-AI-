# routes/ats_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.db import db
from models.ats_model import Job, Applicant, Application, ApplicationStatus
from models.resume_model import Resume
from ai_engines.ats_predictor import score_application
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import json

ats_bp = Blueprint("ats", __name__, template_folder="../templates", static_folder="../static")

# Recruiter: create a job
@ats_bp.route("/jobs/create", methods=["GET", "POST"])
def create_job():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        dept = request.form.get("department", "").strip()
        desc = request.form.get("description", "").strip()
        if not title:
            flash("Job title required", "warning")
            return redirect(url_for("ats.create_job"))
        job = Job(title=title, department=dept, description=desc)
        db.session.add(job)
        db.session.commit()
        flash("Job posted.", "success")
        return redirect(url_for("ats.list_jobs"))
    return render_template("ats/job_create.html")

@ats_bp.route("/jobs")
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template("ats/job_list.html", jobs=jobs)

@ats_bp.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    apps = job.applications.order_by(Application.applied_at.desc()).all()
    return render_template("ats/job_detail.html", job=job, applications=apps)

# Candidate: apply to job
@ats_bp.route("/jobs/<int:job_id>/apply", methods=["GET","POST"])
def apply_job(job_id):
    job = Job.query.get_or_404(job_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        resume_id = request.form.get("resume_id")   # optional link to Resume table
        experience_years = float(request.form.get("experience_years", 0) or 0)

        # create applicant (or reuse if email exists)
        applicant = Applicant.query.filter_by(email=email).first()
        if not applicant:
            applicant = Applicant(name=name, email=email, phone=phone, resume_id=resume_id)
            db.session.add(applicant)
            db.session.commit()

        appn = Application(job_id=job.id, applicant_id=applicant.id)
        # compute resume_score from Resume table if provided
        try:
            if resume_id:
                from models.resume_model import Resume as ResumeModel
                r = ResumeModel.query.get(int(resume_id))
                if r and r.match_score:
                    appn.resume_score = float(r.match_score)
        except Exception:
            pass

        # compute final score using predictor with no interview score yet
        appn.final_score = score_application(appn.resume_score or 0.0, appn.interview_score or 0.0, experience_years)
        db.session.add(appn)
        db.session.commit()
        flash("Application submitted. Thank you!", "success")
        return redirect(url_for("ats.job_detail", job_id=job.id))

    # GET -> show basic apply form; allow selecting resume from user's uploads if they exist
    resumes = []
    try:
        resumes = Resume.query.order_by(Resume.uploaded_at.desc()).limit(20).all()
    except Exception:
        resumes = []
    return render_template("ats/apply_form.html", job=job, resumes=resumes)

# Application detail & stage transitions
@ats_bp.route("/application/<int:app_id>")
def application_detail(app_id):
    appn = Application.query.get_or_404(app_id)
    return render_template("ats/application_detail.html", application=appn, statuses=ApplicationStatus)

@ats_bp.route("/application/<int:app_id>/move", methods=["POST"])
def move_application(app_id):
    new_status = request.form.get("status")
    note = request.form.get("note", "")
    appn = Application.query.get_or_404(app_id)
    try:
        appn.status = ApplicationStatus(new_status)
    except Exception:
        flash("Invalid status", "danger")
        return redirect(url_for("ats.application_detail", app_id=app_id))
    # store note in meta
    meta = appn.meta or {}
    if note:
        meta_notes = meta.get("notes", [])
        meta_notes.append({"at": datetime.utcnow().isoformat(), "note": note})
        meta["notes"] = meta_notes
        appn.meta = meta
    db.session.add(appn)
    db.session.commit()
    flash(f"Application moved to {new_status}", "success")
    return redirect(url_for("ats.application_detail", app_id=app_id))

# Auto-rank and promote top N candidates for a job to next stage
@ats_bp.route("/jobs/<int:job_id>/auto_promote", methods=["POST"])
def auto_promote(job_id):
    job = Job.query.get_or_404(job_id)
    top_n = int(request.form.get("top_n", 3))
    # find candidates in APPLIED status, order by final_score desc
    from models.ats_model import ApplicationStatus
    candidates = job.applications.filter(Application.status == ApplicationStatus.APPLIED).order_by(Application.final_score.desc().nullslast()).limit(top_n).all()
    promoted = []
    for c in candidates:
        c.status = ApplicationStatus.SCREENING
        db.session.add(c)
        promoted.append(c.id)
    db.session.commit()
    flash(f"Promoted {len(promoted)} candidates to SCREENING", "success")
    return redirect(url_for("ats.job_detail", job_id=job.id))

# API helper: hook to update application's interview score and recompute final_score
@ats_bp.route("/application/<int:app_id>/update_interview_score", methods=["POST"])
def update_interview_score(app_id):
    # expects JSON body or form with interview_score and optional experience_years
    data = request.get_json() or request.form
    interview_score = float(data.get("interview_score", 0) or 0)
    experience_years = float(data.get("experience_years", 0) or 0)
    appn = Application.query.get_or_404(app_id)
    appn.interview_score = interview_score
    # recompute final_score using predictor
    appn.final_score = score_application(appn.resume_score or 0.0, appn.interview_score or 0.0, experience_years)
    db.session.add(appn)
    db.session.commit()
    return jsonify({"ok": True, "final_score": appn.final_score}), 200
