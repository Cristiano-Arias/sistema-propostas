from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime

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

# --- Modelos de Dados (Define a estrutura dos nossos dados) ---
class TR_Base(BaseModel):
    titulo: str
    objetivo: Optional[str] = None
    status: Optional[str] = 'rascunho'

class TR(TR_Base):
    id: int
    criadoEm: datetime.datetime
    atualizadoEm: Optional[datetime.datetime] = None

# --- Banco de Dados em Memória (Temporário) ---
db_trs = {
    1: TR(id=1, titulo="Desenvolvimento de novo App Mobile", status="rascunho", criadoEm=datetime.datetime.now()),
    2: TR(id=2, titulo="Reforma do Escritório Central", status="enviado", criadoEm=datetime.datetime.now())
}
next_id = 3

# --- Rotas da API ---

@app.get("/api", tags=["Status"])
def read_root():
    """Verifica se a API está no ar."""
    return {"message": "API PropostaFlow em Python está no ar!"}

# CREATE - Criar um novo TR
@app.post("/api/trs", response_model=TR, status_code=status.HTTP_201_CREATED, tags=["Termos de Referência"])
def create_tr(tr_in: TR_Base):
    """Cria um novo Termo de Referência."""
    global next_id
    novo_tr = TR(id=next_id, criadoEm=datetime.datetime.now(), **tr_in.dict())
    db_trs[next_id] = novo_tr
    next_id += 1
    return novo_tr

# READ - Obter todos os TRs
@app.get("/api/trs", response_model=List[TR], tags=["Termos de Referência"])
def get_all_trs():
    """Retorna uma lista de todos os Termos de Referência."""
    return list(db_trs.values())

# READ - Obter um TR por ID
@app.get("/api/trs/{tr_id}", response_model=TR, tags=["Termos de Referência"])
def get_tr_by_id(tr_id: int):
    """Obtém um Termo de Referência específico pelo seu ID."""
    if tr_id not in db_trs:
        raise HTTPException(status_code=404, detail="TR não encontrado.")
    return db_trs[tr_id]

# UPDATE - Atualizar um TR
@app.put("/api/trs/{tr_id}", response_model=TR, tags=["Termos de Referência"])
def update_tr(tr_id: int, tr_update: TR_Base):
    """Atualiza um Termo de Referência existente."""
    if tr_id not in db_trs:
        raise HTTPException(status_code=404, detail="TR não encontrado.")
    
    tr_db = db_trs[tr_id]
    update_data = tr_update.dict(exclude_unset=True)
    updated_tr = tr_db.copy(update=update_data)
    updated_tr.atualizadoEm = datetime.datetime.now()
    db_trs[tr_id] = updated_tr
    return updated_tr

# DELETE - Apagar um TR
@app.delete("/api/trs/{tr_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Termos de Referência"])
def delete_tr(tr_id: int):
    """Deleta um Termo de Referência."""
    if tr_id not in db_trs:
        raise HTTPException(status_code=404, detail="TR não encontrado.")
    del db_trs[tr_id]
    return
