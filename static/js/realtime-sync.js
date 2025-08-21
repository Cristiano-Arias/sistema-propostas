// ================================
// realtime-sync.js (patched - imports corrigidos)
// ================================

import { app, db, auth } from "/static/js/firebase.js";
import { doc, getDoc, setDoc, onSnapshot } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

let unsubscribers = [];

// Chaves que o app sincroniza (mantidas)
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
          try { isApplyingRemote = true; localStorage.setItem(key, value); }
          finally { isApplyingRemote = false; }
        }
      }
    }).catch((e) => console.warn("[realtime-sync] seed erro:", key, e.code || e.message));

    const unsub = onSnapshot(ref, (snap) => {
      if (!snap.exists()) return;
      const { value } = snap.data() || {};
      try { isApplyingRemote = true; localStorage.setItem(key, value); }
      finally { isApplyingRemote = false; }
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
