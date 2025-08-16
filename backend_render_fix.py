# backend_render_fix.py - Backend completo para Render
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth

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

# Se DATABASE_URL começar com postgres://, corrigir para postgresql://
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Inicializar extensões
CORS(app, resources={r"/*": {"origins": "*"}})
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Inicializar Firebase Admin (para validação server-side)
try:
    # Para Render, use variável de ambiente com credenciais
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_creds:
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
    else:
        # Para desenvolvimento local
        cred = credentials.Certificate('firebase-credentials.json')
    
    firebase_admin.initialize_app(cred)
    firestore_db = firestore.client()
    logger.info("Firebase Admin inicializado com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar Firebase: {e}")
    firestore_db = None

# Modelos do banco de dados
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    perfil = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TermoReferencia(db.Model):
    __tablename__ = 'termos_referencia'
    id = db.Column(db.Integer, primary_key=True)
    numero_tr = db.Column(db.String(50), unique=True, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    requisitante_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    status = db.Column(db.String(50), default='rascunho')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_aprovacao = db.Column(db.DateTime, nullable=True)
    aprovador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    valor_estimado = db.Column(db.Float, nullable=True)
    prazo_entrega = db.Column(db.Integer, nullable=True)

class Processo(db.Model):
    __tablename__ = 'processos'
    id = db.Column(db.Integer, primary_key=True)
    numero_processo = db.Column(db.String(50), unique=True, nullable=False)
    tr_id = db.Column(db.Integer, db.ForeignKey('termos_referencia.id'))
    comprador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    status = db.Column(db.String(50), default='aberto')
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    data_encerramento = db.Column(db.DateTime, nullable=True)
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
    observacoes = db.Column(db.Text, nullable=True)

# Criar tabelas
with app.app_context():
    db.create_all()
    logger.info("Tabelas do banco de dados criadas")

# Rotas de autenticação
@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({'erro': 'Email e senha são obrigatórios'}), 400
        
        # Verificar no banco local primeiro
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and check_password_hash(usuario.senha_hash, senha):
            # Sincronizar com Firebase se necessário
            if firestore_db and not usuario.firebase_uid:
                try:
                    firebase_user = firebase_auth.create_user(
                        email=email,
                        password=senha,
                        display_name=usuario.nome
                    )
                    usuario.firebase_uid = firebase_user.uid
                    
                    # Criar documento no Firestore
                    firestore_db.collection('usuarios').document(firebase_user.uid).set({
                        'email': email,
                        'nome': usuario.nome,
                        'perfil': usuario.perfil,
                        'ativo': usuario.ativo,
                        'criadoEm': datetime.utcnow().isoformat()
                    })
                    
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Erro ao sincronizar com Firebase: {e}")
            
            # Criar token JWT
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
        return jsonify({'erro': 'Erro interno no servidor'}), 500

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        nome = data.get('nome')
        perfil = data.get('perfil', 'requisitante')
        
        # Validações
        if not all([email, senha, nome]):
            return jsonify({'erro': 'Todos os campos são obrigatórios'}), 400
        
        if Usuario.query.filter_by(email=email).first():
            return jsonify({'erro': 'Email já cadastrado'}), 409
        
        # Criar usuário no banco local
        novo_usuario = Usuario(
            email=email,
            senha_hash=generate_password_hash(senha),
            nome=nome,
            perfil=perfil
        )
        
        # Criar usuário no Firebase
        if firestore_db:
            try:
                firebase_user = firebase_auth.create_user(
                    email=email,
                    password=senha,
                    display_name=nome
                )
                novo_usuario.firebase_uid = firebase_user.uid
                
                # Criar documento no Firestore
                firestore_db.collection('usuarios').document(firebase_user.uid).set({
                    'email': email,
                    'nome': nome,
                    'perfil': perfil,
                    'ativo': True,
                    'criadoEm': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Erro ao criar usuário no Firebase: {e}")
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Usuário criado com sucesso',
            'id': novo_usuario.id
        }), 201
        
    except Exception as e:
        logger.error(f"Erro no registro: {e}")
        return jsonify({'erro': 'Erro ao criar usuário'}), 500

# Rotas protegidas para Admin
@app.route('/admin/usuarios', methods=['GET', 'POST'])
@jwt_required()
def gerenciar_usuarios():
    current_user = get_jwt_identity()
    usuario = Usuario.query.get(current_user)
    
    if not usuario or usuario.perfil != 'ADMIN':
        return jsonify({'erro': 'Acesso negado'}), 403
    
    if request.method == 'GET':
        usuarios = Usuario.query.all()
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
        
        novo_usuario = Usuario(
            email=data.get('email'),
            senha_hash=generate_password_hash(data.get('senha')),
            nome=data.get('nome'),
            perfil=data.get('perfil')
        )
        
        # Sincronizar com Firebase
        if firestore_db:
            try:
                firebase_user = firebase_auth.create_user(
                    email=data.get('email'),
                    password=data.get('senha'),
                    display_name=data.get('nome')
                )
                novo_usuario.firebase_uid = firebase_user.uid
                
                firestore_db.collection('usuarios').document(firebase_user.uid).set({
                    'email': data.get('email'),
                    'nome': data.get('nome'),
                    'perfil': data.get('perfil'),
                    'ativo': True,
                    'criadoEm': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Erro Firebase: {e}")
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({'id': novo_usuario.id, 'mensagem': 'Usuário criado'}), 201

# Rotas de API para Termos de Referência
@app.route('/api/termos-referencia', methods=['GET', 'POST'])
@jwt_required()
def termos_referencia():
    if request.method == 'GET':
        termos = TermoReferencia.query.all()
        return jsonify([{
            'id': tr.id,
            'numero_tr': tr.numero_tr,
            'titulo': tr.titulo,
            'descricao': tr.descricao,
            'status': tr.status,
            'data_criacao': tr.data_criacao.isoformat() if tr.data_criacao else None
        } for tr in termos]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        current_user = get_jwt_identity()
        
        novo_tr = TermoReferencia(
            numero_tr=f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            titulo=data.get('titulo'),
            descricao=data.get('descricao'),
            requisitante_id=int(current_user),
            valor_estimado=data.get('valor_estimado'),
            prazo_entrega=data.get('prazo_entrega')
        )
        
        db.session.add(novo_tr)
        db.session.commit()
        
        return jsonify({
            'id': novo_tr.id,
            'numero_tr': novo_tr.numero_tr
        }), 201

# Rotas de API para Processos
@app.route('/api/processos', methods=['GET', 'POST'])
@jwt_required()
def processos():
    if request.method == 'GET':
        processos = Processo.query.all()
        return jsonify([{
            'id': p.id,
            'numero_processo': p.numero_processo,
            'status': p.status,
            'modalidade': p.modalidade,
            'data_abertura': p.data_abertura.isoformat() if p.data_abertura else None
        } for p in processos]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        current_user = get_jwt_identity()
        
        novo_processo = Processo(
            numero_processo=f"PROC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            tr_id=data.get('tr_id'),
            comprador_id=int(current_user),
            modalidade=data.get('modalidade', 'Pregão Eletrônico')
        )
        
        db.session.add(novo_processo)
        db.session.commit()
        
        return jsonify({
            'id': novo_processo.id,
            'numero_processo': novo_processo.numero_processo
        }), 201

# Rotas de API para Propostas
@app.route('/api/propostas', methods=['GET', 'POST'])
@jwt_required()
def propostas():
    if request.method == 'GET':
        propostas = Proposta.query.all()
        return jsonify([{
            'id': p.id,
            'processo_id': p.processo_id,
            'valor': p.valor,
            'prazo_entrega': p.prazo_entrega,
            'status': p.status,
            'data_envio': p.data_envio.isoformat() if p.data_envio else None
        } for p in propostas]), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        current_user = get_jwt_identity()
        
        nova_proposta = Proposta(
            processo_id=data.get('processo_id'),
            fornecedor_id=int(current_user),
            valor=data.get('valor'),
            prazo_entrega=data.get('prazo_entrega'),
            observacoes=data.get('observacoes')
        )
        
        db.session.add(nova_proposta)
        db.session.commit()
        
        return jsonify({
            'id': nova_proposta.id,
            'status': nova_proposta.status
        }), 201

# Servir arquivos estáticos
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('static/'):
        return send_from_directory('.', path)
    return send_from_directory('static', path)

# Health check
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'firebase': 'connected' if firestore_db else 'disconnected'
    }), 200

# Criar usuário admin padrão se não existir
def criar_admin_padrao():
    with app.app_context():
        admin = Usuario.query.filter_by(email='admin@sistema.com').first()
        if not admin:
            admin = Usuario(
                email='admin@sistema.com',
                senha_hash=generate_password_hash('Admin@2025!'),
                nome='Administrador do Sistema',
                perfil='ADMIN'
            )
            db.session.add(admin)
            db.session.commit()
            logger.info("Usuário admin padrão criado")

# Inicialização
if __name__ == '__main__':
    criar_admin_padrao()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
