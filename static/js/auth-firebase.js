// auth-firebase.js - Autenticação com Firebase
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js';
import { 
  getAuth, 
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signOut 
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js';

// Configuração do Firebase (suas credenciais)
const firebaseConfig = {
  apiKey: "AIzaSyCqF366Ft7RkzHYaZb77HboNO3BPbmCjT8",
  authDomain: "portal-de-proposta.firebaseapp.com",
  projectId: "portal-de-proposta",
  storageBucket: "portal-de-proposta.appspot.com",
  messagingSenderId: "321036073908",
  appId: "1:321036073908:web:3149b9ea2cb77a704890e1"
};

// Inicializar Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Classe para gerenciar autenticação
class FirebaseAuthManager {
  constructor() {
    this.currentUser = null;
    this.userProfile = null;
    this.token = null;
    
    // Observar mudanças de autenticação
    onAuthStateChanged(auth, async (user) => {
      if (user) {
        this.currentUser = user;
        this.token = await user.getIdToken();
        await this.loadUserProfile();
      } else {
        this.currentUser = null;
        this.userProfile = null;
        this.token = null;
      }
    });
  }
  
  async loadUserProfile() {
    if (!this.currentUser || !this.token) return;
    
    try {
      const response = await fetch('/auth/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ token: this.token })
      });
      
      if (response.ok) {
        this.userProfile = await response.json();
      }
    } catch (error) {
      console.error('Erro ao carregar perfil:', error);
    }
  }
  
  async login(email, password) {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      this.currentUser = userCredential.user;
      this.token = await userCredential.user.getIdToken();
      await this.loadUserProfile();
      
      return {
        success: true,
        user: this.currentUser,
        profile: this.userProfile
      };
    } catch (error) {
      console.error('Erro no login:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  async register(email, password, nome) {
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      
      // Atualizar display name
      await userCredential.user.updateProfile({
        displayName: nome
      });
      
      this.currentUser = userCredential.user;
      this.token = await userCredential.user.getIdToken();
      
      return {
        success: true,
        user: this.currentUser
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
      this.currentUser = null;
      this.userProfile = null;
      this.token = null;
      window.location.href = '/';
    } catch (error) {
      console.error('Erro no logout:', error);
    }
  }
  
  isAuthenticated() {
    return this.currentUser !== null;
  }
  
  async getToken() {
    if (this.currentUser) {
      return await this.currentUser.getIdToken();
    }
    return null;
  }
  
  hasRole(role) {
    return this.userProfile && this.userProfile.perfil === role;
  }
}

// Criar instância global
window.firebaseAuth = new FirebaseAuthManager();

// Exportar para uso
export default window.firebaseAuth;
