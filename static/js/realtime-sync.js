// ================================
// realtime-sync.js (Option B - baseado no original do usuário)
// Sincroniza chaves de localStorage com Firestore em /localstorage/{key}
// Requer usuário autenticado (mesmo login entre módulos).
// ================================

import { doc, getDoc, setDoc, onSnapshot } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";

// ⚠️ Usa a MESMA config já presente nas páginas do sistema.
// Caso a página já tenha inicializado o app, o Firebase reutiliza a instância automaticamente.
const firebaseConfig = {
  apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.firebasestorage.app",
  messagingSenderId: "321036073908",
  appId: "1:321036073908:web:3149b9ea2cb77a704890e1"
};

let app;
try { app = initializeApp(firebaseConfig); } catch(_) { /* já inicializado */ }
const db = getFirestore();
const auth = getAuth();

// Chaves sincronizadas (compatível com módulos existentes)
const KEYS = [
  "admin_logado","auth_token","azure_ai_config","comprador_logado","convites_processo",
  "credenciais_fornecedores","fornecedor_logado","fornecedor_token","fornecedores_cadastrados",
  "notificacoes_requisitante","pareceres_requisitante","pareceres_tecnicos","processos","processos_compra",
  "propostas_comparativo","propostas_fornecedor","propostas_fornecedor_","propostas_fornecedores",
  "propostas_liberadas_parecer","propostas_para_requisitante","requisitante_logado","sistema_analises_ia",
  "sistema_fornecedores","sistema_processos","sistema_propostas","sistema_propostas_completas","sistema_trs",
  "sistema_usuarios_fornecedores","technical_analysis_draft","technical_analysis_final","termos_referencia",
  "tr_autosave","tr_rascunho","tr_rascunho_","trs_aprovados","trs_pendentes_aprovacao","userData","userToken","usuario_logado"
];

let unsubscribers = [];
let isApplyingRemote = false;

function attachListeners() {
  detachListeners();
  for (const key of KEYS) {
    const ref = doc(db, "localstorage", key);

    // Seed inicial (não bloqueia UI)
    getDoc(ref).then((snap) => {
      if (snap.exists()) {
        const { value } = snap.data() || {};
        if (typeof value !== "undefined") {
          try { isApplyingRemote = True; } catch(_) {}
          try { localStorage.setItem(key, value); } finally { isApplyingRemote = false; }
        }
      }
    }).catch((e) => console.warn("[realtime-sync] seed erro:", key, e.code || e.message));

    const unsub = onSnapshot(ref, (snap) => {
      if (!snap.exists()) return;
      const { value } = snap.data() || {};
      try { isApplyingRemote = true; localStorage.setItem(key, value); } finally { isApplyingRemote = false; }
    }, (err) => {
      console.warn("[realtime-sync] onSnapshot erro:", key, err.code || err.message);
    });

    unsubscribers.push(unsub);
  }
}

function detachListeners() {
  for (const u of unsubscribers) { try { u(); } catch(_) {} }
  unsubscribers = [];
}

// Monkey-patch: enviar para Firestore só autenticado
const _setItem = localStorage.setItem.bind(localStorage);
localStorage.setItem = function(k, v) {
  const res = _setItem(k, v);
  const user = auth.currentUser;
  if (!isApplyingRemote && user && KEYS.includes(k)) {
    const ref = doc(db, "localstorage", k);
    setDoc(ref, { value: v, updatedAt: new Date().toISOString(), uid: user.uid }, { merge: true })
      .catch((e) => console.warn("[realtime-sync] setDoc erro:", k, e.code || e.message));
  }
  return res;
};

onAuthStateChanged(auth, (user) => {
  if (user) {
    console.log("[realtime-sync] autenticado:", user.uid);
    attachListeners();
  } else {
    console.log("[realtime-sync] sem login — desligando listeners");
    detachListeners();
  }
});

console.log("[realtime-sync] aguardando onAuthStateChanged…");
