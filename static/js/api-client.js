export class ApiClient {
  constructor(baseURL = null) {
    this.baseURL = baseURL || (location.hostname === 'localhost' ? 'http://localhost:5000/api' : '/api');
    this.idToken = null;
  }
  async setUser(user) { this.idToken = user ? await user.getIdToken() : null; }
  headers() {
    const h = {'Content-Type':'application/json'};
    if (this.idToken) h['Authorization'] = `Bearer ${this.idToken}`;
    return h;
  }
  async get(path)  { const r = await fetch(this.baseURL+path, {headers:this.headers()}); return r.json(); }
  async post(path, body) { const r = await fetch(this.baseURL+path, {method:'POST',headers:this.headers(), body: JSON.stringify(body||{})}); return r.json(); }

  // ====== Métodos específicos para Termos de Referência (TRs) ======
  /**
   * Tenta obter todos os TRs do backend. Caso a chamada falhe ou não haja API
   * disponível, retorna os dados armazenados localmente no localStorage.
   * @returns {Promise<Array>} Lista de TRs
   */
  async getTRs() {
    try {
      const result = await this.get('/termos-referencia');
      if (Array.isArray(result)) return result;
    } catch (e) {
      // ignora e usa fallback
    }
    return this._loadTRsLocal();
  }

  /**
   * Retorna os TRs pendentes de aprovação. Considera como pendentes os TRs cujo
   * status seja "PENDENTE_APROVACAO", "ENVIADO" ou "PENDENTE", ignorando
   * diferenças de caixa.
   * @returns {Promise<Array>}
   */
  async getTRsPendentes() {
    const trs = await this.getTRs();
    return trs.filter(tr => {
      const s = (tr.status || '').toUpperCase();
      return s === 'PENDENTE_APROVACAO' || s === 'ENVIADO' || s === 'PENDENTE';
    });
  }

  /**
   * Retorna os TRs aprovados. Considera status "aprovado" ignorando caixa.
   * @returns {Promise<Array>}
   */
  async getTRsAprovados() {
    const trs = await this.getTRs();
    return trs.filter(tr => {
      const s = (tr.status || '').toUpperCase();
      return s === 'APROVADO';
    });
  }

  /**
   * Busca um TR específico pelo seu ID ou número. Faz tentativa no backend e,
   * caso falhe, busca no localStorage.
   * @param {string|number} id
   * @returns {Promise<Object|null>}
   */
  async getTR(id) {
    try {
      const result = await this.get(`/termos-referencia/${id}`);
      if (result) return result;
    } catch (e) {
      // fallback
    }
    const trs = await this.getTRs();
    return trs.find(tr => tr.id == id || tr.numeroTR == id || tr.numero == id) || null;
  }

  /**
   * Cria um novo TR no backend se possível ou salva localmente. Retorna o
   * resultado contendo ao menos a propriedade id do TR criado.
   * @param {Object} dados
   * @returns {Promise<{id: string|number}>}
   */
  async criarTR(dados) {
    try {
      const result = await this.post('/termos-referencia', dados);
      if (result && result.id) return result;
    } catch (_) {}
    const trs = this._loadTRsLocal();
    const novoId = Date.now();
    const tr = { ...dados, id: novoId, data_criacao: new Date().toISOString(), status: 'pendente' };
    trs.push(tr);
    this._saveTRsLocal(trs);
    return { id: novoId };
  }

  /**
   * Aprova um TR. Atualiza o status para "aprovado" e persiste localmente.
   * @param {string|number} id
   * @param {string} parecer
   */
  async aprovarTR(id, parecer) {
    try {
      return await this.post(`/termos-referencia/${id}/aprovar`, { parecer });
    } catch (_) {}
    const trs = this._loadTRsLocal();
    const tr = trs.find(tr => tr.id == id || tr.numeroTR == id || tr.numero == id);
    if (tr) {
      tr.status = 'aprovado';
      tr.parecer_comprador = parecer;
      tr.data_aprovacao = new Date().toISOString();
      this._saveTRsLocal(trs);
    }
    return { sucesso: true };
  }

  /**
   * Reprova um TR. Atualiza o status para "reprovado" e persiste localmente.
   * @param {string|number} id
   * @param {string} motivo
   */
  async reprovarTR(id, motivo) {
    try {
      return await this.post(`/termos-referencia/${id}/reprovar`, { motivo });
    } catch (_) {}
    const trs = this._loadTRsLocal();
    const tr = trs.find(tr => tr.id == id || tr.numeroTR == id || tr.numero == id);
    if (tr) {
      tr.status = 'reprovado';
      tr.motivo_reprovacao = motivo;
      tr.data_reprovacao = new Date().toISOString();
      this._saveTRsLocal(trs);
    }
    return { sucesso: true };
  }

  /**
   * (Opcional) Baixa o PDF de um TR. Por padrão, tenta usar a rota do backend.
   * Se não existir, apenas mostra alerta.
   * @param {string|number} id
   */
  async downloadTRPDF(id) {
    try {
      return await this.get(`/termos-referencia/${id}/pdf`);
    } catch (_) {
      alert('Funcionalidade de download de PDF indisponível offline.');
    }
  }

  // ====== Métodos específicos para Processos ======
  /**
   * Cria um novo processo licitatório. Tenta usar o backend, mas salva
   * localmente se a API não estiver disponível. Define status "ATIVO" (ou
   * "aberto") por padrão.
   * @param {Object} dados
   * @returns {Promise<{id: string|number}>}
   */
  async criarProcesso(dados) {
    try {
      const result = await this.post('/processos', dados);
      if (result && result.id) return result;
    } catch (_) {}
    const processos = this._loadProcessosLocal();
    const novoId = Date.now();
    const proc = { ...dados, id: novoId, data_criacao: new Date().toISOString(), status: dados.status || 'ATIVO' };
    processos.push(proc);
    this._saveProcessosLocal(processos);
    return { id: novoId };
  }

  /**
   * Obtém a lista de processos disponíveis. Caso o backend não responda,
   * carrega a lista do localStorage (chaves: 'sistema_processos',
   * 'processos_compra' ou 'processos_licitatorios').
   * @returns {Promise<Array>}
   */
  async getProcessosDisponiveis() {
    try {
      const result = await this.get('/processos');
      if (Array.isArray(result)) return result;
    } catch (_) {}
    return this._loadProcessosLocal();
  }

  // ====== Métodos de Notificações ======
  /**
   * Busca notificações para o comprador. Retorna um array de notificações,
   * mesmo que o backend não esteja disponível. Cada notificação deve ter
   * campo "lida".
   * @returns {Promise<Array>}
   */
  async getNotificacoes() {
    try {
      const result = await this.get('/notificacoes');
      if (Array.isArray(result)) return result;
    } catch (_) {}
    try {
      const local = localStorage.getItem('notificacoes_comprador');
      return local ? JSON.parse(local) : [];
    } catch (_) {
      return [];
    }
  }

  /**
   * Marca uma notificação como lida. Tenta atualizar no backend, mas atualiza
   * localmente se não houver API.
   * @param {string|number} id
   * @returns {Promise<void>}
   */
  async marcarNotificacaoLida(id) {
    try {
      await this.post(`/notificacoes/${id}/ler`, {});
    } catch (_) {
      // fallback: marcar localmente
      try {
        const local = localStorage.getItem('notificacoes_comprador');
        const notificacoes = local ? JSON.parse(local) : [];
        const n = notificacoes.find(n => n.id == id);
        if (n) {
          n.lida = true;
          localStorage.setItem('notificacoes_comprador', JSON.stringify(notificacoes));
        }
      } catch (_) {}
    }
  }

  // ====== Métodos privados de utilidade ======
  /**
   * Carrega TRs do localStorage a partir das chaves compatíveis. Dá
   * preferência para "sistema_trs", mas aceita "termos_referencia" para
   * compatibilidade.
   * @returns {Array}
   */
  _loadTRsLocal() {
    let data = [];
    try {
      const primary = localStorage.getItem('sistema_trs');
      if (primary) {
        data = JSON.parse(primary) || [];
      } else {
        const secondary = localStorage.getItem('termos_referencia');
        data = secondary ? JSON.parse(secondary) : [];
      }
      if (!Array.isArray(data)) data = [];
    } catch (_) {
      data = [];
    }
    return data;
  }

  /**
   * Persiste a lista de TRs no localStorage em ambas as chaves para
   * compatibilidade.
   * @param {Array} trs
   */
  _saveTRsLocal(trs) {
    try {
      const json = JSON.stringify(trs);
      localStorage.setItem('sistema_trs', json);
      localStorage.setItem('termos_referencia', json);
    } catch (_) {}
  }

  /**
   * Carrega processos do localStorage. Dá preferência para "sistema_processos",
   * mas aceita "processos_compra" ou "processos_licitatorios" para
   * compatibilidade.
   * @returns {Array}
   */
  _loadProcessosLocal() {
    let data = [];
    try {
      const keys = ['sistema_processos','processos_compra','processos_licitatorios'];
      for (const key of keys) {
        const val = localStorage.getItem(key);
        if (val) {
          data = JSON.parse(val);
          if (Array.isArray(data)) break;
        }
      }
      if (!Array.isArray(data)) data = [];
    } catch (_) {
      data = [];
    }
    return data;
  }

  /**
   * Persiste a lista de processos no localStorage em múltiplas chaves para
   * compatibilidade.
   * @param {Array} processos
   */
  _saveProcessosLocal(processos) {
    try {
      const json = JSON.stringify(processos);
      localStorage.setItem('sistema_processos', json);
      localStorage.setItem('processos_compra', json);
      localStorage.setItem('processos_licitatorios', json);
    } catch (_) {}
  }
}
window.apiClient = new ApiClient();
