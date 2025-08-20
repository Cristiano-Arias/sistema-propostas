// Sistema de Recuperação e Migração de Dados
// Recupera dados perdidos, migra entre versões e mantém integridade

class SistemaRecuperacaoDados {
    constructor() {
        this.db = null;
        this.firebaseReady = false;
        this.versaoAtual = '2.0.0';
        this.versoesSuportadas = ['1.0.0', '1.5.0', '2.0.0'];
        
        // Mapeamento de chaves antigas para novas
        this.mapeamentoChaves = {
            // Versão 1.0.0 -> 2.0.0
            'termos_referencia': 'sistema_trs',
            'processos_licitatorios': 'processos_compra',
            'propostas': 'sistema_propostas',
            'usuarios_fornecedores': 'fornecedores_cadastrados',
            
            // Chaves específicas de módulos
            'fornecedor_logado': 'fornecedor_logado',
            'comprador_logado': 'comprador_logado',
            'requisitante_logado': 'requisitante_logado'
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
            
            console.log('✅ Sistema de Recuperação de Dados inicializado');
            
            // Verificar e executar migrações necessárias
            await this.verificarMigracoes();
            
        } catch (error) {
            console.error('❌ Erro ao inicializar Sistema de Recuperação:', error);
            this.firebaseReady = false;
        }
    }
    
    // Verificar e executar migrações necessárias
    async verificarMigracoes() {
        try {
            const versaoLocal = localStorage.getItem('sistema_versao') || '1.0.0';
            
            if (versaoLocal !== this.versaoAtual) {
                console.log(`🔄 Migração necessária: ${versaoLocal} -> ${this.versaoAtual}`);
                await this.executarMigracao(versaoLocal, this.versaoAtual);
            } else {
                console.log('✅ Sistema atualizado, nenhuma migração necessária');
            }
            
        } catch (error) {
            console.error('❌ Erro ao verificar migrações:', error);
        }
    }
    
    // Executar migração entre versões
    async executarMigracao(versaoOrigem, versaoDestino) {
        try {
            console.log(`🔄 Iniciando migração ${versaoOrigem} -> ${versaoDestino}`);
            
            // Criar backup antes da migração
            await this.criarBackupMigracao(versaoOrigem);
            
            // Executar migrações específicas
            if (versaoOrigem === '1.0.0' && versaoDestino === '2.0.0') {
                await this.migrarV1ParaV2();
            } else if (versaoOrigem === '1.5.0' && versaoDestino === '2.0.0') {
                await this.migrarV15ParaV2();
            }
            
            // Atualizar versão
            localStorage.setItem('sistema_versao', versaoDestino);
            localStorage.setItem('migracao_executada', new Date().toISOString());
            
            console.log(`✅ Migração ${versaoOrigem} -> ${versaoDestino} concluída`);
            
        } catch (error) {
            console.error(`❌ Erro na migração ${versaoOrigem} -> ${versaoDestino}:`, error);
            await this.restaurarBackupMigracao(versaoOrigem);
        }
    }
    
    // Migração da versão 1.0.0 para 2.0.0
    async migrarV1ParaV2() {
        console.log('🔄 Executando migração v1.0.0 -> v2.0.0');
        
        // Migrar chaves do localStorage
        for (const [chaveAntiga, chaveNova] of Object.entries(this.mapeamentoChaves)) {
            const dados = localStorage.getItem(chaveAntiga);
            if (dados) {
                try {
                    const dadosParsed = JSON.parse(dados);
                    
                    // Aplicar transformações específicas se necessário
                    const dadosTransformados = await this.transformarDadosV1ParaV2(chaveAntiga, dadosParsed);
                    
                    // Salvar com nova chave
                    localStorage.setItem(chaveNova, JSON.stringify(dadosTransformados));
                    localStorage.setItem(`${chaveNova}_timestamp`, new Date().toISOString());
                    
                    console.log(`✅ Migrado: ${chaveAntiga} -> ${chaveNova}`);
                    
                } catch (error) {
                    console.error(`❌ Erro ao migrar ${chaveAntiga}:`, error);
                }
            }
        }
        
        // Migrar estruturas específicas
        await this.migrarEstruturasTRs();
        await this.migrarEstruturasProcessos();
        await this.migrarEstruturasPropostas();
    }
    
    // Transformar dados específicos da v1 para v2
    async transformarDadosV1ParaV2(chave, dados) {
        switch (chave) {
            case 'termos_referencia':
                return this.transformarTRsV1ParaV2(dados);
                
            case 'processos_licitatorios':
                return this.transformarProcessosV1ParaV2(dados);
                
            case 'propostas':
                return this.transformarPropostasV1ParaV2(dados);
                
            default:
                return dados;
        }
    }
    
    // Transformar TRs da v1 para v2
    transformarTRsV1ParaV2(trs) {
        if (!Array.isArray(trs)) return [];
        
        return trs.map(tr => ({
            ...tr,
            id: tr.id || this.gerarId(),
            versao: '2.0.0',
            criadoEm: tr.criadoEm || new Date().toISOString(),
            atualizadoEm: new Date().toISOString(),
            // Garantir campos obrigatórios
            numeroTR: tr.numeroTR || `TR-${Date.now()}`,
            titulo: tr.titulo || 'TR sem título',
            status: tr.status || 'ELABORADO'
        }));
    }
    
    // Transformar Processos da v1 para v2
    transformarProcessosV1ParaV2(processos) {
        if (!Array.isArray(processos)) return [];
        
        return processos.map(processo => ({
            ...processo,
            id: processo.id || this.gerarId(),
            versao: '2.0.0',
            criadoEm: processo.criadoEm || new Date().toISOString(),
            atualizadoEm: new Date().toISOString(),
            // Garantir campos obrigatórios
            numeroProcesso: processo.numeroProcesso || `PROC-${Date.now()}`,
            modalidade: processo.modalidade || 'PREGAO_ELETRONICO',
            status: processo.status || 'ELABORACAO'
        }));
    }
    
    // Transformar Propostas da v1 para v2
    transformarPropostasV1ParaV2(propostas) {
        if (!Array.isArray(propostas)) return [];
        
        return propostas.map(proposta => ({
            ...proposta,
            id: proposta.id || this.gerarId(),
            versao: '2.0.0',
            criadoEm: proposta.criadoEm || new Date().toISOString(),
            atualizadoEm: new Date().toISOString(),
            // Garantir campos obrigatórios
            protocolo: proposta.protocolo || `PROP-${Date.now()}`,
            status: proposta.status || 'RASCUNHO'
        }));
    }
    
    // Migrar estruturas específicas de TRs
    async migrarEstruturasTRs() {
        // Verificar se há TRs aprovados em estrutura antiga
        const trsAprovados = localStorage.getItem('trs_aprovados');
        if (trsAprovados) {
            try {
                const dados = JSON.parse(trsAprovados);
                const dadosTransformados = this.transformarTRsV1ParaV2(dados);
                
                // Mesclar com TRs existentes
                const trsExistentes = JSON.parse(localStorage.getItem('sistema_trs') || '[]');
                const trsMesclados = this.mesclarArraysPorId(trsExistentes, dadosTransformados);
                
                localStorage.setItem('sistema_trs', JSON.stringify(trsMesclados));
                console.log('✅ TRs aprovados migrados');
                
            } catch (error) {
                console.error('❌ Erro ao migrar TRs aprovados:', error);
            }
        }
    }
    
    // Migrar estruturas específicas de Processos
    async migrarEstruturasProcessos() {
        // Verificar estruturas antigas de processos
        const chavesProcessos = ['processos', 'processos_compra_antigo', 'sistema_processos'];
        
        for (const chave of chavesProcessos) {
            const dados = localStorage.getItem(chave);
            if (dados) {
                try {
                    const processos = JSON.parse(dados);
                    const processosTransformados = this.transformarProcessosV1ParaV2(processos);
                    
                    // Mesclar com processos existentes
                    const processosExistentes = JSON.parse(localStorage.getItem('processos_compra') || '[]');
                    const processosMesclados = this.mesclarArraysPorId(processosExistentes, processosTransformados);
                    
                    localStorage.setItem('processos_compra', JSON.stringify(processosMesclados));
                    console.log(`✅ Processos de ${chave} migrados`);
                    
                } catch (error) {
                    console.error(`❌ Erro ao migrar processos de ${chave}:`, error);
                }
            }
        }
    }
    
    // Migrar estruturas específicas de Propostas
    async migrarEstruturasPropostas() {
        // Verificar estruturas antigas de propostas
        const chavesPropostas = ['propostas_fornecedores', 'sistema_propostas_antigo'];
        
        for (const chave of chavesPropostas) {
            const dados = localStorage.getItem(chave);
            if (dados) {
                try {
                    const propostas = JSON.parse(dados);
                    const propostasTransformadas = this.transformarPropostasV1ParaV2(propostas);
                    
                    // Mesclar com propostas existentes
                    const propostasExistentes = JSON.parse(localStorage.getItem('sistema_propostas') || '[]');
                    const propostasMescladas = this.mesclarArraysPorId(propostasExistentes, propostasTransformadas);
                    
                    localStorage.setItem('sistema_propostas', JSON.stringify(propostasMescladas));
                    console.log(`✅ Propostas de ${chave} migradas`);
                    
                } catch (error) {
                    console.error(`❌ Erro ao migrar propostas de ${chave}:`, error);
                }
            }
        }
    }
    
    // Mesclar arrays por ID, evitando duplicatas
    mesclarArraysPorId(array1, array2) {
        const mapa = new Map();
        
        // Adicionar itens do primeiro array
        array1.forEach(item => {
            if (item.id) {
                mapa.set(item.id, item);
            }
        });
        
        // Adicionar itens do segundo array (sobrescreve se já existe)
        array2.forEach(item => {
            if (item.id) {
                mapa.set(item.id, item);
            }
        });
        
        return Array.from(mapa.values());
    }
    
    // Criar backup antes da migração
    async criarBackupMigracao(versao) {
        try {
            const backup = {
                versao: versao,
                timestamp: new Date().toISOString(),
                dados: {}
            };
            
            // Coletar todos os dados do localStorage
            for (let i = 0; i < localStorage.length; i++) {
                const chave = localStorage.key(i);
                if (chave && !chave.startsWith('_')) {
                    backup.dados[chave] = localStorage.getItem(chave);
                }
            }
            
            // Salvar backup localmente
            localStorage.setItem(`backup_migracao_${versao}`, JSON.stringify(backup));
            
            // Salvar backup no Firebase se disponível
            if (this.firebaseReady) {
                const { doc, setDoc } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
                const backupRef = doc(this.db, 'backups_migracao', `backup_${versao}_${Date.now()}`);
                await setDoc(backupRef, backup);
            }
            
            console.log(`💾 Backup de migração criado para versão ${versao}`);
            
        } catch (error) {
            console.error(`❌ Erro ao criar backup de migração:`, error);
        }
    }
    
    // Restaurar backup de migração
    async restaurarBackupMigracao(versao) {
        try {
            const backupLocal = localStorage.getItem(`backup_migracao_${versao}`);
            
            if (backupLocal) {
                const backup = JSON.parse(backupLocal);
                
                // Restaurar dados
                for (const [chave, valor] of Object.entries(backup.dados)) {
                    localStorage.setItem(chave, valor);
                }
                
                console.log(`🔄 Backup de migração restaurado para versão ${versao}`);
                return true;
            }
            
            console.warn(`⚠️ Backup de migração não encontrado para versão ${versao}`);
            return false;
            
        } catch (error) {
            console.error(`❌ Erro ao restaurar backup de migração:`, error);
            return false;
        }
    }
    
    // Recuperar dados perdidos do Firebase
    async recuperarDadosFirebase() {
        if (!this.firebaseReady) {
            console.warn('Firebase não está disponível para recuperação');
            return false;
        }
        
        try {
            const { collection, getDocs } = await import('https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js');
            
            console.log('🔄 Iniciando recuperação de dados do Firebase...');
            
            // Recuperar dados principais
            const colecaoRef = collection(this.db, 'sistema_dados');
            const snapshot = await getDocs(colecaoRef);
            
            let dadosRecuperados = 0;
            
            snapshot.forEach(doc => {
                const dados = doc.data();
                const chave = dados.chave || doc.id;
                
                // Verificar se dados locais existem
                const dadosLocais = localStorage.getItem(chave);
                
                if (!dadosLocais || dadosLocais === 'null' || dadosLocais === '[]') {
                    // Recuperar dados do Firebase
                    localStorage.setItem(chave, JSON.stringify(dados.dados));
                    localStorage.setItem(`${chave}_timestamp`, dados.timestamp);
                    dadosRecuperados++;
                    console.log(`🔄 Recuperado: ${chave}`);
                }
            });
            
            console.log(`✅ Recuperação concluída: ${dadosRecuperados} itens recuperados`);
            return true;
            
        } catch (error) {
            console.error('❌ Erro na recuperação de dados:', error);
            return false;
        }
    }
    
    // Verificar integridade dos dados
    async verificarIntegridade() {
        const problemas = [];
        
        // Verificar chaves essenciais
        const chavesEssenciais = [
            'sistema_trs',
            'processos_compra',
            'sistema_propostas',
            'fornecedores_cadastrados'
        ];
        
        for (const chave of chavesEssenciais) {
            const dados = localStorage.getItem(chave);
            
            if (!dados) {
                problemas.push(`Chave ausente: ${chave}`);
            } else {
                try {
                    const dadosParsed = JSON.parse(dados);
                    if (!Array.isArray(dadosParsed)) {
                        problemas.push(`Formato inválido: ${chave} não é array`);
                    }
                } catch (error) {
                    problemas.push(`JSON inválido: ${chave}`);
                }
            }
        }
        
        // Verificar consistência entre dados relacionados
        await this.verificarConsistenciaRelacionamentos(problemas);
        
        return {
            integro: problemas.length === 0,
            problemas: problemas
        };
    }
    
    // Verificar consistência entre dados relacionados
    async verificarConsistenciaRelacionamentos(problemas) {
        try {
            const trs = JSON.parse(localStorage.getItem('sistema_trs') || '[]');
            const processos = JSON.parse(localStorage.getItem('processos_compra') || '[]');
            const propostas = JSON.parse(localStorage.getItem('sistema_propostas') || '[]');
            
            // Verificar se processos têm TRs válidos
            processos.forEach(processo => {
                if (processo.tr_id && !trs.find(tr => tr.id === processo.tr_id)) {
                    problemas.push(`Processo ${processo.id} referencia TR inexistente: ${processo.tr_id}`);
                }
            });
            
            // Verificar se propostas têm processos válidos
            propostas.forEach(proposta => {
                if (proposta.processoId && !processos.find(p => p.id === proposta.processoId)) {
                    problemas.push(`Proposta ${proposta.id} referencia processo inexistente: ${proposta.processoId}`);
                }
            });
            
        } catch (error) {
            problemas.push(`Erro ao verificar consistência: ${error.message}`);
        }
    }
    
    // Reparar dados corrompidos
    async repararDados() {
        console.log('🔧 Iniciando reparação de dados...');
        
        const integridade = await this.verificarIntegridade();
        
        if (integridade.integro) {
            console.log('✅ Dados íntegros, nenhuma reparação necessária');
            return true;
        }
        
        // Tentar recuperar do Firebase primeiro
        await this.recuperarDadosFirebase();
        
        // Verificar novamente após recuperação
        const integridadePos = await this.verificarIntegridade();
        
        if (integridadePos.integro) {
            console.log('✅ Dados reparados com sucesso');
            return true;
        }
        
        // Se ainda há problemas, aplicar reparações específicas
        await this.aplicarReparacoesEspecificas(integridadePos.problemas);
        
        console.log('🔧 Reparação concluída');
        return true;
    }
    
    // Aplicar reparações específicas
    async aplicarReparacoesEspecificas(problemas) {
        for (const problema of problemas) {
            if (problema.includes('Chave ausente:')) {
                const chave = problema.split(': ')[1];
                localStorage.setItem(chave, JSON.stringify([]));
                console.log(`🔧 Chave criada: ${chave}`);
            }
            
            if (problema.includes('não é array')) {
                const chave = problema.split(': ')[1].split(' ')[0];
                localStorage.setItem(chave, JSON.stringify([]));
                console.log(`🔧 Array corrigido: ${chave}`);
            }
        }
    }
    
    // Gerar ID único
    gerarId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
    
    // Status do sistema
    obterStatus() {
        return {
            versaoAtual: this.versaoAtual,
            versaoLocal: localStorage.getItem('sistema_versao'),
            firebaseReady: this.firebaseReady,
            ultimaMigracao: localStorage.getItem('migracao_executada')
        };
    }
}

// Exportar para uso global
window.SistemaRecuperacaoDados = SistemaRecuperacaoDados;

// Criar instância global
window.SistemaRecuperacao = new SistemaRecuperacaoDados();

console.log('🔧 Sistema de Recuperação de Dados carregado');

