#!/usr/bin/env python3
"""
Backend Completo - Sistema de Gestão de Propostas
Versão 5.0 - Totalmente Integrado
"""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import jwt
import bcrypt
import sqlite3
from werkzeug.utils import secure_filename
from io import BytesIO

# Configuração do Flask
app = Flask(__name__, static_folder='static')

# Configurações
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///sistema_propostas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Criar pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Extensões permitidas
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg'}

# Inicializar CORS
CORS(app, origins=['*'])

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração JWT simples (sem flask-jwt-extended)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-123')

# Inicializar banco de dados SQLite
def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Criar tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Criar tabela de TRs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS termos_referencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            objeto TEXT NOT NULL,
            justificativa TEXT,
            especificacoes TEXT,
            prazo_entrega INTEGER,
            local_entrega TEXT,
            condicoes_pagamento TEXT,
            garantia TEXT,
            criterios_aceitacao TEXT,
            status TEXT DEFAULT 'pendente',
            usuario_id INTEGER,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            parecer TEXT,
            motivo_reprovacao TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Criar tabela de processos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            tr_id INTEGER,
            objeto TEXT NOT NULL,
            modalidade TEXT,
            data_abertura TIMESTAMP,
            hora_abertura TEXT,
            local_abertura TEXT,
            prazo_proposta INTEGER,
            contato_email TEXT,
            contato_telefone TEXT,
            status TEXT DEFAULT 'aberto',
            criado_por INTEGER,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tr_id) REFERENCES termos_referencia (id),
            FOREIGN KEY (criado_por) REFERENCES usuarios (id)
        )
    ''')
    
    # Criar tabela de propostas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS propostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_id INTEGER,
            fornecedor_id INTEGER,
            valor_total REAL,
            prazo_entrega INTEGER,
            validade_proposta INTEGER,
            status TEXT DEFAULT 'enviada',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (processo_id) REFERENCES processos (id),
            FOREIGN KEY (fornecedor_id) REFERENCES usuarios (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Banco de dados inicializado com sucesso")

# Inicializar banco ao iniciar
init_db()

# ========================================
# MODELOS DE BANCO DE DADOS
# ========================================

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'tipo': self.tipo,
            'ativo': self.ativo
        }

class TermoReferencia(db.Model):
    __tablename__ = 'termos_referencia'
    
    id = db.Column(db.String(50), primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    objeto = db.Column(db.Text, nullable=False)
    descricao = db.Column(db.Text)
    modalidade = db.Column(db.String(50))
    local = db.Column(db.String(100))
    prazo_execucao = db.Column(db.Integer)
    valor_estimado = db.Column(db.Numeric(15, 2))
    status = db.Column(db.String(20), default='PENDENTE_APROVACAO')
    criado_por = db.Column(db.String(50), db.ForeignKey('usuarios.id'))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    aprovado_por = db.Column(db.String(50))
    data_aprovacao = db.Column(db.DateTime)
    parecer_comprador = db.Column(db.Text)
    
    # Campos técnicos
    especificacoes_tecnicas = db.Column(db.Text)
    requisitos_funcionais = db.Column(db.Text)
    requisitos_nao_funcionais = db.Column(db.Text)
    criterios_aceitacao = db.Column(db.Text)
    documentacao_exigida = db.Column(db.Text)
    qualificacao_tecnica = db.Column(db.Text)
    local_entrega = db.Column(db.String(200))
    condicoes_pagamento = db.Column(db.Text)
    garantias_exigidas = db.Column(db.Text)
    fonte_pagadora = db.Column(db.String(100))
    justificativa = db.Column(db.Text)
    
    # Relações
    criador = db.relationship('Usuario', backref='trs_criados', foreign_keys=[criado_por])
    
    def to_dict(self):
        return {
            'id': self.id,
            'numeroTR': self.numero,
            'titulo': self.titulo,
            'objeto': self.objeto,
            'descricao': self.descricao,
            'modalidade': self.modalidade,
            'local': self.local,
            'prazoExecucao': self.prazo_execucao,
            'valorEstimado': float(self.valor_estimado) if self.valor_estimado else None,
            'status': self.status,
            'criadoPor': self.criado_por,
            'criadorNome': self.criador.nome if self.criador else None,
            'dataCriacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'aprovadoPor': self.aprovado_por,
            'dataAprovacao': self.data_aprovacao.isoformat() if self.data_aprovacao else None,
            'parecerComprador': self.parecer_comprador,
            'especificacoesTecnicas': self.especificacoes_tecnicas,
            'requisitosFuncionais': self.requisitos_funcionais,
            'requisitosNaoFuncionais': self.requisitos_nao_funcionais,
            'criteriosAceitacao': self.criterios_aceitacao,
            'documentacaoExigida': self.documentacao_exigida,
            'qualificacaoTecnica': self.qualificacao_tecnica,
            'localEntrega': self.local_entrega,
            'condicoesPagamento': self.condicoes_pagamento,
            'garantiasExigidas': self.garantias_exigidas,
            'fontePagadora': self.fonte_pagadora,
            'justificativa': self.justificativa
        }

class Processo(db.Model):
    __tablename__ = 'processos'
    
    id = db.Column(db.String(50), primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    tr_id = db.Column(db.String(50), db.ForeignKey('termos_referencia.id'))
    objeto = db.Column(db.Text, nullable=False)
    modalidade = db.Column(db.String(50), nullable=False)
    data_abertura = db.Column(db.DateTime)
    data_limite = db.Column(db.DateTime)
    local_abertura = db.Column(db.String(200))
    status = db.Column(db.String(20), default='ATIVO')
    criado_por = db.Column(db.String(50), db.ForeignKey('usuarios.id'))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relações
    tr = db.relationship('TermoReferencia', backref='processo')
    criador = db.relationship('Usuario', backref='processos_criados')
    fornecedores = db.relationship('ProcessoFornecedor', backref='processo')
    propostas = db.relationship('Proposta', backref='processo')
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero': self.numero,
            'trId': self.tr_id,
            'objeto': self.objeto,
            'modalidade': self.modalidade,
            'dataAbertura': self.data_abertura.isoformat() if self.data_abertura else None,
            'dataLimite': self.data_limite.isoformat() if self.data_limite else None,
            'localAbertura': self.local_abertura,
            'status': self.status,
            'criadoPor': self.criado_por,
            'criadorNome': self.criador.nome if self.criador else None,
            'dataCriacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'fornecedores': [f.to_dict() for f in self.fornecedores],
            'totalPropostas': len(self.propostas)
        }

class ProcessoFornecedor(db.Model):
    __tablename__ = 'processo_fornecedores'
    
    id = db.Column(db.Integer, primary_key=True)
    processo_id = db.Column(db.String(50), db.ForeignKey('processos.id'))
    cnpj = db.Column(db.String(18), nullable=False)
    razao_social = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    login = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True)
    data_convite = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'processoId': self.processo_id,
            'cnpj': self.cnpj,
            'razaoSocial': self.razao_social,
            'email': self.email,
            'login': self.login,
            'ativo': self.ativo,
            'dataConvite': self.data_convite.isoformat() if self.data_convite else None
        }

class Proposta(db.Model):
    __tablename__ = 'propostas'
    
    id = db.Column(db.String(50), primary_key=True)
    processo_id = db.Column(db.String(50), db.ForeignKey('processos.id'))
    fornecedor_login = db.Column(db.String(50), nullable=False)
    empresa = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), nullable=False)
    valor = db.Column(db.Numeric(15, 2), nullable=False)
    prazo_execucao = db.Column(db.Integer)
    descricao_tecnica = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    status = db.Column(db.String(20), default='ENVIADA')
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'processoId': self.processo_id,
            'fornecedorLogin': self.fornecedor_login,
            'empresa': self.empresa,
            'cnpj': self.cnpj,
            'valor': float(self.valor) if self.valor else 0,
            'prazoExecucao': self.prazo_execucao,
            'descricaoTecnica': self.descricao_tecnica,
            'observacoes': self.observacoes,
            'status': self.status,
            'dataEnvio': self.data_envio.isoformat() if self.data_envio else None
        }

class Notificacao(db.Model):
    __tablename__ = 'notificacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.String(50))
    tipo = db.Column(db.String(50))
    titulo = db.Column(db.String(200))
    mensagem = db.Column(db.Text)
    lida = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'titulo': self.titulo,
            'mensagem': self.mensagem,
            'lida': self.lida,
            'dataCriacao': self.data_criacao.isoformat() if self.data_criacao else None
        }

# ========================================
# FUNÇÕES AUXILIARES
# ========================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def gerar_id():
    return str(uuid.uuid4())

def gerar_login_fornecedor(cnpj):
    cnpj_numeros = ''.join(filter(str.isdigit, cnpj))
    return f"fornecedor_{cnpj_numeros[-8:]}"

def gerar_senha_aleatoria():
    import random
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

def criar_notificacao(usuario_id, tipo, titulo, mensagem):
    """Cria uma nova notificação para um usuário"""
    notificacao = Notificacao(
        usuario_id=usuario_id,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem
    )
    db.session.add(notificacao)
    db.session.commit()

def gerar_pdf_tr(tr):
    """Gera PDF do Termo de Referência"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=1  # Centro
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12
    )
    
    # Título
    elements.append(Paragraph("TERMO DE REFERÊNCIA", title_style))
    elements.append(Paragraph(f"{tr.numero}", styles['Heading2']))
    elements.append(Spacer(1, 0.5*inch))
    
    # Informações básicas
    data = [
        ['Campo', 'Valor'],
        ['Objeto', tr.objeto],
        ['Modalidade', tr.modalidade or 'Não especificada'],
        ['Local', tr.local or 'Não especificado'],
        ['Prazo de Execução', f"{tr.prazo_execucao} dias" if tr.prazo_execucao else 'Não especificado'],
        ['Valor Estimado', f"R$ {tr.valor_estimado:,.2f}" if tr.valor_estimado else 'Não informado'],
        ['Status', tr.status],
        ['Criado por', tr.criador.nome if tr.criador else 'Sistema'],
        ['Data de Criação', tr.data_criacao.strftime('%d/%m/%Y') if tr.data_criacao else '']
    ]
    
    # Tabela de informações
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Seções do TR
    if tr.descricao:
        elements.append(Paragraph("Descrição", heading_style))
        elements.append(Paragraph(tr.descricao, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
    
    if tr.especificacoes_tecnicas:
        elements.append(Paragraph("Especificações Técnicas", heading_style))
        elements.append(Paragraph(tr.especificacoes_tecnicas, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
    
    if tr.requisitos_funcionais:
        elements.append(Paragraph("Requisitos Funcionais", heading_style))
        elements.append(Paragraph(tr.requisitos_funcionais, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
    
    if tr.justificativa:
        elements.append(Paragraph("Justificativa", heading_style))
        elements.append(Paragraph(tr.justificativa, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
    
    # Gerar PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ========================================
# CONFIGURAÇÃO JWT
# ========================================

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'success': False,
        'error': 'Token expirado'
    }), 401

# ========================================
# ROTAS DE AUTENTICAÇÃO
# ========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario or not usuario.verificar_senha(senha):
            return jsonify({
                'success': False,
                'error': 'Credenciais inválidas'
            }), 401
        
        if not usuario.ativo:
            return jsonify({
                'success': False,
                'error': 'Usuário inativo'
            }), 401
        
        access_token = create_access_token(
            identity=usuario.id,
            additional_claims={
                'tipo': usuario.tipo,
                'nome': usuario.nome
            }
        )
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'usuario': usuario.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

@app.route('/api/auth/login-fornecedor', methods=['POST'])
def login_fornecedor():
    try:
        data = request.get_json()
        login = data.get('login')
        senha = data.get('senha')
        
        fornecedor = ProcessoFornecedor.query.filter_by(
            login=login,
            senha=senha,
            ativo=True
        ).first()
        
        if not fornecedor:
            return jsonify({
                'success': False,
                'error': 'Credenciais inválidas'
            }), 401
        
        access_token = create_access_token(
            identity=fornecedor.login,
            additional_claims={
                'tipo': 'fornecedor',
                'cnpj': fornecedor.cnpj,
                'razao_social': fornecedor.razao_social
            }
        )
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'fornecedor': fornecedor.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Erro no login fornecedor: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

# ========================================
# ROTAS DE TERMOS DE REFERÊNCIA
# ========================================

@app.route('/api/trs', methods=['GET'])
@jwt_required()
def listar_trs():
    try:
        claims = get_jwt()
        usuario_tipo = claims.get('tipo')
        usuario_id = get_jwt_identity()
        
        if usuario_tipo == 'requisitante':
            # Requisitante vê apenas seus TRs
            trs = TermoReferencia.query.filter_by(criado_por=usuario_id).all()
        elif usuario_tipo == 'comprador':
            # Comprador vê todos os TRs
            trs = TermoReferencia.query.all()
        else:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403
        
        return jsonify({
            'success': True,
            'trs': [tr.to_dict() for tr in trs]
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar TRs: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

@app.route('/api/trs', methods=['POST'])
@jwt_required()
def criar_tr():
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'requisitante':
            return jsonify({
                'success': False,
                'error': 'Apenas requisitantes podem criar TRs'
            }), 403
        
        data = request.get_json()
        usuario_id = get_jwt_identity()
        
        # Gerar número do TR
        numero_tr = f"TR-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}"
        
        tr = TermoReferencia(
            id=gerar_id(),
            numero=numero_tr,
            titulo=data.get('titulo', data.get('objeto', '')),
            objeto=data.get('objeto', ''),
            descricao=data.get('descricaoObjeto', ''),
            modalidade=data.get('modalidade'),
            local=data.get('local'),
            prazo_execucao=data.get('prazoExecucao'),
            valor_estimado=data.get('valorEstimado'),
            criado_por=usuario_id,
            especificacoes_tecnicas=data.get('especificacoesTecnicas'),
            requisitos_funcionais=data.get('requisitosFuncionais'),
            requisitos_nao_funcionais=data.get('requisitosNaoFuncionais'),
            criterios_aceitacao=data.get('criteriosAceitacao'),
            documentacao_exigida=data.get('documentacaoExigida'),
            qualificacao_tecnica=data.get('qualificacaoTecnica'),
            local_entrega=data.get('localEntrega'),
            condicoes_pagamento=data.get('condicoesPagamento'),
            garantias_exigidas=data.get('garantiasExigidas'),
            fonte_pagadora=data.get('fontePagadora'),
            justificativa=data.get('justificativa')
        )
        
        db.session.add(tr)
        db.session.commit()
        
        # Criar notificação para compradores
        compradores = Usuario.query.filter_by(tipo='comprador', ativo=True).all()
        for comprador in compradores:
            criar_notificacao(
                comprador.id,
                'TR_PENDENTE',
                'Novo TR para Aprovação',
                f'TR {numero_tr} - {tr.objeto}'
            )
        
        return jsonify({
            'success': True,
            'message': 'TR criado com sucesso',
            'tr': tr.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar TR: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao criar TR'
        }), 500

@app.route('/api/trs/<tr_id>', methods=['GET'])
@jwt_required()
def obter_tr(tr_id):
    try:
        tr = TermoReferencia.query.get(tr_id)
        
        if not tr:
            return jsonify({
                'success': False,
                'error': 'TR não encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'tr': tr.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter TR: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

@app.route('/api/trs/<tr_id>/aprovar', methods=['POST'])
@jwt_required()
def aprovar_tr(tr_id):
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'comprador':
            return jsonify({
                'success': False,
                'error': 'Apenas compradores podem aprovar TRs'
            }), 403
        
        data = request.get_json()
        parecer = data.get('parecer', '')
        usuario_id = get_jwt_identity()
        
        tr = TermoReferencia.query.get(tr_id)
        
        if not tr:
            return jsonify({
                'success': False,
                'error': 'TR não encontrado'
            }), 404
        
        tr.status = 'APROVADO'
        tr.aprovado_por = usuario_id
        tr.data_aprovacao = datetime.utcnow()
        tr.parecer_comprador = parecer
        
        db.session.commit()
        
        # Notificar requisitante
        criar_notificacao(
            tr.criado_por,
            'TR_APROVADO',
            'TR Aprovado',
            f'TR {tr.numero} foi aprovado pelo comprador'
        )
        
        return jsonify({
            'success': True,
            'message': 'TR aprovado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao aprovar TR: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao aprovar TR'
        }), 500

@app.route('/api/trs/<tr_id>/reprovar', methods=['POST'])
@jwt_required()
def reprovar_tr(tr_id):
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'comprador':
            return jsonify({
                'success': False,
                'error': 'Apenas compradores podem reprovar TRs'
            }), 403
        
        data = request.get_json()
        parecer = data.get('parecer', '')
        usuario_id = get_jwt_identity()
        
        tr = TermoReferencia.query.get(tr_id)
        
        if not tr:
            return jsonify({
                'success': False,
                'error': 'TR não encontrado'
            }), 404
        
        tr.status = 'REPROVADO'
        tr.aprovado_por = usuario_id
        tr.data_aprovacao = datetime.utcnow()
        tr.parecer_comprador = parecer
        
        db.session.commit()
        
        # Notificar requisitante
        criar_notificacao(
            tr.criado_por,
            'TR_REPROVADO',
            'TR Reprovado',
            f'TR {tr.numero} foi reprovado pelo comprador. Motivo: {parecer}'
        )
        
        return jsonify({
            'success': True,
            'message': 'TR reprovado'
        })
        
    except Exception as e:
        logger.error(f"Erro ao reprovar TR: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao reprovar TR'
        }), 500

@app.route('/api/trs/<tr_id>/download', methods=['GET'])
@jwt_required()
def download_tr(tr_id):
    try:
        tr = TermoReferencia.query.get(tr_id)
        
        if not tr:
            return jsonify({
                'success': False,
                'error': 'TR não encontrado'
            }), 404
        
        # Gerar PDF
        pdf_buffer = gerar_pdf_tr(tr)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'TR_{tr.numero}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar PDF do TR: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar PDF'
        }), 500

# ========================================
# ROTAS DE PROCESSOS
# ========================================

@app.route('/api/processos', methods=['GET'])
@jwt_required()
def listar_processos():
    try:
        processos = Processo.query.all()
        
        return jsonify({
            'success': True,
            'processos': [p.to_dict() for p in processos]
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar processos: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

@app.route('/api/processos', methods=['POST'])
@jwt_required()
def criar_processo():
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'comprador':
            return jsonify({
                'success': False,
                'error': 'Apenas compradores podem criar processos'
            }), 403
        
        data = request.get_json()
        usuario_id = get_jwt_identity()
        
        # Gerar número do processo
        numero_processo = f"PROC-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}"
        
        processo = Processo(
            id=gerar_id(),
            numero=numero_processo,
            tr_id=data.get('trId'),
            objeto=data.get('objeto'),
            modalidade=data.get('modalidade'),
            data_abertura=datetime.fromisoformat(data.get('dataAbertura').replace('Z', '+00:00')) if data.get('dataAbertura') else None,
            data_limite=datetime.fromisoformat(data.get('dataLimite').replace('Z', '+00:00')) if data.get('dataLimite') else None,
            local_abertura=data.get('localAbertura'),
            criado_por=usuario_id
        )
        
        db.session.add(processo)
        
        # Adicionar fornecedores
        fornecedores = data.get('fornecedores', [])
        for f in fornecedores:
            fornecedor = ProcessoFornecedor(
                processo_id=processo.id,
                cnpj=f.get('cnpj'),
                razao_social=f.get('razaoSocial'),
                email=f.get('email'),
                login=gerar_login_fornecedor(f.get('cnpj')),
                senha=gerar_senha_aleatoria()
            )
            db.session.add(fornecedor)
        
        db.session.commit()
        
        # Notificar TR vinculado
        if processo.tr_id:
            tr = TermoReferencia.query.get(processo.tr_id)
            if tr:
                criar_notificacao(
                    tr.criado_por,
                    'PROCESSO_CRIADO',
                    'Processo Criado',
                    f'O processo {numero_processo} foi criado baseado no seu TR {tr.numero}'
                )
        
        return jsonify({
            'success': True,
            'message': 'Processo criado com sucesso',
            'processo': processo.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar processo: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao criar processo'
        }), 500

@app.route('/api/processos/fornecedor', methods=['GET'])
@jwt_required()
def listar_processos_fornecedor():
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'fornecedor':
            return jsonify({
                'success': False,
                'error': 'Acesso restrito a fornecedores'
            }), 403
        
        login_fornecedor = get_jwt_identity()
        
        # Buscar processos do fornecedor
        fornecedor = ProcessoFornecedor.query.filter_by(login=login_fornecedor).all()
        processos_ids = [f.processo_id for f in fornecedor]
        
        processos = Processo.query.filter(Processo.id.in_(processos_ids)).all()
        
        return jsonify({
            'success': True,
            'processos': [p.to_dict() for p in processos]
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar processos do fornecedor: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

# ========================================
# ROTAS DE PROPOSTAS
# ========================================

@app.route('/api/propostas', methods=['POST'])
@jwt_required()
def criar_proposta():
    try:
        claims = get_jwt()
        if claims.get('tipo') != 'fornecedor':
            return jsonify({
                'success': False,
                'error': 'Apenas fornecedores podem enviar propostas'
            }), 403
        
        data = request.get_json()
        login_fornecedor = get_jwt_identity()
        
        # Buscar dados do fornecedor
        fornecedor = ProcessoFornecedor.query.filter_by(login=login_fornecedor).first()
        
        if not fornecedor:
            return jsonify({
                'success': False,
                'error': 'Fornecedor não encontrado'
            }), 404
        
        proposta = Proposta(
            id=gerar_id(),
            processo_id=data.get('processoId'),
            fornecedor_login=login_fornecedor,
            empresa=fornecedor.razao_social,
            cnpj=fornecedor.cnpj,
            valor=data.get('valor'),
            prazo_execucao=data.get('prazoExecucao'),
            descricao_tecnica=data.get('descricaoTecnica'),
            observacoes=data.get('observacoes')
        )
        
        db.session.add(proposta)
        db.session.commit()
        
        # Notificar comprador
        processo = Processo.query.get(proposta.processo_id)
        if processo:
            criar_notificacao(
                processo.criado_por,
                'NOVA_PROPOSTA',
                'Nova Proposta Recebida',
                f'Nova proposta recebida de {fornecedor.razao_social} para o processo {processo.numero}'
            )
        
        return jsonify({
            'success': True,
            'message': 'Proposta enviada com sucesso',
            'proposta': proposta.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar proposta: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao enviar proposta'
        }), 500

@app.route('/api/propostas/processo/<processo_id>', methods=['GET'])
@jwt_required()
def listar_propostas_processo(processo_id):
    try:
        propostas = Proposta.query.filter_by(processo_id=processo_id).all()
        
        return jsonify({
            'success': True,
            'propostas': [p.to_dict() for p in propostas]
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

# ========================================
# ROTAS DE NOTIFICAÇÕES
# ========================================

@app.route('/api/notificacoes', methods=['GET'])
@jwt_required()
def listar_notificacoes():
    try:
        usuario_id = get_jwt_identity()
        
        notificacoes = Notificacao.query.filter_by(
            usuario_id=usuario_id
        ).order_by(Notificacao.data_criacao.desc()).limit(50).all()
        
        return jsonify({
            'success': True,
            'notificacoes': [n.to_dict() for n in notificacoes]
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar notificações: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

@app.route('/api/notificacoes/<int:notificacao_id>/lida', methods=['POST'])
@jwt_required()
def marcar_notificacao_lida(notificacao_id):
    try:
        usuario_id = get_jwt_identity()
        
        notificacao = Notificacao.query.filter_by(
            id=notificacao_id,
            usuario_id=usuario_id
        ).first()
        
        if not notificacao:
            return jsonify({
                'success': False,
                'error': 'Notificação não encontrada'
            }), 404
        
        notificacao.lida = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notificação marcada como lida'
        })
        
    except Exception as e:
        logger.error(f"Erro ao marcar notificação: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

# ========================================
# ROTAS DE STATUS E ARQUIVOS ESTÁTICOS
# ========================================

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/status')
def api_status():
    try:
        stats = {
            'processos_total': Processo.query.count(),
            'processos_ativos': Processo.query.filter_by(status='ATIVO').count(),
            'propostas_total': Proposta.query.count(),
            'usuarios_total': Usuario.query.count(),
            'usuarios_ativos': Usuario.query.filter_by(ativo=True).count(),
            'trs_total': TermoReferencia.query.count(),
            'trs_pendentes': TermoReferencia.query.filter_by(status='PENDENTE_APROVACAO').count()
        }
        
        return jsonify({
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "versao": "5.0",
            "ambiente": os.environ.get('FLASK_ENV', 'development'),
            "estatisticas": stats
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# ========================================
# INICIALIZAÇÃO DO BANCO
# ========================================

def popular_dados_iniciais():
    """Popula o banco com dados iniciais"""
    
    # Verificar se já existe dados
    if Usuario.query.count() > 0:
        return
    
    # Criar usuários
    usuarios = [
        {
            'id': 'req_001',
            'nome': 'Maria Santos',
            'email': 'maria.santos@empresa.com',
            'senha': 'requisitante123',
            'tipo': 'requisitante'
        },
        {
            'id': 'comp_001',
            'nome': 'João Silva',
            'email': 'joao.silva@empresa.com',
            'senha': 'comprador123',
            'tipo': 'comprador'
        },
        {
            'id': 'admin_001',
            'nome': 'Admin Sistema',
            'email': 'admin@sistema.com',
            'senha': 'admin123',
            'tipo': 'admin'
        }
    ]
    
    for u in usuarios:
        usuario = Usuario(
            id=u['id'],
            nome=u['nome'],
            email=u['email'],
            tipo=u['tipo']
        )
        usuario.set_senha(u['senha'])
        db.session.add(usuario)
    
    try:
        db.session.commit()
        logger.info("✅ Dados iniciais populados com sucesso!")
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Erro ao popular dados iniciais: {e}")

# ========================================
# INICIALIZAÇÃO
# ========================================

def init_app():
    with app.app_context():
        db.create_all()
        popular_dados_iniciais()

if __name__ == '__main__':
    init_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"🚀 Iniciando Sistema de Propostas v5.0")
    logger.info(f"📊 Ambiente: {os.environ.get('FLASK_ENV', 'development')}")
    logger.info(f"🔌 Porta: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
else:
    # Para Gunicorn
    init_app()
