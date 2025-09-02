# -*- coding: utf-8 -*-
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from .config import Config

db = SQLAlchemy()
jwt = JWTManager()

# SocketIO: eventlet/gevent supported; fall back to threading if not installed
# In production on Render, use gunicorn with eventlet worker (see README).
socketio = SocketIO(cors_allowed_origins="*")


def create_app() -> Flask:
    app = Flask(__name__, static_folder="../static", static_url_path="/static")
    app.config.from_object(Config())

    CORS(app)  # allow cross-origin for MVP
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()

        # Register blueprints
        from .blueprints.auth import bp as auth_bp
        from .blueprints.procurements import bp as proc_bp
        from .blueprints.tr import bp as tr_bp
        from .blueprints.proposals import bp as proposals_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(proc_bp, url_prefix="/api")
        app.register_blueprint(tr_bp, url_prefix="/api")
        app.register_blueprint(proposals_bp, url_prefix="/api")

        # Simple healthcheck
        @app.get("/healthz")
        def healthz():
            return {"status": "ok"}

    return app
