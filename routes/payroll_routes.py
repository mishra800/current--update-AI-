from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from database.db import db
from models.payroll_model import Attendance, PayrollRecord
from ai_engines.payroll_ai import detect_anomalies, calculate_payroll, predict_salary
from datetime import datetime
import pandas as pd

pay_bp = Blueprint("payroll", __name__, template_folder="../templates", static_folder="../static")

# --- Attendance ---
@pay_bp.route("/attendance/mark", methods=["GET","POST"])
def mark_attendance():
    if request.method=="POST":
        emp_id = int(request.form.get("employee_id"))
        check_in = datetime.strptime(request.form.get("check_in"), "%Y-%m-%dT%H:%M")
        check_out = datetime.strptime(request.form.get("check_out"), "%Y-%m-%dT%H:%M")
        hours = (check_out - check_in).total_seconds()/3600
        geo_lat = request.form.get("geo_lat"); geo_lon = request.form.get("geo_lon")
        att = Attendance(employee_id=emp_id, check_in=check_in, check_out=check_out,
                         hours_worked=hours, geo_lat=geo_lat, geo_lon=geo_lon)
        db.session.add(att); db.session.commit()
        flash("Attendance marked.", "success")
        return redirect(url_for("payroll.list_attendance", employee_id=emp_id))
    return render_template("payroll/attendance_form.html")

@pay_bp.route("/attendance/<int:employee_id>")
def list_attendance(employee_id):
    recs = Attendance.query.filter_by(employee_id=employee_id).order_by(Attendance.check_in.desc()).all()
    return render_template("payroll/attendance_list.html", recs=recs, emp_id=employee_id)

# --- Payroll processing ---
@pay_bp.route("/payroll/process/<int:employee_id>", methods=["POST"])
def process_payroll(employee_id):
    base_salary = float(request.form.get("base_salary"))
    month = request.form.get("month")
    recs = Attendance.query.filter(Attendance.employee_id==employee_id,
                                   Attendance.check_in.like(f"{month}%")).all()
    total_hours = sum(r.hours_worked or 0 for r in recs)
    leaves = sum(1 for r in recs if r.status=="Leave")
    overtime = max(0,total_hours-160)
    final_salary = calculate_payroll(base_salary,total_hours,leaves=leaves)
    record = PayrollRecord(employee_id=employee_id,month=month,base_salary=base_salary,
                           overtime_hours=overtime,leaves=leaves,total_hours=total_hours,
                           final_salary=final_salary)
    db.session.add(record); db.session.commit()
    flash("Payroll processed.", "success")
    return redirect(url_for("payroll.view_payroll", payroll_id=record.id))

@pay_bp.route("/payroll/<int:payroll_id>")
def view_payroll(payroll_id):
    pr = PayrollRecord.query.get_or_404(payroll_id)
    return render_template("payroll/payroll_dashboard.html", pr=pr)

# --- Anomaly detection report ---
@pay_bp.route("/payroll/anomalies")
def anomaly_report():
    # simple global report
    q = Attendance.query.all()
    df = pd.DataFrame([{"emp":a.employee_id,"hours_worked":a.hours_worked,"leaves":1 if a.status=="Leave" else 0,"late_count":0} for a in q])
    if not df.empty:
        df = detect_anomalies(df)
    grouped = df.groupby("emp")["anomaly"].sum().to_dict() if not df.empty else {}
    return render_template("payroll/anomaly_report.html", grouped=grouped)
