/**
 * Sistema de Autenticação Frontend
 * Gerencia login, logout e permissões
 */

const Auth = {
    // Verificar se usuário está autenticado
    isAuthenticated() {
        const token = localStorage.getItem('auth_token');
        const usuario = localStorage.getItem('usuario_atual');
        
        if (!token || !usuario) return false;
        
        // Verificar se token não expirou
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

    // Obter token
    getToken() {
        return localStorage.getItem('auth_token');
    },

    // Login
    async login(email, senha) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, senha })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('usuario_atual', JSON.stringify(data.usuario));
                return { success: true, usuario: data.usuario };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            console.error('Erro no login:', error);
            return { success: false, message: 'Erro de conexão' };
        }
    },

    // Logout
    logout() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('usuario_atual');
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

    // Adicionar token aos headers
    getHeaders() {
        const token = this.getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        };
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
        const perfil = document.getElementById('perfil').value;

        // Primeiro tenta login no backend
        const result = await Auth.login(email, senha);
        
        if (result.success) {
            // Login bem-sucedido via API
            switch(result.usuario.perfil) {
                case 'requisitante':
                    window.location.href = 'dashboard-requisitante.html';
                    break;
                case 'comprador':
                    window.location.href = 'dashboard-comprador.html';
                    break;
                case 'fornecedor':
                    window.location.href = 'dashboard-fornecedor.html';
                    break;
            }
        } else {
            // Fallback para login local (mantém compatibilidade)
            const usuarios = JSON.parse(localStorage.getItem('usuarios') || '[]');
            const usuario = usuarios.find(u => 
                u.email === email && 
                u.senha === senha && 
                u.perfil === perfil
            );

            if (usuario) {
                localStorage.setItem('usuario_atual', JSON.stringify(usuario));
                
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
                }
            } else {
                alert('Email, senha ou perfil incorretos!');
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