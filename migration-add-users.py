#!/usr/bin/env python3
"""
Script de Migração - Adicionar Usuários Reais ao Sistema
Execute este script para criar usuários iniciais no banco de dados
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Usuario, Fornecedor, db
from auth import AuthService

# Configuração do banco
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///sistema_propostas.db')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def criar_usuarios_producao():
    """Cria usuários de produção no sistema"""
    
    print("=== CRIANDO USUÁRIOS DE PRODUÇÃO ===\n")
    
    # Lista de usuários a serem criados
    usuarios_producao = [
        # Administradores
        {
            'nome': 'João Carlos Silva',
            'email': 'joao.silva@empresa.com',
            'cpf': '123.456.789-00',
            'perfil': 'admin_sistema',
            'departamento': 'Tecnologia da Informação',
            'cargo': 'Gerente de TI',
            'telefone': '(11) 98765-4321',
            'senha': 'JoaoAdmin@2025'
        },
        {
            'nome': 'Maria Helena Santos',
            'email': 'maria.santos@empresa.com',
            'cpf': '987.654.321-00',
            'perfil': 'admin_sistema',
            'departamento': 'Tecnologia da Informação',
            'cargo': 'Coordenadora de Sistemas',
            'telefone': '(11) 97654-3210',
            'senha': 'MariaAdmin@2025'
        },
        
        # Compradores
        {
            'nome': 'Pedro Augusto Oliveira',
            'email': 'pedro.oliveira@empresa.com',
            'cpf': '456.789.123-00',
            'perfil': 'comprador',
            'departamento': 'Compras e Licitações',
            'cargo': 'Analista de Compras Sr',
            'telefone': '(11) 96543-2109',
            'senha': 'PedroComp@2025'
        },
        {
            'nome': 'Ana Paula Ferreira',
            'email': 'ana.ferreira@empresa.com',
            'cpf': '789.123.456-00',
            'perfil': 'comprador',
            'departamento': 'Compras e Licitações',
            'cargo': 'Compradora',
            'telefone': '(11) 95432-1098',
            'senha': 'AnaComp@2025'
        },
        {
            'nome': 'Carlos Eduardo Lima',
            'email': 'carlos.lima@empresa.com',
            'cpf': '321.654.987-00',
            'perfil': 'comprador',
            'departamento': 'Compras e Licitações',
            'cargo': 'Supervisor de Compras',
            'telefone': '(11) 94321-0987',
            'senha': 'CarlosComp@2025'
        },
        
        # Requisitantes
        {
            'nome': 'Fernanda Costa Silva',
            'email': 'fernanda.costa@empresa.com',
            'cpf': '654.321.987-00',
            'perfil': 'requisitante',
            'departamento': 'Engenharia',
            'cargo': 'Engenheira Civil',
            'telefone': '(11) 93210-9876',
            'senha': 'FernandaReq@2025'
        },
        {
            'nome': 'Roberto Alves Pereira',
            'email': 'roberto.pereira@empresa.com',
            'cpf': '147.258.369-00',
            'perfil': 'requisitante',
            'departamento': 'Manutenção',
            'cargo': 'Coordenador de Manutenção',
            'telefone': '(11) 92109-8765',
            'senha': 'RobertoReq@2025'
        },
        {
            'nome': 'Juliana Martins Souza',
            'email': 'juliana.souza@empresa.com',
            'cpf': '258.369.147-00',
            'perfil': 'requisitante',
            'departamento': 'Tecnologia da Informação',
            'cargo': 'Analista de Infraestrutura',
            'telefone': '(11) 91098-7654',
            'senha': 'JulianaReq@2025'
        },
        {
            'nome': 'Marcos Antonio Rodrigues',
            'email': 'marcos.rodrigues@empresa.com',
            'cpf': '369.147.258-00',
            'perfil': 'requisitante',
            'departamento': 'Administrativo',
            'cargo': 'Supervisor Administrativo',
            'telefone': '(11) 90987-6543',
            'senha': 'MarcosReq@2025'
        },
        {
            'nome': 'Patricia Lima Santos',
            'email': 'patricia.santos@empresa.com',
            'cpf': '741.852.963-00',
            'perfil': 'requisitante',
            'departamento': 'Recursos Humanos',
            'cargo': 'Analista de RH',
            'telefone': '(11) 89876-5432',
            'senha': 'PatriciaReq@2025'
        }
    ]
    
    # Criar usuários
    usuarios_criados = 0
    for usuario_data in usuarios_producao:
        try:
            # Verificar se já existe
            usuario_existente = session.query(Usuario).filter_by(email=usuario_data['email']).first()
            if usuario_existente:
                print(f"⚠️  Usuário {usuario_data['email']} já existe - pulando")
                continue
            
            # Criar novo usuário
            usuario = Usuario(
                nome=usuario_data['nome'],
                email=usuario_data['email'],
                cpf=usuario_data['cpf'],
                perfil=usuario_data['perfil'],
                departamento=usuario_data['departamento'],
                cargo=usuario_data['cargo'],
                telefone=usuario_data['telefone'],
                ativo=True,
                primeiro_acesso=False  # Já com senha definitiva
            )
            usuario.set_senha(usuario_data['senha'])
            
            session.add(usuario)
            usuarios_criados += 1
            
            print(f"✅ Usuário criado: {usuario_data['nome']} ({usuario_data['email']})")
            print(f"   Perfil: {usuario_data['perfil']}")
            print(f"   Senha: {usuario_data['senha']}")
            print()
            
        except Exception as e:
            print(f"❌ Erro ao criar usuário {usuario_data['email']}: {e}")
    
    # Commit das alterações
    try:
        session.commit()
        print(f"\n✅ Total de usuários criados: {usuarios_criados}")
    except Exception as e:
        session.rollback()
        print(f"\n❌ Erro ao salvar no banco: {e}")

def criar_fornecedores_producao():
    """Cria fornecedores de exemplo no sistema"""
    
    print("\n=== CRIANDO FORNECEDORES DE EXEMPLO ===\n")
    
    fornecedores_exemplo = [
        {
            'razao_social': 'Construtora Moderna Ltda',
            'nome_fantasia': 'Construtora Moderna',
            'cnpj': '12.345.678/0001-90',
            'inscricao_estadual': '123.456.789.123',
            'inscricao_municipal': '1234567',
            'endereco': 'Av. das Construções',
            'numero': '1000',
            'complemento': 'Galpão 5',
            'bairro': 'Distrito Industrial',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'cep': '01234-567',
            'email': 'comercial@construtoramoderna.com',
            'telefone': '(11) 3456-7890',
            'celular': '(11) 98765-4321',
            'website': 'www.construtoramoderna.com',
            'responsavel_nome': 'José da Silva',
            'responsavel_cpf': '111.222.333-44',
            'responsavel_email': 'jose.silva@construtoramoderna.com',
            'responsavel_telefone': '(11) 98765-4321',
            'responsavel_tecnico': 'Eng. Carlos Alberto',
            'crea_cau': 'CREA-SP 123456',
            'senha': 'Construtora@2025',
            'aprovado': True,
            'certidoes_validas': True
        },
        {
            'razao_social': 'Tech Solutions Informática S.A.',
            'nome_fantasia': 'Tech Solutions',
            'cnpj': '98.765.432/0001-10',
            'inscricao_estadual': '987.654.321.098',
            'endereco': 'Rua da Tecnologia',
            'numero': '500',
            'bairro': 'Vila Tech',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'cep': '04567-890',
            'email': 'vendas@techsolutions.com.br',
            'telefone': '(11) 2345-6789',
            'celular': '(11) 97654-3210',
            'website': 'www.techsolutions.com.br',
            'responsavel_nome': 'Ana Maria Costa',
            'responsavel_cpf': '222.333.444-55',
            'responsavel_email': 'ana.costa@techsolutions.com.br',
            'responsavel_telefone': '(11) 97654-3210',
            'senha': 'TechSol@2025',
            'aprovado': True,
            'certidoes_validas': True
        },
        {
            'razao_social': 'Materiais de Construção ABC Ltda',
            'nome_fantasia': 'ABC Materiais',
            'cnpj': '45.678.901/0001-23',
            'endereco': 'Rua dos Materiais',
            'numero': '200',
            'bairro': 'Centro',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'cep': '01010-010',
            'email': 'contato@abcmateriais.com',
            'telefone': '(11) 3333-4444',
            'responsavel_nome': 'Paulo Roberto Almeida',
            'responsavel_cpf': '333.444.555-66',
            'senha': 'ABCMat@2025',
            'aprovado': False,  # Pendente de aprovação
            'certidoes_validas': False
        }
    ]
    
    fornecedores_criados = 0
    for forn_data in fornecedores_exemplo:
        try:
            # Verificar se já existe
            forn_