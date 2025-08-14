ATUALIZAÇÃO COMPLETA (Login Unificado + Cadastro com CNPJ + Segurança)

1) Login unificado: static/login-unificado.html
2) Cadastro com CNPJ: static/admin-cadastro-usuarios.html (somente Comprador/Admin)
3) API: POST /api/usuarios com validação e unicidade de CNPJ/e-mail
4) Banco: db_migration_add_cnpj.sql adiciona coluna CNPJ (ajuste índice conforme SGBD)
5) auth.js: helper de redirecionamento por perfil
6) index.html: links apontam para o login unificado
