# Deploy em Produção — Portal Propostas

## O que foi feito
- Removido **bypass/simulações** no frontend (localStorage, loadSampleData, BYPASS).
- Adicionado **auth real** (Firebase ID Token) + **RBAC por claims/perfil** no backend.
- Criadas **regras** do Firestore/Storage e **índices**.
- Endpoint para **publicar apenas a proposta técnica** ao Requisitante.
- Proxy seguro para **Azure OpenAI** no backend (chave não fica mais no cliente).
- Padrão de **Realtime** via Firestore (use `onSnapshot` no front).
- `infra/` com tudo que precisa para produção (rules, indexes, render, requirements, Postman).

## Passos
1. **Firebase**
   - Crie/Selecione um projeto. Habilite **Auth (Email/Senha)** e **Firestore**.
   - Faça deploy de `infra/firestore.rules` e `infra/firestore.indexes.json`.
   - Aplique `infra/storage.rules` para o Cloud Storage.
2. **Claims (RBAC)**
   - Ao criar usuários (ex.: fornecedores), setar custom claims `role`: `ADMIN|COMPRADOR|REQUISITANTE|FORNECEDOR`.
3. **Render (produção)**
   - Adicione Secrets: `FIREBASE_CREDENTIALS` (JSON) ou `FIREBASE_CREDENTIALS_FILE` (secret file).
   - Adicione: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_KEY`.
   - Use `infra/render.prod.yaml` como referência (ou Blueprint).
4. **Frontend**
   - Use `static/js/auth-guard.js` e `static/js/api-client.js`.
   - Removido `js/azure-config.js` (backup `.REMOVIDO_BACKUP`). Rotacione a chave no Azure.

## Teste rápido (Postman)
Importe `infra/postman_portal_propostas.json`, cole o ID Token do Firebase em `{idToken}` e teste as rotas.

## Observações
- O Admin SDK ignora Rules; por isso há validações no servidor além das rules.
- Consulte as docs linkadas para detalhes.
