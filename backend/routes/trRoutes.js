const express = require('express');
const router = express.Router();

// Banco de dados em memória (temporário)
let db_trs = [
  { id: 1, titulo: "Desenvolvimento de novo App Mobile", status: "rascunho", criadoEm: new Date().toISOString() },
  { id: 2, titulo: "Reforma do Escritório Central", status: "enviado", criadoEm: new Date().toISOString() }
];
let nextId = 3;

// CREATE - Criar um novo TR
router.post('/', (req, res) => {
  if (!req.body.titulo) {
    return res.status(400).json({ message: "O título é obrigatório." });
  }
  const novoTR = {
    id: nextId++,
    status: 'rascunho',
    criadoEm: new Date().toISOString(),
    ...req.body
  };
  db_trs.push(novoTR);
  res.status(201).json(novoTR);
});

// READ - Obter todos os TRs
router.get('/', (req, res) => {
  res.status(200).json(db_trs);
});

// READ - Obter um TR por ID
router.get('/:id', (req, res) => {
  const tr = db_trs.find(t => t.id == req.params.id);
  if (tr) {
    res.status(200).json(tr);
  } else {
    res.status(404).json({ message: "TR não encontrado." });
  }
});

// UPDATE - Atualizar um TR
router.put('/:id', (req, res) => {
  const index = db_trs.findIndex(t => t.id == req.params.id);
  if (index !== -1) {
    db_trs[index] = { ...db_trs[index], ...req.body, atualizadoEm: new Date().toISOString() };
    res.status(200).json(db_trs[index]);
  } else {
    res.status(404).json({ message: "TR não encontrado." });
  }
});

// DELETE - Apagar um TR
router.delete('/:id', (req, res) => {
  const index = db_trs.findIndex(t => t.id == req.params.id);
  if (index !== -1) {
    db_trs.splice(index, 1);
    res.status(204).send();
  } else {
    res.status(404).json({ message: "TR não encontrado." });
  }
});

module.exports = router;
