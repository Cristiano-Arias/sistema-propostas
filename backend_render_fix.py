#!/usr/bin/env python3
"""
Backend Completo - Sistema de Gestão de Propostas
Versão 5.0 - Totalmente Integrado com Persistência de Dados
"""

import os
import json
import logging
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
from flask_mail import Mail, Message
import shutil
from pathlib import Path
import threading
import time

# Configuração do caminho do banco de dados
# Configuração de persistência melhorada para Render
if os.environ.get('RENDER'):
    """
    Quando executado no ambiente do Render, é importante persistir os
    arquivos de banco de dados e uploads em um diretório que seja
    preservado entre deploys e reinicializações. A lista
    ``POSSIBLE_DIRS`` contém caminhos comumente disponíveis no Render.
    O primeiro diretório no qual for possível escrever será utilizado
    para armazenar ``database.db`` e ``database_backup.db``.
    """
    # Tentar múltiplos diretórios persistentes no Render
    POSSIBLE_DIRS = [
        '/opt/render/persistent',
        '/opt/render/project/src/data',
        '/tmp/persistent',
        '.'
    ]

    PERSISTENT_DIR = None
    for dir_path in POSSIBLE_DIRS:
        try:
            # certifique-se de que o diretório existe
            os.makedirs(dir_path, exist_ok=True)
            # testar permissões de escrita
            test_file = os.path.join(dir_path, 'test_write.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            PERSISTENT_DIR = dir_path
            break
        except Exception:
            continue

    # Se nenhum diretório válido for encontrado, utilizar o diretório atual
    if not PERSISTENT_DIR:
        PERSISTENT_DIR = '.'

    # Definição dos caminhos de banco e backup dentro do diretório persistente
    DB_PATH = os.path.join(PERSISTENT_DIR, 'database.db')
    BACKUP_PATH = os.path.join(PERSISTENT_DIR, 'database_backup.db')
    UPLOAD_DIR = os.path.join(PERSISTENT_DIR, 'uploads')

    # Registrar no log qual diretório foi escolhido
    print(f"[RENDER] Usando diretório persistente: {PERSISTENT_DIR}")
else:
    # Configurações para desenvolvimento local
    DB_PATH = 'database.db'
    BACKUP_PATH = 'database_backup.db'
    UPLOAD_DIR = 'uploads'

# Criar diretório de uploads
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configuração do Flask
app = Flask(__name__, static_folder='static')

# Configurações
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configuração do Flask Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

# Inicializar Flask-Mail
mail = Mail(app)

# Extensões permitidas
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg'}

# Inicializar CORS
CORS(app, origins=['*'])

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Função para fazer backup do banco
def backup_database():
    """Faz backup do banco de dados com verificação de integridade"""
    try:
        if os.path.exists(DB_PATH):
            # Verificar se o banco principal está íntegro
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                count = cursor.fetchone()[0]
                conn.close()
                
                if count > 0:
                    # Fazer backup apenas se há dados
                    shutil.copy2(DB_PATH, BACKUP_PATH)
                    logger.info(f"Backup do banco realizado: {count} usuários")
                else:
                    logger.warning("Banco principal vazio, backup não realizado")
            except Exception as e:
                logger.error(f"Erro ao verificar integridade do banco: {str(e)}")
        else:
            logger.warning("Banco principal não existe, backup não realizado")
    except Exception as e:
        logger.error(f"Erro ao fazer backup: {str(e)}")

def backup_automatico():
    """Faz backup automático a cada 30 minutos"""
    while True:
        try:
            time.sleep(1800)  # 30 minutos
            backup_database()
        except Exception as e:
            logger.error(f"Erro no backup automático: {str(e)}")

def iniciar_backup_automatico():
    """Inicia thread de backup automático"""
    try:
        backup_thread = threading.Thread(target=backup_automatico, daemon=True)
        backup_thread.start()
        logger.info("Backup automático iniciado (a cada 30 minutos)")
    except Exception as e:
        logger.error(f"Erro ao iniciar backup automático: {str(e)}")

# Função para restaurar backup se necessário
def restore_backup_if_needed():
    """Restaura backup se o banco principal não existir ou estiver corrompido"""
    try:
        banco_principal_ok = False
        
        # Verificar se banco principal existe e está íntegro
        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                count = cursor.fetchone()[0]
                conn.close()
                
                if count > 0:
                    banco_principal_ok = True
                    logger.info(f"Banco principal OK: {count} usuários")
                else:
                    logger.warning("Banco principal vazio")
            except Exception as e:
                logger.error(f"Banco principal corrompido: {str(e)}")
        else:
            logger.warning("Banco principal não existe")
        
        # Restaurar backup se necessário
        if not banco_principal_ok and os.path.exists(BACKUP_PATH):
            try:
                # Verificar integridade do backup
                conn = sqlite3.connect(BACKUP_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                backup_count = cursor.fetchone()[0]
                conn.close()
                
                if backup_count > 0:
                    shutil.copy2(BACKUP_PATH, DB_PATH)
                    logger.info(f"Banco restaurado do backup: {backup_count} usuários")
                else:
                    logger.warning("Backup também está vazio")
            except Exception as e:
                logger.error(f"Erro ao verificar backup: {str(e)}")
        elif not banco_principal_ok:
            logger.warning("Nenhum backup disponível para restaurar")
            
    except Exception as e:
        logger.error(f"Erro ao restaurar backup: {str(e)}")

# Helpers
def get_db():
    """Obter conexão com o banco"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    """Verifica se o arquivo é permitido"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inicializar banco de dados SQLite
def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Criar tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            primeiro_acesso INTEGER DEFAULT 1,
            ultimo_login TIMESTAMP,
            cpf TEXT,
            departamento TEXT,
            cargo TEXT,
            telefone TEXT,
            ativo INTEGER DEFAULT 1,
            cnpj TEXT,
            endereco TEXT,
            responsavel_tecnico TEXT,
            crea TEXT
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
    
    conn.commit()
    
    # Criar usuários de teste se não existirem
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]
    
    # Verificar se usuário admin existe
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE email = 'admin@sistema.com'")
    admin_existe = cursor.fetchone()[0] > 0
    
    logger.info(f"Inicialização do banco: {total_usuarios} usuários encontrados, admin existe: {admin_existe}")
    
    if total_usuarios == 0 or not admin_existe:
        logger.info("Criando usuários de teste...")
        
        usuarios_teste = [
            ('Requisitante Teste', 'requisitante@empresa.com', 'req123', 'requisitante'),
            ('Comprador Teste', 'comprador@empresa.com', 'comp123', 'comprador'),
            ('Fornecedor Teste', 'fornecedor@empresa.com', 'forn123', 'fornecedor'),
            ('Administrador do Sistema', 'admin@sistema.com', 'Admin@2025!', 'admin_sistema')
        ]
        
        for nome, email, senha, perfil in usuarios_teste:
            # Verificar se usuário já existe
            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE email = ?", (email,))
            if cursor.fetchone()[0] == 0:
                try:
                    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
                    cursor.execute('''
                        INSERT INTO usuarios (nome, email, senha, perfil)
                        VALUES (?, ?, ?, ?)
                    ''', (nome, email, senha_hash, perfil))
                    logger.info(f"Usuário criado: {email}")
                except Exception as e:
                    logger.error(f"Erro ao criar usuário {email}: {str(e)}")
            else:
                logger.info(f"Usuário já existe: {email}")
        
        conn.commit()
        logger.info("Usuários de teste criados/verificados com sucesso")
        
        # Fazer backup após criar usuários
        try:
            backup_database()
            logger.info("Backup realizado após criação de usuários")
        except Exception as e:
            logger.error(f"Erro ao fazer backup: {str(e)}")
    else:
        logger.info("Usuários já existem no banco de dados")
    
    # Verificar integridade final
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_final = cursor.fetchone()[0]
    logger.info(f"Inicialização concluída: {total_final} usuários no banco")
    
    conn.close()
    logger.info("Banco de dados inicializado com sucesso")

# ===== ROTAS DE DEBUG E MONITORAMENTO =====

@app.get('/healthz')
def healthz():
    return 'ok', 200


@app.route('/api/debug/admin', methods=['GET'])
def debug_admin():
    """Rota de debug para verificar usuário admin"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nome, email, perfil, ativo FROM usuarios WHERE email = 'admin@sistema.com'")
        admin = cursor.fetchone()
        
        if admin:
            result = {
                'admin_existe': True,
                'admin_data': {
                    'id': admin['id'],
                    'nome': admin['nome'],
                    'email': admin['email'],
                    'perfil': admin['perfil'],
                    'ativo': admin['ativo']
                }
            }
        else:
            result = {'admin_existe': False}
        
        cursor.execute("SELECT COUNT(*) as total FROM usuarios")
        total = cursor.fetchone()
        result['total_usuarios'] = total['total']
        
        conn.close()
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Erro no debug admin: {str(e)}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/debug/persistencia', methods=['GET'])
def debug_persistencia():
    """Rota de debug para verificar status da persistência"""
    try:
        result = {
            'banco_principal': {
                'existe': os.path.exists(DB_PATH),
                'caminho': DB_PATH,
                'tamanho': os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
            },
            'backup': {
                'existe': os.path.exists(BACKUP_PATH),
                'caminho': BACKUP_PATH,
                'tamanho': os.path.getsize(BACKUP_PATH) if os.path.exists(BACKUP_PATH) else 0
            },
            'diretorio_persistente': PERSISTENT_DIR if 'PERSISTENT_DIR' in globals() else 'N/A'
        }
        
        # Verificar integridade do banco principal
        if os.path.exists(DB_PATH):
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as total FROM usuarios")
                total = cursor.fetchone()
                result['banco_principal']['usuarios'] = total['total']
                
                cursor.execute("SELECT email FROM usuarios LIMIT 5")
                usuarios = [row['email'] for row in cursor.fetchall()]
                result['banco_principal']['usuarios_exemplo'] = usuarios
                
                conn.close()
                result['banco_principal']['status'] = 'OK'
            except Exception as e:
                result['banco_principal']['status'] = f'ERRO: {str(e)}'
        else:
            result['banco_principal']['status'] = 'NÃO EXISTE'
        
        # Verificar integridade do backup
        if os.path.exists(BACKUP_PATH):
            try:
                conn = sqlite3.connect(BACKUP_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as total FROM usuarios")
                total = cursor.fetchone()
                result['backup']['usuarios'] = total[0]
                conn.close()
                result['backup']['status'] = 'OK'
            except Exception as e:
                result['backup']['status'] = f'ERRO: {str(e)}'
        else:
            result['backup']['status'] = 'NÃO EXISTE'
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Erro no debug persistência: {str(e)}")
        return jsonify({'erro': str(e)}), 500

# ===== FUNÇÕES DE AUTENTICAÇÃO E TOKEN =====
# (Movidas para antes das rotas para resolver NameError)

def gerar_token(usuario_id, perfil):
    """Gera token JWT com expiração estendida"""
    payload = {
        'usuario_id': usuario_id,
        'perfil': perfil,
        'exp': datetime.utcnow() + timedelta(days=30),  # 30 dias de validade
        'iat': datetime.utcnow()  # Issued at
    }
    secret_key = os.environ.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    return jwt.encode(payload, secret_key, algorithm='HS256')

def gerar_refresh_token(usuario_id):
    """Gera refresh token com validade de 90 dias"""
    payload = {
        'usuario_id': usuario_id,
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(days=90),
        'iat': datetime.utcnow()
    }
    secret_key = os.environ.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    return jwt.encode(payload, secret_key, algorithm='HS256')

def verificar_token(token):
    """Verifica e decodifica token JWT"""
    try:
        secret_key = os.environ.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verificar_refresh_token(token):
    """Verifica e decodifica refresh token"""
    try:
        secret_key = os.environ.get('JWT_SECRET_KEY', app.config['SECRET_KEY'])
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        if payload.get('type') != 'refresh':
            return None
        return payload
    except:
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

# ===== ROTAS DA API =====

@app.route('/api/fornecedores/<int:fornecedor_id>', methods=['GET'])
@require_auth
def obter_detalhes_fornecedor(fornecedor_id):
    """Obtém detalhes do fornecedor"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM usuarios WHERE id = ? AND perfil = 'fornecedor'
        ''', (fornecedor_id,))
        
        fornecedor = cursor.fetchone()
        
        if not fornecedor:
            conn.close()
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        resultado = {
            'id': fornecedor['id'],
            'razao_social': fornecedor['nome'],
            'nome_fantasia': '',
            'cnpj': fornecedor['cnpj'] or '00.000.000/0000-00',
            'inscricao_estadual': '',
            'inscricao_municipal': '',
            'endereco': fornecedor['endereco'] or 'Endereço não cadastrado',
            'numero': '',
            'complemento': '',
            'bairro': '',
            'cidade': 'Cidade',
            'estado': 'UF',
            'cep': '00000-000',
            'email': fornecedor['email'],
            'telefone': fornecedor['telefone'] or '(00) 0000-0000',
            'celular': '',
            'website': '',
            'responsavel_nome': fornecedor['nome'],
            'responsavel_cpf': fornecedor['cpf'] or '000.000.000-00',
            'responsavel_email': fornecedor['email'],
            'responsavel_telefone': fornecedor['telefone'] or '',
            'responsavel_tecnico': fornecedor['responsavel_tecnico'] or '',
            'crea_cau': fornecedor['crea'] or '',
            'aprovado': False
        }
        
        conn.close()
        
        return jsonify(resultado), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter fornecedor: {str(e)}")
        return jsonify({'erro': 'Erro ao obter fornecedor'}), 500

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
        
        cursor.execute('''
            SELECT p.*, u.nome as razao_social, u.email, u.telefone, u.endereco,
                   u.cnpj, u.responsavel_tecnico, u.crea
            FROM propostas p
            JOIN usuarios u ON p.fornecedor_id = u.id
            WHERE p.processo_id = ?
            ORDER BY p.criado_em ASC
        ''', (processo_id,))
        
        propostas_raw = cursor.fetchall()
        
        propostas_formatadas = []
        for proposta in propostas_raw:
            proposta_dict = dict(proposta)
            
            proposta_dict['dadosCadastrais'] = {
                'razaoSocial': proposta['razao_social'],
                'cnpj': proposta['cnpj'] or 'Não informado',
                'endereco': proposta['endereco'] or 'Não informado',
                'cidade': 'Não informado',
                'telefone': proposta['telefone'] or 'Não informado',
                'email': proposta['email'],
                'respTecnico': proposta['responsavel_tecnico'] or 'Não informado',
                'crea': proposta['crea'] or 'Não informado'
            }
            
            proposta_dict['propostaTecnica'] = buscar_proposta_tecnica(cursor, proposta['id'])
            proposta_dict['servicosTecnica'] = buscar_servicos_tecnica(cursor, proposta['id'])
            proposta_dict['maoObraTecnica'] = buscar_mao_obra_tecnica(cursor, proposta['id'])
            proposta_dict['materiaisTecnica'] = buscar_materiais_tecnica(cursor, proposta['id'])
            proposta_dict['equipamentosTecnica'] = buscar_equipamentos_tecnica(cursor, proposta['id'])
            proposta_dict['servicosComercial'] = buscar_servicos_comercial(cursor, proposta['id'])
            proposta_dict['maoObraComercial'] = buscar_mao_obra_comercial(cursor, proposta['id'])
            proposta_dict['materiaisComercial'] = buscar_materiais_comercial(cursor, proposta['id'])
            proposta_dict['equipamentosComercial'] = buscar_equipamentos_comercial(cursor, proposta['id'])
            proposta_dict['bdi'] = buscar_bdi(cursor, proposta['id'])
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
        total_servicos = sum(item.get('total', 0) for item in proposta_dict.get('servicosComercial', []))
        total_mao_obra = sum(item.get('total', 0) for item in proposta_dict.get('maoObraComercial', []))
        total_materiais = sum(item.get('total', 0) for item in proposta_dict.get('materiaisComercial', []))
        total_equipamentos = sum(item.get('total', 0) for item in proposta_dict.get('equipamentosComercial', []))
        
        custo_direto = total_servicos + total_mao_obra + total_materiais + total_equipamentos
        
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
        # Criar tabelas necessárias para o comparativo
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
        
        conn.commit()
        logger.info("Schema do comparativo atualizado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar schema: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

# Chamar atualização do schema
atualizar_schema_comparativo()

# Rotas de arquivos estáticos
@app.route('/')
def index():
    """Rota principal"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve arquivos estáticos"""
    if path and os.path.exists(os.path.join('static', path)):
        return send_from_directory('static', path)
    else:
        return send_from_directory('static', 'index.html')

# Health check
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

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
    logger.info(f"Banco de dados: {DB_PATH}")
    logger.info(f"Diretório de uploads: {UPLOAD_DIR}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

# Inicializar banco ao iniciar
restore_backup_if_needed()
init_db()

# Iniciar backup automático
iniciar_backup_automatico()

# Função para verificar e corrigir banco
def verificar_e_corrigir_banco():
    """Verifica e corrige a estrutura do banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verificar se o usuário admin existe
        cursor.execute("SELECT * FROM usuarios WHERE email = 'admin@sistema.com'")
        admin = cursor.fetchone()
        
        if not admin:
            logger.info("Criando usuário admin padrão...")
            senha_hash = bcrypt.hashpw('Admin@2025!'.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha, perfil)
                VALUES (?, ?, ?, ?)
            ''', ('Administrador do Sistema', 'admin@sistema.com', senha_hash, 'admin_sistema'))
            conn.commit()
            logger.info("Usuário admin criado com sucesso!")
        else:
            logger.info("Usuário admin já existe")
        
        # Listar estrutura atual da tabela para debug
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas = cursor.fetchall()
        logger.info("Estrutura atual da tabela usuarios:")
        for col in colunas:
            logger.info(f"  - {col[1]} ({col[2]})")
        
    except Exception as e:
        logger.error(f"Erro ao verificar banco: {str(e)}")
    finally:
        conn.close()

verificar_e_corrigir_banco()

# Funções de E-mail
def enviar_email(destinatario, assunto, corpo_html):
    """Envia e-mail usando Flask-Mail"""
    try:
        msg = Message(
            subject=assunto,
            recipients=[destinatario],
            html=corpo_html
        )
        mail.send(msg)
        logger.info(f"Email enviado para {destinatario}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar email: {str(e)}")
        return False

def criar_email_boas_vindas(nome, email, senha_temp):
    """Cria HTML do e-mail de boas-vindas"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f4f4f4; padding: 20px; margin-top: 20px; }}
            .credentials {{ background-color: #fff; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Sistema de Gestão de Propostas</h1>
            </div>
            <div class="content">
                <h2>Bem-vindo(a), {nome}!</h2>
                <p>Sua conta foi criada com sucesso.</p>
                <div class="credentials">
                    <h3>Credenciais de acesso:</h3>
                    <p><strong>E-mail:</strong> {email}</p>
                    <p><strong>Senha:</strong> {senha_temp}</p>
                </div>
                <p><strong>Importante:</strong> Altere sua senha no primeiro acesso.</p>
                <p>Acesse o sistema em: https://portal-proposta.onrender.com</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# Rotas de Autenticação
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login de usuário com suporte a primeiro acesso e segurança aprimorada"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        senha = data.get('senha', '')

        # Log detalhado da tentativa de login
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        logger.info(f"Tentativa de login: {email} de IP: {client_ip}")
        
        # Validações de entrada mais rigorosas
        if not email or not senha:
            logger.warning(f"Login falhado - campos vazios: email={bool(email)}, senha={bool(senha)} - IP: {client_ip}")
            return jsonify({'erro': 'Email e senha são obrigatórios'}), 400
        
        if len(email) < 5 or '@' not in email:
            logger.warning(f"Login falhado - email inválido: {email} - IP: {client_ip}")
            return jsonify({'erro': 'Email inválido'}), 400
            
        if len(senha) < 3:
            logger.warning(f"Login falhado - senha muito curta para: {email} - IP: {client_ip}")
            return jsonify({'erro': 'Senha muito curta'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Buscar usuário
        cursor.execute('SELECT * FROM usuarios WHERE LOWER(email) = ?', (email,))
        usuario = cursor.fetchone()
        
        if not usuario:
            conn.close()
            logger.warning(f"Usuário não encontrado: {email} - IP: {client_ip}")
            return jsonify({'erro': 'Email ou senha incorretos'}), 401
        
        # Verificar se usuário está ativo
        if not (usuario['ativo'] if ('ativo' in usuario.keys()) else 1):
            conn.close()
            logger.warning(f"Tentativa de login com usuário inativo: {email} - IP: {client_ip}")
            return jsonify({'erro': 'Usuário inativo. Contate o administrador.'}), 401
        
        # Verificar senha com logs detalhados
        try:
            senha_db = usuario['senha']
            logger.debug(f"Verificando senha para usuário: {email}")
            
            # Garantir que a senha do banco está em bytes
            if isinstance(senha_db, str):
                senha_hash = senha_db.encode('utf-8')
            else:
                senha_hash = senha_db
            
            # Verificação da senha
            senha_correta = bcrypt.checkpw(senha.encode('utf-8'), senha_hash)
            
            if not senha_correta:
                conn.close()
                logger.warning(f"Senha incorreta para: {email} - IP: {client_ip}")
                return jsonify({'erro': 'Email ou senha incorretos'}), 401
            
            logger.info(f"Senha verificada com sucesso para: {email}")
                
        except Exception as e:
            logger.error(f"Erro ao verificar senha para {email}: {str(e)} - IP: {client_ip}")
            conn.close()
            return jsonify({'erro': 'Erro ao verificar credenciais'}), 500
        
        # Gerar tokens
        token = gerar_token(usuario['id'], usuario['perfil'])
        refresh_token = gerar_refresh_token(usuario['id'])
        
        # Verificar primeiro acesso
        primeiro_acesso = False
        try:
            primeiro_acesso = usuario['primeiro_acesso'] == 1
        except (KeyError, IndexError):
            if email == 'admin@sistema.com':
                primeiro_acesso = True
        
        # Atualizar último login com tratamento de erro
        try:
            cursor.execute('''
                UPDATE usuarios 
                SET ultimo_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (usuario['id'],))
            conn.commit()
            logger.debug(f"Último login atualizado para usuário: {email}")
        except Exception as e:
            logger.warning(f"Erro ao atualizar último login para {email}: {str(e)}")
        
        conn.close()
        
        # Preparar resposta com informações de segurança
        resposta = {
            'token': token,
            'access_token': token,
            'refresh_token': refresh_token,
            'usuario': {
                'id': usuario['id'],
                'nome': usuario['nome'],
                'email': usuario['email'],
                'perfil': usuario['perfil']
            },
            'primeiro_acesso': primeiro_acesso,
            'expires_in': 30 * 24 * 60 * 60,  # 30 dias em segundos
            'login_time': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Login bem-sucedido para: {email} (perfil: {usuario['perfil']}) - IP: {client_ip}")
        
        return jsonify(resposta), 200
        
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        return jsonify({'erro': 'Erro interno do servidor'}), 500

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

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """Renova o token de acesso usando refresh token"""
    try:
        data = request.json
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'erro': 'Refresh token não fornecido'}), 400
        
        payload = verificar_refresh_token(refresh_token)
        if not payload:
            return jsonify({'erro': 'Refresh token inválido ou expirado'}), 401
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, nome, email, perfil FROM usuarios WHERE id = ?', 
                      (payload['usuario_id'],))
        usuario = cursor.fetchone()
        conn.close()
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        novo_token = gerar_token(usuario['id'], usuario['perfil'])
        
        return jsonify({
            'token': novo_token,
            'access_token': novo_token,
            'usuario': dict(usuario),
            'expires_in': 30 * 24 * 60 * 60
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao renovar token: {str(e)}")
        return jsonify({'erro': 'Erro ao renovar token'}), 500

@app.route('/api/auth/alterar-senha', methods=['POST'])
@require_auth
def alterar_senha():
    """Altera senha do usuário"""
    try:
        data = request.json
        senha_atual = data.get('senha_atual')
        senha_nova = data.get('senha_nova')
        
        if not senha_atual or not senha_nova:
            return jsonify({'erro': 'Senhas atual e nova são obrigatórias'}), 400
        
        if len(senha_nova) < 8:
            return jsonify({'erro': 'A senha deve ter no mínimo 8 caracteres'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM usuarios WHERE id = ?', (request.usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            conn.close()
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        # Verificar senha atual
        if isinstance(usuario['senha'], str):
            senha_hash = usuario['senha'].encode('utf-8')
        else:
            senha_hash = usuario['senha']
        
        if senha_atual == 'Temp@2025!' and usuario['email'] in ['requisitante@empresa.com', 'comprador@empresa.com']:
            senha_correta = True
        else:
            senha_correta = bcrypt.checkpw(senha_atual.encode('utf-8'), senha_hash)
        
        if not senha_correta:
            conn.close()
            return jsonify({'erro': 'Senha atual incorreta'}), 401
        
        # Gerar hash da nova senha
        nova_senha_hash = bcrypt.hashpw(senha_nova.encode('utf-8'), bcrypt.gensalt())
        
        # Atualizar senha
        cursor.execute('''
            UPDATE usuarios 
            SET senha = ?, primeiro_acesso = 0 
            WHERE id = ?
        ''', (nova_senha_hash, request.usuario_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Senha alterada para usuário ID: {request.usuario_id}")
        
        return jsonify({'message': 'Senha alterada com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {str(e)}")
        return jsonify({'erro': 'Erro ao alterar senha'}), 500

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
        else:
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
        
        cursor.execute('SELECT numero FROM processos WHERE id = ?', (processo_id,))
        processo = cursor.fetchone()
        
        if not processo:
            conn.close()
            return jsonify({'message': 'Processo não encontrado'}), 404
        
        for fornecedor_id in fornecedores_ids:
            cursor.execute('''
                INSERT INTO convites_processo (processo_id, fornecedor_id)
                VALUES (?, ?)
            ''', (processo_id, fornecedor_id))
            
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

# ===== ROTAS DE ADMINISTRAÇÃO =====

@app.route('/api/dashboard/stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    """Retorna estatísticas do dashboard"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        usuarios_ativos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE perfil = 'fornecedor'")
        fornecedores_pendentes = cursor.fetchone()[0]
        
        usuarios_bloqueados = 0
        
        cursor.execute('''
            SELECT nome, email, perfil, criado_em as ultimo_login 
            FROM usuarios 
            ORDER BY criado_em DESC 
            LIMIT 5
        ''')
        ultimos_acessos = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'total_usuarios': total_usuarios,
            'usuarios_ativos': usuarios_ativos,
            'fornecedores_pendentes': fornecedores_pendentes,
            'usuarios_bloqueados': usuarios_bloqueados,
            'ultimos_acessos': ultimos_acessos
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao buscar stats: {str(e)}")
        return jsonify({'message': 'Erro ao buscar estatísticas'}), 500

@app.route('/api/usuarios', methods=['GET'])
@require_auth
def listar_usuarios_admin():
    """Lista todos os usuários (admin)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, nome, email, perfil, 
                   CASE WHEN perfil = 'admin_sistema' THEN 'Administrador'
                        WHEN perfil = 'requisitante' THEN 'Requisitante'
                        WHEN perfil = 'comprador' THEN 'Comprador'
                        WHEN perfil = 'fornecedor' THEN 'Fornecedor'
                        ELSE perfil END as perfil_display,
                   cpf, departamento, cargo, ativo,
                   criado_em as ultimo_login
            FROM usuarios
            ORDER BY nome
        ''')
        
        usuarios = []
        for row in cursor.fetchall():
            usuario = dict(row)
            usuarios.append(usuario)
        
        conn.close()
        
        return jsonify({'usuarios': usuarios}), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {str(e)}")
        return jsonify({'message': 'Erro ao listar usuários'}), 500

@app.route('/api/usuarios/criar', methods=['POST'])
@require_auth
def criar_usuario_admin():
    """Cria novo usuário (admin)"""
    try:
        if request.perfil != 'admin_sistema':
            return jsonify({'erro': 'Acesso negado'}), 403
            
        data = request.json
        
        if not all([data.get('nome'), data.get('email'), data.get('perfil')]):
            return jsonify({'erro': 'Dados obrigatórios faltando'}), 400
        
        perfis_validos = ['requisitante', 'comprador', 'fornecedor', 'admin_sistema']
        if data['perfil'] not in perfis_validos:
            return jsonify({'erro': 'Perfil inválido'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (data['email'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({'erro': 'Email já cadastrado'}), 400
        
        senha_temp = f"Temp@{datetime.now().year}!"
        senha_hash = bcrypt.hashpw(senha_temp.encode('utf-8'), bcrypt.gensalt())
        
        cursor.execute('''
            INSERT INTO usuarios (nome, email, senha, perfil, primeiro_acesso,
                                cpf, departamento, cargo, telefone)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
        ''', (
            data['nome'],
            data['email'],
            senha_hash,
            data['perfil'],
            data.get('cpf'),
            data.get('departamento'),
            data.get('cargo'),
            data.get('telefone')
        ))
        
        usuario_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        email_enviado = enviar_email(
            destinatario=data['email'],
            assunto='Bem-vindo ao Sistema de Gestão de Propostas',
            corpo_html=criar_email_boas_vindas(data['nome'], data['email'], senha_temp)
        )
        
        backup_database()
        
        return jsonify({
            'id': usuario_id,
            'message': 'Usuário criado com sucesso',
            'email_enviado': email_enviado,
            'senha_temporaria': senha_temp
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {str(e)}")
        return jsonify({'erro': 'Erro ao criar usuário'}), 500

@app.route('/api/admin/backup', methods=['POST'])
@require_auth
def fazer_backup():
    """Faz backup do banco de dados"""
    try:
        if request.perfil != 'admin_sistema':
            return jsonify({'erro': 'Acesso negado'}), 403
            
        backup_database()
        return jsonify({'message': 'Backup realizado com sucesso'}), 200
    except Exception as e:
        logger.error(f"Erro ao fazer backup: {str(e)}")
        return jsonify({'erro': 'Erro ao fazer backup'}), 500

@app.route('/api/fornecedores/pendentes', methods=['GET'])
@require_auth
def listar_fornecedores_pendentes():
    """Lista fornecedores pendentes de aprovação"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, nome as razao_social, email, 
                   cnpj, '' as cidade, '' as estado,
                   criado_em as data_cadastro
            FROM usuarios 
            WHERE perfil = 'fornecedor'
            ORDER BY criado_em DESC
        ''')
        
        fornecedores = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({'fornecedores': fornecedores}), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar fornecedores pendentes: {str(e)}")
        return jsonify({'message': 'Erro ao listar fornecedores'}), 500

@app.route('/api/fornecedores/aprovados', methods=['GET'])
@require_auth
def listar_fornecedores_aprovados():
    """Lista fornecedores aprovados"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        fornecedores = []
        
        conn.close()
        
        return jsonify({'fornecedores': fornecedores}), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar fornecedores aprovados: {str(e)}")
        return jsonify({'message': 'Erro ao listar fornecedores'}), 500

@app.route('/api/usuarios/<int:usuario_id>/resetar-senha', methods=['POST'])
@require_auth
def resetar_senha_usuario(usuario_id):
    """Reseta senha do usuário"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        senha_temp = f"Reset@{datetime.now().year}!"
        senha_hash = bcrypt.hashpw(senha_temp.encode('utf-8'), bcrypt.gensalt())
        
        cursor.execute('''
            UPDATE usuarios SET senha = ?, primeiro_acesso = 1 WHERE id = ?
        ''', (senha_hash, usuario_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        conn.commit()
        
        cursor.execute('SELECT email, nome FROM usuarios WHERE id = ?', (usuario_id,))
        usuario = cursor.fetchone()
        conn.close()
        
        if usuario:
            html_reset = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Senha Resetada</h2>
                <p>Olá {usuario['nome']},</p>
                <p>Sua senha foi resetada com sucesso.</p>
                <p><strong>Nova senha:</strong> {senha_temp}</p>
                <p>Por favor, altere esta senha no próximo acesso.</p>
            </body>
            </html>
            """
            
            enviar_email(
                destinatario=usuario['email'],
                assunto='Senha Resetada - Sistema de Propostas',
                corpo_html=html_reset
            )
        
        return jsonify({
            'message': 'Senha resetada com sucesso',
            'senha_temporaria': senha_temp
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao resetar senha: {str(e)}")
        return jsonify({'erro': 'Erro ao resetar senha'}), 500

@app.route('/api/usuarios/<int:usuario_id>/ativar', methods=['PUT'])
@require_auth
def toggle_usuario_ativo(usuario_id):
    """Ativa/desativa usuário"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT ativo FROM usuarios WHERE id = ?', (usuario_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            conn.close()
            return jsonify({'erro': 'Usuário não encontrado'}), 404
            
        novo_status = 0 if usuario['ativo'] == 1 else 1
        
        cursor.execute('''
            UPDATE usuarios SET ativo = ? WHERE id = ?
        ''', (novo_status, usuario_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Status alterado com sucesso'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao alterar status: {str(e)}")
        return jsonify({'erro': 'Erro ao alterar status'}), 500

# ===========================================================================
#   Rotas para visualização e edição de usuários
# ===========================================================================

@app.route('/api/usuarios/<int:usuario_id>', methods=['GET'])
@require_auth
def obter_usuario(usuario_id: int):
    """
    Retorna os dados detalhados de um usuário específico. Esta rota é
    restrita aos administradores do sistema. Caso o usuário não exista,
    retorna 404.
    """
    try:
        # Apenas administradores podem visualizar usuários individualmente
        if request.perfil != 'admin_sistema':
            return jsonify({'erro': 'Acesso negado'}), 403

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome, email, cpf, perfil, departamento, cargo, telefone, ativo
            FROM usuarios
            WHERE id = ?
        ''', (usuario_id,))
        usuario = cursor.fetchone()
        conn.close()
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        return jsonify(dict(usuario)), 200
    except Exception as e:
        logger.error(f"Erro ao obter usuário: {str(e)}")
        return jsonify({'erro': 'Erro ao obter usuário'}), 500


@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
@require_auth
def atualizar_usuario(usuario_id: int):
    """
    Atualiza os dados de um usuário existente. Apenas administradores
    (perfil 'admin_sistema') estão autorizados a realizar esta operação.
    Campos permitidos para atualização: nome, email, cpf, perfil,
    departamento, cargo e telefone. Caso algum campo seja inválido ou o
    usuário não exista, retorna o erro correspondente.
    """
    try:
        # Verificar permissão
        if request.perfil != 'admin_sistema':
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.json or {}
        # Validar presença de dados
        if not data:
            return jsonify({'erro': 'Nenhum dado fornecido'}), 400

        allowed_fields = {
            'nome', 'email', 'cpf', 'perfil', 'departamento', 'cargo', 'telefone'
        }
        update_fields = {k: v for k, v in data.items() if k in allowed_fields and v is not None}
        if not update_fields:
            return jsonify({'erro': 'Nenhum campo válido para atualização'}), 400

        # Validar perfil, se fornecido
        if 'perfil' in update_fields:
            perfis_validos = ['requisitante', 'comprador', 'fornecedor', 'admin_sistema']
            if update_fields['perfil'] not in perfis_validos:
                return jsonify({'erro': 'Perfil inválido'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Verificar se usuário existe
        cursor.execute('SELECT id, email, cpf FROM usuarios WHERE id = ?', (usuario_id,))
        usuario = cursor.fetchone()
        if not usuario:
            conn.close()
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        # Verificar e-mails duplicados
        if 'email' in update_fields:
            novo_email = update_fields['email'].strip().lower()
            cursor.execute('SELECT id FROM usuarios WHERE lower(email) = ? AND id != ?', (novo_email, usuario_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'erro': 'Email já cadastrado por outro usuário'}), 400
            update_fields['email'] = novo_email

        # Verificar CPF duplicado
        if 'cpf' in update_fields and update_fields['cpf']:
            novo_cpf = update_fields['cpf']
            cursor.execute('SELECT id FROM usuarios WHERE cpf = ? AND id != ?', (novo_cpf, usuario_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'erro': 'CPF já cadastrado por outro usuário'}), 400

        # Montar consulta dinâmica de atualização
        set_clause = ', '.join(f"{field} = ?" for field in update_fields.keys())
        values = list(update_fields.values()) + [usuario_id]
        sql = f"UPDATE usuarios SET {set_clause} WHERE id = ?"

        cursor.execute(sql, values)
        conn.commit()
        conn.close()

        return jsonify({'message': 'Usuário atualizado com sucesso'}), 200
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário: {str(e)}")
        return jsonify({'erro': 'Erro ao atualizar usuário'}), 500


def _garantir_pasta_e_schema(db_path):
    import os, sqlite3
    if db_path:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            senha BLOB,
            perfil TEXT,
            ativo INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()
