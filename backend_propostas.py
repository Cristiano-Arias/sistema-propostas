#!/usr/bin/env python3
"""
Backend Atualizado - Sistema de Gestão de Propostas
Versão 3.1 - CORRIGIDO - Propostas Funcionando
Compatível com Render.com e GitHub
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Configuração do Flask
app = Flask(__name__)
CORS(app, origins="*")  # Permitir todas as origens para desenvolvimento

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Criar diretórios se não existirem
os.makedirs(STATIC_DIR, exist_ok=True)

# Dados de exemplo para demonstração
DADOS_SISTEMA = {
    "processos": [
        {
            "id": "proc_001",
            "numero": "LIC-2025-001",
            "objeto": "Construção de Escola Municipal de Ensino Fundamental",
            "modalidade": "Concorrência",
            "prazo": (datetime.now() + timedelta(days=15)).isoformat(),
            "status": "ativo",
            "criadoPor": "comprador_001",
            "dataCadastro": datetime.now().isoformat(),
            "fornecedoresConvidados": ["forn_001", "forn_002"]
        },
        {
            "id": "proc_002",
            "numero": "LIC-2025-002", 
            "objeto": "Reforma e Ampliação do Centro de Saúde",
            "modalidade": "Tomada de Preços",
            "prazo": (datetime.now() + timedelta(days=10)).isoformat(),
            "status": "ativo",
            "criadoPor": "comprador_001",
            "dataCadastro": datetime.now().isoformat(),
            "fornecedoresConvidados": ["forn_001"]
        },
        {
            "id": "proc_003",
            "numero": "LIC-2025-003",
            "objeto": "Pavimentação Asfáltica de Vias Urbanas",
            "modalidade": "Concorrência", 
            "prazo": (datetime.now() + timedelta(days=20)).isoformat(),
            "status": "ativo",
            "criadoPor": "comprador_002",
            "dataCadastro": datetime.now().isoformat(),
            "fornecedoresConvidados": ["forn_002", "forn_003"]
        }
    ],
    "propostas": [
        {
            "protocolo": "PROP-2025-001",
            "processo": "LIC-2025-001",
            "empresa": "Construtora Alpha LTDA",
            "cnpj": "12.345.678/0001-90",
            "data": datetime.now().isoformat(),
            "valor": "R$ 850.000,00",
            "dados": {
                "dados": {
                    "razaoSocial": "Construtora Alpha LTDA",
                    "cnpj": "12.345.678/0001-90",
                    "email": "contato@alpha.com.br",
                    "telefone": "(11) 3456-7890"
                },
                "tecnica": {
                    "prazoExecucao": "180 dias",
                    "metodologia": "Metodologia construtiva tradicional"
                },
                "comercial": {
                    "valorTotal": "850.000,00",
                    "validadeProposta": "60 dias"
                }
            }
        }
    ],
    "usuarios": [
        {
            "id": "admin_001",
            "nome": "Administrador Sistema",
            "email": "admin@sistema.gov.br",
            "tipo": "admin",
            "ativo": True,
            "dataCriacao": datetime.now().isoformat()
        },
        {
            "id": "comprador_001",
            "nome": "João Silva",
            "email": "joao.silva@prefeitura.gov.br",
            "tipo": "comprador",
            "nivelAcesso": "comprador_senior",
            "ativo": True,
            "dataCriacao": datetime.now().isoformat()
        },
        {
            "id": "requisitante_001",
            "nome": "Maria Santos",
            "email": "maria.santos@educacao.gov.br",
            "tipo": "requisitante",
            "ativo": True,
            "dataCriacao": datetime.now().isoformat()
        },
        {
            "id": "forn_001",
            "nome": "Construtora Alpha LTDA",
            "email": "contato@alpha.com.br",
            "cnpj": "12.345.678/0001-90",
            "tipo": "fornecedor",
            "ativo": True,
            "dataCriacao": datetime.now().isoformat()
        }
    ],
    "notificacoes": []
}

@app.route('/')
def index():
    """Redireciona para a página de login"""
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/api/status')
def api_status():
    """Status detalhado da API"""
    try:
        agora = datetime.now()
        processos_ativos = [p for p in DADOS_SISTEMA["processos"] 
                           if datetime.fromisoformat(p["prazo"]) > agora]
        
        return jsonify({
            "status": "online",
            "timestamp": agora.isoformat(),
            "estatisticas": {
                "processos_total": len(DADOS_SISTEMA["processos"]),
                "processos_ativos": len(processos_ativos),
                "propostas_total": len(DADOS_SISTEMA["propostas"]),
                "usuarios_total": len(DADOS_SISTEMA["usuarios"]),
                "notificacoes_total": len(DADOS_SISTEMA["notificacoes"])
            },
            "versao": "3.1-CORRIGIDO",
            "ambiente": os.environ.get('ENVIRONMENT', 'development')
        })
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({"erro": "Erro interno"}), 500

@app.route('/api/processos')
def listar_processos():
    """Lista todos os processos"""
    try:
        status_filtro = request.args.get('status', 'todos')
        agora = datetime.now()
        
        processos = DADOS_SISTEMA["processos"].copy()
        
        # Aplicar filtro de status
        if status_filtro == 'ativo':
            processos = [p for p in processos 
                        if datetime.fromisoformat(p["prazo"]) > agora]
        elif status_filtro == 'encerrado':
            processos = [p for p in processos 
                        if datetime.fromisoformat(p["prazo"]) <= agora]
        
        # Adicionar informações calculadas
        for processo in processos:
            prazo = datetime.fromisoformat(processo["prazo"])
            processo["dias_restantes"] = (prazo - agora).days
            processo["prazo_formatado"] = prazo.strftime("%d/%m/%Y %H:%M")
            processo["status_calculado"] = "ativo" if prazo > agora else "encerrado"
            
            # Contar propostas
            propostas_processo = [p for p in DADOS_SISTEMA["propostas"] 
                                 if p["processo"] == processo["numero"]]
            processo["total_propostas"] = len(propostas_processo)
        
        return jsonify({
            "success": True,
            "processos": processos,
            "total": len(processos),
            "filtro_aplicado": status_filtro
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar processos: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao carregar processos"
        }), 500

@app.route('/api/processos/ativos')
def processos_ativos():
    """Lista apenas processos ativos (para fornecedores)"""
    try:
        agora = datetime.now()
        processos_formatados = []
        
        for processo in DADOS_SISTEMA["processos"]:
            try:
                prazo = datetime.fromisoformat(processo["prazo"])
                dias_restantes = (prazo - agora).days
                
                if dias_restantes > 0:  # Apenas processos ativos
                    processos_formatados.append({
                        "id": processo["id"],
                        "numero": processo["numero"],
                        "objeto": processo["objeto"],
                        "modalidade": processo["modalidade"],
                        "prazo": processo["prazo"],
                        "prazo_formatado": prazo.strftime("%d/%m/%Y %H:%M"),
                        "dias_restantes": dias_restantes,
                        "status": "ativo"
                    })
            except Exception as e:
                logger.warning(f"Erro ao processar processo {processo.get('numero', 'N/A')}: {e}")
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

@app.route('/api/processos', methods=['POST'])
def criar_processo():
    """Criar novo processo"""
    try:
        dados = request.get_json()
        
        # Validações básicas
        campos_obrigatorios = ['numero', 'objeto', 'modalidade', 'prazo']
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({
                    "success": False,
                    "erro": f"Campo '{campo}' é obrigatório"
                }), 400
        
        # Verificar se número já existe
        if any(p["numero"] == dados["numero"] for p in DADOS_SISTEMA["processos"]):
            return jsonify({
                "success": False,
                "erro": "Já existe um processo com este número"
            }), 400
        
        # Criar novo processo
        novo_processo = {
            "id": f"proc_{len(DADOS_SISTEMA['processos']) + 1:03d}",
            "numero": dados["numero"],
            "objeto": dados["objeto"],
            "modalidade": dados["modalidade"],
            "prazo": dados["prazo"],
            "status": "ativo",
            "criadoPor": dados.get("criadoPor", "sistema"),
            "dataCadastro": datetime.now().isoformat(),
            "fornecedoresConvidados": dados.get("fornecedoresConvidados", [])
        }
        
        DADOS_SISTEMA["processos"].append(novo_processo)
        
        logger.info(f"Processo criado: {novo_processo['numero']}")
        
        return jsonify({
            "success": True,
            "processo": novo_processo,
            "mensagem": "Processo criado com sucesso"
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar processo: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao criar processo"
        }), 500

@app.route('/api/propostas')
def listar_propostas():
    """Lista todas as propostas"""
    try:
        processo_filtro = request.args.get('processo')
        cnpj_filtro = request.args.get('cnpj')
        
        propostas = DADOS_SISTEMA["propostas"].copy()
        
        # Aplicar filtros
        if processo_filtro:
            propostas = [p for p in propostas if p["processo"] == processo_filtro]
        
        if cnpj_filtro:
            cnpj_limpo = cnpj_filtro.replace('.', '').replace('/', '').replace('-', '')
            propostas = [p for p in propostas 
                        if p["cnpj"].replace('.', '').replace('/', '').replace('-', '') == cnpj_limpo]
        
        # Adicionar informações calculadas
        for proposta in propostas:
            proposta["data_formatada"] = datetime.fromisoformat(proposta["data"]).strftime("%d/%m/%Y %H:%M")
        
        return jsonify({
            "success": True,
            "propostas": propostas,
            "total": len(propostas),
            "filtros": {
                "processo": processo_filtro,
                "cnpj": cnpj_filtro
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao carregar propostas"
        }), 500

@app.route('/api/propostas', methods=['POST'])
def enviar_proposta():
    """Enviar nova proposta"""
    try:
        dados = request.get_json()
        
        # Validações básicas
        campos_obrigatorios = ['processo', 'empresa', 'cnpj', 'dados']
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({
                    "success": False,
                    "erro": f"Campo '{campo}' é obrigatório"
                }), 400
        
        # Verificar se processo existe e está ativo
        processo = next((p for p in DADOS_SISTEMA["processos"] 
                        if p["numero"] == dados["processo"]), None)
        
        if not processo:
            return jsonify({
                "success": False,
                "erro": "Processo não encontrado"
            }), 404
        
        # Verificar se processo ainda está ativo
        if datetime.fromisoformat(processo["prazo"]) <= datetime.now():
            return jsonify({
                "success": False,
                "erro": "Prazo do processo já expirou"
            }), 400
        
        # Gerar protocolo único
        protocolo = f"PROP-{datetime.now().strftime('%Y')}-{len(DADOS_SISTEMA['propostas']) + 1:03d}"
        
        # Criar nova proposta
        nova_proposta = {
            "protocolo": protocolo,
            "processo": dados["processo"],
            "empresa": dados["empresa"],
            "cnpj": dados["cnpj"],
            "data": datetime.now().isoformat(),
            "valor": dados.get("valor", "R$ 0,00"),
            "dados": dados["dados"]
        }
        
        DADOS_SISTEMA["propostas"].append(nova_proposta)
        
        logger.info(f"Proposta enviada: {protocolo} para processo {dados['processo']}")
        
        return jsonify({
            "success": True,
            "proposta": nova_proposta,
            "protocolo": protocolo,
            "mensagem": "Proposta enviada com sucesso"
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao enviar proposta: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao enviar proposta"
        }), 500

@app.route('/api/propostas/enviar', methods=['POST'])
def enviar_proposta_frontend():
    """Rota específica para envio de propostas do frontend - CORRIGIDA"""
    try:
        dados = request.get_json()
        
        # Log para debug
        logger.info(f"📥 Dados recebidos do frontend: {json.dumps(dados, indent=2, default=str)}")
        
        # Extrair dados corretamente do formato do frontend
        dados_cadastrais = dados.get("dadosCadastrais", {})
        processo_info = dados.get("processo", {})
        proposta_comercial = dados.get("propostaComercial", {})
        
        # Validações básicas
        if not dados_cadastrais.get("razaoSocial"):
            return jsonify({
                "success": False,
                "erro": "Razão social é obrigatória"
            }), 400
        
        if not dados_cadastrais.get("cnpj"):
            return jsonify({
                "success": False,
                "erro": "CNPJ é obrigatório"
            }), 400
        
        # Gerar protocolo único
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        protocolo = f"PROP-{timestamp}-{len(DADOS_SISTEMA['propostas']) + 1:03d}"
        
        # Extrair valor total da proposta comercial
        valor_total = "R$ 0,00"
        if proposta_comercial.get("valorTotal"):
            valor_total = f"R$ {proposta_comercial['valorTotal']}"
        elif proposta_comercial.get("totais", {}).get("custoDirecto"):
            valor_total = f"R$ {proposta_comercial['totais']['custoDirecto']}"
        
        # Criar nova proposta com estrutura correta
        nova_proposta = {
            "protocolo": protocolo,
            "processo": processo_info.get("numero", "1600003456-150"),
            "empresa": dados_cadastrais.get("razaoSocial", ""),
            "cnpj": dados_cadastrais.get("cnpj", ""),
            "email": dados_cadastrais.get("email", ""),
            "telefone": dados_cadastrais.get("telefone", ""),
            "data": datetime.now().isoformat(),
            "valor": valor_total,
            "status": "enviada",
            "dados_completos": dados,  # Salvar todos os dados originais
            "resumo": {
                "razao_social": dados_cadastrais.get("razaoSocial"),
                "cnpj": dados_cadastrais.get("cnpj"),
                "processo": processo_info.get("numero"),
                "objeto": processo_info.get("objeto"),
                "valor_total": valor_total,
                "prazo_execucao": dados.get("resumo", {}).get("prazoExecucao") or 
                               dados.get("propostaTecnica", {}).get("prazoExecucao"),
                "forma_pagamento": dados.get("resumo", {}).get("formaPagamento"),
                "data_envio": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
        }
        
        # Adicionar à lista de propostas
        DADOS_SISTEMA["propostas"].append(nova_proposta)
        
        # Log de sucesso
        logger.info(f"✅ Proposta salva com sucesso: {protocolo} - {dados_cadastrais.get('razaoSocial')}")
        
        # Criar notificação para o comprador
        notificacao = {
            "id": f"notif_{len(DADOS_SISTEMA['notificacoes']) + 1:03d}",
            "tipo": "nova_proposta",
            "titulo": "Nova Proposta Recebida",
            "mensagem": f"Nova proposta de {dados_cadastrais.get('razaoSocial')} para o processo {processo_info.get('numero')}",
            "destinatario": "todos",
            "destinatarioTipo": "comprador",
            "remetente": "Sistema",
            "lida": False,
            "data": datetime.now().isoformat(),
            "acao": "visualizar_proposta",
            "processoId": processo_info.get("numero"),
            "metadata": {
                "protocolo": protocolo,
                "empresa": dados_cadastrais.get("razaoSocial"),
                "valor": valor_total
            }
        }
        
        DADOS_SISTEMA["notificacoes"].append(notificacao)
        
        # Resposta de sucesso
        return jsonify({
            "success": True,
            "protocolo": protocolo,
            "mensagem": "✅ Proposta enviada com sucesso!",
            "detalhes": {
                "empresa": dados_cadastrais.get("razaoSocial"),
                "processo": processo_info.get("numero"),
                "valor": valor_total,
                "data_envio": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "protocolo": protocolo
            },
            "data": datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar proposta via frontend: {str(e)}")
        logger.error(f"Dados recebidos: {request.get_json()}")
        return jsonify({
            "success": False,
            "erro": f"❌ Erro ao enviar proposta: {str(e)}"
        }), 500

@app.route('/api/propostas/verificar/<protocolo>')
def verificar_proposta(protocolo):
    """Verificar se proposta foi salva corretamente"""
    try:
        proposta = next((p for p in DADOS_SISTEMA["propostas"] 
                        if p["protocolo"] == protocolo), None)
        
        if not proposta:
            return jsonify({
                "success": False,
                "erro": "Proposta não encontrada"
            }), 404
        
        return jsonify({
            "success": True,
            "proposta_encontrada": True,
            "resumo": proposta.get("resumo", {}),
            "protocolo": protocolo,
            "data_envio": proposta.get("data"),
            "status": proposta.get("status", "enviada")
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar proposta {protocolo}: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao verificar proposta"
        }), 500

@app.route('/api/propostas/processo/<numero_processo>')
def propostas_por_processo(numero_processo):
    """Listar propostas de um processo específico"""
    try:
        propostas_processo = [p for p in DADOS_SISTEMA["propostas"] 
                             if p["processo"] == numero_processo]
        
        # Formatar dados para exibição
        propostas_formatadas = []
        for proposta in propostas_processo:
            propostas_formatadas.append({
                "protocolo": proposta["protocolo"],
                "empresa": proposta["empresa"],
                "cnpj": proposta["cnpj"],
                "valor": proposta["valor"],
                "data_envio": datetime.fromisoformat(proposta["data"]).strftime("%d/%m/%Y %H:%M"),
                "status": proposta.get("status", "enviada"),
                "resumo": proposta.get("resumo", {}),
                "tem_dados_completos": "dados_completos" in proposta
            })
        
        return jsonify({
            "success": True,
            "processo": numero_processo,
            "propostas": propostas_formatadas,
            "total": len(propostas_formatadas)
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas do processo {numero_processo}: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao carregar propostas"
        }), 500

@app.route('/api/fornecedor/estatisticas')
def estatisticas_fornecedor():
    """Estatísticas específicas do fornecedor"""
    try:
        cnpj = request.args.get('cnpj', '')
        if not cnpj:
            return jsonify({
                "success": False,
                "erro": "CNPJ não fornecido"
            }), 400
        
        # Limpar CNPJ
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        # Contar propostas do fornecedor
        propostas_fornecedor = [p for p in DADOS_SISTEMA["propostas"] 
                               if p["cnpj"].replace('.', '').replace('/', '').replace('-', '') == cnpj_limpo]
        
        # Contar processos ativos
        agora = datetime.now()
        processos_ativos = len([p for p in DADOS_SISTEMA["processos"] 
                               if datetime.fromisoformat(p["prazo"]) > agora])
        
        # Processos com prazo próximo (7 dias)
        prazos_proximos = len([p for p in DADOS_SISTEMA["processos"] 
                              if datetime.fromisoformat(p["prazo"]) > agora and 
                              (datetime.fromisoformat(p["prazo"]) - agora).days <= 7])
        
        # Calcular valor total das propostas
        valor_total = 0
        for proposta in propostas_fornecedor:
            if proposta.get("valor"):
                valor_str = proposta["valor"].replace("R$", "").replace(".", "").replace(",", ".").strip()
                try:
                    valor_total += float(valor_str)
                except:
                    pass
        
        return jsonify({
            "success": True,
            "estatisticas": {
                "processos_ativos": processos_ativos,
                "propostas_enviadas": len(propostas_fornecedor),
                "prazos_proximos": prazos_proximos,
                "valor_total": f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            },
            "cnpj": cnpj
        })
        
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas do fornecedor: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao calcular estatísticas"
        }), 500

@app.route('/api/usuarios')
def listar_usuarios():
    """Lista usuários do sistema"""
    try:
        tipo_filtro = request.args.get('tipo')
        
        usuarios = DADOS_SISTEMA["usuarios"].copy()
        
        # Aplicar filtro de tipo
        if tipo_filtro:
            usuarios = [u for u in usuarios if u["tipo"] == tipo_filtro]
        
        # Remover informações sensíveis
        for usuario in usuarios:
            if "senha" in usuario:
                del usuario["senha"]
        
        return jsonify({
            "success": True,
            "usuarios": usuarios,
            "total": len(usuarios),
            "filtro_tipo": tipo_filtro
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao carregar usuários"
        }), 500

@app.route('/api/notificacoes')
def listar_notificacoes():
    """Lista notificações do sistema"""
    try:
        usuario_id = request.args.get('usuario_id')
        tipo_usuario = request.args.get('tipo_usuario')
        
        notificacoes = DADOS_SISTEMA["notificacoes"].copy()
        
        # Filtrar por usuário específico ou tipo
        if usuario_id:
            notificacoes = [n for n in notificacoes 
                           if n.get("destinatario") == usuario_id or 
                           n.get("destinatario") == "todos"]
        
        if tipo_usuario:
            notificacoes = [n for n in notificacoes 
                           if n.get("destinatarioTipo") == tipo_usuario or 
                           n.get("destinatario") == "todos"]
        
        # Ordenar por data (mais recentes primeiro)
        notificacoes.sort(key=lambda x: x.get("data", ""), reverse=True)
        
        return jsonify({
            "success": True,
            "notificacoes": notificacoes,
            "total": len(notificacoes)
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar notificações: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao carregar notificações"
        }), 500

@app.route('/api/notificacoes', methods=['POST'])
def criar_notificacao():
    """Criar nova notificação"""
    try:
        dados = request.get_json()
        
        nova_notificacao = {
            "id": f"notif_{len(DADOS_SISTEMA['notificacoes']) + 1:03d}",
            "tipo": dados.get("tipo", "info"),
            "titulo": dados.get("titulo", ""),
            "mensagem": dados.get("mensagem", ""),
            "destinatario": dados.get("destinatario", "todos"),
            "destinatarioTipo": dados.get("destinatarioTipo"),
            "remetente": dados.get("remetente", "Sistema"),
            "lida": False,
            "data": datetime.now().isoformat(),
            "acao": dados.get("acao"),
            "processoId": dados.get("processoId"),
            "metadata": dados.get("metadata", {})
        }
        
        DADOS_SISTEMA["notificacoes"].append(nova_notificacao)
        
        logger.info(f"Notificação criada: {nova_notificacao['titulo']}")
        
        return jsonify({
            "success": True,
            "notificacao": nova_notificacao,
            "mensagem": "Notificação criada com sucesso"
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar notificação: {e}")
        return jsonify({
            "success": False,
            "erro": "Erro ao criar notificação"
        }), 500

# Endpoints para download de arquivos (Excel/Word)
@app.route('/api/download/proposta/<protocolo>/excel')
def download_proposta_excel(protocolo):
    """Download de proposta em formato Excel"""
    try:
        proposta = next((p for p in DADOS_SISTEMA["propostas"] 
                        if p["protocolo"] == protocolo), None)
        
        if not proposta:
            return jsonify({"erro": "Proposta não encontrada"}), 404
        
        # Em produção, aqui seria gerado um arquivo Excel real
        # Por enquanto, retorna JSON simulando o download
        return jsonify({
            "success": True,
            "mensagem": "Em produção, seria gerado arquivo Excel",
            "proposta": proposta,
            "formato": "excel"
        })
        
    except Exception as e:
        logger.error(f"Erro ao gerar Excel: {e}")
        return jsonify({"erro": "Erro ao gerar arquivo"}), 500

@app.route('/api/download/proposta/<protocolo>/word')
def download_proposta_word(protocolo):
    """Download de proposta em formato Word"""
    try:
        proposta = next((p for p in DADOS_SISTEMA["propostas"] 
                        if p["protocolo"] == protocolo), None)
        
        if not proposta:
            return jsonify({"erro": "Proposta não encontrada"}), 404
        
        # Em produção, aqui seria gerado um arquivo Word real
        return jsonify({
            "success": True,
            "mensagem": "Em produção, seria gerado arquivo Word",
            "proposta": proposta,
            "formato": "word"
        })
        
    except Exception as e:
        logger.error(f"Erro ao gerar Word: {e}")
        return jsonify({"erro": "Erro ao gerar arquivo"}), 500

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
            # Se arquivo não existe, retornar index.html para SPAs
            index_path = os.path.join(STATIC_DIR, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(STATIC_DIR, 'index.html')
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
    logger.info("🚀 Iniciando Sistema de Gestão de Propostas...")
    logger.info(f"📁 Diretório de trabalho: {os.getcwd()}")
    logger.info(f"📂 Diretório estático: {STATIC_DIR}")
    
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🌐 Servidor iniciando na porta {port}")
    logger.info("✅ Versão 3.1 - Propostas CORRIGIDAS")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
