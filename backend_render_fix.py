import os, bcrypt
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from flask_migrate import Migrate  # <-- NOVO
from models import db, Usuario, TR, Processo, Proposta

migrate = Migrate()  # <-- NOVO

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")

    # ------------------ Config ------------------
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-me")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

    # ------------------ Extensões ------------------
    CORS(app)  # restrinja origens se quiser
    db.init_app(app)
    migrate.init_app(app, db)  # <-- NOVO: habilita comandos flask db
    JWTManager(app)

    # ------------------ CLI: primeiro admin ------------------
    @app.cli.command("seed-admin")
    def seed_admin():
        """Cria admin padrão se não existir (use uma senha forte!)"""
        with app.app_context():
            email = os.getenv("ADMIN_EMAIL", "admin@local")
            senha = os.getenv("ADMIN_PASSWORD", "Admin#123")
            if Usuario.query.filter_by(email=email).first():
                print("Admin já existe.")
                return
            senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
            u = Usuario(
                nome="Administrador",
                email=email,
                senha_hash=senha_hash,
                perfil="ADMIN",
                ativo=True,
                force_password_change=True
            )
            db.session.add(u)
            db.session.commit()
            print(f"Admin criado: {email}")

    # ------------------ Rotas estáticas ------------------
    @app.route("/")
    def index_root():
        return send_from_directory("static", "index.html")

    # ------------------ Auth ------------------
    @app.post("/auth/login")
    def login():
        data = request.get_json() or {}
        email, senha = data.get("email"), data.get("senha")
        if not email or not senha:
            return jsonify({"erro": "Credenciais obrigatórias"}), 400

        user = Usuario.query.filter_by(email=email).first()
        if not user or not user.ativo:
            return jsonify({"erro": "Usuário inválido ou inativo"}), 401

        # bcrypt: comparar hash
        if not bcrypt.checkpw(senha.encode("utf-8"), user.senha_hash):
            return jsonify({"erro": "Senha incorreta"}), 401

        claims = {"perfil": user.perfil}
        access = create_access_token(identity=user.id, additional_claims=claims)
        refresh = create_refresh_token(identity=user.id, additional_claims=claims)
        return jsonify({
            "access_token": access,
            "refresh_token": refresh,
            "perfil": user.perfil,
            "force_password_change": user.force_password_change
        }), 200

    @app.post("/auth/refresh")
    @jwt_required(refresh=True)
    def refresh():
        uid = get_jwt_identity()
        user = Usuario.query.get(uid)
        if not user or not user.ativo:
            return jsonify({"erro": "Sessão inválida"}), 401
        claims = {"perfil": user.perfil}
        new_access = create_access_token(identity=user.id, additional_claims=claims)
        return jsonify({"access_token": new_access}), 200

    # ------------------ Decorador simples de papel ------------------
    def require_role(*roles):
        def inner(fn):
            from functools import wraps
            @wraps(fn)
            @jwt_required()
            def wrapper(*args, **kwargs):
                uid = get_jwt_identity()
                user = Usuario.query.get(uid)
                if not user or not user.ativo or user.perfil not in roles:
                    return jsonify({"erro": "Acesso negado"}), 403
                return fn(*args, **kwargs)
            return wrapper
        return inner

    # ------------------ Admin: usuários ------------------
    @app.post("/admin/usuarios")
    @require_role("ADMIN")
    def admin_criar_usuario():
        data = request.get_json() or {}
        nome = data.get("nome")
        email = data.get("email")
        perfil = data.get("perfil")
        senha = data.get("senha")  # se ausente, gere temporária no front
        if not all([nome, email, perfil, senha]):
            return jsonify({"erro": "Campos obrigatórios"}), 400
        if Usuario.query.filter_by(email=email).first():
            return jsonify({"erro": "E-mail já cadastrado"}), 409
        # bcrypt hash (até 72 chars efetivos)
        senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())
        u = Usuario(
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            perfil=perfil,
            ativo=True,
            force_password_change=True
        )
        db.session.add(u)
        db.session.commit()
        return jsonify({"id": u.id}), 201

    @app.get("/admin/usuarios")
    @require_role("ADMIN")
    def admin_listar_usuarios():
        q = (request.args.get("q") or "").strip()
        qry = Usuario.query
        if q:
            qry = qry.filter(
                Usuario.email.ilike(f"%{q}%") | Usuario.nome.ilike(f"%{q}%")
            )
        res = [{
            "id": u.id, "nome": u.nome, "email": u.email,
            "perfil": u.perfil, "ativo": u.ativo
        } for u in qry.order_by(Usuario.id.desc()).all()]
        return jsonify(res)

    @app.patch("/admin/usuarios/<int:uid>")
    @require_role("ADMIN")
    def admin_editar_usuario(uid):
        u = Usuario.query.get_or_404(uid)
        data = request.get_json() or {}
        if "nome" in data:
            u.nome = data["nome"]
        if "perfil" in data:
            u.perfil = data["perfil"]
        if "ativo" in data:
            u.ativo = bool(data["ativo"])
        db.session.commit()
        return jsonify({"ok": True})

    @app.post("/admin/usuarios/<int:uid>/reset")
    @require_role("ADMIN")
    def admin_reset_senha(uid):
        u = Usuario.query.get_or_404(uid)
        data = request.get_json() or {}
        nova = data.get("nova_senha")
        if not nova:
            return jsonify({"erro": "nova_senha obrigatória"}), 400
        u.senha_hash = bcrypt.hashpw(nova.encode("utf-8"), bcrypt.gensalt())
        u.force_password_change = True
        db.session.commit()
        return jsonify({"ok": True})

    # ------------------ Saúde ------------------
    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    return app

app = create_app()
