import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js';
import { getAuth, onAuthStateChanged, signOut, signInWithEmailAndPassword } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js';
import { ApiClient } from './api-client.js';

// Espera-se que exista um objeto global window.firebaseConfig definido no HTML
const app = initializeApp(window.firebaseConfig);
const auth = getAuth(app);
const api = new ApiClient();

export function setupAuthGuard() {
  onAuthStateChanged(auth, async (user) => {
    if (!user) { return; }
    await api.setUser(user);
    const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:5000' : '';
const v = await fetch(`${apiUrl}/auth/verify`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({token: await user.getIdToken()})}).then(r=>r.json());
    const perfil = (v && v.perfil || '').toLowerCase();
    const map = {
      admin: '/static/admin-usuarios.html',
      requisitante: '/static/dashboard-requisitante-funcional.html',
      comprador: '/static/dashboard-comprador-funcional.html',
      fornecedor: '/static/dashboard-fornecedor-funcional.html'
    };
    if (map[perfil] && location.pathname.indexOf(map[perfil]) === -1) {
      window.location.href = map[perfil];
    }
  });
}
export { auth, signOut, signInWithEmailAndPassword };
