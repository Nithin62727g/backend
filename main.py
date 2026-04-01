from flask import Flask, jsonify
from flask_cors import CORS
from core.database import init_app as init_db
from core.ai import init_ai_client
from api.auth import auth_bp
from api.roadmaps import roadmaps_bp
from api.mentor import mentor_bp
from api.quizzes import quizzes_bp
from api.career import career_bp
from api.videos import videos_bp
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


def create_app():
    app = Flask(__name__)

    # Enable CORS for all origins (Android app & web)
    CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization", "Accept"]}})

    # Init DB teardown hook
    init_db(app)

    # Init AI client (Roadmaps & Quizzes run here; AI Mentor runs in frontend)
    with app.app_context():
        init_ai_client()

    # Register Blueprints
    app.register_blueprint(auth_bp,      url_prefix="/api/v1/auth")
    app.register_blueprint(roadmaps_bp,  url_prefix="/api/v1/roadmaps")
    app.register_blueprint(mentor_bp,    url_prefix="/api/v1/mentor")
    app.register_blueprint(quizzes_bp,   url_prefix="/api/v1/quizzes")
    app.register_blueprint(career_bp,    url_prefix="/api/v1/career")
    app.register_blueprint(videos_bp,    url_prefix="/api/v1/videos")

    @app.get("/")
    def root():
        return jsonify({"message": "Welcome to MasterAI Backend API 🚀 (Flask + MariaDB)"})

    @app.get("/health")
    def health():
        from core.database import get_db
        try:
            db = get_db()
            with db.cursor() as cursor:
                cursor.execute("SELECT 1")
            return jsonify({"status": "ok", "database": "connected"})
        except Exception as e:
            return jsonify({"status": "error", "database": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8001, debug=True)
