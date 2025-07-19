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
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
CORS(app)

# Configuração de Email CORRIGIDA
app.config['MAIL_SERVER'] = os.environ.get('EMAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('EMAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER')

# IMPORTANTE: Para Gmail, use App Password, não a senha normal
# 1. Ative verificação em duas etapas
# 2. Gere uma senha de app em: https://myaccount.google.com/apppasswords

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

# Configurações de email - MÚLTIPLOS DESTINATÁRIOS
EMAIL_CONFIG = {
    'destinatario_principal': os.environ.get('EMAIL_SUPRIMENTOS', 'suprimentos@empresa.com'),
    'destinatarios_copia': os.environ.get('EMAIL_CC', '').split(',') if os.environ.get('EMAIL_CC') else [],
    'administradores': os.environ.get('EMAIL_ADMINS', 'admin@empresa.com').split(',')
}

def limpar_valor_monetario(valor):
    """Limpa e converte valores monetários para float"""
    if not valor:
        return 0.0
    
    # Remove tudo exceto números, vírgula e ponto
    valor_str = re.sub(r'[^\d,.-]', '', str(valor))
    
    # Trata formato brasileiro (1.234,56) ou americano (1,234.56)
    if ',' in valor_str and '.' in valor_str:
        # Determina qual é o separador decimal
        if valor_str.rindex(',') > valor_str.rindex('.'):
            # Formato brasileiro: ponto é milhar, vírgula é decimal
            valor_str = valor_str.replace('.', '').replace(',', '.')
        else:
            # Formato americano: vírgula é milhar, ponto é decimal
            valor_str = valor_str.replace(',', '')
    elif ',' in valor_str:
        # Apenas vírgula, assume decimal
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

def set_cell_border(cell, **kwargs):
    """Define bordas para célula do Word"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    
    # Remove bordas existentes
    tcBorders = tcPr.first_child_found_in("w:tcBorders")
    if tcBorders is not None:
        tcPr.remove(tcBorders)
    
    # Adiciona novas bordas
    tcBorders = OxmlElement('w:tcBorders')
    
    for edge in ['top', 'left', 'bottom', 'right']:
        if edge in kwargs:
            edge_element = OxmlElement(f'w:{edge}')
            edge_element.set(qn('w:val'), kwargs[edge].get('val', 'single'))
            edge_element.set(qn('w:sz'), str(kwargs[edge].get('sz', 4)))
            edge_element.set(qn('w:space'), str(kwargs[edge].get('space', 0)))
            edge_element.set(qn('w:color'), kwargs[edge].get('color', '000000'))
            tcBorders.append(edge_element)
    
    tcPr.append(tcBorders)

def gerar_excel_proposta_profissional(dados_proposta):
    """Gera arquivo Excel profissional com a proposta comercial - CONTINUAÇÃO"""
    wb = Workbook()
    
    # Remove planilha padrão
    wb.remove(wb.active)
    
    # Estilos personalizados
    header_font = Font(name='Arial', size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    title_font = Font(name='Arial', size=16, bold=True, color="1F497D")
    subtitle_font = Font(name='Arial', size=12, bold=True, color="1F497D")
    label_font = Font(name='Arial', size=10, bold=True)
    normal_font = Font(name='Arial', size=10)
    
    currency_style = NamedStyle(name='currency_style')
    currency_style.number_format = 'R$ #,##0.00'
    currency_style.font = Font(name='Arial', size=10)
    currency_style.alignment = Alignment(horizontal='right')
    
    percent_style = NamedStyle(name='percent_style')
    percent_style.number_format = '0.00%'
    percent_style.font = Font(name='Arial', size=10)
    percent_style.alignment = Alignment(horizontal='center')
    
    # Adiciona estilos ao workbook
    wb.add_named_style(currency_style)
    wb.add_named_style(percent_style)
    
    # Bordas
    thin_border = Border(
        left=Side(style='thin', color='000000'),
        right=Side(style='thin', color='000000'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000')
    )
    
    thick_border = Border(
        left=Side(style='thick', color='000000'),
        right=Side(style='thick', color='000000'),
        top=Side(style='thick', color='000000'),
        bottom=Side(style='thick', color='000000')
    )
    
    # =================================
    # ABA 1: RESUMO EXECUTIVO
    # =================================
    ws_resumo = wb.create_sheet("Resumo Executivo", 0)
    ws_resumo.sheet_properties.tabColor = "1F497D"
    
    # Configurar página
    ws_resumo.page_margins = PageMargins(left=0.7, right=0.7, top=0.75, bottom=0.75)
    ws_resumo.page_setup.orientation = ws_resumo.ORIENTATION_PORTRAIT
    ws_resumo.page_setup.paperSize = ws_resumo.PAPERSIZE_A4
    
    # Largura das colunas
    ws_resumo.column_dimensions['A'].width = 5
    ws_resumo.column_dimensions['B'].width = 25
    ws_resumo.column_dimensions['C'].width = 35
    ws_resumo.column_dimensions['D'].width = 20
    ws_resumo.column_dimensions['E'].width = 20
    
    # Cabeçalho principal
    ws_resumo.merge_cells('A1:E2')
    ws_resumo['A1'] = 'PROPOSTA TÉCNICA E COMERCIAL'
    ws_resumo['A1'].font = Font(name='Arial', size=20, bold=True, color="FFFFFF")
    ws_resumo['A1'].fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    ws_resumo['A1'].alignment = Alignment(horizontal="center", vertical="center")
    ws_resumo.row_dimensions[1].height = 30
    ws_resumo.row_dimensions[2].height = 30
    
    # Informações do processo
    ws_resumo.merge_cells('A4:E4')
    ws_resumo['A4'] = f"Processo: {dados_proposta.get('processo', 'N/A')}"
    ws_resumo['A4'].font = subtitle_font
    ws_resumo['A4'].alignment = Alignment(horizontal="center")
    
    # Dados da empresa
    ws_resumo['B6'] = 'DADOS DA EMPRESA'
    ws_resumo['B6'].font = subtitle_font
    ws_resumo.merge_cells('B6:E6')
    
    dados_empresa = [
        ('Razão Social:', dados_proposta.get('dados', {}).get('razaoSocial', '')),
        ('CNPJ:', dados_proposta.get('dados', {}).get('cnpj', '')),
        ('Endereço:', dados_proposta.get('dados', {}).get('endereco', '')),
        ('Cidade/UF:', dados_proposta.get('dados', {}).get('cidade', '')),
        ('Telefone:', dados_proposta.get('dados', {}).get('telefone', '')),
        ('E-mail:', dados_proposta.get('dados', {}).get('email', '')),
        ('Responsável Técnico:', dados_proposta.get('dados', {}).get('respTecnico', '')),
        ('CREA/CAU:', dados_proposta.get('dados', {}).get('crea', ''))
    ]
    
    row = 8
    for label, value in dados_empresa:
        ws_resumo[f'B{row}'] = label
        ws_resumo[f'B{row}'].font = label_font
        ws_resumo[f'B{row}'].fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        ws_resumo[f'C{row}'] = value
        ws_resumo[f'C{row}'].font = normal_font
        ws_resumo.merge_cells(f'C{row}:E{row}')
        
        # Aplicar bordas
        for col in ['B', 'C', 'D', 'E']:
            ws_resumo[f'{col}{row}'].border = thin_border
        
        row += 1
    
    # Resumo financeiro
    row += 2
    ws_resumo[f'B{row}'] = 'RESUMO FINANCEIRO'
    ws_resumo[f'B{row}'].font = subtitle_font
    ws_resumo.merge_cells(f'B{row}:E{row}')
    
    row += 2
    
    # Cabeçalho da tabela financeira
    headers = ['Componente', 'Valor', '%']
    ws_resumo[f'B{row}'] = headers[0]
    ws_resumo[f'C{row}'] = headers[1]
    ws_resumo[f'D{row}'] = headers[2]
    
    for col in ['B', 'C', 'D']:
        ws_resumo[f'{col}{row}'].font = header_font
        ws_resumo[f'{col}{row}'].fill = header_fill
        ws_resumo[f'{col}{row}'].alignment = header_alignment
        ws_resumo[f'{col}{row}'].border = thin_border
    
    row += 1
    
    # Valores
    total_mo = limpar_valor_monetario(dados_proposta.get('comercial', {}).get('totalMaoObra', 0))
    total_mat = limpar_valor_monetario(dados_proposta.get('comercial', {}).get('totalMateriais', 0))
    total_equip = limpar_valor_monetario(dados_proposta.get('comercial', {}).get('totalEquipamentos', 0))
    total_servicos = limpar_valor_monetario(dados_proposta.get('comercial', {}).get('totalServicos', 0))
    
    custo_direto = total_mo + total_mat + total_equip + total_servicos
    
    bdi_percentual = float(dados_proposta.get('comercial', {}).get('bdiPercentual', 0))
    bdi_valor = limpar_valor_monetario(dados_proposta.get('comercial', {}).get('bdiValor', 0))
    valor_total = limpar_valor_monetario(dados_proposta.get('comercial', {}).get('valorTotal', 0))
    
    if valor_total == 0:
        valor_total = custo_direto + bdi_valor
    
    componentes_financeiros = [
        ('Serviços', total_servicos, total_servicos/valor_total if valor_total > 0 else 0),
        ('Mão de Obra', total_mo, total_mo/valor_total if valor_total > 0 else 0),
        ('Materiais', total_mat, total_mat/valor_total if valor_total > 0 else 0),
        ('Equipamentos', total_equip, total_equip/valor_total if valor_total > 0 else 0),
        ('Custo Direto', custo_direto, custo_direto/valor_total if valor_total > 0 else 0),
        ('BDI', bdi_valor, bdi_percentual/100),
    ]
    
    for componente, valor, percentual in componentes_financeiros:
        ws_resumo[f'B{row}'] = componente
        ws_resumo[f'C{row}'] = valor
        ws_resumo[f'C{row}'].style = 'currency_style'
        ws_resumo[f'D{row}'] = percentual
        ws_resumo[f'D{row}'].style = 'percent_style'
        
        for col in ['B', 'C', 'D']:
            ws_resumo[f'{col}{row}'].border = thin_border
            
        if componente == 'Custo Direto':
            for col in ['B', 'C', 'D']:
                ws_resumo[f'{col}{row}'].font = Font(bold=True, italic=True)
                ws_resumo[f'{col}{row}'].fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        
        row += 1
    
    # Valor Total
    ws_resumo[f'B{row}'] = 'VALOR TOTAL'
    ws_resumo[f'C{row}'] = valor_total
    ws_resumo[f'C{row}'].style = 'currency_style'
    ws_resumo[f'D{row}'] = 1.0
    ws_resumo[f'D{row}'].style = 'percent_style'
    
    for col in ['B', 'C', 'D']:
        ws_resumo[f'{col}{row}'].font = Font(name='Arial', size=12, bold=True, color="FFFFFF")
        ws_resumo[f'{col}{row}'].fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        ws_resumo[f'{col}{row}'].border = thick_border
    
    # Informações adicionais
    row += 3
    ws_resumo[f'B{row}'] = 'CONDIÇÕES COMERCIAIS'
    ws_resumo[f'B{row}'].font = subtitle_font
    ws_resumo.merge_cells(f'B{row}:E{row}')
    
    row += 2
    condicoes = [
        ('Prazo de Execução:', dados_proposta.get('tecnica', {}).get('prazoExecucao', 'N/A')),
        ('Validade da Proposta:', dados_proposta.get('comercial', {}).get('validadeProposta', '60 dias')),
        ('Condições de Pagamento:', dados_proposta.get('resumo', {}).get('formaPagamento', 'A definir')),
        ('Data da Proposta:', datetime.now().strftime('%d/%m/%Y'))
    ]
    
    for label, value in condicoes:
        ws_resumo[f'B{row}'] = label
        ws_resumo[f'B{row}'].font = label_font
        ws_resumo[f'C{row}'] = value
        ws_resumo[f'C{row}'].font = normal_font
        ws_resumo.merge_cells(f'C{row}:D{row}')
        row += 1
    
    # Continuação das outras abas (Serviços, Mão de Obra, etc.)
    # ... [código das outras abas do Excel]
    
    # Salvar em memória
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer

def gerar_word_proposta_profissional(dados_proposta):
    """Gera arquivo Word profissional com a proposta técnica - CONTINUAÇÃO"""
    doc = Document()
    
    # Configurar margens
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)
    
    # =================================
    # CAPA
    # =================================
    # Espaço superior
    for _ in range(5):
        doc.add_paragraph()
    
    # Título principal
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run('PROPOSTA TÉCNICA')
    run.font.name = 'Arial'
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(31, 73, 125)
    
    doc.add_paragraph()
    
    # Subtítulo
    subtitulo = doc.add_paragraph()
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitulo.add_run('E')
    run.font.name = 'Arial'
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(31, 73, 125)
    
    doc.add_paragraph()
    
    titulo2 = doc.add_paragraph()
    titulo2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo2.add_run('COMERCIAL')
    run.font.name = 'Arial'
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(31, 73, 125)
    
    # Linha decorativa
    for _ in range(3):
        doc.add_paragraph()
    
    p = doc.add_paragraph('_' * 50)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Processo
    for _ in range(3):
        doc.add_paragraph()
    
    processo_p = doc.add_paragraph()
    processo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = processo_p.add_run(f"PROCESSO: {dados_proposta.get('processo', 'N/A')}")
    run.font.name = 'Arial'
    run.font.size = Pt(18)
    run.font.bold = True
    
    # Empresa
    doc.add_paragraph()
    empresa_p = doc.add_paragraph()
    empresa_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = empresa_p.add_run(dados_proposta.get('dados', {}).get('razaoSocial', '').upper())
    run.font.name = 'Arial'
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = RGBColor(68, 114, 196)
    
    # Data
    for _ in range(5):
        doc.add_paragraph()
    
    data_p = doc.add_paragraph()
    data_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = data_p.add_run(datetime.now().strftime('%B de %Y').upper())
    run.font.name = 'Arial'
    run.font.size = Pt(14)
    
    # Quebra de página
    doc.add_page_break()
    
    # Continuação do documento...
    # [código continua com índice, seções, etc.]
    
    # Salvar em memória
    docx_buffer = io.BytesIO()
    doc.save(docx_buffer)
    docx_buffer.seek(0)
    
    return docx_buffer

# ===== ROTAS DA API =====

@app.route('/')
def index():
    """Página inicial com informações da API"""
    return jsonify({
        'api': 'Sistema de Gestão de Propostas',
        'versao': '2.0',
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

@app.route('/api/status')
def status():
    """Verificar status da API"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'total_propostas': len(propostas_db),
        'total_processos': len(processos_db)
    })

@app.route('/api/enviar-proposta', methods=['POST'])
def enviar_proposta():
    """Receber e processar nova proposta com envio de e-mail melhorado"""
    try:
        dados = request.json
        protocolo = dados.get('protocolo')
        processo = dados.get('processo')
        
        if not protocolo or not processo:
            return jsonify({
                'success': False,
                'erro': 'Protocolo e processo são obrigatórios'
            }), 400
        
        # Verificar se a empresa já enviou proposta
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
        
        # Gerar arquivos
        arquivos_gerados = False
        email_enviado = False
        mensagem_erro = ""
        
        try:
            logger.info(f"Gerando arquivos para proposta {protocolo}")
            
            # Gerar Excel
            excel_buffer = gerar_excel_proposta_profissional(dados)
            excel_buffer.seek(0)
            
            # Gerar Word
            word_buffer = gerar_word_proposta_profissional(dados)
            word_buffer.seek(0)
            
            # Salvar localmente
            excel_path = os.path.join(PROPOSTAS_DIR, f'{protocolo}_comercial.xlsx')
            word_path = os.path.join(PROPOSTAS_DIR, f'{protocolo}_tecnica.docx')
            json_path = os.path.join(PROPOSTAS_DIR, f'{protocolo}_completa.json')
            
            with open(excel_path, 'wb') as f:
                f.write(excel_buffer.getvalue())
            
            with open(word_path, 'wb') as f:
                f.write(word_buffer.getvalue())
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            arquivos_gerados = True
            logger.info("Arquivos gerados com sucesso")
            
            # Enviar e-mails
            if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
                try:
                    # 1. E-mail para o fornecedor
                    email_fornecedor = dados.get('dados', {}).get('email', '')
                    if email_fornecedor:
                        enviar_email_fornecedor(email_fornecedor, protocolo, processo, dados)
                    
                    # 2. E-mail para suprimentos com anexos
                    excel_buffer.seek(0)
                    word_buffer.seek(0)
                    
                    enviar_email_suprimentos(protocolo, processo, dados, excel_buffer, word_buffer)
                    
                    email_enviado = True
                    logger.info("E-mails enviados com sucesso")
                    
                except Exception as e:
                    logger.error(f"Erro ao enviar e-mail: {e}")
                    mensagem_erro = str(e)
            
        except Exception as e:
            logger.error(f"Erro ao gerar arquivos: {e}")
            mensagem_erro = str(e)
        
        # Resposta
        proposta_resumo = {
            'protocolo': protocolo,
            'processo': processo,
            'empresa': dados.get('dados', {}).get('razaoSocial', ''),
            'cnpj': cnpj,
            'data': datetime.now().isoformat(),
            'valor': dados.get('comercial', {}).get('valorTotal', 'R$ 0,00'),
            'prazo': dados.get('tecnica', {}).get('prazoExecucao', 'N/A'),
            'arquivos_gerados': arquivos_gerados,
            'email_enviado': email_enviado
        }
        
        resposta = {
            'success': True,
            'protocolo': protocolo,
            'mensagem': 'Proposta enviada com sucesso',
            'email_enviado': email_enviado,
            'arquivos_gerados': arquivos_gerados,
            'proposta_resumo': proposta_resumo
        }
        
        if mensagem_erro:
            resposta['aviso'] = f'Alguns serviços falharam: {mensagem_erro}'
        
        return jsonify(resposta)
        
    except Exception as e:
        logger.error(f"Erro ao processar proposta: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

def enviar_email_fornecedor(email, protocolo, processo, dados):
    """Envia e-mail de confirmação para o fornecedor"""
    msg = Message(
        subject=f'Confirmação - Proposta {protocolo}',
        recipients=[email],
        html=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #3498db; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f8f9fa; padding: 20px; }}
                .success {{ color: #27ae60; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Proposta Enviada com Sucesso!</h1>
                </div>
                <div class="content">
                    <p>Prezado(a) {dados.get('dados', {}).get('razaoSocial', 'Fornecedor')},</p>
                    
                    <p>Sua proposta foi recebida com sucesso em nosso sistema.</p>
                    
                    <h3>Dados da Proposta:</h3>
                    <ul>
                        <li><strong>Protocolo:</strong> {protocolo}</li>
                        <li><strong>Processo:</strong> {processo}</li>
                        <li><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M')}</li>
                        <li><strong>Valor Total:</strong> R$ {dados.get('comercial', {}).get('valorTotal', 'N/A')}</li>
                        <li><strong>Prazo:</strong> {dados.get('tecnica', {}).get('prazoExecucao', 'N/A')}</li>
                    </ul>
                    
                    <p>Você será notificado sobre o andamento do processo.</p>
                    
                    <p>Atenciosamente,<br>
                    Setor de Suprimentos</p>
                </div>
            </div>
        </body>
        </html>
        """
    )
    mail.send(msg)

def enviar_email_suprimentos(protocolo, processo, dados, excel_buffer, word_buffer):
    """Envia e-mail para suprimentos com os anexos"""
    msg = Message(
        subject=f'Nova Proposta - {processo} - {dados.get("dados", {}).get("razaoSocial", "")}',
        recipients=[EMAIL_CONFIG['destinatario_principal']] + EMAIL_CONFIG['destinatarios_copia']
    )
    
    # HTML do e-mail
    msg.html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; }}
            .content {{ padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
            th {{ background: #3498db; color: white; }}
            .valor {{ font-size: 24px; color: #27ae60; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📋 Nova Proposta Recebida</h1>
        </div>
        <div class="content">
            <table>
                <tr><th>Protocolo</th><td>{protocolo}</td></tr>
                <tr><th>Processo</th><td>{processo}</td></tr>
                <tr><th>Empresa</th><td>{dados.get('dados', {}).get('razaoSocial', '')}</td></tr>
                <tr><th>CNPJ</th><td>{dados.get('dados', {}).get('cnpj', '')}</td></tr>
                <tr><th>Responsável</th><td>{dados.get('dados', {}).get('respTecnico', '')}</td></tr>
                <tr><th>E-mail</th><td>{dados.get('dados', {}).get('email', '')}</td></tr>
                <tr><th>Telefone</th><td>{dados.get('dados', {}).get('telefone', '')}</td></tr>
            </table>
            
            <h2>Resumo Financeiro</h2>
            <p class="valor">Valor Total: R$ {dados.get('comercial', {}).get('valorTotal', 'N/A')}</p>
            <p><strong>Prazo de Execução:</strong> {dados.get('tecnica', {}).get('prazoExecucao', 'N/A')}</p>
            
            <h3>📎 Anexos:</h3>
            <ul>
                <li>Proposta Comercial Detalhada (Excel)</li>
                <li>Proposta Técnica Completa (Word)</li>
                <li>Dados Completos (JSON)</li>
            </ul>
            
            <p><em>Recebido em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</em></p>
        </div>
    </body>
    </html>
    """
    
    # Anexar arquivos
    msg.attach(
        f'{protocolo}_proposta_comercial.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        excel_buffer.read()
    )
    
    msg.attach(
        f'{protocolo}_proposta_tecnica.docx',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        word_buffer.read()
    )
    
    # Anexar JSON
    json_data = json.dumps(dados, ensure_ascii=False, indent=2)
    msg.attach(
        f'{protocolo}_dados_completos.json',
        'application/json',
        json_data.encode('utf-8')
    )
    
    mail.send(msg)
