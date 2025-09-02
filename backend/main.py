from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import datetime
import os

# Inicializa a aplicação FastAPI
app = FastAPI(
    title="PropostaFlow API",
    description="API para o Sistema de Gestão de Propostas",
    version="1.0.0"
)

# Configura o CORS para permitir acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja para a URL do seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos de Dados ---
class TR_Base(BaseModel):
    titulo: str
    objetivo: Optional[str] = None
    status: Optional[str] = 'rascunho'

class TR(TR_Base):
    id: int
    criado_em: datetime.datetime

# Lista temporária (banco em memória)
db_tr = []

# --- Rotas da API ---
@app.post("/api/tr", response_model=TR, status_code=status.HTTP_201_CREATED)
def criar_tr(tr: TR_Base):
    novo_tr = TR(
        id=len(db_tr) + 1,
        titulo=tr.titulo,
        objetivo=tr.objetivo,
        status=tr.status,
        criado_em=datetime.datetime.utcnow()
    )
    db_tr.append(novo_tr)
    return novo_tr

@app.get("/api/tr", response_model=List[TR])
def listar_tr():
    return db_tr

@app.get("/api/tr/{tr_id}", response_model=TR)
def obter_tr(tr_id: int):
    for tr in db_tr:
        if tr.id == tr_id:
            return tr
    raise HTTPException(status_code=404, detail="TR não encontrada")

# --- Servindo o frontend compilado ---
static_path = os.path.join(os.path.dirname(__file__), "../frontend/dist")

if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")
