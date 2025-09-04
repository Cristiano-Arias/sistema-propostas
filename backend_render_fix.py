# backend_render_fix.py - Versão otimizada para produção no Render
import os
import json
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth
import requests

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "*"}})

# Inicializar Firebase
db = None
try:
    if not firebase_admin._apps:
        cred_json = os.getenv("FIREBASE_CREDENTIALS")
        if cred_json:
            try:
                cred = credentials.Certificate(json.loads(cred_json))
            except Exception:
                cred = credentials.Certificate(cred_json)
        else:
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("✅ Firebase conectado com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao conectar Firebase: {e}")
    db = None

# Configurações Azure OpenAI
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-35-turbo')
AZURE_KEY = os.getenv('AZURE_OPENAI_KEY')
AZURE_API_VER = os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')

# Decoradores de autenticação
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Token não fornecido'}), 401
            
            token = auth_header.split(' ')[1]
            decoded_token = auth.verify_id_token(token)
            request.user = decoded_token
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return jsonify({'error': 'Token inválido'}), 401
    return decorated_function

def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'user'):
                return jsonify({'error': 'Usuário não autenticado'}), 401
            
            user_email = request.user.get('email')
            if not user_email:
                return jsonify({'error': 'Email não encontrado'}), 401
            
            # Verificar perfil do usuário no Firestore
            try:
                user_doc = db.collection('usuarios').where('email', '==', user_email).limit(1).get()
                if not user_doc:
                    return jsonify({'error': 'Usuário não encontrado'}), 403
                
                user_data = user_doc[0].to_dict()
                user_role = user_data.get('perfil', '').upper()
                
                if user_role not in [role.upper() for role in roles]:
                    return jsonify({'error': 'Acesso negado'}), 403
                    
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Erro ao verificar perfil: {e}")
                return jsonify({'error': 'Erro interno'}), 500
        return decorated_function
    return decorator

# Rotas de autenticação
@app.route('/auth/verify', methods=['POST'])
def verify_token():
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token não fornecido'}), 400
        
        decoded_token = auth.verify_id_token(token)
        user_email = decoded_token.get('email')
        
        if not user_email:
            return jsonify({'error': 'Email não encontrado no token'}), 400
        
        # Buscar usuário no Firestore
        if db:
            user_docs = db.collection('usuarios').where('email', '==', user_email).limit(1).get()
            if user_docs:
                user_data = user_docs[0].to_dict()
                return jsonify({
                    'valid': True,
                    'user': {
                        'email': user_email,
                        'nome': user_data.get('nome', ''),
                        'perfil': user_data.get('perfil', ''),
                        'ativo': user_data.get('ativo', True)
                    }
                })
        
        return jsonify({'error': 'Usuário não encontrado'}), 404
        
    except Exception as e:
        logger.error(f"Erro na verificação do token: {e}")
        return jsonify({'error': 'Token inválido'}), 401

# Rotas da API
@app.route('/api/user-profile', methods=['POST'])
@require_auth
def get_user_profile():
    try:
        user_email = request.user.get('email')
        
        if db:
            user_docs = db.collection('usuarios').where('email', '==', user_email).limit(1).get()
            if user_docs:
                user_data = user_docs[0].to_dict()
                return jsonify({
                    'success': True,
                    'user': {
                        'email': user_email,
                        'nome': user_data.get('nome', ''),
                        'perfil': user_data.get('perfil', ''),
                        'ativo': user_data.get('ativo', True)
                    }
                })
        
        return jsonify({'error': 'Usuário não encontrado'}), 404
        
    except Exception as e:
        logger.error(f"Erro ao buscar perfil: {e}")
        return jsonify({'error': 'Erro interno'}), 500

@app.route('/api/fornecedores', methods=['GET'])
def listar_fornecedores():
    return jsonify([
        {
            'id': '1',
            'nome': 'Wesley Lopes',
            'email': 'wesley.lopes@forteoliveira.com',
            'telefone': '(11) 99999-9999',
            'especialidade': 'Engenharia Civil'
        },
        {
            'id': '2', 
            'nome': 'ADM GGR Engenharia',
            'email': 'admggrengenharia@gmail.com',
            'telefone': '(11) 88888-8888',
            'especialidade': 'Engenharia Estrutural'
        }
    ])

@app.route('/api/termos-referencia', methods=['GET', 'POST'])
@require_auth
def termos_referencia():
    if request.method == 'GET':
        return jsonify([])
    else:
        data = request.get_json()
        return jsonify({'success': True, 'id': 'tr_001'})

@app.route('/api/processos', methods=['GET', 'POST'])
@require_auth
def processos():
    if request.method == 'GET':
        return jsonify([])
    else:
        data = request.get_json()
        return jsonify({'success': True, 'id': 'proc_001'})

@app.route('/api/propostas', methods=['GET', 'POST'])
@require_auth
def propostas():
    if request.method == 'GET':
        return jsonify([])
    else:
        data = request.get_json()
        return jsonify({'success': True, 'id': 'prop_001'})

@app.route('/api/ia/analise-tecnica', methods=['POST'])
@require_auth
@require_role('COMPRADOR', 'ADMIN')
def ia_analise_tecnica():
    try:
        data = request.get_json()
        propostas = data.get('propostas', [])
        
        if not AZURE_ENDPOINT or not AZURE_KEY:
            return jsonify({'error': 'Azure OpenAI não configurado'}), 500
        
        # Preparar dados para análise
        prompt = f"Analise as seguintes propostas técnicas: {json.dumps(propostas, indent=2)}"
        
        # Chamar Azure OpenAI
        headers = {
            'Content-Type': 'application/json',
            'api-key': AZURE_KEY
        }
        
        payload = {
            'messages': [
                {'role': 'system', 'content': 'Você é um especialista em análise de propostas técnicas.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1000,
            'temperature': 0.7
        }
        
        url = f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version={AZURE_API_VER}"
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            analise = result['choices'][0]['message']['content']
            return jsonify({'success': True, 'analise': analise})
        else:
            logger.error(f"Erro Azure OpenAI: {response.status_code} - {response.text}")
            return jsonify({'error': 'Erro na análise IA'}), 500
            
    except Exception as e:
        logger.error(f"Erro na análise técnica: {e}")
        return jsonify({'error': 'Erro interno'}), 500

# Rotas estáticas
@app.route('/')
def index():
    return send_from_directory('static', 'dashboard-fornecedor-funcional.html')

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory('static', path)
    except:
        return send_from_directory('static', 'dashboard-fornecedor-funcional.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'firebase': 'connected' if db else 'disconnected',
        'azure_openai': 'configured' if AZURE_ENDPOINT and AZURE_KEY else 'not_configured'
    })

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'firebase': bool(db),
        'azure_openai': bool(AZURE_ENDPOINT and AZURE_KEY)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"🚀 Iniciando servidor na porta {port}")
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info(f"🔥 Firebase: {'✅ Conectado' if db else '❌ Desconectado'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
