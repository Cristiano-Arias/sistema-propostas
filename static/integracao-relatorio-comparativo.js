// ========================================
// INTEGRAÇÃO DO RELATÓRIO ANALÍTICO
// Adicione este código ao dashboard-comparativo.html
// ========================================

// Função para adicionar botão de relatório no dashboard comparativo
function adicionarBotaoRelatorio() {
    // Procurar pelos botões de exportação existentes
    const exportButtons = document.querySelectorAll('.export-buttons');
    
    exportButtons.forEach(buttonContainer => {
        // Verificar se já não existe o botão
        if (!buttonContainer.querySelector('.btn-relatorio-analitico')) {
            // Criar botão do relatório
            const btnRelatorio = document.createElement('button');
            btnRelatorio.className = 'btn btn-success btn-relatorio-analitico';
            btnRelatorio.innerHTML = `
                <i class="fas fa-file-alt"></i> Relatório Analítico
            `;
            btnRelatorio.style.cssText = `
                background: linear-gradient(135deg, #27ae60, #229954);
                border: none;
                color: white;
                font-weight: 600;
            `;
            
            // Adicionar evento de clique
            btnRelatorio.onclick = function() {
                gerarRelatorioAnalitico();
            };
            
            // Inserir o botão
            buttonContainer.appendChild(btnRelatorio);
        }
    });
}

// Função para gerar o relatório analítico
function gerarRelatorioAnalitico() {
    // Verificar se há um processo carregado
    if (!window.comparativoReal || !window.comparativoReal.currentProcess) {
        alert('Selecione um processo antes de gerar o relatório.');
        return;
    }
    
    // Verificar se há propostas
    if (!window.comparativoReal.proposals || window.comparativoReal.proposals.length === 0) {
        alert('Não há propostas para gerar o relatório.');
        return;
    }
    
    // Salvar o processo atual no sessionStorage
    sessionStorage.setItem('processoRelatorio', window.comparativoReal.currentProcess);
    
    // Abrir o relatório em nova aba
    window.open('relatorio-analitico-propostas.html?processo=' + window.comparativoReal.currentProcess, '_blank');
}

// Adicionar CSS personalizado para o botão
function adicionarEstilosRelatorio() {
    const style = document.createElement('style');
    style.textContent = `
        .btn-relatorio-analitico {
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .btn-relatorio-analitico:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(39, 174, 96, 0.3);
        }
        
        .btn-relatorio-analitico:active {
            transform: translateY(0);
        }
        
        /* Animação de destaque para o novo botão */
        @keyframes pulseNew {
            0% {
                box-shadow: 0 0 0 0 rgba(39, 174, 96, 0.7);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(39, 174, 96, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(39, 174, 96, 0);
            }
        }
        
        .btn-relatorio-analitico.novo {
            animation: pulseNew 2s infinite;
        }
    `;
    document.head.appendChild(style);
}

// Função para inicializar a integração
function inicializarIntegracaoRelatorio() {
    console.log('🚀 Inicializando integração do Relatório Analítico...');
    
    // Adicionar estilos
    adicionarEstilosRelatorio();
    
    // Aguardar o carregamento completo do comparativo
    setTimeout(() => {
        // Adicionar botões
        adicionarBotaoRelatorio();
        
        // Adicionar classe de destaque temporariamente
        const botoes = document.querySelectorAll('.btn-relatorio-analitico');
        botoes.forEach(btn => {
            btn.classList.add('novo');
            setTimeout(() => btn.classList.remove('novo'), 5000);
        });
        
        console.log('✅ Botão de Relatório Analítico adicionado!');
    }, 1000);
    
    // Observar mudanças no DOM para adicionar botão em conteúdo dinâmico
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                adicionarBotaoRelatorio();
            }
        });
    });
    
    // Observar o container principal
    const mainContainer = document.querySelector('.container');
    if (mainContainer) {
        observer.observe(mainContainer, {
            childList: true,
            subtree: true
        });
    }
}

// ========================================
// ADICIONE TAMBÉM NO MÓDULO COMPRADOR
// Para o dashboard-comprador-funcional.html
// ========================================

// Função para abrir relatório do módulo comprador
function abrirRelatorioAnalitico(processoId) {
    if (!processoId) {
        alert('Processo não identificado.');
        return;
    }
    
    // Verificar se há propostas para o processo
    const propostasCompletas = JSON.parse(localStorage.getItem('propostas_completas') || '[]');
    const propostasFornecedores = JSON.parse(localStorage.getItem('propostas_fornecedores') || '[]');
    
    const temPropostas = propostasCompletas.some(p => p.processoId === processoId) ||
                        propostasFornecedores.some(p => p.processoId === processoId);
    
    if (!temPropostas) {
        alert('Não há propostas para este processo.');
        return;
    }
    
    // Salvar processo e abrir relatório
    sessionStorage.setItem('processoRelatorio', processoId);
    window.open('relatorio-analitico-propostas.html?processo=' + processoId, '_blank');
}

// Adicionar botão nos cards de processo do comprador
function adicionarBotaoRelatorioComprador() {
    const processosComPropostas = document.querySelectorAll('.tr-item');
    
    processosComPropostas.forEach(processo => {
        // Verificar se tem propostas
        const temPropostas = processo.innerHTML.includes('Propostas Recebidas');
        
        if (temPropostas) {
            // Procurar container de botões
            const botoesContainer = processo.querySelector('div[style*="margin-top: 15px"]');
            
            if (botoesContainer && !botoesContainer.querySelector('.btn-relatorio-analitico')) {
                // Extrair ID do processo
                const onclickAttr = processo.querySelector('[onclick*="visualizarProcesso"]')?.getAttribute('onclick');
                const processoId = onclickAttr?.match(/'([^']+)'/)?.[1];
                
                if (processoId) {
                    // Criar botão
                    const btnRelatorio = document.createElement('button');
                    btnRelatorio.className = 'btn btn-success btn-relatorio-analitico';
                    btnRelatorio.innerHTML = '<i class="fas fa-file-alt"></i> Relatório Analítico';
                    btnRelatorio.onclick = () => abrirRelatorioAnalitico(processoId);
                    
                    // Adicionar após o botão de análise comparativa
                    const btnComparativo = botoesContainer.querySelector('.btn-success');
                    if (btnComparativo) {
                        btnComparativo.insertAdjacentElement('afterend', btnRelatorio);
                    } else {
                        botoesContainer.appendChild(btnRelatorio);
                    }
                }
            }
        }
    });
}

// ========================================
// INICIALIZAÇÃO
// ========================================

// Detectar em qual página estamos e inicializar adequadamente
document.addEventListener('DOMContentLoaded', function() {
    // Se estiver no dashboard comparativo
    if (window.location.href.includes('dashboard-comparativo')) {
        inicializarIntegracaoRelatorio();
    }
    
    // Se estiver no dashboard do comprador
    if (window.location.href.includes('dashboard-comprador')) {
        // Aguardar carregamento dos processos
        setTimeout(() => {
            adicionarBotaoRelatorioComprador();
            
            // Observar mudanças para processos carregados dinamicamente
            const observer = new MutationObserver(() => {
                adicionarBotaoRelatorioComprador();
            });
            
            const container = document.getElementById('processos-list');
            if (container) {
                observer.observe(container, { childList: true, subtree: true });
            }
        }, 2000);
    }
});