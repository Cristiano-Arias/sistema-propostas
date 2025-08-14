# Sistema de Gestão de Propostas - v5.0

Sistema completo e integrado para gestão de propostas licitatórias com fluxo completo entre Requisitante, Comprador e Fornecedor.

## 🚀 Novidades da Versão 5.0

### ✅ Funcionalidades Implementadas

1. **Integração Completa entre Módulos**
   - TRs criados pelo Requisitante chegam automaticamente ao Comprador
   - Comprador pode aprovar/reprovar TRs com parecer
   - Processos criados são visíveis aos Fornecedores convidados
   - Sistema de notificações em tempo real

2. **Persistência de Dados**
   - Backend com banco de dados SQLite
   - APIs REST completas para todos os módulos
   - Mantém compatibilidade com LocalStorage como fallback

3. **Segurança**
   - Autenticação JWT implementada
   - Senhas com hash bcrypt
   - Controle de acesso por perfil
   - Validações no backend

4. **Novas Funcionalidades**
   - Download de TRs em PDF
   - Workflow de aprovação de TRs
   - Seleção e convite de fornecedores
   - Upload de documentos
   - Dashboard com dados reais

## 📁 Estrutura de Arquivos

```
sistema-propostas/
├── backend.py              # Backend Flask completo
├── requirements.txt        # Dependências Python
├── static/
│   ├── index.html         # Página inicial (login)
│   ├── dashboard-requisitante.html
│   ├── dashboard-comprador.html
│   ├── dashboard-fornecedor.html
│   ├── criar-tr.html
│   ├── criar-processo.html
│   ├── selecionar-fornecedores.html
│   ├── enviar-proposta.html
│   ├── analise-propostas.html
│   └── js/
│       ├── api-client.js      # Cliente API
│       ├── auth.js           # Sistema de autenticação
│       ├── integration.js    # Scripts de integração
│       └── (arquivos JS originais mantidos)
└── uploads/               # Diretório para arquivos enviados
```

## 🔧 Instalação e Deploy

### Deploy no Render

1. **Preparar o repositório GitHub:**
   ```bash
   # Adicionar todos os arquivos
   git add .
   
   # Commit com as mudanças
   git commit -m "Versão 5.0 - Sistema totalmente integrado"
   
   # Push para o GitHub
   git push origin main
   ```

2. **Configurar no Render:**
   - O Render detectará automaticamente as mudanças
   - O deploy será feito automaticamente
   - Aguarde 2-3 minutos para o sistema ficar online

### Instalação Local (para testes)

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Executar o sistema:**
   ```bash
   python backend.py
   ```

3. **Acessar no navegador:**
   ```
   http://localhost:5000
   ```

## 👥 Usuários de Teste

O sistema cria automaticamente alguns usuários para teste:

### Requisitante
- Email: requisitante@empresa.com
- Senha: req123
- Perfil: requisitante

### Comprador
- Email: comprador@empresa.com
- Senha: comp123
- Perfil: comprador

### Fornecedor
- Email: fornecedor@empresa.com
- Senha: forn123
- Perfil: fornecedor

## 📋 Fluxo do Sistema

1. **Requisitante:**
   - Login → Dashboard → Criar TR
   - TR é enviado automaticamente para aprovação

2. **Comprador:**
   - Login → Dashboard → Ver TRs pendentes
   - Aprovar/Reprovar TR com parecer
   - Se aprovado → Criar Processo
   - Sel