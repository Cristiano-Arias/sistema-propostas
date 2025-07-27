/**
 * Cliente API para Sistema de Gestão de Propostas
 * Conecta frontend com backend usando JWT
 */

class APIClient {
    constructor() {
        this.baseURL = window.location.hostname === 'localhost' 
            ? 'http://localhost:5000' 
            : window.location.origin;
        this.token = localStorage.getItem('access_token');
    }

    // Configurar headers padrão
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        return headers;
    }

    // Método genérico para requisições
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: this.getHeaders(),
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Token expirado, fazer logout
                this.logout();
                throw new Error('Sessão expirada. Faça login novamente.');
            }
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `Erro HTTP: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Erro na requisição:', error);
            throw error;
        }
    }

    // Métodos de autenticação
    async login(email, senha) {
        const response = await this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, senha })
        });
        
        if (response.access_token) {
            this.token = response.access_token;
            localStorage.setItem('access_token', this.token);
            localStorage.setItem('user_data', JSON.stringify(response.user));
        }
        
        return response;
    }

    logout() {
        this.token = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_data');
        window.location.href = '/';
    }

    // Métodos para TRs
    async salvarTR(dadosTR) {
        return await this.request('/api/v1/trs', {
            method: 'POST',
            body: JSON.stringify(dadosTR)
        });
    }

    async listarTRs() {
        return await this.request('/api/v1/trs');
    }

    async obterTR(id) {
        return await this.request(`/api/v1/trs/${id}`);
    }

    async atualizarTR(id, dadosTR) {
        return await this.request(`/api/v1/trs/${id}`, {
            method: 'PUT',
            body: JSON.stringify(dadosTR)
        });
    }

    async excluirTR(id) {
        return await this.request(`/api/v1/trs/${id}`, {
            method: 'DELETE'
        });
    }

    // Métodos para Processos
    async salvarProcesso(dadosProcesso) {
        return await this.request('/api/v1/processos', {
            method: 'POST',
            body: JSON.stringify(dadosProcesso)
        });
    }

    async listarProcessos() {
        return await this.request('/api/v1/processos');
    }

    async obterProcesso(id) {
        return await this.request(`/api/v1/processos/${id}`);
    }

    // Métodos para Propostas
    async salvarProposta(dadosProposta) {
        return await this.request('/api/v1/propostas', {
            method: 'POST',
            body: JSON.stringify(dadosProposta)
        });
    }

    async listarPropostas() {
        return await this.request('/api/v1/propostas');
    }

    // Métodos para Usuários
    async listarUsuarios() {
        return await this.request('/api/v1/usuarios');
    }

    async criarUsuario(dadosUsuario) {
        return await this.request('/api/v1/usuarios', {
            method: 'POST',
            body: JSON.stringify(dadosUsuario)
        });
    }

    // Métodos para Relatórios
    async obterEstatisticas() {
        return await this.request('/api/v1/relatorios/estatisticas');
    }

    async gerarRelatorio(tipo, filtros = {}) {
        return await this.request('/api/v1/relatorios/gerar', {
            method: 'POST',
            body: JSON.stringify({ tipo, filtros })
        });
    }

    // Método para verificar status da API
    async verificarStatus() {
        return await this.request('/api/status');
    }
}

// Instância global do cliente API
window.apiClient = new APIClient();

// Funções auxiliares para compatibilidade
window.API = {
    salvarTR: (dados) => window.apiClient.salvarTR(dados),
    listarTRs: () => window.apiClient.listarTRs(),
    salvarProcesso: (dados) => window.apiClient.salvarProcesso(dados),
    listarProcessos: () => window.apiClient.listarProcessos(),
    login: (email, senha) => window.apiClient.login(email, senha),
    logout: () => window.apiClient.logout()
};

console.log('✅ API Client carregado com sucesso');

