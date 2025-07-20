#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, send_from_directory, render_template_string, send_file
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import json
import os
import uuid
import logging
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from openpyxl import Workbook
from openpyxl.styles import Font, Fill, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io
import base64

# Configuração do Flask
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json; charset=utf-8'
CORS(app)

# Configuração de Email
app.config['MAIL_SERVER'] = os.environ.get('EMAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('EMAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER', '')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER', '')

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
    'destinatario_principal': os.environ.get('EMAIL_SUPRIMENTOS', 'portaldofornecedor.arias@gmail.com')
}

def inicializar_dados_exemplo():
    """Inicializa dados de exemplo para demonstração"""
    global processos_db, fornecedores_db
    
    # Dados de exemplo de processos
    agora = datetime.now()
    processos_exemplo = [
        {
            "numero": "001/2025",
            "objeto": "Construção de Escola Municipal",
            "modalidade": "Concorrência",
            "prazo": (agora + timedelta(days=15)).isoformat(),
            "valor_estimado": "R$ 2.500.000,00",
            "status": "ativo"
        },
        {
            "numero": "002/2025", 
            "objeto": "Reforma do Centro de Saúde",
            "modalidade": "Tomada de Preços",
            "prazo": (agora + timedelta(days=10)).isoformat(),
            "valor_estimado": "R$ 850.000,00",
            "status": "ativo"
        },
        {
            "numero": "003/2025",
            "objeto": "Pavimentação de Ruas",
            "modalidade": "Concorrência", 
            "prazo": (agora + timedelta(days=20)).isoformat(),
            "valor_estimado": "R$ 1.200.000,00",
            "status": "ativo"
        }
    ]
    
    # Adicionar aos processos_db
    for processo in processos_exemplo:
        processos_db[processo["numero"]] = processo
    
    # Dados de exemplo de fornecedores
    fornecedores_exemplo = [
        {
            "cnpj": "12.345.678/0001-90",
            "razaoSocial": "Construtora Exemplo LTDA",
            "email": "contato@exemplo.com.br",
            "telefone": "(11) 99999-9999",
            "status": "ativo"
        }
    ]
    
    # Adicionar aos fornecedores_db
    for fornecedor in fornecedores_exemplo:
        fornecedores_db[fornecedor["cnpj"]] = fornecedor
    
    logger.info(f"Dados de exemplo inicializados: {len(processos_db)} processos, {len(fornecedores_db)} fornecedores")

# Inicializar dados de exemplo
inicializar_dados_exemplo()

def gerar_excel_proposta(dados_proposta):
    """Gera arquivo Excel com a proposta comercial"""
    wb = Workbook()
    
    # Estilos
    header_font = Font(name='Arial', size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    title_font = Font(name='Arial', size=14, bold=True)
    subtitle_font = Font(name='Arial', size=11, bold=True)
    normal_font = Font(name='Arial', size=10)
    
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Aba 1: Resumo
    ws_resumo = wb.active
    ws_resumo.title = "Resumo"
    
    # Cabeçalho
    ws_resumo.merge_cells('A1:F1')
    ws_resumo['A1'] = 'PROPOSTA COMERCIAL'
    ws_resumo['A1'].font = Font(name='Arial', size=16, bold=True)
    ws_resumo['A1'].alignment = Alignment(horizontal="center")
    
    ws_resumo['A3'] = 'Dados da Empresa'
    ws_resumo['A3'].font = subtitle_font
    
    # Dados da empresa
    dados_empresa = [
        ['Razão Social:', dados_proposta.get('dados', {}).get('razaoSocial', '')],
        ['CNPJ:', dados_proposta.get('dados', {}).get('cnpj', '')],
        ['Endereço:', dados_proposta.get('dados', {}).get('endereco', '')],
        ['Cidade:', dados_proposta.get('dados', {}).get('cidade', '')],
        ['Telefone:', dados_proposta.get('dados', {}).get('telefone', '')],
        ['E-mail:', dados_proposta.get('dados', {}).get('email', '')],
        ['Responsável Técnico:', dados_proposta.get('dados', {}).get('respTecnico', '')],
        ['CREA/CAU:', dados_proposta.get('dados', {}).get('crea', '')]
    ]
    
    row = 5
    for label, value in dados_empresa:
        ws_resumo[f'A{row}'] = label
        ws_resumo[f'A{row}'].font = Font(bold=True)
        ws_resumo[f'B{row}'] = value
        ws_resumo.merge_cells(f'B{row}:D{row}')
        row += 1
    
    # Resumo financeiro
    ws_resumo[f'A{row+2}'] = 'Resumo Financeiro'
    ws_resumo[f'A{row+2}'].font = subtitle_font
    
    row += 4
    resumo_financeiro = [
        ['Mão de Obra:', dados_proposta.get('comercial', {}).get('totalMaoObra', '0,00')],
        ['Materiais:', dados_proposta.get('comercial', {}).get('totalMateriais', '0,00')],
        ['Equipamentos:', dados_proposta.get('comercial', {}).get('totalEquipamentos', '0,00')],
        ['BDI:', f"{dados_proposta.get('comercial', {}).get('bdiPercentual', '0')}% = R$ {dados_proposta.get('comercial', {}).get('bdiValor', '0,00')}"],
        ['VALOR TOTAL:', f"R$ {dados_proposta.get('comercial', {}).get('valorTotal', '0,00')}"]
    ]
    
    for label, value in resumo_financeiro:
        ws_resumo[f'A{row}'] = label
        ws_resumo[f'A{row}'].font = Font(bold=True)
        ws_resumo[f'B{row}'] = value
        ws_resumo.merge_cells(f'B{row}:D{row}')
        if label == 'VALOR TOTAL:':
            ws_resumo[f'A{row}'].font = Font(bold=True, size=12, color="FF0000")
            ws_resumo[f'B{row}'].font = Font(bold=True, size=12, color="FF0000")
        row += 1
    
    # Aba 2: Serviços
    if dados_proposta.get('comercial', {}).get('servicos'):
        ws_servicos = wb.create_sheet("Serviços")
        
        # Cabeçalho
        headers = ['Item', 'Descrição', 'Unidade', 'Quantidade', 'Preço Unit.', 'Total']
        for col, header in enumerate(headers, 1):
            cell = ws_servicos.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        # Dados
        row = 2
        for servico in dados_proposta['comercial']['servicos']:
            for col, value in enumerate(servico[:6], 1):
                cell = ws_servicos.cell(row=row, column=col, value=value)
                cell.border = border
                if col >= 4:  # Colunas numéricas
                    cell.alignment = Alignment(horizontal="right")
            row += 1
        
        # Total
        ws_servicos[f'E{row}'] = 'TOTAL:'
        ws_servicos[f'E{row}'].font = Font(bold=True)
        ws_servicos[f'F{row}'] = f"R$ {dados_proposta.get('comercial', {}).get('totalServicos', '0,00')}"
        ws_servicos[f'F{row}'].font = Font(bold=True)
        
        # Ajustar largura das colunas
        ws_servicos.column_dimensions['B'].width = 50
        for col in ['C', 'D', 'E', 'F']:
            ws_servicos.column_dimensions[col].width = 15
    
    # Aba 3: Mão de Obra
    if dados_proposta.get('comercial', {}).get('maoObra'):
        ws_mo = wb.create_sheet("Mão de Obra")
        
        headers = ['Função', 'Qtd', 'Tempo', 'Salário', 'Encargos %', 'Total Mensal', 'Total Geral']
        for col, header in enumerate(headers, 1):
            cell = ws_mo.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        row = 2
        for mo in dados_proposta['comercial']['maoObra']:
            for col, value in enumerate(mo[:7], 1):
                cell = ws_mo.cell(row=row, column=col, value=value)
                cell.border = border
                if col >= 2:
                    cell.alignment = Alignment(horizontal="right")
            row += 1
        
        ws_mo[f'F{row}'] = 'TOTAL:'
        ws_mo[f'F{row}'].font = Font(bold=True)
        ws_mo[f'G{row}'] = f"R$ {dados_proposta.get('comercial', {}).get('totalMaoObra', '0,00')}"
        ws_mo[f'G{row}'].font = Font(bold=True)
    
    # Aba 4: Materiais
    if dados_proposta.get('comercial', {}).get('materiaisComercial'):
        ws_mat = wb.create_sheet("Materiais")
        
        headers = ['Material', 'Especificação', 'Unidade', 'Quantidade', 'Preço Unit.', 'Total']
        for col, header in enumerate(headers, 1):
            cell = ws_mat.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        row = 2
        for material in dados_proposta['comercial']['materiaisComercial']:
            for col, value in enumerate(material[:6], 1):
                cell = ws_mat.cell(row=row, column=col, value=value)
                cell.border = border
                if col >= 4:
                    cell.alignment = Alignment(horizontal="right")
            row += 1
        
        ws_mat[f'E{row}'] = 'TOTAL:'
        ws_mat[f'E{row}'].font = Font(bold=True)
        ws_mat[f'F{row}'] = f"R$ {dados_proposta.get('comercial', {}).get('totalMateriais', '0,00')}"
        ws_mat[f'F{row}'].font = Font(bold=True)
    
    # Aba 5: Equipamentos
    if dados_proposta.get('comercial', {}).get('equipamentosComercial'):
        ws_equip = wb.create_sheet("Equipamentos")
        
        headers = ['Equipamento', 'Especificação', 'Quantidade', 'Tempo', 'Preço/mês', 'Total']
        for col, header in enumerate(headers, 1):
            cell = ws_equip.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        row = 2
        for equip in dados_proposta['comercial']['equipamentosComercial']:
            for col, value in enumerate(equip[:6], 1):
                cell = ws_equip.cell(row=row, column=col, value=value)
                cell.border = border
                if col >= 3:
                    cell.alignment = Alignment(horizontal="right")
            row += 1
        
        ws_equip[f'E{row}'] = 'TOTAL:'
        ws_equip[f'E{row}'].font = Font(bold=True)
        ws_equip[f'F{row}'] = f"R$ {dados_proposta.get('comercial', {}).get('totalEquipamentos', '0,00')}"
        ws_equip[f'F{row}'].font = Font(bold=True)
    
    # Aba 6: BDI
    if dados_proposta.get('comercial', {}).get('bdi'):
        ws_bdi = wb.create_sheet("BDI")
        
        headers = ['Componente', 'Percentual %', 'Valor R$']
        for col, header in enumerate(headers, 1):
            cell = ws_bdi.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        row = 2
        for bdi_item in dados_proposta['comercial']['bdi']:
            for col, value in enumerate(bdi_item[:3], 1):
                cell = ws_bdi.cell(row=row, column=col, value=value)
                cell.border = border
                if col >= 2:
                    cell.alignment = Alignment(horizontal="right")
            row += 1
        
        # Total BDI
        ws_bdi[f'A{row+1}'] = 'BDI TOTAL:'
        ws_bdi[f'B{row+1}'] = f"{dados_proposta.get('comercial', {}).get('bdiPercentual', '0')}%"
        ws_bdi[f'C{row+1}'] = f"R$ {dados_proposta.get('comercial', {}).get('bdiValor', '0,00')}"
        for col in range(1, 4):
            ws_bdi.cell(row=row+1, column=col).font = Font(bold=True, size=12)
    
    # Salvar em memória
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer

def gerar_word_proposta(dados_proposta):
    """Gera arquivo Word com a proposta técnica"""
    doc = Document()
    
    # Configurar margens
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Título principal
    titulo = doc.add_heading('PROPOSTA TÉCNICA', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Dados da empresa
    doc.add_heading('1. DADOS DA EMPRESA', level=1)
    
    table = doc.add_table(rows=8, cols=2)
    table.style = 'Table Grid'
    
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
    
    for i, (label, value) in enumerate(dados_empresa):
        table.cell(i, 0).text = label
        table.cell(i, 0).paragraphs[0].runs[0].bold = True
        table.cell(i, 1).text = str(value)
    
    # Objeto
    doc.add_heading('2. OBJETO DA CONCORRÊNCIA', level=1)
    doc.add_paragraph(dados_proposta.get('tecnica', {}).get('objetoConcorrencia', ''))
    
    # Escopo
    if dados_proposta.get('tecnica', {}).get('escopoInclusos'):
        doc.add_heading('3. ESCOPO DOS SERVIÇOS', level=1)
        doc.add_heading('3.1 Serviços Inclusos:', level=2)
        doc.add_paragraph(dados_proposta['tecnica']['escopoInclusos'])
    
    if dados_proposta.get('tecnica', {}).get('escopoExclusos'):
        doc.add_heading('3.2 Serviços Exclusos:', level=2)
        doc.add_paragraph(dados_proposta['tecnica']['escopoExclusos'])
    
    # Metodologia
    if dados_proposta.get('tecnica', {}).get('metodologia'):
        doc.add_heading('4. METODOLOGIA DE EXECUÇÃO', level=1)
        doc.add_paragraph(dados_proposta['tecnica']['metodologia'])
    
    if dados_proposta.get('tecnica', {}).get('sequenciaExecucao'):
        doc.add_heading('4.1 Sequência de Execução:', level=2)
        doc.add_paragraph(dados_proposta['tecnica']['sequenciaExecucao'])
    
    # Prazo
    doc.add_heading('5. PRAZO DE EXECUÇÃO', level=1)
    prazo_exec = dados_proposta.get('tecnica', {}).get('prazoExecucao', 'Não informado')
    doc.add_paragraph(f'Prazo total para execução dos serviços: {prazo_exec}')
    
    if dados_proposta.get('tecnica', {}).get('prazoMobilizacao'):
        doc.add_paragraph(f'Prazo de mobilização: {dados_proposta["tecnica"]["prazoMobilizacao"]}')
    
    # Cronograma
    if dados_proposta.get('tecnica', {}).get('cronograma'):
        doc.add_heading('6. CRONOGRAMA DE EXECUÇÃO', level=1)
        
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        
        # Cabeçalho
        hdr_cells = table.rows[0].cells
        headers = ['Atividade', 'Duração', 'Início', 'Fim']
        for i, header in enumerate(headers):
            hdr_cells[i].text = header
            hdr_cells[i].paragraphs[0].runs[0].bold = True
        
        # Dados
        for atividade in dados_proposta['tecnica']['cronograma']:
            row_cells = table.add_row().cells
            for i in range(min(4, len(atividade))):
                row_cells[i].text = str(atividade[i])
    
    # Equipe técnica
    if dados_proposta.get('tecnica', {}).get('equipe'):
        doc.add_heading('7. EQUIPE TÉCNICA', level=1)
        
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        
        hdr_cells = table.rows[0].cells
        headers = ['Função', 'Quantidade', 'Tempo (meses)']
        for i, header in enumerate(headers):
            hdr_cells[i].text = header
            hdr_cells[i].paragraphs[0].runs[0].bold = True
        
        for membro in dados_proposta['tecnica']['equipe']:
            row_cells = table.add_row().cells
            for i in range(min(3, len(membro))):
                row_cells[i].text = str(membro[i])
    
    # Experiência
    if dados_proposta.get('tecnica', {}).get('experiencia'):
        doc.add_heading('8. EXPERIÊNCIA DA EMPRESA', level=1)
        
        for i, obra in enumerate(dados_proposta['tecnica']['experiencia'], 1):
            doc.add_heading(f'8.{i} Obra {i}:', level=2)
            if len(obra) > 0 and obra[0]:
                doc.add_paragraph(f'Obra: {obra[0]}')
            if len(obra) > 1 and obra[1]:
                doc.add_paragraph(f'Cliente: {obra[1]}')
            if len(obra) > 2 and obra[2]:
                doc.add_paragraph(f'Valor: {obra[2]}')
            if len(obra) > 3 and obra[3]:
                doc.add_paragraph(f'Ano: {obra[3]}')
    
    # Garantias
    if dados_proposta.get('tecnica', {}).get('garantias'):
        doc.add_heading('9. GARANTIAS OFERECIDAS', level=1)
        doc.add_paragraph(dados_proposta['tecnica']['garantias'])
    
    # Rodapé com data
    doc.add_paragraph()
    doc.add_paragraph()
    data_proposta = doc.add_paragraph(f'Data da Proposta: {datetime.now().strftime("%d/%m/%Y")}')
    data_proposta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Salvar em memória
    word_buffer = io.BytesIO()
    doc.save(word_buffer)
    word_buffer.seek(0)
    
    return word_buffer

def enviar_email_proposta(protocolo, dados_proposta):
    """Envia email com os dados da proposta e anexos Excel e Word"""
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        logger.warning("Configurações de email não definidas")
        return False
    
    try:
        # Gerar anexos
        excel_buffer = gerar_excel_proposta(dados_proposta)
        word_buffer = gerar_word_proposta(dados_proposta)
        
        # Criar mensagem
        msg = Message(
            subject=f"Nova Proposta Recebida - {protocolo}",
            recipients=[EMAIL_CONFIG['destinatario_principal']]
        )
        
        # Extrai informações principais
        empresa = dados_proposta.get('dados', {}).get('razaoSocial', 'N/A')
        cnpj = dados_proposta.get('dados', {}).get('cnpj', 'N/A')
        valor_total = dados_proposta.get('comercial', {}).get('valorTotal', '0,00')
        processo = dados_proposta.get('processo', 'N/A')
        prazo = dados_proposta.get('tecnica', {}).get('prazoExecucao', 'N/A')
        
        # Corpo do email em HTML
        msg.html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px;">
                <h2 style="color: #333;">🏢 Nova Proposta Recebida</h2>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin-top: 20px;">
                    <h3 style="color: #2c3e50;">Informações Principais</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Protocolo:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{protocolo}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Processo:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{processo}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Empresa:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{empresa}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>CNPJ:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{cnpj}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>E-mail:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{dados_proposta.get('dados', {}).get('email', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Telefone:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{dados_proposta.get('dados', {}).get('telefone', 'N/A')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Prazo de Execução:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{prazo}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px;"><strong>Valor Total:</strong></td>
                            <td style="padding: 8px; color: #27ae60; font-size: 18px;"><strong>R$ {valor_total}</strong></td>
                        </tr>
                    </table>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #e8f5e9; border-radius: 5px;">
                    <p style="margin: 0;"><strong>📎 Anexos:</strong></p>
                    <ul>
                        <li>Proposta Comercial Detalhada (Excel)</li>
                        <li>Proposta Técnica Completa (Word)</li>
                    </ul>
                </div>
                
                <p style="text-align: center; color: #666; margin-top: 20px;">
                    <small>Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</small>
                </p>
            </div>
        </body>
        </html>
        """
        
        # Anexar Excel
        msg.attach(
            f"proposta_comercial_{protocolo}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            excel_buffer.getvalue()
        )
        
        # Anexar Word
        msg.attach(
            f"proposta_tecnica_{protocolo}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            word_buffer.getvalue()
        )
        
        # Enviar
        mail.send(msg)
        
        logger.info(f"Email enviado com sucesso para proposta {protocolo}")
        
        # Enviar email de confirmação ao fornecedor
        if dados_proposta.get('dados', {}).get('email'):
            enviar_email_confirmacao_fornecedor(protocolo, dados_proposta)
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email: {str(e)}")
        return False

def enviar_email_confirmacao_fornecedor(protocolo, dados_proposta):
    """Envia email de confirmação para o fornecedor"""
    try:
        email_fornecedor = dados_proposta.get('dados', {}).get('email')
        if not email_fornecedor:
            return False
        
        msg = Message(
            subject=f"Confirmação de Recebimento - Proposta {protocolo}",
            recipients=[email_fornecedor]
        )
        
        empresa = dados_proposta.get('dados', {}).get('razaoSocial', 'N/A')
        processo = dados_proposta.get('processo', 'N/A')
        
        msg.html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px;">
                <h2 style="color: #333;">✅ Proposta Recebida com Sucesso!</h2>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin-top: 20px;">
                    <p>Prezado(a) {empresa},</p>
                    
                    <p>Confirmamos o recebimento de sua proposta para o processo <strong>{processo}</strong>.</p>
                    
                    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Protocolo:</strong> {protocolo}</p>
                        <p style="margin: 0;"><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    </div>
                    
                    <p>Sua proposta será analisada e você será notificado sobre o andamento do processo.</p>
                    
                    <p>Guarde este protocolo para futuras consultas.</p>
                    
                    <p style="margin-top: 30px;">Atenciosamente,<br>
                    Equipe de Suprimentos</p>
                </div>
                
                <p style="text-align: center; color: #666; margin-top: 20px;">
                    <small>Este é um e-mail automático, por favor não responda.</small>
                </p>
            </div>
        </body>
        </html>
        """
        
        mail.send(msg)
        logger.info(f"Email de confirmação enviado para {email_fornecedor}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar confirmação ao fornecedor: {str(e)}")
        return False

def enviar_notificacao_novo_processo(processo):
    """Envia notificação aos fornecedores sobre novo processo"""
    try:
        # Buscar fornecedores cadastrados
        fornecedores = list(fornecedores_db.values())
        
        if not fornecedores:
            logger.info("Nenhum fornecedor cadastrado para notificar")
            return
        
        for fornecedor in fornecedores:
            if fornecedor.get('email'):
                msg = Message(
                    subject=f"Novo Processo de Licitação - {processo['numero']}",
                    recipients=[fornecedor['email']]
                )
                
                prazo = datetime.fromisoformat(processo['prazo'].replace('Z', '+00:00'))
                prazo_formatado = prazo.strftime('%d/%m/%Y às %H:%M')
                
                msg.html = f"""
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px;">
                        <h2 style="color: #333;">📢 Novo Processo de Licitação</h2>
                        
                        <div style="background-color: white; padding: 20px; border-radius: 5px; margin-top: 20px;">
                            <p>Prezado(a) {fornecedor.get('razaoSocial', 'Fornecedor')},</p>
                            
                            <p>Informamos que foi aberto um novo processo de licitação que pode ser de seu interesse:</p>
                            
                            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                                <p><strong>Número:</strong> {processo['numero']}</p>
                                <p><strong>Objeto:</strong> {processo['objeto']}</p>
                                <p><strong>Modalidade:</strong> {processo['modalidade']}</p>
                                <p><strong>Prazo para envio:</strong> {prazo_formatado}</p>
                            </div>
                            
                            <p>Para participar, acesse o portal de propostas através do link:</p>
                            
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{request.url_root}portal-propostas?processo={processo['numero']}" 
                                   style="background-color: #4CAF50; color: white; padding: 15px 30px; 
                                          text-decoration: none; border-radius: 5px; display: inline-block;">
                                    Acessar Portal de Propostas
                                </a>
                            </div>
                            
                            <p>Não perca esta oportunidade!</p>
                            
                            <p style="margin-top: 30px;">Atenciosamente,<br>
                            Equipe de Suprimentos</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                mail.send(msg)
                logger.info(f"Notificação enviada para {fornecedor['email']}")
                
    except Exception as e:
        logger.error(f"Erro ao enviar notificações: {str(e)}")

def verificar_prazos_proximos():
    """Verifica processos com prazo próximo e envia lembretes"""
    try:
        agora = datetime.now()
        tres_dias = timedelta(days=3)
        
        for processo in processos_db.values():
            prazo = datetime.fromisoformat(processo['prazo'].replace('Z', '+00:00'))
            
            # Se faltam 3 dias ou menos
            if prazo > agora and (prazo - agora) <= tres_dias:
                # Buscar fornecedores que não enviaram proposta
                propostas_processo = [p for p in propostas_db.values() if p['processo'] == processo['numero']]
                cnpjs_com_proposta = [p['dados']['cnpj'] for p in propostas_processo if 'dados' in p and 'cnpj' in p['dados']]
                
                for fornecedor in fornecedores_db.values():
                    if fornecedor.get('cnpj') not in cnpjs_com_proposta and fornecedor.get('email'):
                        enviar_lembrete_prazo(fornecedor, processo)
                        
    except Exception as e:
        logger.error(f"Erro ao verificar prazos: {str(e)}")

def enviar_lembrete_prazo(fornecedor, processo):
    """Envia lembrete de prazo para fornecedor"""
    try:
        msg = Message(
            subject=f"⏰ Lembrete: Prazo próximo - Processo {processo['numero']}",
            recipients=[fornecedor['email']]
        )
        
        prazo = datetime.fromisoformat(processo['prazo'].replace('Z', '+00:00'))
        prazo_formatado = prazo.strftime('%d/%m/%Y às %H:%M')
        
        msg.html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: #fff3cd; padding: 20px; border-radius: 10px; border: 1px solid #ffeaa7;">
                <h2 style="color: #856404;">⏰ Lembrete de Prazo</h2>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin-top: 20px;">
                    <p>Prezado(a) {fornecedor.get('razaoSocial', 'Fornecedor')},</p>
                    
                    <p>Este é um lembrete de que o prazo para envio de propostas para o processo abaixo está próximo:</p>
                    
                    <div style="background-color: #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Processo:</strong> {processo['numero']}</p>
                        <p><strong>Objeto:</strong> {processo['objeto']}</p>
                        <p><strong>PRAZO FINAL:</strong> {prazo_formatado}</p>
                    </div>
                    
                    <p><strong>Ainda não recebemos sua proposta!</strong></p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{request.url_root}portal-propostas?processo={processo['numero']}" 
                           style="background-color: #ff9800; color: white; padding: 15px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Enviar Proposta Agora
                        </a>
                    </div>
                    
                    <p style="color: #dc3545;"><strong>Não perca o prazo!</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        mail.send(msg)
        
        # Enviar cópia para o comprador
        if EMAIL_CONFIG['destinatario_principal']:
            msg_comprador = Message(
                subject=f"Lembrete enviado - Processo {processo['numero']}",
                recipients=[EMAIL_CONFIG['destinatario_principal']]
            )
            msg_comprador.body = f"Lembrete de prazo enviado para {fornecedor['razaoSocial']} ({fornecedor['email']})"
            mail.send(msg_comprador)
            
        logger.info(f"Lembrete enviado para {fornecedor['email']}")
        
    except Exception as e:
        logger.error(f"Erro ao enviar lembrete: {str(e)}")

def salvar_proposta_arquivo(proposta_id, proposta_data):
    """Salva a proposta em arquivo JSON"""
    try:
        safe_id = str(proposta_id).replace('/', '_').replace('\\', '_').replace(':', '_')
        filename = os.path.join(PROPOSTAS_DIR, f'proposta_{safe_id}.json')
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(proposta_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Proposta salva: {filename}")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar proposta: {str(e)}")
        return False

def carregar_dados():
    """Carrega propostas, processos e fornecedores do diretório"""
    try:
        if not os.path.exists(PROPOSTAS_DIR):
            logger.info(f"Diretório {PROPOSTAS_DIR} não existe ainda")
            return
            
        # Carrega propostas
        for filename in os.listdir(PROPOSTAS_DIR):
            if filename.endswith('.json') and filename.startswith('proposta_'):
                filepath = os.path.join(PROPOSTAS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        proposta = json.load(f)
                        propostas_db[proposta.get('protocolo', proposta.get('id'))] = proposta
                except Exception as e:
                    logger.error(f"Erro ao carregar {filename}: {e}")
        
        logger.info(f"Carregadas {len(propostas_db)} propostas")
        
        # Carrega processos se existir arquivo
        processos_file = os.path.join(PROPOSTAS_DIR, 'processos.json')
        if os.path.exists(processos_file):
            with open(processos_file, 'r', encoding='utf-8') as f:
                processos = json.load(f)
                for processo in processos:
                    processos_db[processo['numero']] = processo
                    
        # Carrega fornecedores se existir arquivo
        fornecedores_file = os.path.join(PROPOSTAS_DIR, 'fornecedores.json')
        if os.path.exists(fornecedores_file):
            with open(fornecedores_file, 'r', encoding='utf-8') as f:
                fornecedores = json.load(f)
                for fornecedor in fornecedores:
                    fornecedores_db[fornecedor.get('cnpj', fornecedor.get('id'))] = fornecedor
                    
    except Exception as e:
        logger.error(f"Erro ao carregar dados: {str(e)}")

# Carrega dados existentes ao iniciar
carregar_dados()

@app.route('/')
def home():
    """Serve a página principal ou informações da API"""
    static_index = os.path.join(STATIC_DIR, 'index.html')
    if os.path.exists(static_index):
        return send_from_directory(STATIC_DIR, 'index.html')
    else:
        return jsonify({
            "message": "Sistema de Propostas - API v2.0",
            "status": "online",
            "endpoints": [
                "/portal-propostas",
                "/api/enviar-proposta",
                "/api/status",
                "/api/propostas/listar",
                "/api/processos/listar",
                "/api/processos/<numero>",
                "/api/criar-processo",
                "/api/cadastrar-fornecedor"
            ],
            "email_configurado": bool(app.config['MAIL_USERNAME']),
            "total_propostas": len(propostas_db),
            "total_processos": len(processos_db),
            "total_fornecedores": len(fornecedores_db)
        }), 200

@app.route('/portal-propostas')
def portal_propostas():
    """Serve o portal de propostas"""
    portal_path = os.path.join(STATIC_DIR, 'portal-propostas-novo.html')
    if os.path.exists(portal_path):
        return send_from_directory(STATIC_DIR, 'portal-propostas-novo.html')
    else:
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Portal de Propostas</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>Portal de Propostas</h1>
            <p>O arquivo portal-propostas-novo.html não foi encontrado.</p>
            <p>Por favor, faça o upload do arquivo para a pasta static/</p>
            <hr>
            <p><a href="/api/status">Verificar Status da API</a></p>
        </body>
        </html>
        """)

@app.route('/api/status', methods=['GET'])
def api_status():
    """Verifica o status do servidor"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "propostas_total": len(propostas_db),
        "processos_total": len(processos_db),
        "fornecedores_total": len(fornecedores_db),
        "encoding": "UTF-8",
        "versao": "2.0.0",
        "email_configurado": bool(app.config['MAIL_USERNAME']),
        "diretorios": {
            "propostas": os.path.exists(PROPOSTAS_DIR),
            "static": os.path.exists(STATIC_DIR)
        }
    }), 200

@app.route('/api/enviar-proposta', methods=['POST'])
def enviar_proposta():
    """Recebe proposta do portal novo"""
    try:
        data = request.get_json(force=True)
        
        # Gera protocolo único
        protocolo = data.get('protocolo')
        if not protocolo:
            protocolo = f"PROP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Verifica se fornecedor já enviou proposta para este processo
        processo_numero = data.get('processo', 'N/A')
        cnpj = data.get('dados', {}).get('cnpj', '')
        
        # Verifica propostas existentes
        for proposta in propostas_db.values():
            if (proposta.get('processo') == processo_numero and 
                proposta.get('dados', {}).get('cnpj') == cnpj):
                return jsonify({
                    "success": False,
                    "erro": "Sua empresa já enviou uma proposta para este processo"
                }), 400
        
        # Estrutura completa da proposta
        proposta = {
            "protocolo": protocolo,
            "data_envio": datetime.now().isoformat(),
            "processo": processo_numero,
            "status": "recebida",
            "dados": data.get('dados', {}),
            "resumo": data.get('resumo', {}),
            "tecnica": data.get('tecnica', {}),
            "comercial": data.get('comercial', {})
        }
        
        # Armazena na memória
        propostas_db[protocolo] = proposta
        
        # Salva em arquivo
        if salvar_proposta_arquivo(protocolo, proposta):
            logger.info(f"Nova proposta recebida: {protocolo}")
            
            # Envia email com anexos
            email_enviado = enviar_email_proposta(protocolo, proposta)
            
            return jsonify({
                "success": True,
                "protocolo": protocolo,
                "mensagem": "Proposta enviada com sucesso!",
                "email_enviado": email_enviado,
                "data": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                "proposta_resumo": {
                    "protocolo": protocolo,
                    "processo": processo_numero,
                    "empresa": proposta['dados'].get('razaoSocial', 'N/A'),
                    "cnpj": cnpj,
                    "valor": f"R$ {proposta['comercial'].get('valorTotal', '0,00')}",
                    "data": proposta['data_envio'],
                    "dados": proposta
                }
            }), 201
        else:
            return jsonify({
                "success": False,
                "erro": "Erro ao salvar proposta"
            }), 500
            
    except Exception as e:
        logger.error(f"Erro ao processar proposta: {str(e)}")
        return jsonify({
            "success": False,
            "erro": "Erro interno ao processar proposta",
            "detalhes": str(e)
        }), 500

@app.route('/api/propostas/listar', methods=['GET'])
def listar_propostas():
    """Lista todas as propostas com formato compatível com o frontend"""
    try:
        # Filtros opcionais
        processo = request.args.get('processo')
        cnpj = request.args.get('cnpj')
        
        propostas_lista = []
        
        for proposta in propostas_db.values():
            # Aplicar filtros se especificados
            if processo and proposta.get('processo') != processo:
                continue
            if cnpj and proposta.get('dados', {}).get('cnpj') != cnpj:
                continue
            
            # Formatar proposta para o frontend
            proposta_formatada = {
                "protocolo": proposta.get('protocolo', ''),
                "processo": proposta.get('processo', ''),
                "empresa": proposta.get('dados', {}).get('razaoSocial', 'N/A'),
                "cnpj": proposta.get('dados', {}).get('cnpj', ''),
                "valor": f"R$ {proposta.get('comercial', {}).get('valorTotal', '0,00')}",
                "data": proposta.get('data_envio', ''),
                "dados": proposta
            }
            
            propostas_lista.append(proposta_formatada)
        
        # Ordena por data
        propostas_lista.sort(key=lambda x: x.get('data', ''), reverse=True)
        
        return jsonify({
            "propostas": propostas_lista,
            "total": len(propostas_lista)
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {str(e)}")
        return jsonify({
            "erro": "Erro ao listar propostas"
        }), 500

@app.route('/api/processos/<numero>', methods=['GET'])
def obter_processo(numero):
    """Obtém informações de um processo específico"""
    if numero in processos_db:
        return jsonify(processos_db[numero]), 200
    else:
        # Retorna dados padrão se não encontrar
        return jsonify({
            "numero": numero,
            "objeto": "Processo não cadastrado",
            "modalidade": "Não informada",
            "prazo": datetime.now().isoformat()
        }), 200

@app.route('/api/processos/listar', methods=['GET'])
def listar_processos():
    """Lista todos os processos"""
    return jsonify({
        "processos": list(processos_db.values()),
        "total": len(processos_db)
    }), 200

# ===== NOVOS ENDPOINTS PARA ÁREA DO FORNECEDOR =====

@app.route('/api/processos/ativos', methods=['GET'])
def listar_processos_ativos():
    """Lista apenas processos com prazo não vencido"""
    try:
        agora = datetime.now()
        processos_ativos = []
        
        for processo in processos_db.values():
            try:
                # Converter prazo para datetime
                prazo = datetime.fromisoformat(processo['prazo'].replace('Z', '+00:00'))
                
                # Verificar se ainda está ativo
                if prazo > agora:
                    # Calcular dias restantes
                    dias_restantes = (prazo - agora).days
                    
                    processo_ativo = {
                        "numero": processo['numero'],
                        "objeto": processo['objeto'],
                        "modalidade": processo['modalidade'],
                        "prazo": processo['prazo'],
                        "prazo_formatado": prazo.strftime('%d/%m/%Y %H:%M'),
                        "dias_restantes": dias_restantes,
                        "status": "ativo"
                    }
                    processos_ativos.append(processo_ativo)
                    
            except Exception as e:
                logger.error(f"Erro ao processar processo {processo.get('numero', 'N/A')}: {e}")
                continue
        
        # Ordenar por prazo (mais próximos primeiro)
        processos_ativos.sort(key=lambda x: x['prazo'])
        
        return jsonify({
            "success": True,
            "processos": processos_ativos,
            "total": len(processos_ativos)
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar processos ativos: {str(e)}")
        return jsonify({
            "success": False,
            "erro": "Erro ao listar processos ativos"
        }), 500

@app.route('/api/propostas/fornecedor/<cnpj>', methods=['GET'])
def listar_propostas_fornecedor(cnpj):
    """Lista propostas de um fornecedor específico"""
    try:
        # Remover formatação do CNPJ para comparação
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        propostas_fornecedor = []
        
        for proposta in propostas_db.values():
            proposta_cnpj = proposta.get('dados', {}).get('cnpj', '')
            proposta_cnpj_limpo = proposta_cnpj.replace('.', '').replace('/', '').replace('-', '')
            
            if proposta_cnpj_limpo == cnpj_limpo:
                # Buscar informações do processo
                processo = processos_db.get(proposta.get('processo', ''), {})
                
                proposta_formatada = {
                    "protocolo": proposta.get('protocolo', ''),
                    "processo": proposta.get('processo', ''),
                    "processo_objeto": processo.get('objeto', 'N/A'),
                    "data_envio": proposta.get('data_envio', ''),
                    "data_envio_formatada": datetime.fromisoformat(proposta.get('data_envio', '')).strftime('%d/%m/%Y %H:%M') if proposta.get('data_envio') else '',
                    "valor_total": proposta.get('comercial', {}).get('valorTotal', '0,00'),
                    "status": proposta.get('status', 'enviada'),
                    "empresa": proposta.get('dados', {}).get('razaoSocial', ''),
                    "processo_prazo": processo.get('prazo', ''),
                    "processo_encerrado": datetime.fromisoformat(processo.get('prazo', '').replace('Z', '+00:00')) < datetime.now() if processo.get('prazo') else False
                }
                
                propostas_fornecedor.append(proposta_formatada)
        
        # Ordenar por data de envio (mais recentes primeiro)
        propostas_fornecedor.sort(key=lambda x: x.get('data_envio', ''), reverse=True)
        
        return jsonify({
            "success": True,
            "propostas": propostas_fornecedor,
            "total": len(propostas_fornecedor),
            "cnpj": cnpj
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas do fornecedor {cnpj}: {str(e)}")
        return jsonify({
            "success": False,
            "erro": "Erro ao listar propostas do fornecedor"
        }), 500

@app.route('/api/fornecedor/estatisticas/<cnpj>', methods=['GET'])
def estatisticas_fornecedor(cnpj):
    """Retorna estatísticas específicas do fornecedor"""
    try:
        # Remover formatação do CNPJ
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        # Contar propostas do fornecedor
        propostas_fornecedor = []
        for proposta in propostas_db.values():
            proposta_cnpj = proposta.get('dados', {}).get('cnpj', '')
            proposta_cnpj_limpo = proposta_cnpj.replace('.', '').replace('/', '').replace('-', '')
            
            if proposta_cnpj_limpo == cnpj_limpo:
                propostas_fornecedor.append(proposta)
        
        # Contar processos ativos
        agora = datetime.now()
        processos_ativos = 0
        for processo in processos_db.values():
            try:
                prazo = datetime.fromisoformat(processo['prazo'].replace('Z', '+00:00'))
                if prazo > agora:
                    processos_ativos += 1
            except:
                continue
        
        # Contar prazos próximos (próximos 7 dias)
        uma_semana = agora + timedelta(days=7)
        prazos_proximos = 0
        for processo in processos_db.values():
            try:
                prazo = datetime.fromisoformat(processo['prazo'].replace('Z', '+00:00'))
                if agora < prazo <= uma_semana:
                    prazos_proximos += 1
            except:
                continue
        
        # Calcular valor total das propostas
        valor_total = 0
        for proposta in propostas_fornecedor:
            valor_str = proposta.get('comercial', {}).get('valorTotal', '0,00')
            try:
                # Remover formatação e converter para float
                valor_limpo = valor_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
                valor_total += float(valor_limpo)
            except:
                continue
        
        return jsonify({
            "success": True,
            "estatisticas": {
                "processos_ativos": processos_ativos,
                "propostas_enviadas": len(propostas_fornecedor),
                "prazos_proximos": prazos_proximos,
                "valor_total": f"{valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas do fornecedor {cnpj}: {str(e)}")
        return jsonify({
            "success": False,
            "erro": "Erro ao calcular estatísticas"
        }), 500

# ===== FIM DOS NOVOS ENDPOINTS =====

@app.route('/api/criar-processo', methods=['POST'])
def criar_processo():
    """Cria um novo processo e notifica fornecedores"""
    try:
        data = request.get_json(force=True)
        
        processo = {
            "id": str(uuid.uuid4()),
            "numero": data.get('numero', ''),
            "objeto": data.get('objeto', ''),
            "modalidade": data.get('modalidade', ''),
            "prazo": data.get('prazo', ''),
            "dataCadastro": datetime.now().isoformat(),
            "criadoPor": data.get('criadoPor', ''),
            "notificarFornecedores": data.get('notificarFornecedores', False)
        }
        
        # Salva processo
        processos_db[processo['numero']] = processo
        
        # Salvar em arquivo
        processos_file = os.path.join(PROPOSTAS_DIR, 'processos.json')
        with open(processos_file, 'w', encoding='utf-8') as f:
            json.dump(list(processos_db.values()), f, ensure_ascii=False, indent=2)
        
        # Notificar fornecedores se solicitado
        if processo['notificarFornecedores']:
            enviar_notificacao_novo_processo(processo)
        
        return jsonify({
            "success": True,
            "processo": processo,
            "mensagem": "Processo criado com sucesso!"
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar processo: {str(e)}")
        return jsonify({
            "success": False,
            "erro": "Erro ao criar processo"
        }), 500

@app.route('/api/cadastrar-fornecedor', methods=['POST'])
def cadastrar_fornecedor():
    """Cadastra um novo fornecedor"""
    try:
        data = request.get_json(force=True)
        
        cnpj = data.get('cnpj', '')
        
        # Verifica se já existe
        if cnpj in fornecedores_db:
            return jsonify({
                "success": False,
                "erro": "Fornecedor já cadastrado"
            }), 400
        
        fornecedor = {
            "id": str(uuid.uuid4()),
            "cnpj": cnpj,
            "razaoSocial": data.get('razaoSocial', ''),
            "email": data.get('email', ''),
            "telefone": data.get('telefone', ''),
            "endereco": data.get('endereco', ''),
            "cidade": data.get('cidade', ''),
            "estado": data.get('estado', ''),
            "cep": data.get('cep', ''),
            "responsavel": data.get('responsavel', ''),
            "dataCadastro": datetime.now().isoformat(),
            "ativo": True
        }
        
        # Salva fornecedor
        fornecedores_db[cnpj] = fornecedor
        
        # Salvar em arquivo
        fornecedores_file = os.path.join(PROPOSTAS_DIR, 'fornecedores.json')
        with open(fornecedores_file, 'w', encoding='utf-8') as f:
            json.dump(list(fornecedores_db.values()), f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "fornecedor": fornecedor,
            "mensagem": "Fornecedor cadastrado com sucesso!"
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao cadastrar fornecedor: {str(e)}")
        return jsonify({
            "success": False,
            "erro": "Erro ao cadastrar fornecedor"
        }), 500

# Endpoints para arquivos estáticos movidos para o final

@app.errorhandler(404)
def nao_encontrado(e):
    return jsonify({"erro": "Endpoint não encontrado"}), 404

@app.errorhandler(500)
def erro_interno(e):
    return jsonify({"erro": "Erro interno do servidor"}), 500
@app.route('/api/download/proposta/<protocolo>/<tipo>', methods=['GET'])
def download_proposta(protocolo, tipo):
    """Download de proposta em Excel ou Word usando as mesmas funções dos anexos de e-mail"""
    try:
        # Buscar proposta
        proposta = None
        for p in propostas_db.values():
            if p.get('protocolo') == protocolo:
                proposta = p
                break
        
        if not proposta:
            return jsonify({
                "success": False,
                "erro": "Proposta não encontrada"
            }), 404
        
        if tipo == 'excel':
            # Gerar Excel usando a mesma função do e-mail
            excel_buffer = gerar_excel_proposta(proposta)
            
            # Configurar response
            response = send_file(
                excel_buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'proposta_{protocolo}_completa.xlsx'
            )
            return response
            
        elif tipo == 'word':
            # Gerar Word usando a mesma função do e-mail
            word_buffer = gerar_word_proposta(proposta)
            
            # Configurar response
            response = send_file(
                word_buffer,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                as_attachment=True,
                download_name=f'proposta_{protocolo}_tecnica.docx'
            )
            return response
            
        else:
            return jsonify({
                "success": False,
                "erro": "Tipo inválido. Use 'excel' ou 'word'"
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao fazer download: {str(e)}")
        return jsonify({
            "success": False,
            "erro": f"Erro ao gerar arquivo: {str(e)}"
        }), 500

# ===== ENDPOINT CATCH-ALL (DEVE SER O ÚLTIMO) =====
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos com tratamento de erro"""
    try:
        # Previne path traversal
        if '..' in filename or filename.startswith('/'):
            return jsonify({"erro": "Caminho inválido"}), 400
            
        file_path = os.path.join(STATIC_DIR, filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(STATIC_DIR, filename)
        else:
            return jsonify({"erro": "Arquivo não encontrado"}), 404
    except Exception as e:
        logger.error(f"Erro ao servir arquivo {filename}: {e}")
        return jsonify({"erro": "Erro ao acessar arquivo"}), 500

if __name__ == '__main__':
    logger.info("Iniciando servidor de propostas v2.0.0...")
    logger.info(f"Diretório de trabalho: {os.getcwd()}")
    logger.info(f"Email configurado: {bool(app.config['MAIL_USERNAME'])}")
    logger.info(f"Destinatário principal: {EMAIL_CONFIG['destinatario_principal']}")
    
    # Verificar prazos periodicamente (em produção usar scheduler apropriado)
    # verificar_prazos_proximos()
    
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
