# backend_seguro.py - Sistema com Sessão Firebase Apenas
import os
import json
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "*"}})

# Variável global para database
db = None

def initialize_firebase():
    """Inicializa Firebase com credenciais"""
    global db
    
    logger.info("🔍 Iniciando configuração do Firebase...")
    
    cred_dict = None
    
    # Tentativa 1: Arquivo credentials.json
    if os.path.exists('credentials.json'):
        logger.info("📁 Encontrado: credentials.json")
        try:
            with open('credentials.json', 'r') as f:
                cred_dict = json.load(f)
            logger.info("✅ Arquivo credentials.json carregado!")
        except Exception as e:
            logger.error(f"❌ Erro ao ler credentials.json: {e}")
    
    # Tentativa 2: Secret Files do Render
    elif os.path.exists('/etc/secrets/credentials.json'):
        logger.info("📁 Encontrado: /etc/secrets/credentials.json")
        try:
            with open('/etc/secrets/credentials.json', 'r') as f:
                cred_dict = json.load(f)
            logger.info("✅ Secret File carregado!")
        except Exception as e:
            logger.error(f"❌ Erro ao ler Secret File: {e}")
    
    # Tentativa 3: Variável de ambiente
    elif os.environ.get('FIREBASE_CREDENTIALS'):
        logger.info("📦 Encontrado: FIREBASE_CREDENTIALS em variável de ambiente")
        try:
            firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
            cred_dict = json.loads(firebase_creds)
            logger.info("✅ Variável de ambiente parseada!")
        except Exception as e:
            logger.error(f"❌ Erro ao parsear variável: {e}")
    
    if cred_dict:
        try:
            logger.info(f"🔧 Inicializando Firebase com project_id: {cred_dict.get('project_id')}")
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            
            logger.info("✅ Firebase inicializado com sucesso!")
            
            # Testar conexão
            test_collection = db.collection('_test').limit(1).get()
            logger.info("✅ Conexão com Firestore verificada!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Firebase: {e}")
            db = None
            return False
    else:
        logger.error("❌ Nenhuma credencial Firebase encontrada!")
        db = None
        return False

# Inicializar Firebase
initialize_firebase()

def require_auth(f):
    """Decorator para verificar autenticação via token Firebase"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not db:
            return jsonify({'erro': 'Serviço indisponível'}), 503
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'erro': 'Token não fornecido'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            decoded = auth.verify_id_token(token)
            request.user = decoded
            return f(*args, **kwargs)
        except auth.InvalidIdTokenError:
            logger.error("Token inválido ou expirado")
            return jsonify({'erro': 'Token inválido ou expirado'}), 401
        except Exception as e:
            logger.error(f"Erro na verificação do token: {e}")
            return jsonify({'erro': 'Erro na autenticação'}), 401
    
    return decorated_function

def require_admin(f):
    """Decorator para verificar se é admin"""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        email = request.user.get('email')
        if not email:
            return jsonify({'erro': 'Email não encontrado no token'}), 401
            
        users = db.collection('Usuario').where('email', '==', email).get()
        if not users or len(users) == 0:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
            
        user_data = users[0].to_dict()
        perfil = user_data.get('perfil', '').upper()
        
        if perfil != 'ADMIN':
            return jsonify({'erro': 'Acesso negado. Apenas administradores.'}), 403
            
        return f(*args, **kwargs)
    
    return decorated_function

# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    """Página principal - Portal único"""
    # Verificar se existe o arquivo portal-unico-inteligente.html
    if os.path.exists('static/portal-unico-inteligente.html'):
        return send_from_directory('static', 'portal-unico-inteligente.html')
    # Fallback para index.html
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Servir arquivos estáticos"""
    return send_from_directory('static', path)

# ==================== AUTENTICAÇÃO ====================

@app.route('/auth/verify', methods=['POST'])
def verify_token():
    """
    Verifica token Firebase e retorna dados do usuário.
    Cria usuário no Firestore se não existir.
    """
    if not db:
        return jsonify({'erro': 'Serviço indisponível'}), 503
    
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            # Tentar pegar do header Authorization
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                return jsonify({'erro': 'Token não fornecido'}), 400
        
        # Verificar token com Firebase
        decoded = auth.verify_id_token(token)
        uid = decoded['uid']
        email = decoded.get('email')
        
        if not email:
            return jsonify({'erro': 'Email não encontrado no token'}), 400
        
        logger.info(f"🔍 Verificando usuário: {email}")
        
        # Buscar usuário por email primeiro
        users_by_email = db.collection('Usuario').where('email', '==', email).get()
        
        if users_by_email and len(users_by_email) > 0:
            # Usuário encontrado
            user_doc = users_by_email[0]
            user_data = user_doc.to_dict()
            user_id = user_doc.id
            
            logger.info(f"✅ Usuário encontrado: {email}")
            logger.info(f"   Perfil: {user_data.get('perfil', 'não definido')}")
            
            # Se o ID do documento não corresponde ao UID, corrigir
            if user_id != uid:
                logger.info(f"🔄 Sincronizando documento do usuário")
                # Copiar dados para documento com UID correto
                db.collection('Usuario').document(uid).set(user_data)
                # Deletar documento antigo
                db.collection('Usuario').document(user_id).delete()
                
        else:
            # Usuário não existe - criar novo
            logger.info(f"📝 Criando novo usuário: {email}")
            
            # Determinar perfil padrão baseado no email
            perfil_padrao = detectar_perfil_por_email(email)
            
            user_data = {
                'email': email,
                'nome': decoded.get('name', email.split('@')[0]),
                'perfil': perfil_padrao,
                'ativo': True,
                'criadoEm': firestore.SERVER_TIMESTAMP,
                'primeiroAcesso': True
            }
            
            # Criar documento com UID
            db.collection('Usuario').document(uid).set(user_data)
            user_data['novo_usuario'] = True
            
            logger.info(f"✅ Novo usuário criado com perfil: {perfil_padrao}")
        
        # Preparar resposta
        response_data = {
            'valid': True,
            'uid': uid,
            'email': email,
            'nome': user_data.get('nome', email.split('@')[0]),
            'perfil': user_data.get('perfil'),
            'ativo': user_data.get('ativo', True),
            'novo_usuario': user_data.get('novo_usuario', False)
        }
        
        return jsonify(response_data), 200
        
    except auth.InvalidIdTokenError as e:
        logger.error(f"Token inválido: {e}")
        return jsonify({'erro': 'Token inválido ou expirado'}), 401
    except Exception as e:
        logger.error(f"Erro na verificação: {e}")
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500

@app.route('/api/user-profile', methods=['POST'])
def get_user_profile():
    """
    Retorna o perfil do usuário baseado no email.
    Usado para detecção automática de perfil.
    """
    if not db:
        return jsonify({'erro': 'Serviço indisponível'}), 503
        
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'erro': 'Email não fornecido'}), 400
        
        # Buscar usuário por email
        users = db.collection('Usuario').where('email', '==', email).get()
        
        if users and len(users) > 0:
            user_data = users[0].to_dict()
            return jsonify({
                'perfil': user_data.get('perfil'),
                'nome': user_data.get('nome'),
                'ativo': user_data.get('ativo', True)
            }), 200
        else:
            # Usuário não existe ainda - retornar perfil sugerido
            perfil_sugerido = detectar_perfil_por_email(email)
            return jsonify({
                'perfil': perfil_sugerido,
                'sugerido': True
            }), 200
            
    except Exception as e:
        logger.error(f"Erro ao buscar perfil: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

def detectar_perfil_por_email(email):
    """
    Detecta o perfil baseado no domínio do email.
    Retorna None se não conseguir detectar.
    """
    email_lower = email.lower()
    
    # Verificar padrões conhecidos
    if 'admin' in email_lower:
        return 'admin'
    elif 'fornecedor' in email_lower or 'empresa' in email_lower:
        return 'fornecedor'
    elif 'comprador' in email_lower or 'compras' in email_lower:
        return 'comprador'
    elif 'requisitante' in email_lower:
        return 'requisitante'
    
    # Verificar domínio
    domain = email.split('@')[1] if '@' in email else ''
    
    if 'gov' in domain:
        return 'requisitante'
    elif 'empresa' in domain or 'corp' in domain:
        return 'fornecedor'
    
    # Padrão: requisitante
    return 'requisitante'

# ==================== GESTÃO DE USUÁRIOS ====================

@app.route('/api/usuarios', methods=['GET'])
@require_admin
def listar_usuarios():
    """Lista todos os usuários (apenas admin)"""
    try:
        usuarios = []
        for doc in db.collection('Usuario').stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            # Remover dados sensíveis
            user_data.pop('criadoEm', None)
            user_data.pop('atualizadoEm', None)
            usuarios.append(user_data)
        
        return jsonify(usuarios), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

@app.route('/api/usuarios/<uid>/perfil', methods=['PUT'])
@require_admin
def atualizar_perfil(uid):
    """Atualiza o perfil de um usuário (apenas admin)"""
    try:
        data = request.get_json()
        novo_perfil = data.get('perfil')
        
        if not novo_perfil:
            return jsonify({'erro': 'Perfil não especificado'}), 400
        
        perfis_validos = ['admin', 'requisitante', 'comprador', 'fornecedor']
        if novo_perfil.lower() not in perfis_validos:
            return jsonify({'erro': f'Perfil inválido. Valores aceitos: {perfis_validos}'}), 400
        
        # Verificar se usuário existe
        user_doc = db.collection('Usuario').document(uid).get()
        if not user_doc.exists:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        # Atualizar perfil
        db.collection('Usuario').document(uid).update({
            'perfil': novo_perfil.lower(),
            'atualizadoEm': firestore.SERVER_TIMESTAMP,
            'atualizadoPor': request.user['uid']
        })
        
        logger.info(f"✅ Perfil do usuário {uid} atualizado para {novo_perfil}")
        
        return jsonify({
            'sucesso': True,
            'uid': uid,
            'novo_perfil': novo_perfil.lower()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

@app.route('/api/usuarios', methods=['POST'])
@require_admin
def criar_usuario():
    """Cria novo usuário (apenas admin)"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ['email', 'senha', 'nome', 'perfil']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'erro': f'Campo {field} é obrigatório'}), 400
        
        # Criar no Firebase Auth
        new_user = auth.create_user(
            email=data['email'],
            password=data['senha'],
            display_name=data['nome']
        )
        
        # Criar no Firestore
        db.collection('Usuario').document(new_user.uid).set({
            'email': data['email'],
            'nome': data['nome'],
            'perfil': data['perfil'].lower(),
            'ativo': True,
            'criadoEm': firestore.SERVER_TIMESTAMP,
            'criadoPor': request.user['uid']
        })
        
        logger.info(f"✅ Novo usuário criado: {data['email']}")
        
        return jsonify({
            'sucesso': True,
            'uid': new_user.uid,
            'email': data['email']
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        return jsonify({'erro': str(e)}), 500

# ==================== ROTAS DOS MÓDULOS ====================

@app.route('/requisitante')
@app.route('/requisitante/<path:path>')
def modulo_requisitante(path=''):
    """Módulo do Requisitante"""
    if path and os.path.exists(f'static/requisitante/{path}'):
        return send_from_directory('static/requisitante', path)
    if os.path.exists('static/dashboard-requisitante-funcional.html'):
        return send_from_directory('static', 'dashboard-requisitante-funcional.html')
    return send_from_directory('static/requisitante', 'index.html')

@app.route('/comprador')
@app.route('/comprador/<path:path>')
def modulo_comprador(path=''):
    """Módulo do Comprador"""
    if path and os.path.exists(f'static/comprador/{path}'):
        return send_from_directory('static/comprador', path)
    if os.path.exists('static/dashboard-comprador-funcional.html'):
        return send_from_directory('static', 'dashboard-comprador-funcional.html')
    return send_from_directory('static/comprador', 'index.html')

@app.route('/fornecedor')
@app.route('/fornecedor/<path:path>')
def modulo_fornecedor(path=''):
    """Módulo do Fornecedor"""
    if path and os.path.exists(f'static/fornecedor/{path}'):
        return send_from_directory('static/fornecedor', path)
    if os.path.exists('static/dashboard-fornecedor-funcional.html'):
        return send_from_directory('static', 'dashboard-fornecedor-funcional.html')
    return send_from_directory('static/fornecedor', 'index.html')

@app.route('/admin')
@app.route('/admin/<path:path>')
def modulo_admin(path=''):
    """Módulo do Admin"""
    if path and os.path.exists(f'static/admin/{path}'):
        return send_from_directory('static/admin', path)
    if os.path.exists('static/admin-usuarios.html'):
        return send_from_directory('static', 'admin-usuarios.html')
    return send_from_directory('static/admin', 'index.html')

# ==================== HEALTH CHECK ====================

@app.route('/api/status')
def api_status():
    """Status da API"""
    return jsonify({
        'api': 'online',
        'firebase': 'connected' if db else 'disconnected',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '3.0.0',
        'features': {
            'login_unificado': True,
            'sessao_segura': True,
            'sem_localstorage': True,
            'firebase_session_only': True
        }
    }), 200

@app.route('/health')
def health():
    """Health check simples"""
    return jsonify({'status': 'healthy'}), 200

# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info("="*60)
    logger.info(f"🚀 Iniciando servidor na porta {port}")
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info(f"🔥 Firebase: {'✅ Conectado' if db else '❌ Desconectado'}")
    logger.info(f"🔐 Sistema de Login: Unificado")
    logger.info(f"🛡️ Segurança: Sessão Firebase apenas (sem localStorage)")
    logger.info("="*60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
