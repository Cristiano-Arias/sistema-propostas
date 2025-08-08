/**
 * Autenticação Frontend – usando API real
 * CORREÇÃO: Compatibilidade total com o backend
 */

const Auth = {
    // Verificar se usuário está autenticado (access token válido)
    isAuthenticated() {
        const token = localStorage.getItem('auth_token');
        const usuario = localStorage.getItem('usuario_atual');
        if (!token || !usuario) return false;

        try {
            // Verificar se é um JWT válido
            const parts = token.split('.');
            if (parts.length !== 3) return false;
            
            const payload = JSON.parse(atob(parts[1]));
            return payload.exp > Date.now() / 1000;
        } catch (e) {
            console.error('Token inválido:', e);
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

    // Login na API - CORRIGIDO
    async login(email, senha) {
        try {
            // CORREÇÃO: Enviar tanto 'email' quanto 'login' para compatibilidade
            const resp = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include', // Importante para cookies de sessão
                body: JSON.stringify({ 
                    email: email,
                    login: email,  // ADICIONAR: enviar também como 'login'
                    senha: senha 
                })
            });
            
            const data = await resp.json();

            if (!resp.ok) {
                console.error('Erro no login:', resp.status, data);
                return { 
                    success: false, 
                    message: data.message || data.error || 'Credenciais inválidas' 
                };
            }

            // Ajuste de compatibilidade — aceita access_token OU token
            const token = data.access_token || data.token;
            if (!token) {
                console.error('Token não recebido:', data);
                return { success: false, message: 'Token não recebido do servidor' };
            }
            
            // Armazenar dados
            localStorage.setItem('auth_token', token);
            if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
            }
            
            // CORREÇÃO: Garantir que o perfil seja armazenado corretamente
            const usuario = data.usuario || {};
            // Normalizar o campo perfil/tipo
            if (!usuario.perfil && usuario.tipo) {
                usuario.perfil = usuario.tipo;
            }
            
            localStorage.setItem('usuario_atual', JSON.stringify(usuario));
            
            console.log('Login bem-sucedido:', usuario);
            return { success: true, usuario: usuario };
            
        } catch (e) {
            console.error('Erro no login:', e);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    },

    // Renovar access_token usando refresh_token (opcional)
    async refresh() {
        const refresh = localStorage.getItem('refresh_token');
        if (!refresh) return false;

        try {
            const resp = await fetch('/api/auth/refresh', { 
                method: 'POST', 
                headers: this.getHeaders(),
                credentials: 'include'
            });
            const data = await resp.json();
            if (resp.ok && data.access_token) {
                localStorage.setItem('auth_token', data.access_token);
                return true;
            }
        } catch (e) {
            console.error('Erro ao renovar token:', e);
        }
        return false;
    },

    // Logout
    async logout() {
        try { 
            await fetch('/api/auth/logout', { 
                method: 'POST', 
                headers: this.getHeaders(),
                credentials: 'include'
            }); 
        } catch (e) {
            console.error('Erro no logout:', e);
        }
        
        // Limpar dados locais
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('usuario_atual');
        
        // Redirecionar para página apropriada
        window.location.href = '/static/index.html';
    },

    // Guard simples por perfil
    temPermissao(perfil) {
        const u = this.getUsuario();
        // CORREÇÃO: Verificar tanto 'perfil' quanto 'tipo'
        return u && (u.perfil === perfil || u.tipo === perfil);
    },

    // Exigir login na página
    requireAuth() {
        if (this.isAuthenticated()) return true;
        alert('Você precisa fazer login.');
        
        // Redirecionar para página de login apropriada
        const path = window.location.pathname;
        if (path.includes('fornecedor')) {
            window.location.href = '/static/sistema-autenticacao-fornecedores.html';
        } else {
            window.location.href = '/static/index.html';
        }
        return false;
    },

    // NOVA FUNÇÃO: Obter perfil normalizado
    getPerfil() {
        const u = this.getUsuario();
        return u ? (u.perfil || u.tipo || 'unknown') : null;
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
        'analise-propostas.html',
        'selecionar-fornecedores.html'
    ];

    // Verificar se está em página protegida
    if (paginasProtegidas.includes(path) && !Auth.requireAuth()) return;

    // Nome do usuário no topo, se existir
    const el = document.getElementById('usuario-nome');
    if (el && Auth.isAuthenticated()) {
        const u = Auth.getUsuario();
        el.textContent = u?.nome || 'Usuário';
    }

    // Botão de logout
    const btnLogout = document.getElementById('logout-btn');
    if (btnLogout) {
        btnLogout.addEventListener('click', e => { 
            e.preventDefault(); 
            if (confirm('Deseja realmente sair?')) {
                Auth.logout(); 
            }
        });
    }
});

// Expor global (para páginas chamarem)
window.Auth = Auth;
