#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRETOR AUTOMÁTICO DO SISTEMA DE PROPOSTAS
Este script corrige todos os problemas identificados no sistema
"""

import os
import shutil
from datetime import datetime

def criar_arquivo_env():
    """Cria arquivo .env com as configurações corretas"""
    print("📝 Criando arquivo .env...")
    
    env_content = """# Configurações de Email
EMAIL_USER=portaldofornecedor.arias@gmail.com
EMAIL_PASS=ctzf xkek qzfq hkdb
EMAIL_SERVER=smtp.gmail.com
EMAIL_PORT=587
EMAIL_SUPRIMENTOS=portaldofornecedor.arias@gmail.com
EMAIL_CC=
EMAIL_ADMINS=admin@empresa.com

# Configurações da Aplicação
DEBUG=False
PORT=10000
PYTHON_VERSION=3.11.0
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ Arquivo .env criado com sucesso!")

def corrigir_backend():
    """Aplica correções ao backend_propostas.py"""
    print("\n🔧 Corrigindo backend_propostas.py...")
    
    # Fazer backup
    if os.path.exists('backend_propostas.py'):
        shutil.copy('backend_propostas.py', f'backend_propostas_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py')
        print("✅ Backup criado")
    
    # Ler o arquivo original
    with open('backend_propostas (2).py', 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Correção 1: Importações necessárias
    if "from email.mime.base import MIMEBase" not in conteudo:
        imports_pos = conteudo.find("from email.mime.application import MIMEApplication")
        if imports_pos != -1:
            conteudo = conteudo[:imports_pos] + "from email.mime.base import MIMEBase\n" + conteudo[imports_pos:]
    
    # Correção 2: Atualizar função enviar_proposta
    # Encontrar início da função
    inicio = conteudo.find("@app.route('/api/enviar-proposta'")
    if inicio != -1:
        # Encontrar próxima rota
        fim = conteudo.find("@app.route", inicio + 1)
        if fim == -1:
            fim = len(conteudo)
        
        # Nova implementação da função
        nova_funcao = '''@app.route('/api/enviar-proposta', methods=['POST'])
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
'''
        
        # Substituir a função
        conteudo = conteudo[:inicio] + nova_funcao + '\n\n'
        
        # Adicionar próxima rota se existir
        next_route_pos = conteudo.find("@app.route", fim)
        if next_route_pos != -1:
            conteudo += conteudo[next_route_pos:]
    
    # Salvar arquivo corrigido
    with open('backend_propostas.py', 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print("✅ backend_propostas.py corrigido com sucesso!")

def main():
    """Função principal"""
    print("=" * 60)
    print("🚀 CORRETOR AUTOMÁTICO DO SISTEMA DE PROPOSTAS")
    print("=" * 60)
    
    # 1. Criar .env
    if not os.path.exists('.env'):
        criar_arquivo_env()
    else:
        print("ℹ️  Arquivo .env já existe")
    
    # 2. Corrigir backend
    corrigir_backend()
    
    print("\n✅ CORREÇÕES APLICADAS COM SUCESSO!")
    print("\n📋 O que foi corrigido:")
    print("1. ✅ Arquivo .env configurado")
    print("2. ✅ Função de envio de proposta atualizada")
    print("3. ✅ Envio de e-mail para fornecedor e suprimentos")
    print("4. ✅ Geração e anexo de arquivos Excel e Word")
    
    print("\n🎯 Próximos passos:")
    print("1. Instale as dependências: pip install -r requirements.txt")
    print("2. Teste o e-mail: python test_email.py")
    print("3. Inicie o servidor: python backend_propostas.py")
    print("4. Acesse: http://localhost:5000")
    
    print("\n💡 Dicas importantes:")
    print("- Para Gmail, use uma 'senha de aplicativo' (16 caracteres)")
    print("- Verifique a pasta SPAM se não receber os e-mails")
    print("- Os arquivos de propostas são salvos na pasta 'propostas'")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
