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
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv

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

def enviar_email_boas_vindas(email_destino, senha_temporaria, nome_fornecedor="Fornecedor"):
    """Envia email de boas-vindas para fornecedor cadastrado"""
    
    # Verificar se SendGrid está configurado
    sg_api_key = os.environ.get('SENDGRID_API_KEY')
    if not sg_api_key:
        logger.warning("⚠️ SENDGRID_API_KEY não configurada - Email não enviado")
        return False
    
    try:
        sg = sendgrid.SendGridAPIClient(api_key=sg_api_key)
        
        # Email do remetente (configure no SendGrid)
        from_email = Email(os.environ.get('EMAIL_FROM', 'noreply@seudominio.com'))
        to_email = To(email_destino)
        subject = "🎉 Bem-vindo ao Portal do Fornecedor"
        
        # HTML do email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .credentials {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #999; }}
                .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏢 Portal do Fornecedor</h1>
                    <p>Bem-vindo ao Sistema de Licitações</p>
                </div>
                
                <div class="content">
                    <h2>Olá, {nome_fornecedor}!</h2>
                    
                    <p>Você foi cadastrado com sucesso em nosso Portal de Licitações. Agora você pode:</p>
                    <ul>
                        <li>✅ Participar de processos licitatórios</li>
                        <li>📄 Enviar propostas e documentos</li>
                        <li>📊 Acompanhar resultados em tempo real</li>
                        <li>🔔 Receber notificações de novas oportunidades</li>
                    </ul>
                    
                    <div class="credentials">
                        <h3>📧 Suas Credenciais de Acesso:</h3>
                        <p><strong>E-mail:</strong> {email_destino}</p>
                        <p><strong>Senha Temporária:</strong> {senha_temporaria}</p>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Importante:</strong> Por segurança, você deve trocar sua senha no primeiro acesso.
                    </div>
                    
                    <center>
                        <a href="{os.environ.get('PORTAL_URL', 'https://seu-dominio.onrender.com')}/static/sistema-autenticacao-fornecedores.html" 
                           class="button" style="color: white;">
                            Acessar Portal do Fornecedor
                        </a>
                    </center>
                    
                    <h3>Próximos Passos:</h3>
                    <ol>
                        <li>Acesse o portal usando suas credenciais</li>
                        <li>Complete seu cadastro com informações da empresa</li>
                        <li>Faça upload dos documentos necessários</li>
                        <li>Aguarde a validação do setor de compras</li>
                    </ol>
                    
                    <p>Se tiver dúvidas, entre em contato com nosso setor de compras:</p>
                    <p>📧 compras@seudominio.com<br>
                    📞 (00) 0000-0000</p>
                </div>
                
                <div class="footer">
                    <p>Este é um email automático, por favor não responda.</p>
                    <p>© 2024 Portal de Licitações - Todos os direitos reservados</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        content = Content("text/html", html_content)
        mail = Mail(from_email, to_email, subject, content)
        
        # Enviar email
        response = sg.send(mail)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ Email enviado para {email_destino}")
            
            # Registrar no Firestore se disponível
            if db:
                db.collection('emails_log').add({
                    'para': email_destino,
                    'tipo': 'boas_vindas',
                    'status': 'enviado',
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
            
            return True
        else:
            logger.error(f"❌ Erro ao enviar email: Status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar email: {e}")
        return False

def enviar_email_reset_senha(email_destino):
    """Envia email com link para reset de senha"""
    
    sg_api_key = os.environ.get('SENDGRID_API_KEY')
    if not sg_api_key:
        logger.warning("⚠️ SENDGRID_API_KEY não configurada")
        return False
    
    try:
        # Gerar link de reset usando Firebase Auth
        link_reset = auth.generate_password_reset_link(email_destino)
        
        sg = sendgrid.SendGridAPIClient(api_key=sg_api_key)
        from_email = Email(os.environ.get('EMAIL_FROM', 'noreply@seudominio.com'))
        to_email = To(email_destino)
        subject = "🔑 Recuperação de Senha - Portal do Fornecedor"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔑 Recuperação de Senha</h1>
                </div>
                
                <div class="content">
                    <h2>Solicitação de Nova Senha</h2>
                    
                    <p>Recebemos uma solicitação para redefinir a senha da sua conta no Portal do Fornecedor.</p>
                    
                    <p>Para criar uma nova senha, clique no botão abaixo:</p>
                    
                    <center>
                        <a href="{link_reset}" class="button" style="color: white;">
                            Redefinir Minha Senha
                        </a>
                    </center>
                    
                    <div class="warning">
                        <strong>⚠️ Atenção:</strong> Este link é válido por apenas 1 hora. Se você não solicitou esta alteração, ignore este email.
                    </div>
                    
                    <p>Se o botão não funcionar, copie e cole o link abaixo em seu navegador:</p>
                    <p style="word-break: break-all; font-size: 12px; color: #666;">{link_reset}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        content = Content("text/html", html_content)
        mail = Mail(from_email, to_email, subject, content)
        
        response = sg.send(mail)
        return response.status_code in [200, 201, 202]
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar email de reset: {e}")
        return False

# ==================== ROTAS DE EMAIL ====================

@app.route('/api/fornecedor/cadastrar', methods=['POST'])
@require_auth
def cadastrar_fornecedor():
    """Cadastra novo fornecedor e envia email"""
    
    try:
        data = request.get_json()
        email = data.get('email')
        senha_temp = data.get('senha_temporaria')
        
        if not email or not senha_temp:
            return jsonify({'erro': 'Email e senha são obrigatórios'}), 400
        
        # Criar usuário no Firebase Auth
        try:
            user = auth.create_user(
                email=email,
                password=senha_temp,
                disabled=False
            )
            uid = user.uid
        except Exception as e:
            if 'EMAIL_EXISTS' in str(e):
                return jsonify({'erro': 'Email já cadastrado'}), 400
            raise e
        
        # Salvar dados no Firestore
        if db:
            fornecedor_data = {
                'uid': uid,
                'email': email,
                'razaoSocial': data.get('razaoSocial', f'Fornecedor - {email.split("@")[0]}'),
                'cnpj': data.get('cnpj', 'Pendente'),
                'status': 'pendente_cadastro',
                'perfil': 'fornecedor',
                'criadoPor': request.user.get('email', 'sistema'),
                'criadoEm': firestore.SERVER_TIMESTAMP,
                'primeiroAcesso': True
            }
            
            db.collection('fornecedores').document(uid).set(fornecedor_data)
        
        # Enviar email de boas-vindas
        email_enviado = enviar_email_boas_vindas(
            email_destino=email,
            senha_temporaria=senha_temp,
            nome_fornecedor=fornecedor_data.get('razaoSocial')
        )
        
        return jsonify({
            'sucesso': True,
            'uid': uid,
            'email': email,
            'emailEnviado': email_enviado
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao cadastrar fornecedor: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Envia email para reset de senha"""
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'erro': 'Email é obrigatório'}), 400
        
        # Verificar se usuário existe
        try:
            user = auth.get_user_by_email(email)
        except:
            # Não revelar se o email existe ou não (segurança)
            return jsonify({'sucesso': True, 'mensagem': 'Se o email existir, instruções serão enviadas'}), 200
        
        # Enviar email
        email_enviado = enviar_email_reset_senha(email)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Email de recuperação enviado' if email_enviado else 'Email será enviado em breve'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no reset de senha: {e}")
        return jsonify({'erro': 'Erro ao processar solicitação'}), 500

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
