# routes/performance_routes.py

from flask import Blueprint, request, jsonify
from database.db import db
from models.performance_model import PerformanceReview  # adjust if your model name differs

perf_bp = Blueprint("perf_bp", __name__)

@perf_bp.route("/submit", methods=["POST"])
def submit_performance_review():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    review = PerformanceReview(
        employee_id=data.get("employee_id"),
        reviewer=data.get("reviewer"),
        rating=data.get("rating"),
        feedback=data.get("feedback"),
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({"message": "Performance review submitted successfully"}), 201


@perf_bp.route("/list/<int:employee_id>", methods=["GET"])
def get_reviews(employee_id):
    reviews = PerformanceReview.query.filter_by(employee_id=employee_id).all()
    return jsonify([{
        "reviewer": r.reviewer,
        "rating": r.rating,
        "feedback": r.feedback,
        "created_at": r.created_at.strftime("%Y-%m-%d")
    } for r in reviews]), 200
