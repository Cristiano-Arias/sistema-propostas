// firebase.js - Configuração centralizada do Firebase
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { 
  getAuth, 
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signOut 
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { 
  getFirestore, 
  doc, 
  getDoc, 
  setDoc 
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// ⚠️ Substituir pelas suas credenciais
const firebaseConfig = {
    apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
    authDomain: "portal-de-proposta.firebaseapp.com",
    projectId: "portal-de-proposta",
    storageBucket: "portal-de-proposta.firebasestorage.app",
    messagingSenderId: "321036073908",
    appId: "1:321036073908:web:3149b9ea2cb77a704890e1",
    measurementId: "G-CFFVQGM3EC"
  };

// Inicializar Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

// Exportações comuns
export { signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, signOut, doc, getDoc, setDoc };
