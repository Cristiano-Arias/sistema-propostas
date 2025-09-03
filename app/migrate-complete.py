#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migração do banco de dados para o novo fluxo
Execute este script para atualizar o banco de dados existente

Uso: python migrate_database.py
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
import sys
import os

# Configurar o Flask app
app = Flask(__name__)

# Detectar o tipo de banco baseado na configuração
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Render Postgres
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://")
else:
    # SQLite local
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///concorrencia.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def migrate_database():
    """Executa as migrações necessárias"""
    
    with app.app_context():
        try:
            print("=" * 60)
            print("INICIANDO MIGRAÇÃO DO BANCO DE DADOS")
            print("=" * 60)
            
            # 1. Adicionar campo requisitante_id na tabela procurements
            print("\n1. Adicionando campo requisitante_id...")
            try:
                db.session.execute(text("""
                    ALTER TABLE procurements 
                    ADD COLUMN requisitante_id INTEGER REFERENCES users(id)
                """))
                db.session.commit()
                print("   ✓ Campo requisitante_id adicionado com sucesso")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("   ✓ Campo requisitante_id já existe")
                    db.session.rollback()
                else:
                    print(f"   ⚠️  Erro ao adicionar campo: {e}")
                    db.session.rollback()
            
            # 2. Adicionar campo rejection_reason no TR
            print("\n2. Adicionando campo rejection_reason no TR...")
            try:
                db.session.execute(text("""
                    ALTER TABLE tr_terms 
                    ADD COLUMN rejection_reason TEXT
                """))
                db.session.commit()
                print("   ✓ Campo rejection_reason adicionado com sucesso")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("   ✓ Campo rejection_reason já existe")
                    db.session.rollback()
                else:
                    print(f"   ⚠️  Erro ao adicionar campo: {e}")
                    db.session.rollback()
            
            # 3. Atualizar status dos processos existentes
            print("\n3. Atualizando status dos processos...")
            
            # Mapear status antigos para novos
            result = db.session.execute(text("""
                UPDATE procurements 
                SET status = CASE
                    WHEN status = 'RASCUNHO' THEN 'TR_PENDENTE'
                    WHEN status = 'DRAFT' THEN 'TR_PENDENTE'
                    WHEN status = 'OPEN' THEN 'ABERTO'
                    ELSE status
                END
                WHERE status IN ('RASCUNHO', 'DRAFT', 'OPEN')
            """))
            db.session.commit()
            print(f"   ✓ {result.rowcount} processos atualizados")
            
            # 4. Atribuir requisitante aos processos existentes
            print("\n4. Atribuindo requisitantes aos processos...")
            
            # Primeiro, verificar se existem requisitantes
            req_check = db.session.execute(text(
                "SELECT COUNT(*) as count FROM users WHERE role = 'REQUISITANTE'"
            )).fetchone()
            
            if req_check and req_check[0] > 0:
                # Tentar atribuir o criador se ele for requisitante
                result = db.session.execute(text("""
                    UPDATE procurements 
                    SET requisitante_id = created_by
                    WHERE requisitante_id IS NULL
                    AND created_by IN (SELECT id FROM users WHERE role = 'REQUISITANTE')
                """))
                db.session.commit()
                print(f"   ✓ {result.rowcount} processos atribuídos ao requisitante criador")
                
                # Para processos sem requisitante, atribuir o primeiro requisitante disponível
                result = db.session.execute(text("""
                    UPDATE procurements 
                    SET requisitante_id = (
                        SELECT id FROM users 
                        WHERE role = 'REQUISITANTE' 
                        ORDER BY id 
                        LIMIT 1
                    )
                    WHERE requisitante_id IS NULL
                """))
                db.session.commit()
                print(f"   ✓ {result.rowcount} processos atribuídos a requisitante padrão")
            else:
                print("   ⚠️  Nenhum requisitante encontrado no banco")
            
            # 5. Sincronizar status do processo com status do TR
            print("\n5. Sincronizando status de processos com TRs...")
            
            # Para SQLite
            if "sqlite" in app.config['SQLALCHEMY_DATABASE_URI'].lower():
                # SQLite não suporta UPDATE FROM, então fazemos diferente
                trs = db.session.execute(text(
                    "SELECT procurement_id, status FROM tr_terms"
                )).fetchall()
                
                for tr in trs:
                    proc_id, tr_status = tr
                    new_status = None
                    
                    if tr_status == 'RASCUNHO':
                        new_status = 'TR_CRIADO'
                    elif tr_status == 'SUBMETIDO':
                        new_status = 'TR_SUBMETIDO'
                    elif tr_status == 'APROVADO':
                        new_status = 'TR_APROVADO'
                    elif tr_status == 'REJEITADO':
                        new_status = 'TR_REJEITADO'
                    
                    if new_status:
                        db.session.execute(text("""
                            UPDATE procurements 
                            SET status = :status
                            WHERE id = :proc_id
                        """), {"status": new_status, "proc_id": proc_id})
                
                db.session.commit()
                print("   ✓ Status sincronizados (SQLite)")
            else:
                # PostgreSQL suporta UPDATE FROM
                db.session.execute(text("""
                    UPDATE procurements 
                    SET status = CASE
                        WHEN tr.status = 'RASCUNHO' THEN 'TR_CRIADO'
                        WHEN tr.status = 'SUBMETIDO' THEN 'TR_SUBMETIDO'
                        WHEN tr.status = 'APROVADO' THEN 'TR_APROVADO'
                        WHEN tr.status = 'REJEITADO' THEN 'TR_REJEITADO'
                        ELSE procurements.status
                    END
                    FROM tr_terms AS tr
                    WHERE procurements.id = tr.procurement_id
                """))
                db.session.commit()
                print("   ✓ Status sincronizados (PostgreSQL)")
            
            # 6. Verificar integridade dos dados
            print("\n6. Verificando integridade dos dados...")
            
            # Contar registros
            proc_count = db.session.execute(text("SELECT COUNT(*) FROM procurements")).scalar()
            tr_count = db.session.execute(text("SELECT COUNT(*) FROM tr_terms")).scalar()
            user_count = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            
            print(f"   - Processos: {proc_count}")
            print(f"   - TRs: {tr_count}")
            print(f"   - Usuários: {user_count}")
            
            # Verificar requisitantes
            req_count = db.session.execute(text(
                "SELECT COUNT(*) FROM users WHERE role = 'REQUISITANTE'"
            )).scalar()
            comp_count = db.session.execute(text(
                "SELECT COUNT(*) FROM users WHERE role = 'COMPRADOR'"
            )).scalar()
            forn_count = db.session.execute(text(
                "SELECT COUNT(*) FROM users WHERE role = 'FORNECEDOR'"
            )).scalar()
            
            print(f"   - Requisitantes: {req_count}")
            print(f"   - Compradores: {comp_count}")
            print(f"   - Fornecedores: {forn_count}")
            
            # Verificar processos sem requisitante
            proc_sem_req = db.session.execute(text(
                "SELECT COUNT(*) FROM procurements WHERE requisitante_id IS NULL"
            )).scalar()
            
            if proc_sem_req > 0:
                print(f"\n   ⚠️  ATENÇÃO: {proc_sem_req} processos sem requisitante atribuído!")
                print("      Você pode atribuir manualmente ou criar um requisitante.")
            
            # 7. Criar usuários de teste se não existirem
            if user_count == 0:
                print("\n7. Criando usuários de teste...")
                create_test_users()
            else:
                print("\n7. Usuários já existem, pulando criação de usuários de teste")
            
            print("\n" + "=" * 60)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Erro durante migração: {e}")
            db.session.rollback()
            sys.exit(1)


def create_test_users():
    """Cria usuários de teste para o sistema"""
    from werkzeug.security import generate_password_hash
    
    try:
        # Criar organização de teste
        org_exists = db.session.execute(text(
            "SELECT COUNT(*) FROM organizations WHERE name = 'Empresa Teste'"
        )).scalar()
        
        if org_exists == 0:
            db.session.execute(text("""
                INSERT INTO organizations (name, cnpj, address, phone)
                VALUES ('Empresa Teste', '00.000.000/0001-00', 'Rua Teste, 123', '(11) 1234-5678')
            """))
            db.session.commit()
        
        org_id = db.session.execute(text(
            "SELECT id FROM organizations WHERE name = 'Empresa Teste'"
        )).scalar()
        
        # Senha padrão para todos
        password = generate_password_hash('123456')
        
        # Criar usuários de teste
        users = [
            ('requisitante@teste.com', 'Requisitante Teste', 'REQUISITANTE', None),
            ('comprador@teste.com', 'Comprador Teste', 'COMPRADOR', None),
            ('fornecedor@teste.com', 'Fornecedor Teste', 'FORNECEDOR', org_id),
        ]
        
        for email, name, role, user_org_id in users:
            # Verificar se usuário já existe
            exists = db.session.execute(text(
                "SELECT COUNT(*) FROM users WHERE email = :email"
            ), {"email": email}).scalar()
            
            if exists == 0:
                db.session.execute(text("""
                    INSERT INTO users (email, password_hash, full_name, role, org_id, is_active, created_at)
                    VALUES (:email, :password, :name, :role, :org_id, 1, :now)
                """), {
                    'email': email,
                    'password': password,
                    'name': name,
                    'role': role,
                    'org_id': user_org_id,
                    'now': datetime.utcnow()
                })
                print(f"   ✓ Usuário criado: {email} (senha: 123456)")
            else:
                print(f"   - Usuário já existe: {email}")
        
        db.session.commit()
        print("\n   ✅ Usuários de teste prontos!")
        
    except Exception as e:
        print(f"   ❌ Erro ao criar usuários: {e}")
        db.session.rollback()


if __name__ == "__main__":
    print("\n🚀 Iniciando migração do banco de dados...")
    print(f"📁 Banco de dados: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("-" * 60)
    
    confirm = input("\n⚠️  Este script irá modificar o banco de dados.\n   Deseja continuar? (s/n): ")
    
    if confirm.lower() in ['s', 'sim', 'yes', 'y']:
        migrate_database()
    else:
        print("\n❌ Migração cancelada pelo usuário")
        sys.exit(0)