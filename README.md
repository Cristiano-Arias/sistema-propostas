# Sistema de Gestão de Propostas

Sistema integrado para gestão de processos licitatórios e propostas comerciais.

## 🚀 Estrutura Atualizada

### Dashboard Geral (Visão geral do sistema)

### 1. Requisitante
- 1.1 Dashboard Requisitante
- 1.2 Criar TR (emissão de Termo de Referência)
- 1.3 Meus TRs (visualizar TRs criados)
- 1.4 Emitir Parecer (parecer técnico sobre propostas)

### 2. Comprador
- 2.1 Dashboard Comprador
- 2.2 Processos (listar todos)
- 2.3 Cadastrar Processos
- 2.4 Propostas (análise comercial)
- 2.5 Relatórios

### 3. Fornecedor
- 3.1 Dashboard Fornecedor
- 3.2 Meu Cadastro
- 3.3 Processos Disponíveis
- 3.4 Minhas Propostas
- 3.5 Enviar Proposta

### 4. Usuários (Gerenciamento de usuários)

## 📁 Estrutura de Arquivos

```
/
├── static/                          # Arquivos frontend
│   ├── index.html                   # Página de login
│   ├── sistema-gestao-corrigido2.html # Sistema principal
│   ├── auth.js                      # Sistema de autenticação
│   ├── dashboard-fornecedor.html    # Portal do fornecedor
│   ├── dashboard-requisitante-seguro.html # Portal do requisitante
│   ├── dashboard-comprador.html     # Portal do comprador
│   ├── portal-propostas-novo.html   # Sistema de propostas
│   ├── modulo-relatorios.html       # Módulo de relatórios
│   ├── modulo-termo-referencia-seguro.html # Módulo de TR
│   ├── sistema-notificacoes.js      # Sistema de notificações
│   └── analise-tecnica-ia.js        # Análise técnica IA
├── backend_render_fix.py            # Servidor Flask
├── requirements.txt                 # Dependências Python
├── render.yaml                      # Configuração Render
└── README.md                        # Este arquivo
```

## 🔑 Credenciais de Teste

- **ADMIN:** admin@sistema.com / admin123
- **COMPRADOR:** joao.silva@empresa.com / comprador123
- **REQUISITANTE:** carlos.oliveira@requisitante.com / requisitante123
- **FORNECEDOR:** contato@alpha.com / fornecedor123
- **AUDITOR:** ana.auditora@sistema.com / auditor123

## 🛠️ Tecnologias

- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **Backend:** Python Flask
- **Banco de Dados:** SQLite (desenvolvimento) / PostgreSQL (produção)
- **Deploy:** Render.com

## 📦 Instalação Local

1. Clone o repositório
2. Instale as dependências: `pip install -r requirements.txt`
3. Execute o servidor: `python backend_render_fix.py`
4. Acesse: `http://localhost:5000`

## 🌐 Deploy

O sistema está configurado para deploy automático no Render.com através do arquivo `render.yaml`.

## 📝 Funcionalidades

- ✅ Sistema de autenticação multi-perfil
- ✅ Gestão de processos licitatórios
- ✅ Sistema de propostas comerciais
- ✅ Análise técnica e comercial
- ✅ Geração de relatórios
- ✅ Sistema de notificações
- ✅ Interface responsiva
- ✅ APIs REST completas

## 🔄 Última Atualização

Sistema atualizado com nova estrutura de navegação conforme especificação:
- Dashboard Geral → 1. Requisitante → 2. Comprador → 3. Fornecedor → 4. Usuários
- Todos os módulos numerados e organizados hierarquicamente
- Integração completa entre todos os componentes

