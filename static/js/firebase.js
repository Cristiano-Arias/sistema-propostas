// /static/js/firebase.js
import { initializeApp, getApps, getApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  setPersistence,
  browserSessionPersistence
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import {
  getFirestore,
  doc,
  getDoc,
  setDoc,
  onSnapshot
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// Config do projeto CORRIGIDA
export const firebaseConfig = {
  apiKey: "AIzaSyD_366FT6RkZhYqZb77HboN038P5mCjT8", // CORRIGIDO
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.firebasestorage.app",
  messagingSenderId: "321836873088", // CORRIGIDO
  appId: "1:321836873088:web:3149b9ea2cb77a704890e1" // CORRIGIDO
};

// Inicializa UMA ÚNICA instância
export const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

// Configurar persistência de sessão (sem localStorage)
setPersistence(auth, browserSessionPersistence);

// Re-exporta utilitários
export { onAuthStateChanged, signInWithEmailAndPassword, signOut, doc, getDoc, setDoc, onSnapshot };
