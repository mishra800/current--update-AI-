from database.db import db
from models.admin_model import AIActivity
from datetime import datetime

def record_model_activity(model_name: str, endpoint: str, payload_summary: str, latency_ms: float, success: bool=True, error_text: str=None, actor_id: int=None, cost_estimate: float=None):
    a = AIActivity(
        model_name=model_name,
        endpoint=endpoint,
        payload_summary=payload_summary[:1000] if payload_summary else None,
        latency_ms=float(latency_ms),
        success=bool(success),
        error_text=error_text,
        created_at=datetime.utcnow(),
        actor_id=actor_id,
        cost_estimate=cost_estimate
    )
    db.session.add(a)
    db.session.commit()
