# backend_render_fix.py - Backend corrigido para Render
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

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

# Corrigir URL do PostgreSQL se necessário
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Inicializar extensões
CORS(app, resources={r"/*": {"origins": "*"}})
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Firebase é opcional - não falhar se não estiver configurado
firestore_db = None
firebase_auth = None

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth as fb_auth
    
    # Tentar carregar credenciais do Firebase
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_creds:
        try:
            cred_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            firestore_db = firestore.client()
            firebase_auth = fb_auth
            logger.info("Firebase Admin inicializado com sucesso")
        except Exception as e:
            logger.warning(f"Firebase configurado mas não inicializado: {e}")
    else:
        logger.info("Firebase não configurado - usando apenas banco local")
except ImportError:
    logger.info("Firebase Admin não instalado - usando apenas banco local")
except Exception as e:
    logger.warning(f"Erro ao configurar Firebase: {e}")

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
    try:
        db.create_all()
        logger.info("Tabelas do banco de dados criadas/verificadas")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")

# Rotas de autenticação
@app.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({'erro': 'Email e senha são obrigatórios'}), 400
        
        # Verificar no banco local
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and check_password_hash(usuario.senha_hash, senha):
            # Sincronizar com Firebase se disponível e necessário
            if firestore_db and firebase_auth and not usuario.firebase_uid:
                try:
                    # Tentar criar usuário no Firebase
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
                    logger.info(f"Usuário {email} sincronizado com Firebase")
                except Exception as e:
                    logger.warning(f"Não foi possível sincronizar com Firebase: {e}")
            
            # Criar token JWT
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
        
        # Tentar criar no Firebase se disponível
        if firestore_db and firebase_auth:
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
                logger.info(f"Usuário {email} criado no Firebase")
            except Exception as e:
                logger.warning(f"Usuário criado localmente mas não no Firebase: {e}")
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Usuário criado com sucesso',
            'id': novo_usuario.id
        }), 201
        
    except Exception as e:
        logger.error(f"Erro no registro: {e}")
        db.session.rollback()
        return jsonify({'erro': 'Erro ao criar usuário'}), 500

# Rotas protegidas para Admin
@app.route('/admin/usuarios', methods=['GET', 'POST'])
@jwt_required()
def gerenciar_usuarios():
    try:
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(int(current_user_id))
        
        if not usuario or usuario.perfil != 'ADMIN':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        if request.method == 'GET':
            # Buscar com filtro opcional
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
            
            # Validar dados
            if not all([data.get('email'), data.get('senha'), data.get('nome')]):
                return jsonify({'erro': 'Campos obrigatórios faltando'}), 400
            
            # Verificar se email já existe
            if Usuario.query.filter_by(email=data.get('email')).first():
                return jsonify({'erro': 'Email já cadastrado'}), 409
            
            novo_usuario = Usuario(
                email=data.get('email'),
                senha_hash=generate_password_hash(data.get('senha')),
                nome=data.get('nome'),
                perfil=data.get('perfil', 'requisitante')
            )
            
            # Sincronizar com Firebase se disponível
            if firestore_db and firebase_auth:
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
                    logger.warning(f"Firebase sync failed: {e}")
            
            db.session.add(novo_usuario)
            db.session.commit()
            
            return jsonify({
                'id': novo_usuario.id,
                'mensagem': 'Usuário criado com sucesso'
            }), 201
            
    except Exception as e:
        logger.error(f"Erro em gerenciar_usuarios: {e}")
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

@app.route('/admin/usuarios/<int:user_id>/reset', methods=['POST'])
@jwt_required()
def reset_senha(user_id):
    try:
        current_user_id = get_jwt_identity()
        admin = Usuario.query.get(int(current_user_id))
        
        if not admin or admin.perfil != 'ADMIN':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        data = request.get_json()
        nova_senha = data.get('nova_senha')
        
        if not nova_senha:
            return jsonify({'erro': 'Nova senha é obrigatória'}), 400
        
        usuario = Usuario.query.get(user_id)
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        usuario.senha_hash = generate_password_hash(nova_senha)
        usuario.atualizado_em = datetime.utcnow()
        
        # Atualizar no Firebase se disponível
        if firestore_db and firebase_auth and usuario.firebase_uid:
            try:
                firebase_auth.update_user(
                    usuario.firebase_uid,
                    password=nova_senha
                )
            except Exception as e:
                logger.warning(f"Não foi possível atualizar senha no Firebase: {e}")
        
        db.session.commit()
        
        return jsonify({'mensagem': 'Senha atualizada com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao resetar senha: {e}")
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

# Rotas de API para Termos de Referência
@app.route('/api/termos-referencia', methods=['GET', 'POST'])
@jwt_required()
def termos_referencia():
    try:
        if request.method == 'GET':
            termos = TermoReferencia.query.all()
            return jsonify([{
                'id': tr.id,
                'numero_tr': tr.numero_tr,
                'titulo': tr.titulo,
                'descricao': tr.descricao,
                'status': tr.status,
                'data_criacao': tr.data_criacao.isoformat() if tr.data_criacao else None,
                'valor_estimado': tr.valor_estimado,
                'prazo_entrega': tr.prazo_entrega
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
                'numero_tr': novo_tr.numero_tr,
                'mensagem': 'Termo de Referência criado com sucesso'
            }), 201
            
    except Exception as e:
        logger.error(f"Erro em termos_referencia: {e}")
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

# Rotas de API para Processos
@app.route('/api/processos', methods=['GET', 'POST'])
@jwt_required()
def processos():
    try:
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
                'numero_processo': novo_processo.numero_processo,
                'mensagem': 'Processo criado com sucesso'
            }), 201
            
    except Exception as e:
        logger.error(f"Erro em processos: {e}")
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

# Rotas de API para Propostas
@app.route('/api/propostas', methods=['GET', 'POST'])
@jwt_required()
def propostas():
    try:
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
                'status': nova_proposta.status,
                'mensagem': 'Proposta enviada com sucesso'
            }), 201
            
    except Exception as e:
        logger.error(f"Erro em propostas: {e}")
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

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
        'firebase': 'connected' if firestore_db else 'not_configured',
        'database': 'connected'
    }), 200

# Criar usuário admin padrão se não existir
def criar_admin_padrao():
    try:
        with app.app_context():
            admin = Usuario.query.filter_by(email='admin@sistema.com').first()
            if not admin:
                admin = Usuario(
                    email='admin@sistema.com',
                    senha_hash=generate_password_hash('Admin@2025!'),
                    nome='Administrador do Sistema',
                    perfil='ADMIN',
                    ativo=True
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("Usuário admin padrão criado: admin@sistema.com / Admin@2025!")
                
                # Tentar criar no Firebase também
                if firestore_db and firebase_auth:
                    try:
                        firebase_user = firebase_auth.create_user(
                            email='admin@sistema.com',
                            password='Admin@2025!',
                            display_name='Administrador do Sistema'
                        )
                        admin.firebase_uid = firebase_user.uid
                        
                        firestore_db.collection('usuarios').document(firebase_user.uid).set({
                            'email': 'admin@sistema.com',
                            'nome': 'Administrador do Sistema',
                            'perfil': 'ADMIN',
                            'ativo': True,
                            'criadoEm': datetime.utcnow().isoformat()
                        })
                        db.session.commit()
                        logger.info("Admin sincronizado com Firebase")
                    except Exception as e:
                        logger.warning(f"Admin criado localmente mas não no Firebase: {e}")
            else:
                logger.info("Usuário admin já existe")
    except Exception as e:
        logger.error(f"Erro ao criar admin padrão: {e}")

# Inicialização
if __name__ == '__main__':
    criar_admin_padrao()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    # Quando executado pelo Gunicorn
    criar_admin_padrao()
