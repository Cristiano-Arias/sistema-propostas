// firebase.js - Configuração Firebase centralizada e otimizada
import { firebaseConfig, AUTH_CONFIG, SESSION_KEYS } from "./js/firebase-config.js";
import { initializeApp, getApps, getApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { 
    getAuth, 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword, 
    onAuthStateChanged, 
    signOut,
    sendPasswordResetEmail
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

// Initialize Firebase com proteção contra duplicação
const app = getApps().length ? getApp() : initializeApp(firebaseConfig);
const auth = getAuth(app);

// Log de inicialização
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    console.log('🔥 Firebase principal inicializado:', {
        projectId: firebaseConfig.projectId,
        apps: getApps().length
    });
}

// Estado global do usuário
let currentUser = null;
let userToken = null;

// Funções auxiliares de persistência de sessão
function persistUserSession(userData) {
    try {
        // Salvar em localStorage para persistência
        localStorage.setItem(SESSION_KEYS.USER_DATA, JSON.stringify(userData));
        localStorage.setItem(SESSION_KEYS.AUTH_TOKEN, userData.token);
        localStorage.setItem('user', JSON.stringify(userData)); // Compatibilidade
        localStorage.setItem('userToken', userData.token); // Compatibilidade
        
        // Salvar em sessionStorage para sessão atual
        sessionStorage.setItem(SESSION_KEYS.USER_DATA, JSON.stringify(userData));
        sessionStorage.setItem(SESSION_KEYS.AUTH_TOKEN, userData.token);
        
        // Atualizar atividade
        updateLastActivity();
        
        console.log('✅ Sessão persistida para perfil:', userData.profile);
    } catch (error) {
        console.error('❌ Erro ao persistir sessão:', error);
    }
}

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

function getCurrentUserData() {
    try {
        const userData = localStorage.getItem(SESSION_KEYS.USER_DATA) || 
                        localStorage.getItem('userData'); // Compatibilidade
        return userData ? JSON.parse(userData) : null;
    } catch (error) {
        console.error('❌ Erro ao obter dados do usuário:', error);
        return null;
    }
}

function updateLastActivity() {
    try {
        const userData = getCurrentUserData();
        if (userData) {
            userData.lastActivity = new Date().toISOString();
            localStorage.setItem(SESSION_KEYS.USER_DATA, JSON.stringify(userData));
            sessionStorage.setItem(SESSION_KEYS.USER_DATA, JSON.stringify(userData));
        }
    } catch (error) {
        console.error('❌ Erro ao atualizar atividade:', error);
    }
}

// ==================== FUNÇÕES DE AUTENTICAÇÃO ====================

/**
 * Fazer login com email e senha com persistência de sessão adequada
 */
async function login(email, password, userProfile = null) {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        
        // Obter token
        const token = await user.getIdToken();
        
        // Verificar com backend
        const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:5000' : '';
        const response = await fetch(`${apiUrl}/auth/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ uid: user.uid })
        });
        
        if (response.ok) {
            const userData = await response.json();
            
            // Normalizar perfil do usuário
            const normalizedProfile = userProfile || userData.profile || 'requisitante';
            
            // Criar dados completos do usuário
            const completeUserData = {
                uid: user.uid,
                email: user.email,
                token: token,
                profile: normalizedProfile,
                loginTime: new Date().toISOString(),
                lastActivity: new Date().toISOString(),
                ...userData
            };
            
            currentUser = completeUserData;
            userToken = token;
            
            // Persistir sessão usando chaves padronizadas
            localStorage.setItem('userToken', token);
            localStorage.setItem('userData', JSON.stringify(completeUserData));
            localStorage.setItem('user', JSON.stringify(completeUserData));
            localStorage.setItem('authToken', token);
            
            return { success: true, user: completeUserData };
        } else {
            const error = await response.json();
            throw new Error(error.erro || 'Erro na autenticação');
        }
    } catch (error) {
        console.error('Erro no login:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Fazer logout com limpeza completa de sessão
 */
async function logout() {
    try {
        await signOut(auth);
        
        // Limpar todas as sessões
        currentUser = null;
        userToken = null;
        
        // Limpar localStorage completamente
        localStorage.removeItem('userToken');
        localStorage.removeItem('userData');
        localStorage.removeItem('user');
        localStorage.removeItem('authToken');
        
        // Redirecionar para página de login
         window.location.href = '/static/portal_login_simples.html';
        
        return { success: true };
    } catch (error) {
        console.error('Erro no logout:', error);
        // Mesmo com erro, limpar sessões locais
        currentUser = null;
        userToken = null;
        localStorage.removeItem('userToken');
        localStorage.removeItem('userData');
        localStorage.removeItem('user');
        localStorage.removeItem('authToken');
        return { success: false, error: error.message };
    }
}

/**
 * Registrar novo usuário (apenas cria no Firebase Auth)
 */
async function register(email, password, nome) {
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        
        // Atualizar perfil
        await user.updateProfile({
            displayName: nome
        });
        
        // Fazer login automático
        return await login(email, password);
    } catch (error) {
        console.error('Erro no registro:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Resetar senha
 */
async function resetPassword(email) {
    try {
        await sendPasswordResetEmail(auth, email);
        return { success: true };
    } catch (error) {
        console.error('Erro ao resetar senha:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Verificar se usuário está logado com validação de token
 */
function isLoggedIn() {
    try {
        const userData = localStorage.getItem('userData');
        const token = localStorage.getItem('userToken');
        
        if (!userData || !token) {
            return false;
        }
        
        const parsedUserData = JSON.parse(userData);
        
        // Verificar se o token não expirou (tokens Firebase duram 1 hora)
        const loginTime = new Date(parsedUserData.loginTime || parsedUserData.lastActivity);
        const now = new Date();
        const hoursSinceLogin = (now - loginTime) / (1000 * 60 * 60);
        
        if (hoursSinceLogin > 1) { // 1 hora de expiração
            // Token expirado, limpar sessão
            localStorage.removeItem('userToken');
            localStorage.removeItem('userData');
            localStorage.removeItem('user');
            localStorage.removeItem('authToken');
            currentUser = null;
            userToken = null;
            return false;
        }
        
        return currentUser !== null && userToken !== null;
    } catch (error) {
        console.error('Erro ao verificar login:', error);
        return false;
    }
}

/**
 * Obter dados do usuário atual
 */
function getCurrentUser() {
    return currentUser;
}

/**
 * Obter token do usuário atual
 */
function getUserToken() {
    return userToken;
}

// ==================== FUNÇÕES DE API ====================

/**
 * Fazer requisição autenticada para API
 */
async function apiRequest(url, options = {}) {
    const token = getUserToken();
    
    if (!token) {
        throw new Error('Usuário não autenticado');
    }
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };
    
    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, finalOptions);
        
        if (response.status === 401) {
            // Token expirado, fazer logout
            await logout();
            throw new Error('Sessão expirada');
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.erro || 'Erro na requisição');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Erro na API:', error);
        throw error;
    }
}

// ==================== INICIALIZAÇÃO ====================

/**
 * Inicializar sistema de autenticação
 */
function initAuth() {
    // Verificar se há dados salvos
    const savedToken = localStorage.getItem('userToken');
    const savedUserData = localStorage.getItem('userData');
    
    if (savedToken && savedUserData) {
        try {
            userToken = savedToken;
            currentUser = JSON.parse(savedUserData);
        } catch (error) {
            console.error('Erro ao carregar dados salvos:', error);
            localStorage.removeItem('userToken');
            localStorage.removeItem('userData');
        }
    }
    
    // Monitorar mudanças de autenticação
    onAuthStateChanged(auth, async (user) => {
        if (user && !currentUser) {
            // Usuário logado mas não temos dados locais
            try {
                const token = await user.getIdToken();
                const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:5000' : '';
                const response = await fetch(`${apiUrl}/auth/verify`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ token })
                });
                
                if (response.ok) {
                    const userData = await response.json();
                    currentUser = userData;
                    userToken = token;
                    
                    localStorage.setItem('userToken', token);
                    localStorage.setItem('userData', JSON.stringify(userData));
                }
            } catch (error) {
                console.error('Erro ao verificar usuário:', error);
            }
        } else if (!user && currentUser) {
            // Usuário deslogado
            currentUser = null;
            userToken = null;
            localStorage.removeItem('userToken');
            localStorage.removeItem('userData');
        }
    });
}

// ==================== UTILITÁRIOS ====================

/**
 * Verificar se usuário tem permissão
 */
function hasPermission(requiredRole) {
    if (!currentUser) return false;
    
    const userRole = currentUser.perfil;
    
    // Admin tem acesso a tudo
    if (userRole === 'ADMIN') return true;
    
    // Verificar permissão específica
    switch (requiredRole) {
        case 'requisitante':
            return ['requisitante', 'comprador'].includes(userRole);
        case 'comprador':
            return userRole === 'comprador';
        case 'fornecedor':
            return userRole === 'fornecedor';
        default:
            return false;
    }
}

/**
 * Redirecionar se não autenticado
 */
function requireAuth(redirectTo = '/') {
    if (!isLoggedIn()) {
        window.location.href = redirectTo;
        return false;
    }
    return true;
}

/**
 * Redirecionar se não tem permissão
 */
function requirePermission(role, redirectTo = '/') {
    if (!requireAuth(redirectTo)) return false;
    
    if (!hasPermission(role)) {
        alert('Você não tem permissão para acessar esta página');
        window.location.href = redirectTo;
        return false;
    }
    return true;
}

// ==================== EXPORTAÇÕES ====================

// Inicializar ao carregar
document.addEventListener('DOMContentLoaded', initAuth);

// Exportar para uso global
window.FirebaseAuth = {
    login,
    logout,
    register,
    resetPassword,
    isLoggedIn,
    getCurrentUser,
    getUserToken,
    apiRequest,
    hasPermission,
    requireAuth,
    requirePermission,
    initAuth
};

// Exportar funções individuais
export {
    login,
    logout,
    register,
    resetPassword,
    isLoggedIn,
    getCurrentUser,
    getUserToken,
    apiRequest,
    hasPermission,
    requireAuth,
    requirePermission,
    initAuth
};
