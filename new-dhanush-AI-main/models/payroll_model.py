from database.db import db
from datetime import datetime, date
from sqlalchemy.dialects.postgresql import JSON

class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False, index=True)
    check_in = db.Column(db.DateTime, nullable=False)
    check_out = db.Column(db.DateTime, nullable=True)
    hours_worked = db.Column(db.Float, default=0.0)
    geo_lat = db.Column(db.Float, nullable=True)
    geo_lon = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default="Present")  # Present/Leave/Late
    meta = db.Column(JSON, nullable=True)

class PayrollRecord(db.Model):
    __tablename__ = "payroll_records"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False, index=True)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    base_salary = db.Column(db.Float, nullable=False)
    overtime_hours = db.Column(db.Float, default=0.0)
    leaves = db.Column(db.Integer, default=0)
    total_hours = db.Column(db.Float, default=0.0)
    final_salary = db.Column(db.Float, nullable=True)
    anomalies = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
