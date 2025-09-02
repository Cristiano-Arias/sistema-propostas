# Concorrência MVP (Requisitante • Comprador • Fornecedor)

MVP com **3 módulos**, **login/JWT**, e **tempo real** via **Socket.IO** para eventos de processo (TR submetido, convite enviado, proposta recebida etc.). **Pronto para Deploy no Render** via `render.yaml` e Gunicorn com **eventlet**.

## Como rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_DEBUG=1
python app.py
# abra http://localhost:5000/static/index.html
```

## Deploy no Render (GitHub)

1. Faça fork ou suba este repo no seu GitHub.
2. No Render, crie **Blueprint** (IaC) com este repositório. O arquivo `render.yaml` já configura o serviço web.
3. Configure as variáveis de ambiente **SECRET_KEY**, **JWT_SECRET_KEY** e **DATABASE_URL** (Postgres do Render).
4. Deploy. O **startCommand** usa `gunicorn` com **eventlet** para suportar **WebSocket/Socket.IO**.

> **Fontes oficiais:** Render Blueprints (`render.yaml`) e suporte a WebSockets; Flask‑SocketIO + Gunicorn com eventlet. Veja “Referências” abaixo.

## Endpoints principais (resumo)

- **Auth**
  - `POST /api/auth/register` — `{ email, full_name, password, role, organization? }`
  - `POST /api/auth/login` — retorna `{ access_token }`
  - `GET /api/auth/me` — dados do usuário (JWT)

- **Comprador**
  - `POST /api/procurements` — cria processo
  - `POST /api/procurements/{id}/invites` — cria convite de fornecedor

- **Requisitante**
  - `POST /api/procurements/{id}/tr` — cria/edita TR e **baseline da Tabela de Serviço**
  - `POST /api/tr/{tr_id}/submit` — submete TR

- **Fornecedor**
  - `PUT /api/proposals/{proc_id}/service-qty` — define **quantidades** por item do TR (somente isto pode mudar)
  - `PUT /api/proposals/{proc_id}/prices` — define **preço unitário** por item
  - `GET /api/proposals/{proc_id}/commercial-items` — consolida itens (qty × preço)

### Regra de negócio “Tabela de Serviço”
Nos templates de proposta **somente a quantidade** pode mudar. O design do banco garante isso via chaves estrangeiras e tabelas `proposal_service` (qty) e `proposal_prices` (unit_price). As colunas imutáveis (código/descrição/unidade) vêm da baseline do TR por *JOIN*.

## Tempo real

O cliente (página em `/static/index.html`) conecta a Socket.IO e entra na sala do processo com:
```js
socket.emit("join_procurement", { procurement_id: 1 });
```
O servidor emite eventos como `tr.submitted`, `invite.sent`, `proposal.tech.received`, etc., todos enviados à sala `proc:{id}`.

## Segurança (MVP)
- Autenticação via **JWT**; *roles* `REQUISITANTE`, `COMPRADOR`, `FORNECEDOR` em cada rota.
- Hash de senha com **bcrypt** (passlib).
- **CORS** aberto no MVP; restrinja em produção.

> Para alta disponibilidade/escala horizontal com múltiplos workers/instâncias, configure um *message queue* (ex.: Redis) para o Flask‑SocketIO e ajuste o `startCommand`. No MVP usamos 1 worker (`-w 1`).

## Estrutura

```
app/
  __init__.py      # Flask app, DB, JWT, SocketIO
  config.py        # Configurações (SECRET_KEY, DATABASE_URL etc.)
  models.py        # Tabelas (Users, Procurements, TR, Service Items, Proposals, etc.)
  blueprints/
    auth.py
    procurements.py
    tr.py
    proposals.py
static/
  index.html
  js/app.js
render.yaml
requirements.txt
app.py             # entrypoint; socketio.run para dev; Gunicorn em prod
```

## Referências (oficiais/confiáveis)
- **Flask‑SocketIO — Deploy com Gunicorn (eventlet/gevent).** https://flask-socketio.readthedocs.io/en/latest/deployment.html
- **Flask‑SocketIO — API (emit/join rooms/async modes).** https://flask-socketio.readthedocs.io/en/latest/api.html
- **Flask — Deploy com eventlet (recomendação de usar Gunicorn com eventlet).** https://flask.palletsprojects.com/en/stable/deploying/eventlet/
- **Render — Blueprints (`render.yaml`).** https://render.com/docs/blueprint-spec
- **Render — Web Services (binding de porta, boas práticas).** https://render.com/docs/web-services
- **Render — Uptime/Long‑lived connections (retry para WebSockets).** https://render.com/docs/uptime-best-practices
- **Render — WebSockets (comparativo oficial).** https://render.com/docs/render-vs-vercel-comparison
- **Flask‑JWT‑Extended — docs.** https://flask-jwt-extended.readthedocs.io/
- **Flask‑CORS — docs.** https://flask-cors.readthedocs.io/en/latest/
- **Passlib (bcrypt).** https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html
- **SQLAlchemy ORM — docs.** https://docs.sqlalchemy.org/orm/
```

