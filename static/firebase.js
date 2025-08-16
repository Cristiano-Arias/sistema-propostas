// static/firebase.js  (JS puro, sem <script> dentro)

// SDKs via CDN (modo simples p/ site estático)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth }       from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getFirestore }  from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// COLE AQUI o seu firebaseConfig exatamente como o console mostrou
const firebaseConfig = {
  // apiKey: "...",
  // authDomain: "...",
  // projectId: "...",
  // storageBucket: "...",
  // messagingSenderId: "...",
  // appId: "...",
  // measurementId: "..." // (se existir)
};

const app  = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db   = getFirestore(app);

// expõe para outros scripts
window.__firebase = { app, auth, db };
