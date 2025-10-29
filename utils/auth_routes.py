from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from database.db import db
from models.user_model import User, UserRole
from utils.security import hash_password, verify_password, generate_jwt, decode_jwt
from utils.role_utils import login_required, role_required
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint("auth", __name__, template_folder="../templates", static_folder="../static")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "employee")

        if not username or not email or not password:
            flash("Please fill required fields.", "warning")
            return redirect(url_for("auth.register"))

        pw_hash = hash_password(password)
        try:
            user = User(username=username, email=email, password_hash=pw_hash, role=UserRole(role))
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("auth.login"))
        except IntegrityError:
            db.session.rollback()
            flash("Email already registered.", "danger")
            return redirect(url_for("auth.register"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Register error")
            flash("An error occurred. Try again.", "danger")
            return redirect(url_for("auth.register"))

    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not verify_password(user.password_hash, password):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.login"))

        # prepare JWT
        payload = {"user_id": user.id, "email": user.email, "role": user.role.value}
        token = generate_jwt(payload)

        # store token in session for browser-based pages (simple approach)
        session["jwt_token"] = token
        session.permanent = True  # can configure PERMANENT_SESSION_LIFETIME if needed

        # Redirect based on role
        if user.role == UserRole.ADMIN:
            return redirect(url_for("auth.admin_dashboard"))
        elif user.role == UserRole.HR:
            return redirect(url_for("auth.hr_dashboard"))
        else:
            return redirect(url_for("auth.employee_dashboard"))

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("jwt_token", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

# Dashboards (simple placeholders)
@auth_bp.route("/dashboard/admin")
@role_required("admin")
def admin_dashboard():
    token = session.get("jwt_token")
    data = decode_jwt(token)
    return render_template("dashboards/admin_dashboard.html", user=data)

@auth_bp.route("/dashboard/hr")
@role_required("hr")
def hr_dashboard():
    token = session.get("jwt_token")
    data = decode_jwt(token)
    return render_template("dashboards/hr_dashboard.html", user=data)

@auth_bp.route("/dashboard/employee")
@login_required
def employee_dashboard():
    token = session.get("jwt_token")
    data = decode_jwt(token)
    return render_template("dashboards/employee_dashboard.html", user=data)
