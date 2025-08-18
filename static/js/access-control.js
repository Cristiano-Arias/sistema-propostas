// access-control.js - Sistema de Controle de Acesso Centralizado
// Compatível com Firebase e Sistema Legado

const AccessControl = {
    // Configuração de permissões por perfil
    permissions: {
        'admin': ['admin', 'requisitante', 'comprador', 'fornecedor'],
        'requisitante': ['requisitante'],
        'comprador': ['comprador'],
        'fornecedor': ['fornecedor']
    },

    // Verificar autenticação (Firebase + Legado)
    checkAuth: function() {
        // 1. Verificar Firebase primeiro
        const firebaseUser = this.getFirebaseUser();
        if (firebaseUser) {
            return {
                authenticated: true,
                type: 'firebase',
                user: firebaseUser
            };
        }

        // 2. Verificar sistema legado
        const legacyUser = this.getLegacyUser();
        if (legacyUser) {
            return {
                authenticated: true,
                type: 'legacy',
                user: legacyUser
            };
        }

        // 3. Não autenticado
        return {
            authenticated: false,
            type: null,
            user: null
        };
    },

    // Obter usuário Firebase
    getFirebaseUser: function() {
        try {
            const token = localStorage.getItem('userToken');
            const userData = localStorage.getItem('userData');
            
            if (token && userData) {
                return JSON.parse(userData);
            }
        } catch (error) {
            console.error('Erro ao obter usuário Firebase:', error);
        }
        return null;
    },

    // Obter usuário do sistema legado
    getLegacyUser: function() {
        // Verificar cada tipo de sessão legada
        const sessions = [
            { key: 'admin_logado', perfil: 'admin' },
            { key: 'requisitante_logado', perfil: 'requisitante' },
            { key: 'comprador_logado', perfil: 'comprador' },
            { key: 'fornecedor_logado', perfil: 'fornecedor' }
        ];

        for (const session of sessions) {
            try {
                const data = localStorage.getItem(session.key);
                if (data) {
                    const user = JSON.parse(data);
                    // Garantir que tem perfil
                    if (!user.perfil) {
                        user.perfil = session.perfil;
                    }
                    return user;
                }
            } catch (error) {
                console.error(`Erro ao ler ${session.key}:`, error);
            }
        }

        return null;
    },

    // Verificar se tem permissão para acessar módulo
    hasPermission: function(requiredModule) {
        const auth = this.checkAuth();
        
        if (!auth.authenticated) {
            return false;
        }

        const userProfile = auth.user.perfil?.toLowerCase() || 'requisitante';
        const allowedModules = this.permissions[userProfile] || [];
        
        return allowedModules.includes(requiredModule.toLowerCase());
    },

    // Validar acesso à página atual
    validatePageAccess: function(requiredModule) {
        const auth = this.checkAuth();
        
        // Não autenticado
        if (!auth.authenticated) {
            this.redirectToLogin();
            return false;
        }

        // Verificar permissão
        if (!this.hasPermission(requiredModule)) {
            this.showAccessDenied();
            return false;
        }

        // Acesso permitido
        return true;
    },

    // Redirecionar para login apropriado
    redirectToLogin: function() {
        // Verificar se existe portal unificado
        fetch('/static/portal-unificado.html', { method: 'HEAD' })
            .then(response => {
                if (response.ok) {
                    window.location.href = '/static/portal-unificado.html';
                } else {
                    // Fallback para index
                    window.location.href = '/static/index.html';
                }
            })
            .catch(() => {
                window.location.href = '/static/index.html';
            });
    },

    // Mostrar acesso negado
    showAccessDenied: function() {
        const auth = this.checkAuth();
        const userProfile = auth.user?.perfil || 'desconhecido';
        
        alert(`Acesso Negado!\n\nSeu perfil (${userProfile.toUpperCase()}) não tem permissão para acessar este módulo.\n\nVocê será redirecionado.`);
        
        // Redirecionar para módulo apropriado
        this.redirectToAllowedModule();
    },

    // Redirecionar para módulo permitido
    redirectToAllowedModule: function() {
        const auth = this.checkAuth();
        if (!auth.authenticated) {
            this.redirectToLogin();
            return;
        }

        const profile = auth.user.perfil?.toLowerCase() || 'requisitante';
        
        switch(profile) {
            case 'admin':
                window.location.href = '/static/admin-usuarios.html';
                break;
            case 'requisitante':
                window.location.href = '/static/dashboard-requisitante-funcional.html';
                break;
            case 'comprador':
                window.location.href = '/static/dashboard-comprador-funcional.html';
                break;
            case 'fornecedor':
                window.location.href = '/static/dashboard-fornecedor-funcional.html';
                break;
            default:
                this.redirectToLogin();
        }
    },

    // Obter informações do usuário atual
    getCurrentUser: function() {
        const auth = this.checkAuth();
        return auth.authenticated ? auth.user : null;
    },

    // Fazer logout
    logout: function() {
        // Limpar todas as possíveis sessões
        const keysToRemove = [
            'userToken',
            'userData',
            'admin_logado',
            'requisitante_logado',
            'comprador_logado',
            'fornecedor_logado'
        ];

        keysToRemove.forEach(key => localStorage.removeItem(key));

        // Redirecionar para login
        this.redirectToLogin();
    },

    // Inicializar proteção em uma página
    protectPage: function(requiredModule) {
        // Verificar acesso ao carregar a página
        document.addEventListener('DOMContentLoaded', () => {
            if (!this.validatePageAccess(requiredModule)) {
                return;
            }

            // Adicionar informações do usuário na página se existir elemento
            this.displayUserInfo();
        });
    },

    // Mostrar informações do usuário na página
    displayUserInfo: function() {
        const user = this.getCurrentUser();
        if (!user) return;

        // Procurar elementos comuns para exibir info
        const elements = {
            'user-name': user.nome || user.login || user.email?.split('@')[0] || 'Usuário',
            'user-email': user.email || '',
            'user-profile': user.perfil || 'requisitante',
            'user-avatar': (user.nome || user.email || 'U').charAt(0).toUpperCase()
        };

        Object.keys(elements).forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = elements[id];
            }
        });
    },

    // Função auxiliar para verificar compatibilidade
    checkCompatibility: function() {
        console.log('=== VERIFICAÇÃO DE COMPATIBILIDADE ===');
        
        // Verificar Firebase
        const firebaseUser = this.getFirebaseUser();
        console.log('Firebase:', firebaseUser ? '✅ Conectado' : '❌ Não conectado');
        
        // Verificar Sistema Legado
        const legacyUser = this.getLegacyUser();
        console.log('Sistema Legado:', legacyUser ? '✅ Ativo' : '❌ Inativo');
        
        // Verificar localStorage keys
        const keys = Object.keys(localStorage);
        console.log('Chaves no localStorage:', keys);
        
        // Verificar autenticação atual
        const auth = this.checkAuth();
        console.log('Autenticação:', auth);
        
        return {
            firebase: !!firebaseUser,
            legacy: !!legacyUser,
            authenticated: auth.authenticated,
            user: auth.user
        };
    }
};

// Exportar para uso global
if (typeof window !== 'undefined') {
    window.AccessControl = AccessControl;
}

// Exportar para módulos ES6
export default AccessControl;
