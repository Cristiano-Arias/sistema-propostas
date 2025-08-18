# backend_simplificado.py - Versão otimizada e simplificada
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
    """Inicializa Firebase com credenciais - múltiplas tentativas"""
    global db
    
    print("🔍 DEBUG: Iniciando busca por credenciais Firebase...")
    
    cred_dict = None
    
    # Tentativa 1: Arquivo credentials.json
    if os.path.exists('credentials.json'):
        print("📁 Encontrado: credentials.json")
        try:
            with open('credentials.json', 'r') as f:
                cred_dict = json.load(f)
            print("✅ Arquivo credentials.json carregado!")
        except Exception as e:
            print(f"❌ Erro ao ler credentials.json: {e}")
    
    # Tentativa 2: Secret Files do Render
    elif os.path.exists('/etc/secrets/credentials.json'):
        print("📁 Encontrado: /etc/secrets/credentials.json")
        try:
            with open('/etc/secrets/credentials.json', 'r') as f:
                cred_dict = json.load(f)
            print("✅ Secret File carregado!")
        except Exception as e:
            print(f"❌ Erro ao ler Secret File: {e}")
    
    # Tentativa 3: Variável de ambiente FIREBASE_CREDENTIALS
    elif os.environ.get('FIREBASE_CREDENTIALS'):
        print("📦 Encontrado: FIREBASE_CREDENTIALS em variável de ambiente")
        try:
            firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
            print(f"   Tamanho: {len(firebase_creds)} caracteres")
            cred_dict = json.loads(firebase_creds)
            print("✅ Variável de ambiente parseada!")
        except Exception as e:
            print(f"❌ Erro ao parsear variável: {e}")
    
    # Tentativa 4: Variável GOOGLE_APPLICATION_CREDENTIALS
    elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        print("📦 Encontrado: GOOGLE_APPLICATION_CREDENTIALS")
        try:
            path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            with open(path, 'r') as f:
                cred_dict = json.load(f)
            print("✅ GOOGLE_APPLICATION_CREDENTIALS carregado!")
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    # Se encontrou credenciais, inicializar Firebase
    if cred_dict:
        try:
            print(f"🔧 Inicializando Firebase com project_id: {cred_dict.get('project_id')}")
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            
            logger.info("✅ Firebase inicializado com sucesso!")
            print("✅ Firebase inicializado com sucesso!")
            
            # Testar conexão
            test_collection = db.collection('_test').limit(1).get()
            print("✅ Conexão com Firestore verificada!")
            
            return True
            
        except Exception as e:
            error_msg = f"❌ Erro ao inicializar Firebase: {e}"
            logger.error(error_msg)
            print(error_msg)
            db = None
            return False
    else:
        print("❌ NENHUMA credencial encontrada!")
        print("   Tentativas falhadas:")
        print("   - credentials.json")
        print("   - /etc/secrets/credentials.json") 
        print("   - FIREBASE_CREDENTIALS (env)")
        print("   - GOOGLE_APPLICATION_CREDENTIALS (env)")
        
        logger.error("❌ Nenhuma credencial Firebase encontrada!")
        db = None
        return False

# Inicializar Firebase na inicialização
initialize_firebase()

def require_auth(f):
    """Decorator para verificar autenticação"""
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
        except Exception as e:
            logger.error(f"Token inválido: {e}")
            return jsonify({'erro': 'Token inválido'}), 401
    
    return decorated_function

def require_admin(f):
    """Decorator para verificar se é admin"""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        user_doc = db.collection('usuário').document(request.user['uid']).get()
        if not user_doc.exists or user_doc.to_dict().get('perfil') != 'ADMIN':
            return jsonify({'erro': 'Acesso negado'}), 403
        return f(*args, **kwargs)
    
    return decorated_function

# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.route('/auth/verify', methods=['POST'])
def verify_token():
    """Verifica token e retorna/cria dados do usuário"""
    if not db:
        return jsonify({'erro': 'Serviço indisponível'}), 503
    
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'erro': 'Token não fornecido'}), 400
        
        # Verificar token
        decoded = auth.verify_id_token(token)
        uid = decoded['uid']
        email = decoded.get('email')
        
        # Buscar ou criar usuário no Firestore
        user_doc = db.collection('usuário').document(uid).get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
        else:
            # Criar novo usuário
            user_data = {
                'email': email,
                'nome': decoded.get('name', email.split('@')[0] if email else 'Usuário'),
                'perfil': 'requisitante',
                'ativo': True,
                'criadoEm': firestore.SERVER_TIMESTAMP
            }
            db.collection('usuário').document(uid).set(user_data)
            user_data['novo_usuario'] = True
        
        return jsonify({
            'valid': True,
            'uid': uid,
            'email': email,
            'nome': user_data.get('nome'),
            'perfil': user_data.get('perfil'),
            'ativo': user_data.get('ativo', True),
            'novo_usuario': user_data.get('novo_usuario', False)
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na verificação: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

# ==================== ROTAS DE USUÁRIOS ====================

@app.route('/api/usuarios', methods=['GET'])
@require_admin
def listar_usuarios():
    """Lista todos os usuários (apenas admin)"""
    try:
        usuarios = []
        for doc in db.collection('usuário').stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            # Remover dados sensíveis
            user_data.pop('criadoEm', None)
            usuarios.append(user_data)
        
        return jsonify(usuarios), 200
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

@app.route('/api/usuarios', methods=['POST'])
@require_admin
def criar_usuario():
    """Cria novo usuário (apenas admin)"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ['email', 'senha', 'nome']
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
        db.collection('usuário').document(new_user.uid).set({
            'email': data['email'],
            'nome': data['nome'],
            'perfil': data.get('perfil', 'requisitante'),
            'ativo': True,
            'criadoEm': firestore.SERVER_TIMESTAMP,
            'criadoPor': request.user['uid']
        })
        
        return jsonify({
            'sucesso': True,
            'uid': new_user.uid,
            'email': data['email']
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

# ==================== ROTAS DE DADOS ====================

@app.route('/api/termos-referencia', methods=['GET', 'POST'])
@require_auth
def termos_referencia():
    """Gerencia Termos de Referência"""
    try:
        if request.method == 'GET':
            trs = []
            for doc in db.collection('termos_referencia').stream():
                tr_data = doc.to_dict()
                tr_data['id'] = doc.id
                trs.append(tr_data)
            return jsonify(trs), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            
            if not data.get('titulo'):
                return jsonify({'erro': 'Título é obrigatório'}), 400
            
            tr_ref = db.collection('termos_referencia').document()
            tr_data = {
                'numero_tr': f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'titulo': data['titulo'],
                'descricao': data.get('descricao', ''),
                'requisitante_uid': request.user['uid'],
                'requisitante_email': request.user.get('email'),
                'status': 'rascunho',
                'criadoEm': firestore.SERVER_TIMESTAMP
            }
            tr_ref.set(tr_data)
            
            return jsonify({
                'id': tr_ref.id,
                'numero_tr': tr_data['numero_tr']
            }), 201
            
    except Exception as e:
        logger.error(f"Erro em TRs: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

@app.route('/api/processos', methods=['GET', 'POST'])
@require_auth
def processos():
    """Gerencia Processos"""
    try:
        if request.method == 'GET':
            processos = []
            for doc in db.collection('processos').stream():
                proc_data = doc.to_dict()
                proc_data['id'] = doc.id
                processos.append(proc_data)
            return jsonify(processos), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            
            if not data.get('tr_id'):
                return jsonify({'erro': 'TR é obrigatório'}), 400
            
            proc_ref = db.collection('processos').document()
            proc_data = {
                'numero_processo': f"PROC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'tr_id': data['tr_id'],
                'comprador_uid': request.user['uid'],
                'comprador_email': request.user.get('email'),
                'modalidade': data.get('modalidade', 'Pregão Eletrônico'),
                'status': 'aberto',
                'criadoEm': firestore.SERVER_TIMESTAMP
            }
            proc_ref.set(proc_data)
            
            return jsonify({
                'id': proc_ref.id,
                'numero_processo': proc_data['numero_processo']
            }), 201
            
    except Exception as e:
        logger.error(f"Erro em processos: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

@app.route('/api/propostas', methods=['GET', 'POST'])
@require_auth
def propostas():
    """Gerencia Propostas"""
    try:
        if request.method == 'GET':
            propostas = []
            for doc in db.collection('propostas').stream():
                prop_data = doc.to_dict()
                prop_data['id'] = doc.id
                propostas.append(prop_data)
            return jsonify(propostas), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            
            required_fields = ['processo_id', 'valor']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'erro': f'Campo {field} é obrigatório'}), 400
            
            prop_ref = db.collection('propostas').document()
            prop_data = {
                'processo_id': data['processo_id'],
                'fornecedor_uid': request.user['uid'],
                'fornecedor_email': request.user.get('email'),
                'valor': float(data['valor']),
                'prazo_entrega': data.get('prazo_entrega'),
                'observacoes': data.get('observacoes', ''),
                'status': 'enviada',
                'criadoEm': firestore.SERVER_TIMESTAMP
            }
            prop_ref.set(prop_data)
            
            return jsonify({
                'id': prop_ref.id,
                'status': 'enviada'
            }), 201
            
    except Exception as e:
        logger.error(f"Erro em propostas: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

# ==================== ROTAS ESTÁTICAS ====================

@app.route('/')
def index():
    """Página inicial"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Servir arquivos estáticos"""
    try:
        if path.startswith('static/'):
            return send_from_directory('.', path)
        return send_from_directory('static', path)
    except:
        return send_from_directory('static', 'index.html')

# ==================== HEALTH CHECK ====================

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'firebase': 'connected' if db else 'disconnected'
    }), 200

@app.route('/api/status')
def api_status():
    """Status da API"""
    return jsonify({
        'api': 'online',
        'firebase': 'connected' if db else 'disconnected',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"🚀 Iniciando servidor na porta {port}")
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info(f"🔥 Firebase: {'✅ Conectado' if db else '❌ Desconectado'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
