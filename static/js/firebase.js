// /static/js/firebase.js - módulo unificado (v9 modular)

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// >>> CONFIG DO SEU PROJETO (a mesma que você já usa nos dashboards)
export const firebaseConfig = {
  apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.firebasestorage.app",
  messagingSenderId: "321036073908",
  appId: "1:321036073908:web:3149b9ea2cb77a704890e1"
};

// Inicializa uma ÚNICA instância e exporta tudo que o resto do app consome
export const app  = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db   = getFirestore(app);

// (Opcional) expor helpers de Auth/Firestore se precisar em outros arquivos
export { onAuthStateChanged, signInWithEmailAndPassword, signOut } 
  from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
export { doc, getDoc, setDoc, onSnapshot } 
  from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
