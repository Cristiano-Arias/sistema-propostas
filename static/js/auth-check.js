// auth-check.js - Verificação de autenticação centralizada para dashboards
import { firebaseConfig, SESSION_KEYS, DASHBOARD_ROUTES } from './firebase-config.js';
import { getCurrentUser } from './auth-facade.js';

/**
 * Verifica se o usuário está autenticado e tem permissão para acessar o dashboard
 * @param {string} requiredProfile - Perfil necessário para acessar a página
 * @param {boolean} redirectOnFail - Se deve redirecionar em caso de falha (padrão: true)
 * @returns {Object} - { isAuthenticated: boolean, user: Object|null, error: string|null }
 */
export async function checkAuthentication(requiredProfile = null, redirectOnFail = true) {
    try {
        console.log('🔐 Verificando autenticação para perfil:', requiredProfile);
        
        // Verificar se há usuário autenticado
        const currentUser = await getCurrentUser();
        
        if (!currentUser) {
            console.log('❌ Usuário não autenticado');
            if (redirectOnFail) {
                redirectToLogin('Sessão expirada. Faça login novamente.');
            }
            return { isAuthenticated: false, user: null, error: 'Usuário não autenticado' };
        }
        
        // Verificar se o perfil é necessário e se o usuário tem permissão
        if (requiredProfile) {
            const normalizedRequired = requiredProfile.toLowerCase();
            const normalizedCurrent = (currentUser.profile || '').toLowerCase();
            
            if (normalizedCurrent !== normalizedRequired) {
                console.log('❌ Perfil não autorizado:', {
                    required: requiredProfile,
                    current: currentUser.profile,
                    normalizedRequired,
                    normalizedCurrent
                });
                
                if (redirectOnFail) {
                    redirectToCorrectDashboard(currentUser.profile);
                }
                
                return { 
                    isAuthenticated: false, 
                    user: currentUser, 
                    error: `Acesso negado. Perfil necessário: ${requiredProfile}` 
                };
            }
        }
        
        // Atualizar última atividade
        updateLastActivity();
        
        console.log('✅ Usuário autenticado:', {
            email: currentUser.email,
            profile: currentUser.profile
        });
        
        return { isAuthenticated: true, user: currentUser, error: null };
        
    } catch (error) {
        console.error('❌ Erro na verificação de autenticação:', error);
        
        if (redirectOnFail) {
            redirectToLogin('Erro na verificação de autenticação.');
        }
        
        return { isAuthenticated: false, user: null, error: error.message };
    }
}

/**
 * Redireciona para a página de login com mensagem opcional
 * @param {string} message - Mensagem a ser exibida
 */
export function redirectToLogin(message = null) {
    console.log('🔄 Redirecionando para login:', message);
    
    // Limpar sessão antes de redirecionar
    clearUserSession();
    
    // Construir URL com mensagem se fornecida
    let loginUrl = '/static/portal-unico-inteligente.html';
    if (message) {
        loginUrl += `?message=${encodeURIComponent(message)}`;
    }
    
    window.location.href = loginUrl;
}

/**
 * Redireciona para o dashboard correto baseado no perfil do usuário
 * @param {string} userProfile - Perfil do usuário
 */
export function redirectToCorrectDashboard(userProfile) {
    const dashboardUrl = DASHBOARD_ROUTES[userProfile];
    
    if (dashboardUrl) {
        console.log('🔄 Redirecionando para dashboard correto:', {
            profile: userProfile,
            url: dashboardUrl
        });
        window.location.href = dashboardUrl;
    } else {
        console.error('❌ Dashboard não encontrado para perfil:', userProfile);
        redirectToLogin('Perfil de usuário inválido.');
    }
}

/**
 * Atualiza a última atividade do usuário
 */
function updateLastActivity() {
    try {
        const userData = localStorage.getItem(SESSION_KEYS.USER_DATA);
        if (userData) {
            const user = JSON.parse(userData);
            user.lastActivity = new Date().toISOString();
            localStorage.setItem(SESSION_KEYS.USER_DATA, JSON.stringify(user));
            sessionStorage.setItem(SESSION_KEYS.USER_DATA, JSON.stringify(user));
        }
    } catch (error) {
        console.error('❌ Erro ao atualizar atividade:', error);
    }
}

/**
 * Limpa todas as sessões do usuário
 */
function clearUserSession() {
    try {
        // Limpar localStorage
        Object.values(SESSION_KEYS).forEach(key => {
            localStorage.removeItem(key);
        });
        
        // Limpar chaves de compatibilidade
        ['user', 'userToken', 'userData', 'authToken'].forEach(key => {
            localStorage.removeItem(key);
        });
        
        // Limpar sessionStorage
        Object.values(SESSION_KEYS).forEach(key => {
            sessionStorage.removeItem(key);
        });
        
        console.log('🧹 Sessão limpa completamente');
    } catch (error) {
        console.error('❌ Erro ao limpar sessão:', error);
    }
}

/**
 * Inicializa a verificação de autenticação para uma página
 * @param {string} requiredProfile - Perfil necessário
 * @param {Function} onSuccess - Callback executado quando autenticação é bem-sucedida
 * @param {Function} onError - Callback executado quando há erro
 */
export async function initializeAuthCheck(requiredProfile, onSuccess = null, onError = null) {
    try {
        const authResult = await checkAuthentication(requiredProfile, true);
        
        if (authResult.isAuthenticated) {
            console.log('✅ Autenticação inicializada com sucesso');
            if (onSuccess) {
                onSuccess(authResult.user);
            }
        } else {
            console.log('❌ Falha na inicialização da autenticação');
            if (onError) {
                onError(authResult.error);
            }
        }
        
        return authResult;
        
    } catch (error) {
        console.error('❌ Erro na inicialização da verificação de autenticação:', error);
        if (onError) {
            onError(error.message);
        }
        return { isAuthenticated: false, user: null, error: error.message };
    }
}

/**
 * Monitora mudanças na autenticação e redireciona se necessário
 */
export function startAuthMonitoring() {
    // Verificar autenticação a cada 5 minutos
    setInterval(async () => {
        const authResult = await checkAuthentication(null, false);
        if (!authResult.isAuthenticated) {
            redirectToLogin('Sessão expirada.');
        }
    }, 5 * 60 * 1000); // 5 minutos
    
    console.log('👁️ Monitoramento de autenticação iniciado');
}

// Exportar funções principais
export default {
    checkAuthentication,
    redirectToLogin,
    redirectToCorrectDashboard,
    initializeAuthCheck,
    startAuthMonitoring
};