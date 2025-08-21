// static/js/realtime-sync.js - Sincronização localStorage <-> Firestore (não-invasiva)
import { db } from './firebase.js';
import { doc, getDoc, setDoc, onSnapshot } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';

const COLLECTION = 'localstorage';
const KEYS = ["admin_logado", "auth_token", "azure_ai_config", "comprador_logado", "convites_processo", "credenciais_fornecedores", "fornecedor_logado", "fornecedor_token", "fornecedores_cadastrados", "notificacoes_requisitante", "pareceres_requisitante", "pareceres_tecnicos", "processos", "processos_compra", "propostas_comparativo", "propostas_fornecedor", "propostas_fornecedor_", "propostas_fornecedores", "propostas_liberadas_parecer", "propostas_para_requisitante", "requisitante_logado", "sistema_analises_ia", "sistema_fornecedores", "sistema_processos", "sistema_propostas", "sistema_propostas_completas", "sistema_trs", "sistema_usuarios_fornecedores", "technical_analysis_draft", "technical_analysis_final", "termos_referencia", "tr_autosave", "tr_rascunho", "tr_rascunho_", "trs_aprovados", "trs_pendentes_aprovacao", "userData", "userToken", "usuario_logado"];

let isApplyingRemote = false;

// Listener remoto -> local
for (const key of KEYS) {
  const ref = doc(db, COLLECTION, key);
  onSnapshot(ref, (snap) => {
    if (!snap.exists()) return;
    const { value } = snap.data();
    try {
      isApplyingRemote = true;
      localStorage.setItem(key, value);
      window.dispatchEvent(new CustomEvent('ls:updated', { detail: { key, source: 'remote' } }));
    } finally {
      isApplyingRemote = false;
    }
  });
}

// Monkey-patch setItem para subir ao Firestore
const _setItem = localStorage.setItem.bind(localStorage);
localStorage.setItem = function(k, v) {
  const result = _setItem(k, v);
  if (!isApplyingRemote && KEYS.includes(k)) {
    const ref = doc(db, COLLECTION, k);
    setDoc(ref, { value: v, updatedAt: new Date().toISOString() }, { merge: true }).catch(console.error);
  }
  return result;
};

console.log('[realtime-sync] ativo para chaves:', KEYS);
