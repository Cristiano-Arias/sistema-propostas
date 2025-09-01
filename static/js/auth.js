// auth.js - Controle unificado de autenticação e roteamento
import { 
  auth, 
  db, 
  signInWithEmailAndPassword, 
  onAuthStateChanged, 
  signOut, 
  doc, 
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
      } else {
        this.currentUser = null;
        this.userProfile = null;
      }
    });
  }

  async login(email, password) {
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (error) {
      alert("Erro no login: " + error.message);
    }
  }

  async loadUserProfile(uid) {
    try {
      const userDocRef = doc(db, "usuarios", uid);
      const userSnap = await getDoc(userDocRef);

      if (userSnap.exists()) {
        this.userProfile = userSnap.data();

        if (!this.userProfile.ativo) {
          alert("Usuário inativo, contate o administrador.");
          return;
        }

        this.redirectByProfile(this.userProfile.perfil);
      } else {
        console.warn("Usuário não encontrado no Firestore");
      }
    } catch (error) {
      console.error("Erro ao carregar perfil:", error);
    }
  }

  redirectByProfile(perfil) {
    switch (perfil.toLowerCase()) {
      case "fornecedor":
        window.location.href = "/static/dashboard-fornecedor-funcional.html";
        break;
      case "requisitante":
        window.location.href = "/static/dashboard-requisitante-funcional.html";
        break;
      case "comprador":
        window.location.href = "/static/dashboard-comprador-funcional.html";
        break;
      default:
        alert("Perfil não reconhecido.");
        break;
    }
  }

  async logout() {
    await signOut(auth);
    window.location.href = "/static/index.html"; // volta para tela inicial
  }
}

// Instância global
window.authSystem = new AuthSystem();
