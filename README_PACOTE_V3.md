# Pacote V3 — (v1 + Login Firebase unificado + Sincronização em tempo real)

## O que inclui
- **Tudo do Pacote Completo (v1)**: correções de imports e migração de dados p/ Fornecedor.
- **Login unificado Firebase** para Requisitante, Comprador e Fornecedor (via `static/js/firebase.js` + `static/js/auth-facade.js`).
- **Sincronização em tempo real** entre navegadores e máquinas: `static/js/realtime-sync.js` espelha chaves do `localStorage` no Firestore.

## Importante (compatível com o seu código real)
- Não alteramos a lógica de telas. O front continua usando `localStorage`. A sincronização garante que os dados apareçam em outras máquinas/abas quase em tempo real.
- Config Firebase usada foi a já presente no repositório (`auth-firebase.js`).

## Passos de Deploy
1) Substitua os arquivos pelos deste pacote.
2) Garanta que o **Firestore** está habilitado no projeto `portal-de-proposta` e com regras que permitam leitura/escrita autenticada.
3) No Render, não é necessário mudar `render.yaml` (usa `backend_render_fix:app`). Não precisa FIREBASE_ADMIN para o front.

## Observação
- Para performance/escala, a etapa futura ideal é migrar gradualmente as leituras do front para Firestore (sem ficar dependente do `localStorage`). Este pacote já te dá sincronização imediata mantendo seu fluxo atual.
