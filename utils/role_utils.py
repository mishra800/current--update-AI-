from functools import wraps
from flask import session, redirect, url_for, flash, request
from models.user_model import UserRole
import jwt
from config.config import Config

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = session.get("jwt_token")
        if not token:
            flash("Please login to access this page.", "warning")
            return redirect(url_for('auth.login'))
        try:
            jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
        except Exception:
            flash("Session expired. Please login again.", "warning")
            return redirect(url_for('auth.login'))
        return fn(*args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = session.get("jwt_token")
            if not token:
                flash("Please login.", "warning")
                return redirect(url_for('auth.login'))
            try:
                data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
                user_role = data.get("role")
                if user_role not in allowed_roles:
                    flash("You do not have permission to access this page.", "danger")
                    return redirect(url_for('auth.login'))
            except Exception:
                flash("Invalid session. Please login again.", "warning")
                return redirect(url_for('auth.login'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator
