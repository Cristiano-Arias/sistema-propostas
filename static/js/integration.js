/**
 * Scripts de Integração - Adiciona funcionalidades ao sistema existente
 * Mantém compatibilidade total com o código atual
 */

// ========================================
// INTEGRAÇÃO PARA DASHBOARD-REQUISITANTE
// ========================================

if (window.location.pathname.includes('dashboard-requisitante')) {
    // Carregar TRs do backend além do localStorage
    async function carregarTRsIntegrado() {
        try {
            // Tenta carregar do backend
            const trs = await apiClient.getTRs();
            
            // Atualiza tabela se existir
            const tbody = document.querySelector('#tabela-trs tbody');
            if (tbody && trs.length > 0) {
                tbody.innerHTML = '';
                trs.forEach(tr => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${tr.numero || 'TR-' + tr.id}</td>
                        <td>${tr.titulo}</td>
                        <td>${new Date(tr.data_criacao).toLocaleDateString('pt-BR')}</td>
                        <td><span class="badge ${getStatusClass(tr.status)}">${tr.status}</span></td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="visualizarTR(${tr.id})">
                                <i class="fas fa-eye"></i> Ver
                            </button>
                            ${tr.status === 'rascunho' ? `
                                <button class="btn btn-sm btn-warning" onclick="editarTR(${tr.id})">
                                    <i class="fas fa-edit"></i> Editar
                                </button>
                            ` : ''}
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }
        } catch (error) {
            console.log('Usando dados locais:', error);
            // Mantém comportamento original com localStorage
        }
    }

    // Adicionar função de visualizar TR
    window.visualizarTR = async function(id) {
        try {
            const tr = await apiClient.getTR(id);
            
            // Criar modal para visualização
            const modal = document.createElement('div');
            modal.className = 'modal fade show d-block';
            modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Termo de Referência - ${tr.numero || 'TR-' + tr.id}</h5>
                            <button type="button" class="close" onclick="this.closest('.modal').remove()">
                                <span>&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <h6>Título: ${tr.titulo}</h6>
                            <p><strong>Objeto:</strong> ${tr.objeto}</p>
                            <p><strong>Justificativa:</strong> ${tr.justificativa}</p>
                            <p><strong>Prazo de Entrega:</strong> ${tr.prazo_entrega} dias</p>
                            <p><strong>Status:</strong> <span class="badge ${getStatusClass(tr.status)}">${tr.status}</span></p>
                            
                            ${tr.status === 'aprovado' ? `
                                <div class="alert alert-success">
                                    <i class="fas fa-check-circle"></i> Este TR foi aprovado pelo comprador
                                </div>
                            ` : ''}
                            
                            ${tr.status === 'reprovado' ? `
                                <div class="alert alert-danger">
                                    <i class="fas fa-times-circle"></i> Este TR foi reprovado
                                    <p>Motivo: ${tr.motivo_reprovacao || 'Não especificado'}</p>
                                </div>
                            ` : ''}
                        </div>
                        <div class="modal-footer">
                            <button class="btn btn-primary" onclick="baixarTRPDF(${tr.id})">
                                <i class="fas fa-download"></i> Baixar PDF
                            </button>
                            <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Fechar</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        } catch (error) {
            alert('Erro ao visualizar TR');
        }
    };

    // Baixar TR em PDF
    window.baixarTRPDF = async function(id) {
        try {
            await apiClient.downloadTRPDF(id);
        } catch (error) {
            alert('Erro ao baixar PDF');
        }
    };

    // Carregar ao iniciar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', carregarTRsIntegrado);
    } else {
        carregarTRsIntegrado();
    }
}

// ========================================
// INTEGRAÇÃO PARA CRIAR-TR
// ========================================

if (window.location.pathname.includes('criar-tr')) {
    // Interceptar formulário de criação de TR
    const formTR = document.getElementById('form-tr');
    if (formTR) {
        // Remover listener antigo e adicionar novo
        const novoForm = formTR.cloneNode(true);
        formTR.parentNode.replaceChild(novoForm, formTR);
        
        novoForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const dados = {
                titulo: document.getElementById('titulo').value,
                objeto: document.getElementById('objeto').value,
                justificativa: document.getElementById('justificativa').value,
                especificacoes: document.getElementById('especificacoes').value,
                prazo_entrega: document.getElementById('prazo').value,
                local_entrega: document.getElementById('local').value,
                condicoes_pagamento: document.getElementById('pagamento').value,
                garantia: document.getElementById('garantia').value,
                criterios_aceitacao: document.getElementById('criterios').value
            };

            try {
                // Tentar salvar no backend
                const result = await apiClient.criarTR(dados);

                // Normalizar objeto salvo
                const novoTr = {
                    ...dados,
                    id: result.id,
                    data: new Date().toISOString(),
                    status: 'pendente'
                };

                // Carregar lista existente nas duas chaves compatíveis
                const listaSistema = JSON.parse(localStorage.getItem('sistema_trs') || '[]');
                listaSistema.push(novoTr);

                // Persistir em ambas as chaves para compatibilidade
                localStorage.setItem('sistema_trs', JSON.stringify(listaSistema));
                localStorage.setItem('termos_referencia', JSON.stringify(listaSistema));

                alert('Termo de Referência criado com sucesso! O comprador será notificado.');
                window.location.href = 'dashboard-requisitante.html';
            } catch (error) {
                // Fallback offline: gerar ID local e persistir
                const novoTr = {
                    ...dados,
                    id: Date.now(),
                    data: new Date().toISOString(),
                    status: 'pendente'
                };
                
                // Carregar lista existente nas duas chaves compatíveis
                const listaSistema = JSON.parse(localStorage.getItem('sistema_trs') || '[]');
                listaSistema.push(novoTr);

                // Persistir em ambas as chaves
                localStorage.setItem('sistema_trs', JSON.stringify(listaSistema));
                localStorage.setItem('termos_referencia', JSON.stringify(listaSistema));

                alert('TR salvo localmente com sucesso!');
                window.location.href = 'dashboard-requisitante.html';
            }
        });
    }
}

// ========================================
// INTEGRAÇÃO PARA DASHBOARD-COMPRADOR
// ========================================

if (window.location.pathname.includes('dashboard-comprador')) {
    // Carregar TRs pendentes de aprovação
    async function carregarTRsPendentes() {
        try {
            const trs = await apiClient.getTRsPendentes();
            
            const container = document.querySelector('.trs-pendentes');
            if (container && trs.length > 0) {
                container.innerHTML = '<h4>TRs Pendentes de Aprovação</h4>';
                
                trs.forEach(tr => {
                    const card = document.createElement('div');
                    card.className = 'card mb-3';
                    card.innerHTML = `
                        <div class="card-body">
                            <h5 class="card-title">${tr.titulo}</h5>
                            <p class="card-text">${tr.objeto}</p>
                            <p><small class="text-muted">Criado em: ${new Date(tr.data_criacao).toLocaleDateString('pt-BR')}</small></p>
                            <button class="btn btn-info btn-sm" onclick="visualizarTRComprador(${tr.id})">
                                <i class="fas fa-eye"></i> Analisar
                            </button>
                        </div>
                    `;
                    container.appendChild(card);
                });
            }
        } catch (error) {
            console.log('Erro ao carregar TRs pendentes:', error);
        }
    }

    // Visualizar e aprovar/reprovar TR
    window.visualizarTRComprador = async function(id) {
        try {
            const tr = await apiClient.getTR(id);
            
            const modal = document.createElement('div');
            modal.className = 'modal fade show d-block';
            modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Análise de TR - ${tr.numero || 'TR-' + tr.id}</h5>
                            <button type="button" class="close" onclick="this.closest('.modal').remove()">
                                <span>&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <h6>Título: ${tr.titulo}</h6>
                            <p><strong>Objeto:</strong> ${tr.objeto}</p>
                            <p><strong>Justificativa:</strong> ${tr.justificativa}</p>
                            <p><strong>Especificações:</strong> ${tr.especificacoes}</p>
                            <p><strong>Prazo de Entrega:</strong> ${tr.prazo_entrega} dias</p>
                            
                            <hr>
                            
                            <div class="form-group">
                                <label>Parecer:</label>
                                <textarea id="parecer-tr" class="form-control" rows="3" placeholder="Digite seu parecer..."></textarea>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="btn btn-success" onclick="aprovarTR(${tr.id})">
                                <i class="fas fa-check"></i> Aprovar TR
                            </button>
                            <button class="btn btn-danger" onclick="reprovarTR(${tr.id})">
                                <i class="fas fa-times"></i> Reprovar TR
                            </button>
                            <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancelar</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        } catch (error) {
            alert('Erro ao visualizar TR');
        }
    };

    // Aprovar TR
    window.aprovarTR = async function(id) {
        const parecer = document.getElementById('parecer-tr').value;
        
        if (!parecer) {
            alert('Por favor, digite um parecer');
            return;
        }
        
        try {
            await apiClient.aprovarTR(id, parecer);
            alert('TR aprovado com sucesso! Você pode criar um processo de compra.');
            document.querySelector('.modal').remove();
            location.reload();
        } catch (error) {
            alert('Erro ao aprovar TR');
        }
    };

    // Reprovar TR
    window.reprovarTR = async function(id) {
        const motivo = document.getElementById('parecer-tr').value;
        
        if (!motivo) {
            alert('Por favor, informe o motivo da reprovação');
            return;
        }
        
        try {
            await apiClient.reprovarTR(id, motivo);
            alert('TR reprovado. O requisitante será notificado.');
            document.querySelector('.modal').remove();
            location.reload();
        } catch (error) {
            alert('Erro ao reprovar TR');
        }
    };

    // Adicionar seção de TRs pendentes
    const mainContent = document.querySelector('.container-fluid');
    if (mainContent && !document.querySelector('.trs-pendentes')) {
        const divPendentes = document.createElement('div');
        divPendentes.className = 'trs-pendentes mb-4';
        mainContent.insertBefore(divPendentes, mainContent.firstChild);
    }

    // Carregar ao iniciar
    carregarTRsPendentes();
}

// ========================================
// INTEGRAÇÃO PARA CRIAR-PROCESSO
// ========================================

if (window.location.pathname.includes('criar-processo')) {
    // Carregar TRs aprovados para selecionar
    async function carregarTRsAprovados() {
        try {
            const trs = await apiClient.getTRsAprovados();
            
            const select = document.createElement('select');
            select.className = 'form-control mb-3';
            select.id = 'tr-selecionado';
            select.innerHTML = '<option value="">Selecione um TR aprovado...</option>';
            
            trs.forEach(tr => {
                const option = document.createElement('option');
                option.value = tr.id;
                option.textContent = `${tr.numero || 'TR-' + tr.id} - ${tr.titulo}`;
                select.appendChild(option);
            });
            
            // Adicionar antes do primeiro campo do formulário
            const form = document.querySelector('#form-processo');
            if (form) {
                const firstField = form.querySelector('.form-group');
                const div = document.createElement('div');
                div.className = 'form-group';
                div.innerHTML = '<label>Termo de Referência:</label>';
                div.appendChild(select);
                form.insertBefore(div, firstField);
                
                // Preencher campos ao selecionar TR
                select.addEventListener('change', async function() {
                    if (this.value) {
                        const tr = await apiClient.getTR(this.value);
                        document.getElementById('objeto').value = tr.objeto;
                        document.getElementById('modalidade').focus();
                    }
                });
            }
        } catch (error) {
            console.log('Erro ao carregar TRs:', error);
        }
    }

    // Interceptar criação de processo
    const formProcesso = document.getElementById('form-processo');
    if (formProcesso) {
        const novoForm = formProcesso.cloneNode(true);
        formProcesso.parentNode.replaceChild(novoForm, formProcesso);
        
        novoForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const trId = document.getElementById('tr-selecionado')?.value;
            
            const dados = {
                tr_id: trId,
                numero: document.getElementById('numero').value,
                objeto: document.getElementById('objeto').value,
                modalidade: document.getElementById('modalidade').value,
                data_abertura: document.getElementById('data-abertura').value,
                hora_abertura: document.getElementById('hora-abertura').value,
                local_abertura: document.getElementById('local').value,
                prazo_proposta: document.getElementById('prazo-proposta').value,
                contato_email: document.getElementById('email-contato').value,
                contato_telefone: document.getElementById('telefone-contato').value
            };

            try {
                const result = await apiClient.criarProcesso(dados);
                
                // Também salvar localmente
                const processos = JSON.parse(localStorage.getItem('processos_compra') || '[]');
                processos.push({
                    ...dados,
                    id: result.id,
                    data_criacao: new Date().toISOString(),
                    status: 'aberto'
                });
                localStorage.setItem('processos_compra', JSON.stringify(processos));
                
                alert('Processo criado com sucesso! Agora você pode convidar fornecedores.');
                
                // Redirecionar para seleção de fornecedores
                window.location.href = `selecionar-fornecedores.html?processo=${result.id}`;
            } catch (error) {
                // Fallback local
                const processos = JSON.parse(localStorage.getItem('processos_compra') || '[]');
                dados.id = Date.now();
                dados.data_criacao = new Date().toISOString();
                dados.status = 'aberto';
                processos.push(dados);
                localStorage.setItem('processos_compra', JSON.stringify(processos));
                
                alert('Processo salvo localmente!');
                window.location.href = 'dashboard-comprador.html';
            }
        });
    }

    // Carregar ao iniciar
    carregarTRsAprovados();
}

// ========================================
// INTEGRAÇÃO PARA DASHBOARD-FORNECEDOR
// ========================================

if (window.location.pathname.includes('dashboard-fornecedor')) {
    // Carregar processos disponíveis
    async function carregarProcessosDisponiveis() {
        try {
            const processos = await apiClient.getProcessosDisponiveis();
            
            const container = document.querySelector('.processos-disponiveis');
            if (container && processos.length > 0) {
                container.innerHTML = '<h4>Processos Disponíveis</h4><div class="row"></div>';
                const row = container.querySelector('.row');
                
                processos.forEach(processo => {
                    const col = document.createElement('div');
                    col.className = 'col-md-6 mb-3';
                    col.innerHTML = `
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">Processo ${processo.numero}</h5>
                                <p class="card-text">${processo.objeto}</p>
                                <p><small>Modalidade: ${processo.modalidade}</small></p>
                                <p><small>Prazo: ${new Date(processo.data_abertura).toLocaleDateString('pt-BR')}</small></p>
                                <button class="btn btn-primary" onclick="participarProcesso(${processo.id})">
                                    <i class="fas fa-paper-plane"></i> Enviar Proposta
                                </button>
                            </div>
                        </div>
                    `;
                    row.appendChild(col);
                });
            }
        } catch (error) {
            console.log('Erro ao carregar processos:', error);
        }
    }

    // Participar de processo
    window.participarProcesso = function(processoId) {
        window.location.href = `enviar-proposta.html?processo=${processoId}`;
    };

    // Adicionar seção de processos disponíveis
    const mainContent = document.querySelector('.container-fluid');
    if (mainContent && !document.querySelector('.processos-disponiveis')) {
        const div = document.createElement('div');
        div.className = 'processos-disponiveis mb-4';
        mainContent.insertBefore(div, mainContent.firstChild);
    }

    // Carregar ao iniciar
    carregarProcessosDisponiveis();
}

// ========================================
// FUNÇÕES AUXILIARES
// ========================================

function getStatusClass(status) {
    const classes = {
        'rascunho': 'badge-secondary',
        'pendente': 'badge-warning',
        'aprovado': 'badge-success',
        'reprovado': 'badge-danger',
        'aberto': 'badge-primary',
        'em_analise': 'badge-info',
        'finalizado': 'badge-dark'
    };
    return classes[status] || 'badge-secondary';
}

// ========================================
// SISTEMA DE NOTIFICAÇÕES
// ========================================

// Verificar notificações a cada 30 segundos
if (Auth.isAuthenticated()) {
    async function verificarNotificacoes() {
        try {
            const notificacoes = await apiClient.getNotificacoes();
            
            if (notificacoes.length > 0) {
                // Mostrar badge no menu
                const badge = document.querySelector('.notificacao-badge');
                if (badge) {
                    badge.textContent = notificacoes.length;
                    badge.style.display = 'inline-block';
                }
                
                // Mostrar primeira notificação não lida
                const naoLida = notificacoes.find(n => !n.lida);
                if (naoLida) {
                    mostrarNotificacao(naoLida);
                }
            }
        } catch (error) {
            console.log('Erro ao verificar notificações:', error);
        }
    }

    function mostrarNotificacao(notificacao) {
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.innerHTML = `
            <div class="toast-header">
                <strong>${notificacao.titulo}</strong>
                <button onclick="this.closest('.toast-notification').remove()">×</button>
            </div>
            <div class="toast-body">
                ${notificacao.mensagem}
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Marcar como lida
        apiClient.marcarNotificacaoLida(notificacao.id);
        
        // Remover após 5 segundos
        setTimeout(() => toast.remove(), 5000);
    }

    // Verificar a cada 30 segundos
    setInterval(verificarNotificacoes, 30000);
    
    // Verificar ao carregar
    verificarNotificacoes();
}

// ========================================
// INICIALIZAÇÃO
// ========================================

console.log('Sistema de integração carregado com sucesso!');