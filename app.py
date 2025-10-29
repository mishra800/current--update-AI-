from flask import Flask, request, current_app, render_template
from config.config import Config
from database.db import db, migrate

# Import all blueprints
from routes.auth_routes import auth_bp
from routes.resume_routes import resume_bp
from routes.interview_routes import interview_bp
from routes.ats_routes import ats_bp
from routes.onboarding_routes import onboard_bp
from routes.performance_routes import perf_bp
from routes.analytics_routes import analytics_bp
from routes.chatbot_routes import chatbot_bp
from routes.admin_routes import admin_bp

from time import time


def create_app():
    """Flask app factory for AI HR Application"""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints (all modules)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(resume_bp, url_prefix="/resume")
    app.register_blueprint(interview_bp, url_prefix="/interview")
    app.register_blueprint(ats_bp, url_prefix="/ats")
    app.register_blueprint(onboard_bp, url_prefix="/onboard")
    app.register_blueprint(perf_bp, url_prefix="/performance")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # ✅ Root Landing Page (UI)
    @app.route("/")
    def index():
        return render_template("index.html")

    # API Request Logging (optional)
    @app.before_request
    def _start_timer():
        request._start_time = time()

    @app.after_request
    def _log_api(response):
        try:
            latency = (time() - getattr(request, "_start_time", time())) * 1000.0
        except Exception:
            latency = None

        try:
            from utils.audit import log_api_request
            log_api_request(
                path=request.path,
                method=request.method,
                status_code=response.status_code,
                latency_ms=latency,
            )
        except Exception:
            pass

        return response

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
