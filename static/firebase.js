// firebase_simplificado.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, signOut, sendPasswordResetEmail } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyCqF366Ft7RkzHYaZb77HboNO3BPbmCjT8",
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.appspot.com",
  messagingSenderId: "321036073908",
  appId: "1:321036073908:web:3149b9ea2cb77a704890e1"
};
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

let currentUser = null;
let userToken = null;

export async function login(email, password){
  try{
    const cred = await signInWithEmailAndPassword(auth, email, password);
    const token = await cred.user.getIdToken();
    const resp = await fetch('/auth/verify', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ token }) });
    if (!resp.ok){
      let msg = 'Erro na autenticação'; try{ const j = await resp.json(); if (j && j.erro) msg = j.erro }catch(_){}
      throw new Error(msg);
    }
    const userData = await resp.json();
    currentUser = userData; userToken = token;
    localStorage.setItem('userToken', token);
    localStorage.setItem('userData', JSON.stringify(userData));
    return { success:true, user:userData };
  }catch(err){
    console.error('Erro no login:', err);
    return { success:false, error: err.message };
  }
}

export async function logout(){
  try{ await signOut(auth); }catch(_){}
  currentUser = null; userToken = null;
  localStorage.removeItem('userToken'); localStorage.removeItem('userData');
  window.location.href = '/';
  return { success:true };
}

export async function register(email, password, nome){
  try{ await createUserWithEmailAndPassword(auth, email, password); return await login(email, password); }
  catch(err){ console.error('Erro no registro:', err); return { success:false, error: err.message } }
}

export async function resetPassword(email){
  try{ await sendPasswordResetEmail(auth, email); return { success:true } }
  catch(err){ console.error('Erro ao resetar senha:', err); return { success:false, error: err.message } }
}

export function isLoggedIn(){ return currentUser !== null && userToken !== null }
export function getCurrentUser(){ return currentUser }
export function getUserToken(){ return userToken }

function initAuth(){
  const t = localStorage.getItem('userToken'); const d = localStorage.getItem('userData');
  if (t && d){ try{ userToken = t; currentUser = JSON.parse(d) }catch(_){ localStorage.removeItem('userToken'); localStorage.removeItem('userData'); } }
  onAuthStateChanged(auth, async (user)=>{
    if (user && !currentUser){
      try{
        const token = await user.getIdToken();
        const r = await fetch('/auth/verify',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ token })});
        if (r.ok){ const ud = await r.json(); currentUser = ud; userToken = token; localStorage.setItem('userToken', token); localStorage.setItem('userData', JSON.stringify(ud)); }
      }catch(e){ console.error('Erro ao verificar usuário:', e) }
    } else if (!user && currentUser){
      currentUser = null; userToken = null; localStorage.removeItem('userToken'); localStorage.removeItem('userData');
    }
  });
}
document.addEventListener('DOMContentLoaded', initAuth);
