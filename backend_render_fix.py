#!/usr/bin/env python3
"""
Backend específico para resolver o problema no Render
Versão simplificada focada na área do fornecedor
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Configuração do Flask
app = Flask(__name__)
CORS(app)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Criar diretórios se não existirem
os.makedirs(STATIC_DIR, exist_ok=True)

# Dados em memória para demonstração
DADOS_EXEMPLO = {
    "processos": [
        {
            "numero": "001/2025",
            "objeto": "Construção de Escola Municipal",
            "modalidade": "Concorrência",
            "prazo": (datetime.now() + timedelta(days=15)).isoformat(),
            "status": "ativo"
        },
        {
            "numero": "002/2025", 
            "objeto": "Reforma do Centro de Saúde",
            "modalidade": "Tomada de Preços",
            "prazo": (datetime.now() + timedelta(days=10)).isoformat(),
            "status": "ativo"
        },
        {
            "numero": "003/2025",
            "objeto": "Pavimentação de Ruas",
            "modalidade": "Concorrência", 
            "prazo": (datetime.now() + timedelta(days=20)).isoformat(),
            "status": "ativo"
        }
    ],
    "fornecedores": {
        "12345678000190": {
            "cnpj": "12.345.678/0001-90",
            "razaoSocial": "Construtora Exemplo LTDA",
            "propostas_enviadas": 0,
            "valor_total": "0,00"
        }
    }
}

@app.route('/')
def index():
    """Página inicial"""
    return jsonify({
        "sistema": "Portal do Fornecedor",
        "status": "online",
        "versao": "1.0-render"
    })

@app.route('/api/status')
def api_status():
    """Status da API"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "processos_total": len(DADOS_EXEMPLO["processos"]),
        "fornecedores_total": len(DADOS_EXEMPLO["fornecedores"]),
        "versao": "1.0-render"
    })

@app.route('/api/processos/ativos')
def processos_ativos():
    """Lista processos ativos"""
    try:
        agora = datetime.now()
        processos_formatados = []
        
        for processo in DADOS_EXEMPLO["processos"]:
            try:
                prazo = datetime.fromisoformat(processo["prazo"])
                dias_restantes = (prazo - agora).days
                
                if dias_restantes > 0:  # Apenas processos ativos
                    processos_formatados.append({
                        "numero": processo["numero"],
                        "objeto": processo["objeto"],
                        "modalidade": processo["modalidade"],
                        "prazo": processo["prazo"],
                        "prazo_formatado": prazo.strftime("%d/%m/%Y %H:%M"),
                        "dias_restantes": dias_restantes,
                        "status": "ativo"
                    })
            except:
                continue
        
        # Ordenar por prazo (mais próximos primeiro)
        processos_formatados.sort(key=lambda x: x["dias_restantes"])
        
        return jsonify({
            "success": True,
            "processos": processos_formatados,
            "total": len(processos_formatados)
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar processos ativos: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao carregar processos"
        }), 500

@app.route('/api/fornecedor/estatisticas')
def estatisticas_fornecedor():
    """Estatísticas do fornecedor via query parameter"""
    try:
        cnpj = request.args.get('cnpj', '')
        if not cnpj:
            return jsonify({
                "success": False,
                "erro": "CNPJ não fornecido"
            }), 400
        
        # Limpar CNPJ
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        # Buscar dados do fornecedor
        fornecedor = DADOS_EXEMPLO["fornecedores"].get(cnpj_limpo, {})
        
        # Contar processos ativos
        agora = datetime.now()
        processos_ativos = 0
        prazos_proximos = 0
        
        for processo in DADOS_EXEMPLO["processos"]:
            try:
                prazo = datetime.fromisoformat(processo["prazo"])
                if prazo > agora:
                    processos_ativos += 1
                    # Próximos 7 dias
                    if (prazo - agora).days <= 7:
                        prazos_proximos += 1
            except:
                continue
        
        return jsonify({
            "success": True,
            "estatisticas": {
                "processos_ativos": processos_ativos,
                "propostas_enviadas": fornecedor.get("propostas_enviadas", 0),
                "prazos_proximos": prazos_proximos,
                "valor_total": fornecedor.get("valor_total", "0,00")
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao calcular estatísticas"
        }), 500

@app.route('/api/propostas/fornecedor')
def propostas_fornecedor():
    """Propostas do fornecedor via query parameter"""
    try:
        cnpj = request.args.get('cnpj', '')
        if not cnpj:
            return jsonify({
                "success": False,
                "erro": "CNPJ não fornecido"
            }), 400
        
        # Por enquanto retorna lista vazia (sem propostas)
        return jsonify({
            "success": True,
            "propostas": [],
            "total": 0,
            "cnpj": cnpj
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao listar propostas"
        }), 500

# Servir arquivos estáticos (DEVE SER O ÚLTIMO)
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos"""
    try:
        # Não interceptar rotas da API
        if filename.startswith('api/'):
            return jsonify({"erro": "Endpoint não encontrado"}), 404
            
        # Prevenir path traversal
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

@app.errorhandler(404)
def not_found(e):
    return jsonify({"erro": "Endpoint não encontrado"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"erro": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    logger.info("Iniciando servidor para Render...")
    logger.info(f"Diretório de trabalho: {os.getcwd()}")
    
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )

