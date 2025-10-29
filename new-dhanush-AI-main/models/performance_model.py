from database.db import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

class Feedback(db.Model):
    __tablename__ = "feedbacks"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, nullable=True)        # optional FK to users.id
    employee_id = db.Column(db.Integer, nullable=False, index=True)   # who the feedback is about
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # sentiment fields
    polarity = db.Column(db.Float, nullable=True)           # -1 .. 1 (TextBlob/VADER aggregate)
    subjectivity = db.Column(db.Float, nullable=True)       # 0..1
    vader_compound = db.Column(db.Float, nullable=True)
    tags = db.Column(JSON, nullable=True)                   # extracted tags/keywords
    meta = db.Column(JSON, nullable=True)                   # store model details (e.g., llm_summary_id)

class PerformanceReview(db.Model):
    __tablename__ = "performance_reviews"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False, index=True)
    reviewer_id = db.Column(db.Integer, nullable=True)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    scores = db.Column(JSON, nullable=True)      # e.g., {'communication': 4, 'delivery':3.5}
    overall_score = db.Column(db.Float, nullable=True)
    summary = db.Column(db.Text, nullable=True)  # AI generated summary
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(JSON, nullable=True)

class EmployeeMetric(db.Model):
    """
    Time-series metrics for employees (attendance, hours, avg_feedback_sentiment, tasks_completed)
    Aggregated daily/weekly/monthly.
    """
    __tablename__ = "employee_metrics"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)   # day for the metric
    hours_worked = db.Column(db.Float, nullable=True)
    leaves_taken = db.Column(db.Integer, nullable=True, default=0)
    avg_feedback_polarity = db.Column(db.Float, nullable=True)
    tasks_completed = db.Column(db.Integer, nullable=True, default=0)
    meta = db.Column(JSON, nullable=True)
