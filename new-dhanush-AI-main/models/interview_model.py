from database.db import db
from datetime import datetime
import json
from sqlalchemy.dialects.postgresql import JSON

class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)         # e.g., "Python OOP"
    prompt = db.Column(db.Text, nullable=False)               # the question text
    reference_answer = db.Column(db.Text, nullable=True)      # model/reference ideal answer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Interview(db.Model):
    __tablename__ = "interviews"
    id = db.Column(db.Integer, primary_key=True)
    candidate_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, nullable=True)                # overall average score
    meta = db.Column(JSON, nullable=True)

class Response(db.Model):
    __tablename__ = "responses"
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey("interviews.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    answer_text = db.Column(db.Text, nullable=True)
    audio_filename = db.Column(db.String(255), nullable=True)
    score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    interview = db.relationship("Interview", backref=db.backref("responses", lazy="dynamic"))
    question = db.relationship("Question")
