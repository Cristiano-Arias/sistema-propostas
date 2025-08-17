# backend_firebase_only.py - Sistema usando apenas Firebase
import os
import json
import logging
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__, static_folder='static', static_url_path='/static')

# CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Inicializar Firebase Admin
try:
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_creds:
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("✅ Firebase inicializado com sucesso!")
    else:
        logger.error("❌ FIREBASE_CREDENTIALS não configurado!")
        db = None
except Exception as e:
    logger.error(f"❌ Erro ao inicializar Firebase: {e}")
    db = None

# Verificar token Firebase
def verify_firebase_token(token):
    """Verifica o token do Firebase"""
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token inválido: {e}")
        return None

# Rotas de autenticação (simplificadas)
@app.route('/auth/verify', methods=['POST'])
def verify_token():
    """Verifica se o token Firebase é válido e retorna dados do usuário"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'erro': 'Token não fornecido'}), 400
        
        # Verificar token
        decoded = verify_firebase_token(token)
        if not decoded:
            return jsonify({'erro': 'Token inválido'}), 401
        
        # Buscar dados do usuário no Firestore
        user_doc = db.collection('usuarios').document(decoded['uid']).get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return jsonify({
                'valid': True,
                'uid': decoded['uid'],
                'email': decoded.get('email'),
                'nome': user_data.get('nome'),
                'perfil': user_data.get('perfil'),
                'ativo': user_data.get('ativo', True)
            }), 200
        else:
            # Usuário não existe no Firestore, criar
            user_data = {
                'email': decoded.get('email'),
                'nome': decoded.get('name', decoded.get('email', '').split('@')[0]),
                'perfil': 'requisitante',
                'ativo': True,
                'criadoEm': firestore.SERVER_TIMESTAMP
            }
            db.collection('usuarios').document(decoded['uid']).set(user_data)
            
            return jsonify({
                'valid': True,
                'uid': decoded['uid'],
                'email': decoded.get('email'),
                'nome': user_data['nome'],
                'perfil': user_data['perfil'],
                'ativo': True,
                'novo_usuario': True
            }), 200
            
    except Exception as e:
        logger.error(f"Erro ao verificar token: {e}")
        return jsonify({'erro': str(e)}), 500

# APIs para gerenciar dados
@app.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    """Lista todos os usuários"""
    try:
        # Verificar autorização (simplificado)
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'erro': 'Não autorizado'}), 401
        
        token = auth_header.split(' ')[1]
        decoded = verify_firebase_token(token)
        
        if not decoded:
            return jsonify({'erro': 'Token inválido'}), 401
        
        # Verificar se é admin
        user_doc = db.collection('usuarios').document(decoded['uid']).get()
        if not user_doc.exists or user_doc.to_dict().get('perfil') != 'ADMIN':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        # Listar usuários
        usuarios = []
        for doc in db.collection('usuarios').stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            usuarios.append(user_data)
        
        return jsonify(usuarios), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/usuarios', methods=['POST'])
def criar_usuario():
    """Cria novo usuário"""
    try:
        # Verificar autorização
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'erro': 'Não autorizado'}), 401
        
        token = auth_header.split(' ')[1]
        decoded = verify_firebase_token(token)
        
        if not decoded:
            return jsonify({'erro': 'Token inválido'}), 401
        
        # Verificar se é admin
        user_doc = db.collection('usuarios').document(decoded['uid']).get()
        if not user_doc.exists or user_doc.to_dict().get('perfil') != 'ADMIN':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        # Criar usuário
        data = request.get_json()
        
        # Criar no Firebase Auth
        new_user = auth.create_user(
            email=data.get('email'),
            password=data.get('senha'),
            display_name=data.get('nome')
        )
        
        # Criar no Firestore
        db.collection('usuarios').document(new_user.uid).set({
            'email': data.get('email'),
            'nome': data.get('nome'),
            'perfil': data.get('perfil', 'requisitante'),
            'ativo': True,
            'criadoEm': firestore.SERVER_TIMESTAMP,
            'criadoPor': decoded['uid']
        })
        
        return jsonify({
            'sucesso': True,
            'uid': new_user.uid,
            'email': data.get('email')
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        return jsonify({'erro': str(e)}), 500

# APIs para Termos de Referência
@app.route('/api/termos-referencia', methods=['GET', 'POST'])
def termos_referencia():
    """Gerencia Termos de Referência"""
    try:
        # Verificar autorização
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'erro': 'Não autorizado'}), 401
        
        token = auth_header.split(' ')[1]
        decoded = verify_firebase_token(token)
        
        if not decoded:
            return jsonify({'erro': 'Token inválido'}), 401
        
        if request.method == 'GET':
            # Listar TRs
            trs = []
            for doc in db.collection('termos_referencia').stream():
                tr_data = doc.to_dict()
                tr_data['id'] = doc.id
                trs.append(tr_data)
            return jsonify(trs), 200
        
        elif request.method == 'POST':
            # Criar TR
            data = request.get_json()
            tr_ref = db.collection('termos_referencia').document()
            tr_data = {
                'numero_tr': f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'titulo': data.get('titulo'),
                'descricao': data.get('descricao'),
                'requisitante_uid': decoded['uid'],
                'requisitante_email': decoded.get('email'),
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
        return jsonify({'erro': str(e)}), 500

# APIs para Processos
@app.route('/api/processos', methods=['GET', 'POST'])
def processos():
    """Gerencia Processos"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'erro': 'Não autorizado'}), 401
        
        token = auth_header.split(' ')[1]
        decoded = verify_firebase_token(token)
        
        if not decoded:
            return jsonify({'erro': 'Token inválido'}), 401
        
        if request.method == 'GET':
            processos = []
            for doc in db.collection('processos').stream():
                proc_data = doc.to_dict()
                proc_data['id'] = doc.id
                processos.append(proc_data)
            return jsonify(processos), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            proc_ref = db.collection('processos').document()
            proc_data = {
                'numero_processo': f"PROC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'tr_id': data.get('tr_id'),
                'comprador_uid': decoded['uid'],
                'comprador_email': decoded.get('email'),
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
        return jsonify({'erro': str(e)}), 500

# APIs para Propostas
@app.route('/api/propostas', methods=['GET', 'POST'])
def propostas():
    """Gerencia Propostas"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'erro': 'Não autorizado'}), 401
        
        token = auth_header.split(' ')[1]
        decoded = verify_firebase_token(token)
        
        if not decoded:
            return jsonify({'erro': 'Token inválido'}), 401
        
        if request.method == 'GET':
            propostas = []
            for doc in db.collection('propostas').stream():
                prop_data = doc.to_dict()
                prop_data['id'] = doc.id
                propostas.append(prop_data)
            return jsonify(propostas), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            prop_ref = db.collection('propostas').document()
            prop_data = {
                'processo_id': data.get('processo_id'),
                'fornecedor_uid': decoded['uid'],
                'fornecedor_email': decoded.get('email'),
                'valor': data.get('valor'),
                'prazo_entrega': data.get('prazo_entrega'),
                'observacoes': data.get('observacoes'),
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
        'firebase': 'connected' if db else 'not_connected'
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
