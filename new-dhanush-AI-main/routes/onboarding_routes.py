from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from database.db import db
from models.onboarding_model import OnboardingRequest, OnboardingTask, OfferLetter, TaskStatus
from utils.offer_utils import generate_offer_docx
from utils.mailer import send_email
from datetime import datetime, date
import os

onboard_bp = Blueprint("onboard", __name__, template_folder="../templates", static_folder="../static")

# Create onboarding request
@onboard_bp.route("/requests/create", methods=["GET", "POST"])
def create_request():
    if request.method == "POST":
        name = request.form.get("candidate_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        position = request.form.get("position", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        start_date = None
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except Exception:
            pass

        if not name or not email or not position:
            flash("Name, email and position are required.", "warning")
            return redirect(url_for("onboard.create_request"))

        req = OnboardingRequest(candidate_name=name, email=email, phone=phone, position=position, start_date=start_date)
        db.session.add(req)
        db.session.commit()

        # create default tasks
        default_tasks = [
            ("Create corporate email account", "Create a company email for the new user", "IT"),
            ("Prepare workstation & access", "Allocate laptop and necessary software", "IT"),
            ("ID card & office access", "Create ID card and grant access", "Admin"),
            ("Payroll registration", "Add to payroll system and collect bank details", "Finance"),
            ("Welcome & orientation", "Schedule orientation and assign buddy", "HR")
        ]
        for t in default_tasks:
            task = OnboardingTask(request_id=req.id, title=t[0], description=t[1], owner=t[2])
            db.session.add(task)
        db.session.commit()
        flash("Onboarding request created and tasks assigned.", "success")
        return redirect(url_for("onboard.view_request", request_id=req.id))

    return render_template("onboard/create_request.html")

# List requests
@onboard_bp.route("/requests")
def list_requests():
    reqs = OnboardingRequest.query.order_by(OnboardingRequest.created_at.desc()).all()
    return render_template("onboard/request_list.html", requests=reqs)

# View request detail & tasks
@onboard_bp.route("/request/<int:request_id>")
def view_request(request_id):
    req = OnboardingRequest.query.get_or_404(request_id)
    tasks = req.tasks.order_by(OnboardingTask.created_at.asc()).all()
    return render_template("onboard/request_detail.html", request=req, tasks=tasks, TaskStatus=TaskStatus)

# Update task status (AJAX/form)
@onboard_bp.route("/task/<int:task_id>/update", methods=["POST"])
def update_task(task_id):
    task = OnboardingTask.query.get_or_404(task_id)
    new_status = request.form.get("status")
    owner = request.form.get("owner")
    if new_status:
        try:
            task.status = TaskStatus(new_status)
        except Exception:
            # if invalid int/string, fallback to plain string handling for earlier versions
            task.status = new_status
    if owner:
        task.owner = owner
    db.session.add(task)
    db.session.commit()
    flash("Task updated.", "success")
    return redirect(url_for("onboard.view_request", request_id=task.request_id))

# Generate offer letter (DOCX) and save record
@onboard_bp.route("/request/<int:request_id>/generate_offer", methods=["POST"])
def generate_offer(request_id):
    req = OnboardingRequest.query.get_or_404(request_id)
    compensation = request.form.get("compensation", "").strip()
    hr_name = request.form.get("hr_name", "HR Team").strip()
    company_name = request.form.get("company_name", "Company").strip()
    vars = {
        "candidate_name": req.candidate_name,
        "position": req.position,
        "start_date": req.start_date.isoformat() if req.start_date else "",
        "compensation": compensation,
        "hr_name": hr_name,
        "company_name": company_name,
        "date": datetime.utcnow().strftime("%Y-%m-%d")
    }
    path = generate_offer_docx(vars, filename_prefix="Offer")
    # create OfferLetter record (one per request)
    # if exists, update
    existing = OfferLetter.query.filter_by(request_id=req.id).first()
    if existing:
        existing.filename = os.path.basename(path)
        existing.template_vars = vars
        existing.generated_at = datetime.utcnow()
        db.session.add(existing)
    else:
        ol = OfferLetter(request_id=req.id, filename=os.path.basename(path), template_vars=vars)
        db.session.add(ol)
    db.session.commit()
    flash("Offer letter generated.", "success")
    return redirect(url_for("onboard.view_request", request_id=req.id))

# Download offer letter
@onboard_bp.route("/offer/<int:request_id>/download")
def download_offer(request_id):
    ol = OfferLetter.query.filter_by(request_id=request_id).first_or_404()
    path = os.path.join("generated_offers", ol.filename)
    if not os.path.exists(path):
        flash("Offer file not found.", "danger")
        return redirect(url_for("onboard.view_request", request_id=request_id))
    return send_file(path, as_attachment=True)

# Send offer letter by email (synchronously)
@onboard_bp.route("/offer/<int:request_id>/send", methods=["POST"])
def send_offer(request_id):
    ol = OfferLetter.query.filter_by(request_id=request_id).first_or_404()
    req = ol.request
    path = os.path.join("generated_offers", ol.filename)
    subject = request.form.get("subject", f"Offer Letter from {request.form.get('company_name','Company')}")
    body = request.form.get("body", f"Dear {req.candidate_name},\n\nPlease find attached your offer letter.\n\nBest,\nHR")
    try:
        send_email([req.email], subject, body, html=None, attachments=[path])
        flash("Offer sent by email.", "success")
    except Exception as e:
        current_app.logger.exception("Failed to send offer email")
        flash("Failed to send email. Check mail server settings.", "danger")
    return redirect(url_for("onboard.view_request", request_id=request_id))

# Simple endpoint to trigger reminder emails for pending tasks (can be queued via Celery)
@onboard_bp.route("/request/<int:request_id>/send_task_reminders", methods=["POST"])
def send_task_reminders(request_id):
    req = OnboardingRequest.query.get_or_404(request_id)
    pending = req.tasks.filter(OnboardingTask.status != TaskStatus.DONE).all()
    # build message per owner
    owner_map = {}
    for t in pending:
        owner_map.setdefault(t.owner or "team", []).append(t)
    sent = 0
    for owner, tasks in owner_map.items():
        # if owner looks like an email, send there; else send to HR user (FROM_ADDRESS)
        to_addr = [owner] if "@" in (owner or "") else [os.environ.get("FROM_ADDRESS", os.environ.get("SMTP_USER",""))]
        subject = f"Pending onboarding tasks for {req.candidate_name}"
        lines = [f"Tasks for {req.candidate_name} ({req.position}):"]
        for tt in tasks:
            lines.append(f"- {tt.title} (due: {tt.due_date or 'N/A'})")
        try:
            send_email(to_addr, subject, "\n".join(lines))
            sent += 1
        except Exception:
            current_app.logger.exception("Reminder send failed")
    flash(f"Reminders sent to {sent} owners (best-effort).", "info")
    return redirect(url_for("onboard.view_request", request_id=request_id))
