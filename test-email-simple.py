#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTADOR DE E-MAIL SIMPLES
Execute este arquivo para verificar se o e-mail está funcionando
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
from dotenv import load_dotenv

# Carregar configurações do .env
load_dotenv()

def testar_email():
    """Testa o envio de e-mail"""
    
    # Pegar configurações
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASS = os.getenv('EMAIL_PASS')
    EMAIL_DEST = os.getenv('EMAIL_SUPRIMENTOS')
    
    print("=" * 50)
    print("🧪 TESTE DE E-MAIL")
    print("=" * 50)
    print(f"De: {EMAIL_USER}")
    print(f"Para: {EMAIL_DEST}")
    print("=" * 50)
    
    if not EMAIL_USER or not EMAIL_PASS:
        print("\n❌ ERRO: Configure EMAIL_USER e EMAIL_PASS no arquivo .env")
        return False
    
    try:
        # Conectar ao Gmail
        print("\n📡 Conectando ao Gmail...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        print("✅ Login realizado com sucesso!")
        
        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_DEST
        msg['Subject'] = f'[TESTE] Sistema de Propostas - {datetime.now().strftime("%H:%M")}'
        
        # Corpo do e-mail
        corpo = f"""
        <h2>✅ Teste de E-mail Bem Sucedido!</h2>
        
        <p>Este é um e-mail de teste do Sistema de Propostas.</p>
        
        <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        
        <p>Se você está recebendo este e-mail, o sistema está configurado corretamente!</p>
        
        <hr>
        <small>E-mail automático - Não responder</small>
        """
        
        msg.attach(MIMEText(corpo, 'html'))
        
        # Enviar
        print("📧 Enviando e-mail de teste...")
        server.send_message(msg)
        server.quit()
        
        print("\n✅ SUCESSO! E-mail enviado!")
        print(f"📬 Verifique a caixa de entrada de: {EMAIL_DEST}")
        print("\n💡 Se não recebeu, verifique:")
        print("   • Pasta de SPAM")
        print("   • Se o e-mail está correto")
        print("   • Se a senha é de 16 caracteres (senha de app)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        print("\n💡 Dicas:")
        print("1. Para Gmail, use 'Senha de Aplicativo' (16 caracteres)")
        print("2. Ative verificação em 2 etapas no Gmail")
        print("3. Gere a senha em: https://myaccount.google.com/apppasswords")
        return False

if __name__ == "__main__":
    testar_email()
    input("\n\nPressione ENTER para sair...")
