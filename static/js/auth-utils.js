/**
 * Utilitários de Autenticação RBAC
 * Sistema de Propostas v2.0
 * 
 * Funções auxiliares para gerenciar autenticação JWT e controle de permissões
 */

class AuthUtils {
    constructor() {
        this.baseUrl = window.location.origin;
        this.tokenKey = 'access_token';
        this.refreshTokenKey = 'refresh_token';
        this.userDataKey = 'user_data';
        this.tokenRefreshInterval = null;
        
        // Inicializar verificação automática de token
        this.initTokenRefresh();
    }

    /**
     * Verificar se o usuário está autenticado
     * @returns {boolean}
     */
    isAuthenticated() {
        const token = this.getToken();
        const userData = this.getUserData();
        
        if (!token || !userData) {
            return false;
        }
        
        // Verificar se o token não expirou
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const now = Math.floor(Date.now() / 1000);
            
            if (payload.exp && payload.exp < now) {
                console.log('Token expirado');
                this.logout();
                return false;
            }
            
            return true;
        } catch (error) {
            console.error('Erro ao verificar token:', error);
            this.logout();
            return false;
        }
    }

    /**
     * Obter token de acesso
     * @returns {string|null}
     */
    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    /**
     * Obter token de refresh
     * @returns {string|null}
     */
    getRefreshToken() {
        return localStorage.getItem(this.refreshTokenKey);
    }

    /**
     * Obter dados do usuário
     * @returns {object|null}
     */
    getUserData() {
        try {
            const userData = localStorage.getItem(this.userDataKey);
            return userData ? JSON.parse(userData) : null;
        } catch (error) {
            console.error('Erro ao obter dados do usuário:', error);
            return null;
        }
    }

    /**
     * Salvar dados de autenticação
     * @param {string} accessToken 
     * @param {string} refreshToken 
     * @param {object} userData 
     */
    saveAuthData(accessToken, refreshToken, userData) {
        localStorage.setItem(this.tokenKey, accessToken);
        localStorage.setItem(this.refreshTokenKey, refreshToken);
        localStorage.setItem(this.userDataKey, JSON.stringify(userData));
    }

    /**
     * Verificar se o usuário tem uma permissão específica
     * @param {string} permission 
     * @returns {boolean}
     */
    hasPermission(permission) {
        const userData = this.getUserData();
        
        if (!userData || !userData.permissions) {
            return false;
        }
        
        return userData.permissions.includes(permission);
    }

    /**
     * Verificar se o usuário tem um role específico
     * @param {string} role 
     * @returns {boolean}
     */
    hasRole(role) {
        const userData = this.getUserData();
        
        if (!userData || !userData.roles) {
            return false;
        }
        
        return userData.roles.includes(role);
    }

    /**
     * Obter role primário do usuário
     * @returns {string|null}
     */
    getPrimaryRole() {
        const userData = this.getUserData();
        return userData ? userData.primary_role : null;
    }

    /**
     * Fazer requisição autenticada
     * @param {string} url 
     * @param {object} options 
     * @returns {Promise<Response>}
     */
    async authenticatedFetch(url, options = {}) {
        const token = this.getToken();
        
        if (!token) {
            throw new Error('Token de acesso não encontrado');
        }
        
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...options.headers
        };
        
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        // Se token expirou, tentar renovar
        if (response.status === 401) {
            const refreshed = await this.refreshToken();
            
            if (refreshed) {
                // Tentar novamente com novo token
                headers['Authorization'] = `Bearer ${this.getToken()}`;
                return fetch(url, { ...options, headers });
            } else {
                // Refresh falhou, fazer logout
                this.logout();
                throw new Error('Sessão expirada. Faça login novamente.');
            }
        }
        
        return response;
    }

    /**
     * Renovar token de acesso
     * @returns {Promise<boolean>}
     */
    async refreshToken() {
        const refreshToken = this.getRefreshToken();
        
        if (!refreshToken) {
            return false;
        }
        
        try {
            const response = await fetch(`${this.baseUrl}/api/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            
            const result = await response.json();
            
            if (result.success && result.access_token) {
                localStorage.setItem(this.tokenKey, result.access_token);
                
                // Atualizar dados do usuário se fornecidos
                if (result.user) {
                    localStorage.setItem(this.userDataKey, JSON.stringify(result.user));
                }
                
                return true;
            }
            
            return false;
        } catch (error) {
            console.error('Erro ao renovar token:', error);
            return false;
        }
    }

    /**
     * Fazer logout
     */
    async logout() {
        const token = this.getToken();
        
        // Tentar invalidar token no servidor
        if (token) {
            try {
                await fetch(`${this.baseUrl}/api/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
            } catch (error) {
                console.error('Erro ao fazer logout no servidor:', error);
            }
        }
        
        // Limpar dados locais
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.refreshTokenKey);
        localStorage.removeItem(this.userDataKey);
        
        // Parar renovação automática
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval);
        }
        
        // Redirecionar para login
        window.location.href = '/login.html';
    }

    /**
     * Inicializar renovação automática de token
     */
    initTokenRefresh() {
        // Verificar e renovar token a cada 10 minutos
        this.tokenRefreshInterval = setInterval(async () => {
            if (this.isAuthenticated()) {
                const token = this.getToken();
                
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    const now = Math.floor(Date.now() / 1000);
                    const timeToExpiry = payload.exp - now;
                    
                    // Se o token expira em menos de 5 minutos, renovar
                    if (timeToExpiry < 300) {
                        await this.refreshToken();
                    }
                } catch (error) {
                    console.error('Erro na verificação automática de token:', error);
                }
            }
        }, 600000); // 10 minutos
    }

    /**
     * Redirecionar baseado no role do usuário
     */
    redirectByRole() {
        const userData = this.getUserData();
        
        if (!userData) {
            window.location.href = '/login.html';
            return;
        }
        
        const primaryRole = userData.primary_role;
        
        const roleRedirects = {
            'SUPER_ADMIN': '/admin/dashboard',
            'ADMIN_COMPRADOR': '/dashboard-comprador-funcional.html',
            'ADMIN_REQUISITANTE': '/dashboard-requisitante-integrado.html',
            'COMPRADOR_SENIOR': '/dashboard-comprador-funcional.html',
            'COMPRADOR_JUNIOR': '/dashboard-comprador-funcional.html',
            'REQUISITANTE_SENIOR': '/dashboard-requisitante-integrado.html',
            'REQUISITANTE_JUNIOR': '/dashboard-requisitante-funcional.html',
            'FORNECEDOR_PREMIUM': '/dashboard-fornecedor-funcional.html',
            'FORNECEDOR_BASICO': '/dashboard-fornecedor-funcional.html'
        };
        
        const redirectUrl = roleRedirects[primaryRole] || '/index.html';
        window.location.href = redirectUrl;
    }

    /**
     * Proteger página - verificar autenticação e permissões
     * @param {string|array} requiredPermissions 
     * @param {string} redirectUrl 
     */
    protectPage(requiredPermissions = null, redirectUrl = '/login.html') {
        if (!this.isAuthenticated()) {
            window.location.href = redirectUrl;
            return false;
        }
        
        if (requiredPermissions) {
            const permissions = Array.isArray(requiredPermissions) 
                ? requiredPermissions 
                : [requiredPermissions];
            
            const hasAllPermissions = permissions.every(permission => 
                this.hasPermission(permission)
            );
            
            if (!hasAllPermissions) {
                alert('Você não tem permissão para acessar esta página.');
                this.redirectByRole();
                return false;
            }
        }
        
        return true;
    }

    /**
     * Mostrar/esconder elementos baseado em permissões
     * @param {string} selector 
     * @param {string|array} requiredPermissions 
     */
    toggleElementsByPermission(selector, requiredPermissions) {
        const elements = document.querySelectorAll(selector);
        const permissions = Array.isArray(requiredPermissions) 
            ? requiredPermissions 
            : [requiredPermissions];
        
        const hasPermission = permissions.some(permission => 
            this.hasPermission(permission)
        );
        
        elements.forEach(element => {
            element.style.display = hasPermission ? '' : 'none';
        });
    }

    /**
     * Obter informações do usuário para exibição
     * @returns {object}
     */
    getUserDisplayInfo() {
        const userData = this.getUserData();
        
        if (!userData) {
            return null;
        }
        
        return {
            nome: userData.nome,
            email: userData.email,
            role: userData.primary_role,
            roles: userData.roles,
            permissions: userData.permissions,
            avatar: userData.avatar || null
        };
    }

    /**
     * Verificar se a sessão está próxima do vencimento
     * @returns {boolean}
     */
    isSessionNearExpiry() {
        const token = this.getToken();
        
        if (!token) {
            return true;
        }
        
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const now = Math.floor(Date.now() / 1000);
            const timeToExpiry = payload.exp - now;
            
            // Considera próximo do vencimento se restam menos de 10 minutos
            return timeToExpiry < 600;
        } catch (error) {
            return true;
        }
    }
}

// Instância global
const authUtils = new AuthUtils();

// Funções de conveniência globais
window.isAuthenticated = () => authUtils.isAuthenticated();
window.hasPermission = (permission) => authUtils.hasPermission(permission);
window.hasRole = (role) => authUtils.hasRole(role);
window.logout = () => authUtils.logout();
window.protectPage = (permissions, redirectUrl) => authUtils.protectPage(permissions, redirectUrl);
window.getUserData = () => authUtils.getUserData();
window.authenticatedFetch = (url, options) => authUtils.authenticatedFetch(url, options);

// Auto-inicialização quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se está em página de login
    if (window.location.pathname.includes('login')) {
        return;
    }
    
    // Para outras páginas, verificar autenticação
    if (!authUtils.isAuthenticated()) {
        console.log('Usuário não autenticado, redirecionando para login...');
        window.location.href = '/login.html';
        return;
    }
    
    // Atualizar interface com dados do usuário
    const userInfo = authUtils.getUserDisplayInfo();
    
    if (userInfo) {
        // Atualizar elementos com dados do usuário
        const userNameElements = document.querySelectorAll('[data-user-name]');
        const userEmailElements = document.querySelectorAll('[data-user-email]');
        const userRoleElements = document.querySelectorAll('[data-user-role]');
        
        userNameElements.forEach(el => el.textContent = userInfo.nome);
        userEmailElements.forEach(el => el.textContent = userInfo.email);
        userRoleElements.forEach(el => el.textContent = userInfo.role);
    }
    
    // Configurar botões de logout
    const logoutButtons = document.querySelectorAll('[data-logout]');
    logoutButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Tem certeza que deseja sair?')) {
                authUtils.logout();
            }
        });
    });
    
    // Avisar se sessão está próxima do vencimento
    if (authUtils.isSessionNearExpiry()) {
        console.warn('Sessão próxima do vencimento');
        
        // Mostrar aviso se elemento existir
        const sessionWarning = document.getElementById('session-warning');
        if (sessionWarning) {
            sessionWarning.style.display = 'block';
        }
    }
});

// Exportar para uso em módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthUtils;
}

