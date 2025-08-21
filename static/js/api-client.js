/**
 * Cliente API para integração com o backend
 * Mantém compatibilidade com localStorage existente
 */

class ApiClient {
    constructor() {
        this.baseURL = window.location.hostname === 'localhost' 
            ? 'http://localhost:5000/api' 
            : '/api';
        this.token = localStorage.getItem('auth_token');
        this.fornecedorToken = localStorage.getItem('fornecedor_token');
    }

    // Headers padrão para requisições
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        } else if (this.fornecedorToken) {
            headers['Authorization'] = `Bearer ${this.fornecedorToken}`;
        }
        
        return headers;
    }

    // Método genérico para requisições
    async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                headers: {
                    ...this.getHeaders(),
                    ...options.headers
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erro na requisição');
            }

            return data;
        } catch (error) {
            console.error('Erro na API:', error);
            // Fallback para localStorage se API falhar
            return null;
        }
    }

    // ========================================
    // AUTENTICAÇÃO
    // ========================================

    async login(email, senha) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, senha })
        });

        if (response && response.success) {
            this.token = response.access_token;
            localStorage.setItem('auth_token', this.token);
            localStorage.setItem('usuario_logado', JSON.stringify(response.usuario));
        }

        return response;
    }

    async loginFornecedor(login, senha) {
        const response = await this.request('/auth/login-fornecedor', {
            method: 'POST',
            body: JSON.stringify({ login, senha })
        });

        if (response && response.success) {
            this.fornecedorToken = response.access_token;
            localStorage.setItem('fornecedor_token', this.fornecedorToken);
            localStorage.setItem('fornecedor_logado', JSON.stringify(response.fornecedor));
        }

        return response;
    }

    logout() {
        this.token = null;
        this.fornecedorToken = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('fornecedor_token');
        localStorage.removeItem('usuario_logado');
        localStorage.removeItem('fornecedor_logado');
    }

    // ========================================
    // TERMOS DE REFERÊNCIA
    // ========================================

    async listarTRs() {
        const response = await this.request('/trs');
        
        if (response && response.success) {
            // Salvar também no localStorage para compatibilidade
            localStorage.setItem('termos_referencia', JSON.stringify(response.trs));
            return response.trs;
        }
        
        // Fallback para localStorage
        return JSON.parse(localStorage.getItem('termos_referencia') || '[]');
    }

    async obterTR(trId) {
        const response = await this.request(`/trs/${trId}`);
        return response ? response.tr : null;
    }

    async salvarTR(dados) {
        // Salvar no localStorage primeiro (compatibilidade)
        const trs = JSON.parse(localStorage.getItem('termos_referencia') || '[]');
        const novoTR = {
            ...dados,
            id: Date.now().toString(),
            numeroTR: `TR-${new Date().getFullYear()}-${Date.now().toString().slice(-6)}`,
            dataCriacao: new Date().toISOString(),
            status: 'PENDENTE_APROVACAO'
        };
        trs.push(novoTR);
        localStorage.setItem('termos_referencia', JSON.stringify(trs));

        // Tentar salvar no backend
        const response = await this.request('/trs', {
            method: 'POST',
            body: JSON.stringify(dados)
        });

        if (response && response.success) {
            // Atualizar com dados do servidor
            const index = trs.findIndex(tr => tr.id === novoTR.id);
            if (index !== -1) {
                trs[index] = response.tr;
                localStorage.setItem('termos_referencia', JSON.stringify(trs));
            }
            return response.tr;
        }

        return novoTR;
    }

    async aprovarTR(trId, parecer) {
        // Atualizar localStorage
        const trs = JSON.parse(localStorage.getItem('termos_referencia') || '[]');
        const tr = trs.find(t => t.id === trId);
        if (tr) {
            tr.status = 'APROVADO';
            tr.parecerComprador = parecer;
            tr.dataAprovacao = new Date().toISOString();
            localStorage.setItem('termos_referencia', JSON.stringify(trs));
        }

        // Enviar para backend
        const response = await this.request(`/trs/${trId}/aprovar`, {
            method: 'POST',
            body: JSON.stringify({ parecer })
        });

        return response || { success: true };
    }

    async reprovarTR(trId, parecer) {
        // Atualizar localStorage
        const trs = JSON.parse(localStorage.getItem('termos_referencia') || '[]');
        const tr = trs.find(t => t.id === trId);
        if (tr) {
            tr.status = 'REPROVADO';
            tr.parecerComprador = parecer;
            tr.dataReprovacao = new Date().toISOString();
            localStorage.setItem('termos_referencia', JSON.stringify(trs));
        }

        // Enviar para backend
        const response = await this.request(`/trs/${trId}/reprovar`, {
            method: 'POST',
            body: JSON.stringify({ parecer })
        });

        return response || { success: true };
    }

    async baixarTR(trId) {
        try {
            const token = this.token || this.fornecedorToken;
            const response = await fetch(`${this.baseURL}/trs/${trId}/download`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `TR_${trId}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                return true;
            }
        } catch (error) {
            console.error('Erro ao baixar TR:', error);
        }
        return false;
    }

    async getTRsPendentes() {
        // 1) Tenta no backend (se existir endpoint)
        const response = await this.request('/trs?status=PENDENTE_APROVACAO');
        if (response && response.success && Array.isArray(response.trs)) {
            return response.trs;
        }
    
        // 2) Fallback local: filtra o armazenamento "oficial"
        const trs = JSON.parse(localStorage.getItem('termos_referencia') || '[]');
        return trs.filter(t => t.status === 'PENDENTE_APROVACAO');
    }
    
    // ========================================
    // PROCESSOS
    // ========================================

    async listarProcessos() {
        const response = await this.request('/processos');
        
        if (response && response.success) {
            localStorage.setItem('processos', JSON.stringify(response.processos));
            return response.processos;
        }
        
        return JSON.parse(localStorage.getItem('processos') || '[]');
    }

    async listarProcessosFornecedor() {
        const response = await this.request('/processos/fornecedor');
        
        if (response && response.success) {
            return response.processos;
        }
        
        return [];
    }

    async criarProcesso(dados) {
        // Salvar no localStorage
        const processos = JSON.parse(localStorage.getItem('processos') || '[]');
        const novoProcesso = {
            ...dados,
            id: Date.now().toString(),
            numero: `PROC-${new Date().getFullYear()}-${Date.now().toString().slice(-6)}`,
            dataCriacao: new Date().toISOString(),
            status: 'ATIVO'
        };
        processos.push(novoProcesso);
        localStorage.setItem('processos', JSON.stringify(processos));

        // Salvar credenciais dos fornecedores
        if (dados.fornecedores && dados.fornecedores.length > 0) {
            const credenciais = JSON.parse(localStorage.getItem('credenciais_fornecedores') || '[]');
            dados.fornecedores.forEach(f => {
                const login = `fornecedor_${f.cnpj.replace(/\D/g, '').slice(-8)}`;
                const senha = this.gerarSenhaAleatoria();
                
                credenciais.push({
                    processoId: novoProcesso.id,
                    numeroProcesso: novoProcesso.numero,
                    cnpj: f.cnpj,
                    razaoSocial: f.razaoSocial,
                    email: f.email,
                    login: login,
                    senha: senha,
                    ativo: true,
                    dataCriacao: new Date().toISOString()
                });
            });
            localStorage.setItem('credenciais_fornecedores', JSON.stringify(credenciais));
        }

        // Enviar para backend
        const response = await this.request('/processos', {
            method: 'POST',
            body: JSON.stringify(dados)
        });

        if (response && response.success) {
            const index = processos.findIndex(p => p.id === novoProcesso.id);
            if (index !== -1) {
                processos[index] = response.processo;
                localStorage.setItem('processos', JSON.stringify(processos));
            }
            return response.processo;
        }

        return novoProcesso;
    }

    // ========================================
    // PROPOSTAS
    // ========================================

    async enviarProposta(dados) {
        // Salvar no localStorage
        const propostas = JSON.parse(localStorage.getItem('propostas_fornecedor') || '[]');
        const novaProposta = {
            ...dados,
            id: Date.now().toString(),
            dataEnvio: new Date().toISOString(),
            status: 'ENVIADA'
        };
        propostas.push(novaProposta);
        localStorage.setItem('propostas_fornecedor', JSON.stringify(propostas));

        // Enviar para backend
        const response = await this.request('/propostas', {
            method: 'POST',
            body: JSON.stringify(dados)
        });

        if (response && response.success) {
            return response.proposta;
        }

        return novaProposta;
    }

    async listarPropostasProcesso(processoId) {
        const response = await this.request(`/propostas/processo/${processoId}`);
        
        if (response && response.success) {
            return response.propostas;
        }
        
        // Fallback para localStorage
        const propostas = JSON.parse(localStorage.getItem('propostas_fornecedor') || '[]');
        return propostas.filter(p => p.processoId === processoId);
    }

    // ========================================
    // NOTIFICAÇÕES
    // ========================================

    async listarNotificacoes() {
        const response = await this.request('/notificacoes');
        
        if (response && response.success) {
            return response.notificacoes;
        }
        
        return [];
    }

    async marcarNotificacaoLida(notificacaoId) {
        await this.request(`/notificacoes/${notificacaoId}/lida`, {
            method: 'POST'
        });
    }

    // ========================================
    // UTILITÁRIOS
    // ========================================

    gerarSenhaAleatoria() {
        const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
        let senha = '';
        for (let i = 0; i < 8; i++) {
            senha += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return senha;
    }

    // Função para verificar status da API
    async verificarStatus() {
        try {
            const response = await fetch(`${this.baseURL.replace('/api', '')}/api/status`);
            return response.ok;
        } catch {
            return false;
        }
    }
}

// Criar instância global
window.apiClient = new ApiClient();
