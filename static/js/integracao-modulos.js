/* arquivo: /static/js/integracao-modulos.js */
/**
 * Sistema de Integração entre Módulos
 * Conecta Requisitante -> Comprador -> Fornecedor
 */

// ========================================
// SISTEMA DE NOTIFICAÇÕES E CONFIRMAÇÕES
// =====

// (conteúdo original do seu arquivo permanece aqui — NÃO REMOVA)

// ... (SEU CONTEÚDO ORIGINAL) ...

/* ===== PATCH: Convidar Fornecedores via API (Firebase Auth + Firestore) =====
   Este bloco sobrescreve a função global 'convidarFornecedores' para:
   1) Criar o usuário no Firebase Authentication via backend (/api/usuarios)
   2) Registrar/atualizar metadados no Firestore pelo backend
   3) Manter compatibilidade salvando no localStorage os mesmos objetos de antes
   Requisitos: usuário COMPRADOR logado no Firebase; backend_render_fix exposto em /api.
*/
(async () => {
  // tenta obter token do Firebase para autenticar no backend
  async function getBearerToken() {
    try {
      if (window.firebaseAuth && typeof window.firebaseAuth.getToken === 'function') {
        const t = await window.firebaseAuth.getToken();
        if (t) return t;
      }
    } catch(e) { console.warn('Token Firebase indisponível:', e); }
    // fallback (se você já persistir em outro lugar)
    return localStorage.getItem('auth_token') || null;
  }

  window.convidarFornecedores = async function(processoId, fornecedoresIds) {
    try {
      let processos = JSON.parse(localStorage.getItem('processos_compra') || '[]');
      const processo = processos.find(p => p.id === processoId);
      if (!processo) {
        if (typeof mostrarErro === 'function') mostrarErro('Processo não encontrado!');
        return false;
      }

      const fornecedores = JSON.parse(localStorage.getItem('fornecedores_cadastrados') || '[]');
      let credenciais = JSON.parse(localStorage.getItem('credenciais_fornecedores') || '[]');

      const token = await getBearerToken();
      if (!token) {
        if (typeof mostrarErro === 'function') mostrarErro('Sessão inválida. Faça login novamente como Comprador.');
        return false;
      }

      for (const fornId of fornecedoresIds) {
        const fornecedor = fornecedores.find(f => f.id === fornId);
        if (!fornecedor) continue;

        const senhaProvisoria = (Math.random().toString(36).slice(-8) + 'A1'); // senha provisória simples

        // 1) cria usuário no backend -> Firebase Auth + coleções
        //    Ajustado para utilizar a nova rota /api/fornecedores que permite
        //    compradores ou administradores criarem contas de fornecedores.
        const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:5000' : '';
        const resp = await fetch(`${apiUrl}/api/fornecedores`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({
            email: fornecedor.email,
            senha: senhaProvisoria,
            nome: fornecedor.razaoSocial || fornecedor.nome || 'fornecedor',
            perfil: 'fornecedor',
            ativo: true,
            metadata: {
              cnpj: fornecedor.cnpj,
              razaoSocial: fornecedor.razaoSocial
            }
          })
        });

        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          console.error('Falha ao criar usuário fornecedor', data);
          if (typeof mostrarErro === 'function') mostrarErro('Erro ao criar fornecedor: ' + (data.erro || resp.status));
          continue;
        }

        // 2) compatibilidade com o front atual (mantém objetos locais)
        const credencial = {
          id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
          processoId,
          numeroProcesso: processo.numeroProcesso,
          fornecedorId: fornecedor.id,
          cnpj: fornecedor.cnpj,
          razaoSocial: fornecedor.razaoSocial,
          email: fornecedor.email,
          login: fornecedor.email,        // agora o login é o e-mail do Authentication
          senha: senhaProvisoria,         // entregue ao fornecedor por canal adequado
          ativo: true,
          dataCriacao: new Date().toISOString()
        };
        credenciais.push(credencial);

        processo.fornecedoresConvidados = processo.fornecedoresConvidados || [];
        processo.fornecedoresConvidados.push({
          id: fornecedor.id,
          nome: fornecedor.razaoSocial,
          cnpj: fornecedor.cnpj,
          credencial: credencial.login
        });

        if (typeof criarNotificacao === 'function') {
          criarNotificacao('fornecedor_' + fornecedor.id, {
            tipo: 'convite_processo',
            titulo: '📧 Novo Convite para Processo',
            mensagem: `Você foi convidado para o processo ${processo.numeroProcesso}`,
            processo_id: processoId,
            credenciais: { login: credencial.login, senha: credencial.senha }
          });
        }
      }

      localStorage.setItem('credenciais_fornecedores', JSON.stringify(credenciais));
      localStorage.setItem('processos_compra', JSON.stringify(processos));

      if (typeof mostrarConfirmacao === 'function') {
        mostrarConfirmacao(`✅ ${fornecedoresIds.length} fornecedor(es) convidado(s) com sucesso!`);
      }
      return true;

    } catch (err) {
      console.error('Erro ao convidar fornecedores (API):', err);
      if (typeof mostrarErro === 'function') mostrarErro('Erro inesperado ao convidar fornecedores.');
      return false;
    }
  };
})();



// Funções de aprovação/reprovação de TR para o módulo Comprador
window.IntegracaoModulos = window.IntegracaoModulos || {};

window.IntegracaoModulos.aprovarTRComprador = function(numeroTR, parecer) {
    let trs = SistemaLocal.carregar(SistemaLocal.CHAVES.TRS, []);
    const trIndex = trs.findIndex(t => t.numeroTR === numeroTR);

    if (trIndex === -1) {
        console.error(`TR ${numeroTR} não encontrado para aprovação.`);
        return null;
    }

    let tr = trs[trIndex];
    tr.status = 'APROVADO';
    tr.parecerComprador = parecer;
    tr.dataAprovacao = new Date().toISOString();
    tr.aprovadoPor = 'Comprador'; // Em um sistema real, seria o usuário logado

    SistemaLocal.salvar(SistemaLocal.CHAVES.TRS, trs);
    console.log(`✅ TR ${numeroTR} aprovado e salvo.`);

    // Notificar requisitante
    const notificacao = {
        id: Date.now(),
        tipo: 'TR_APROVADO',
        titulo: 'TR Aprovado',
        mensagem: `TR ${numeroTR} foi aprovado pelo comprador.`, 
        data: new Date().toISOString(),
        lida: false,
        tr_id: numeroTR
    };
    SistemaLocal.salvar(SistemaLocal.CHAVES.NOTIFICACOES, [...SistemaLocal.carregar(SistemaLocal.CHAVES.NOTIFICACOES, []), notificacao]);
    console.log(`📢 Notificação de aprovação enviada para o requisitante.`);

    return tr;
};

window.IntegracaoModulos.reprovarTRComprador = function(numeroTR, parecer) {
    let trs = SistemaLocal.carregar(SistemaLocal.CHAVES.TRS, []);
    const trIndex = trs.findIndex(t => t.numeroTR === numeroTR);

    if (trIndex === -1) {
        console.error(`TR ${numeroTR} não encontrado para reprovação.`);
        return null;
    }

    let tr = trs[trIndex];
    tr.status = 'REPROVADO';
    tr.parecerComprador = parecer;
    tr.dataReprovacao = new Date().toISOString();
    tr.reprovadoPor = 'Comprador'; // Em um sistema real, seria o usuário logado

    SistemaLocal.salvar(SistemaLocal.CHAVES.TRS, trs);
    console.log(`❌ TR ${numeroTR} reprovado e salvo.`);

    // Notificar requisitante
    const notificacao = {
        id: Date.now(),
        tipo: 'TR_REPROVADO',
        titulo: 'TR Reprovado',
        mensagem: `TR ${numeroTR} foi reprovado pelo comprador. Motivo: ${parecer}`, 
        data: new Date().toISOString(),
        lida: false,
        tr_id: numeroTR
    };
    SistemaLocal.salvar(SistemaLocal.CHAVES.NOTIFICACOES, [...SistemaLocal.carregar(SistemaLocal.CHAVES.NOTIFICACOES, []), notificacao]);
    console.log(`📢 Notificação de reprovação enviada para o requisitante.`);

    return tr;
};

