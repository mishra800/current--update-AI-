from database.db import db
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    HR = "hr"
    EMPLOYEE = "employee"

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
