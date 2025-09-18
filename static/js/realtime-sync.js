/*
 * realtime-sync.js - Versão Corrigida com Isolamento por Usuário
 * SEM MÓDULO ADMIN - Sincroniza chaves de localStorage com Firestore
 * Este cabeçalho usa comentários de bloco para evitar que
 * qualquer minificador trate barras iniciais como regex.
 */

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

// Chaves sincronizadas (compatível com módulos existentes - SEM ADMIN)
const KEYS = [
  // REMOVIDO: "admin_logado"
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
  "sistema_fornecedores",
  "sistema_processos",
  "sistema_propostas",
  "sistema_trs",
  "sistema_usuario_logado",
  "termos_referencia",
  "trs_aprovados",
  "trs_pendentes_aprovacao",
  "usuarios_fornecedores",
  "userToken",
  "userData"
];

let unsubscribers = [];
let isApplyingRemote = false;

function attachListeners() {
  detachListeners();
  
  const user = auth.currentUser;
  if (!user) {
    console.warn('[realtime-sync] Sem usuário autenticado');
    return;
  }
  
  for (const key of KEYS) {
    // Usar chave composta com UID do usuário + isolamento por perfil
    let docKey = `${key}_${user.uid}`;

// 🔧 COMPARTILHADO ENTRE REQUISITANTE E COMPRADOR:
// Estas chaves precisam ser vistas pelos dois perfis, portanto
// removemos o UID para sincronizar em um documento global.
if (key === 'propostas_para_requisitante' || key === 'pareceres_requisitante') {
    docKey = key; // documento global compartilhado
}

    
    // CORREÇÃO: Isolar TRs por perfil para evitar conflito entre módulos
    if (key === 'sistema_trs') {
        const userEmail = user.email || '';
        const perfil = userEmail.includes('suprimentos') ? 'comprador' : 'requisitante';
        docKey = `${key}_${perfil}_${user.uid}`;
    }
    
    const ref = doc(db, "localstorage", docKey);

    // Seed inicial
    getDoc(ref).then((snap) => {
      if (snap.exists()) {
        const data = snap.data() || {};
        // Para chaves globais (propostas_para_requisitante e pareceres_requisitante),
        // não restringir pelo UID: qualquer valor deve ser aplicado. Para outras
        // chaves, verificar se o documento pertence ao usuário atual.
        const isGlobalKey = (key === 'propostas_para_requisitante' || key === 'pareceres_requisitante');
        const apply = isGlobalKey ? (typeof data.value !== 'undefined') : (data.uid === user.uid && typeof data.value !== 'undefined');
        if (apply) {
          try { 
            isApplyingRemote = true; 
            localStorage.setItem(key, data.value); 
            console.log(`📥 Carregado do Firebase: ${key}`);
          } finally { 
            isApplyingRemote = false; 
          }
        }
      }
    }).catch((e) => {
      // Ignorar erros de permissão esperados
      if (e.code !== 'permission-denied') {
        console.warn("[realtime-sync] Erro ao carregar:", key, e.code || e.message);
      }
    });

    // Listener em tempo real
    const unsub = onSnapshot(ref, (snap) => {
      if (!snap.exists()) return;
      
      const data = snap.data() || {};
      // Determinar se a chave é global para não restringir pelo UID
      const isGlobalKey = (key === 'propostas_para_requisitante' || key === 'pareceres_requisitante');
      const apply = isGlobalKey ? (typeof data.value !== 'undefined') : (data.uid === user.uid && typeof data.value !== 'undefined');
      if (apply) {
        try { 
          isApplyingRemote = true; 
          let valueToStore = data.value;
          // Se estivermos sincronizando a chave de TRs, garantir normalização dos objetos
          if (key === 'sistema_trs') {
            try {
              const arr = JSON.parse(data.value) || [];
              if (Array.isArray(arr)) {
                valueToStore = JSON.stringify(arr.map(tr => ({
                  ...tr,
                  id: tr.id || tr.numeroTR,
                  numeroTR: tr.numeroTR || tr.id
                })));
              }
            } catch (e) {
              // se parse falhar, salva valor original sem alteração
            }
          }
          localStorage.setItem(key, valueToStore); 
          console.log(`🔄 Atualizado do Firebase: ${key}`);
          
          // Disparar evento customizado para notificar a aplicação
          window.dispatchEvent(new CustomEvent('localStorage-sync', {
            detail: { key, value: data.value }
          }));
          
          // Atualizar UI específica se as funções estiverem disponíveis
          if (key === 'sistema_trs') {
            // Para evitar sobrescrever atualizações locais com dados antigos,
            // fazemos um merge por updatedAt.  Se o remoto é mais antigo que
            // o local, mantemos o local; se é mais novo, aplicamos o remoto.
            try {
              const remoteArr = JSON.parse(data.value) || [];
              const localArr  = JSON.parse(localStorage.getItem(key) || '[]');
              // Indexar por id/numeroTR
              const byKey = (arr) => {
                const map = {};
                arr.forEach(tr => {
                  const k = tr.id || tr.numeroTR;
                  if (k) map[k] = tr;
                });
                return map;
              };
              const L = byKey(localArr);
              const R = byKey(remoteArr);
              const merged = [];
              const keysSet = new Set([...Object.keys(L), ...Object.keys(R)]);
              keysSet.forEach(k => {
                const l = L[k];
                const r = R[k];
                if (!l) return merged.push(r);
                if (!r) return merged.push(l);
                const lu = Number(l.updatedAt) || 0;
                const ru = Number(r.updatedAt) || 0;
                merged.push(ru > lu ? r : l);
              });
              valueToStore = JSON.stringify(merged);
            } catch (e) {
              // se der erro no merge, continua com valueToStore original
            }
            // Quando a lista de TRs muda, atualizar as listas e contadores
            if (window.carregarMeusTRs) window.carregarMeusTRs();
            if (window.carregarEstatisticas) window.carregarEstatisticas();
            if (window.carregarTRsPendentes) window.carregarTRsPendentes();
            if (window.carregarTRsAprovados) window.carregarTRsAprovados();
          }
          // Atualizar processos quando a coleção de processos muda
          if (key === 'sistema_processos') {
            if (window.carregarProcessos) window.carregarProcessos();
            if (window.carregarEstatisticas) window.carregarEstatisticas();
          }
          
        } finally { 
          isApplyingRemote = false; 
        }
      }
    }, (err) => {
      // Ignorar erros de permissão esperados
      if (err.code !== 'permission-denied') {
        console.warn("[realtime-sync] Erro no listener:", key, err.code || err.message);
      }
    });

    unsubscribers.push(unsub);
  }
  
  console.log(`✅ ${KEYS.length} listeners anexados para usuário ${user.email || user.uid}`);
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
    // Usar chave composta com UID do usuário
    const docKey = `${k}_${user.uid}`;
    const ref = doc(db, "localstorage", docKey);
    
    // Incluir UID no documento (OBRIGATÓRIO para as regras)
    // Normalizar dados de TRs antes de enviar ao Firebase e adicionar updatedAt.
    let valueToSave = v;
    if (k === 'sistema_trs') {
      try {
        const arr = JSON.parse(v);
        if (Array.isArray(arr)) {
          const now = Date.now();
          const normalized = arr.map(tr => {
            const id = tr.id || tr.numeroTR;
            const numeroTR = tr.numeroTR || tr.id;
            const updatedAt = tr.updatedAt ? Number(tr.updatedAt) : 0;
            return {
              ...tr,
              id: id,
              numeroTR: numeroTR,
              updatedAt: updatedAt || now
            };
          });
          valueToSave = JSON.stringify(normalized);
        }
      } catch (_) {
        // If parsing fails, leave valueToSave as original v
      }
    }
    setDoc(ref, { 
      value: valueToSave, 
      uid: user.uid,  // Campo obrigatório para as regras de segurança
      updatedAt: new Date().toISOString(),
      userEmail: user.email || 'unknown',
      key: k  // Chave original para referência
    }, { merge: true })
    .then(() => {
      console.log(`📤 Enviado para Firebase: ${k}`);
    })
    .catch((e) => {
      if (e.code !== 'permission-denied') {
        console.warn("[realtime-sync] Erro ao enviar:", k, e.code || e.message);
      }
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
    // Usar chave composta com UID do usuário
    const docKey = `${k}_${user.uid}`;
    const ref = doc(db, "localstorage", docKey);
    
    setDoc(ref, { 
      value: null, 
      uid: user.uid,  // Manter UID mesmo na remoção
      updatedAt: new Date().toISOString(),
      deleted: true,
      deletedBy: user.email || user.uid
    }, { merge: true })
    .then(() => {
      console.log(`🗑️ Removido do Firebase: ${k}`);
    })
    .catch((e) => {
      if (e.code !== 'permission-denied') {
        console.warn("[realtime-sync] Erro ao remover:", k, e.code || e.message);
      }
    });
  }
  
  return res;
};

// Monitorar autenticação
onAuthStateChanged(auth, (user) => {
  if (user) {
    console.log("[realtime-sync] ✅ Usuário autenticado:", user.email || user.uid);
    
    // Criar perfil de usuário se não existir
    const userRef = doc(db, "usuarios", user.uid);
    getDoc(userRef).then((docSnap) => {
      if (!docSnap.exists()) {
        setDoc(userRef, {
          uid: user.uid,
          email: user.email,
          nome: user.displayName || user.email?.split('@')[0] || 'Usuário',
          perfil: 'requisitante', // Perfil padrão
          dataCriacao: new Date().toISOString()
        }, { merge: true }).then(() => {
          console.log('✅ Perfil de usuário criado');
        }).catch((e) => {
          console.warn('Erro ao criar perfil:', e);
        });
      }
    });
    
    // Aguardar um momento para garantir autenticação completa
    setTimeout(() => {
      attachListeners();
    }, 1000);
    
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

// Exportar funções úteis (mantidas como original)
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
  },
  // Adicionar função de debug
  debugSync: () => {
    const user = auth.currentUser;
    if (user) {
      console.log("🔍 Debug Info:");
      console.log("User ID:", user.uid);
      console.log("User Email:", user.email);
      console.log("Keys monitoradas:", KEYS.length);
      console.log("Listeners ativos:", unsubscribers.length);
      console.log("Módulo Admin:", "❌ REMOVIDO");
    } else {
      console.log("Nenhum usuário autenticado");
    }
  }
};

console.log("[realtime-sync] 🚀 Sistema de sincronização em tempo real inicializado - SEM ADMIN");
console.log("[realtime-sync] 📋 Monitorando", KEYS.length, "chaves (admin removido)");
console.log("[realtime-sync] ⏳ Aguardando autenticação...");
