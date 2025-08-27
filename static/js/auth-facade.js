/* /static/js/auth-facade.js — PRODUÇÃO */
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const app   = initializeApp(window.firebaseConfig);   // window.firebaseConfig deve estar no HTML
const auth  = getAuth(app);

async function verifyAndRedirect(user) {
  const idToken = await user.getIdToken();
  const resp = await fetch('/auth/verify', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ token: idToken })
  });
  const data   = await resp.json();
  const perfil = (data.perfil || '').toLowerCase();

  const map = {
    admin:        '/static/admin-usuarios.html',
    requisitante: '/static/dashboard-requisitante-funcional.html',
    comprador:    '/static/dashboard-comprador-funcional.html',
    fornecedor:   '/static/dashboard-fornecedor-funcional.html'
  };
  if (map[perfil]) window.location.href = map[perfil];
  else alert('Usuário sem perfil definido. Peça ao administrador para configurar.');
}

// Form padrão: <form id="formLogin"> com inputs de e-mail e senha
const form = document.querySelector('#formLogin') || document.forms[0];
const emailI = form?.querySelector('input[type="email"], #email');
const passI  = form?.querySelector('input[type="password"], #senha');

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const { user } = await signInWithEmailAndPassword(auth, emailI.value.trim(), passI.value);
    await verifyAndRedirect(user);
  } catch (err) {
    console.error(err);
    alert(err?.message || 'Falha no login');
  }
});

// Já logado? redireciona
onAuthStateChanged(auth, (user) => { if (user) verifyAndRedirect(user); });
