# models/analytics_model.py

from database.db import db
from datetime import datetime

class AnalyticsSnapshot(db.Model):
    __tablename__ = "analytics_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    total_resumes = db.Column(db.Integer, default=0)
    shortlisted = db.Column(db.Integer, default=0)
    rejected = db.Column(db.Integer, default=0)
    hired = db.Column(db.Integer, default=0)

    avg_experience = db.Column(db.Float, default=0.0)
    top_skills = db.Column(db.Text)  # store JSON string list of skills

    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
