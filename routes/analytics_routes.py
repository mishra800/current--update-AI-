from flask import Blueprint, request, jsonify, render_template
from database.db import db
from models.analytics_model import AnalyticsSnapshot
from ai_engines.analytics_forecast import forecast_hiring, cluster_employees, summarize_insights
import pandas as pd
from datetime import datetime

analytics_bp = Blueprint("analytics", __name__, template_folder="../templates", static_folder="../static")

# ---------- API ENDPOINTS ----------

@analytics_bp.route("/forecast", methods=["POST"])
def forecast_api():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "CSV file required"}), 400
    df = pd.read_csv(file)
    forecast = forecast_hiring(df)
    snap = AnalyticsSnapshot(type="forecast", title="Hiring Forecast", data=forecast.to_dict(orient="records"))
    db.session.add(snap); db.session.commit()
    return jsonify(snap.data)

@analytics_bp.route("/cluster", methods=["POST"])
def cluster_api():
    df = pd.read_csv(request.files["file"])
    clustered, centers = cluster_employees(df)
    snap = AnalyticsSnapshot(type="cluster", title="Employee Clusters",
                             data={"clusters": clustered.to_dict(orient="records"),
                                   "centroids": centers})
    db.session.add(snap); db.session.commit()
    return jsonify(snap.data)

@analytics_bp.route("/summary", methods=["POST"])
def summary_api():
    text = request.json.get("text", "")
    summary = summarize_insights(text)
    snap = AnalyticsSnapshot(type="summary", title="AI Summary", data={"text": summary})
    db.session.add(snap); db.session.commit()
    return jsonify(snap.data)

# ---------- DASHBOARD UI ----------
@analytics_bp.route("/dashboard")
def dashboard_page():
    snaps = AnalyticsSnapshot.query.order_by(AnalyticsSnapshot.created_at.desc()).limit(10).all()
    return render_template("analytics/analytics_dashboard.html", snaps=snaps)
