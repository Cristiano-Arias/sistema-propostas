// static/js/auth-facade.js
import { auth, signInWithEmailAndPassword } from './firebase.js';

export async function loginComPerfil(email, senha, perfil) {
    try {
        const cred = await signInWithEmailAndPassword(auth, email, senha);
        
        // NÃO usar localStorage - apenas retornar o usuário
        // O perfil será gerenciado pelo backend via token
        
        console.log(`Login realizado: ${email}, perfil: ${perfil}`);
        return cred.user;
    } catch (error) {
        console.error('Erro no login:', error);
        throw error;
    }
}

export function getCurrentUser() {
    return auth.currentUser;
}

export async function logout() {
    try {
        await auth.signOut();
        console.log('Logout realizado');
    } catch (error) {
        console.error('Erro no logout:', error);
    }
}
