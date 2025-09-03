# fix_db.py
import os
from sqlalchemy import create_engine, text

# Usa a mesma URL do seu app
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

# Conecta
engine = create_engine(DATABASE_URL)

# Executa o comando
with engine.connect() as conn:
    try:
        conn.execute(text("""
            ALTER TABLE procurements 
            ADD COLUMN requisitante_id INTEGER REFERENCES users(id)
        """))
        conn.commit()
        print("✅ Coluna adicionada!")
    except Exception as e:
        if "already exists" in str(e):
            print("✅ Coluna já existe!")
        else:
            print(f"❌ Erro: {e}")
