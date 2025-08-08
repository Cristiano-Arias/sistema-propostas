#!/usr/bin/env python3
"""
Backend Completo - Sistema de Gestão de Propostas
Versão 5.0 - Totalmente Integrado
"""

import os
import json
import logging
from auth_routes import auth_bp
from security_middleware import init_security_middleware
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, session, send_file
from flask_cors import CORS
import jwt
import bcrypt
import sqlite3
from werkzeug.utils import secure_filename
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Configuração do Flask
app = Flask(__name__, static_folder='static')
app.register_blueprint(auth_bp)
init_security_middleware(app)

# Configurações
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Criar pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Extensões permitidas
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg'}

# Configuração CORS baseada no ambiente
if os.environ.get('FLASK_ENV') == 'production':
    # Em produção, restringir CORS a domínios específicos
    allowed_origins = [
        'https://sistema-propostas.onrender.com',
        'https://sistema-gestao-propostas.onrender.com'
    ]
    CORS(app, origins=allowed_origins)
else:
    # Em desenvolvimento, permitir qualquer origem
    CORS(app, origins=['https://SEU-DOMINIO.com'])

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar banco de dados SQLite
def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # ADICIONAR ESTA LINHA PARA FORÇAR RECRIAÇÃO:
    cursor.execute("DROP TABLE IF EXISTS usuarios")
    
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
    
    # Criar tabela de notificações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            lida INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Criar tabela de convites
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS convites_processo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_id INTEGER,
            fornecedor_id INTEGER,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (processo_id) REFERENCES processos (id),
            FOREIGN KEY (fornecedor_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Criar tabela de auditoria
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            acao TEXT NOT NULL,
            usuario_id INTEGER,
            ip TEXT,
            detalhes TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # Criar usuários de teste se não existirem
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        usuarios_teste = [
            ('Requisitante Teste', 'requisitante@empresa.com', 'req123', 'requisitante'),
            ('Comprador Teste', 'comprador@empresa.com', 'comp123', 'comprador'),
            ('Fornecedor Teste', 'fornecedor@empresa.com', 'forn123', 'fornecedor'),
            ('Forte & Oliveira Construções', 'wesley.lopes@forteoliveira.com', '123456', 'fornecedor'),
            ('Equilibra Construções LTDA', 'orcamento@equilibraengenharia.com.br', '123456', 'fornecedor'),
            ('GRAFYT ENGENHARIA LTDA', 'fbezerra@grafyt.com.br', '123456', 'fornecedor')
        ]
        
        for nome, email, senha, perfil in usuarios_teste:
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha, perfil)
                VALUES (?, ?, ?, ?)
            ''', (nome, email, senha_hash, perfil))
        
        conn.commit()
        logger.info("Usuários de teste criados")
    conn.close()
    logger.info("Banco de dados inicializado com sucesso")

# Inicializar banco ao iniciar
init_db()

# Helpers
def get_db():
    """Obter conexão com o banco"""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    """Verifica se o arquivo é permitido"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_auditoria(acao, usuario_id=None, detalhes=None, ip=None):
    """Registra ações importantes para auditoria"""
    try:
        timestamp = datetime.utcnow().isoformat()
        ip_address = ip or request.remote_addr if request else 'unknown'
        
        log_entry = {
            'timestamp': timestamp,
            'acao': acao,
            'usuario_id': usuario_id,
            'ip': ip_address,
            'detalhes': detalhes
        }
        
        logger.info(f"AUDITORIA: {json.dumps(log_entry)}")
        
        # Salvar no banco de dados para auditoria
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO auditoria (timestamp, acao, usuario_id, ip, detalhes)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, acao, usuario_id, ip_address, json.dumps(detalhes) if detalhes else None))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao registrar auditoria: {str(e)}")

def gerar_token(usuario_id, perfil):
    """Gera token JWT"""
    payload = {
        'usuario_id': usuario_id,
        'perfil': perfil,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm='HS256')

def verificar_token(token):
    """Verifica e decodifica token JWT"""
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Decorator para rotas protegidas
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'message': 'Token inválido'}), 401
        
        if not token:
            return jsonify({'message': 'Token ausente'}), 401
        
        payload = verificar_token(token)
        if not payload:
            return jsonify({'message': 'Token inválido ou expirado'}), 401
        
        request.usuario_id = payload['usuario_id']
        request.perfil = payload['perfil']
        
        return f(*args, **kwargs)
    
    return decorated_function


@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email') or data.get('login')  # ACEITAR AMBOS
        senha = data.get('senha')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = ?', (email,))
        usuario = cursor.fetchone()

        if not usuario:
            conn.close()
            return jsonify({'message': 'Usuário não encontrado'}), 404

        # Verificar senha (garante bytes vs str)
        hash_db = usuario['senha']
        if isinstance(hash_db, str):
            hash_db = hash_db.encode('utf-8')
        if not bcrypt.checkpw(senha.encode('utf-8'), hash_db):
            conn.close()
            return jsonify({'message': 'Senha incorreta'}), 401

        # Gerar token
        token = gerar_token(usuario['id'], usuario['perfil'])
        
        conn.close()
        
        # Log de sucesso
        log_auditoria('LOGIN_SUCESSO', usuario_id=usuario['id'], detalhes={'email': email, 'perfil': usuario['perfil']})
        
        return jsonify({
            'success': True,
            'message': 'Login OK',
            'token': token,              # compat com front antigo
            'access_token': token,       # compat com front novo
            'refresh_token': None,       # placeholder
            'usuario': {
                'id': usuario['id'],
                'nome': usuario['nome'],
                'email': usuario['email'],
                'perfil': usuario['perfil']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        return jsonify({'message': 'Erro interno'}), 500


@app.route('/api/auth/verify', methods=['GET'])
@require_auth
def verify_token():
    """Verifica se o token é válido"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, nome, email, perfil FROM usuarios WHERE id = ?', (request.usuario_id,))
    usuario = cursor.fetchone()
    
    conn.close()
    
    if usuario:
        return jsonify({
            'valid': True,
            'usuario': dict(usuario)
        }), 200
    else:
        return jsonify({'valid': False}), 401

# Rotas de Termos de Referência
@app.route('/api/trs', methods=['GET'])
@require_auth
def listar_trs():
    """Lista TRs do usuário ou todos se for comprador"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if request.perfil == 'requisitante':
            cursor.execute('''
                SELECT tr.*, u.nome as usuario_nome 
                FROM termos_referencia tr
                JOIN usuarios u ON tr.usuario_id = u.id
                WHERE tr.usuario_id = ?
                ORDER BY tr.criado_em DESC
            ''', (request.usuario_id,))
        else:  # comprador vê todos
            cursor.execute('''
                SELECT tr.*, u.nome as usuario_nome 
                FROM termos_referencia tr
                JOIN usuarios u ON tr.usuario_id = u.id
                ORDER BY tr.criado_em DESC
            ''')
        
        trs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(trs), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar TRs: {str(e)}")
        return jsonify({'message': 'Erro ao listar TRs'}), 500

@app.route('/api/trs', methods=['POST'])
@require_auth
def criar_tr():
    """Cria novo TR"""
    try:
        if request.perfil != 'requisitante':
            return jsonify({'message': 'Apenas requisitantes podem criar TRs'}), 403
        
        data = request.json
        numero = f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO termos_referencia (
                numero, titulo, objeto, justificativa, especificacoes,
                prazo_entrega, local_entrega, condicoes_pagamento,
                garantia, criterios_aceitacao, usuario_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            numero,
            data.get('titulo'),
            data.get('objeto'),
            data.get('justificativa'),
            data.get('especificacoes'),
            data.get('prazo_entrega'),
            data.get('local_entrega'),
            data.get('condicoes_pagamento'),
            data.get('garantia'),
            data.get('criterios_aceitacao'),
            request.usuario_id
        ))
        
        tr_id = cursor.lastrowid
        conn.commit()
        
        # Notificar compradores
        cursor.execute('SELECT id FROM usuarios WHERE perfil = ?', ('comprador',))
        compradores = cursor.fetchall()
        
        for comprador in compradores:
            cursor.execute('''
                INSERT INTO notificacoes (usuario_id, titulo, mensagem)
                VALUES (?, ?, ?)
            ''', (
                comprador['id'],
                'Novo TR para aprovação',
                f'O TR {numero} foi criado e aguarda sua aprovação'
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': tr_id,
            'numero': numero,
            'message': 'TR criado com sucesso'
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar TR: {str(e)}")
        return jsonify({'message': 'Erro ao criar TR'}), 500

@app.route('/api/trs/<int:tr_id>', methods=['GET'])
@require_auth
def obter_tr(tr_id):
    """Obtém TR específico"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tr.*, u.nome as usuario_nome 
            FROM termos_referencia tr
            JOIN usuarios u ON tr.usuario_id = u.id
            WHERE tr.id = ?
        ''', (tr_id,))
        
        tr = cursor.fetchone()
        conn.close()
        
        if not tr:
            return jsonify({'message': 'TR não encontrado'}), 404
        
        return jsonify(dict(tr)), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter TR: {str(e)}")
        return jsonify({'message': 'Erro ao obter TR'}), 500

@app.route('/api/trs/<int:tr_id>/aprovar', methods=['PUT'])
@require_auth
def aprovar_tr(tr_id):
    """Aprova TR"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Apenas compradores podem aprovar TRs'}), 403
        
        data = request.json
        parecer = data.get('parecer', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE termos_referencia 
            SET status = 'aprovado', parecer = ?
            WHERE id = ?
        ''', (parecer, tr_id))
        
        # Notificar requisitante
        cursor.execute('''
            SELECT usuario_id, numero FROM termos_referencia WHERE id = ?
        ''', (tr_id,))
        tr = cursor.fetchone()
        
        if tr:
            cursor.execute('''
                INSERT INTO notificacoes (usuario_id, titulo, mensagem)
                VALUES (?, ?, ?)
            ''', (
                tr['usuario_id'],
                'TR Aprovado',
                f'Seu TR {tr["numero"]} foi aprovado!'
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'TR aprovado com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao aprovar TR: {str(e)}")
        return jsonify({'message': 'Erro ao aprovar TR'}), 500

@app.route('/api/trs/<int:tr_id>/reprovar', methods=['PUT'])
@require_auth
def reprovar_tr(tr_id):
    """Reprova TR"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Apenas compradores podem reprovar TRs'}), 403
        
        data = request.json
        motivo = data.get('motivo', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE termos_referencia 
            SET status = 'reprovado', motivo_reprovacao = ?
            WHERE id = ?
        ''', (motivo, tr_id))
        
        # Notificar requisitante
        cursor.execute('''
            SELECT usuario_id, numero FROM termos_referencia WHERE id = ?
        ''', (tr_id,))
        tr = cursor.fetchone()
        
        if tr:
            cursor.execute('''
                INSERT INTO notificacoes (usuario_id, titulo, mensagem)
                VALUES (?, ?, ?)
            ''', (
                tr['usuario_id'],
                'TR Reprovado',
                f'Seu TR {tr["numero"]} foi reprovado. Motivo: {motivo}'
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'TR reprovado'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao reprovar TR: {str(e)}")
        return jsonify({'message': 'Erro ao reprovar TR'}), 500

@app.route('/api/trs/pendentes', methods=['GET'])
@require_auth
def listar_trs_pendentes():
    """Lista TRs pendentes de aprovação"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tr.*, u.nome as usuario_nome 
            FROM termos_referencia tr
            JOIN usuarios u ON tr.usuario_id = u.id
            WHERE tr.status = 'pendente'
            ORDER BY tr.criado_em DESC
        ''')
        
        trs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(trs), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar TRs pendentes: {str(e)}")
        return jsonify({'message': 'Erro ao listar TRs'}), 500

@app.route('/api/trs/aprovados', methods=['GET'])
@require_auth
def listar_trs_aprovados():
    """Lista TRs aprovados"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tr.*, u.nome as usuario_nome 
            FROM termos_referencia tr
            JOIN usuarios u ON tr.usuario_id = u.id
            WHERE tr.status = 'aprovado'
            ORDER BY tr.criado_em DESC
        ''')
        
        trs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(trs), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar TRs aprovados: {str(e)}")
        return jsonify({'message': 'Erro ao listar TRs'}), 500

@app.route('/api/trs/<int:tr_id>/pdf', methods=['GET'])
@require_auth
def download_tr_pdf(tr_id):
    """Download TR como PDF usando reportlab"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM termos_referencia WHERE id = ?', (tr_id,))
        tr = cursor.fetchone()
        
        if not tr:
            conn.close()
            return jsonify({'message': 'TR não encontrado'}), 404
        
        # Gerar PDF
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
        
        # Título
        elements.append(Paragraph("TERMO DE REFERÊNCIA", title_style))
        elements.append(Paragraph(f"{tr['numero']}", styles['Heading2']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Informações básicas
        data = [
            ['Campo', 'Valor'],
            ['Título', tr['titulo'] or ''],
            ['Objeto', tr['objeto'] or ''],
            ['Justificativa', tr['justificativa'] or ''],
            ['Prazo de Entrega', f"{tr['prazo_entrega']} dias" if tr['prazo_entrega'] else 'Não especificado'],
            ['Local de Entrega', tr['local_entrega'] or 'Não especificado'],
            ['Status', tr['status']],
            ['Data de Criação', tr['criado_em'] or '']
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
        
        # Construir PDF
        doc.build(elements)
        buffer.seek(0)
        
        conn.close()
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'TR_{tr["numero"]}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {str(e)}")
        return jsonify({'message': 'Erro ao gerar PDF'}), 500

# Rotas de Processos
@app.route('/api/processos', methods=['GET'])
@require_auth
def listar_processos():
    """Lista processos"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if request.perfil == 'comprador':
            cursor.execute('''
                SELECT p.*, tr.numero as tr_numero, u.nome as criador_nome
                FROM processos p
                LEFT JOIN termos_referencia tr ON p.tr_id = tr.id
                JOIN usuarios u ON p.criado_por = u.id
                ORDER BY p.criado_em DESC
            ''')
        elif request.perfil == 'fornecedor':
            # Fornecedor vê apenas processos para os quais foi convidado
            cursor.execute('''
                SELECT DISTINCT p.*, tr.numero as tr_numero, u.nome as criador_nome
                FROM processos p
                JOIN convites_processo cp ON p.id = cp.processo_id
                LEFT JOIN termos_referencia tr ON p.tr_id = tr.id
                JOIN usuarios u ON p.criado_por = u.id
                WHERE cp.fornecedor_id = ? AND p.status = 'aberto'
                ORDER BY p.criado_em DESC
            ''', (request.usuario_id,))
        else:
            conn.close()
            return jsonify([]), 200
        
        processos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(processos), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar processos: {str(e)}")
        return jsonify({'message': 'Erro ao listar processos'}), 500

@app.route('/api/processos', methods=['POST'])
@require_auth
def criar_processo():
    """Cria novo processo"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Apenas compradores podem criar processos'}), 403
        
        data = request.json
        numero = f"PROC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO processos (
                numero, tr_id, objeto, modalidade, data_abertura,
                hora_abertura, local_abertura, prazo_proposta,
                contato_email, contato_telefone, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            numero,
            data.get('tr_id'),
            data.get('objeto'),
            data.get('modalidade'),
            data.get('data_abertura'),
            data.get('hora_abertura'),
            data.get('local_abertura'),
            data.get('prazo_proposta'),
            data.get('contato_email'),
            data.get('contato_telefone'),
            request.usuario_id
        ))
        
        processo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': processo_id,
            'numero': numero,
            'message': 'Processo criado com sucesso'
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar processo: {str(e)}")
        return jsonify({'message': 'Erro ao criar processo'}), 500

@app.route('/api/processos/<int:processo_id>', methods=['GET'])
@require_auth
def obter_processo(processo_id):
    """Obtém processo específico"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, tr.numero as tr_numero, u.nome as criador_nome
            FROM processos p
            LEFT JOIN termos_referencia tr ON p.tr_id = tr.id
            JOIN usuarios u ON p.criado_por = u.id
            WHERE p.id = ?
        ''', (processo_id,))
        
        processo = cursor.fetchone()
        conn.close()
        
        if not processo:
            return jsonify({'message': 'Processo não encontrado'}), 404
        
        return jsonify(dict(processo)), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter processo: {str(e)}")
        return jsonify({'message': 'Erro ao obter processo'}), 500

@app.route('/api/processos/<int:processo_id>/convidar', methods=['POST'])
@require_auth
def convidar_fornecedores(processo_id):
    """Convida fornecedores para processo"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Apenas compradores podem convidar fornecedores'}), 403
        
        data = request.json
        fornecedores_ids = data.get('fornecedores', [])
        
        if not fornecedores_ids:
            return jsonify({'message': 'Selecione pelo menos um fornecedor'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verificar se processo existe
        cursor.execute('SELECT numero FROM processos WHERE id = ?', (processo_id,))
        processo = cursor.fetchone()
        
        if not processo:
            conn.close()
            return jsonify({'message': 'Processo não encontrado'}), 404
        
        # Inserir convites
        for fornecedor_id in fornecedores_ids:
            cursor.execute('''
                INSERT INTO convites_processo (processo_id, fornecedor_id)
                VALUES (?, ?)
            ''', (processo_id, fornecedor_id))
            
            # Notificar fornecedor
            cursor.execute('''
                INSERT INTO notificacoes (usuario_id, titulo, mensagem)
                VALUES (?, ?, ?)
            ''', (
                fornecedor_id,
                'Novo convite para processo',
                f'Você foi convidado para participar do processo {processo["numero"]}'
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'{len(fornecedores_ids)} fornecedores convidados com sucesso'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao convidar fornecedores: {str(e)}")
        return jsonify({'message': 'Erro ao convidar fornecedores'}), 500

@app.route('/api/processos/disponiveis', methods=['GET'])
@require_auth
def listar_processos_disponiveis():
    """Lista processos disponíveis para o fornecedor"""
    try:
        if request.perfil != 'fornecedor':
            return jsonify({'message': 'Acesso negado'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT p.*, tr.numero as tr_numero
            FROM processos p
            JOIN convites_processo cp ON p.id = cp.processo_id
            LEFT JOIN termos_referencia tr ON p.tr_id = tr.id
            WHERE cp.fornecedor_id = ? AND p.status = 'aberto'
            ORDER BY p.criado_em DESC
        ''', (request.usuario_id,))
        
        processos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(processos), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar processos disponíveis: {str(e)}")
        return jsonify({'message': 'Erro ao listar processos'}), 500

# Rotas de Propostas
@app.route('/api/propostas', methods=['GET'])
@require_auth
def listar_propostas():
    """Lista propostas"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if request.perfil == 'fornecedor':
            cursor.execute('''
                SELECT p.*, proc.numero as processo_numero
                FROM propostas p
                JOIN processos proc ON p.processo_id = proc.id
                WHERE p.fornecedor_id = ?
                ORDER BY p.criado_em DESC
            ''', (request.usuario_id,))
        elif request.perfil == 'comprador':
            cursor.execute('''
                SELECT p.*, proc.numero as processo_numero, u.nome as fornecedor_nome
                FROM propostas p
                JOIN processos proc ON p.processo_id = proc.id
                JOIN usuarios u ON p.fornecedor_id = u.id
                ORDER BY p.criado_em DESC
            ''')
        else:
            conn.close()
            return jsonify([]), 200
        
        propostas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(propostas), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {str(e)}")
        return jsonify({'message': 'Erro ao listar propostas'}), 500

@app.route('/api/propostas', methods=['POST'])
@require_auth
def criar_proposta():
    """Cria nova proposta"""
    try:
        if request.perfil != 'fornecedor':
            return jsonify({'message': 'Apenas fornecedores podem criar propostas'}), 403
        
        data = request.json
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verificar se foi convidado para o processo
        cursor.execute('''
            SELECT COUNT(*) FROM convites_processo
            WHERE processo_id = ? AND fornecedor_id = ?
        ''', (data.get('processo_id'), request.usuario_id))
        
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({'message': 'Você não foi convidado para este processo'}), 403
        
        cursor.execute('''
            INSERT INTO propostas (
                processo_id, fornecedor_id, valor_total,
                prazo_entrega, validade_proposta
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('processo_id'),
            request.usuario_id,
            data.get('valor_total'),
            data.get('prazo_entrega'),
            data.get('validade_proposta')
        ))
        
        proposta_id = cursor.lastrowid
        conn.commit()
        
        # Notificar comprador
        cursor.execute('''
            SELECT criado_por, numero FROM processos WHERE id = ?
        ''', (data.get('processo_id'),))
        processo = cursor.fetchone()
        
        if processo:
            cursor.execute('''
                INSERT INTO notificacoes (usuario_id, titulo, mensagem)
                VALUES (?, ?, ?)
            ''', (
                processo['criado_por'],
                'Nova proposta recebida',
                f'Uma nova proposta foi enviada para o processo {processo["numero"]}'
            ))
            conn.commit()
        
        conn.close()
        
        return jsonify({
            'id': proposta_id,
            'message': 'Proposta enviada com sucesso'
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar proposta: {str(e)}")
        return jsonify({'message': 'Erro ao criar proposta'}), 500

# Rotas de Fornecedores
@app.route('/api/fornecedores', methods=['GET'])
@require_auth
def listar_fornecedores():
    """Lista fornecedores"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, nome, email 
            FROM usuarios 
            WHERE perfil = 'fornecedor'
            ORDER BY nome
        ''')
        
        fornecedores = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(fornecedores), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar fornecedores: {str(e)}")
        return jsonify({'message': 'Erro ao listar fornecedores'}), 500

# Rotas de Notificações
@app.route('/api/notificacoes', methods=['GET'])
@require_auth
def listar_notificacoes():
    """Lista notificações do usuário"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM notificacoes
            WHERE usuario_id = ?
            ORDER BY criado_em DESC
            LIMIT 20
        ''', (request.usuario_id,))
        
        notificacoes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(notificacoes), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar notificações: {str(e)}")
        return jsonify({'message': 'Erro ao listar notificações'}), 500

@app.route('/api/notificacoes/<int:notif_id>/lida', methods=['PUT'])
@require_auth
def marcar_notificacao_lida(notif_id):
    """Marca notificação como lida"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notificacoes 
            SET lida = 1 
            WHERE id = ? AND usuario_id = ?
        ''', (notif_id, request.usuario_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Notificação marcada como lida'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao marcar notificação: {str(e)}")
        return jsonify({'message': 'Erro ao marcar notificação'}), 500

# ===== ROTAS PARA COMPARATIVO DE PROPOSTAS =====

@app.route('/api/comparativo/<int:processo_id>', methods=['GET'])
@require_auth
def get_comparativo_propostas(processo_id):
    """Busca todas as propostas de um processo para comparação"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Buscar informações do processo
        cursor.execute('''
            SELECT p.*, tr.numero as tr_numero, tr.objeto
            FROM processos p
            LEFT JOIN termos_referencia tr ON p.tr_id = tr.id
            WHERE p.id = ?
        ''', (processo_id,))
        
        processo = cursor.fetchone()
        if not processo:
            conn.close()
            return jsonify({'message': 'Processo não encontrado'}), 404
        
        # Buscar todas as propostas do processo
        cursor.execute('''
            SELECT p.*, u.nome as razao_social, u.email, u.telefone, u.endereco,
                   u.cnpj, u.responsavel_tecnico, u.crea
            FROM propostas p
            JOIN usuarios u ON p.fornecedor_id = u.id
            WHERE p.processo_id = ?
            ORDER BY p.criado_em ASC
        ''', (processo_id,))
        
        propostas_raw = cursor.fetchall()
        
        # Buscar dados detalhados de cada proposta
        propostas_formatadas = []
        for proposta in propostas_raw:
            proposta_dict = dict(proposta)
            
            # Buscar dados cadastrais
            proposta_dict['dadosCadastrais'] = {
                'razaoSocial': proposta['razao_social'],
                'cnpj': proposta['cnpj'] or 'Não informado',
                'endereco': proposta['endereco'] or 'Não informado',
                'cidade': 'Não informado',  # Adicionar campo cidade se necessário
                'telefone': proposta['telefone'] or 'Não informado',
                'email': proposta['email'],
                'respTecnico': proposta['responsavel_tecnico'] or 'Não informado',
                'crea': proposta['crea'] or 'Não informado'
            }
            
            # Buscar proposta técnica
            proposta_dict['propostaTecnica'] = buscar_proposta_tecnica(cursor, proposta['id'])
            
            # Buscar tabelas técnicas
            proposta_dict['servicosTecnica'] = buscar_servicos_tecnica(cursor, proposta['id'])
            proposta_dict['maoObraTecnica'] = buscar_mao_obra_tecnica(cursor, proposta['id'])
            proposta_dict['materiaisTecnica'] = buscar_materiais_tecnica(cursor, proposta['id'])
            proposta_dict['equipamentosTecnica'] = buscar_equipamentos_tecnica(cursor, proposta['id'])
            
            # Buscar tabelas comerciais
            proposta_dict['servicosComercial'] = buscar_servicos_comercial(cursor, proposta['id'])
            proposta_dict['maoObraComercial'] = buscar_mao_obra_comercial(cursor, proposta['id'])
            proposta_dict['materiaisComercial'] = buscar_materiais_comercial(cursor, proposta['id'])
            proposta_dict['equipamentosComercial'] = buscar_equipamentos_comercial(cursor, proposta['id'])
            
            # Buscar BDI
            proposta_dict['bdi'] = buscar_bdi(cursor, proposta['id'])
            
            # Calcular resumo financeiro
            proposta_dict['resumoFinanceiro'] = calcular_resumo_financeiro(proposta_dict)
            
            propostas_formatadas.append(proposta_dict)
        
        conn.close()
        
        return jsonify({
            'processo': {
                'id': processo['id'],
                'numero': processo['numero'],
                'tr_numero': processo['tr_numero'],
                'objeto': processo['objeto'],
                'status': processo['status']
            },
            'propostas': propostas_formatadas
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao buscar comparativo: {str(e)}")
        return jsonify({'message': 'Erro ao buscar dados do comparativo'}), 500

# ===== FUNÇÕES AUXILIARES PARA BUSCAR DADOS DAS PROPOSTAS =====

def buscar_proposta_tecnica(cursor, proposta_id):
    """Busca dados da proposta técnica"""
    cursor.execute('''
        SELECT * FROM proposta_tecnica WHERE proposta_id = ?
    ''', (proposta_id,))
    
    tecnica = cursor.fetchone()
    if not tecnica:
        return {
            'objetoConcorrencia': 'Não informado',
            'escopoInclusos': 'Não informado',
            'escopoExclusos': 'Não informado',
            'metodologia': 'Não informado',
            'sequenciaExecucao': 'Não informado',
            'prazoExecucao': 'Não informado',
            'prazoMobilizacao': 'Não informado',
            'garantias': 'Não informado',
            'estruturaCanteiro': 'Não informado',
            'obrigacoesContratada': 'Não informado',
            'obrigacoesContratante': 'Não informado'
        }
    
    return dict(tecnica)

def buscar_servicos_tecnica(cursor, proposta_id):
    """Busca tabela de serviços (quantidades)"""
    cursor.execute('''
        SELECT descricao, unidade, quantidade
        FROM servicos_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def buscar_mao_obra_tecnica(cursor, proposta_id):
    """Busca tabela de mão de obra (quantidades)"""
    cursor.execute('''
        SELECT funcao, quantidade, tempo
        FROM mao_obra_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def buscar_materiais_tecnica(cursor, proposta_id):
    """Busca tabela de materiais (quantidades)"""
    cursor.execute('''
        SELECT material, especificacao, unidade, quantidade
        FROM materiais_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def buscar_equipamentos_tecnica(cursor, proposta_id):
    """Busca tabela de equipamentos (quantidades)"""
    cursor.execute('''
        SELECT equipamento, especificacao, unidade, quantidade, tempo
        FROM equipamentos_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def buscar_servicos_comercial(cursor, proposta_id):
    """Busca tabela de serviços (valores)"""
    cursor.execute('''
        SELECT descricao, unidade, quantidade, preco_unitario, 
               (quantidade * preco_unitario) as total
        FROM servicos_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def buscar_mao_obra_comercial(cursor, proposta_id):
    """Busca tabela de mão de obra (custos)"""
    cursor.execute('''
        SELECT funcao, quantidade, tempo, salario, encargos_sociais,
               (quantidade * tempo * salario * (1 + encargos_sociais/100)) as total
        FROM mao_obra_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def buscar_materiais_comercial(cursor, proposta_id):
    """Busca tabela de materiais (custos)"""
    cursor.execute('''
        SELECT material, especificacao, unidade, quantidade, preco_unitario,
               (quantidade * preco_unitario) as total
        FROM materiais_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def buscar_equipamentos_comercial(cursor, proposta_id):
    """Busca tabela de equipamentos (custos)"""
    cursor.execute('''
        SELECT equipamento, especificacao, quantidade, tempo, preco_mensal,
               (quantidade * tempo * preco_mensal) as total
        FROM equipamentos_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def buscar_bdi(cursor, proposta_id):
    """Busca BDI detalhado"""
    cursor.execute('''
        SELECT item, percentual, valor
        FROM bdi_proposta 
        WHERE proposta_id = ?
        ORDER BY id
    ''', (proposta_id,))
    
    bdi_items = cursor.fetchall()
    if not bdi_items:
        # BDI padrão se não informado
        return [
            {'item': 'Administração Central', 'percentual': 0, 'valor': 0},
            {'item': 'Seguros e Garantias', 'percentual': 0, 'valor': 0},
            {'item': 'Riscos', 'percentual': 0, 'valor': 0},
            {'item': 'Despesas Financeiras', 'percentual': 0, 'valor': 0},
            {'item': 'Lucro', 'percentual': 0, 'valor': 0},
            {'item': 'Tributos (ISS, PIS, COFINS)', 'percentual': 0, 'valor': 0}
        ]
    
    return [dict(row) for row in bdi_items]

def calcular_resumo_financeiro(proposta_dict):
    """Calcula resumo financeiro da proposta"""
    try:
        # Somar totais de cada categoria
        total_servicos = sum(item.get('total', 0) for item in proposta_dict.get('servicosComercial', []))
        total_mao_obra = sum(item.get('total', 0) for item in proposta_dict.get('maoObraComercial', []))
        total_materiais = sum(item.get('total', 0) for item in proposta_dict.get('materiaisComercial', []))
        total_equipamentos = sum(item.get('total', 0) for item in proposta_dict.get('equipamentosComercial', []))
        
        custo_direto = total_servicos + total_mao_obra + total_materiais + total_equipamentos
        
        # Somar BDI
        bdi_valor = sum(item.get('valor', 0) for item in proposta_dict.get('bdi', []))
        bdi_percentual = (bdi_valor / custo_direto * 100) if custo_direto > 0 else 0
        
        valor_total = custo_direto + bdi_valor
        
        return {
            'totalServicos': total_servicos,
            'totalMaoObra': total_mao_obra,
            'totalMateriais': total_materiais,
            'totalEquipamentos': total_equipamentos,
            'custoDireto': custo_direto,
            'bdiPercentual': round(bdi_percentual, 1),
            'bdiValor': bdi_valor,
            'valorTotal': valor_total
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular resumo financeiro: {str(e)}")
        return {
            'totalServicos': 0,
            'totalMaoObra': 0,
            'totalMateriais': 0,
            'totalEquipamentos': 0,
            'custoDireto': 0,
            'bdiPercentual': 0,
            'bdiValor': 0,
            'valorTotal': 0
        }

# ===== ROTA PARA LISTAR PROCESSOS COM PROPOSTAS =====

@app.route('/api/processos/com-propostas', methods=['GET'])
@require_auth
def listar_processos_com_propostas():
    """Lista processos que têm propostas para comparação"""
    try:
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT p.id, p.numero, p.objeto, p.status,
                   COUNT(pr.id) as total_propostas,
                   tr.numero as tr_numero
            FROM processos p
            LEFT JOIN propostas pr ON p.id = pr.processo_id
            LEFT JOIN termos_referencia tr ON p.tr_id = tr.id
            WHERE pr.id IS NOT NULL
            GROUP BY p.id, p.numero, p.objeto, p.status, tr.numero
            HAVING COUNT(pr.id) >= 2
            ORDER BY p.criado_em DESC
        ''')
        
        processos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(processos), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar processos com propostas: {str(e)}")
        return jsonify({'message': 'Erro ao listar processos'}), 500

# ===== ATUALIZAÇÃO DO BANCO DE DADOS =====

def atualizar_schema_comparativo():
    """Atualiza schema do banco para suportar comparativo"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Tabela para proposta técnica
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proposta_tecnica (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposta_id INTEGER NOT NULL,
                objetoConcorrencia TEXT,
                escopoInclusos TEXT,
                escopoExclusos TEXT,
                metodologia TEXT,
                sequenciaExecucao TEXT,
                prazoExecucao TEXT,
                prazoMobilizacao TEXT,
                garantias TEXT,
                estruturaCanteiro TEXT,
                obrigacoesContratada TEXT,
                obrigacoesContratante TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proposta_id) REFERENCES propostas (id)
            )
        ''')
        
        # Tabela para serviços da proposta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servicos_proposta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposta_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                unidade TEXT NOT NULL,
                quantidade REAL NOT NULL,
                preco_unitario REAL DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proposta_id) REFERENCES propostas (id)
            )
        ''')
        
        # Tabela para mão de obra da proposta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mao_obra_proposta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposta_id INTEGER NOT NULL,
                funcao TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                tempo REAL NOT NULL,
                salario REAL DEFAULT 0,
                encargos_sociais REAL DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proposta_id) REFERENCES propostas (id)
            )
        ''')
        
        # Tabela para materiais da proposta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materiais_proposta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposta_id INTEGER NOT NULL,
                material TEXT NOT NULL,
                especificacao TEXT,
                unidade TEXT NOT NULL,
                quantidade REAL NOT NULL,
                preco_unitario REAL DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proposta_id) REFERENCES propostas (id)
            )
        ''')
        
        # Tabela para equipamentos da proposta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipamentos_proposta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposta_id INTEGER NOT NULL,
                equipamento TEXT NOT NULL,
                especificacao TEXT,
                unidade TEXT NOT NULL,
                quantidade REAL NOT NULL,
                tempo REAL NOT NULL,
                preco_mensal REAL DEFAULT 0,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proposta_id) REFERENCES propostas (id)
            )
        ''')
        
        # Tabela para BDI da proposta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bdi_proposta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposta_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                percentual REAL NOT NULL,
                valor REAL NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proposta_id) REFERENCES propostas (id)
            )
        ''')
        
        # Adicionar campos extras na tabela usuarios para dados cadastrais
        try:
            cursor.execute('ALTER TABLE usuarios ADD COLUMN cnpj TEXT')
        except:
            pass  # Campo já existe
            
        try:
            cursor.execute('ALTER TABLE usuarios ADD COLUMN endereco TEXT')
        except:
            pass
            
        try:
            cursor.execute('ALTER TABLE usuarios ADD COLUMN telefone TEXT')
        except:
            pass
            
        try:
            cursor.execute('ALTER TABLE usuarios ADD COLUMN responsavel_tecnico TEXT')
        except:
            pass
            
        try:
            cursor.execute('ALTER TABLE usuarios ADD COLUMN crea TEXT')
        except:
            pass
        
        conn.commit()
        logger.info("Schema do comparativo atualizado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar schema: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

atualizar_schema_comparativo()

# Health Check
@app.route('/health')
def health_check():
    """Health check endpoint para monitoramento"""
    try:
        # Verificar conexão com banco de dados
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '5.0',
            'database': 'connected'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503

# Rotas de Administração de Usuários
@app.route('/api/admin/usuarios', methods=['GET'])
@require_auth
def listar_usuarios():
    """Lista todos os usuários (apenas para administradores)"""
    try:
        # Verificar se é administrador (comprador com permissões especiais)
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, nome, email, perfil, criado_em 
            FROM usuarios 
            ORDER BY criado_em DESC
        ''')
        usuarios = cursor.fetchall()
        
        usuarios_list = []
        for usuario in usuarios:
            usuarios_list.append({
                'id': usuario['id'],
                'nome': usuario['nome'],
                'email': usuario['email'],
                'perfil': usuario['perfil'],
                'criado_em': usuario['criado_em']
            })
        
        conn.close()
        log_auditoria('LISTAR_USUARIOS', usuario_id=request.usuario_id)
        
        return jsonify({'usuarios': usuarios_list}), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {str(e)}")
        return jsonify({'message': 'Erro interno'}), 500

@app.route('/api/admin/usuarios', methods=['POST'])
@require_auth
def criar_usuario():
    """Cria novo usuário (apenas para administradores)"""
    try:
        # Verificar se é administrador
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        data = request.json
        nome = data.get('nome')
        email = data.get('email')
        perfil = data.get('perfil')
        senha_temporaria = data.get('senha', 'temp123456')  # Senha temporária padrão
        
        if not all([nome, email, perfil]):
            return jsonify({'message': 'Nome, email e perfil são obrigatórios'}), 400
        
        if perfil not in ['requisitante', 'comprador', 'fornecedor']:
            return jsonify({'message': 'Perfil inválido'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verificar se email já existe
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'message': 'Email já cadastrado'}), 409
        
        # Criptografar senha
        senha_hash = bcrypt.hashpw(senha_temporaria.encode('utf-8'), bcrypt.gensalt())
        
        # Inserir usuário
        cursor.execute('''
            INSERT INTO usuarios (nome, email, senha, perfil)
            VALUES (?, ?, ?, ?)
        ''', (nome, email, senha_hash, perfil))
        
        usuario_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_auditoria('CRIAR_USUARIO', usuario_id=request.usuario_id, 
                     detalhes={'novo_usuario_id': usuario_id, 'email': email, 'perfil': perfil})
        
        return jsonify({
            'message': 'Usuário criado com sucesso',
            'usuario_id': usuario_id,
            'senha_temporaria': senha_temporaria
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {str(e)}")
        return jsonify({'message': 'Erro interno'}), 500

@app.route('/api/admin/usuarios/<int:usuario_id>', methods=['PUT'])
@require_auth
def atualizar_usuario(usuario_id):
    """Atualiza dados de usuário (apenas para administradores)"""
    try:
        # Verificar se é administrador
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        data = request.json
        nome = data.get('nome')
        email = data.get('email')
        perfil = data.get('perfil')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verificar se usuário existe
        cursor.execute('SELECT id FROM usuarios WHERE id = ?', (usuario_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'message': 'Usuário não encontrado'}), 404
        
        # Atualizar campos fornecidos
        updates = []
        params = []
        
        if nome:
            updates.append('nome = ?')
            params.append(nome)
        if email:
            updates.append('email = ?')
            params.append(email)
        if perfil and perfil in ['requisitante', 'comprador', 'fornecedor']:
            updates.append('perfil = ?')
            params.append(perfil)
        
        if not updates:
            conn.close()
            return jsonify({'message': 'Nenhum campo para atualizar'}), 400
        
        params.append(usuario_id)
        query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?"
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        log_auditoria('ATUALIZAR_USUARIO', usuario_id=request.usuario_id,
                     detalhes={'usuario_atualizado': usuario_id, 'campos': updates})
        
        return jsonify({'message': 'Usuário atualizado com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário: {str(e)}")
        return jsonify({'message': 'Erro interno'}), 500

@app.route('/api/admin/usuarios/<int:usuario_id>/reset-senha', methods=['POST'])
@require_auth
def resetar_senha(usuario_id):
    """Reseta senha de usuário (apenas para administradores)"""
    try:
        # Verificar se é administrador
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        nova_senha = 'temp123456'  # Senha temporária padrão
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verificar se usuário existe
        cursor.execute('SELECT email FROM usuarios WHERE id = ?', (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            conn.close()
            return jsonify({'message': 'Usuário não encontrado'}), 404
        
        # Criptografar nova senha
        senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt())
        
        # Atualizar senha
        cursor.execute('UPDATE usuarios SET senha = ? WHERE id = ?', (senha_hash, usuario_id))
        conn.commit()
        conn.close()
        
        log_auditoria('RESET_SENHA', usuario_id=request.usuario_id,
                     detalhes={'usuario_resetado': usuario_id, 'email': usuario['email']})
        
        return jsonify({
            'message': 'Senha resetada com sucesso',
            'nova_senha': nova_senha
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao resetar senha: {str(e)}")
        return jsonify({'message': 'Erro interno'}), 500

@app.route('/api/admin/usuarios/<int:usuario_id>', methods=['DELETE'])
@require_auth
def desativar_usuario(usuario_id):
    """Desativa usuário (apenas para administradores)"""
    try:
        # Verificar se é administrador
        if request.perfil != 'comprador':
            return jsonify({'message': 'Acesso negado'}), 403
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verificar se usuário existe
        cursor.execute('SELECT email FROM usuarios WHERE id = ?', (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            conn.close()
            return jsonify({'message': 'Usuário não encontrado'}), 404
        
        # Em vez de deletar, podemos adicionar um campo 'ativo' ou prefixar email
        cursor.execute('''
            UPDATE usuarios 
            SET email = 'DESATIVADO_' || email || '_' || datetime('now')
            WHERE id = ?
        ''', (usuario_id,))
        
        conn.commit()
        conn.close()
        
        log_auditoria('DESATIVAR_USUARIO', usuario_id=request.usuario_id,
                     detalhes={'usuario_desativado': usuario_id, 'email': usuario['email']})
        
        return jsonify({'message': 'Usuário desativado com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao desativar usuário: {str(e)}")
        return jsonify({'message': 'Erro interno'}), 500

# Rotas específicas para os dashboards
@app.route('/static/dashboard-fornecedor.html')
def dashboard_fornecedor():
    """Serve dashboard do fornecedor"""
    return send_from_directory('static', 'dashboard-fornecedor.html')

@app.route('/static/dashboard-requisitante.html')
def dashboard_requisitante():
    """Serve dashboard do requisitante"""
    return send_from_directory('static', 'dashboard-requisitante.html')

@app.route('/static/dashboard-comprador.html')
def dashboard_comprador():
    """Serve dashboard do comprador"""
    return send_from_directory('static', 'dashboard-comprador.html')

# Rotas de arquivos estáticos
@app.route('/')
def index():
    """Rota principal"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve arquivos estáticos com mapeamento"""
    # Mapeamento de nomes CORRETOS
    file_mapping = {
        'dashboard-fornecedor.html': 'dashboard-fornecedor-funcional.html',
        'dashboard-comprador.html': 'dashboard-comprador-funcional.html',
        'dashboard-requisitante.html': 'dashboard-requisitante-funcional.html',
    }
    
    # Verifica se precisa mapear
    if path in file_mapping:
        path = file_mapping[path]
    
    # Remove 'static/' do início se existir
    if path.startswith('static/'):
        path = path[7:]
    
    # Tenta servir o arquivo
    if path and os.path.exists(os.path.join('static', path)):
        return send_from_directory('static', path)
    else:
        return send_from_directory('static', 'index.html')

# Tratamento de erros
@app.errorhandler(404)
def not_found(error):
    """Erro 404"""
    return jsonify({'message': 'Recurso não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Erro 500"""
    logger.error(f"Erro interno: {str(error)}")
    return jsonify({'message': 'Erro interno do servidor'}), 500

# Inicialização
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Iniciando servidor na porta {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
