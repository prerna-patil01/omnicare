"""Application factory."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import BASE_DIR, get_config
from .extensions import cors, db, jwt, migrate

load_dotenv(BASE_DIR / ".env")


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)

    config = get_config(config_name)
    config.validate()
    app.config.from_object(config)

    # SQLite needs the directory to exist before the engine opens the file.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    # Import for the side effect of registering mappers, so Alembic
    # autogenerate sees the tables.
    from . import models  # noqa: F401
    from .api import bp as api_bp
    from .auth.routes import bp as auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    _register_error_handlers(app)
    _register_jwt_handlers(app)

    @app.get("/api/health")
    def health():
        return jsonify({"data": {"status": "ok"}}), 200

    return app


def _register_error_handlers(app):
    """Every error leaves as JSON. A stray HTML 500 hitting an Axios client
    surfaces as an unparseable blob, which is how "something went wrong" bugs
    become unreadable."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        return jsonify({"message": err.description}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Unhandled exception: %s", err)
        db.session.rollback()
        if app.config.get("DEBUG"):
            return jsonify({"message": f"{type(err).__name__}: {err}"}), 500
        return jsonify({"message": "Something went wrong on our end."}), 500


def _register_jwt_handlers(app):
    """Default flask-jwt-extended errors use their own body shape; normalise
    them to {"message": ...} so the frontend has one parser."""

    @jwt.expired_token_loader
    def expired(_header, _payload):
        return jsonify({"message": "Your session has expired.",
                        "code": "token_expired"}), 401

    @jwt.invalid_token_loader
    def invalid(reason):
        return jsonify({"message": "Invalid authentication token.",
                        "code": "token_invalid", "detail": reason}), 401

    @jwt.unauthorized_loader
    def missing(reason):
        return jsonify({"message": "Authentication required.",
                        "code": "token_missing", "detail": reason}), 401
