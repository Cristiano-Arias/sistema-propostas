# backend_render_fix.py - Versão Final Limpa
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Configurações
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'portal-propostas-2025-secure-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-2025')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///propostas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Corrigir URL do PostgreSQL
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Inicializar extensões
CORS(app, resources={r"/*": {"origins": "*"}})
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Modelos do banco de dados
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    perfil = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

class TermoReferencia(db.Model):
    __tablename__ = 'termos_referencia'
    id = db.Column(db.Integer, primary_key=True)
    numero_tr = db.Column(db.String(50), unique=True, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    requisitante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    status = db.Column(db.String(50), default='rascunho')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class Processo(db.Model):
    __tablename__ = 'processos'
    id = db.Column(db.Integer, primary_key=True)
    numero_processo = db.Column(db.String(50), unique=True, nullable=False)
    tr_id = db.Column(db.Integer, db.ForeignKey('termos_referencia.id'))
    comprador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    status = db.Column(db.String(50), default='aberto')
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    modalidade = db.Column(db.String(50), nullable=False)

class Proposta(db.Model):
    __tablename__ = 'propostas'
    id = db.Column(db.Integer, primary_key=True)
    processo_id = db.Column(db.Integer, db.ForeignKey('processos.id'))
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    valor = db.Column(db.Float, nullable=False)
    prazo_entrega = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='enviada')
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)

# Criar tabelas
with app.app_context():
    db.create_all()
    logger.info("Tabelas criadas/verificadas")

# Rotas de autenticação
@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({'erro': 'Email e senha são obrigatórios'}), 400
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and check_password_hash(usuario.senha_hash, senha):
            access_token = create_access_token(
                identity=str(usuario.id),
                additional_claims={'perfil': usuario.perfil, 'email': usuario.email}
            )
            
            return jsonify({
                'access_token': access_token,
                'perfil': usuario.perfil,
                'nome': usuario.nome,
                'email': usuario.email
            }), 200
        
        return jsonify({'erro': 'Credenciais inválidas'}), 401
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        if Usuario.query.filter_by(email=data.get('email')).first():
            return jsonify({'erro': 'Email já cadastrado'}), 409
        
        novo_usuario = Usuario(
            email=data.get('email'),
            senha_hash=generate_password_hash(data.get('senha')),
            nome=data.get('nome'),
            perfil=data.get('perfil', 'requisitante')
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({'mensagem': 'Usuário criado', 'id': novo_usuario.id}), 201
        
    except Exception as e:
        logger.error(f"Erro no registro: {e}")
        return jsonify({'erro': 'Erro ao criar usuário'}), 500

# Rotas admin
@app.route('/admin/usuarios', methods=['GET', 'POST'])
@jwt_required()
def gerenciar_usuarios():
    current_user_id = get_jwt_identity()
    usuario = Usuario.query.get(int(current_user_id))
    
    if not usuario or usuario.perfil != 'ADMIN':
        return jsonify({'erro': 'Acesso negado'}), 403
    
    if request.method == 'GET':
        q = request.args.get('q', '')
        query = Usuario.query
        
        if q:
            query = query.filter(
                db.or_(
                    Usuario.nome.ilike(f'%{q}%'),
                    Usuario.email.ilike(f'%{q}%')
                )
            )
        
        usuarios = query.all()
        return jsonify([{
            'id': u.id,
            'email': u.email,
            'nome': u.nome,
            'perfil': u.perfil,
            'ativo': u.ativo,
            'criado_em': u.criado_em.isoformat() if u.criado_em else None
        } for u in usuarios]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        
        if Usuario.query.filter_by(email=data.get('email')).first():
            return jsonify({'erro': 'Email já existe'}), 409
        
        novo_usuario = Usuario(
            email=data.get('email'),
            senha_hash=generate_password_hash(data.get('senha')),
            nome=data.get('nome'),
            perfil=data.get('perfil', 'requisitante')
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({'id': novo_usuario.id}), 201

@app.route('/admin/usuarios/<int:user_id>/reset', methods=['POST'])
@jwt_required()
def reset_senha(user_id):
    current_user_id = get_jwt_identity()
    admin = Usuario.query.get(int(current_user_id))
    
    if not admin or admin.perfil != 'ADMIN':
        return jsonify({'erro': 'Acesso negado'}), 403
    
    data = request.get_json()
    usuario = Usuario.query.get(user_id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    usuario.senha_hash = generate_password_hash(data.get('nova_senha'))
    db.session.commit()
    
    return jsonify({'mensagem': 'Senha atualizada'}), 200

# APIs REST
@app.route('/api/termos-referencia', methods=['GET', 'POST'])
@jwt_required()
def termos_referencia():
    if request.method == 'GET':
        termos = TermoReferencia.query.all()
        return jsonify([{
            'id': tr.id,
            'numero_tr': tr.numero_tr,
            'titulo': tr.titulo,
            'status': tr.status
        } for tr in termos]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        novo_tr = TermoReferencia(
            numero_tr=f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            titulo=data.get('titulo'),
            descricao=data.get('descricao'),
            requisitante_id=int(get_jwt_identity())
        )
        db.session.add(novo_tr)
        db.session.commit()
        return jsonify({'id': novo_tr.id}), 201

@app.route('/api/processos', methods=['GET', 'POST'])
@jwt_required()
def processos():
    if request.method == 'GET':
        processos = Processo.query.all()
        return jsonify([{
            'id': p.id,
            'numero_processo': p.numero_processo,
            'status': p.status
        } for p in processos]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        novo_processo = Processo(
            numero_processo=f"PROC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            tr_id=data.get('tr_id'),
            comprador_id=int(get_jwt_identity()),
            modalidade=data.get('modalidade', 'Pregão Eletrônico')
        )
        db.session.add(novo_processo)
        db.session.commit()
        return jsonify({'id': novo_processo.id}), 201

@app.route('/api/propostas', methods=['GET', 'POST'])
@jwt_required()
def propostas():
    if request.method == 'GET':
        propostas = Proposta.query.all()
        return jsonify([{
            'id': p.id,
            'processo_id': p.processo_id,
            'valor': p.valor,
            'status': p.status
        } for p in propostas]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        nova_proposta = Proposta(
            processo_id=data.get('processo_id'),
            fornecedor_id=int(get_jwt_identity()),
            valor=data.get('valor'),
            prazo_entrega=data.get('prazo_entrega')
        )
        db.session.add(nova_proposta)
        db.session.commit()
        return jsonify({'id': nova_proposta.id}), 201

# Servir arquivos estáticos
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

# Criar admin padrão
def criar_admin():
    with app.app_context():
        if not Usuario.query.filter_by(email='admin@sistema.com').first():
            admin = Usuario(
                email='admin@sistema.com',
                senha_hash=generate_password_hash('Admin@2025!'),
                nome='Administrador',
                perfil='ADMIN'
            )
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin criado: admin@sistema.com / Admin@2025!")

# Inicialização
if __name__ == '__main__':
    criar_admin()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    criar_admin()
