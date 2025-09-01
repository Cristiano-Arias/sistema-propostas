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
  apiKey: "SUA_API_KEY",
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.appspot.com",
  messagingSenderId: "XXXXXXXXX",
  appId: "1:XXXXXXXX:web:XXXXXXX"
};

// Inicializar Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);

// Exportações comuns
export { signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, signOut, doc, getDoc, setDoc };
