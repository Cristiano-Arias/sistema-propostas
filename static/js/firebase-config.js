// firebase-config.js - Configuração Firebase Centralizada
// Versão única e padronizada para todo o sistema

// Configuração Firebase oficial do projeto
export const firebaseConfig = {
    apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
    authDomain: "portal-de-proposta.firebaseapp.com",
    projectId: "portal-de-proposta",
    storageBucket: "portal-de-proposta.firebasestorage.app",
    messagingSenderId: "321036073908",
    appId: "1:321036073908:web:3149b9ea2cb77a704890e1",
    measurementId: "G-CFFVQGM3EC"
};

// Versão padronizada do Firebase SDK
export const FIREBASE_VERSION = "10.12.2";

// URLs dos módulos Firebase
export const FIREBASE_MODULES = {
    app: `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-app.js`,
    auth: `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-auth.js`,
    firestore: `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-firestore.js`,
    storage: `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-storage.js`
};

// Configuração para uso global (compatibilidade)
if (typeof window !== 'undefined') {
    window.firebaseConfig = firebaseConfig;
    window.FIREBASE_VERSION = FIREBASE_VERSION;
    window.FIREBASE_MODULES = FIREBASE_MODULES;
}

// Mapeamento de perfis para dashboards
export const DASHBOARD_ROUTES = {
    'admin': '/static/admin-usuarios.html',
    'requisitante': '/static/dashboard-requisitante-funcional.html',
    'comprador': '/static/dashboard-comprador-funcional.html',
    'fornecedor': '/static/dashboard-fornecedor-funcional.html'
};

// Chaves de sessão padronizadas
export const SESSION_KEYS = {
    TOKEN: 'userToken',
    USER_DATA: 'userData',
    PROFILE: 'userProfile',
    // Chaves específicas por perfil (para compatibilidade)
    ADMIN: 'admin_logado',
    REQUISITANTE: 'requisitante_logado',
    COMPRADOR: 'comprador_logado',
    FORNECEDOR: 'fornecedor_logado'
};

// Configurações de autenticação
export const AUTH_CONFIG = {
    // Tempo de expiração do token (em milissegundos)
    TOKEN_EXPIRY: 3600000, // 1 hora
    
    // URL de redirecionamento após logout
    LOGOUT_REDIRECT: '/static/portal-unico-inteligente.html',
    
    // URL de redirecionamento para login
    LOGIN_REDIRECT: '/static/portal-unico-inteligente.html',
    
    // Endpoints da API
    API_ENDPOINTS: {
        VERIFY_TOKEN: (typeof window !== 'undefined' && window.location.hostname === 'localhost') ? 'http://localhost:5000/auth/verify' : '/auth/verify',
        USER_PROFILE: (typeof window !== 'undefined' && window.location.hostname === 'localhost') ? 'http://localhost:5000/api/user-profile' : '/api/user-profile',
        LOGOUT: (typeof window !== 'undefined' && window.location.hostname === 'localhost') ? 'http://localhost:5000/auth/logout' : '/auth/logout'
    }
};

// Utilitários de configuração
export const ConfigUtils = {
    /**
     * Obter URL do dashboard baseado no perfil
     */
    getDashboardUrl(profile) {
        const normalizedProfile = (profile || '').toLowerCase();
        return DASHBOARD_ROUTES[normalizedProfile] || DASHBOARD_ROUTES.requisitante;
    },
    
    /**
     * Obter chave de sessão baseada no perfil
     */
    getSessionKey(profile) {
        const normalizedProfile = (profile || '').toLowerCase();
        return SESSION_KEYS[normalizedProfile.toUpperCase()] || SESSION_KEYS.USER_DATA;
    },
    
    /**
     * Verificar se perfil é válido
     */
    isValidProfile(profile) {
        const normalizedProfile = (profile || '').toLowerCase();
        return Object.keys(DASHBOARD_ROUTES).includes(normalizedProfile);
    },
    
    /**
     * Normalizar nome do perfil
     */
    normalizeProfile(profile) {
        const profileMap = {
            'administrador': 'admin',
            'administrator': 'admin',
            'req': 'requisitante',
            'comp': 'comprador',
            'forn': 'fornecedor',
            'supplier': 'fornecedor',
            'buyer': 'comprador'
        };
        
        const normalized = (profile || '').toLowerCase();
        return profileMap[normalized] || normalized;
    }
};

// Log de configuração (apenas em desenvolvimento)
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    console.log('🔧 Firebase Config carregada:', {
        projectId: firebaseConfig.projectId,
        version: FIREBASE_VERSION,
        dashboards: Object.keys(DASHBOARD_ROUTES).length,
        sessionKeys: Object.keys(SESSION_KEYS).length
    });
}