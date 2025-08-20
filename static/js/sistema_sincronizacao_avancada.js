// Sistema Avançado de Sincronização Firebase
// Inclui resolução de conflitos, sincronização bidirecional e recuperação de dados

class SistemaSincronizacaoAvancada {
    constructor() {
        this.db = null;
        this.firebaseReady = false;
        this.sincronizandoAtivamente = false;
        this.intervalSincronizacao = null;
        this.filaConflitos = [];
        this.ultimaSincronizacao = {};
        
        // Configurações
        this.config = {
            intervaloSincronizacao: 30000, // 30 segundos
            tentativasMaximas: 3,
            timeoutOperacao: 10000, // 10 segundos
            chavesPrioritarias: [
                'sistema_trs',
                'processos_compra',
                'sistema_propostas',
                'fornecedores_cadastrados'
            ]
        };
        
        this.inicializar();
    }
    
    async inicializar() {
        try {
            // Importar Firebase
            const { initializeApp } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js');
            const { getFirestore } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
            
            // Configuração Firebase
            const firebaseConfig = {
                apiKey: "AIzaSyCgF366Ft7RkZHYaZb77HboNO3BPbmCjT8",
                authDomain: "portal-de-proposta.firebaseapp.com",
                projectId: "portal-de-proposta",
                storageBucket: "portal-de-proposta.firebasestorage.app",
                messagingSenderId: "321036073908",
                appId: "1:321036073908:web:3149b9ea2cb77a704890e1"
            };
            
            const app = initializeApp(firebaseConfig);
            this.db = getFirestore(app);
            this.firebaseReady = true;
            
            console.log('✅ Sistema de Sincronização Avançada inicializado');
            
            // Iniciar sincronização automática
            this.iniciarSincronizacaoAutomatica();
            
            // Sincronização inicial
            await this.sincronizacaoCompleta();
            
        } catch (error) {
            console.error('❌ Erro ao inicializar Sistema de Sincronização:', error);
            this.firebaseReady = false;
        }
    }
    
    // Sincronização completa de todos os dados
    async sincronizacaoCompleta() {
        if (!this.firebaseReady || this.sincronizandoAtivamente) return;
        
        this.sincronizandoAtivamente = true;
        console.log('🔄 Iniciando sincronização completa...');
        
        try {
            // 1. Sincronizar chaves prioritárias primeiro
            for (const chave of this.config.chavesPrioritarias) {
                await this.sincronizarChave(chave);
            }
            
            // 2. Sincronizar outras chaves
            const todasChaves = this.obterTodasChavesLocalStorage();
            const chavesRestantes = todasChaves.filter(chave => 
                !this.config.chavesPrioritarias.includes(chave) && 
                !chave.endsWith('_timestamp') &&
                !chave.includes('_temp')
            );
            
            for (const chave of chavesRestantes) {
                await this.sincronizarChave(chave);
            }
            
            // 3. Resolver conflitos pendentes
            await this.resolverConflitos();
            
            this.ultimaSincronizacao.completa = new Date().toISOString();
            console.log('✅ Sincronização completa finalizada');
            
        } catch (error) {
            console.error('❌ Erro na sincronização completa:', error);
        } finally {
            this.sincronizandoAtivamente = false;
        }
    }
    
    // Sincronizar uma chave específica
    async sincronizarChave(chave) {
        try {
            const { doc, getDoc, setDoc } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
            
            // Obter dados locais
            const dadosLocal = this.obterDadosLocal(chave);
            const timestampLocal = this.obterTimestampLocal(chave);
            
            // Obter dados do Firebase
            const docRef = doc(this.db, 'sistema_dados', chave);
            const docSnap = await getDoc(docRef);
            
            if (docSnap.exists()) {
                const dadosFirebase = docSnap.data();
                const timestampFirebase = new Date(dadosFirebase.timestamp);
                const timestampLocalDate = new Date(timestampLocal);
                
                // Verificar qual versão é mais recente
                if (timestampFirebase > timestampLocalDate) {
                    // Firebase mais recente - atualizar local
                    await this.atualizarDadosLocal(chave, dadosFirebase.dados, dadosFirebase.timestamp);
                    console.log(`⬇️ ${chave}: Dados atualizados do Firebase`);
                    
                } else if (timestampLocalDate > timestampFirebase) {
                    // Local mais recente - atualizar Firebase
                    await this.atualizarDadosFirebase(chave, dadosLocal, timestampLocal);
                    console.log(`⬆️ ${chave}: Dados enviados para Firebase`);
                    
                } else {
                    // Mesma versão - verificar integridade
                    if (!this.compararDados(dadosLocal, dadosFirebase.dados)) {
                        // Dados diferentes com mesmo timestamp - conflito
                        await this.adicionarConflito(chave, dadosLocal, dadosFirebase.dados, timestampLocal);
                    }
                }
                
            } else if (dadosLocal !== null) {
                // Dados só existem localmente - enviar para Firebase
                await this.atualizarDadosFirebase(chave, dadosLocal, timestampLocal);
                console.log(`⬆️ ${chave}: Novos dados enviados para Firebase`);
            }
            
            this.ultimaSincronizacao[chave] = new Date().toISOString();
            
        } catch (error) {
            console.error(`❌ Erro ao sincronizar ${chave}:`, error);
        }
    }
    
    // Obter dados do localStorage
    obterDadosLocal(chave) {
        try {
            const dados = localStorage.getItem(chave);
            return dados ? JSON.parse(dados) : null;
        } catch (error) {
            console.error(`Erro ao obter dados locais de ${chave}:`, error);
            return null;
        }
    }
    
    // Obter timestamp local
    obterTimestampLocal(chave) {
        const timestamp = localStorage.getItem(`${chave}_timestamp`);
        return timestamp || new Date(0).toISOString();
    }
    
    // Atualizar dados locais
    async atualizarDadosLocal(chave, dados, timestamp) {
        try {
            localStorage.setItem(chave, JSON.stringify(dados));
            localStorage.setItem(`${chave}_timestamp`, timestamp);
            
            // Disparar evento de atualização
            window.dispatchEvent(new CustomEvent('dadosAtualizados', {
                detail: { chave, dados, origem: 'firebase' }
            }));
            
        } catch (error) {
            console.error(`Erro ao atualizar dados locais de ${chave}:`, error);
        }
    }
    
    // Atualizar dados no Firebase
    async atualizarDadosFirebase(chave, dados, timestamp) {
        try {
            const { doc, setDoc } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
            
            const docRef = doc(this.db, 'sistema_dados', chave);
            await setDoc(docRef, {
                dados: dados,
                timestamp: timestamp || new Date().toISOString(),
                chave: chave,
                ultimaAtualizacao: new Date().toISOString()
            });
            
        } catch (error) {
            console.error(`Erro ao atualizar dados Firebase de ${chave}:`, error);
            throw error;
        }
    }
    
    // Comparar dados para detectar diferenças
    compararDados(dados1, dados2) {
        try {
            return JSON.stringify(dados1) === JSON.stringify(dados2);
        } catch (error) {
            return false;
        }
    }
    
    // Adicionar conflito à fila
    async adicionarConflito(chave, dadosLocal, dadosFirebase, timestamp) {
        const conflito = {
            id: Date.now().toString(36) + Math.random().toString(36).substr(2),
            chave: chave,
            dadosLocal: dadosLocal,
            dadosFirebase: dadosFirebase,
            timestamp: timestamp,
            criadoEm: new Date().toISOString(),
            resolvido: false
        };
        
        this.filaConflitos.push(conflito);
        console.warn(`⚠️ Conflito detectado em ${chave}:`, conflito);
        
        // Tentar resolução automática
        await this.tentarResolucaoAutomatica(conflito);
    }
    
    // Tentar resolução automática de conflitos
    async tentarResolucaoAutomatica(conflito) {
        try {
            let dadosResolvidos = null;
            
            // Estratégias de resolução automática
            if (Array.isArray(conflito.dadosLocal) && Array.isArray(conflito.dadosFirebase)) {
                // Para arrays: mesclar e remover duplicatas
                dadosResolvidos = this.mesclarArrays(conflito.dadosLocal, conflito.dadosFirebase);
                
            } else if (typeof conflito.dadosLocal === 'object' && typeof conflito.dadosFirebase === 'object') {
                // Para objetos: mesclar propriedades
                dadosResolvidos = this.mesclarObjetos(conflito.dadosLocal, conflito.dadosFirebase);
                
            } else {
                // Para valores primitivos: usar o mais recente (Firebase)
                dadosResolvidos = conflito.dadosFirebase;
            }
            
            if (dadosResolvidos !== null) {
                // Aplicar resolução
                const novoTimestamp = new Date().toISOString();
                await this.atualizarDadosLocal(conflito.chave, dadosResolvidos, novoTimestamp);
                await this.atualizarDadosFirebase(conflito.chave, dadosResolvidos, novoTimestamp);
                
                conflito.resolvido = true;
                conflito.resolvidoEm = novoTimestamp;
                conflito.dadosResolvidos = dadosResolvidos;
                
                console.log(`✅ Conflito resolvido automaticamente para ${conflito.chave}`);
            }
            
        } catch (error) {
            console.error(`Erro ao resolver conflito automaticamente:`, error);
        }
    }
    
    // Mesclar arrays removendo duplicatas
    mesclarArrays(array1, array2) {
        try {
            const mapa = new Map();
            
            // Adicionar itens do primeiro array
            array1.forEach(item => {
                const chave = item.id || JSON.stringify(item);
                mapa.set(chave, item);
            });
            
            // Adicionar itens do segundo array (sobrescreve se já existe)
            array2.forEach(item => {
                const chave = item.id || JSON.stringify(item);
                mapa.set(chave, item);
            });
            
            return Array.from(mapa.values());
        } catch (error) {
            console.error('Erro ao mesclar arrays:', error);
            return array2; // Fallback para dados do Firebase
        }
    }
    
    // Mesclar objetos
    mesclarObjetos(obj1, obj2) {
        try {
            return { ...obj1, ...obj2 };
        } catch (error) {
            console.error('Erro ao mesclar objetos:', error);
            return obj2; // Fallback para dados do Firebase
        }
    }
    
    // Resolver conflitos pendentes
    async resolverConflitos() {
        const conflitosNaoResolvidos = this.filaConflitos.filter(c => !c.resolvido);
        
        if (conflitosNaoResolvidos.length === 0) return;
        
        console.log(`🔧 Resolvendo ${conflitosNaoResolvidos.length} conflitos pendentes...`);
        
        for (const conflito of conflitosNaoResolvidos) {
            if (!conflito.resolvido) {
                await this.tentarResolucaoAutomatica(conflito);
            }
        }
        
        // Limpar conflitos resolvidos antigos (mais de 1 hora)
        const agora = new Date();
        this.filaConflitos = this.filaConflitos.filter(conflito => {
            if (conflito.resolvido) {
                const tempoResolucao = new Date(conflito.resolvidoEm);
                return (agora - tempoResolucao) < 3600000; // 1 hora
            }
            return true;
        });
    }
    
    // Obter todas as chaves do localStorage
    obterTodasChavesLocalStorage() {
        const chaves = [];
        for (let i = 0; i < localStorage.length; i++) {
            chaves.push(localStorage.key(i));
        }
        return chaves.filter(chave => chave && !chave.startsWith('_'));
    }
    
    // Iniciar sincronização automática
    iniciarSincronizacaoAutomatica() {
        if (this.intervalSincronizacao) {
            clearInterval(this.intervalSincronizacao);
        }
        
        this.intervalSincronizacao = setInterval(() => {
            if (this.firebaseReady && !this.sincronizandoAtivamente) {
                this.sincronizacaoCompleta();
            }
        }, this.config.intervaloSincronizacao);
        
        console.log(`🔄 Sincronização automática iniciada (${this.config.intervaloSincronizacao/1000}s)`);
    }
    
    // Parar sincronização automática
    pararSincronizacaoAutomatica() {
        if (this.intervalSincronizacao) {
            clearInterval(this.intervalSincronizacao);
            this.intervalSincronizacao = null;
            console.log('⏹️ Sincronização automática parada');
        }
    }
    
    // Forçar sincronização de uma chave específica
    async sincronizarChaveEspecifica(chave) {
        if (!this.firebaseReady) {
            console.warn('Firebase não está pronto para sincronização');
            return false;
        }
        
        try {
            await this.sincronizarChave(chave);
            return true;
        } catch (error) {
            console.error(`Erro ao sincronizar ${chave}:`, error);
            return false;
        }
    }
    
    // Backup de emergência
    async criarBackupEmergencia() {
        try {
            const backup = {
                timestamp: new Date().toISOString(),
                dados: {}
            };
            
            // Coletar todos os dados do localStorage
            for (let i = 0; i < localStorage.length; i++) {
                const chave = localStorage.key(i);
                if (chave && !chave.startsWith('_') && !chave.endsWith('_timestamp')) {
                    backup.dados[chave] = this.obterDadosLocal(chave);
                }
            }
            
            // Salvar backup no Firebase
            const { doc, setDoc } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
            const backupRef = doc(this.db, 'backups', `backup_${Date.now()}`);
            await setDoc(backupRef, backup);
            
            console.log('💾 Backup de emergência criado');
            return true;
            
        } catch (error) {
            console.error('❌ Erro ao criar backup de emergência:', error);
            return false;
        }
    }
    
    // Status do sistema
    obterStatus() {
        return {
            firebaseReady: this.firebaseReady,
            sincronizandoAtivamente: this.sincronizandoAtivamente,
            conflitosNaoResolvidos: this.filaConflitos.filter(c => !c.resolvido).length,
            ultimaSincronizacao: this.ultimaSincronizacao,
            sincronizacaoAutomaticaAtiva: this.intervalSincronizacao !== null
        };
    }
}

// Exportar para uso global
window.SistemaSincronizacaoAvancada = SistemaSincronizacaoAvancada;

// Criar instância global
window.SistemaSincronizacao = new SistemaSincronizacaoAvancada();

console.log('🔄 Sistema de Sincronização Avançada carregado');

