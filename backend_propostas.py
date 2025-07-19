# backend_propostas_corrigido.py
# Versão corrigida para deploy no Render

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime
import os
import json
import io
import logging
from werkzeug.exceptions import RequestEntityTooLarge

# Imports para Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, NamedStyle, Border, Side
from openpyxl.utils import get_column_letter

# Imports para Word
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Imports para email com fallback
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
from email.header import Header

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["*"])  # Permitir todas as origens em produção

# Configurações do Flask
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configuração do servidor de e-mail usando variáveis de ambiente
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', '')

# Configurar Flask-Mail apenas se houver credenciais
if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
    mail = Mail(app)
    logger.info("Flask-Mail configurado com sucesso")
else:
    mail = None
    logger.warning("Flask-Mail não configurado - variáveis de ambiente ausentes")

# E-mail do setor de suprimentos
EMAIL_SUPRIMENTOS = os.environ.get('EMAIL_SUPRIMENTOS', os.environ.get('EMAIL_CC', 'suprimentos@empresa.com'))

# Diretório para salvar propostas
PROPOSTAS_DIR = os.path.join(os.path.dirname(__file__), 'propostas')
os.makedirs(PROPOSTAS_DIR, exist_ok=True)

# Bases de dados em memória
propostas_db = {}
processos_db = {}

# Template HTML para e-mail do elaborador
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }
        .info-box { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
        h1 { margin: 0; }
        strong { color: #667eea; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Proposta Enviada com Sucesso!</h1>
        </div>
        <div class="content">
            <p>Prezado(a) <strong>{{ responsavel }}</strong>,</p>
            <p>Confirmamos o recebimento de sua proposta comercial.</p>
            
            <div class="info-box">
                <h3>📋 Detalhes da Proposta:</h3>
                <p><strong>Protocolo:</strong> {{ protocolo }}<br>
                <strong>Empresa:</strong> {{ empresa }}<br>
                <strong>CNPJ:</strong> {{ cnpj }}<br>
                <strong>Processo:</strong> {{ processo }}<br>
                <strong>Valor Total:</strong> R$ {{ valor_total }}<br>
                <strong>Data/Hora:</strong> {{ data_envio }}</p>
            </div>
            
            <p>Sua proposta foi encaminhada para análise. Você receberá atualizações sobre o andamento do processo.</p>
            
            <div class="footer">
                <p>Este é um e-mail automático. Por favor, não responda.</p>
                <p>Em caso de dúvidas, entre em contato com o setor de suprimentos.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Template HTML para e-mail de suprimentos
EMAIL_SUPRIMENTOS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 700px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #f5a623 0%, #f76b1c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 10px 10px; }
        .alert { background: #fff3cd; border: 1px solid #ffeeba; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: bold; color: #495057; }
        .attachments { background: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0; }
        h1 { margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔔 Nova Proposta Recebida</h1>
        </div>
        <div class="content">
            <div class="alert">
                <strong>⚠️ ATENÇÃO:</strong> Nova proposta comercial recebida para análise.
            </div>
            
            <h2>Informações da Proposta</h2>
            <table>
                <tr><th>Protocolo:</th><td><strong>{{ protocolo }}</strong></td></tr>
                <tr><th>Processo:</th><td>{{ processo }}</td></tr>
                <tr><th>Empresa:</th><td>{{ empresa }}</td></tr>
                <tr><th>CNPJ:</th><td>{{ cnpj }}</td></tr>
                <tr><th>Responsável:</th><td>{{ responsavel }}</td></tr>
                <tr><th>E-mail:</th><td>{{ email }}</td></tr>
                <tr><th>Telefone:</th><td>{{ telefone }}</td></tr>
            </table>
            
            <h2>Resumo Financeiro</h2>
            <table>
                <tr><th>Valor Total:</th><td><strong>R$ {{ valor_total }}</strong></td></tr>
                <tr><th>Prazo de Execução:</th><td>{{ prazo }}</td></tr>
                <tr><th>Condição de Pagamento:</th><td>{{ pagamento }}</td></tr>
                <tr><th>Validade da Proposta:</th><td>{{ validade }}</td></tr>
            </table>
            
            <div class="attachments">
                <strong>📎 ANEXOS:</strong><br>
                ✓ Proposta Comercial (Excel)<br>
                ✓ Proposta Técnica (Word)<br>
                ✓ Dados Completos (JSON)
            </div>
            
            <p><strong>Ação Necessária:</strong> Analisar a proposta e incluir no processo licitatório.</p>
        </div>
    </div>
</body>
</html>
"""

def enviar_email_com_anexos(destinatario, assunto, corpo_html, anexos=None):
    """Função robusta para envio de email com fallback"""
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        logger.warning("Credenciais de email não configuradas")
        return False
    
    try:
        if mail:
            # Tentar com Flask-Mail
            msg = Message(
                subject=assunto,
                recipients=[destinatario],
                html=corpo_html
            )
            
            if anexos:
                for nome_arquivo, tipo_mime, conteudo in anexos:
                    msg.attach(nome_arquivo, tipo_mime, conteudo)
            
            mail.send(msg)
            logger.info(f"Email enviado com sucesso via Flask-Mail para {destinatario}")
            return True
            
    except Exception as e:
        logger.error(f"Erro Flask-Mail: {e}")
        
        # Fallback para SMTP direto
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr(('Sistema de Propostas', app.config['MAIL_USERNAME']))
            msg['To'] = destinatario
            msg['Subject'] = Header(assunto, 'utf-8')
            
            msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
            
            if anexos:
                for nome_arquivo, tipo_mime, conteudo in anexos:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(conteudo)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{nome_arquivo}"'
                    )
                    msg.attach(part)
            
            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email enviado com sucesso via SMTP direto para {destinatario}")
            return True
            
        except Exception as e2:
            logger.error(f"Erro SMTP direto: {e2}")
            return False

def gerar_excel_proposta_profissional(dados_proposta):
    """Gera arquivo Excel profissional com a proposta comercial"""
    wb = Workbook()
    
    # Remove planilha padrão
    wb.remove(wb.active)
    
    # Estilos personalizados
    header_font = Font(name='Arial', size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    title_font = Font(name='Arial', size=16, bold=True, color="1F497D")
    subtitle_font = Font(name='Arial', size=12, bold=True, color="1F497D")
    
    # Criar abas
    ws_resumo = wb.create_sheet("Resumo Executivo")
    ws_servicos = wb.create_sheet("Tabela de Serviços")
    ws_mao_obra = wb.create_sheet("Mão de Obra")
    ws_materiais = wb.create_sheet("Materiais")
    ws_equipamentos = wb.create_sheet("Equipamentos")
    ws_bdi = wb.create_sheet("Composição BDI")
    
    # ABA 1 - RESUMO EXECUTIVO
    ws_resumo['A1'] = 'PROPOSTA COMERCIAL'
    ws_resumo['A1'].font = Font(size=20, bold=True, color="1F497D")
    ws_resumo['A1'].alignment = Alignment(horizontal="center")
    ws_resumo.merge_cells('A1:F1')
    
    # Dados da empresa
    ws_resumo['A3'] = 'DADOS DA EMPRESA'
    ws_resumo['A3'].font = subtitle_font
    ws_resumo.merge_cells('A3:C3')
    
    dados_empresa = [
        ('Razão Social:', dados_proposta.get('dados', {}).get('razaoSocial', '')),
        ('CNPJ:', dados_proposta.get('dados', {}).get('cnpj', '')),
        ('Endereço:', dados_proposta.get('dados', {}).get('endereco', '')),
        ('Telefone:', dados_proposta.get('dados', {}).get('telefone', '')),
        ('E-mail:', dados_proposta.get('dados', {}).get('email', ''))
    ]
    
    row = 4
    for label, value in dados_empresa:
        ws_resumo[f'A{row}'] = label
        ws_resumo[f'A{row}'].font = Font(bold=True)
        ws_resumo[f'B{row}'] = value
        ws_resumo.merge_cells(f'B{row}:D{row}')
        row += 1
    
    # Resumo financeiro
    ws_resumo[f'A{row+1}'] = 'RESUMO FINANCEIRO'
    ws_resumo[f'A{row+1}'].font = subtitle_font
    ws_resumo.merge_cells(f'A{row+1}:C{row+1}')
    
    # Calcular totais
    valor_total = dados_proposta.get('comercial', {}).get('valorTotal', 'R$ 0,00')
    prazo = dados_proposta.get('resumo', {}).get('prazoExecucao', 'N/A')
    validade = dados_proposta.get('comercial', {}).get('validadeProposta', '60 dias')
    
    ws_resumo[f'A{row+3}'] = 'Valor Total da Proposta:'
    ws_resumo[f'A{row+3}'].font = Font(bold=True, size=14)
    ws_resumo[f'C{row+3}'] = valor_total
    ws_resumo[f'C{row+3}'].font = Font(bold=True, size=14, color="28a745")
    
    # ABA 2 - TABELA DE SERVIÇOS
    # Cabeçalho
    headers_servicos = ['Item', 'Descrição', 'Unidade', 'Quantidade', 'Valor Unitário', 'Valor Total']
    for col, header in enumerate(headers_servicos, 1):
        cell = ws_servicos.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Dados dos serviços
    servicos = dados_proposta.get('comercial', {}).get('servicos', [])
    row = 2
    for servico in servicos:
        ws_servicos.cell(row=row, column=1, value=row-1)
        ws_servicos.cell(row=row, column=2, value=servico.get('descricao', ''))
        ws_servicos.cell(row=row, column=3, value=servico.get('unidade', ''))
        ws_servicos.cell(row=row, column=4, value=servico.get('quantidade', 0))
        ws_servicos.cell(row=row, column=5, value=servico.get('valorUnitario', 'R$ 0,00'))
        ws_servicos.cell(row=row, column=6, value=servico.get('valorTotal', 'R$ 0,00'))
        row += 1
    
    # Ajustar largura das colunas
    for ws in [ws_resumo, ws_servicos, ws_mao_obra, ws_materiais, ws_equipamentos, ws_bdi]:
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # Salvar em memória
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer

def gerar_word_proposta_profissional(dados_proposta):
    """Gera arquivo Word profissional com a proposta técnica"""
    doc = Document()
    
    # Configurar margens
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)
    
    # CAPA
    for _ in range(5):
        doc.add_paragraph()
    
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run('PROPOSTA TÉCNICA')
    run.font.name = 'Arial'
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = RGBColor(31, 73, 125)
    
    doc.add_paragraph()
    
    processo_p = doc.add_paragraph()
    processo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = processo_p.add_run(f"PROCESSO: {dados_proposta.get('processo', 'N/A')}")
    run.font.name = 'Arial'
    run.font.size = Pt(18)
    run.font.bold = True
    
    doc.add_paragraph()
    
    empresa_p = doc.add_paragraph()
    empresa_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = empresa_p.add_run(dados_proposta.get('dados', {}).get('razaoSocial', '').upper())
    run.font.name = 'Arial'
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = RGBColor(68, 114, 196)
    
    for _ in range(5):
        doc.add_paragraph()
    
    data_p = doc.add_paragraph()
    data_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = data_p.add_run(datetime.now().strftime('%B de %Y').upper())
    run.font.name = 'Arial'
    run.font.size = Pt(14)
    
    doc.add_page_break()
    
    # CONTEÚDO
    doc.add_heading('1. DADOS DA EMPRESA', level=1)
    
    table = doc.add_table(rows=8, cols=2)
    table.style = 'Light Grid Accent 1'
    
    dados_empresa = [
        ('Razão Social:', dados_proposta.get('dados', {}).get('razaoSocial', '')),
        ('CNPJ:', dados_proposta.get('dados', {}).get('cnpj', '')),
        ('Endereço:', dados_proposta.get('dados', {}).get('endereco', '')),
        ('Cidade:', dados_proposta.get('dados', {}).get('cidade', '')),
        ('Telefone:', dados_proposta.get('dados', {}).get('telefone', '')),
        ('E-mail:', dados_proposta.get('dados', {}).get('email', '')),
        ('Responsável Técnico:', dados_proposta.get('dados', {}).get('respTecnico', '')),
        ('CREA/CAU:', dados_proposta.get('dados', {}).get('crea', ''))
    ]
    
    for i, (label, value) in enumerate(dados_empresa):
        table.cell(i, 0).text = label
        table.cell(i, 1).text = value or 'Não informado'
        table.cell(i, 0).paragraphs[0].runs[0].font.bold = True
    
    doc.add_paragraph()
    
    # Seções técnicas
    doc.add_heading('2. OBJETO DA PROPOSTA', level=1)
    doc.add_paragraph(dados_proposta.get('resumo', {}).get('objetoConcorrencia', ''))
    
    doc.add_heading('3. METODOLOGIA DE EXECUÇÃO', level=1)
    doc.add_paragraph(dados_proposta.get('tecnica', {}).get('metodologia', ''))
    
    doc.add_heading('4. EQUIPE TÉCNICA', level=1)
    doc.add_paragraph(dados_proposta.get('tecnica', {}).get('equipeTecnica', ''))
    
    # Salvar em memória
    docx_buffer = io.BytesIO()
    doc.save(docx_buffer)
    docx_buffer.seek(0)
    
    return docx_buffer

# ROTAS DA API

@app.route('/')
def index():
    """Rota principal - retorna informações da API"""
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
            'GET /api/status': 'Status da API',
            'GET /api/download/proposta/<protocolo>/<tipo>': 'Download de proposta'
        }
    })

@app.route('/api/status')
def status():
    """Verificar status da API"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'total_propostas': len(propostas_db),
        'total_processos': len(processos_db),
        'email_configurado': bool(app.config['MAIL_USERNAME'])
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
        try:
            excel_buffer = gerar_excel_proposta_profissional(dados)
            word_buffer = gerar_word_proposta_profissional(dados)
            
            # Salvar arquivos localmente
            excel_path = os.path.join(PROPOSTAS_DIR, f'{protocolo}_proposta.xlsx')
            word_path = os.path.join(PROPOSTAS_DIR, f'{protocolo}_proposta.docx')
            
            with open(excel_path, 'wb') as f:
                f.write(excel_buffer.getvalue())
            
            with open(word_path, 'wb') as f:
                f.write(word_buffer.getvalue())
            
            # Reset buffers para email
            excel_buffer.seek(0)
            word_buffer.seek(0)
            
            # Preparar dados para email
            template_data = {
                'protocolo': protocolo,
                'processo': processo,
                'empresa': dados.get('dados', {}).get('razaoSocial', ''),
                'cnpj': dados.get('dados', {}).get('cnpj', ''),
                'responsavel': dados.get('dados', {}).get('respTecnico', ''),
                'email': dados.get('dados', {}).get('email', ''),
                'telefone': dados.get('dados', {}).get('telefone', ''),
                'valor_total': dados.get('comercial', {}).get('valorTotal', 'R$ 0,00'),
                'prazo': dados.get('resumo', {}).get('prazoExecucao', 'N/A'),
                'pagamento': dados.get('resumo', {}).get('formaPagamento', 'N/A'),
                'validade': dados.get('comercial', {}).get('validadeProposta', '60 dias'),
                'data_envio': datetime.now().strftime('%d/%m/%Y às %H:%M')
            }
            
            # Enviar emails
            email_enviado = False
            if app.config['MAIL_USERNAME']:
                # Email para o elaborador
                html_elaborador = EMAIL_TEMPLATE.replace('{{ protocolo }}', template_data['protocolo'])
                for key, value in template_data.items():
                    html_elaborador = html_elaborador.replace('{{ ' + key + ' }}', str(value))
                
                enviar_email_com_anexos(
                    template_data['email'],
                    f'Confirmação - Proposta {protocolo}',
                    html_elaborador
                )
                
                # Email para suprimentos com anexos
                html_suprimentos = EMAIL_SUPRIMENTOS_TEMPLATE
                for key, value in template_data.items():
                    html_suprimentos = html_suprimentos.replace('{{ ' + key + ' }}', str(value))
                
                anexos = [
                    (f'{protocolo}_proposta_comercial.xlsx', 
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     excel_buffer.read()),
                    (f'{protocolo}_proposta_tecnica.docx',
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     word_buffer.read()),
                    (f'{protocolo}_dados_completos.json',
                     'application/json',
                     json.dumps(dados, ensure_ascii=False, indent=2).encode('utf-8'))
                ]
                
                email_enviado = enviar_email_com_anexos(
                    EMAIL_SUPRIMENTOS,
                    f'NOVA PROPOSTA - {protocolo} - {template_data["empresa"]}',
                    html_suprimentos,
                    anexos
                )
            
        except Exception as e:
            logger.error(f"Erro ao gerar arquivos: {e}")
        
        return jsonify({
            'success': True,
            'protocolo': protocolo,
            'mensagem': 'Proposta enviada com sucesso',
            'email_enviado': email_enviado
        })
        
    except Exception as e:
        logger.error(f"Erro ao enviar proposta: {e}")
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500

@app.route('/api/propostas/listar', methods=['GET'])
def listar_propostas():
    """Listar todas as propostas"""
    try:
        propostas_lista = list(propostas_db.values())
        return jsonify({
            'success': True,
            'propostas': propostas_lista,
            'total': len(propostas_lista)
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
            'objeto': dados.get('objeto', ''),
            'modalidade': dados.get('modalidade', ''),
            'prazo': dados.get('prazo', ''),
            'valorEstimado': dados.get('valorEstimado', ''),
            'dataCadastro': datetime.now().isoformat(),
            'criadoPor': dados.get('criadoPor', 'sistema')
        }
        
        return jsonify({
            'success': True,
            'processo': processos_db[numero]
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

@app.route('/api/download/proposta/<protocolo>/<tipo>', methods=['GET'])
def download_proposta(protocolo, tipo):
    """Download de proposta em Excel ou Word"""
    try:
        proposta = propostas_db.get(protocolo)
        
        if not proposta:
            return jsonify({
                'success': False,
                'erro': 'Proposta não encontrada'
            }), 404
        
        if tipo == 'excel':
            arquivo = f'{protocolo}_proposta.xlsx'
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif tipo == 'word':
            arquivo = f'{protocolo}_proposta.docx'
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            return jsonify({
                'success': False,
                'erro': 'Tipo inválido. Use excel ou word'
            }), 400
        
        caminho_arquivo = os.path.join(PROPOSTAS_DIR, arquivo)
        
        if not os.path.exists(caminho_arquivo):
            return jsonify({
                'success': False,
                'erro': 'Arquivo não encontrado'
            }), 404
        
        return send_file(
            caminho_arquivo,
            mimetype=mimetype,
            as_attachment=True,
            download_name=arquivo
        )
        
    except Exception as e:
        logger.error(f"Erro ao fazer download: {e}")
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
    logger.error(f"Erro interno: {error}")
    return jsonify({
        'success': False,
        'erro': 'Erro interno do servidor'
    }), 500

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({
        'success': False,
        'erro': 'Arquivo muito grande. Máximo permitido: 16MB'
    }), 413

# Health check para o Render
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    # Configurações para produção no Render
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Iniciando servidor na porta {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Email configurado: {bool(app.config['MAIL_USERNAME'])}")
    
    # Criar processo de exemplo se estiver em debug
    if debug:
        processos_db['LIC-2025-001'] = {
            'numero': 'LIC-2025-001',
            'objeto': 'Construção de Complexo Comercial - 5.000m²',
            'modalidade': 'Concorrência',
            'prazo': '2025-08-30T17:00:00',
            'dataCadastro': datetime.now().isoformat(),
            'criadoPor': 'admin'
        }
        logger.info("Processo de exemplo criado")
    
    # Iniciar servidor
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
