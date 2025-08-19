// 🔄 Função de Migração de Dados - Compatibilidade com Sistema Antigo

function migrarDadosParaNovasChaves() {
    console.log('🔄 Iniciando migração de dados para novas chaves...');
    
    try {
        // 1. Migrar Fornecedores
        const fornecedoresAntigos = localStorage.getItem('fornecedores_cadastrados');
        if (fornecedoresAntigos && !localStorage.getItem('sistema_fornecedores')) {
            localStorage.setItem('sistema_fornecedores', fornecedoresAntigos);
            console.log('✅ Fornecedores migrados: fornecedores_cadastrados → sistema_fornecedores');
        }
        
        // 2. Migrar Usuários Fornecedores
        const usuariosAntigos = localStorage.getItem('usuarios_fornecedores');
        if (usuariosAntigos && !localStorage.getItem('sistema_usuarios_fornecedores')) {
            localStorage.setItem('sistema_usuarios_fornecedores', usuariosAntigos);
            console.log('✅ Usuários fornecedores migrados: usuarios_fornecedores → sistema_usuarios_fornecedores');
        }
        
        // 3. Migrar Processos
        const processosAntigos = localStorage.getItem('processos_licitatorios');
        if (processosAntigos && !localStorage.getItem('sistema_processos')) {
            localStorage.setItem('sistema_processos', processosAntigos);
            console.log('✅ Processos migrados: processos_licitatorios → sistema_processos');
        }
        
        // 4. Migrar Propostas
        const propostasAntigas = localStorage.getItem('propostas_fornecedores');
        if (propostasAntigas && !localStorage.getItem('sistema_propostas')) {
            localStorage.setItem('sistema_propostas', propostasAntigas);
            console.log('✅ Propostas migradas: propostas_fornecedores → sistema_propostas');
        }
        
        // 5. Migrar Propostas Completas
        const propostasCompletasAntigas = localStorage.getItem('propostas_completas');
        if (propostasCompletasAntigas && !localStorage.getItem('sistema_propostas_completas')) {
            localStorage.setItem('sistema_propostas_completas', propostasCompletasAntigas);
            console.log('✅ Propostas completas migradas: propostas_completas → sistema_propostas_completas');
        }
        
        // 6. Migrar Análises IA
        const analisesAntigas = localStorage.getItem('analises_ia');
        if (analisesAntigas && !localStorage.getItem('sistema_analises_ia')) {
            localStorage.setItem('sistema_analises_ia', analisesAntigas);
            console.log('✅ Análises IA migradas: analises_ia → sistema_analises_ia');
        }
        
        console.log('✅ Migração de dados concluída com sucesso!');
        
    } catch (error) {
        console.error('❌ Erro durante migração de dados:', error);
    }
}

// Função para carregar dados com fallback automático
function carregarComFallback(chaveNova, chaveAntiga, padrao = []) {
    try {
        // Tentar carregar da chave nova primeiro
        let dados = localStorage.getItem(chaveNova);
        
        // Se não existir, tentar chave antiga
        if (!dados) {
            dados = localStorage.getItem(chaveAntiga);
            
            // Se encontrou na chave antiga, migrar para nova
            if (dados) {
                localStorage.setItem(chaveNova, dados);
                console.log(`🔄 Dados migrados automaticamente: ${chaveAntiga} → ${chaveNova}`);
            }
        }
        
        return dados ? JSON.parse(dados) : padrao;
        
    } catch (error) {
        console.error(`❌ Erro ao carregar dados (${chaveNova}/${chaveAntiga}):`, error);
        return padrao;
    }
}

// Executar migração automaticamente quando o script for carregado
if (typeof window !== 'undefined') {
    // Executar após 1 segundo para garantir que o sistema esteja carregado
    setTimeout(migrarDadosParaNovasChaves, 1000);
}

