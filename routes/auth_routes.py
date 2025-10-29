# routes/auth_routes.py

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db
from models.user_model import User
from utils.jwt_utils import generate_token

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    hashed_pw = generate_password_hash(data["password"], method="sha256")
    user = User(email=data["email"], password=hashed_pw)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered successfully!"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token({"user_id": user.id})
    return jsonify({"token": token, "message": "Login successful"}), 200
