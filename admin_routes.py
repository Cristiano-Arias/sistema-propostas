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

# Configuração do banco de dados PostgreSQL
def get_db_config():
    """Retorna configuração do banco PostgreSQL"""
    if os.environ.get('DATABASE_URL'):
        return os.environ.get('DATABASE_URL')
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

def init_admin_routes(app):
    """Inicializa rotas de administração no app Flask existente"""
    
    def admin_required(f):
        """Decorator para verificar se usuário é admin"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
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
                    
                except jwt.InvalidTokenError:
                    return jsonify({'success': False, 'message': 'Token inválido'}), 401
                    
            except Exception as e:
                logger.error(f"Erro na verificação de admin: {e}")
                return jsonify({'success': False, 'message': 'Erro de autenticação'}), 401
        
        return decorated_function
    
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
                WHERE email = %s AND perfil = %s
            ''', (email,))
            
            usuario = cursor.fetchone()
            conn.close()
            
            if not usuario:
                return jsonify({'success': False, 'message': 'Credenciais inválidas ou usuário não é admin'}), 401
            
            # Verificar senha
            if bcrypt.checkpw(senha.encode('utf-8'), usuario['senha']):
                # Gerar token JWT
                payload = {
                    'user_id': usuario['id'],
                    'nome': usuario['nome'],
                    'email': usuario['email'],
                    'perfil': usuario['perfil']
                }
                
                token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
                
                # Log da ação
                logger.info(f"Login admin realizado: {usuario['nome']} ({usuario['email']})")
                
                return jsonify({
                    'success': True,
                    'message': 'Login realizado com sucesso',
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
        """Listar todos os usuários"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, nome, email, perfil, created_at
                FROM usuarios
                ORDER BY created_at DESC
            ''')
            
            usuarios = cursor.fetchall()
            conn.close()
            
            # Converter para lista de dicionários
            usuarios_list = []
            for usuario in usuarios:
                usuarios_list.append({
                    'id': usuario['id'],
                    'nome': usuario['nome'],
                    'email': usuario['email'],
                    'perfil': usuario['perfil'],
                    'created_at': usuario['created_at'].strftime('%d/%m/%Y %H:%M') if usuario['created_at'] else ''
                })
            
            return jsonify({'success': True, 'usuarios': usuarios_list})
            
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}")
            return jsonify({'success': False, 'message': 'Erro ao carregar usuários'}), 500
    
    @app.route('/api/admin/usuarios', methods=['POST'])
    @admin_required
    def criar_usuario():
        """Criar novo usuário"""
        try:
            data = request.get_json()
            nome = data.get('nome')
            email = data.get('email')
            senha = data.get('senha')
            perfil = data.get('perfil')
            
            if not all([nome, email, senha, perfil]):
                return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'}), 400
            
            conn = get_db()
            cursor = conn.cursor()
            
            # Verificar se email já existe
            cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': 'Email já cadastrado'}), 400
            
            # Criptografar senha
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
            
            # Inserir usuário
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha, perfil)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (nome, email, senha_hash, perfil))
            
            usuario_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            
            # Log da ação
            logger.info(f"Usuário criado pelo admin {request.current_user['nome']}: {nome} ({email})")
            
            return jsonify({
                'success': True,
                'message': 'Usuário criado com sucesso',
                'usuario_id': usuario_id
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
            nome = data.get('nome')
            email = data.get('email')
            senha = data.get('senha')
            perfil = data.get('perfil')
            
            if not all([nome, email, perfil]):
                return jsonify({'success': False, 'message': 'Nome, email e perfil são obrigatórios'}), 400
            
            conn = get_db()
            cursor = conn.cursor()
            
            # Verificar se usuário existe
            cursor.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
            if not cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
            
            # Verificar se email já existe em outro usuário
            cursor.execute("SELECT * FROM usuarios WHERE email = %s AND id != %s", (email, usuario_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': 'Email já cadastrado para outro usuário'}), 400
            
            # Atualizar usuário
            if senha:
                # Se senha foi fornecida, criptografar e atualizar
                senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
                cursor.execute('''
                    UPDATE usuarios 
                    SET nome = %s, email = %s, senha = %s, perfil = %s
                    WHERE id = %s
                ''', (nome, email, senha_hash, perfil, usuario_id))
            else:
                # Se senha não foi fornecida, manter a atual
                cursor.execute('''
                    UPDATE usuarios 
                    SET nome = %s, email = %s, perfil = %s
                    WHERE id = %s
                ''', (nome, email, perfil, usuario_id))
            
            conn.commit()
            conn.close()
            
            # Log da ação
            logger.info(f"Usuário editado pelo admin {request.current_user['nome']}: {nome} ({email})")
            
            return jsonify({'success': True, 'message': 'Usuário atualizado com sucesso'})
            
        except Exception as e:
            logger.error(f"Erro ao editar usuário: {e}")
            return jsonify({'success': False, 'message': 'Erro ao editar usuário'}), 500
    
    @app.route('/api/admin/usuarios/<int:usuario_id>', methods=['DELETE'])
    @admin_required
    def excluir_usuario(usuario_id):
        """Excluir usuário"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Verificar se usuário existe
            cursor.execute("SELECT nome, email FROM usuarios WHERE id = %s", (usuario_id,))
            usuario = cursor.fetchone()
            if not usuario:
                conn.close()
                return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
            
            # Não permitir excluir o próprio usuário
            if usuario_id == request.current_user['user_id']:
                conn.close()
                return jsonify({'success': False, 'message': 'Não é possível excluir seu próprio usuário'}), 400
            
            # Excluir usuário
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
            conn.commit()
            conn.close()
            
            # Log da ação
            logger.info(f"Usuário excluído pelo admin {request.current_user['nome']}: {usuario['nome']} ({usuario['email']})")
            
            return jsonify({'success': True, 'message': 'Usuário excluído com sucesso'})
            
        except Exception as e:
            logger.error(f"Erro ao excluir usuário: {e}")
            return jsonify({'success': False, 'message': 'Erro ao excluir usuário'}), 500
    
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
            
            stats_perfil = {}
            for row in cursor.fetchall():
                stats_perfil[row['perfil']] = row['total']
            
            # Total de usuários
            cursor.execute("SELECT COUNT(*) as total FROM usuarios")
            total_usuarios = cursor.fetchone()['total']
            
            conn.close()
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_usuarios': total_usuarios,
                    'por_perfil': stats_perfil
                }
            })
            
        except Exception as e:
            logger.error(f"Erro ao carregar estatísticas: {e}")
            return jsonify({'success': False, 'message': 'Erro ao carregar estatísticas'}), 500
    
    logger.info("Rotas de administração inicializadas com sucesso")

def criar_admin_inicial():
    """Criar usuário admin inicial se não existir"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verificar se já existe admin
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE perfil = %s", ('admin',))
        if cursor.fetchone()[0] == 0:
            # Criar admin padrão
            senha_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha, perfil)
                VALUES (%s, %s, %s, %s)
            ''', ('Administrador', 'admin@sistema.com', senha_hash, 'admin'))
            
            conn.commit()
            logger.info("Usuário admin inicial criado: admin@sistema.com / admin123")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao criar admin inicial: {e}")
