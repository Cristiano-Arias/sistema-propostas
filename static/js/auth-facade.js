// /static/js/auth-facade.js - VERSÃO CORRIGIDA
import { 
    auth, 
    db,
    signInWithEmailAndPassword,
    doc,
    getDoc,
    setDoc
} from './firebase.js';

// Mapeamento de perfis baseado nos usuários do seu Firebase
const PERFIS_FIXOS = {
    'c.arias@fraport-brasil.com': 'requisitante',
    'suprimentos@fraport-brasil.com': 'comprador', 
    'cristianoarlas@hotmail.com': 'fornecedor'
};

// Detectar perfil do usuário
async function detectarPerfilUsuario(email) {
    try {
        // Tentar buscar perfil no Firestore
        const userDoc = await getDoc(doc(db, 'usuarios', email));
        if (userDoc.exists() && userDoc.data().perfil) {
            return userDoc.data().perfil;
        }
        
        // Usar mapeamento fixo como fallback
        return PERFIS_FIXOS[email.toLowerCase()] || null;
    } catch (error) {
        console.warn('Erro ao buscar perfil no Firestore:', error);
        return PERFIS_FIXOS[email.toLowerCase()] || null;
    }
}

// Função de login com perfil
export async function loginComPerfil(email, senha, perfilManual = null) {
    try {
        // Autenticar no Firebase
        const userCredential = await signInWithEmailAndPassword(auth, email, senha);
        const user = userCredential.user;
        
        // Detectar perfil
        let perfil = perfilManual || await detectarPerfilUsuario(email);
        
        if (!perfil) {
            throw new Error('Perfil não identificado para este usuário');
        }
        
        // Normalizar nome do perfil
        const perfilNormalizado = perfil.toLowerCase();
        
        // Salvar dados do usuário
        const userData = {
            email: user.email,
            uid: user.uid,
            perfil: perfilNormalizado,
            timestamp: new Date().toISOString()
        };
        
        // Salvar no localStorage
        localStorage.setItem(`${perfilNormalizado}_logado`, JSON.stringify(userData));
        localStorage.setItem('currentUser', JSON.stringify(userData));
        
        // Atualizar Firestore
        await setDoc(doc(db, 'usuarios', email), {
            email: email,
            perfil: perfilNormalizado,
            ultimoLogin: new Date().toISOString(),
            uid: user.uid
        }, { merge: true });
        
        return { user, perfil: perfilNormalizado };
        
    } catch (error) {
        console.error('Erro no login:', error);
        throw error;
    }
}

// Mapear dashboards
export function obterDashboardPorPerfil(perfil) {
    const dashboards = {
        'admin': '/static/admin-usuarios.html',
        'requisitante': '/static/dashboard-requisitante-funcional.html',
        'comprador': '/static/dashboard-comprador-funcional.html',
        'fornecedor': '/static/dashboard-fornecedor-funcional.html'
    };
    
    return dashboards[perfil.toLowerCase()] || null;
}
