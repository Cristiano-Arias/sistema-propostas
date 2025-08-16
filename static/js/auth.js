/** 
 * Sistema de Autenticação Frontend
 * Gerencia login, logout e permissões
 */

const Auth = {
    // Verificar se usuário está autenticado (usa access_token)
    isAuthenticated() {
        const token = localStorage.getItem('access_token');
        const usuario = localStorage.getItem('usuario_atual');
        if (!token || !usuario) return false;

        // Verifica expiração do JWT (payload.exp em segundos)
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp > Date.now() / 1000;
        } catch {
            return false;
        }
    },

    // Obter usuário atual
    getUsuario() {
        const usuario = localStorage.getItem('usuario_atual');
        return usuario ? JSON.parse(usuario) : null;
    },

    // Obter tokens
    getAccessToken() {
        return localStorage.getItem('access_token');
    },
    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    // Limpar tokens/usuário
    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('usuario_atual');
    },

    // Login (usa /auth/login). Salva access/refresh e monta usuario_atual.
    async login(email, senha) {
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, senha })
            });

            const data = await response.json();

            if (response.ok) {
                // Salva tokens (DE: 'auth_token' -> PARA: 'access_token' + 'refresh_token')
                if (data.access_token) localStorage.setItem('access_token', data.access_token);
                if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token);

                // Monta usuario_atual:
                // - se o backend enviar data.usuario, usa;
                // - senão, decodifica o token e usa o perfil do payload;
                let usuario = data.usuario || null;
                try {
                    const payload = JSON.parse(atob(data.access_token.split('.')[1]));
                    if (!usuario) {
                        usuario = {
                            nome: 'Usuário',
                            perfil: payload.perfil || 'requisitante'
                        };
                    } else if (!usuario.perfil && payload.perfil) {
                        usuario.perfil = payload.perfil;
                    }
                } catch (_) {
                    // ignora erro de decode; mantém 'usuario' se existir
                    if (!usuario) {
                        usuario = { nome: 'Usuário', perfil: 'requisitante' };
                    }
                }

                localStorage.setItem('usuario_atual', JSON.stringify(usuario));
                return { success: true, usuario };
            } else {
                return { success: false, message: data.message || 'Credenciais inválidas' };
            }
        } catch (error) {
            console.error('Erro no login:', error);
            return { success: false, message: 'Erro de conexão' };
        }
    },

    // Logout
    logout() {
        this.clearTokens();
        window.location.href = '/';
    },

    // Verificar permissão
    temPermissao(perfil) {
        const usuario = this.getUsuario();
        return usuario && usuario.perfil === perfil;
    },

    // Redirecionar se não autenticado
    requireAuth() {
        if (!this.isAuthenticated()) {
            alert('Você precisa fazer login para acessar esta página');
            window.location.href = '/';
            return false;
        }
        return true;
    },

    // Adicionar token aos headers (usa access token)
    getHeaders() {
        const token = this.getAccessToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        };
    },

    // Wrapper de fetch com refresh automático
    async apiFetch(url, options = {}) {
        const token = this.getAccessToken();
        const headers = { ...(options.headers || {}), 'Authorization': token ? `Bearer ${token}` : '' };
        let response = await fetch(url, { ...options, headers });

        // Se não deu 401, retorna direto
        if (response.status !== 401) return response;

        // 401: tenta renovar com refresh token
        const rt = this.getRefreshToken();
        if (!rt) { 
            this.clearTokens(); 
            throw new Error('Sessão expirada'); 
        }

        const refreshResp = await fetch('/auth/refresh', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${rt}` }
        });

        if (!refreshResp.ok) {
            this.clearTokens();
            throw new Error('Sessão expirada');
        }

        const { access_token } = await refreshResp.json();
        if (!access_token) {
            this.clearTokens();
            throw new Error('Sessão expirada');
        }

        localStorage.setItem('access_token', access_token);

        // Reexecuta a requisição original com o novo token
        const retryHeaders = { ...(options.headers || {}), 'Authorization': `Bearer ${access_token}` };
        return fetch(url, { ...options, headers: retryHeaders });
    }
};

// Verificar autenticação ao carregar páginas protegidas
document.addEventListener('DOMContentLoaded', function() {
    // Identificar página atual
    const path = window.location.pathname;
    const paginasProtegidas = [
        'dashboard-requisitante.html',
        'dashboard-comprador.html',
        'dashboard-fornecedor.html',
        'criar-tr.html',
        'criar-processo.html',
        'enviar-proposta.html',
        'analise-propostas.html'
    ];

    // Verificar se é página protegida
    const paginaAtual = path.split('/').pop();
    if (paginasProtegidas.includes(paginaAtual)) {
        if (!Auth.requireAuth()) {
            return;
        }

        // Verificar permissões específicas
        const usuario = Auth.getUsuario();
        if (paginaAtual.includes('requisitante') && usuario.perfil !== 'requisitante') {
            alert('Acesso negado. Esta área é exclusiva para requisitantes.');
            window.location.href = '/';
        } else if (paginaAtual.includes('comprador') && usuario.perfil !== 'comprador') {
            alert('Acesso negado. Esta área é exclusiva para compradores.');
            window.location.href = '/';
        } else if (paginaAtual.includes('fornecedor') && usuario.perfil !== 'fornecedor') {
            alert('Acesso negado. Esta área é exclusiva para fornecedores.');
            window.location.href = '/';
        }
    }

    // Atualizar interface com dados do usuário
    const usuarioElement = document.getElementById('usuario-nome');
    if (usuarioElement && Auth.isAuthenticated()) {
        const usuario = Auth.getUsuario();
        usuarioElement.textContent = usuario.nome;
    }

    // Adicionar logout handler
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Deseja realmente sair?')) {
                Auth.logout();
            }
        });
    }
});

// Interceptar formulário de login existente
if (document.getElementById('login-form')) {
    document.getElementById('login-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const senha = document.getElementById('senha').value;
        const perfilSelecionado = document.getElementById('perfil') ? document.getElementById('perfil').value : null;

        // Tenta login no backend
        const result = await Auth.login(email, senha);
        
        if (result.success) {
            // Redireciona pelo perfil retornado/decodificado
            const perfil = result.usuario.perfil;
            switch (perfil) {
                case 'requisitante':
                    window.location.href = 'dashboard-requisitante.html';
                    break;
                case 'comprador':
                    window.location.href = 'dashboard-comprador.html';
                    break;
                case 'fornecedor':
                    window.location.href = 'dashboard-fornecedor.html';
                    break;
                default:
                    // fallback
                    window.location.href = 'dashboard-requisitante.html';
            }
        } else {
            // Fallback para login local (compatibilidade legado)
            const usuarios = JSON.parse(localStorage.getItem('usuarios') || '[]');
            const usuario = usuarios.find(u => 
                u.email === email && 
                u.senha === senha && 
                (!perfilSelecionado || u.perfil === perfilSelecionado)
            );

            if (usuario) {
                localStorage.setItem('usuario_atual', JSON.stringify(usuario));
                
                const perfil = usuario.perfil || perfilSelecionado;
                switch(perfil) {
                    case 'requisitante':
                        window.location.href = 'dashboard-requisitante.html';
                        break;
                    case 'comprador':
                        window.location.href = 'dashboard-comprador.html';
                        break;
                    case 'fornecedor':
                        window.location.href = 'dashboard-fornecedor.html';
                        break;
                    default:
                        window.location.href = 'dashboard-requisitante.html';
                }
            } else {
                alert(result.message || 'Email, senha ou perfil incorretos!');
            }
        }
    });
}

// Funções auxiliares para páginas específicas
function checkRequisitanteAuth() {
    return Auth.requireAuth() && Auth.temPermissao('requisitante');
}

function checkCompradorAuth() {
    return Auth.requireAuth() && Auth.temPermissao('comprador');
}

function checkFornecedorAuth() {
    return Auth.requireAuth() && Auth.temPermissao('fornecedor');
}

// Exportar para uso global
window.Auth = Auth;
