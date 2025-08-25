const functions = require('firebase-functions');
const admin = require('firebase-admin');

admin.initializeApp();

// Trigger quando novo usuário é criado
exports.enviarEmailBoasVindas = functions.auth.user().onCreate(async (user) => {
    const email = user.email;
    const uid = user.uid;
    
    console.log('Novo fornecedor criado:', email);
    
    // Buscar dados do fornecedor no Firestore
    const fornecedorDoc = await admin.firestore()
        .collection('fornecedores')
        .doc(uid)
        .get();
    
    if (!fornecedorDoc.exists) {
        console.log('Dados do fornecedor não encontrados no Firestore');
        return null;
    }
    
    const fornecedorData = fornecedorDoc.data();
    
    // Por enquanto, apenas registrar no console
    // (O envio real de email requer configuração SMTP)
    console.log('Email seria enviado para:', email);
    console.log('Senha temporária:', fornecedorData.senhaTemporaria);
    
    // Registrar tentativa de envio
    await admin.firestore().collection('emails_log').add({
        para: email,
        tipo: 'boas_vindas',
        fornecedorId: uid,
        senhaTemporaria: fornecedorData.senhaTemporaria,
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
        status: 'pendente_configuracao_smtp'
    });
    
    return { success: true };
});