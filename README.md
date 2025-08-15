# Sistema de Gestão de Propostas - Versão com Administração

## 🚀 Novidades da Versão Atualizada

### ✅ **FUNCIONALIDADES IMPLEMENTADAS:**
- **Sistema de Administração Completo**: Gestão segura de usuários
- **Interface Discreta**: Ícone de administração no canto superior direito
- **Autenticação Robusta**: JWT com persistência no servidor
- **Banco de Dados Permanente**: SQLite com dados que não se perdem
- **Zero Conflitos**: Sistema original 100% preservado

### 🔐 **CREDENCIAIS DE ADMINISTRADOR:**
- **Email**: `admin@sistema.com`
- **Senha**: `admin123`

## 📁 Estrutura de Arquivos

### **Arquivos Principais:**
- `backend_render_fix.py` - Servidor Flask principal (ATUALIZADO)
- `admin_routes.py` - Módulo de administração (NOVO)
- `requirements.txt` - Dependências Python
- `database.db` - Banco de dados SQLite

### **Frontend:**
- `static/index.html` - Página principal (ATUALIZADA com ícone admin)
- `static/admin-users.html` - Página de gerenciamento de usuários (NOVA)
- `static/js/auth.js` - Sistema de autenticação (PRESERVADO)
- Demais arquivos HTML/JS/CSS (PRESERVADOS)

### **Configuração:**
- `config.py` - Configurações do sistema
- `models.py` - Modelos do banco de dados
- `auth.py` - Sistema de autenticação JWT

## 🛠️ Instalação e Deploy

### **1. Preparação Local:**
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar sistema
python backend_render_fix.py
```

### **2. Deploy no Render:**
1. Faça upload de todos os arquivos para seu repositório GitHub
2. No Render, conecte ao repositório
3. Configure as variáveis de ambiente:
   - `SECRET_KEY`: Chave secreta para JWT
   - `DATABASE_URL`: URL do banco (opcional, usa SQLite por padrão)

### **3. Configuração do Banco:**
- O sistema cria automaticamente o banco SQLite
- Usuário admin é criado na primeira execução
- Dados persistem entre deployments no Render

## 🎯 Como Usar o Sistema de Administração

### **1. Acessar Administração:**
1. Abra a página principal do sistema
2. Clique no ícone de engrenagem (⚙️) no canto superior direito
3. Faça login com as credenciais de administrador

### **2. Gerenciar Usuários:**
1. No painel admin, clique em "Gerenciar Usuários"
2. Funcionalidades disponíveis:
   - ➕ **Criar usuário**: Nome, email, senha e perfil
   - ✏️ **Editar usuário**: Alterar dados e perfil
   - 🗑️ **Excluir usuário**: Remover usuários do sistema
   - 🔍 **Buscar usuário**: Filtrar por nome, email ou perfil

### **3. Perfis Disponíveis:**
- **Admin**: Acesso total ao sistema
- **Comprador**: Gestão de processos licitatórios
- **Requisitante**: Criação de TRs e pareceres
- **Fornecedor**: Participação em licitações

## 🔒 Segurança e Persistência

### **Dados Seguros:**
- Senhas criptografadas com bcrypt
- Tokens JWT com expiração configurável
- Logs de auditoria para todas as ações

### **Persistência no Render:**
- Banco SQLite em volume persistente
- Dados não se perdem em atualizações
- Backup automático recomendado

## 🛡️ Compatibilidade

### **Sistema Original Preservado:**
- ✅ Todos os módulos funcionam normalmente
- ✅ Dashboards de Requisitante, Comprador e Fornecedor intactos
- ✅ APIs existentes mantidas
- ✅ Sistema de autenticação original como fallback

### **Melhorias Implementadas:**
- ✅ Administração centralizada de usuários
- ✅ Interface moderna e responsiva
- ✅ Autenticação mais robusta
- ✅ Logs de auditoria expandidos

## 🆘 Suporte e Troubleshooting

### **Problemas Comuns:**

**1. Erro de conexão com banco:**
- Verificar se `database.db` tem permissões corretas
- Recriar banco: deletar `database.db` e reiniciar servidor

**2. Login admin não funciona:**
- Verificar credenciais: `admin@sistema.com` / `admin123`
- Verificar se servidor está rodando na porta correta

**3. Ícone de admin não aparece:**
- Limpar cache do navegador
- Verificar se `static/index.html` foi atualizado

### **Logs e Debug:**
- Logs do servidor mostram todas as operações
- Console do navegador mostra erros JavaScript
- Verificar rede/conectividade se APIs não respondem

## 📊 Estatísticas do Sistema

O painel de administração mostra:
- Total de usuários por perfil
- Quantidade de TRs por status
- Número de processos ativos
- Logs de atividade recente

## 🔄 Atualizações Futuras

Para manter o sistema atualizado:
1. Fazer backup do banco `database.db`
2. Atualizar arquivos do código
3. Reiniciar servidor
4. Dados de usuários são preservados

---

## 📞 Contato

Para dúvidas ou suporte técnico, consulte a documentação completa ou entre em contato com o desenvolvedor.

**Versão**: 2.0 com Sistema de Administração  
**Data**: Agosto 2025  
**Compatibilidade**: Render.com, Heroku, VPS

