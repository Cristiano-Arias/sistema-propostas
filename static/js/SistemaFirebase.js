// SistemaFirebase.js - Versão Corrigida
// Substitui SistemaLocal com Firebase Firestore

// Importações Firebase via CDN (sem erros de módulo)
import { initializeApp } from 'https://www.gstatic.com/firebasejs/9.23.0/firebase-app.js';
import { 
    getFirestore, 
    collection, 
    doc, 
    setDoc, 
    getDoc, 
    getDocs, 
    query, 
    where, 
    orderBy, 
    deleteDoc,
    updateDoc 
} from 'https://www.gstatic.com/firebasejs/9.23.0/firebase-firestore.js';

class SistemaFirebase {
    constructor() {
        this.db = null;
        this.inicializado = false;
        this.init();
    }

    async init() {
        try {
            // Configuração Firebase (usar a mesma do seu projeto)
            const firebaseConfig = {
                apiKey: "AIzaSyBXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX", // Substitua pela sua
                authDomain: "portal-de-proposta.firebaseapp.com",
                projectId: "portal-de-proposta",
                storageBucket: "portal-de-proposta.appspot.com",
                messagingSenderId: "123456789",
                appId: "1:123456789:web:xxxxxxxxxxxxxxxxxx"
            };

            const app = initializeApp(firebaseConfig);
            this.db = getFirestore(app);
            this.inicializado = true;
            console.log('✅ SistemaFirebase inicializado');
        } catch (error) {
            console.error('❌ Erro ao inicializar Firebase:', error);
            // Fallback para localStorage se Firebase falhar
            this.usarLocalStorage = true;
        }
    }

    // Aguardar inicialização
    async aguardarInicializacao() {
        while (!this.inicializado && !this.usarLocalStorage) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }

    // Mapeamento de coleções
    obterColecao(chave) {
        const mapeamento = {
            'sistema_trs': 'termos_referencia',
            'processos_licitatorios': 'processos',
            'propostas_fornecedores': 'propostas_fornecedores',
            'propostas_completas': 'propostas_completas',
            'analises_ia': 'analises_ia',
            'notificacoes_comprador': 'notificacoes',
            'sistema_estatisticas': 'estatisticas',
            'sistema_usuario_logado': 'usuarios_sessao'
        };
        return mapeamento[chave] || chave;
    }

    // Salvar dados
    async salvar(chave, dados) {
        await this.aguardarInicializacao();
        
        try {
            if (this.usarLocalStorage) {
                localStorage.setItem(chave, JSON.stringify(dados));
                return true;
            }

            const colecao = this.obterColecao(chave);
            
            if (Array.isArray(dados)) {
                // Salvar array como documentos individuais
                for (const item of dados) {
                    const id = item.id || this.gerarId();
                    await setDoc(doc(this.db, colecao, id), {
                        ...item,
                        id: id,
                        timestamp: new Date().toISOString()
                    });
                }
            } else {
                // Salvar objeto único
                const id = dados.id || this.gerarId();
                await setDoc(doc(this.db, colecao, id), {
                    ...dados,
                    id: id,
                    timestamp: new Date().toISOString()
                });
            }
            
            console.log(`✅ Dados salvos em ${colecao}`);
            return true;
        } catch (error) {
            console.error('❌ Erro ao salvar:', error);
            // Fallback para localStorage
            localStorage.setItem(chave, JSON.stringify(dados));
            return false;
        }
    }

    // Carregar dados
    async carregar(chave, padrao = null) {
        await this.aguardarInicializacao();
        
        try {
            if (this.usarLocalStorage) {
                const dados = localStorage.getItem(chave);
                return dados ? JSON.parse(dados) : padrao;
            }

            const colecao = this.obterColecao(chave);
            const querySnapshot = await getDocs(collection(this.db, colecao));
            
            if (querySnapshot.empty) {
                return padrao;
            }

            const dados = [];
            querySnapshot.forEach((doc) => {
                dados.push({ id: doc.id, ...doc.data() });
            });

            console.log(`✅ Dados carregados de ${colecao}: ${dados.length} itens`);
            return dados.length === 1 ? dados[0] : dados;
        } catch (error) {
            console.error('❌ Erro ao carregar:', error);
            // Fallback para localStorage
            const dados = localStorage.getItem(chave);
            return dados ? JSON.parse(dados) : padrao;
        }
    }

    // Gerar ID único
    gerarId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    // Obter usuário logado
    obterUsuario() {
        try {
            // Tentar obter do localStorage primeiro (compatibilidade)
            const userData = localStorage.getItem('userData');
            if (userData) {
                return JSON.parse(userData);
            }
            
            // Fallback padrão
            return { 
                id: 1, 
                nome: 'Admin', 
                email: 'admin@sistema.com',
                perfil: 'admin'
            };
        } catch (error) {
            console.error('❌ Erro ao obter usuário:', error);
            return { 
                id: 1, 
                nome: 'Admin', 
                email: 'admin@sistema.com',
                perfil: 'admin'
            };
        }
    }

    // Migrar dados existentes do localStorage
    async migrarDados() {
        console.log('🔄 Iniciando migração de dados...');
        
        try {
            const chaves = [
                'sistema_trs',
                'processos_licitatorios', 
                'propostas_fornecedores',
                'propostas_completas',
                'analises_ia',
                'notificacoes_comprador',
                'sistema_estatisticas'
            ];

            let migrados = 0;
            
            for (const chave of chaves) {
                const dados = localStorage.getItem(chave);
                if (dados) {
                    try {
                        const dadosParsed = JSON.parse(dados);
                        if (dadosParsed && (Array.isArray(dadosParsed) ? dadosParsed.length > 0 : Object.keys(dadosParsed).length > 0)) {
                            await this.salvar(chave, dadosParsed);
                            migrados++;
                            console.log(`✅ Migrado: ${chave}`);
                        }
                    } catch (error) {
                        console.warn(`⚠️ Erro ao migrar ${chave}:`, error);
                    }
                }
            }

            console.log(`✅ Migração concluída! ${migrados} coleções migradas.`);
            return { success: true, migrados };
        } catch (error) {
            console.error('❌ Erro na migração:', error);
            return { success: false, error };
        }
    }

    // Compatibilidade com SistemaLocal existente
    get CHAVES() {
        return {
            TRS: 'sistema_trs',
            NOTIFICACOES_COMPRADOR: 'notificacoes_comprador',
            PROCESSOS: 'processos_licitatorios',
            PROPOSTAS: 'propostas_fornecedores',
            PROPOSTAS_COMPLETAS: 'propostas_completas',
            USUARIO_COMPRADOR: 'comprador_user',
            ANALISE_REQUISITANTE: 'analise_tecnica_requisitante',
            ANALISES_IA: 'analises_ia',
            USUARIO: 'sistema_usuario_logado',
            ESTATISTICAS: 'sistema_estatisticas',
            FORNECEDOR_LOGADO: 'fornecedor_logado',
            FORNECEDORES_CADASTRADOS: 'fornecedores_cadastrados',
            USUARIOS_FORNECEDORES: 'usuarios_fornecedores',
            PROCESSOS_POR_FORNECEDOR: 'processos_por_fornecedor'
        };
    }
}

// Criar instância única
const sistemaFirebase = new SistemaFirebase();

// Exportar como default
export default sistemaFirebase;
