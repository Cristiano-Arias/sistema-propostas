// firebase-firestore.js - Módulo Firestore centralizado
import { db } from './firebase.js';
import {
    collection,
    doc,
    getDoc,
    getDocs,
    setDoc,
    addDoc,
    updateDoc,
    deleteDoc,
    query,
    where,
    orderBy,
    limit,
    onSnapshot
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

/**
 * Classe para operações do Firestore
 */
class FirebaseFirestore {
    /**
     * Buscar propostas com filtros
     * @param {Object} filtros - Filtros para a busca
     * @param {string} ordenarPor - Campo para ordenação
     * @param {string} direcao - Direção da ordenação ('asc' ou 'desc')
     * @returns {Array} Array de propostas
     */
    static async buscarPropostas(filtros = {}, ordenarPor = 'dataCriacao', direcao = 'desc') {
        try {
            console.log('🔍 Buscando propostas com filtros:', filtros);
            
            let q = collection(db, 'propostas');
            
            // Aplicar filtros
            if (filtros.fornecedorId) {
                q = query(q, where('fornecedorId', '==', filtros.fornecedorId));
            }
            
            if (filtros.processoId) {
                q = query(q, where('processoId', '==', filtros.processoId));
            }
            
            if (filtros.status) {
                q = query(q, where('status', '==', filtros.status));
            }
            
            // Aplicar ordenação
            if (ordenarPor) {
                q = query(q, orderBy(ordenarPor, direcao));
            }
            
            const querySnapshot = await getDocs(q);
            const propostas = [];
            
            querySnapshot.forEach((docSnap) => {
                propostas.push({
                    id: docSnap.id,
                    ...docSnap.data()
                });
            });
            
            console.log('✅ Propostas encontradas:', propostas.length);
            return propostas;
            
        } catch (error) {
            console.error('❌ Erro ao buscar propostas:', error);
            throw error;
        }
    }
    
    /**
     * Salvar proposta
     * @param {Object} proposta - Dados da proposta
     * @returns {string} ID da proposta salva
     */
    static async salvarProposta(proposta) {
        try {
            console.log('💾 Salvando proposta:', proposta.id || 'nova');
            
            if (proposta.id) {
                // Atualizar proposta existente
                const propostaRef = doc(db, 'propostas', proposta.id);
                await updateDoc(propostaRef, {
                    ...proposta,
                    dataAtualizacao: new Date()
                });
                return proposta.id;
            } else {
                // Criar nova proposta
                const docRef = await addDoc(collection(db, 'propostas'), {
                    ...proposta,
                    dataCriacao: new Date(),
                    dataAtualizacao: new Date()
                });
                return docRef.id;
            }
            
        } catch (error) {
            console.error('❌ Erro ao salvar proposta:', error);
            throw error;
        }
    }
    
    /**
     * Buscar proposta por ID
     * @param {string} id - ID da proposta
     * @returns {Object|null} Dados da proposta ou null
     */
    static async buscarPropostaPorId(id) {
        try {
            const docRef = doc(db, 'propostas', id);
            const docSnap = await getDoc(docRef);
            
            if (docSnap.exists()) {
                return {
                    id: docSnap.id,
                    ...docSnap.data()
                };
            } else {
                return null;
            }
            
        } catch (error) {
            console.error('❌ Erro ao buscar proposta:', error);
            throw error;
        }
    }
    
    /**
     * Excluir proposta
     * @param {string} id - ID da proposta
     */
    static async excluirProposta(id) {
        try {
            console.log('🗑️ Excluindo proposta:', id);
            
            const docRef = doc(db, 'propostas', id);
            await deleteDoc(docRef);
            
            console.log('✅ Proposta excluída com sucesso');
            
        } catch (error) {
            console.error('❌ Erro ao excluir proposta:', error);
            throw error;
        }
    }
    
    /**
     * Buscar processos com filtros
     * @param {Object} filtros - Filtros para a busca
     * @returns {Array} Array de processos
     */
    static async buscarProcessos(filtros = {}) {
        try {
            console.log('🔍 Buscando processos com filtros:', filtros);
            
            let q = collection(db, 'processos');
            
            // Aplicar filtros
            if (filtros.status) {
                q = query(q, where('status', '==', filtros.status));
            }
            
            if (filtros.modalidade) {
                q = query(q, where('modalidade', '==', filtros.modalidade));
            }
            
            // Ordenar por data de criação
            q = query(q, orderBy('dataCriacao', 'desc'));
            
            const querySnapshot = await getDocs(q);
            const processos = [];
            
            querySnapshot.forEach((docSnap) => {
                processos.push({
                    id: docSnap.id,
                    ...docSnap.data()
                });
            });
            
            console.log('✅ Processos encontrados:', processos.length);
            return processos;
            
        } catch (error) {
            console.error('❌ Erro ao buscar processos:', error);
            throw error;
        }
    }
    
    /**
     * Escutar mudanças em tempo real
     * @param {string} colecao - Nome da coleção
     * @param {Function} callback - Função de callback
     * @param {Object} filtros - Filtros opcionais
     * @returns {Function} Função para cancelar a escuta
     */
    static escutarMudancas(colecao, callback, filtros = {}) {
        try {
            let q = collection(db, colecao);
            
            // Aplicar filtros se fornecidos
            Object.entries(filtros).forEach(([campo, valor]) => {
                q = query(q, where(campo, '==', valor));
            });
            
            return onSnapshot(q, (querySnapshot) => {
                const dados = [];
                querySnapshot.forEach((doc) => {
                    dados.push({
                        id: doc.id,
                        ...doc.data()
                    });
                });
                callback(dados);
            });
            
        } catch (error) {
            console.error('❌ Erro ao escutar mudanças:', error);
            throw error;
        }
    }
}

// Exportar a classe
export default FirebaseFirestore;

// Disponibilizar globalmente para compatibilidade
if (typeof window !== 'undefined') {
    window.FirebaseFirestore = FirebaseFirestore;
}

console.log('🔥 Firebase Firestore módulo carregado');