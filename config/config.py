import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-to-a-strong-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/ai_hr_app"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "another-secret")
    JWT_EXP_DELTA_SECONDS = int(os.environ.get("JWT_EXP_DELTA_SECONDS", 7200))  # 2 hours
