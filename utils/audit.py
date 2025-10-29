import json
from flask import request, current_app
from database.db import db
from models.admin_model import AuditLog, AuditAction, APILog
from datetime import datetime
import functools
import time

def _get_actor_from_request():
    """
    Customize this to extract user id/name from session/jwt.
    We try session['jwt_token'] -> decode to retrieve user_id & email.
    """
    actor = {"id": None, "name": None}
    try:
        from utils.jwt_utils import decode_jwt_from_session
        data = decode_jwt_from_session()
        if data:
            actor["id"] = data.get("user_id")
            actor["name"] = data.get("email")
    except Exception:
        pass
    return actor

def log_audit(action: AuditAction, resource_type: str=None, resource_id: str=None, details: dict=None):
    actor = _get_actor_from_request()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "")
    entry = AuditLog(
        actor_id=actor.get("id"),
        actor_name=actor.get("name"),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details or {},
        ip_address=ip,
        user_agent=ua
    )
    db.session.add(entry)
    db.session.commit()
    current_app.logger.debug(f"Audit logged: {action} by {actor}")

def audit_endpoint(action_name: AuditAction=None, resource_type=None, resource_id_expr=None):
    """
    Decorator to wrap a Flask view — logs an AuditLog entry after successful run.
    resource_id_expr can be a lambda(func_args, func_kwargs, response) to compute resource id.
    Example:
        @audit_endpoint(action_name=AuditAction.DELETE, resource_type="Application", resource_id_expr=lambda a,k,r: k['id'])
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            try:
                rid = None
                if callable(resource_id_expr):
                    try:
                        rid = resource_id_expr(args, kwargs, result)
                    except Exception:
                        rid = None
                # fallback: try to find 'id' in kwargs
                if rid is None:
                    rid = kwargs.get("id") or kwargs.get("app_id") or kwargs.get("resume_id")
                log_audit(action_name or AuditAction.READ, resource_type=resource_type, resource_id=rid, details={"endpoint": request.path})
            except Exception:
                current_app.logger.exception("Failed to write audit log")
            return result
        return wrapper
    return decorator

# ---- API logging middleware helper ----
def log_api_request(path, method, status_code, request_body=None, response_body=None, latency_ms=0.0, actor_id=None):
    entry = APILog(
        path=path,
        method=method,
        status_code=int(status_code) if status_code else None,
        request_body=request_body if isinstance(request_body, dict) else (request_body and str(request_body)),
        response_body=response_body if isinstance(response_body, dict) else (response_body and str(response_body)),
        latency_ms=latency_ms,
        actor_id=actor_id,
        ip_address=request.remote_addr
    )
    db.session.add(entry)
    db.session.commit()
