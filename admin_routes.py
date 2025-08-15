#!/usr/bin/env python3
"""
Módulo de Administração - Sistema de Compras
Funcionalidades de gestão de usuários para administradores
COMPATÍVEL com sistema existente - ZERO CONFLITOS
"""

import os
import psycopg2
import psycopg2.extras
import bcrypt
import logging
from datetime import datetime
from flask import request, jsonify, session
import jwt
from functools import wraps

logger = logging.getLogger(__name__)

def init_admin_routes(app):
    """Inicializa rotas de administração no app Flask existente"""
    
    def admin_required(f):
        """Decorator para verificar se usuário é admin"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'success': False, 'message': 'Token não fornecido'}), 401
            
            try:
                token = auth_header.split(' ')[1]  # Bearer TOKEN
                payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                
                # Verificar se é admin
                if payload.get('perfil') != 'admin':
                    return jsonify({'success': False, 'message': 'Acesso negado - Admin necessário'}), 403
                
                request.current_user = payload
                return f(*args, **kwargs)
                
            except jwt.ExpiredSignatureError:
                return jsonify({'success': False, 'message': 'Token expirado'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'success': False, 'message': 'Token inválido'}), 401
            except Exception as e:
                logger.error(f"Erro na verificação de admin: {e}")
                return jsonify({'success': False, 'message': 'Erro de autenticação'}), 401
        
        return decorated_function
    
    # Configuração do banco de dados PostgreSQL
    def get_db_config():
        """Retorna configuração do banco PostgreSQL"""
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return database_url
        else:
            return {
                'host': os.environ.get('DB_HOST', 'localhost'),
                'database': os.environ.get('DB_NAME', 'sistema_compras'),
                'user': os.environ.get('DB_USER', 'postgres'),
                'password': os.environ.get('DB_PASSWORD', 'postgres'),
                'port': os.environ.get('DB_PORT', '5432')
            }

    def get_db():
        """Conecta ao banco PostgreSQL"""
        try:
            db_config = get_db_config()
            if isinstance(db_config, str):
                conn = psycopg2.connect(db_config, cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                conn = psycopg2.connect(**db_config, cursor_factory=psycopg2.extras.RealDictCursor)
            
            conn.autocommit = False
            return conn
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao banco: {e}")
            raise
    
    @app.route('/api/admin/login', methods=['POST'])
    def admin_login():
        """Login específico para administradores"""
        try:
            data = request.get_json()
            email = data.get('email')
            senha = data.get('senha')
            
            if not email or not senha:
                return jsonify({'success': False, 'message': 'Email e senha são obrigatórios'}), 400
            
            conn = get_db()
            cursor = conn.cursor()
            
            # Buscar usuário admin
            cursor.execute('''
                SELECT id, nome, email, senha, perfil 
                FROM usuarios 
                WHERE email = %s AND perfil = 'admin'
            ''', (email,))
            
            usuario = cursor.fetchone()
            conn.close()
            
            if not usuario:
                return jsonify({'success': False, 'message': 'Credenciais inválidas ou usuário não é admin'}), 401
            
            # Verificar senha
            senha_hash = usuario['senha']
            # Se a senha está como string, usar diretamente
            # Se está como bytes, converter para string
            if isinstance(senha_hash, bytes):
                senha_hash = senha_hash.decode('utf-8')
            
            if bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
                # Gerar token JWT
                payload = {
                    'usuario_id': usuario['id'],
                    'nome': usuario['nome'],
                    'email': usuario['email'],
                    'perfil': usuario['perfil'],
                    'exp': datetime.utcnow().timestamp() + (8 * 3600)  # 8 horas
                }
                token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
                
                return jsonify({
                    'success': True,
                    'message': 'Login admin realizado com sucesso',
                    'token': token,
                    'usuario': {
                        'id': usuario['id'],
                        'nome': usuario['nome'],
                        'email': usuario['email'],
                        'perfil': usuario['perfil']
                    }
                })
            else:
                return jsonify({'success': False, 'message': 'Credenciais inválidas'}), 401
                
        except Exception as e:
            logger.error(f"Erro no login admin: {e}")
            return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
    
    @app.route('/api/admin/usuarios', methods=['GET'])
    @admin_required
    def listar_usuarios():
        """Listar todos os usuários do sistema"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, nome, email, perfil, criado_em
                FROM usuarios
                ORDER BY criado_em DESC
            ''')
            
            usuarios = []
            for row in cursor.fetchall():
                usuarios.append({
                    'id': row['id'],
                    'nome': row['nome'],
                    'email': row['email'],
                    'perfil': row['perfil'],
                    'criado_em': row['criado_em']
                })
            
            conn.close()
            
            return jsonify({
                'success': True,
                'usuarios': usuarios,
                'total': len(usuarios)
            })
            
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}")
            return jsonify({'success': False, 'message': 'Erro ao carregar usuários'}), 500
    
    @app.route('/api/admin/usuarios', methods=['POST'])
    @admin_required
    def criar_usuario():
        """Criar novo usuário"""
        try:
            data = request.get_json()
            
            # Validar dados obrigatórios
            campos_obrigatorios = ['nome', 'email', 'senha', 'perfil']
            for campo in campos_obrigatorios:
                if not data.get(campo):
                    return jsonify({'success': False, 'message': f'{campo} é obrigatório'}), 400
            
            nome = data['nome']
            email = data['email']
            senha = data['senha']
            perfil = data['perfil']
            
            # Validar perfil
            perfis_validos = ['admin', 'comprador', 'requisitante', 'fornecedor']
            if perfil not in perfis_validos:
                return jsonify({'success': False, 'message': 'Perfil inválido'}), 400
            
            conn = get_db()
            cursor = conn.cursor()
            
            # Verificar se email já existe
            cursor.execute('SELECT id FROM usuarios WHERE email = %s', (email,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': 'Email já cadastrado'}), 400
            
            # Criptografar senha
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
            
            # Inserir usuário
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha, perfil)
                VALUES (%s, %s, %s, %s)
            ''', (nome, email, senha_hash, perfil))
            
            usuario_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Log da ação
            logger.info(f"Usuário criado pelo admin {request.current_user['nome']}: {nome} ({email})")
            
            return jsonify({
                'success': True,
                'message': 'Usuário criado com sucesso',
                'usuario': {
                    'id': usuario_id,
                    'nome': nome,
                    'email': email,
                    'perfil': perfil
                }
            })
            
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}")
            return jsonify({'success': False, 'message': 'Erro ao criar usuário'}), 500
    
    @app.route('/api/admin/usuarios/<int:usuario_id>', methods=['PUT'])
    @admin_required
    def editar_usuario(usuario_id):
        """Editar usuário existente"""
        try:
            data = request.get_json()
            
            conn = get_db()
            cursor = conn.cursor()
            
            # Verificar se usuário existe
            cursor.execute('SELECT * FROM usuarios WHERE id = %s', (usuario_id,))
            usuario_atual = cursor.fetchone()
            
            if not usuario_atual:
                conn.close()
                return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
            
            # Campos que podem ser atualizados
            nome = data.get('nome', usuario_atual['nome'])
            email = data.get('email', usuario_atual['email'])
            perfil = data.get('perfil', usuario_atual['perfil'])
            
            # Validar perfil se fornecido
            if perfil not in ['admin', 'comprador', 'requisitante', 'fornecedor']:
                conn.close()
                return jsonify({'success': False, 'message': 'Perfil inválido'}), 400
            
            # Verificar se email já existe (exceto para o próprio usuário)
            cursor.execute('SELECT id FROM usuarios WHERE email = %s AND id != %s', (email, usuario_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': 'Email já cadastrado'}), 400
            
            # Atualizar usuário
            if data.get('senha'):
                # Se nova senha fornecida, criptografar
                senha_hash = bcrypt.hashpw(data['senha'].encode('utf-8'), bcrypt.gensalt())
                cursor.execute('''
                    UPDATE usuarios 
                    SET nome = %s, email = %s, senha = %s, perfil = %s
                    WHERE id = %s
                ''', (nome, email, senha_hash, perfil, usuario_id))
            else:
                # Manter senha atual
                cursor.execute('''
                    UPDATE usuarios 
                    SET nome = %s, email = %s, perfil = %s
                    WHERE id = %s
                ''', (nome, email, perfil, usuario_id))
            
            conn.commit()
            conn.close()
            
            # Log da ação
            logger.info(f"Usuário editado pelo admin {request.current_user['nome']}: {nome} ({email})")
            
            return jsonify({
                'success': True,
                'message': 'Usuário atualizado com sucesso',
                'usuario': {
                    'id': usuario_id,
                    'nome': nome,
                    'email': email,
                    'perfil': perfil
                }
            })
            
        except Exception as e:
            logger.error(f"Erro ao editar usuário: {e}")
            return jsonify({'success': False, 'message': 'Erro ao atualizar usuário'}), 500
    
    @app.route('/api/admin/usuarios/<int:usuario_id>', methods=['DELETE'])
    @admin_required
    def deletar_usuario(usuario_id):
        """Deletar usuário"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Verificar se usuário existe
            cursor.execute('SELECT nome, email FROM usuarios WHERE id = %s', (usuario_id,))
            usuario = cursor.fetchone()
            
            if not usuario:
                conn.close()
                return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
            
            # Não permitir deletar o próprio usuário admin
            if usuario_id == request.current_user['usuario_id']:
                conn.close()
                return jsonify({'success': False, 'message': 'Não é possível deletar seu próprio usuário'}), 400
            
            # Deletar usuário
            cursor.execute('DELETE FROM usuarios WHERE id = %s', (usuario_id,))
            conn.commit()
            conn.close()
            
            # Log da ação
            logger.info(f"Usuário deletado pelo admin {request.current_user['nome']}: {usuario['nome']} ({usuario['email']})")
            
            return jsonify({
                'success': True,
                'message': 'Usuário deletado com sucesso'
            })
            
        except Exception as e:
            logger.error(f"Erro ao deletar usuário: {e}")
            return jsonify({'success': False, 'message': 'Erro ao deletar usuário'}), 500
    
    @app.route('/api/admin/stats', methods=['GET'])
    @admin_required
    def estatisticas_admin():
        """Estatísticas do sistema para admin"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Contar usuários por perfil
            cursor.execute('''
                SELECT perfil, COUNT(*) as total
                FROM usuarios
                GROUP BY perfil
            ''')
            usuarios_por_perfil = {row['perfil']: row['total'] for row in cursor.fetchall()}
            
            # Contar TRs por status
            cursor.execute('''
                SELECT status, COUNT(*) as total
                FROM termos_referencia
                GROUP BY status
            ''')
            trs_por_status = {row['status']: row['total'] for row in cursor.fetchall()}
            
            # Contar processos por status
            cursor.execute('''
                SELECT status, COUNT(*) as total
                FROM processos
                GROUP BY status
            ''')
            processos_por_status = {row['status']: row['total'] for row in cursor.fetchall()}
            
            conn.close()
            
            return jsonify({
                'success': True,
                'stats': {
                    'usuarios_por_perfil': usuarios_por_perfil,
                    'trs_por_status': trs_por_status,
                    'processos_por_status': processos_por_status,
                    'total_usuarios': sum(usuarios_por_perfil.values()),
                    'total_trs': sum(trs_por_status.values()),
                    'total_processos': sum(processos_por_status.values())
                }
            })
            
        except Exception as e:
            logger.error(f"Erro ao carregar estatísticas: {e}")
            return jsonify({'success': False, 'message': 'Erro ao carregar estatísticas'}), 500
    
    logger.info("Rotas de administração inicializadas com sucesso")

def criar_admin_inicial():
    """Criar usuário admin inicial se não existir"""
    try:
        # Usar a mesma configuração do sistema principal
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            db_config = {
                'host': os.environ.get('DB_HOST', 'localhost'),
                'database': os.environ.get('DB_NAME', 'sistema_compras'),
                'user': os.environ.get('DB_USER', 'postgres'),
                'password': os.environ.get('DB_PASSWORD', 'postgres'),
                'port': os.environ.get('DB_PORT', '5432')
            }
            conn = psycopg2.connect(**db_config, cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor = conn.cursor()
        
        # Verificar se já existe admin
        cursor.execute("SELECT COUNT(*) as count FROM usuarios WHERE perfil = %s", ('admin',))
        result = cursor.fetchone()
        
        if result['count'] == 0:
            # Criar admin padrão
            senha_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha, perfil)
                VALUES (%s, %s, %s, %s)
            ''', ('Administrador', 'admin@sistema.com', senha_hash, 'admin'))
            
            conn.commit()
            logger.info("Usuário admin inicial criado: admin@sistema.com / admin123")
        else:
            logger.info("Usuário admin já existe")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao criar admin inicial: {e}")

