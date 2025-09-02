const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();

// Middlewares essenciais
app.use(cors());
app.use(express.json());

// Importação das rotas
const trRoutes = require('./routes/trRoutes');

// Rota de "saúde" da API
app.get('/api', (req, res) => {
  res.status(200).json({ message: 'API PropostaFlow está no ar!' });
});

// Rotas principais da aplicação
app.use('/api/trs', trRoutes);
// Futuramente: app.use('/api/processos', processoRoutes);

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`🚀 Servidor rodando na porta ${PORT}`);
});
