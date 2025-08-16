// static/auth.js - Sistema de Autenticação Integrado
import { 
  auth, 
  db, 
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signOut,
  doc,
  setDoc,
  getDoc
} from './firebase.js';

class AuthSystem {
  constructor() {
    this.currentUser = null;
    this.userProfile = null;
    this.initAuthListener();
  }

  initAuthListener() {
    onAuthStateChanged(auth, async (user) => {
      if (user) {
        this.currentUser = user;
        await this.loadUserProfile(user.uid);
        console.log('Usuário autenticado:', user.email);
      } else {
        this.currentUser = null;
        this.userProfile = null;
        console.log('Usuário não autenticado');
      }
    });
  }

  async loadUserProfile(uid) {
    try {
      const userDoc = await getDoc(doc(db, 'usuarios', uid));
      if (userDoc.exists()) {
        this.userProfile = userDoc.data();
        return this.userProfile;
      }
      return null;
    } catch (error) {
      console.error('Erro ao carregar perfil:', error);
      return null;
    }
  }

  async login(email, senha, perfil) {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, senha);
      const userProfile = await this.loadUserProfile(userCredential.user.uid);
      
      // Verificar se o perfil corresponde
      if (userProfile && userProfile.perfil === perfil) {
        return { 
          success: true, 
          user: userCredential.user,
          profile: userProfile 
        };
      } else if (!userProfile) {
        // Criar perfil se não existir (primeira vez)
        await this.createUserProfile(userCredential.user.uid, {
          email: email,
          perfil: perfil,
          nome: email.split('@')[0],
          ativo: true,
          criadoEm: new Date().toISOString()
        });
        return { 
          success: true, 
          user: userCredential.user,
          profile: { email, perfil }
        };
      } else {
        await signOut(auth);
        throw new Error('Perfil não autorizado para este tipo de acesso');
      }
    } catch (error) {
      console.error('Erro no login:', error);
      return { 
        success: false, 
        error: error.message 
      };
    }
  }

  async createUserProfile(uid, profileData) {
    try {
      await setDoc(doc(db, 'usuarios', uid), profileData);
      return true;
    } catch (error) {
      console.error('Erro ao criar perfil:', error);
      return false;
    }
  }

  async register(email, senha, perfil, dadosAdicionais = {}) {
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, senha);
      
      // Criar perfil no Firestore
      const profileData = {
        email: email,
        perfil: perfil,
        nome: dadosAdicionais.nome || email.split('@')[0],
        ativo: true,
        criadoEm: new Date().toISOString(),
        ...dadosAdicionais
      };
      
      await this.createUserProfile(userCredential.user.uid, profileData);
      
      return { 
        success: true, 
        user: userCredential.user 
      };
    } catch (error) {
      console.error('Erro no registro:', error);
      return { 
        success: false, 
        error: error.message 
      };
    }
  }

  async logout() {
    try {
      await signOut(auth);
      localStorage.clear();
      window.location.href = '/static/index.html';
      return { success: true };
    } catch (error) {
      console.error('Erro no logout:', error);
      return { 
        success: false, 
        error: error.message 
      };
    }
  }

  isAuthenticated() {
    return this.currentUser !== null;
  }

  getUserProfile() {
    return this.userProfile;
  }

  checkPermission(requiredProfile) {
    return this.userProfile && this.userProfile.perfil === requiredProfile;
  }
}

// Criar instância global
window.authSystem = new AuthSystem();

// Exportar para uso em outros módulos
export default window.authSystem;
