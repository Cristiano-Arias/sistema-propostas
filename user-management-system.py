#!/usr/bin/env python3
"""
Sistema de Gerenciamento de Usuários - Produção
Para o Sistema de Gestão de Propostas
"""

import os
import json
import bcrypt
import secrets
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuração do Flask
app = Flask(__name__)

# Configurações
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///usuarios_producao.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', secrets.token_hex(32))

# Inicializar extensões
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# MODELOS DE BANCO DE DADOS
# ========================================

class Usuario(db.Model):
    """Modelo de usuário para produção"""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False)  # requisitante, comprador, admin_sistema
    departamento = db.Column(db.String(100))
    cargo = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, default=True)
    primeiro_acesso = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    tentativas_login = db.Column(db.Integer, default=0)
    bloqueado_ate = db.Column(db.DateTime)
    token_reset = db.Column(db.String(100))
    token_reset_expira = db.Column(db.DateTime)
    
    # Relacionamentos
    logs = db.relationship('LogAuditoria', backref='usuario', lazy=True)
    
    def set_senha(self, senha):
        """Define senha com hash seguro"""
        self.senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verificar_senha(self, senha):
        """Verifica senha contra hash"""
        return bcrypt.checkpw(senha.encode('utf-8'), self.senha_hash.encode('utf-8'))
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'cpf': self.cpf,
            'perfil': self.perfil,
            'departamento': self.departamento,
            'cargo': self.cargo,
            'telefone': self.telefone,
            'ativo': self.ativo,
            'primeiro_acesso': self.primeiro_acesso,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'ultimo_login': self.ultimo_login.isoformat() if self.ultimo_login else None
        }

class Fornecedor(db.Model):
    """Modelo de fornecedor para produção"""
    __tablename__ = 'fornecedores'
    
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(200), nullable=False)
    nome_fantasia = db.Column(db.String(200))
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    inscricao_estadual = db.Column(db.String(20))
    inscricao_municipal = db.Column(db.String(20))
    
    # Endereço
    endereco = db.Column(db.String(200))
    numero = db.Column(db.String(20))
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(9))
    
    # Contatos
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    celular = db.Column(db.String(20))
    website = db.Column(db.String(200))
    
    # Responsáveis
    responsavel_nome = db.Column(db.String(100))
    responsavel_cpf = db.Column(db.String(14))
    responsavel_email = db.Column(db.String(120))
    responsavel_telefone = db.Column(db.String(20))
    
    # Dados técnicos
    responsavel_tecnico = db.Column(db.String(100))
    crea_cau = db.Column(db.String(50))
    
    # Controle de acesso
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    aprovado = db.Column(db.Boolean, default=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    data_aprovacao = db.Column(db.DateTime)
    aprovado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Documentação
    certidoes_validas = db.Column(db.Boolean, default=False)
    data_validade_certidoes = db.Column(db.Date)
    
    def set_senha(self, senha):
        """Define senha com hash seguro"""
        self.senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verificar_senha(self, senha):
        """Verifica senha contra hash"""
        return bcrypt.checkpw(senha.encode('utf-8'), self.senha_hash.encode('utf-8'))
    
    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'razao_social': self.razao_social,
            'nome_fantasia': self.nome_fantasia,
            'cnpj': self.cnpj,
            'email': self.email,
            'telefone': self.telefone,
            'cidade': self.cidade,
            'estado': self.estado,
            'ativo': self.ativo,
            'aprovado': self.aprovado,
            'certidoes_validas': self.certidoes_validas,
            'data_cadastro': self.data_cadastro.isoformat() if self.data_cadastro else None
        }

class LogAuditoria(db.Model):
    """Log de auditoria para todas as ações"""
    __tablename__ = 'logs_auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    acao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    ip_origem = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    sucesso = db.Column(db.Boolean, default=True)

# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def gerar_senha_temporaria():
    """Gera senha temporária segura"""
    chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$%'
    senha = ''.join(secrets.choice(chars) for _ in range(12))
    return senha

def enviar_email(destinatario, assunto, corpo_html):
    """Envia e-mail (configurar servidor SMTP)"""
    try:
        # Configurações do servidor SMTP
        smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_pass = os.environ.get('SMTP_PASS')
        
        if not smtp_user or not smtp_pass:
            logger.warning("Servidor SMTP não configurado")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = smtp_user
        msg['To'] = destinatario
        
        msg.attach(MIMEText(corpo_html, 'html'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        return False

def registrar_log(usuario_id, acao, descricao, ip_origem=None, sucesso=True):
    """Registra ação no log de auditoria"""
    try:
        log = LogAuditoria(
            usuario_id=usuario_id,
            acao=acao,
            descricao=descricao,
            ip_origem=ip_origem or request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            sucesso=sucesso
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")

# ========================================
# ROTAS DE GERENCIAMENTO DE USUÁRIOS
# ========================================

@app.route('/api/usuarios/criar', methods=['POST'])
@jwt_required()
def criar_usuario():
    """Cria novo usuário (apenas admin)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)
        
        if current_user.perfil != 'admin_sistema':
            return jsonify({'erro': 'Sem permissão para criar usuários'}), 403
        
        data = request.json
        
        # Validar dados obrigatórios
        campos_obrigatorios = ['nome', 'email', 'cpf', 'perfil', 'departamento']
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return jsonify({'erro': f'Campo {campo} é obrigatório'}), 400
        
        # Verificar se usuário já existe
        if Usuario.query.filter_by(email=data['email']).first():
            return jsonify({'erro': 'E-mail já cadastrado'}), 400
        
        if Usuario.query.filter_by(cpf=data['cpf']).first():
            return jsonify({'erro': 'CPF já cadastrado'}), 400
        
        # Criar usuário
        senha_temp = gerar_senha_temporaria()
        
        usuario = Usuario(
            nome=data['nome'],
            email=data['email'],
            cpf=data['cpf'],
            perfil=data['perfil'],
            departamento=data['departamento'],
            cargo=data.get('cargo'),
            telefone=data.get('telefone'),
            primeiro_acesso=True
        )
        usuario.set_senha(senha_temp)
        
        db.session.add(usuario)
        db.session.commit()
        
        # Enviar e-mail com credenciais
        corpo_email = f"""
        <h2>Bem-vindo ao Sistema de Gestão de Propostas</h2>
        <p>Olá {usuario.nome},</p>
        <p>Sua conta foi criada com sucesso. Seguem suas credenciais de acesso:</p>
        <ul>
            <li><strong>E-mail:</strong> {usuario.email}</li>
            <li><strong>Senha temporária:</strong> {senha_temp}</li>
            <li><strong>Perfil:</strong> {usuario.perfil}</li>
        </ul>
        <p>Por segurança, você deverá alterar sua senha no primeiro acesso.</p>
        <p>Acesse o sistema em: {request.host_url}</p>
        """
        
        enviar_email(usuario.email, 'Conta Criada - Sistema de Propostas', corpo_email)
        
        # Log de auditoria
        registrar_log(
            current_user_id, 
            'CRIAR_USUARIO', 
            f'Usuário {usuario.nome} ({usuario.email}) criado'
        )
        
        return jsonify({
            'mensagem': 'Usuário criado com sucesso',
            'usuario': usuario.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        return jsonify({'erro': 'Erro ao criar usuário'}), 500

@app.route('/api/usuarios', methods=['GET'])
@jwt_required()
def listar_usuarios():
    """Lista todos os usuários (apenas admin e comprador)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)
        
        if current_user.perfil not in ['admin_sistema', 'comprador']:
            return jsonify({'erro': 'Sem permissão para listar usuários'}), 403
        
        usuarios = Usuario.query.all()
        
        return jsonify({
            'usuarios': [u.to_dict() for u in usuarios]
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({'erro': 'Erro ao listar usuários'}), 500

@app.route('/api/usuarios/<int:id>/ativar', methods=['PUT'])
@jwt_required()
def ativar_desativar_usuario(id):
    """Ativa ou desativa usuário"""
    try:
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)
        
        if current_user.perfil != 'admin_sistema':
            return jsonify({'erro': 'Sem permissão'}), 403
        
        usuario = Usuario.query.get(id)
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        usuario.ativo = not usuario.ativo
        db.session.commit()
        
        acao = 'ATIVAR_USUARIO' if usuario.ativo else 'DESATIVAR_USUARIO'
        registrar_log(
            current_user_id,
            acao,
            f'Usuário {usuario.nome} ({usuario.email}) {"ativado" if usuario.ativo else "desativado"}'
        )
        
        return jsonify({
            'mensagem': f'Usuário {"ativado" if usuario.ativo else "desativado"} com sucesso',
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao ativar/desativar usuário: {e}")
        return jsonify({'erro': 'Erro ao processar solicitação'}), 500

@app.route('/api/usuarios/<int:id>/resetar-senha', methods=['POST'])
@jwt_required()
def resetar_senha_usuario(id):
    """Reseta senha do usuário"""
    try:
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)
        
        if current_user.perfil != 'admin_sistema':
            return jsonify({'erro': 'Sem permissão'}), 403
        
        usuario = Usuario.query.get(id)
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        nova_senha = gerar_senha_temporaria()
        usuario.set_senha(nova_senha)
        usuario.primeiro_acesso = True
        db.session.commit()
        
        # Enviar e-mail
        corpo_email = f"""
        <h2>Senha Resetada</h2>
        <p>Olá {usuario.nome},</p>
        <p>Sua senha foi resetada pelo administrador do sistema.</p>
        <p><strong>Nova senha temporária:</strong> {nova_senha}</p>
        <p>Por segurança, você deverá alterar sua senha no próximo acesso.</p>
        """
        
        enviar_email(usuario.email, 'Senha Resetada - Sistema de Propostas', corpo_email)
        
        registrar_log(
            current_user_id,
            'RESETAR_SENHA',
            f'Senha resetada para usuário {usuario.nome} ({usuario.email})'
        )
        
        return jsonify({
            'mensagem': 'Senha resetada com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao resetar senha: {e}")
        return jsonify({'erro': 'Erro ao resetar senha'}), 500

# ========================================
# ROTAS DE GERENCIAMENTO DE FORNECEDORES
# ========================================

@app.route('/api/fornecedores/cadastro', methods=['POST'])
def cadastro_fornecedor():
    """Auto-cadastro de fornecedor"""
    try:
        data = request.json
        
        # Validar dados obrigatórios
        campos_obrigatorios = [
            'razao_social', 'cnpj', 'email', 'telefone',
            'endereco', 'cidade', 'estado', 'cep',
            'responsavel_nome', 'responsavel_cpf', 'senha'
        ]
        
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return jsonify({'erro': f'Campo {campo} é obrigatório'}), 400
        
        # Verificar se já existe
        if Fornecedor.query.filter_by(cnpj=data['cnpj']).first():
            return jsonify({'erro': 'CNPJ já cadastrado'}), 400
        
        if Fornecedor.query.filter_by(email=data['email']).first():
            return jsonify({'erro': 'E-mail já cadastrado'}), 400
        
        # Criar fornecedor
        fornecedor = Fornecedor(
            razao_social=data['razao_social'],
            nome_fantasia=data.get('nome_fantasia'),
            cnpj=data['cnpj'],
            inscricao_estadual=data.get('inscricao_estadual'),
            inscricao_municipal=data.get('inscricao_municipal'),
            endereco=data['endereco'],
            numero=data.get('numero'),
            complemento=data.get('complemento'),
            bairro=data.get('bairro'),
            cidade=data['cidade'],
            estado=data['estado'],
            cep=data['cep'],
            email=data['email'],
            telefone=data['telefone'],
            celular=data.get('celular'),
            website=data.get('website'),
            responsavel_nome=data['responsavel_nome'],
            responsavel_cpf=data['responsavel_cpf'],
            responsavel_email=data.get('responsavel_email'),
            responsavel_telefone=data.get('responsavel_telefone'),
            responsavel_tecnico=data.get('responsavel_tecnico'),
            crea_cau=data.get('crea_cau')
        )
        fornecedor.set_senha(data['senha'])
        
        db.session.add(fornecedor)
        db.session.commit()
        
        # Enviar e-mail de confirmação
        corpo_email = f"""
        <h2>Cadastro Realizado com Sucesso</h2>
        <p>Prezado(a) {fornecedor.responsavel_nome},</p>
        <p>O cadastro da empresa {fornecedor.razao_social} foi realizado com sucesso.</p>
        <p>Seu cadastro está <strong>pendente de aprovação</strong> pelo setor de compras.</p>
        <p>Você receberá um e-mail quando seu cadastro for aprovado.</p>
        """
        
        enviar_email(fornecedor.email, 'Cadastro Realizado - Aguardando Aprovação', corpo_email)
        
        # Notificar compradores
        compradores = Usuario.query.filter_by(perfil='comprador', ativo=True).all()
        for comprador in compradores:
            corpo_notif = f"""
            <h2>Novo Fornecedor Aguardando Aprovação</h2>
            <p>Um novo fornecedor se cadastrou e aguarda aprovação:</p>
            <ul>
                <li><strong>Razão Social:</strong> {fornecedor.razao_social}</li>
                <li><strong>CNPJ:</strong> {fornecedor.cnpj}</li>
                <li><strong>E-mail:</strong> {fornecedor.email}</li>
            </ul>
            <p>Acesse o sistema para aprovar ou rejeitar o cadastro.</p>
            """
            enviar_email(comprador.email, 'Novo Fornecedor Aguardando Aprovação', corpo_notif)
        
        return jsonify({
            'mensagem': 'Cadastro realizado com sucesso. Aguarde aprovação.',
            'fornecedor_id': fornecedor.id
        }), 201
        
    except Exception as e:
        logger.error(f"Erro no cadastro de fornecedor: {e}")
        return jsonify({'erro': 'Erro ao realizar cadastro'}), 500

@app.route('/api/fornecedores/pendentes', methods=['GET'])
@jwt_required()
def listar_fornecedores_pendentes():
    """Lista fornecedores pendentes de aprovação"""
    try:
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)
        
        if current_user.perfil not in ['admin_sistema', 'comprador']:
            return jsonify({'erro': 'Sem permissão'}), 403
        
        fornecedores = Fornecedor.query.filter_by(aprovado=False, ativo=True).all()
        
        return jsonify({
            'fornecedores': [f.to_dict() for f in fornecedores]
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar fornecedores pendentes: {e}")
        return jsonify({'erro': 'Erro ao listar fornecedores'}), 500

@app.route('/api/fornecedores/<int:id>/aprovar', methods=['PUT'])
@jwt_required()
def aprovar_fornecedor(id):
    """Aprova cadastro de fornecedor"""
    try:
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)
        
        if current_user.perfil not in ['admin_sistema', 'comprador']:
            return jsonify({'erro': 'Sem permissão'}), 403
        
        fornecedor = Fornecedor.query.get(id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        fornecedor.aprovado = True
        fornecedor.data_aprovacao = datetime.utcnow()
        fornecedor.aprovado_por = current_user_id
        db.session.commit()
        
        # Enviar e-mail
        corpo_email = f"""
        <h2>Cadastro Aprovado</h2>
        <p>Prezado(a) {fornecedor.responsavel_nome},</p>
        <p>O cadastro da empresa {fornecedor.razao_social} foi <strong>aprovado</strong>.</p>
        <p>Você já pode acessar o sistema e participar dos processos de compra.</p>
        <p>Acesse em: {request.host_url}sistema-autenticacao-fornecedores.html</p>
        <p>Use seu CNPJ ou e-mail para login.</p>
        """
        
        enviar_email(fornecedor.email, 'Cadastro Aprovado - Sistema de Propostas', corpo_email)
        
        registrar_log(
            current_user_id,
            'APROVAR_FORNECEDOR',
            f'Fornecedor {fornecedor.razao_social} ({fornecedor.cnpj}) aprovado'
        )
        
        return jsonify({
            'mensagem': 'Fornecedor aprovado com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao aprovar fornecedor: {e}")
        return jsonify({'erro': 'Erro ao aprovar fornecedor'}), 500

# ========================================
# ROTAS DE AUTENTICAÇÃO
# ========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login de usuários internos"""
    try:
        data = request.json
        email = data.get('email')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({'erro': 'E-mail e senha são obrigatórios'}), 400
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            registrar_log(None, 'LOGIN_FALHOU', f'E-mail não encontrado: {email}', sucesso=False)
            return jsonify({'erro': 'Credenciais inválidas'}), 401
        
        if not usuario.ativo:
            return jsonify({'erro': 'Usuário inativo'}), 401
        
        if usuario.bloqueado_ate and usuario.bloqueado_ate > datetime.utcnow():
            return jsonify({'erro': 'Usuário bloqueado temporariamente'}), 401
        
        if not usuario.verificar_senha(senha):
            usuario.tentativas_login += 1
            
            if usuario.tentativas_login >= 5:
                usuario.bloqueado_ate = datetime.utcnow() + timedelta(minutes=30)
                
            db.session.commit()
            registrar_log(usuario.id, 'LOGIN_FALHOU', 'Senha incorreta', sucesso=False)
            return jsonify({'erro': 'Credenciais inválidas'}), 401
        
        # Login bem-sucedido
        usuario.tentativas_login = 0
        usuario.ultimo_login = datetime.utcnow()
        db.session.commit()
        
        access_token = create_access_token(identity=usuario.id)
        
        registrar_log(usuario.id, 'LOGIN', 'Login bem-sucedido')
        
        return jsonify({
            'access_token': access_token,
            'usuario': usuario.to_dict(),
            'primeiro_acesso': usuario.primeiro_acesso
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({'erro': 'Erro ao processar login'}), 500

@app.route('/api/auth/login-fornecedor', methods=['POST'])
def login_fornecedor():
    """Login de fornecedores"""
    try:
        data = request.json
        login = data.get('login')  # CNPJ ou e-mail
        senha = data.get('senha')
        
        if not login or not senha:
            return jsonify({'erro': 'Login e senha são obrigatórios'}), 400
        
        # Buscar por CNPJ ou e-mail
        fornecedor = Fornecedor.query.filter(
            (Fornecedor.cnpj == login) | (Fornecedor.email == login)
        ).first()
        
        if not fornecedor:
            return jsonify({'erro': 'Credenciais inválidas'}), 401
        
        if not fornecedor.ativo:
            return jsonify({'erro': 'Fornecedor inativo'}), 401
        
        if not fornecedor.aprovado:
            return jsonify({'erro': 'Cadastro pendente de aprovação'}), 401
        
        if not fornecedor.verificar_senha(senha):
            return jsonify({'erro': 'Credenciais inválidas'}), 401
        
        # Login bem-sucedido
        access_token = create_access_token(
            identity=f'fornecedor_{fornecedor.id}',
            additional_claims={'tipo': 'fornecedor'}
        )
        
        return jsonify({
            'access_token': access_token,
            'fornecedor': fornecedor.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no login fornecedor: {e}")
        return jsonify({'erro': 'Erro ao processar login'}), 500

@app.route('/api/auth/alterar-senha', methods=['POST'])
@jwt_required()
def alterar_senha():
    """Altera senha do usuário"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        senha_atual = data.get('senha_atual')
        senha_nova = data.get('senha_nova')
        
        if not senha_atual or not senha_nova:
            return jsonify({'erro': 'Senhas são obrigatórias'}), 400
        
        # Verificar se é usuário ou fornecedor
        if current_user_id.startswith('fornecedor_'):
            fornecedor_id = int(current_user_id.replace('fornecedor_', ''))
            usuario = Fornecedor.query.get(fornecedor_id)
        else:
            usuario = Usuario.query.get(current_user_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        if not usuario.verificar_senha(senha_atual):
            return jsonify({'erro': 'Senha atual incorreta'}), 400
        
        # Validar nova senha
        if len(senha_nova) < 8:
            return jsonify({'erro': 'Senha deve ter no mínimo 8 caracteres'}), 400
        
        usuario.set_senha(senha_nova)
        
        if hasattr(usuario, 'primeiro_acesso'):
            usuario.primeiro_acesso = False
        
        db.session.commit()
        
        return jsonify({'mensagem': 'Senha alterada com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {e}")
        return jsonify({'erro': 'Erro ao alterar senha'}), 500

# ========================================
# INICIALIZAÇÃO DO BANCO
# ========================================

def criar_usuario_admin():
    """Cria usuário administrador padrão"""
    admin = Usuario.query.filter_by(email='admin@sistema.com').first()
    if not admin:
        admin = Usuario(
            nome='Administrador do Sistema',
            email='admin@sistema.com',
            cpf='000.000.000-00',
            perfil='admin_sistema',
            departamento='TI',
            cargo='Administrador',
            primeiro_acesso=False
        )
        admin.set_senha('Admin@2025!')
        db.session.add(admin)
        db.session.commit()
        logger.info("Usuário administrador criado")

@app.before_first_request
def inicializar():
    """Inicializa o banco de dados"""
    db.create_all()
    criar_usuario_admin()

# ========================================
# ROTAS DE RELATÓRIOS
# ========================================

@app.route('/api/relatorios/usuarios', methods=['GET'])
@jwt_required()
def relatorio_usuarios():
    """Relatório de usuários do sistema"""
    try:
        current_user_id = get_jwt_identity()
        current_user = Usuario.query.get(current_user_id)
        
        if current_user.perfil != 'admin_sistema':
            return jsonify({'erro': 'Sem permissão'}), 403
        
        # Estatísticas
        total_usuarios = Usuario.query.count()
        usuarios_ativos = Usuario.query.filter_by(ativo=True).count()
        usuarios_por_perfil = db.session.query(
            Usuario.perfil, 
            db.func.count(Usuario.id)
        ).group_by(Usuario.perfil).all()
        
        # Últimos acessos
        ultimos_acessos = Usuario.query.filter(
            Usuario.ultimo_login.isnot(None)
        ).order_by(Usuario.ultimo_login.desc()).limit(10).all()
        
        return jsonify({
            'estatisticas': {
                'total': total_usuarios,
                'ativos': usuarios_ativos,
                'inativos': total_usuarios - usuarios_ativos,
                'por_perfil': dict(usuarios_por_perfil)
            },
            'ultimos_acessos': [
                {
                    'nome': u.nome,
                    'email': u.email,
                    'perfil': u.perfil,
                    'ultimo_login': u.ultimo_login.isoformat()
                }
                for u in ultimos_acessos
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        return jsonify({'erro': 'Erro ao gerar relatório'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)