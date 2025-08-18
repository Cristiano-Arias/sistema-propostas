# PATCH MÍNIMO - Adicionar apenas a rota /auth/verify ao backend existente

# Adicione este código ao seu backend_render_fix.py atual:

@app.route('/auth/verify', methods=['POST'])
def verify_token():
    """Verifica token e retorna dados do usuário - BUSCA POR EMAIL"""
    if not db:
        return jsonify({'erro': 'Serviço indisponível'}), 503
    
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'erro': 'Token não fornecido'}), 400
        
        # Verificar token
        decoded = auth.verify_id_token(token)
        uid = decoded['uid']
        email = decoded.get('email')
        
        if not email:
            return jsonify({'erro': 'Email não encontrado no token'}), 400
        
        # BUSCAR POR EMAIL (não por UID)
        users = db.collection('Usuario').where('email', '==', email).get()
        
        if users and len(users) > 0:
            # Usuário encontrado - usar dados do Firestore
            user_data = users[0].to_dict()
            logger.info(f"✅ Usuário encontrado: {email}, perfil: {user_data.get('perfil')}")
        else:
            # Usuário não encontrado - criar novo com perfil requisitante
            logger.info(f"⚠️ Usuário não encontrado: {email}, criando novo...")
            user_data = {
                'email': email,
                'nome': decoded.get('name', email.split('@')[0] if email else 'Usuário'),
                'perfil': 'requisitante',
                'ativo': True,
                'criadoEm': firestore.SERVER_TIMESTAMP
            }
            # Criar com UID como ID do documento
            db.collection('Usuario').document(uid).set(user_data)
            user_data['novo_usuario'] = True
        
        return jsonify({
            'valid': True,
            'uid': uid,
            'email': email,
            'nome': user_data.get('nome'),
            'perfil': user_data.get('perfil'),
            'ativo': user_data.get('ativo', True),
            'novo_usuario': user_data.get('novo_usuario', False)
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na verificação: {e}")
        return jsonify({'erro': 'Erro interno'}), 500

# INSTRUÇÕES:
# 1. Copie esta função e cole no final do seu backend_render_fix.py
# 2. Certifique-se de que os imports estão corretos (auth, firestore, logger)
# 3. Faça deploy da alteração
# 4. Teste o login novamente

