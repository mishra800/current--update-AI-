# models/ats_model.py
from database.db import db
from datetime import datetime
import enum
from sqlalchemy.dialects.postgresql import JSON

class ApplicationStatus(enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"

class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_open = db.Column(db.Boolean, default=True)

    applications = db.relationship("Application", backref="job", lazy="dynamic")

class Applicant(db.Model):
    __tablename__ = "applicants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(50), nullable=True)
    resume_id = db.Column(db.Integer, nullable=True)   # optional link to Resume.id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(JSON, nullable=True)

    applications = db.relationship("Application", backref="applicant", lazy="dynamic")

class Application(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey("applicants.id"), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(ApplicationStatus), default=ApplicationStatus.APPLIED)
    # scoring candidates:
    resume_score = db.Column(db.Float, nullable=True)   # semantic match resume vs job (0..1)
    interview_score = db.Column(db.Float, nullable=True) # average interview score (0..100)
    final_score = db.Column(db.Float, nullable=True)    # 0..100 combined
    meta = db.Column(JSON, nullable=True)               # any extra metadata (notes, tags)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "applicant_id": self.applicant_id,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "status": self.status.value if self.status else None,
            "resume_score": self.resume_score,
            "interview_score": self.interview_score,
            "final_score": self.final_score,
            "meta": self.meta
        }
