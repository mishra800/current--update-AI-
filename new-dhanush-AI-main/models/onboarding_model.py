from database.db import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
import enum

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class OnboardingRequest(db.Model):
    __tablename__ = "onboarding_requests"
    id = db.Column(db.Integer, primary_key=True)
    candidate_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(50), nullable=True)
    position = db.Column(db.String(255), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="initiated")   # initiated, in_progress, completed
    meta = db.Column(JSON, nullable=True)                     # extra info

    tasks = db.relationship("OnboardingTask", backref="request", lazy="dynamic")
    offer = db.relationship("OfferLetter", uselist=False, backref="request")

class OnboardingTask(db.Model):
    __tablename__ = "onboarding_tasks"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("onboarding_requests.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner = db.Column(db.String(255), nullable=True)   # e.g., IT, Admin, HR person name/email
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING)
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(JSON, nullable=True)

class OfferLetter(db.Model):
    __tablename__ = "offer_letters"
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("onboarding_requests.id"), nullable=False, unique=True)
    filename = db.Column(db.String(255), nullable=False)       # stored filename on disk
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    template_vars = db.Column(JSON, nullable=True)
