// /static/js/firebase.js — Web v9 modular (CDN) com proteção contra init duplicado

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

// Config do projeto (a mesma do Console)
export const firebaseConfig = {
  apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.firebasestorage.app",
  messagingSenderId: "321036073908",
  appId: "1:321036073908:web:3149b9ea2cb77a704890e1"
};

// ✅ Inicializa UMA ÚNICA instância
export const app  = getApps().length ? getApp() : initializeApp(firebaseConfig);  // evita app/duplicate-app
export const auth = getAuth(app);
export const db   = getFirestore(app);

// Re-exporta utilitários que o resto do app usa
export { onAuthStateChanged, signInWithEmailAndPassword, signOut, doc, getDoc, setDoc, onSnapshot };
