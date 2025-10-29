# models/chatbot_model.py
from database.db import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

class ChatSession(db.Model):
    __tablename__ = "chat_sessions"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, nullable=True)   # optional user id
    session_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(JSON, nullable=True)

class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)   # user / assistant / system
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(JSON, nullable=True)

    session = db.relationship("ChatSession", backref=db.backref("messages", lazy="dynamic"))
