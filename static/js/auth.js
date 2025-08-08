/**
 * Autenticação Frontend – usando API real
 * Armazena access_token/refresh_token + usuario_atual no localStorage
 */

const Auth = {
    // Verificar se usuário está autenticado (access token válido)
    isAuthenticated() {
        const token = localStorage.getItem('auth_token');
        const usuario = localStorage.getItem('usuario_atual');
        if (!token || !usuario) return false;

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

    // Obter headers com Authorization
    getHeaders() {
        const token = localStorage.getItem('auth_token');
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        };
    },

    // Login na API
    async login(email, senha) {
        try {
            const resp = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ email, senha })
            });
            const data = await resp.json();

            if (!resp.ok) {
                return { success: false, message: data.message || data.error || 'Credenciais inválidas' };
            }

            // Ajuste de compatibilidade — aceita access_token OU token
            const token = data.access_token || data.token;
            if (!token) {
                return { success: false, message: 'Token não recebido do servidor' };
            }
            
            localStorage.setItem('auth_token', token);
            if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
            }
            localStorage.setItem('usuario_atual', JSON.stringify(data.usuario));
            
            return { success: true, usuario: data.usuario };
            } catch (e) {
                console.error('Erro no login:', e);
                return { success: false, message: 'Erro de conexão' };
            }
    },

    // Renovar access_token usando refresh_token (opcional)
    async refresh() {
        const refresh = localStorage.getItem('refresh_token');
        if (!refresh) return false;

        try {
            const resp = await fetch('/api/auth/refresh', { method: 'POST', headers: this.getHeaders() });
            const data = await resp.json();
            if (resp.ok && data.access_token) {
                localStorage.setItem('auth_token', data.access_token);
                return true;
            }
        } catch {}
        return false;
    },

    // Logout
    async logout() {
        try { await fetch('/api/auth/logout', { method: 'POST', headers: this.getHeaders() }); } catch {}
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('usuario_atual');
        window.location.href = '/static/index.html';
    },

    // Guard simples por perfil
    temPermissao(perfil) {
        const u = this.getUsuario();
        return u && u.perfil === perfil;
    },

    // Exigir login na página
    requireAuth() {
        if (this.isAuthenticated()) return true;
        alert('Você precisa fazer login.');
        window.location.href = '/static/login-fornecedor.html';
        return false;
    }
};

// Aplicar proteção básica nas páginas conhecidas
document.addEventListener('DOMContentLoaded', () => {
    const path = (window.location.pathname || '').split('/').pop();
    const paginasProtegidas = [
        'dashboard-requisitante.html',
        'dashboard-comprador.html',
        'dashboard-fornecedor.html',
        'criar-tr.html',
        'criar-processo.html',
        'enviar-proposta.html',
        'analise-propostas.html'
    ];

    if (paginasProtegidas.includes(path) && !Auth.requireAuth()) return;

    // Nome do usuário no topo, se existir
    const el = document.getElementById('usuario-nome');
    if (el && Auth.isAuthenticated()) {
        const u = Auth.getUsuario();
        el.textContent = u?.nome || 'Usuário';
    }

    // Botão de logout
    const btnLogout = document.getElementById('logout-btn');
    if (btnLogout) btnLogout.addEventListener('click', e => { e.preventDefault(); Auth.logout(); });
});

// Expor global (para páginas chamarem)
window.Auth = Auth;
