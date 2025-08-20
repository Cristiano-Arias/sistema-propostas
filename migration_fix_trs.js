// migration_fix_trs.js
function migrarTRs() {
    console.log('🔄 Iniciando migração de TRs...');
    
    // Buscar TRs na chave antiga
    const trsAntigos = localStorage.getItem('termos_referencia');
    
    if (trsAntigos) {
        try {
            const trs = JSON.parse(trsAntigos);
            
            // Salvar na nova chave
            localStorage.setItem('sistema_trs', JSON.stringify(trs));
            
            console.log(`✅ ${trs.length} TRs migrados com sucesso!`);
            
            // Opcional: remover chave antiga após confirmar que tudo funciona
            // localStorage.removeItem('termos_referencia');
            
        } catch (error) {
            console.error('❌ Erro na migração:', error);
        }
    } else {
        console.log('ℹ️ Nenhum TR para migrar');
    }
}

// Executar migração
migrarTRs();
