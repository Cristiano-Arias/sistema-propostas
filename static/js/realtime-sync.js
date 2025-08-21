// ================================
// realtime-sync.js - Versão Corrigida
// Sincroniza chaves de localStorage com Firestore em /localstorage/{key}
// ================================

import { doc, getDoc, setDoc, onSnapshot } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";

// Configuração Firebase
const firebaseConfig = {
  apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.firebasestorage.app",
  messagingSenderId: "321036073908",
  appId: "1:321036073908:web:3149b9ea2cb77a704890e1"
};

let app;
try { 
  app = initializeApp(firebaseConfig); 
  console.log('✅ Firebase inicializado para realtime-sync');
} catch(e) { 
  console.log('⚠️ Firebase já estava inicializado');
}

const db = getFirestore();
const auth = getAuth();

// Chaves sincronizadas (compatível com módulos existentes)
const KEYS = [
  "admin_logado",
  "auth_token",
  "azure_ai_config",
  "comprador_logado",
  "convites_processo",
  "credenciais_fornecedores",
  "fornecedor_logado",
  "fornecedor_token",
  "fornecedores_cadastrados",
  "notificacoes_requisitante",
  "notificacoes_comprador",
  "pareceres_requisitante",
  "pareceres_tecnicos",
  "processos",
  "processos_compra",
  "propostas_comparativo",
  "propostas_fornecedor",
  "propostas_fornecedor_",
  "propostas_fornecedores",
  "propostas_liberadas_parecer",
  "propostas_para_requisitante",
  "requisitante_logado",
  "sistema_analises_ia",
  "sistema_fornecedores",
  "sistema_processos",
  "sistema_propostas",
  "sistema_propostas_completas",
  "sistema_trs",
  "sistema_usuarios_fornecedores",
  "sistema_usuario_logado",
  "sistema_estatisticas",
  "sistema_vinculacoes_fornecedores",
  "technical_analysis_draft",
  "technical_analysis_final",
  "termos_referencia",
  "tr_autosave",
  "tr_rascunho",
  "tr_rascunho_",
  "trs_aprovados",
  "trs_pendentes_aprovacao",
  "userData",
  "userToken",
  "usuario_logado"
];

let unsubscribers = [];
let isApplyingRemote = false;

function attachListeners() {
  detachListeners();
  
  for (const key of KEYS) {
    const ref = doc(db, "localstorage", key);

    // Buscar valor inicial do Firestore
    getDoc(ref).then((snap) => {
      if (snap.exists()) {
        const { value } = snap.data() || {};
        if (typeof value !== "undefined") {
          try { 
            isApplyingRemote = true; // CORRIGIDO: true com minúscula
            localStorage.setItem(key, value); 
            console.log(`📥 Carregado do Firebase: ${key}`);
          } finally { 
            isApplyingRemote = false; 
          }
        }
      }
    }).catch((e) => {
      console.warn("[realtime-sync] Erro ao buscar:", key, e.code || e.message);
    });

    // Listener em tempo real
    const unsub = onSnapshot(ref, (snap) => {
      if (!snap.exists()) return;
      
      const { value } = snap.data() || {};
      if (typeof value === "undefined") return;
      
      try { 
        isApplyingRemote = true; 
        localStorage.setItem(key, value); 
        console.log(`🔄 Atualizado do Firebase: ${key}`);
        
        // Disparar evento customizado para notificar a aplicação
        window.dispatchEvent(new CustomEvent('localStorage-sync', {
          detail: { key, value }
        }));
        
        // Atualizar UI específica se as funções estiverem disponíveis
        if (key === 'sistema_trs') {
          if (window.carregarMeusTRs) window.carregarMeusTRs();
          if (window.carregarEstatisticas) window.carregarEstatisticas();
        }
        
      } finally { 
        isApplyingRemote = false; 
      }
    }, (err) => {
      console.warn("[realtime-sync] Erro no listener:", key, err.code || err.message);
    });

    unsubscribers.push(unsub);
  }
  
  console.log(`✅ ${KEYS.length} listeners anexados`);
}

function detachListeners() {
  for (const u of unsubscribers) { 
    try { u(); } catch(_) {} 
  }
  unsubscribers = [];
  console.log("🔌 Listeners desconectados");
}

// Override do localStorage.setItem para sincronizar com Firebase
const _setItem = localStorage.setItem.bind(localStorage);
localStorage.setItem = function(k, v) {
  const res = _setItem(k, v);
  const user = auth.currentUser;
  
  // Só sincronizar se:
  // 1. Não for uma aplicação remota (evita loop)
  // 2. Usuário estiver autenticado
  // 3. A chave estiver na lista de sincronização
  if (!isApplyingRemote && user && KEYS.includes(k)) {
    const ref = doc(db, "localstorage", k);
    
    setDoc(ref, { 
      value: v, 
      updatedAt: new Date().toISOString(), 
      uid: user.uid,
      userEmail: user.email || 'unknown'
    }, { merge: true })
    .then(() => {
      console.log(`📤 Enviado para Firebase: ${k}`);
    })
    .catch((e) => {
      console.warn("[realtime-sync] Erro ao enviar:", k, e.code || e.message);
    });
  }
  
  return res;
};

// Override do localStorage.removeItem para sincronizar remoções
const _removeItem = localStorage.removeItem.bind(localStorage);
localStorage.removeItem = function(k) {
  const res = _removeItem(k);
  const user = auth.currentUser;
  
  if (!isApplyingRemote && user && KEYS.includes(k)) {
    const ref = doc(db, "localstorage", k);
    
    setDoc(ref, { 
      value: null, 
      updatedAt: new Date().toISOString(), 
      uid: user.uid,
      deleted: true
    }, { merge: true })
    .then(() => {
      console.log(`🗑️ Removido do Firebase: ${k}`);
    })
    .catch((e) => {
      console.warn("[realtime-sync] Erro ao remover:", k, e.code || e.message);
    });
  }
  
  return res;
};

// Monitorar autenticação
onAuthStateChanged(auth, (user) => {
  if (user) {
    console.log("[realtime-sync] ✅ Usuário autenticado:", user.email || user.uid);
    attachListeners();
    
    // Salvar informação do usuário no localStorage
    if (!isApplyingRemote) {
      localStorage.setItem('realtime_sync_user', JSON.stringify({
        uid: user.uid,
        email: user.email,
        displayName: user.displayName
      }));
    }
  } else {
    console.log("[realtime-sync] ⚠️ Sem autenticação - desligando sincronização");
    detachListeners();
    
    // Limpar informação do usuário
    if (!isApplyingRemote) {
      localStorage.removeItem('realtime_sync_user');
    }
  }
});

// Exportar funções úteis
window.realtimeSync = {
  isConnected: () => auth.currentUser !== null,
  getCurrentUser: () => auth.currentUser,
  forceSync: () => {
    if (auth.currentUser) {
      console.log("🔄 Forçando sincronização...");
      attachListeners();
    } else {
      console.warn("⚠️ Não é possível sincronizar sem autenticação");
    }
  },
  addKey: (key) => {
    if (!KEYS.includes(key)) {
      KEYS.push(key);
      console.log(`➕ Chave adicionada para sincronização: ${key}`);
      if (auth.currentUser) attachListeners();
    }
  },
  removeKey: (key) => {
    const index = KEYS.indexOf(key);
    if (index > -1) {
      KEYS.splice(index, 1);
      console.log(`➖ Chave removida da sincronização: ${key}`);
      if (auth.currentUser) attachListeners();
    }
  }
};

console.log("[realtime-sync] 🚀 Sistema de sincronização em tempo real inicializado");
console.log("[realtime-sync] 📋 Monitorando", KEYS.length, "chaves");
console.log("[realtime-sync] ⏳ Aguardando autenticação...");
