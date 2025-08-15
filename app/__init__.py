from flask import Flask, jsonify
from .config import get_config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    from . import models  # noqa: F401

    from .auth import bp as auth_bp
    from .invitations import bp as invitations_bp
    from .requisitante import bp as requisitante_bp
    from .comprador import bp as comprador_bp
    from .fornecedor import bp as fornecedor_bp
    from .analysis import bp as analysis_bp
    from .files import bp as files_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(invitations_bp, url_prefix="/api/invitations")
    app.register_blueprint(requisitante_bp, url_prefix="/api/requisitante")
    app.register_blueprint(comprador_bp, url_prefix="/api/comprador")
    app.register_blueprint(fornecedor_bp, url_prefix="/api/fornecedor")
    app.register_blueprint(analysis_bp, url_prefix="/api/analysis")
    app.register_blueprint(files_bp, url_prefix="/api/files")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}, 200

    def bootstrap_admin():
        email = os.environ.get("FIRST_ADMIN_EMAIL")
        name = os.environ.get("FIRST_ADMIN_NAME")
        password = os.environ.get("FIRST_ADMIN_PASSWORD")
        if not (email and name and password):
            return
        from .models import User
        if User.query.count() == 0 and "@" in email:
            u = User(email=email.lower(), name=name, role="ADMIN", active=True)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()

    # Flask 3.x removeu before_first_request – execute o bootstrap na criação da app.
    with app.app_context():
        bootstrap_admin()

    @app.errorhandler(400)
    @app.errorhandler(422)
    def bad_request(e):
        return jsonify({"error": "bad_request"}), 400

    return app
