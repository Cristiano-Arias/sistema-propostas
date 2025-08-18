/**
 * SistemaFirebase.js
 * Sistema para substituir SistemaLocal usando Firebase Firestore
 * Mantém compatibilidade total com a API existente
 */

import { 
    getFirestore, 
    collection, 
    doc, 
    setDoc, 
    getDoc, 
    getDocs, 
    deleteDoc, 
    query, 
    where, 
    orderBy 
} from 'firebase/firestore';

const SistemaFirebase = {
    // Inicialização do Firestore
    db: null,
    
    // Chaves mapeadas para coleções Firestore
    CHAVES: {
        TRS: 'termos_referencia',
        PROCESSOS: 'processos',
        PROPOSTAS_FORNECEDORES: 'propostas_fornecedores',
        ANALISES_IA: 'analises_ia',
        USUARIO: 'usuarios',
        ESTATISTICAS: 'estatisticas',
        FORNECEDOR_LOGADO: 'fornecedores_logados'
    },

    // Inicializar Firestore
    init() {
        if (!this.db) {
            this.db = getFirestore();
            console.log('✅ SistemaFirebase inicializado');
        }
        return this.db;
    },

    // Salvar dados no Firestore
    async salvar(chave, dados, id = null) {
        try {
            this.init();
            
            // Se não forneceu ID, gerar um novo
            if (!id) {
                id = this.gerarId();
            }
            
            // Adicionar metadados
            const dadosCompletos = {
                ...dados,
                _metadata: {
                    criadoEm: new Date().toISOString(),
                    atualizadoEm: new Date().toISOString(),
                    criadoPor: await this.obterUsuarioAtual()?.uid || 'sistema'
                }
            };
            
            const docRef = doc(this.db, chave, id);
            await setDoc(docRef, dadosCompletos);
            
            console.log(`✅ Dados salvos em ${chave}/${id}`);
            return { success: true, id };
            
        } catch (error) {
            console.error('❌ Erro ao salvar dados:', error);
            return { success: false, error: error.message };
        }
    },

    // Carregar dados do Firestore
    async carregar(chave, padrao = null, filtros = null) {
        try {
            this.init();
            
            // Se é uma busca com filtros
            if (filtros) {
                return await this.listar(chave, filtros);
            }
            
            // Se é busca de um documento específico
            if (typeof padrao === 'string') {
                const docRef = doc(this.db, chave, padrao);
                const docSnap = await getDoc(docRef);
                
                if (docSnap.exists()) {
                    return { id: docSnap.id, ...docSnap.data() };
                } else {
                    return null;
                }
            }
            
            // Buscar todos os documentos da coleção
            const colRef = collection(this.db, chave);
            const snapshot = await getDocs(colRef);
            
            const dados = [];
            snapshot.forEach(doc => {
                dados.push({ id: doc.id, ...doc.data() });
            });
            
            console.log(`✅ Carregados ${dados.length} documentos de ${chave}`);
            return dados.length > 0 ? dados : padrao;
            
        } catch (error) {
            console.error('❌ Erro ao carregar dados:', error);
            return padrao;
        }
    },

    // Listar documentos com filtros
    async listar(chave, filtros = {}) {
        try {
            this.init();
            
            let q = collection(this.db, chave);
            
            // Aplicar filtros
            if (filtros.where) {
                filtros.where.forEach(filtro => {
                    q = query(q, where(filtro.campo, filtro.operador, filtro.valor));
                });
            }
            
            // Aplicar ordenação
            if (filtros.orderBy) {
                q = query(q, orderBy(filtros.orderBy.campo, filtros.orderBy.direcao || 'asc'));
            }
            
            const snapshot = await getDocs(q);
            const dados = [];
            
            snapshot.forEach(doc => {
                dados.push({ id: doc.id, ...doc.data() });
            });
            
            return dados;
            
        } catch (error) {
            console.error('❌ Erro ao listar dados:', error);
            return [];
        }
    },

    // Deletar documento
    async deletar(chave, id) {
        try {
            this.init();
            
            const docRef = doc(this.db, chave, id);
            await deleteDoc(docRef);
            
            console.log(`✅ Documento ${id} deletado de ${chave}`);
            return { success: true };
            
        } catch (error) {
            console.error('❌ Erro ao deletar documento:', error);
            return { success: false, error: error.message };
        }
    },

    // Gerar ID único (compatível com SistemaLocal)
    gerarId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },

    // Obter usuário atual (compatível com SistemaLocal)
    async obterUsuario() {
        try {
            // Tentar obter do Firebase Auth
            const user = await this.obterUsuarioAtual();
            if (user) {
                return {
                    id: user.uid,
                    nome: user.displayName || user.email,
                    email: user.email
                };
            }
            
            // Fallback para dados locais (compatibilidade)
            const userData = localStorage.getItem('userData');
            if (userData) {
                return JSON.parse(userData);
            }
            
            // Usuário padrão (compatibilidade)
            return { 
                id: 1, 
                nome: 'Admin', 
                email: 'admin@sistema.com' 
            };
            
        } catch (error) {
            console.error('❌ Erro ao obter usuário:', error);
            return { id: 1, nome: 'Admin', email: 'admin@sistema.com' };
        }
    },

    // Função auxiliar para obter usuário atual do Firebase Auth
    async obterUsuarioAtual() {
        try {
            const { getAuth, onAuthStateChanged } = await import('firebase/auth');
            const auth = getAuth();
            
            return new Promise((resolve) => {
                const unsubscribe = onAuthStateChanged(auth, (user) => {
                    unsubscribe();
                    resolve(user);
                });
            });
        } catch (error) {
            console.error('❌ Erro ao obter usuário do Auth:', error);
            return null;
        }
    },

    // Migrar dados do localStorage para Firestore
    async migrarDados() {
        try {
            console.log('🔄 Iniciando migração de dados...');
            
            const chavesParaMigrar = [
                'sistema_trs',
                'sistema_processos', 
                'propostas_fornecedores',
                'analises_ia'
            ];
            
            for (const chave of chavesParaMigrar) {
                const dadosLocais = localStorage.getItem(chave);
                if (dadosLocais) {
                    const dados = JSON.parse(dadosLocais);
                    
                    if (Array.isArray(dados)) {
                        // Migrar array de documentos
                        for (const item of dados) {
                            await this.salvar(this.CHAVES[chave.toUpperCase()] || chave, item, item.id);
                        }
                    } else {
                        // Migrar documento único
                        await this.salvar(this.CHAVES[chave.toUpperCase()] || chave, dados);
                    }
                    
                    console.log(`✅ Migrados dados de ${chave}`);
                }
            }
            
            console.log('✅ Migração concluída!');
            return { success: true };
            
        } catch (error) {
            console.error('❌ Erro na migração:', error);
            return { success: false, error: error.message };
        }
    }
};

// Compatibilidade com SistemaLocal existente
window.SistemaFirebase = SistemaFirebase;

export default SistemaFirebase;

