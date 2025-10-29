from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from database.db import db
from models.admin_model import AuditLog, APILog, AIActivity, RolePermission, AuditAction
from utils.audit import log_audit
import io, csv, datetime, json

admin_bp = Blueprint("admin", __name__, template_folder="../templates", static_folder="../static")

# Simple Admin Dashboard
@admin_bp.route("/admin")
def admin_index():
    # counts
    audits_count = AuditLog.query.count()
    api_count = APILog.query.count()
    ai_count = AIActivity.query.count()
    return render_template("admin/admin_dashboard.html", audits_count=audits_count, api_count=api_count, ai_count=ai_count)

# View audit logs
@admin_bp.route("/admin/audits")
def admin_audits():
    # filters: action, actor_id, from, to, resource_type
    q = AuditLog.query
    action = request.args.get("action")
    actor = request.args.get("actor_id")
    resource_type = request.args.get("resource_type")
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    if action:
        try:
            q = q.filter(AuditLog.action == AuditAction(action))
        except Exception:
            pass
    if actor:
        q = q.filter(AuditLog.actor_id == int(actor))
    if resource_type:
        q = q.filter(AuditLog.resource_type.ilike(f"%{resource_type}%"))
    if from_date:
        q = q.filter(AuditLog.created_at >= datetime.datetime.fromisoformat(from_date))
    if to_date:
        q = q.filter(AuditLog.created_at <= datetime.datetime.fromisoformat(to_date))
    logs = q.order_by(AuditLog.created_at.desc()).limit(500).all()
    return render_template("admin/audit_list.html", logs=logs)

# Export audit logs CSV
@admin_bp.route("/admin/audits/export")
def export_audits():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10000).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id","actor_id","actor_name","action","resource_type","resource_id","details","created_at","ip","agent"])
    for l in logs:
        writer.writerow([
            l.id, l.actor_id, l.actor_name, l.action.value if l.action else None,
            l.resource_type, l.resource_id, json.dumps(l.details or {}), l.created_at.isoformat(), l.ip_address, l.user_agent
        ])
    buffer.seek(0)
    return send_file(io.BytesIO(buffer.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="audit_logs.csv")

# API log viewer & export
@admin_bp.route("/admin/api_logs")
def view_api_logs():
    logs = APILog.query.order_by(APILog.created_at.desc()).limit(500).all()
    return render_template("admin/api_logs.html", logs=logs)

@admin_bp.route("/admin/api_logs/export")
def export_api_logs():
    logs = APILog.query.order_by(APILog.created_at.desc()).limit(10000).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id","path","method","status_code","latency_ms","actor_id","created_at"])
    for l in logs:
        writer.writerow([l.id, l.path, l.method, l.status_code, l.latency_ms, l.actor_id, l.created_at.isoformat()])
    buffer.seek(0)
    return send_file(io.BytesIO(buffer.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="api_logs.csv")

# AI activity viewer
@admin_bp.route("/admin/ai_activity")
def ai_activity():
    q = AIActivity.query.order_by(AIActivity.created_at.desc()).limit(1000).all()
    return render_template("admin/ai_activity.html", rows=q)

# Role permission CRUD (very small)
@admin_bp.route("/admin/permissions", methods=["GET","POST"])
def permissions():
    if request.method == "POST":
        role = request.form.get("role_name")
        perm = request.form.get("permission")
        if role and perm:
            rp = RolePermission(role_name=role, permission=perm)
            db.session.add(rp); db.session.commit()
            log_audit(action=AuditAction.PERMISSION_CHANGE, resource_type="RolePermission", details={"role": role, "permission": perm})
    items = RolePermission.query.order_by(RolePermission.created_at.desc()).all()
    return render_template("admin/permissions.html", items=items)

@admin_bp.route("/admin/permissions/delete/<int:pid>", methods=["POST"])
def permission_delete(pid):
    p = RolePermission.query.get_or_404(pid)
    db.session.delete(p); db.session.commit()
    log_audit(action=AuditAction.PERMISSION_CHANGE, resource_type="RolePermission", details={"deleted_id": pid})
    return ("", 204)
