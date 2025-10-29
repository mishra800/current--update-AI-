from database.db import db
from datetime import datetime
import json
from sqlalchemy.dialects.postgresql import JSON

class Resume(db.Model):
    __tablename__ = "resumes"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, nullable=True)  # FK to users.id - add constraint as needed
    parsed_text = db.Column(db.Text, nullable=True)
    skills = db.Column(JSON, nullable=True)             # JSON list of detected skills
    embedding = db.Column(db.Text, nullable=True)       # JSON string of embedding vector
    match_score = db.Column(db.Float, nullable=True)    # score vs last matched job
    meta = db.Column(JSON, nullable=True)               # other parsed metadata (education, experience)

    def set_embedding(self, arr):
        self.embedding = json.dumps([float(x) for x in arr])

    def get_embedding(self):
        if not self.embedding:
            return None
        return json.loads(self.embedding)
