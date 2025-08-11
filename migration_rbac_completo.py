#!/usr/bin/env python3
"""
Script de Migração RBAC - Sistema de Propostas
Versão: 2.0
Data: 11 de agosto de 2025
Autor: Manus AI

Este script inicializa o banco de dados com a estrutura RBAC completa,
incluindo usuários, roles, permissões e dados iniciais necessários.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Adicionar o diretório atual ao path para importar os modelos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from models import db, Usuario, Role, Permission
    from config import Config
    from flask import Flask
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print("Certifique-se de que os arquivos models.py e config.py estão no mesmo diretório.")
    sys.exit(1)

def create_app():
    """Cria e configura a aplicação Flask para migração"""
    app = Flask(__name__)
    
    # Configurações do banco de dados
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'chave-secreta-para-migracao'
    
    # Inicializar banco de dados
    db.init_app(app)
    
    return app

def backup_database():
    """Cria backup do banco de dados atual se existir"""
    db_file = 'database.db'
    if os.path.exists(db_file):
        backup_name = f'database_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        try:
            import shutil
            shutil.copy2(db_file, backup_name)
            print(f"✅ Backup criado: {backup_name}")
            return backup_name
        except Exception as e:
            print(f"⚠️ Erro ao criar backup: {e}")
            return None
    return None

def create_permissions():
    """Cria todas as permissões do sistema"""
    permissions_data = [
        # Gestão de Usuários
        {'name': 'criar_usuario', 'description': 'Criar novos usuários no sistema'},
        {'name': 'editar_usuario', 'description': 'Editar informações de usuários'},
        {'name': 'excluir_usuario', 'description': 'Excluir usuários do sistema'},
        {'name': 'listar_usuarios', 'description': 'Visualizar lista de usuários'},
        {'name': 'resetar_senha', 'description': 'Resetar senhas de usuários'},
        
        # Gestão de Processos
        {'name': 'criar_processo', 'description': 'Criar novos processos licitatórios'},
        {'name': 'editar_processo', 'description': 'Editar processos licitatórios'},
        {'name': 'excluir_processo', 'description': 'Excluir processos licitatórios'},
        {'name': 'aprovar_processo', 'description': 'Aprovar processos licitatórios'},
        {'name': 'visualizar_processo', 'description': 'Visualizar processos licitatórios'},
        
        # Gestão de Propostas
        {'name': 'criar_proposta', 'description': 'Criar propostas para processos'},
        {'name': 'editar_proposta', 'description': 'Editar propostas existentes'},
        {'name': 'excluir_proposta', 'description': 'Excluir propostas'},
        {'name': 'avaliar_proposta', 'description': 'Avaliar e pontuar propostas'},
        {'name': 'visualizar_proposta', 'description': 'Visualizar propostas'},
        
        # Gestão de TRs (Termos de Referência)
        {'name': 'criar_tr', 'description': 'Criar Termos de Referência'},
        {'name': 'editar_tr', 'description': 'Editar Termos de Referência'},
        {'name': 'aprovar_tr', 'description': 'Aprovar Termos de Referência'},
        {'name': 'visualizar_tr', 'description': 'Visualizar Termos de Referência'},
        
        # Relatórios e Análises
        {'name': 'visualizar_relatorios', 'description': 'Visualizar relatórios do sistema'},
        {'name': 'exportar_relatorios', 'description': 'Exportar relatórios em diversos formatos'},
        {'name': 'analise_tecnica', 'description': 'Realizar análises técnicas avançadas'},
        {'name': 'ia_integrada', 'description': 'Utilizar funcionalidades de IA integrada'},
        
        # Administração do Sistema
        {'name': 'gerenciar_sistema', 'description': 'Gerenciar configurações do sistema'},
        {'name': 'configurar_sistema', 'description': 'Configurar parâmetros do sistema'},
        {'name': 'visualizar_auditoria', 'description': 'Visualizar logs de auditoria'},
        {'name': 'gerenciar_roles', 'description': 'Gerenciar roles e permissões'},
    ]
    
    created_permissions = []
    for perm_data in permissions_data:
        # Verificar se permissão já existe
        existing = Permission.query.filter_by(name=perm_data['name']).first()
        if not existing:
            permission = Permission(
                name=perm_data['name'],
                description=perm_data['description'],
                active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(permission)
            created_permissions.append(perm_data['name'])
    
    return created_permissions

def create_roles():
    """Cria os roles padrão do sistema"""
    roles_data = [
        {
            'name': 'admin',
            'description': 'Administrador do sistema com acesso total',
            'permissions': [
                'criar_usuario', 'editar_usuario', 'excluir_usuario', 'listar_usuarios', 'resetar_senha',
                'criar_processo', 'editar_processo', 'excluir_processo', 'aprovar_processo', 'visualizar_processo',
                'criar_proposta', 'editar_proposta', 'excluir_proposta', 'avaliar_proposta', 'visualizar_proposta',
                'criar_tr', 'editar_tr', 'aprovar_tr', 'visualizar_tr',
                'visualizar_relatorios', 'exportar_relatorios', 'analise_tecnica', 'ia_integrada',
                'gerenciar_sistema', 'configurar_sistema', 'visualizar_auditoria', 'gerenciar_roles'
            ]
        },
        {
            'name': 'comprador',
            'description': 'Comprador responsável por processos licitatórios',
            'permissions': [
                'criar_processo', 'editar_processo', 'aprovar_processo', 'visualizar_processo',
                'avaliar_proposta', 'visualizar_proposta',
                'aprovar_tr', 'visualizar_tr',
                'visualizar_relatorios', 'exportar_relatorios', 'analise_tecnica', 'ia_integrada'
            ]
        },
        {
            'name': 'requisitante',
            'description': 'Requisitante responsável por criar TRs e acompanhar processos',
            'permissions': [
                'criar_tr', 'editar_tr', 'visualizar_tr',
                'visualizar_processo', 'visualizar_proposta',
                'visualizar_relatorios', 'analise_tecnica'
            ]
        },
        {
            'name': 'fornecedor',
            'description': 'Fornecedor que participa de processos licitatórios',
            'permissions': [
                'criar_proposta', 'editar_proposta', 'visualizar_proposta',
                'visualizar_processo', 'visualizar_tr'
            ]
        }
    ]
    
    created_roles = []
    for role_data in roles_data:
        # Verificar se role já existe
        existing = Role.query.filter_by(name=role_data['name']).first()
        if not existing:
            role = Role(
                name=role_data['name'],
                description=role_data['description'],
                active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(role)
            db.session.flush()  # Para obter o ID do role
            
            # Adicionar permissões ao role
            for perm_name in role_data['permissions']:
                permission = Permission.query.filter_by(name=perm_name).first()
                if permission:
                    role.add_permission(permission)
            
            created_roles.append(role_data['name'])
    
    return created_roles

def create_admin_user():
    """Cria o usuário administrador padrão"""
    admin_email = 'admin@sistema.com'
    admin_password = 'Admin@123'
    
    # Verificar se usuário admin já existe
    existing_admin = Usuario.query.filter_by(email=admin_email).first()
    if existing_admin:
        print(f"⚠️ Usuário admin já existe: {admin_email}")
        return False
    
    # Criar usuário admin
    admin_user = Usuario(
        nome='Administrador do Sistema',
        email=admin_email,
        tipo='admin',
        nivel_acesso=1,
        ativo=True,
        bloqueado=False,
        tentativas_login=0,
        data_criacao=datetime.utcnow(),
        senha_criada_em=datetime.utcnow(),
        senha_expira_em=datetime.utcnow() + timedelta(days=90),
        historico_senhas='[]'
    )
    
    # Definir senha
    admin_user.set_senha(admin_password)
    
    # Adicionar role admin
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role:
        admin_user.add_role(admin_role)
    
    db.session.add(admin_user)
    
    print(f"✅ Usuário admin criado: {admin_email}")
    print(f"🔑 Senha padrão: {admin_password}")
    print("⚠️ ALTERE A SENHA IMEDIATAMENTE APÓS O PRIMEIRO LOGIN!")
    
    return True

def validate_migration():
    """Valida se a migração foi executada corretamente"""
    print("\n🔍 Validando migração...")
    
    # Verificar tabelas
    try:
        user_count = Usuario.query.count()
        role_count = Role.query.count()
        permission_count = Permission.query.count()
        
        print(f"📊 Usuários criados: {user_count}")
        print(f"📊 Roles criados: {role_count}")
        print(f"📊 Permissões criadas: {permission_count}")
        
        # Verificar usuário admin
        admin = Usuario.query.filter_by(email='admin@sistema.com').first()
        if admin:
            print(f"✅ Usuário admin encontrado: {admin.nome}")
            print(f"✅ Roles do admin: {[role.name for role in admin.roles]}")
            print(f"✅ Permissões do admin: {len(admin.get_permissions())}")
        else:
            print("❌ Usuário admin não encontrado!")
            return False
        
        # Verificar se admin pode fazer login
        if admin.verificar_senha('Admin@123'):
            print("✅ Senha do admin está correta")
        else:
            print("❌ Senha do admin está incorreta!")
            return False
        
        print("✅ Migração validada com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        return False

def main():
    """Função principal de migração"""
    print("🚀 Iniciando Migração RBAC - Sistema de Propostas")
    print("=" * 60)
    
    # Confirmar execução
    response = input("Deseja continuar com a migração? (s/N): ").lower().strip()
    if response != 's':
        print("❌ Migração cancelada pelo usuário.")
        return
    
    # Criar aplicação Flask
    app = create_app()
    
    with app.app_context():
        try:
            # Fazer backup
            backup_file = backup_database()
            
            # Criar todas as tabelas
            print("\n📋 Criando estrutura do banco de dados...")
            db.create_all()
            print("✅ Tabelas criadas com sucesso!")
            
            # Criar permissões
            print("\n🔐 Criando permissões...")
            created_permissions = create_permissions()
            print(f"✅ {len(created_permissions)} permissões criadas")
            
            # Criar roles
            print("\n👥 Criando roles...")
            created_roles = create_roles()
            print(f"✅ {len(created_roles)} roles criados")
            
            # Criar usuário admin
            print("\n👤 Criando usuário administrador...")
            admin_created = create_admin_user()
            
            # Commit das alterações
            db.session.commit()
            print("\n💾 Alterações salvas no banco de dados!")
            
            # Validar migração
            if validate_migration():
                print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
                print("\n📋 Próximos passos:")
                print("1. Acesse o portal: https://portal-proposta.onrender.com/")
                print("2. Faça login com: admin@sistema.com / Admin@123")
                print("3. ALTERE A SENHA IMEDIATAMENTE!")
                print("4. Crie usuários para outros módulos")
                print("5. Configure permissões conforme necessário")
                
                if backup_file:
                    print(f"\n💾 Backup disponível em: {backup_file}")
            else:
                print("\n❌ MIGRAÇÃO FALHOU NA VALIDAÇÃO!")
                return
                
        except Exception as e:
            print(f"\n❌ Erro durante a migração: {e}")
            db.session.rollback()
            print("🔄 Rollback executado")
            
            if backup_file:
                print(f"💾 Restaure o backup se necessário: {backup_file}")
            return

if __name__ == "__main__":
    main()

