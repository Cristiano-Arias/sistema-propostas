// static/js/auth-facade.js - Fachada simples para logins via Firebase
import { auth, signInWithEmailAndPassword } from './firebase.js';

export async function loginComPerfil(email, senha, perfil) {
  const cred = await signInWithEmailAndPassword(auth, email, senha);
  // Após login, persistimos perfil no localStorage (mantendo compatibilidade com o front atual)
  const lower = (perfil || '').toLowerCase();
  if (lower.includes('requisitante')) {
    /* REMOVIDO PARA PRODUÇÃO */);
  } else if (lower.includes('comprador')) {
    /* REMOVIDO PARA PRODUÇÃO */);
  } else if (lower.includes('fornecedor')) {
    /* REMOVIDO PARA PRODUÇÃO */);
  }
  return cred.user;
}
