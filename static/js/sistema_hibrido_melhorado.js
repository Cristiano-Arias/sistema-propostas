// Sistema Híbrido Melhorado - Firebase + localStorage
// Versão corrigida e otimizada para todos os módulos

class SistemaHibridoFirebase {
    constructor() {
        this.db = null;
        this.firebaseReady = false;
        this.inicializando = false;
        this.filaOperacoes = [];
        this.tentativasReconexao = 0;
        this.maxTentativas = 3;
        
        // Configuração Firebase
        this.firebaseConfig = {
            apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
            authDomain: "portal-de-proposta.firebaseapp.com",
            projectId: "portal-de-proposta",
            storageBucket: "portal-de-proposta.firebasestorage.app",
            messagingSenderId: "321036073908",
            appId: "1:321036073908:web:3149b9ea2cb77a704890e1"
        };
        
        // Chaves padronizadas para todos os módulos
        this.CHAVES = {
            // Usuários e Autenticação
            REQUISITANTE_LOGADO: 'requisitante_logado',
            COMPRADOR_LOGADO: 'comprador_logado',
            FORNECEDOR_LOGADO: 'fornecedor_logado',
            ADMIN_LOGADO: 'admin_logado',
            USER_TOKEN: 'userToken',
            USER_DATA: 'userData',
            
            // Dados Principais
            TRS: 'sistema_trs',
            PROCESSOS: 'processos_compra',
            PROPOSTAS: 'sistema_propostas',
            FORNECEDORES: 'fornecedores_cadastrados',
            USUARIOS_FORNECEDORES: 'usuarios_fornecedores',
            
            // Análises e Pareceres
            PARECERES_TECNICOS: 'pareceres_tecnicos',
            ANALISES_IA: 'analises_ia',
            PROPOSTAS_LIBERADAS: 'propostas_liberadas_parecer',
            
            // Dados Temporários
            TR_RASCUNHO: 'tr_rascunho',
            TR_AUTOSAVE: 'tr_autosave',
            TECHNICAL_ANALYSIS_DRAFT: 'technical_analysis_draft',
            
            // Notificações
            NOTIFICACOES_REQUISITANTE: 'notificacoes_requisitante',
            CONVITES_PROCESSO: 'convites_processo'
        };
        
        this.inicializar();
    }
    
    async inicializar() {
        if (this.inicializando) return;
        this.inicializando = true;
        
        try {
            // Importar Firebase dinamicamente
            const { initializeApp } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js');
            const { getFirestore, doc, setDoc, getDoc, collection, getDocs } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
            
            // Inicializar Firebase
            const app = initializeApp(this.firebaseConfig);
            this.db = getFirestore(app);
            
            // Testar conexão
            await this.testarConexao();
            
            this.firebaseReady = true;
            this.tentativasReconexao = 0;
            console.log('✅ Sistema Híbrido Firebase inicializado com sucesso');
            
            // Processar fila de operações pendentes
            await this.processarFilaOperacoes();
            
        } catch (error) {
            console.warn('⚠️ Firebase não disponível, usando apenas localStorage:', error);
            this.firebaseReady = false;
            this.tentarReconexao();
        } finally {
            this.inicializando = false;
        }
    }
    
    async testarConexao() {
        if (!this.db) throw new Error('Database não inicializado');
        
        // Tentar uma operação simples para verificar conectividade
        const testDoc = doc(this.db, 'sistema', 'teste_conexao');
        await setDoc(testDoc, { 
            timestamp: new Date().toISOString(),
            teste: true 
        }, { merge: true });
    }
    
    async tentarReconexao() {
        if (this.tentativasReconexao >= this.maxTentativas) {
            console.log('🔄 Máximo de tentativas de reconexão atingido, usando apenas localStorage');
            return;
        }
        
        this.tentativasReconexao++;
        const delay = Math.pow(2, this.tentativasReconexao) * 1000; // Backoff exponencial
        
        console.log(`🔄 Tentativa de reconexão ${this.tentativasReconexao}/${this.maxTentativas} em ${delay}ms`);
        
        setTimeout(() => {
            this.inicializar();
        }, delay);
    }
    
    // Salvar dados (localStorage imediato + Firebase background)
    salvar(chave, dados) {
        try {
            // 1. SEMPRE salvar no localStorage primeiro (síncrono, imediato)
            localStorage.setItem(chave, JSON.stringify(dados));
            
            // 2. Tentar salvar no Firebase em background (assíncrono)
            if (this.firebaseReady && this.db) {
                this.salvarFirebase(chave, dados).catch(error => {
                    console.warn(`Erro ao salvar ${chave} no Firebase:`, error);
                    // Adicionar à fila para tentar novamente
                    this.adicionarFilaOperacao('salvar', chave, dados);
                });
            } else {
                // Adicionar à fila para quando Firebase estiver disponível
                this.adicionarFilaOperacao('salvar', chave, dados);
            }
            
            return true;
        } catch (error) {
            console.error('Erro ao salvar dados:', error);
            return false;
        }
    }
    
    // Carregar dados (localStorage imediato + sincronização Firebase background)
    carregar(chave, padrao = null) {
        try {
            // 1. SEMPRE carregar do localStorage primeiro (síncrono, imediato)
            const dados = localStorage.getItem(chave);
            let dadosLocal = dados ? JSON.parse(dados) : padrao;
            
            // Garantir que arrays sempre retornam array
            if (padrao !== null && Array.isArray(padrao) && !Array.isArray(dadosLocal)) {
                console.warn(`${chave} não é array, inicializando como array vazio`);
                dadosLocal = [];
                localStorage.setItem(chave, JSON.stringify([]));
            }
            
            // 2. Sincronizar com Firebase em background (assíncrono)
            if (this.firebaseReady && this.db) {
                this.sincronizarFirebase(chave, dadosLocal).catch(error => {
                    console.warn(`Erro ao sincronizar ${chave} com Firebase:`, error);
                });
            }
            
            return dadosLocal;
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            return padrao;
        }
    }
    
    // Salvar no Firebase (assíncrono)
    async salvarFirebase(chave, dados) {
        if (!this.firebaseReady || !this.db) return false;
        
        try {
            const { doc, setDoc } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
            
            const docRef = doc(this.db, 'sistema_dados', chave);
            await setDoc(docRef, {
                dados: dados,
                timestamp: new Date().toISOString(),
                chave: chave
            });
            
            console.log(`✅ Dados salvos no Firebase: ${chave}`);
            return true;
        } catch (error) {
            console.error(`Erro ao salvar ${chave} no Firebase:`, error);
            throw error;
        }
    }
    
    // Sincronizar com Firebase (assíncrono)
    async sincronizarFirebase(chave, dadosLocal) {
        if (!this.firebaseReady || !this.db) return dadosLocal;
        
        try {
            const { doc, getDoc } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
            
            const docRef = doc(this.db, 'sistema_dados', chave);
            const docSnap = await getDoc(docRef);
            
            if (docSnap.exists()) {
                const dadosFirebase = docSnap.data();
                const timestampFirebase = new Date(dadosFirebase.timestamp);
                const timestampLocal = new Date(localStorage.getItem(`${chave}_timestamp`) || '1970-01-01');
                
                // Se dados do Firebase são mais recentes, atualizar localStorage
                if (timestampFirebase > timestampLocal) {
                    localStorage.setItem(chave, JSON.stringify(dadosFirebase.dados));
                    localStorage.setItem(`${chave}_timestamp`, dadosFirebase.timestamp);
                    console.log(`🔄 Dados sincronizados do Firebase: ${chave}`);
                    return dadosFirebase.dados;
                }
            }
            
            return dadosLocal;
        } catch (error) {
            console.warn(`Erro ao sincronizar ${chave} com Firebase:`, error);
            return dadosLocal;
        }
    }
    
    // Adicionar operação à fila
    adicionarFilaOperacao(tipo, chave, dados) {
        this.filaOperacoes.push({ tipo, chave, dados, timestamp: Date.now() });
        
        // Limitar tamanho da fila
        if (this.filaOperacoes.length > 100) {
            this.filaOperacoes = this.filaOperacoes.slice(-50);
        }
    }
    
    // Processar fila de operações pendentes
    async processarFilaOperacoes() {
        if (!this.firebaseReady || this.filaOperacoes.length === 0) return;
        
        console.log(`🔄 Processando ${this.filaOperacoes.length} operações pendentes`);
        
        const operacoes = [...this.filaOperacoes];
        this.filaOperacoes = [];
        
        for (const operacao of operacoes) {
            try {
                if (operacao.tipo === 'salvar') {
                    await this.salvarFirebase(operacao.chave, operacao.dados);
                }
            } catch (error) {
                console.warn(`Erro ao processar operação ${operacao.tipo} para ${operacao.chave}:`, error);
                // Recolocar na fila se falhou
                this.adicionarFilaOperacao(operacao.tipo, operacao.chave, operacao.dados);
            }
        }
    }
    
    // Gerar ID único
    gerarId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
    
    // Limpar dados (localStorage + Firebase)
    async limpar(chave) {
        try {
            localStorage.removeItem(chave);
            localStorage.removeItem(`${chave}_timestamp`);
            
            if (this.firebaseReady && this.db) {
                const { doc, deleteDoc } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
                const docRef = doc(this.db, 'sistema_dados', chave);
                await deleteDoc(docRef);
            }
            
            return true;
        } catch (error) {
            console.error('Erro ao limpar dados:', error);
            return false;
        }
    }
    
    // Status do sistema
    getStatus() {
        return {
            firebaseReady: this.firebaseReady,
            inicializando: this.inicializando,
            filaOperacoes: this.filaOperacoes.length,
            tentativasReconexao: this.tentativasReconexao
        };
    }
}

// Exportar para uso global
window.SistemaHibridoFirebase = SistemaHibridoFirebase;

// Criar instância global
window.SistemaLocal = new SistemaHibridoFirebase();

console.log('📦 Sistema Híbrido Firebase carregado');

