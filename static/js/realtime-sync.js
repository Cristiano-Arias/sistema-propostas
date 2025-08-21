// ================================
// realtime-sync.js (patched)
// ================================

import { getFirestore, doc, getDoc, setDoc, onSnapshot } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { app } from "/static/firebase.js";

const db = getFirestore(app);
const auth = getAuth(app);

let unsubscribes = [];

/**
 * Atacha listeners Firestore -> localStorage
 */
function attachListeners() {
  const keys = ["requisicoes", "compras", "fornecedores", "sistema_dados"];
  keys.forEach(key => {
    const ref = doc(db, "localstorage", key);
    const unsub = onSnapshot(
      ref,
      snap => {
        if (snap.exists()) {
          localStorage.setItem(key, snap.data().value);
          console.log(`📥 Sync Firestore -> localStorage [${key}]`);
        }
      },
      err => {
        console.error("❌ Firestore listener error:", err);
      }
    );
    unsubscribes.push(unsub);
  });
}

/**
 * Remove listeners ativos
 */
function detachListeners() {
  unsubscribes.forEach(u => u());
  unsubscribes = [];
}

// ================================
// Aguardar login antes de ligar sync
// ================================
onAuthStateChanged(auth, async user => {
  if (user) {
    console.log("✅ Usuário autenticado, iniciando sync...");
    attachListeners();
    // Seed inicial
    for (const key of ["requisicoes", "compras", "fornecedores", "sistema_dados"]) {
      const ref = doc(db, "localstorage", key);
      const snap = await getDoc(ref);
      if (snap.exists()) {
        localStorage.setItem(key, snap.data().value);
      }
    }
  } else {
    console.log("ℹ️ Usuário deslogado, removendo listeners...");
    detachListeners();
  }
});

// ================================
// Monkey-patch localStorage.setItem
// ================================
const originalSetItem = localStorage.setItem;
localStorage.setItem = function (key, value) {
  originalSetItem.apply(this, [key, value]);
  const user = auth.currentUser;
  if (user) {
    const ref = doc(db, "localstorage", key);
    setDoc(ref, { value: value }, { merge: true })
      .then(() => console.log(`📤 Sync localStorage -> Firestore [${key}]`))
      .catch(err => console.error("❌ Firestore write error:", err));
  }
};
