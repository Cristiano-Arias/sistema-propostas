// auth-firebase.js - Autenticação com Firebase
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js';
import { 
  getAuth, 
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signOut 
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js';
import { 
  getFirestore,
  doc,
  getDoc,
  setDoc
} from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';

// Configuração do Firebase CORRETA (sistema-propostas)
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
const db = getFirestore(app);

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
    if (!this.currentUser) return;
    
    try {
      console.log('Carregando perfil do usuário:', this.currentUser.uid);
      
      // Buscar perfil na coleção usuarios
      const userDoc = await getDoc(doc(db, 'usuarios', this.currentUser.uid));
      
      if (userDoc.exists()) {
        this.userProfile = userDoc.data();
        console.log('Perfil encontrado em usuarios:', this.userProfile);
        return;
      }
      
      // Se não encontrar em usuarios, verificar em fornecedores
      const fornecedorDoc = await getDoc(doc(db, 'fornecedores', this.currentUser.uid));
      
      if (fornecedorDoc.exists()) {
        this.userProfile = {
          ...fornecedorDoc.data(),
          perfil: 'fornecedor',
          tipo: 'fornecedor'
        };
        console.log('Perfil encontrado em fornecedores:', this.userProfile);
        
        // Criar entrada em usuarios para consistência
        await setDoc(doc(db, 'usuarios', this.currentUser.uid), {
          email: this.currentUser.email,
          perfil: 'fornecedor',
          tipo: 'fornecedor',
          nome: fornecedorDoc.data().razaoSocial || fornecedorDoc.data().empresa,
          cnpj: fornecedorDoc.data().cnpj,
          dataCriacao: new Date().toISOString()
        }, { merge: true });
      }
      
    } catch (error) {
      console.error('Erro ao carregar perfil:', error);
    }
  }
  
  async login(email, password) {
    try {
      console.log('Tentando login com:', email);
      
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      this.currentUser = userCredential.user;
      this.token = await userCredential.user.getIdToken();
      
      console.log('Login bem-sucedido, UID:', this.currentUser.uid);
      
      // Carregar perfil completo
      await this.loadUserProfile();
      
      // Determinar redirecionamento baseado no perfil
      let redirectUrl = '/index.html';
      
      if (this.userProfile) {
        const perfil = this.userProfile.perfil || this.userProfile.tipo || this.userProfile.role;
        console.log('Perfil identificado:', perfil);
        
        switch(perfil) {
          case 'fornecedor':
            redirectUrl = '/dashboard-fornecedor-funcional.html';
            
            // Salvar dados do fornecedor no localStorage para o dashboard
            const fornecedorData = {
              id: this.currentUser.uid,
              razaoSocial: this.userProfile.razaoSocial || this.userProfile.nome || this.userProfile.empresa,
              cnpj: this.userProfile.cnpj,
              email: this.currentUser.email,
              telefone: this.userProfile.telefone || '',
              endereco: this.userProfile.endereco || '',
              cidade: this.userProfile.cidade || '',
              tipo: 'fornecedor',
              ativo: true
            };
            
            // Salvar no formato esperado pelo dashboard
            localStorage.setItem('fornecedor_logado', JSON.stringify(fornecedorData));
            
            // Também salvar em fornecedores_cadastrados se não existir
            let fornecedoresCadastrados = JSON.parse(localStorage.getItem('fornecedores_cadastrados') || '[]');
            if (!fornecedoresCadastrados.find(f => f.id === fornecedorData.id)) {
              fornecedoresCadastrados.push(fornecedorData);
              localStorage.setItem('fornecedores_cadastrados', JSON.stringify(fornecedoresCadastrados));
            }
            
            // Adicionar também em usuarios_fornecedores
            let usuariosFornecedores = JSON.parse(localStorage.getItem('usuarios_fornecedores') || '[]');
            if (!usuariosFornecedores.find(u => u.id === fornecedorData.id)) {
              usuariosFornecedores.push({
                id: fornecedorData.id,
                email: email,
                senha: password, // Nota: em produção, nunca salvar senha em texto puro
                tipo: 'fornecedor',
                ativo: true
              });
              localStorage.setItem('usuarios_fornecedores', JSON.stringify(usuariosFornecedores));
            }
            
            break;
            
          case 'requisitante':
            redirectUrl = '/dashboard-requisitante-funcional.html';
            break;
            
          case 'comprador':
            redirectUrl = '/dashboard-comprador-funcional.html';
            break;
            
          case 'admin':
            redirectUrl = '/admin-usuarios.html';
            break;
            
          default:
            console.warn('Perfil não reconhecido:', perfil);
            // Tentar identificar pelo email ou outros campos
            if (this.userProfile.cnpj) {
              // Se tem CNPJ, é fornecedor
              redirectUrl = '/dashboard-fornecedor-funcional.html';
            }
        }
      }
      
      console.log('Redirecionando para:', redirectUrl);
      
      // Fazer o redirecionamento
      setTimeout(() => {
        window.location.href = redirectUrl;
      }, 500);
      
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
  
  async register(email, password, nome, dados = {}) {
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      
      // Atualizar display name
      await userCredential.user.updateProfile({
        displayName: nome
      });
      
      this.currentUser = userCredential.user;
      this.token = await userCredential.user.getIdToken();
      
      // Criar perfil no Firestore baseado no tipo
      const perfil = dados.perfil || dados.tipo || 'fornecedor';
      
      if (perfil === 'fornecedor') {
        // Criar documento em fornecedores
        await setDoc(doc(db, 'fornecedores', this.currentUser.uid), {
          razaoSocial: dados.razaoSocial || nome,
          cnpj: dados.cnpj || '',
          email: email,
          telefone: dados.telefone || '',
          endereco: dados.endereco || '',
          cidade: dados.cidade || '',
          dataCadastro: new Date().toISOString(),
          status: 'ativo',
          perfil: 'fornecedor'
        });
      }
      
      // Criar documento em usuarios
      await setDoc(doc(db, 'usuarios', this.currentUser.uid), {
        nome: nome,
        email: email,
        perfil: perfil,
        tipo: perfil,
        dataCriacao: new Date().toISOString(),
        ...dados
      });
      
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
      
      // Limpar dados do localStorage
      localStorage.removeItem('fornecedor_logado');
      localStorage.removeItem('currentUser');
      
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
    return this.userProfile && (this.userProfile.perfil === role || this.userProfile.tipo === role);
  }
  
  // Método auxiliar para verificar se é fornecedor
  isFornecedor() {
    return this.hasRole('fornecedor');
  }
  
  // Método para obter dados do fornecedor
  getFornecedorData() {
    if (this.isFornecedor()) {
      return {
        id: this.currentUser.uid,
        razaoSocial: this.userProfile.razaoSocial || this.userProfile.nome,
        cnpj: this.userProfile.cnpj,
        email: this.currentUser.email,
        telefone: this.userProfile.telefone || '',
        endereco: this.userProfile.endereco || '',
        cidade: this.userProfile.cidade || ''
      };
    }
    return null;
  }
}

// Criar instância global
window.firebaseAuth = new FirebaseAuthManager();

// Exportar para uso
export default window.firebaseAuth;
