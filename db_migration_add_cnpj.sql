-- Executar no seu banco (ajuste conforme SGBD)
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cnpj TEXT;
-- Em Postgres: CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_cnpj_unique ON usuarios(cnpj) WHERE cnpj IS NOT NULL;
-- Em MySQL: ALTER TABLE usuarios ADD COLUMN cnpj VARCHAR(32) UNIQUE NULL;
