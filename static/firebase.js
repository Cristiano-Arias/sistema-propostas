// firebase_simplificado.js - Configuração Firebase otimizada
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { 
    getAuth, 
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword, 
    onAuthStateChanged, 
    signOut,
    sendPasswordResetEmail
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

// Configuração Firebase (suas credenciais)
const firebaseConfig = {
    apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
    authDomain: "portal-de-proposta.firebaseapp.com",
    projectId: "portal-de-proposta",
    storageBucket: "portal-de-proposta.firebasestorage.app",
    messagingSenderId: "321036073908",
    appId: "1:321036073908:web:3149b9ea2cb77a704890e1",
    measurementId: "G-CFFVQGM3EC"
};
// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Estado global do usuário
let currentUser = null;
let userToken = null;

// ==================== FUNÇÕES DE AUTENTICAÇÃO ====================

/**
 * Fazer login com email e senha
 */
async function login(email, password) {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        
        // Obter token
        const token = await user.getIdToken();
        
        // Verificar com backend
        const response = await fetch('/auth/verify', {
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
            
            // Salvar no localStorage
            localStorage.setItem('userToken', token);
            localStorage.setItem('userData', JSON.stringify(userData));
            
            return { success: true, user: userData };
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
 * Fazer logout
 */
async function logout() {
    try {
        await signOut(auth);
        currentUser = null;
        userToken = null;
        
        // Limpar localStorage
        localStorage.removeItem('userToken');
        localStorage.removeItem('userData');
        
        // Redirecionar para login
        window.location.href = '/';
        
        return { success: true };
    } catch (error) {
        console.error('Erro no logout:', error);
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
 * Verificar se usuário está logado
 */
function isLoggedIn() {
    return currentUser !== null && userToken !== null;
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
                const response = await fetch('/auth/verify', {
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
