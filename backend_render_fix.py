# backend_render_fix.py - Versão Final com Firebase
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError, OperationalError
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

# Inicializar Firebase (opcional)
firestore_db = None
firebase_auth = None
firebase_initialized = False

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth as fb_auth
    
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_creds:
        try:
            # Verificar se já foi inicializado
            firebase_admin.get_app()
            firebase_initialized = True
            logger.info("Firebase já estava inicializado")
        except ValueError:
            # Não foi inicializado, inicializar agora
            cred_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            firebase_initialized = True
            logger.info("✅ Firebase inicializado com sucesso!")
        
        firestore_db = firestore.client()
        firebase_auth = fb_auth
    else:
        logger.info("⚠️ FIREBASE_CREDENTIALS não configurado - usando apenas banco local")
except Exception as e:
    logger.warning(f"Firebase não disponível: {e}")

# Modelos do banco de dados
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    empresa = db.Column(db.String(200), nullable=True)
    cnpj = db.Column(db.String(20), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)
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

# Função para limpar e recriar o banco
def reset_database():
    """Limpa e recria as tabelas do banco"""
    with app.app_context():
        try:
            # Dropar todas as tabelas
            db.drop_all()
            logger.info("Tabelas antigas removidas")
            
            # Recriar tabelas
            db.create_all()
            logger.info("✅ Tabelas recriadas com sucesso")
            
            # Criar admin padrão
            criar_admin_padrao()
            
        except Exception as e:
            logger.error(f"Erro ao resetar banco: {e}")

# Função para criar admin
def criar_admin_padrao():
    """Cria o usuário admin padrão"""
    try:
        # Verificar se já existe usando SQL direto para evitar problemas de schema
        result = db.session.execute(
            text("SELECT COUNT(*) FROM usuarios WHERE email = :email"),
            {"email": "admin@sistema.com"}
        )
        count = result.scalar()
        
        if count > 0:
            logger.info("✅ Admin já existe no banco")
            return
        
        # Criar admin
        admin = Usuario(
            nome='Administrador do Sistema',
            email='admin@sistema.com',
            senha_hash=generate_password_hash('Admin@2025!'),
            perfil='ADMIN',
            ativo=True
        )
        
        # Se Firebase está configurado, buscar UID
        if firebase_initialized and firestore_db:
            try:
                # Buscar usuário no Firebase Auth
                firebase_user = firebase_auth.get_user_by_email('admin@sistema.com')
                admin.firebase_uid = firebase_user.uid
                logger.info(f"Admin sincronizado com Firebase: {firebase_user.uid}")
            except:
                logger.info("Admin será criado apenas localmente")
        
        db.session.add(admin)
        db.session.commit()
        logger.info("✅ Admin criado com sucesso: admin@sistema.com / Admin@2025!")
        
    except IntegrityError as e:
        db.session.rollback()
        logger.info("Admin já existe (integrity check)")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao criar admin: {e}")

# Inicializar banco - USAR RESET PARA LIMPAR PROBLEMAS
def init_database():
    """Inicializa o banco de dados"""
    with app.app_context():
        try:
            # Tentar criar tabelas
            db.create_all()
            logger.info("✅ Banco de dados verificado")
            
            # Criar admin
            criar_admin_padrao()
            
        except Exception as e:
            logger.error(f"Erro no banco, tentando reset: {e}")
            # Se houver erro, fazer reset completo
            try:
                reset_database()
            except:
                logger.error("Não foi possível resetar o banco")

# Inicializar
init_database()

# Rotas de autenticação
@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        senha = data.get('senha', '')
        
        if not email or not senha:
            return jsonify({'erro': 'Email e senha são obrigatórios'}), 400
        
        # Buscar usuário
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            # Se Firebase está configurado, tentar buscar lá
            if firebase_initialized and firestore_db:
                try:
                    firebase_user = firebase_auth.get_user_by_email(email)
                    user_doc = firestore_db.collection('usuarios').document(firebase_user.uid).get()
                    
                    if user_doc.exists:
                        user_data = user_doc.to_dict()
                        # Criar usuário local
                        usuario = Usuario(
                            nome=user_data.get('nome', 'Usuário'),
                            email=email,
                            senha_hash=generate_password_hash(senha),
                            perfil=user_data.get('perfil', 'requisitante'),
                            firebase_uid=firebase_user.uid,
                            ativo=True
                        )
                        db.session.add(usuario)
                        db.session.commit()
                except:
                    pass
            
            if not usuario:
                return jsonify({'erro': 'Usuário não encontrado'}), 401
        
        # Verificar senha
        if not check_password_hash(usuario.senha_hash, senha):
            return jsonify({'erro': 'Senha incorreta'}), 401
        
        # Criar token
        access_token = create_access_token(
            identity=str(usuario.id),
            additional_claims={
                'perfil': usuario.perfil,
                'email': usuario.email,
                'nome': usuario.nome
            }
        )
        
        return jsonify({
            'access_token': access_token,
            'perfil': usuario.perfil,
            'nome': usuario.nome,
            'email': usuario.email
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({'erro': 'Erro interno no servidor'}), 500

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        if Usuario.query.filter_by(email=data.get('email')).first():
            return jsonify({'erro': 'Email já cadastrado'}), 409
        
        novo_usuario = Usuario(
            nome=data.get('nome'),
            email=data.get('email'),
            senha_hash=generate_password_hash(data.get('senha')),
            perfil=data.get('perfil', 'requisitante'),
            ativo=True
        )
        
        # Criar no Firebase se configurado
        if firebase_initialized and firestore_db:
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
                    'criadoEm': firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                logger.warning(f"Usuário criado localmente: {e}")
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({'mensagem': 'Usuário criado', 'id': novo_usuario.id}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro no registro: {e}")
        return jsonify({'erro': 'Erro ao criar usuário'}), 500

# Rotas admin
@app.route('/admin/usuarios', methods=['GET', 'POST'])
@jwt_required()
def gerenciar_usuarios():
    try:
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
                nome=data.get('nome'),
                email=data.get('email'),
                senha_hash=generate_password_hash(data.get('senha')),
                perfil=data.get('perfil', 'requisitante'),
                ativo=True
            )
            
            db.session.add(novo_usuario)
            db.session.commit()
            
            return jsonify({'id': novo_usuario.id}), 201
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

@app.route('/admin/usuarios/<int:user_id>/reset', methods=['POST'])
@jwt_required()
def reset_senha(user_id):
    try:
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
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

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
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'firebase': 'connected' if firebase_initialized else 'not_configured'
    }), 200

# Rota para reset manual (REMOVER EM PRODUÇÃO)
@app.route('/admin/reset-database', methods=['POST'])
def reset_db():
    try:
        reset_database()
        return jsonify({'mensagem': 'Banco resetado com sucesso'}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
