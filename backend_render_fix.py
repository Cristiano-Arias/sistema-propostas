# backend_simplificado.py - Versão corrigida para buscar por email
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
        # Buscar usuário por email em vez de UID
        email = request.user.get('email')
        if not email:
            return jsonify({'erro': 'Email não encontrado no token'}), 401
            
        users = db.collection('Usuario').where('email', '==', email).get()
        if not users or len(users) == 0:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
            
        user_data = users[0].to_dict()
        if user_data.get('perfil') != 'ADMIN':
            return jsonify({'erro': 'Acesso negado'}), 403
            
        return f(*args, **kwargs)
    
    return decorated_function

# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.route('/auth/verify', methods=['POST'])
def verify_token():
    """Verifica token e retorna/cria dados do usuário - VERSÃO CORRIGIDA"""
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
        
        if not email:
            return jsonify({'erro': 'Email não encontrado no token'}), 400
        
        # CORREÇÃO: Buscar usuário por EMAIL em vez de UID
        users = db.collection('Usuario').where('email', '==', email).get()
        
        if users and len(users) > 0:
            # Usuário encontrado - usar dados do Firestore
            user_data = users[0].to_dict()
            logger.info(f"✅ Usuário encontrado por email: {email}, perfil: {user_data.get('perfil')}")
        else:
            # Usuário não encontrado - criar novo
            logger.info(f"⚠️ Usuário não encontrado por email: {email}, criando novo...")
            user_data = {
                'email': email,
                'nome': decoded.get('name', email.split('@')[0] if email else 'Usuário'),
                'perfil': 'requisitante',
                'ativo': True,
                'criadoEm': firestore.SERVER_TIMESTAMP
            }
            # Criar com UID como ID do documento
            db.collection('Usuario').document(uid).set(user_data)
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

@app.route('/api/user-profile', methods=['POST'])
def get_user_profile():
    """Retorna o perfil do usuário baseado no email - usado pelo portal unificado"""
    if not db:
        return jsonify({'erro': 'Serviço indisponível'}), 503
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'erro': 'Email não fornecido'}), 400
        
        # Buscar usuário por email na coleção Usuario
        users = db.collection('Usuario').where('email', '==', email).limit(1).get()
        
        if users and len(users) > 0:
            user_data = users[0].to_dict()
            perfil_firestore = (user_data.get('perfil') or '').lower()
            
            # Mapear para o formato esperado pelo frontend
            perfil_map = {
                'fornecedor': 'Fornecedor',
                'requisitante': 'Requisitante', 
                'comprador': 'Comprador',
                'admin': 'Admin'
            }
            
            # Retornar perfil no formato correto
            perfil_final = perfil_map.get(perfil_firestore)
            
            if perfil_final:
                logger.info(f"✅ Perfil encontrado para {email}: {perfil_final}")
                return jsonify({'perfil': perfil_final}), 200
            else:
                logger.warning(f"⚠️ Perfil não mapeado para {email}: {perfil_firestore}")
                return jsonify({'erro': 'Perfil não configurado'}), 404
                
        else:
            logger.info(f"❌ Usuário não encontrado: {email}")
            return jsonify({'erro': 'Usuário não encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Erro ao buscar perfil: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

# ==================== ROTAS DE USUÁRIOS ====================

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
        
        # Criar no Firestore com UID como ID do documento
        db.collection('Usuario').document(new_user.uid).set({
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

# ==================== NOVA ROTA PARA CRIAR FORNECEDOR ====================
@app.route('/api/fornecedores', methods=['POST'])
@require_auth
def criar_fornecedor():
    """
    Cria um novo fornecedor no Firebase Authentication e registra no Firestore.

    Esta rota pode ser acessada por usuários com perfil COMPRADOR ou ADMIN.
    Ela recebe um JSON com pelo menos os campos: email, senha e nome. O campo
    'perfil' é opcional e por padrão será 'fornecedor'. Campos adicionais
    enviados em 'metadata' serão mesclados ao documento salvo no Firestore.
    """
    try:
        data = request.get_json() or {}

        # Verificar dados obrigatórios
        required_fields = ['email', 'senha', 'nome']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'erro': f'Campo {field} é obrigatório'}), 400

        # Verificar o perfil do usuário que está realizando a chamada
        # Buscar o usuário autenticado pelo email no Firestore
        requester_email = request.user.get('email')
        if not requester_email:
            return jsonify({'erro': 'Email não encontrado no token'}), 401

        users = db.collection('Usuario').where('email', '==', requester_email).get()
        if not users or len(users) == 0:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        requester_data = users[0].to_dict()
        perfil_solicitante = (requester_data.get('perfil') or '').upper()

        # Apenas COMPRADOR ou ADMIN podem criar fornecedores
        if perfil_solicitante not in ['COMPRADOR', 'ADMIN']:
            return jsonify({'erro': 'Acesso negado'}), 403

        # Verificar se o fornecedor já existe pelo e-mail
        try:
            existing = auth.get_user_by_email(data['email'])
            # Já existe - retornar erro para evitar duplicidade
            return jsonify({'erro': 'Usuário já existe'}), 400
        except auth.UserNotFoundError:
            # Não encontrado - pode continuar
            pass

        # Criar usuário no Firebase Authentication
        new_user = auth.create_user(
            email=data['email'],
            password=data['senha'],
            display_name=data['nome']
        )

        # Preparar dados para Firestore
        perfil_fornecedor = data.get('perfil', 'fornecedor')
        metadata = data.get('metadata') or {}

        user_doc = {
            'email': data['email'],
            'nome': data['nome'],
            'perfil': perfil_fornecedor,
            'ativo': True,
            'criadoEm': firestore.SERVER_TIMESTAMP,
            'criadoPor': request.user['uid']
        }

        # Mesclar metadados adicionais (cnpj, razaoSocial, etc.)
        for key, value in metadata.items():
            user_doc[key] = value

        # Salvar no Firestore com o UID como ID do documento
        db.collection('Usuario').document(new_user.uid).set(user_doc)

        return jsonify({
            'sucesso': True,
            'uid': new_user.uid,
            'email': data['email']
        }), 201

    except Exception as e:
        logger.error(f'Erro ao criar fornecedor: {e}')
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



# ====== PRODUÇÃO: Middleware de autenticação Firebase e rotas essenciais ======
import os, json, requests
from functools import wraps
from flask import request, jsonify

import firebase_admin
from firebase_admin import credentials, auth, firestore as fa_firestore

# Inicialização segura do Firebase Admin (ler de ENV ou Secret File)
if not firebase_admin._apps:
    cred_json = os.getenv("FIREBASE_CREDENTIALS")
    cred_path = os.getenv("FIREBASE_CREDENTIALS_FILE")
    if cred_json:
        try:
            cred = credentials.Certificate(json.loads(cred_json))
        except Exception:
            # Se a env vier com caminho em vez de JSON
            cred = credentials.Certificate(cred_json)
    elif cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
    else:
        # Tentar padrão do ambiente (ex.: Google ADC)
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)
db = fa_firestore.client()

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        authz = request.headers.get('Authorization', '')
        token = None
        if authz.startswith('Bearer '):
            token = authz.split(' ',1)[1].strip()
        if not token and request.is_json:
            body = request.get_json(silent=True) or {}
            token = body.get('token') or body.get('idToken') or token
        if not token:
            return jsonify({'erro':'Não autenticado'}), 401
        try:
            decoded = auth.verify_id_token(token)
        except Exception as e:
            return jsonify({'erro':'Token inválido','detalhe':str(e)}), 401
        request.user = {
            'uid': decoded.get('uid'),
            'email': decoded.get('email'),
            'role': (decoded.get('role') or decoded.get('firebase',{}).get('sign_in_provider') or decoded.get('claims',{}).get('role'))
        }
        # Tentar enriquecer com perfil do Firestore
        try:
            ud = db.collection('Usuario').document(request.user['uid']).get()
            if ud.exists:
                u = ud.to_dict()
                request.user['perfil'] = u.get('perfil')
                request.user['nome'] = u.get('nome')
                if u.get('perfil') and not request.user.get('role'):
                    request.user['role'] = u.get('perfil')
        except Exception:
            pass
        return f(*args, **kwargs)
    return wrapper

def require_role(*roles):
    roles = set([r.upper() for r in roles])
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if not getattr(request, 'user', None):
                return jsonify({'erro':'Não autenticado'}), 401
            urole = (request.user.get('role') or request.user.get('perfil') or '').upper()
            if 'ADMIN' in roles and urole == 'ADMIN':
                return f(*a, **kw)
            if urole not in roles and urole != 'ADMIN':
                return jsonify({'erro':'Acesso negado'}), 403
            return f(*a, **kw)
        return wrapper
    return deco

@app.route('/health')
def health():
    return jsonify({'ok': True, 'ts': __import__('time').time()})

@app.post('/auth/verify', endpoint='auth_verify')
def auth_verify():
    from flask import request, jsonify
    data = request.get_json(silent=True) or {}
    token = data.get('token') or data.get('idToken')
    if not token:
        return jsonify({'erro': 'Token ausente'}), 400
    try:
        decoded = auth.verify_id_token(token)  # firebase_admin.auth
    except Exception as e:
        return jsonify({'erro':'Token inválido','detalhe':str(e)}), 401

    uid = decoded.get('uid')
    perfil = None
    try:
        udoc = db.collection('Usuario').document(uid).get()
        if udoc.exists:
            perfil = udoc.to_dict().get('perfil')
    except Exception:
        pass

    role = (decoded.get('claims') or {}).get('role') or perfil
    return jsonify({'uid': uid, 'email': decoded.get('email'), 'perfil': role or perfil}), 200

# ===== IA via Azure OpenAI - proxy backend =====
AZURE_ENDPOINT  = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_DEPLOYMENT= os.getenv('AZURE_OPENAI_DEPLOYMENT')
AZURE_KEY       = os.getenv('AZURE_OPENAI_KEY')
AZURE_API_VER   = os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')

@app.post('/api/ia/analise-tecnica')
@require_auth
@require_role('COMPRADOR','ADMIN')
def ia_analise_tecnica():
    if not (AZURE_ENDPOINT and AZURE_DEPLOYMENT and AZURE_KEY):
        return jsonify({'erro':'Azure OpenAI não configurado'}), 400
    data = request.get_json(silent=True) or {}
    processo = data.get('processo',{})
    propostas = data.get('propostas',[])
    prompt = f"""
Compare APENAS critérios técnicos das propostas abaixo e retorne JSON com:
'destaques', 'riscos', 'lacunas', 'recomendacao'. Ignore preços.

Processo: {processo}
PropostasTecnicas: {propostas}
    """.strip()
    url = f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version={AZURE_API_VER}"
    headers = {'Content-Type':'application/json','api-key':AZURE_KEY}
    payload = {
        'messages':[
            {'role':'system','content':'Você avalia propostas técnicas para concorrências.'},
            {'role':'user','content':prompt}
        ],
        'temperature':0.1
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code >= 400:
            return jsonify({'erro':'Falha Azure','detalhe':r.text}), 502
        out = r.json()
        content = out['choices'][0]['message']['content']
        return jsonify({'ok':True,'analise':content})
    except Exception as e:
        return jsonify({'erro':'Exceção','detalhe':str(e)}), 500

# ===== Publicar apenas TÉCNICA ao Requisitante =====
from google.cloud import firestore
@app.post('/api/processos/<proc_id>/publicar-tecnica')
@require_auth
@require_role('COMPRADOR','ADMIN')
def publicar_tecnica(proc_id):
    proc_ref = db.collection('processos').document(proc_id)
    proc_doc = proc_ref.get()
    if not proc_doc.exists:
        return jsonify({'erro':'Processo não encontrado'}), 404
    p = proc_doc.to_dict()
    if p.get('comprador_uid') != request.user['uid'] and (request.user.get('perfil') or '').upper() != 'ADMIN':
        return jsonify({'erro':'Acesso negado'}), 403

    # ler propostas originais
    props = db.collection('propostas').where('processo_id','==',proc_id).stream()
    batch = db.batch()
    count = 0
    for s in props:
        d = s.to_dict()
        tecnica = {
            'processo_id': proc_id,
            'fornecedor_uid': d.get('fornecedor_uid'),
            'fornecedor_email': d.get('fornecedor_email'),
            'dados_tecnicos': d.get('dados_tecnicos') or {k:v for k,v in d.items() if k not in ['valor','preco','preco_total','impostos','proposta_comercial']},
            'criadoEm': firestore.SERVER_TIMESTAMP,
            'comprador_uid': p.get('comprador_uid'),
            'requisitante_uid': p.get('requisitante_uid')
        }
        pub_ref = db.collection('propostas_publicadas').document()
        batch.set(pub_ref, tecnica)
        count += 1
    batch.commit()
    return jsonify({'ok':True,'publicados':count})

