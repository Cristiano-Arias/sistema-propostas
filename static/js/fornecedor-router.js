// fornecedor-router.js - Sistema de roteamento inteligente para fornecedores
import { auth, onAuthStateChanged } from './firebase.js';

/**
 * Sistema de roteamento inteligente para fornecedores
 * Detecta perfil do usuário e redireciona automaticamente
 */
export class FornecedorRouter {
    constructor() {
        this.currentUser = null;
        this.initializeRouter();
    }

    /**
     * Inicializa o sistema de roteamento
     */
    initializeRouter() {
        // Verificar se já existe sessão ativa
        this.checkExistingSession();
        
        // Monitorar mudanças de autenticação
        onAuthStateChanged(auth, (user) => {
            this.currentUser = user;
            if (user) {
                this.handleAuthenticatedUser(user);
            }
        });
    }

    /**
     * Verifica se existe sessão ativa no sistema legado
     */
    checkExistingSession() {
        const fornecedorLogado = localStorage.getItem('fornecedor_logado');
        const requisitanteLogado = localStorage.getItem('requisitante_logado');
        const compradorLogado = localStorage.getItem('comprador_logado');
        const adminLogado = localStorage.getItem('admin_logado');

        // Se fornecedor já está logado, redirecionar para dashboard
        if (fornecedorLogado) {
            try {
                const userData = JSON.parse(fornecedorLogado);
                if (userData && userData.perfil === 'Fornecedor') {
                    this.redirectToFornecedorDashboard();
                    return true;
                }
            } catch (e) {
                console.warn('Erro ao verificar sessão de fornecedor:', e);
            }
        }

        // Se outro perfil está logado, redirecionar para portal unificado
        if (requisitanteLogado || compradorLogado || adminLogado) {
            this.redirectToPortalUnificado();
            return true;
        }

        return false;
    }

    /**
     * Processa usuário autenticado e determina redirecionamento
     */
    async handleAuthenticatedUser(user) {
        try {
            // Buscar perfil do usuário no backend
            const perfil = await this.getUserProfile(user);
            
            if (perfil === 'Fornecedor') {
                this.setupFornecedorSession(user, perfil);
                this.redirectToFornecedorDashboard();
            } else {
                this.setupGeneralSession(user, perfil);
                this.redirectToPortalUnificado();
            }
        } catch (error) {
            console.error('Erro ao processar usuário autenticado:', error);
            // Em caso de erro, assumir fornecedor se estiver na página de fornecedor
            if (this.isOnFornecedorPage()) {
                this.setupFornecedorSession(user, 'Fornecedor');
                this.redirectToFornecedorDashboard();
            } else {
                this.redirectToPortalUnificado();
            }
        }
    }

    /**
     * Busca perfil do usuário no backend
     */
    async getUserProfile(user) {
        try {
            const response = await fetch('/api/user-profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${await user.getIdToken()}`
                },
                body: JSON.stringify({ email: user.email })
            });

            if (response.ok) {
                const data = await response.json();
                return data.perfil || 'Fornecedor';
            }
        } catch (error) {
            console.warn('Erro ao buscar perfil do usuário:', error);
        }

        // Fallback: assumir fornecedor se estiver na página de fornecedor
        return this.isOnFornecedorPage() ? 'Fornecedor' : 'Requisitante';
    }

    /**
     * Configura sessão para fornecedor
     */
    setupFornecedorSession(user, perfil) {
        const sessionData = {
            email: user.email,
            uid: user.uid,
            perfil: perfil,
            dataLogin: new Date().toISOString()
        };

        localStorage.setItem('fornecedor_logado', JSON.stringify(sessionData));
        localStorage.setItem('userToken', user.accessToken);
        localStorage.setItem('userData', JSON.stringify(sessionData));
    }

    /**
     * Configura sessão geral (não-fornecedor)
     */
    setupGeneralSession(user, perfil) {
        const sessionData = {
            email: user.email,
            uid: user.uid,
            perfil: perfil,
            dataLogin: new Date().toISOString()
        };

        // Salvar na chave apropriada baseada no perfil
        const perfilLower = perfil.toLowerCase();
        if (perfilLower.includes('requisitante')) {
            localStorage.setItem('requisitante_logado', JSON.stringify(sessionData));
        } else if (perfilLower.includes('comprador')) {
            localStorage.setItem('comprador_logado', JSON.stringify(sessionData));
        } else if (perfilLower.includes('admin')) {
            localStorage.setItem('admin_logado', JSON.stringify(sessionData));
        }

        localStorage.setItem('userToken', user.accessToken);
        localStorage.setItem('userData', JSON.stringify(sessionData));
    }

    /**
     * Verifica se está em página relacionada a fornecedor
     */
    isOnFornecedorPage() {
        const currentPage = window.location.pathname;
        return currentPage.includes('fornecedor') || 
               currentPage.includes('sistema-autenticacao-fornecedores') ||
               currentPage.includes('portal-fornecedor');
    }

    /**
     * Redireciona para dashboard do fornecedor
     */
    redirectToFornecedorDashboard() {
        if (window.location.pathname !== '/static/dashboard-fornecedor-funcional.html') {
            window.location.href = '/static/dashboard-fornecedor-funcional.html';
        }
    }

    /**
     * Redireciona para portal unificado
     */
    redirectToPortalUnificado() {
        if (window.location.pathname !== '/static/portal-unificado.html') {
            window.location.href = '/static/portal-unificado.html';
        }
    }

    /**
     * Realiza logout completo
     */
    async logout() {
        try {
            // Limpar todas as sessões
            localStorage.removeItem('fornecedor_logado');
            localStorage.removeItem('requisitante_logado');
            localStorage.removeItem('comprador_logado');
            localStorage.removeItem('admin_logado');
            localStorage.removeItem('userToken');
            localStorage.removeItem('userData');

            // Logout do Firebase
            if (auth.currentUser) {
                await auth.signOut();
            }

            // Redirecionar para página de login
            window.location.href = '/static/portal-fornecedor-unificado.html';
        } catch (error) {
            console.error('Erro no logout:', error);
            window.location.reload();
        }
    }
}

// Instância global do router
export const fornecedorRouter = new FornecedorRouter();

// Função de conveniência para logout
window.logoutFornecedor = () => fornecedorRouter.logout();

