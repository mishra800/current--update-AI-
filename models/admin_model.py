from database.db import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
import enum

class AuditAction(enum.Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    API_CALL = "API_CALL"
    MODEL_CALL = "MODEL_CALL"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.BigInteger, primary_key=True)
    actor_id = db.Column(db.Integer, nullable=True)           # user id who performed action
    actor_name = db.Column(db.String(255), nullable=True)
    action = db.Column(db.Enum(AuditAction), nullable=False)
    resource_type = db.Column(db.String(128), nullable=True)  # e.g., "Application", "Resume", "Offer"
    resource_id = db.Column(db.String(128), nullable=True)
    details = db.Column(JSON, nullable=True)                  # extra structured data
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

class APILog(db.Model):
    __tablename__ = "api_logs"
    id = db.Column(db.BigInteger, primary_key=True)
    path = db.Column(db.String(512), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer, nullable=True)
    request_body = db.Column(JSON, nullable=True)
    response_body = db.Column(JSON, nullable=True)
    latency_ms = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    actor_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)

class AIActivity(db.Model):
    __tablename__ = "ai_activity"
    id = db.Column(db.BigInteger, primary_key=True)
    model_name = db.Column(db.String(255), nullable=False)      # e.g., "gpt-4o-mini" or "mistral-7b"
    endpoint = db.Column(db.String(255), nullable=True)        # route that triggered model call
    payload_summary = db.Column(db.String(1024), nullable=True)
    latency_ms = db.Column(db.Float, nullable=False)
    success = db.Column(db.Boolean, default=True)
    error_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    actor_id = db.Column(db.Integer, nullable=True)
    cost_estimate = db.Column(db.Float, nullable=True)         # optional, for cost tracking

class RolePermission(db.Model):
    __tablename__ = "role_permissions"
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(100), nullable=False, index=True)   # e.g., "hr", "admin", "employee"
    permission = db.Column(db.String(200), nullable=False)             # e.g., "view_audit", "export_audit"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
