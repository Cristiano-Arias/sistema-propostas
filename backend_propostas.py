#!/usr/bin/env python3
"""
Backend Corrigido - Sistema de Gestão de Propostas
Versão 4.0 - Estrutura Revisada e Confirmada
Compatível com Render.com e GitHub

CORREÇÕES IMPLEMENTADAS:
- Banco de dados SQLite real (substitui dados em memória)
- Sistema de autenticação JWT seguro
- APIs RESTful padronizadas
- Logs de auditoria
- Tratamento de erros robusto
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Imports dos módulos criados
from config import get_config
from models import db, init_db, Usuario, Processo, Proposta, Notificacao, LogAuditoria
from auth import init_jwt, AuthService, require_auth, require_role, log_user_action

# Configuração do Flask
app = Flask(__name__, static_folder='static')

# Carregar configuração baseada no ambiente
config_class = get_config()
app.config.from_object(config_class)

# Configurar CORS
CORS(app, origins=app.config['CORS_ORIGINS'])

# Inicializar extensões
init_jwt(app)
init_db(app)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, app.config['LOG_LEVEL']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# ROTAS DE AUTENTICAÇÃO
# ========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login com JWT"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('senha'):
            return jsonify({
                'success': False,
                'error': 'Dados incompletos',
                'message': 'Email e senha são obrigatórios'
            }), 400
        
        result = AuthService.login(
            email=data['email'],
            senha=data['senha'],
            ip_origem=request.remote_addr
        )
        
        status_code = 200 if result['success'] else 401
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro interno do servidor'
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Logout revogando token"""
    try:
        from flask_jwt_extended import get_jwt
        jti = get_jwt()['jti']
        
        result = AuthService.logout(jti)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro no logout: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro ao realizar logout'
        }), 500

@app.route('/api/auth/refresh', methods=['POST'])
@require_auth
def refresh():
    """Renovar token de acesso"""
    try:
        result = AuthService.refresh_token()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao renovar token: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno',
            'message': 'Erro ao renovar token'
        }), 500

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Obter dados do usuário atual"""
    try:
        usuario = AuthService.get_current_user()
        if usuario:
            return jsonify({
                'success': True,
                'usuario': usuario.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Usuário não encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Erro ao obter usuário atual: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno'
        }), 500

# ========================================
# ROTAS DE STATUS E INFORMAÇÕES
# ========================================

@app.route('/')
def index():
    """Redireciona para a página de login"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/status')
def api_status():
    """Status detalhado da API"""
    try:
        # Estatísticas do banco
        stats = {
            'processos_total': Processo.query.count(),
            'processos_ativos': Processo.query.filter_by(status='ativo').count(),
            'propostas_total': Proposta.query.count(),
            'usuarios_total': Usuario.query.count(),
            'usuarios_ativos': Usuario.query.filter_by(ativo=True).count(),
            'notificacoes_total': Notificacao.query.count()
        }
        
        return jsonify({
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "versao": "4.0",
            "ambiente": os.environ.get('FLASK_ENV', 'development'),
            "estatisticas": stats
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# ========================================
# ROTAS DE PROCESSOS
# ========================================

@app.route('/api/v1/processos', methods=['GET'])
@require_auth
def listar_processos():
    """Lista todos os processos com filtros"""
    try:
        # Parâmetros de filtro
        status_filtro = request.args.get('status', 'todos')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Query base
        query = Processo.query
        
        # Aplicar filtros
        if status_filtro != 'todos':
            if status_filtro == 'ativo':
                query = query.filter(Processo.prazo >= datetime.now())
            elif status_filtro == 'encerrado':
                query = query.filter(Processo.prazo < datetime.now())
        
        # Paginação
        processos_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Converter para dict e calcular status
        processos = []
        for processo in processos_paginated.items:
            processo_dict = processo.to_dict()
            processo_dict['status_calculado'] = processo.calcular_status()
            
            # Contar propostas
            processo_dict['total_propostas'] = len(processo.propostas)
            
            processos.append(processo_dict)
        
        # Log da ação
        log_user_action('VIEW_PROCESSOS', 'processo', detalhes={
            'filtro': status_filtro,
            'total': len(processos)
        })
        
        return jsonify({
            "success": True,
            "processos": processos,
            "total": processos_paginated.total,
            "pages": processos_paginated.pages,
            "current_page": page,
            "filtro_aplicado": status_filtro
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar processos: {e}")
        return jsonify({
            "success": False,
            "error": "Erro ao carregar processos"
        }), 500

@app.route('/api/v1/processos/<processo_id>', methods=['GET'])
@require_auth
def obter_processo(processo_id):
    """Obtém um processo específico"""
    try:
        processo = Processo.query.get(processo_id)
        
        if not processo:
            return jsonify({
                'success': False,
                'error': 'Processo não encontrado'
            }), 404
        
        processo_dict = processo.to_dict()
        processo_dict['status_calculado'] = processo.calcular_status()
        processo_dict['propostas'] = [p.to_dict() for p in processo.propostas]
        
        # Log da ação
        log_user_action('VIEW_PROCESSO', 'processo', processo_id)
        
        return jsonify({
            'success': True,
            'processo': processo_dict
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter processo {processo_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar processo'
        }), 500

@app.route('/api/v1/processos', methods=['POST'])
@require_role('admin', 'comprador', 'requisitante')
def criar_processo():
    """Cria um novo processo"""
    try:
        data = request.get_json()
        
        # Validações básicas
        required_fields = ['numero', 'objeto', 'modalidade', 'prazo']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                }), 400
        
        # Verificar se número já existe
        if Processo.query.filter_by(numero=data['numero']).first():
            return jsonify({
                'success': False,
                'error': 'Número de processo já existe'
            }), 400
        
        # Criar processo
        from flask_jwt_extended import get_jwt_identity
        usuario_id = get_jwt_identity()
        
        processo = Processo(
            id=f"proc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            numero=data['numero'],
            objeto=data['objeto'],
            modalidade=data['modalidade'],
            prazo=datetime.fromisoformat(data['prazo'].replace('Z', '+00:00')),
            criado_por=usuario_id
        )
        
        if data.get('fornecedores_convidados'):
            processo.set_fornecedores_convidados(data['fornecedores_convidados'])
        
        db.session.add(processo)
        db.session.commit()
        
        # Log da ação
        log_user_action('CREATE_PROCESSO', 'processo', processo.id, {
            'numero': processo.numero,
            'objeto': processo.objeto
        })
        
        return jsonify({
            'success': True,
            'message': 'Processo criado com sucesso',
            'processo': processo.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar processo: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao criar processo'
        }), 500

# ========================================
# ROTAS DE PROPOSTAS
# ========================================

@app.route('/api/v1/propostas', methods=['GET'])
@require_auth
def listar_propostas():
    """Lista propostas com filtros"""
    try:
        processo_id = request.args.get('processo_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Query base
        query = Proposta.query
        
        # Filtrar por processo se especificado
        if processo_id:
            query = query.filter_by(processo_id=processo_id)
        
        # Paginação
        propostas_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        propostas = [p.to_dict() for p in propostas_paginated.items]
        
        # Log da ação
        log_user_action('VIEW_PROPOSTAS', 'proposta', detalhes={
            'processo_id': processo_id,
            'total': len(propostas)
        })
        
        return jsonify({
            'success': True,
            'propostas': propostas,
            'total': propostas_paginated.total,
            'pages': propostas_paginated.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar propostas: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar propostas'
        }), 500

@app.route('/api/v1/propostas', methods=['POST'])
@require_role('admin', 'fornecedor')
def criar_proposta():
    """Cria uma nova proposta"""
    try:
        data = request.get_json()
        
        # Validações básicas
        required_fields = ['processo_id', 'empresa', 'cnpj', 'valor_total']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório: {field}'
                }), 400
        
        # Verificar se processo existe
        processo = Processo.query.get(data['processo_id'])
        if not processo:
            return jsonify({
                'success': False,
                'error': 'Processo não encontrado'
            }), 404
        
        # Verificar se processo ainda está ativo
        if processo.prazo < datetime.now():
            return jsonify({
                'success': False,
                'error': 'Prazo do processo encerrado'
            }), 400
        
        # Criar proposta
        from flask_jwt_extended import get_jwt_identity
        usuario_id = get_jwt_identity()
        
        proposta = Proposta(
            id=f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            protocolo=f"PROP-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            processo_id=data['processo_id'],
            empresa=data['empresa'],
            cnpj=data['cnpj'],
            valor_total=float(data['valor_total']),
            validade_proposta=data.get('validade_proposta', '60 dias'),
            fornecedor_id=usuario_id
        )
        
        # Adicionar dados técnicos e comerciais se fornecidos
        if data.get('dados_tecnicos'):
            proposta.set_dados_tecnicos(data['dados_tecnicos'])
        
        if data.get('dados_comerciais'):
            proposta.set_dados_comerciais(data['dados_comerciais'])
        
        db.session.add(proposta)
        db.session.commit()
        
        # Log da ação
        log_user_action('CREATE_PROPOSTA', 'proposta', proposta.id, {
            'processo_id': data['processo_id'],
            'empresa': data['empresa'],
            'valor_total': data['valor_total']
        })
        
        return jsonify({
            'success': True,
            'message': 'Proposta enviada com sucesso',
            'proposta': proposta.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Erro ao criar proposta: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Erro ao enviar proposta'
        }), 500

# ========================================
# ROTAS DE USUÁRIOS
# ========================================

@app.route('/api/v1/usuarios', methods=['GET'])
@require_role('admin', 'auditor')
def listar_usuarios():
    """Lista usuários (apenas admin e auditor)"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        tipo_filtro = request.args.get('tipo')
        
        query = Usuario.query
        
        if tipo_filtro:
            query = query.filter_by(tipo=tipo_filtro)
        
        usuarios_paginated = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        usuarios = []
        for usuario in usuarios_paginated.items:
            user_dict = usuario.to_dict()
            # Remover dados sensíveis
            user_dict.pop('senha_hash', None)
            usuarios.append(user_dict)
        
        # Log da ação
        log_user_action('VIEW_USUARIOS', 'usuario', detalhes={
            'filtro': tipo_filtro,
            'total': len(usuarios)
        })
        
        return jsonify({
            'success': True,
            'usuarios': usuarios,
            'total': usuarios_paginated.total,
            'pages': usuarios_paginated.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar usuários'
        }), 500

# ========================================
# ROTAS DE NOTIFICAÇÕES
# ========================================

@app.route('/api/v1/notificacoes', methods=['GET'])
@require_auth
def listar_notificacoes():
    """Lista notificações do usuário atual"""
    try:
        from flask_jwt_extended import get_jwt_identity
        usuario_id = get_jwt_identity()
        
        notificacoes = Notificacao.query.filter_by(
            usuario_id=usuario_id
        ).order_by(Notificacao.data_criacao.desc()).limit(50).all()
        
        return jsonify({
            'success': True,
            'notificacoes': [n.to_dict() for n in notificacoes]
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar notificações: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar notificações'
        }), 500

# ========================================
# ROTAS DE LOGS E AUDITORIA
# ========================================

@app.route('/api/v1/logs', methods=['GET'])
@require_role('admin', 'auditor')
def listar_logs():
    """Lista logs de auditoria"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        acao_filtro = request.args.get('acao')
        usuario_filtro = request.args.get('usuario_id')
        
        query = LogAuditoria.query
        
        if acao_filtro:
            query = query.filter_by(acao=acao_filtro)
        
        if usuario_filtro:
            query = query.filter_by(usuario_id=usuario_filtro)
        
        logs_paginated = query.order_by(
            LogAuditoria.data_acao.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        logs = [log.to_dict() for log in logs_paginated.items]
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': logs_paginated.total,
            'pages': logs_paginated.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar logs: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao carregar logs'
        }), 500

# ========================================
# ROTAS ESTÁTICAS (COMPATIBILIDADE)
# ========================================

@app.route('/<path:filename>')
def static_files(filename):
    """Serve arquivos estáticos"""
    return send_from_directory(app.static_folder, filename)

# ========================================
# TRATAMENTO DE ERROS
# ========================================

@app.errorhandler(404)
def not_found(error):
    """Tratamento para 404"""
    return jsonify({
        'success': False,
        'error': 'Recurso não encontrado',
        'message': 'O recurso solicitado não foi encontrado'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Tratamento para 500"""
    logger.error(f"Erro interno: {error}")
    return jsonify({
        'success': False,
        'error': 'Erro interno do servidor',
        'message': 'Erro interno do servidor'
    }), 500

@app.errorhandler(403)
def forbidden(error):
    """Tratamento para 403"""
    return jsonify({
        'success': False,
        'error': 'Acesso negado',
        'message': 'Você não tem permissão para acessar este recurso'
    }), 403

# ========================================
# INICIALIZAÇÃO
# ========================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"🚀 Iniciando Sistema de Propostas v4.0")
    logger.info(f"📊 Ambiente: {os.environ.get('FLASK_ENV', 'development')}")
    logger.info(f"🔌 Porta: {port}")
    logger.info(f"🔧 Debug: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
