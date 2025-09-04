// static/js/auth-facade.js - Fachada completa para autenticação com Firebase
import { auth, signInWithEmailAndPassword } from './firebase.js';
import { SESSION_KEYS, ConfigUtils, AUTH_CONFIG } from './firebase-config.js';

/**
 * Fazer login com perfil específico
 * @param {string} email - Email do usuário
 * @param {string} senha - Senha do usuário
 * @param {string} perfil - Perfil do usuário (admin, requisitante, comprador, fornecedor)
 * @returns {Promise<Object>} Dados do usuário autenticado
 */
export async function loginComPerfil(email, senha, perfil) {
    try {
        // 1. Autenticar com Firebase
        const cred = await signInWithEmailAndPassword(auth, email, senha);
        const user = cred.user;
        
        // 2. Obter token de autenticação
        const token = await user.getIdToken();
        
        // 3. Normalizar perfil
        const normalizedProfile = ConfigUtils.normalizeProfile(perfil);
        
        // 4. Verificar se perfil é válido
        if (!ConfigUtils.isValidProfile(normalizedProfile)) {
            throw new Error(`Perfil inválido: ${perfil}`);
        }
        
        // 5. Criar dados do usuário
        const userData = {
            uid: user.uid,
            email: user.email,
            displayName: user.displayName || email.split('@')[0],
            profile: normalizedProfile,
            token: token,
            loginTime: new Date().toISOString(),
            lastActivity: new Date().toISOString()
        };
        
        // 6. Pular verificação com backend por enquanto (endpoint com problemas)
        console.log('⚠️ Pulando verificação com backend - usando autenticação Firebase direta');
        
        // 7. Persistir sessão
        await persistUserSession(userData);
        
        // 8. Log de sucesso
        console.log(`✅ Login realizado com sucesso:`, {
            email: userData.email,
            profile: userData.profile,
            uid: userData.uid
        });
        
        return userData;
        
    } catch (error) {
        console.error('❌ Erro no login:', error);
        throw error;
    }
}

/**
 * Persistir sessão do usuário em múltiplos formatos para compatibilidade
 * @param {Object} userData - Dados do usuário
 */
async function persistUserSession(userData) {
    try {
        // 1. Dados principais (formato novo)
        localStorage.setItem(SESSION_KEYS.TOKEN, userData.token);
        localStorage.setItem(SESSION_KEYS.USER_DATA, JSON.stringify(userData));
        localStorage.setItem(SESSION_KEYS.PROFILE, userData.profile);
        
        // 2. Compatibilidade com sistema antigo (sessionStorage)
        const profileKey = ConfigUtils.getSessionKey(userData.profile);
        const legacyData = {
            email: userData.email,
            nome: userData.displayName,
            perfil: userData.profile,
            logado: true,
            loginTime: userData.loginTime
        };
        
        sessionStorage.setItem(profileKey, JSON.stringify(legacyData));
        
        // 3. Dados específicos por perfil (para compatibilidade total)
        const profileSpecificData = {
            ...legacyData,
            uid: userData.uid,
            token: userData.token
        };
        
        switch (userData.profile) {
            case 'requisitante':
                localStorage.setItem('requisitante_logado', JSON.stringify(profileSpecificData));
                sessionStorage.setItem('sistema_usuario_logado', JSON.stringify({
                    ...profileSpecificData,
                    tipo: 'requisitante'
                }));
                break;
                
            case 'comprador':
                localStorage.setItem('comprador_logado', JSON.stringify(profileSpecificData));
                sessionStorage.setItem('sistema_usuario_logado', JSON.stringify({
                    ...profileSpecificData,
                    tipo: 'comprador'
                }));
                break;
                
            case 'fornecedor':
                localStorage.setItem('fornecedor_logado', JSON.stringify(profileSpecificData));
                sessionStorage.setItem('sistema_usuario_logado', JSON.stringify({
                    ...profileSpecificData,
                    tipo: 'fornecedor'
                }));
                break;
                
            case 'admin':
                localStorage.setItem('admin_logado', JSON.stringify(profileSpecificData));
                sessionStorage.setItem('sistema_usuario_logado', JSON.stringify({
                    ...profileSpecificData,
                    tipo: 'admin'
                }));
                break;
        }
        
        // 4. Marcar última atividade
        localStorage.setItem('last_activity', new Date().toISOString());
        
        console.log(`💾 Sessão persistida para perfil: ${userData.profile}`);
        
    } catch (error) {
        console.error('❌ Erro ao persistir sessão:', error);
        throw new Error('Falha ao salvar sessão do usuário');
    }
}

/**
 * Limpar todas as sessões do usuário
 */
export async function clearUserSession() {
    try {
        // 1. Limpar dados principais
        localStorage.removeItem(SESSION_KEYS.TOKEN);
        localStorage.removeItem(SESSION_KEYS.USER_DATA);
        localStorage.removeItem(SESSION_KEYS.PROFILE);
        
        // 2. Limpar dados específicos por perfil
        Object.values(SESSION_KEYS).forEach(key => {
            if (key.includes('_logado')) {
                localStorage.removeItem(key);
                sessionStorage.removeItem(key);
            }
        });
        
        // 3. Limpar dados do sistema antigo
        sessionStorage.removeItem('sistema_usuario_logado');
        localStorage.removeItem('last_activity');
        
        // 4. Limpar dados específicos conhecidos
        ['requisitante_logado', 'comprador_logado', 'fornecedor_logado', 'admin_logado'].forEach(key => {
            localStorage.removeItem(key);
            sessionStorage.removeItem(key);
        });
        
        console.log('🧹 Sessão limpa com sucesso');
        
    } catch (error) {
        console.error('❌ Erro ao limpar sessão:', error);
    }
}

/**
 * Verificar se usuário está autenticado
 * @returns {Object|null} Dados do usuário ou null se não autenticado
 */
export function getCurrentUser() {
    try {
        const userData = localStorage.getItem(SESSION_KEYS.USER_DATA);
        if (userData) {
            const user = JSON.parse(userData);
            
            // Verificar se token não expirou
            const loginTime = new Date(user.loginTime);
            const now = new Date();
            const timeDiff = now.getTime() - loginTime.getTime();
            
            if (timeDiff > AUTH_CONFIG.TOKEN_EXPIRY) {
                console.warn('⏰ Token expirado, limpando sessão');
                clearUserSession();
                return null;
            }
            
            return user;
        }
        
        return null;
    } catch (error) {
        console.error('❌ Erro ao obter usuário atual:', error);
        return null;
    }
}

/**
 * Atualizar última atividade do usuário
 */
export function updateLastActivity() {
    const user = getCurrentUser();
    if (user) {
        user.lastActivity = new Date().toISOString();
        localStorage.setItem(SESSION_KEYS.USER_DATA, JSON.stringify(user));
        localStorage.setItem('last_activity', user.lastActivity);
    }
}
