# Sistema Pro — Deploy no Render (Postgres Starter)

## Passos
1) Suba estes arquivos em um repositório (GitHub).
2) No Render: **New → Web Service** (conecte o repo). O `render.yaml`:
   - Cria **Render Postgres (Starter)** e injeta `DATABASE_URL`.
   - Gera `SECRET_KEY` e `JWT_SECRET_KEY`.
   - Usa `./start.sh` (roda as migrações automaticamente e inicia o gunicorn).
3) (Opcional) Para criar o primeiro ADMIN automaticamente:
   - Defina `FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_NAME`, `FIRST_ADMIN_PASSWORD` nas Env Vars do serviço **antes do primeiro acesso**.
   - Se o banco estiver vazio, o usuário é criado na primeira requisição.

## Endpoints principais
- `POST /api/auth/login` → cookies JWT (e aceita **Authorization: Bearer**)
- `POST /api/auth/logout`
- `GET  /api/auth/session`
- **Requisitante**
  - `POST /api/requisitante/tr` — cria TR com `items` (JSON) e `responsibility_matrix` (opcional; por padrão entra com itens fixos + 4 extras)
  - `GET  /api/requisitante/tr` — lista TRs do usuário
- **Comprador**
  - `POST /api/comprador/tr/{tr_id}/approve`
  - `POST /api/comprador/process` {tr_id}
  - `POST /api/comprador/process/{id}/invite-supplier` {email}
- **Fornecedor**
  - `POST /api/fornecedor/accept-process` {token}
  - `POST /api/fornecedor/proposal` {process_id, tech, commercial, total_price}
- **Análise**
  - `GET  /api/analysis/compare?process_id=...`
- **Arquivos**
  - `POST /api/files` (multipart) — arquivo salvo no Postgres (BYTEA)
  - `GET  /api/files/{id}`

## Segurança e Persistência (fontes)
- JWT em cookies HttpOnly + CSRF (e suporte a Bearer) — Flask-JWT-Extended: https://flask-jwt-extended.readthedocs.io/
- Senhas (Argon2id) — OWASP Password Storage: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- Boas práticas de API / compatibilidade — OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- Render: use Postgres; filesystem do serviço web é efêmero — https://render.com/docs e https://render.com/docs/databases
