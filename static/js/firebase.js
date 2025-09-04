// /static/js/firebase.js — Firebase centralizado com configuração padronizada

import { firebaseConfig, FIREBASE_MODULES } from './firebase-config.js';
import { initializeApp, getApps, getApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import {
  getFirestore,
  doc,
  getDoc,
  setDoc,
  onSnapshot
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// ✅ Usar configuração centralizada
export { firebaseConfig };

// ✅ Inicializa UMA ÚNICA instância com proteção contra duplicação
export const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

// Log de inicialização (apenas em desenvolvimento)
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    console.log('🔥 Firebase inicializado:', {
        projectId: firebaseConfig.projectId,
        apps: getApps().length,
        authReady: !!auth,
        dbReady: !!db
    });
}

// Re-exporta utilitários que o resto do app usa
export { onAuthStateChanged, signInWithEmailAndPassword, signOut, doc, getDoc, setDoc, onSnapshot };
