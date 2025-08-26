// static/js/auth-facade.js - Fachada simples para logins via Firebase
import { auth, signInWithEmailAndPassword } from './firebase.js';

export async function loginComPerfil(email, senha, perfil) {
  const cred = await signInWithEmailAndPassword(auth, email, senha);
  // Após login, persistimos perfil no localStorage (mantendo compatibilidade com o front atual)
  const lower = (perfil || '').toLowerCase();
  if (lower.includes('requisitante')) {
    localStorage.setItem('requisitante_logado', JSON.stringify({ email, uid: cred.user.uid, perfil: 'Requisitante' }));
  } else if (lower.includes('comprador')) {
    localStorage.setItem('comprador_logado', JSON.stringify({ email, uid: cred.user.uid, perfil: 'Comprador' }));
  } else if (lower.includes('fornecedor')) {
    localStorage.setItem('fornecedor_logado', JSON.stringify({ email, uid: cred.user.uid, perfil: 'Fornecedor' }));
  }
  return cred.user;
}
