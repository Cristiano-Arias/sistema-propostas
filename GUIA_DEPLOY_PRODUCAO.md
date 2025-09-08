# 🚀 Guia Completo - Deploy em Produção no Render

## 📋 Pré-requisitos

### 1. Contas Necessárias
- ✅ Conta no GitHub (para hospedar o código)
- ✅ Conta no Render (https://render.com) - **GRATUITA**
- ✅ Projeto Firebase configurado
- ✅ Conta Azure OpenAI (opcional)

### 2. Arquivos Preparados
- ✅ `backend_render_fix.py` - Backend Flask
- ✅ `requirements.txt` - Dependências Python
- ✅ `render.yaml` - Configuração Render
- ✅ `static/` - Todos os arquivos frontend
- ✅ `credentials.json` - Service Account Firebase

## 🔧 Passo 1: Preparar Repositório GitHub

### 1.1 Criar Repositório
```bash
# No seu computador
cd "c:\Users\c.arias\Downloads\03.09.25 sistema completo TRAE"
git init
git add .
git commit -m "Initial commit - Portal Propostas"

# Criar repositório no GitHub e conectar
git remote add origin https://github.com/SEU_USUARIO/portal-propostas.git
git branch -M main
git push -u origin main
```

### 1.2 Estrutura Final do Repositório
```
portal-propostas/
├── backend_render_fix.py      # ✅ Backend Flask
├── requirements.txt           # ✅ Dependências
├── render.yaml               # ✅ Config Render
├── credentials.json          # ⚠️ NÃO COMMITAR
├── static/                   # ✅ Frontend
│   ├── dashboard-fornecedor-funcional.html
│   ├── dashboard-comprador-funcional.html
│   ├── dashboard-requisitante-funcional.html
│   └── js/                   # ✅ Módulos JS
└── infra/                    # ✅ Configs produção
```

## 🔐 Passo 2: Configurar Firebase

### 2.1 Service Account (Obrigatório)
1. Acesse [Firebase Console](https://console.firebase.google.com)
2. Selecione seu projeto: **portal-de-proposta**
3. Vá em **Configurações** → **Contas de serviço**
4. Clique **Gerar nova chave privada**
5. Baixe o arquivo JSON

### 2.2 Preparar Credenciais para Render
```json
{
  "type": "service_account",
  "project_id": "portal-de-proposta",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-...@portal-de-proposta.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

## 🌐 Passo 3: Deploy no Render

### 3.1 Criar Web Service
1. Acesse [Render Dashboard](https://dashboard.render.com)
2. Clique **New** → **Web Service**
3. Conecte seu repositório GitHub
4. Configure:
   - **Name**: `portal-propostas`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn backend_render_fix:app`

### 3.2 Configurar Variáveis de Ambiente

#### Obrigatórias (Firebase)
```
FIREBASE_CREDENTIALS
```
**Valor**: Cole todo o conteúdo JSON do service account (uma linha só)

#### Opcionais (Azure OpenAI)
```
AZURE_OPENAI_ENDPOINT=https://portalcompras.openai.azure.com
AZURE_OPENAI_KEY=6Z0VYdgofYJMu32yWoaJfQtuocrVPKFi0sZhnBge7hluMgJXDVvuJQQJ99BHACYeBjFXJ3w3AAABACOGvaka
AZURE_OPENAI_DEPLOYMENT=gpt-35-turbo
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

#### Configurações Adicionais
```
PYTHON_VERSION=3.11.9
FLASK_ENV=production
CORS_ALLOWED_ORIGINS=https://seu-app.onrender.com
```

### 3.3 Deploy Automático
- ✅ Render fará deploy automático
- ✅ Cada push no GitHub = novo deploy
- ✅ SSL/HTTPS automático
- ✅ URL: `https://portal-propostas.onrender.com`

## 🧪 Passo 4: Testar em Produção

### 4.1 URLs de Teste
```
# Backend API
https://portal-propostas.onrender.com/api/status

# Dashboards
https://portal-propostas.onrender.com/static/dashboard-fornecedor-funcional.html
https://portal-propostas.onrender.com/static/dashboard-comprador-funcional.html
https://portal-propostas.onrender.com/static/dashboard-requisitante-funcional.html
```

### 4.2 Checklist de Funcionamento
- [ ] ✅ API Status responde
- [ ] ✅ Firebase conectado
- [ ] ✅ Dashboards carregam sem erro
- [ ] ✅ Login funciona
- [ ] ✅ Firestore lê/escreve dados
- [ ] ✅ Azure OpenAI responde (se configurado)

## 🔧 Passo 5: Configurações Finais

### 5.1 Domínio Personalizado (Opcional)
1. No Render: **Settings** → **Custom Domains**
2. Adicione seu domínio
3. Configure DNS conforme instruções

### 5.2 Monitoramento
- ✅ Logs automáticos no Render
- ✅ Métricas de performance
- ✅ Alertas de erro

## 🚨 Troubleshooting

### Erro: "Firebase not initialized"
**Solução**: Verificar variável `FIREBASE_CREDENTIALS`
```bash
# No Render, verificar se a variável está definida
echo $FIREBASE_CREDENTIALS
```

### Erro: "Module not found"
**Solução**: Verificar `requirements.txt`
```txt
Flask==2.3.3
Flask-CORS==4.0.0
firebase-admin==6.2.0
gunicorn==21.2.0
```

### Erro: "CORS blocked"
**Solução**: Configurar `CORS_ALLOWED_ORIGINS`
```
CORS_ALLOWED_ORIGINS=https://seu-dominio.com,https://portal-propostas.onrender.com
```

## 📊 Monitoramento e Manutenção

### Logs em Tempo Real
```bash
# Via Render CLI (opcional)
npm install -g @render/cli
render login
render logs -s portal-propostas
```

### Backup Automático
- ✅ Firestore: Backup automático do Google
- ✅ Código: Versionado no GitHub
- ✅ Configurações: Documentadas neste guia

## 🎯 Próximos Passos

1. **Deploy Inicial**: Seguir passos 1-4
2. **Testes**: Validar todas as funcionalidades
3. **Usuários**: Criar contas de teste
4. **Produção**: Liberar para usuários finais
5. **Monitoramento**: Acompanhar métricas

---

## 📞 Suporte

### Documentação Oficial
- [Render Docs](https://render.com/docs)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Flask Deployment](https://flask.palletsprojects.com/en/2.3.x/deploying/)

### Comandos Úteis
```bash
# Verificar status do deploy
curl https://portal-propostas.onrender.com/api/status

# Testar Firebase
curl -X POST https://portal-propostas.onrender.com/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"token":"SEU_ID_TOKEN"}'
```

**🚀 Pronto para produção!** 🎉