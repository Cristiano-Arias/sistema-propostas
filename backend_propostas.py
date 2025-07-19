#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import json
import os
import uuid
import logging
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_PARAGRAPH_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from openpyxl import Workbook
from openpyxl.styles import Font, Fill, PatternFill, Alignment, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from openpyxl.worksheet.page import PageMargins
import io
import base64
import re
from decimal import Decimal

# Configuração do Flask
app = Flask(__name__, static_folder='static', static_url_path='/static')    
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
CORS(app)

# Configuração de Email
app.config['MAIL_SERVER'] = os.environ.get('EMAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('EMAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER')

mail = Mail(app)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Diretórios
PROPOSTAS_DIR = 'propostas'
STATIC_DIR = 'static'

# Criar diretórios se não existirem
for dir_name in [PROPOSTAS_DIR, STATIC_DIR]:
    try:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            logger.info(f"Diretório {dir_name} criado")
    except Exception as e:
        logger.error(f"Erro ao criar diretório {dir_name}: {e}")

# Base de dados em memória
propostas_db = {}
processos_db = {}
fornecedores_db = {}

# Configurações de email
EMAIL_CONFIG = {
    'destinatario_principal': os.environ.get('EMAIL_SUPRIMENTOS', 'suprimentos@empresa.com'),
    'destinatarios_copia': os.environ.get('EMAIL_CC', '').split(',') if os.environ.get('EMAIL_CC') else [],
    'administradores': os.environ.get('EMAIL_ADMINS', 'admin@empresa.com').split(',')
}

def limpar_valor_monetario(valor):
    """Limpa e converte valores monetários para float"""
    if not valor:
        return 0.0
    
    valor_str = re.sub(r'[^\d,.-]', '', str(valor))
    
    if ',' in valor_str and '.' in valor_str:
        if valor_str.rindex(',') > valor_str.rindex('.'):
            valor_str = valor_str.replace('.', '').replace(',', '.')
        else:
            valor_str = valor_str.replace(',', '')
    elif ',' in valor_str:
        valor_str = valor_str.replace(',', '.')
    
    try:
        return float(valor_str)
    except:
        return 0.0

def formatar_moeda(valor):
    """Formata valor para moeda brasileira"""
    try:
        valor_num = float(valor) if not isinstance(valor, (int, float)) else valor
        return f"R$ {valor_num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

# ===== ROTAS PARA PÁGINAS HTML =====

@app.route('/')
def index():
    """Página inicial com informações da API"""
    return jsonify({
        'api': 'Sistema de Gestão de Propostas',
        'versao': '2.0.0',
        'status': 'online',
        'endpoints': {
            'POST /api/enviar-proposta': 'Enviar nova proposta',
            'GET /api/propostas/listar': 'Listar todas as propostas',
            'GET /api/proposta/<protocolo>': 'Buscar proposta específica',
            'POST /api/criar-processo': 'Criar novo processo',
            'GET /api/processos/<numero>': 'Buscar processo',
            'GET /api/status': 'Status da API'
        }
    })

# Rotas para servir arquivos HTML
@app.route('/portal-propostas-novo.html')
def portal_propostas():
    """Servir página do portal de propostas"""
    # Primeiro tenta na pasta static
    if os.path.exists(os.path.join('static', 'portal-propostas-novo.html')):
        return send_from_directory('static', 'portal-propostas-novo.html')
    # Depois tenta na raiz
    elif os.path.exists('portal-propostas-novo.html'):
        return send_from_directory('.', 'portal-propostas-novo.html')
    else:
        return "Arquivo não encontrado", 404

@app.route('/sistema-gestao-corrigido2.html')
def sistema_gestao():
    """Servir página do sistema de gestão"""
    if os.path.exists(os.path.join('static', 'sistema-gestao-corrigido2.html')):
        return send_from_directory('static', 'sistema-gestao-corrigido2.html')
    elif os.path.exists('sistema-gestao-corrigido2.html'):
        return send_from_directory('.', 'sistema-gestao-corrigido2.html')
    else:
        return "Arquivo não encontrado", 404

@app.route('/auth.js')
def auth_js():
    """Servir arquivo de autenticação"""
    if os.path.exists(os.path.join('static', 'auth.js')):
        return send_from_directory('static', 'auth.js')
    elif os.path.exists('auth.js'):
        return send_from_directory('.', 'auth.js')
    else:
        return "Arquivo não encontrado", 404

@app.route('/index.html')
def index_html():
    """Servir página index"""
    if os.path.exists(os.path.join('static', 'index.html')):
        return send_from_directory('static', 'index.html')
    elif os.path.exists('index.html'):
        return send_from_directory('.', 'index.html')
    else:
        return "Arquivo não encontrado", 404

@app.route('/cadastro-comprador.html')
def cadastro_comprador():
    """Servir página de cadastro de comprador"""
    if os.path.exists(os.path.join('static', 'cadastro-comprador.html')):
        return send_from_directory('static', 'cadastro-comprador.html')
    elif os.path.exists('cadastro-comprador.html'):
        return send_from_directory('.', 'cadastro-comprador.html')
    else:
        return "Arquivo não encontrado", 404

@app.route('/cadastro-fornecedor.html')
def cadastro_fornecedor():
    """Servir página de cadastro de fornecedor"""
    if os.path.exists(os.path.join('static', 'cadastro-fornecedor.html')):
        return send_from_directory('static', 'cadastro-fornecedor.html')
    elif os.path.exists('cadastro-fornecedor.html'):
        return send_from_directory('.', 'cadastro-fornecedor.html')
    else:
        return "Arquivo não encontrado", 404

@app.route('/dashboard-auditor.html')
def dashboard_auditor():
    """Servir dashboard do auditor"""
    if os.path.exists(os.path.join('static', 'dashboard-auditor.html')):
        return send_from_directory('static', 'dashboard-auditor.html')
    elif os.path.exists('dashboard-auditor.html'):
        return send_from_directory('.', 'dashboard-auditor.html')
    else:
        return "Arquivo não encontrado", 404

@app.route('/dashboard-fornecedor-completo.html')
def dashboard_fornecedor():
    """Servir dashboard do fornecedor"""
    if os.path.exists(os.path.join('static', 'dashboard-fornecedor-completo.html')):
        return send_from_directory('static', 'dashboard-fornecedor-completo.html')
    elif os.path.exists('dashboard-fornecedor-completo.html'):
        return send_from_directory('.', 'dashboard-fornecedor-completo.html')
    else:
        return "Arquivo não encontrado", 404

@app.route('/modulo-relatorios.html')
def modulo_relatorios():
    """Servir módulo de relatórios"""
    if os.path.exists(os.path.join('static', 'modulo-relatorios.html')):
        return send_from_directory('static', 'modulo-relatorios.html')
    elif os.path.exists('modulo-relatorios.html'):
        return send_from_directory('.', 'modulo-relatorios.html')
    else:
        return "Arquivo não encontrado", 404

# ===== ROTAS DA API =====

@app.route('/api/status')
def status():
    """Verificar status da API"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'total_propostas': len(propostas_db),
        'total_processos': len(processos_db),
        'total_fornecedores': len(fornecedores_db),
        'email_configurado': bool(app.config['MAIL_USERNAME']),
        'versao': '2.0',
        'encoding': 'UTF-8',
        'diretorios': {
            'propostas': os.path.exists(PROPOSTAS_DIR),
            'static': os.path.exists(STATIC_DIR)
        }
    })

@app.route('/api/enviar-proposta', methods=['POST'])
def enviar_proposta():
    """Receber e processar nova proposta"""
    try:
        dados = request.json
        protocolo = dados.get('protocolo')
        processo = dados.get('processo')
        
        if not protocolo or not processo:
            return jsonify({
                'success': False,
                'erro': 'Protocolo e processo são obrigatórios'
            }), 400
        
        # Verificar se a empresa já enviou proposta para este processo
        cnpj = dados.get('dados', {}).get('cnpj', '')
        for prop_id, prop in propostas_db.items():
            if prop.get('processo') == processo and prop.get('dados', {}).get('cnpj') == cnpj:
                return jsonify({
                    'success': False,
                    'erro': 'Sua empresa já enviou uma proposta para este processo'
                }), 409
        
        # Salvar proposta
        propostas_db[protocolo] = {
            'protocolo': protocolo,
            'processo': processo,
            'data': datetime.now().isoformat(),
            'dados': dados.get('dados', {}),
            'resumo': dados.get('resumo', {}),
            'tecnica': dados.get('tecnica', {}),
            'comercial': dados.get('comercial', {})
        }
        
        # Gerar arquivos Excel e Word
        email_enviado = False
        try:
            # Aqui você pode adicionar a geração de Excel/Word se necessário
            # excel_buffer = gerar_excel_proposta_profissional(dados)
            # word_buffer = gerar_word_proposta_profissional(dados)
            
            # Enviar email
            if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
                try:
                    msg = Message(
                        subject=f'Nova Proposta - Processo {processo} - {dados.get("dados", {}).get("razaoSocial", "")}',
                        recipients=[EMAIL_CONFIG['destinatario_principal']] + EMAIL_CONFIG['destinatarios_copia'],
                        body=f'''
Nova proposta recebida:

Protocolo: {protocolo}
Processo: {processo}
Empresa: {dados.get('dados', {}).get('razaoSocial', '')}
CNPJ: {dados.get('dados', {}).get('cnpj', '')}
Valor Total: {dados.get('comercial', {}).get('valorTotal', 'N/A')}
Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Atenciosamente,
Sistema de Gestão de Propostas
                        '''
                    )
                    
                    mail.send(msg)
                    email_enviado = True
                    logger.info(f"Email enviado para proposta {protocolo}")
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar email: {e}")
            
        except Exception as e:
            logger.error(f"Erro ao processar proposta: {e}")
        
        # Criar resumo para o sistema de gestão
        proposta_resumo = {
            'protocolo': protocolo,
            'processo': processo,
            'empresa': dados.get('dados', {}).get('razaoSocial', ''),
            'cnpj': dados.get('dados', {}).get('cnpj', ''),
            'data': datetime.now().isoformat(),
            'valor': dados.get('comercial', {}).get('valorTotal', 'R$ 0,00'),
            'dados': dados
        }
        
        return jsonify({
            'success': True,
            'protocolo': protocolo,
            'mensagem': 'Proposta enviada com sucesso',
            'email_enviado': email_enviado,
            'proposta_resumo': proposta_resumo
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar proposta: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@app.route('/api/propostas/listar', methods=['GET'])
def listar_propostas():
    """Listar todas as propostas"""
    try:
        propostas_lista = []
        
        for protocolo, proposta in propostas_db.items():
            propostas_lista.append({
                'protocolo': protocolo,
                'processo': proposta.get('processo'),
                'empresa': proposta.get('dados', {}).get('razaoSocial', ''),
                'cnpj': proposta.get('dados', {}).get('cnpj', ''),
                'data': proposta.get('data'),
                'valor': proposta.get('comercial', {}).get('valorTotal', 'R$ 0,00')
            })
        
        # Ordenar por data (mais recente primeiro)
        propostas_lista.sort(key=lambda x: x['data'], reverse=True)
        
        return jsonify({
            'success': True,
            'total': len(propostas_lista),
            'propostas': propostas_lista
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@app.route('/api/proposta/<protocolo>', methods=['GET'])
def buscar_proposta(protocolo):
    """Buscar proposta específica"""
    try:
        proposta = propostas_db.get(protocolo)
        
        if not proposta:
            return jsonify({
                'success': False,
                'erro': 'Proposta não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'proposta': proposta
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar proposta: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@app.route('/api/criar-processo', methods=['POST'])
def criar_processo():
    """Criar novo processo"""
    try:
        dados = request.json
        numero = dados.get('numero')
        
        if not numero:
            return jsonify({
                'success': False,
                'erro': 'Número do processo é obrigatório'
            }), 400
        
        # Salvar processo
        processos_db[numero] = {
            'numero': numero,
            'objeto': dados.get('objeto'),
            'modalidade': dados.get('modalidade'),
            'prazo': dados.get('prazo'),
            'dataCadastro': datetime.now().isoformat(),
            'criadoPor': dados.get('criadoPor')
        }
        
        # Notificar fornecedores se solicitado
        fornecedores_notificados = 0
        if dados.get('notificarFornecedores'):
            fornecedores_notificados = len(fornecedores_db)
            logger.info(f"Notificando {fornecedores_notificados} fornecedores sobre processo {numero}")
        
        return jsonify({
            'success': True,
            'processo': numero,
            'fornecedores_notificados': fornecedores_notificados
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar processo: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@app.route('/api/processos/<numero>', methods=['GET'])
def buscar_processo(numero):
    """Buscar processo específico"""
    try:
        processo = processos_db.get(numero)
        
        if not processo:
            return jsonify({
                'success': False,
                'erro': 'Processo não encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'processo': processo
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar processo: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

# Tratamento de erros
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'erro': 'Endpoint não encontrado'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'erro': 'Erro interno do servidor'
    }), 500
# Rota para servir arquivos da pasta static sem /static/ na URL
@app.route('/<path:filename>')
def serve_static_files(filename):
    """Servir arquivos HTML da pasta static"""
    if filename.endswith('.html') or filename.endswith('.js'):
        return send_from_directory('static', filename)
    return "Arquivo não encontrado", 404
if __name__ == '__main__':
    # Configurações para desenvolvimento
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Iniciando servidor na porta {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Email configurado: {bool(app.config['MAIL_USERNAME'])}")
    
    # Criar alguns dados de exemplo
    if debug:
        # Processo de exemplo
        processos_db['LIC-2025-001'] = {
            'numero': 'LIC-2025-001',
            'objeto': 'Construção de Complexo Comercial - 5.000m²',
            'modalidade': 'Concorrência',
            'prazo': '2025-08-30T17:00:00',
            'dataCadastro': datetime.now().isoformat(),
            'criadoPor': 'admin'
        }
        
        logger.info("Dados de exemplo criados")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
        # Rota para servir arquivos da pasta static sem /static/ na URL
    )
