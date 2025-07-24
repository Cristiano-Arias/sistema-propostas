// ===== PORTAL DE PROPOSTAS - SCRIPTS JAVASCRIPT =====
// Arquivo: portal-propostas-scripts.js

// ===== VARIÁVEIS GLOBAIS =====
let currentTab = 'dados';
let usuarioAtual = null;
let processoAtual = null;
let dadosSalvosTemp = {};

// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Iniciando Portal de Propostas...');
    
    // Verificar autenticação usando o Auth.js
    usuarioAtual = Auth.verificarAutenticacao(['fornecedor']);
    
    if (!usuarioAtual) {
        mostrarMensagem('Você precisa estar autenticado como fornecedor para acessar esta página.', 'error');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 2000);
        return;
    }
    
    // Exibir informações do usuário
    document.getElementById('authInfo').innerHTML = `
        <strong>${usuarioAtual.nome}</strong><br>
        <small>Fornecedor</small>
    `;
    
    // Carregar dados do processo
    const urlParams = new URLSearchParams(window.location.search);
    const numeroProcesso = urlParams.get('processo');
    
    if (!numeroProcesso) {
        mostrarMensagem('Nenhum processo especificado.', 'error');
        setTimeout(() => {
            window.location.href = 'dashboard-fornecedor.html';
        }, 2000);
        return;
    }
    
    carregarProcesso(numeroProcesso);
    
    // Carregar dados da empresa
    carregarDadosEmpresa();
    
    // Iniciar auto-save
    iniciarAutoSave();
    
    // Verificar rascunho existente
    verificarRascunho();
    
    // Atualizar progresso inicial
    updateProgress();
});

// ===== FUNÇÕES DE CARREGAMENTO =====
function carregarProcesso(numeroProcesso) {
    const processos = JSON.parse(localStorage.getItem('processos') || '[]');
    processoAtual = processos.find(p => p.numero === numeroProcesso);
    
    if (!processoAtual) {
        mostrarMensagem('Processo não encontrado.', 'error');
        setTimeout(() => {
            window.location.href = 'dashboard-fornecedor.html';
        }, 2000);
        return;
    }
    
    // Verificar se o fornecedor foi convidado
    if (processoAtual.fornecedoresConvidados && 
        !processoAtual.fornecedoresConvidados.includes(usuarioAtual.usuarioId)) {
        mostrarMensagem('Você não foi convidado para este processo.', 'error');
        setTimeout(() => {
            window.location.href = 'dashboard-fornecedor.html';
        }, 2000);
        return;
    }
    
    // Preencher dados do processo
    document.getElementById('numeroProcesso').value = processoAtual.numero;
    document.getElementById('objetoProcesso').value = processoAtual.objeto || '';
    
    if (processoAtual.prazo) {
        const prazoDate = new Date(processoAtual.prazo);
        document.getElementById('prazoEnvio').value = prazoDate.toLocaleString('pt-BR');
    }
    
    // Copiar objeto para proposta técnica
    document.getElementById('objetoConcorrencia').value = processoAtual.objeto || '';
}

function carregarDadosEmpresa() {
    // Buscar dados do cadastro do fornecedor
    const cadastros = JSON.parse(localStorage.getItem('cadastros_fornecedores') || '[]');
    const meuCadastro = cadastros.find(c => c.usuarioId === usuarioAtual.usuarioId);
    
    if (meuCadastro) {
        // Preencher dados cadastrais automaticamente
        document.getElementById('razaoSocial').value = meuCadastro.razaoSocial || '';
        document.getElementById('cnpj').value = meuCadastro.cnpj || '';
        document.getElementById('endereco').value = 
            `${meuCadastro.endereco || ''} ${meuCadastro.numero || ''} ${meuCadastro.complemento || ''}`.trim();
        document.getElementById('cidade').value = 
            `${meuCadastro.cidade || ''} - ${meuCadastro.estado || ''}`;
        document.getElementById('telefone').value = meuCadastro.telefone || '';
        document.getElementById('email').value = meuCadastro.email || '';
        document.getElementById('respTecnico').value = meuCadastro.responsavelTecnico || '';
        document.getElementById('crea').value = meuCadastro.registroTecnico || '';
    }
}

// ===== NAVEGAÇÃO ENTRE ABAS =====
function showTab(tabName, buttonElement) {
    // Validar aba atual antes de mudar
    if (!validarAbaAtual()) {
        return;
    }
    
    // Ocultar todas as seções
    document.querySelectorAll('.form-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Remover classe active de todas as abas
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Mostrar seção selecionada
    document.getElementById(tabName).classList.add('active');
    buttonElement.classList.add('active');
    
    currentTab = tabName;
    updateProgress();
    
    // Se for a aba de revisão, gerar resumo
    if (tabName === 'revisao') {
        gerarResumo();
    }
    
    // Scroll para o topo
    window.scrollTo(0, 0);
}

function updateProgress() {
    const tabs = ['dados', 'tecnica', 'comercial', 'revisao'];
    const currentIndex = tabs.indexOf(currentTab);
    const progress = ((currentIndex + 1) / tabs.length) * 100;
    
    document.getElementById('progressFill').style.width = progress + '%';
    document.getElementById('progressText').textContent = Math.round(progress) + '%';
}

// ===== VALIDAÇÕES =====
function validarAbaAtual() {
    let valido = true;
    
    if (currentTab === 'dados') {
        const camposObrigatorios = ['razaoSocial', 'cnpj', 'email'];
        camposObrigatorios.forEach(campo => {
            const elemento = document.getElementById(campo);
            if (!elemento.value.trim()) {
                elemento.style.borderColor = '#e74c3c';
                valido = false;
            } else {
                elemento.style.borderColor = '#e9ecef';
            }
        });
        
        if (!valido) {
            mostrarMensagem('Por favor, preencha todos os campos obrigatórios marcados com *.', 'error');
        }
    } else if (currentTab === 'tecnica') {
        const camposObrigatorios = ['objetoConcorrencia', 'metodologia', 'prazoExecucao'];
        camposObrigatorios.forEach(campo => {
            const elemento = document.getElementById(campo);
            if (!elemento.value.trim()) {
                elemento.style.borderColor = '#e74c3c';
                valido = false;
            } else {
                elemento.style.borderColor = '#e9ecef';
            }
        });
        
        if (!valido) {
            mostrarMensagem('Por favor, preencha todos os campos obrigatórios da proposta técnica.', 'error');
        }
    } else if (currentTab === 'comercial') {
        const valorTotal = document.getElementById('valorTotal');
        if (!valorTotal.value.trim() || limparValor(valorTotal.value) <= 0) {
            valorTotal.style.borderColor = '#e74c3c';
            valido = false;
            mostrarMensagem('Por favor, informe o valor total da proposta.', 'error');
        } else {
            valorTotal.style.borderColor = '#e9ecef';
        }
    }
    
    return valido;
}

// ===== FUNÇÕES DE TABELA DINÂMICA =====
function addEquipeRow() {
    const tbody = document.querySelector('#equipeTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Nome completo"></td>
        <td><input type="text" placeholder="Função"></td>
        <td><input type="text" placeholder="CREA/CAU"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addExperienciaRow() {
    const tbody = document.querySelector('#experienciaTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Descrição da obra"></td>
        <td><input type="text" placeholder="Nome do cliente"></td>
        <td><input type="number" placeholder="2024" min="1900" max="2030"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addCustoRow() {
    const tbody = document.querySelector('#custosTable tbody');
    const nextItem = tbody.rows.length + 1;
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" value="${nextItem}" readonly style="text-align: center;"></td>
        <td><input type="text" placeholder="Descrição do item/serviço"></td>
        <td><input type="number" placeholder="1" min="0" step="0.01" onchange="calcularTotal(this)"></td>
        <td><input type="text" placeholder="R$ 0,00" onblur="formatarValorUnitario(this)" onchange="calcularTotal(this)"></td>
        <td><input type="text" placeholder="R$ 0,00" readonly style="background: #f8f9fa;"></td>
        <td><button type="button" class="remove-btn" onclick="removeRowComCalculo(this)">×</button></td>
    `;
}

function removeRow(button) {
    const row = button.closest('tr');
    const tbody = row.parentElement;
    
    // Não remover se for a última linha
    if (tbody.rows.length > 1) {
        row.remove();
    } else {
        mostrarMensagem('Deve haver pelo menos um item na tabela.', 'error');
    }
}

function removeRowComCalculo(button) {
    const row = button.closest('tr');
    const tbody = row.parentElement;
    
    // Não remover se for a última linha
    if (tbody.rows.length > 1) {
        row.remove();
        // Renumerar itens
        renumerarItens();
        // Recalcular total
        calcularTotalGeral();
    } else {
        mostrarMensagem('Deve haver pelo menos um item na planilha.', 'error');
    }
}

function renumerarItens() {
    const tbody = document.querySelector('#custosTable tbody');
    const rows = tbody.rows;
    
    for (let i = 0; i < rows.length; i++) {
        const itemInput = rows[i].cells[0].querySelector('input');
        if (itemInput) {
            itemInput.value = i + 1;
        }
    }
}

// ===== CÁLCULOS E FORMATAÇÃO =====
function formatarValor(input) {
    let valor = input.value.replace(/\D/g, '');
    if (valor === '') {
        input.value = '';
        return;
    }
    
    valor = (parseInt(valor) / 100).toFixed(2);
    input.value = `R$ ${valor.replace('.', ',')}`;
}

function formatarValorUnitario(input) {
    formatarValor(input);
}

function limparValor(valor) {
    if (!valor) return 0;
    return parseFloat(valor.replace(/[^\d,.-]/g, '').replace('.', '').replace(',', '.')) || 0;
}

function calcularTotal(input) {
    const row = input.closest('tr');
    const qtdInput = row.cells[2].querySelector('input');
    const valorInput = row.cells[3].querySelector('input');
    const totalInput = row.cells[4].querySelector('input');
    
    const qtd = parseFloat(qtdInput.value) || 0;
    const valorUnit = limparValor(valorInput.value);
    const total = qtd * valorUnit;
    
    totalInput.value = `R$ ${total.toFixed(2).replace('.', ',')}`;
    
    calcularTotalGeral();
}

function calcularTotalGeral() {
    let total = 0;
    
    document.querySelectorAll('#custosTable tbody tr').forEach(row => {
        const totalCell = row.cells[4].querySelector('input');
        if (totalCell) {
            total += limparValor(totalCell.value);
        }
    });
    
    document.getElementById('totalGeral').textContent = total.toFixed(2).replace('.', ',');
    
    // Atualizar valor total da proposta se estiver vazio
    const valorTotalInput = document.getElementById('valorTotal');
    if (!valorTotalInput.value || limparValor(valorTotalInput.value) === 0) {
        valorTotalInput.value = `R$ ${total.toFixed(2).replace('.', ',')}`;
    }
}

// ===== COLETA DE DADOS =====
function coletarDados() {
    // Função auxiliar para coletar dados de tabela
    const coletarTabela = (tableId) => {
        const dados = [];
        const tbody = document.querySelector(`#${tableId} tbody`);
        
        if (tbody) {
            Array.from(tbody.rows).forEach(row => {
                const rowData = [];
                Array.from(row.cells).forEach((cell, index) => {
                    // Pular a última célula (botão de ação)
                    if (index < row.cells.length - 1) {
                        const input = cell.querySelector('input');
                        if (input) {
                            rowData.push(input.value);
                        }
                    }
                });
                
                // Adicionar apenas se tiver dados válidos
                if (rowData.some(val => val && val.trim() !== '')) {
                    dados.push(rowData);
                }
            });
        }
        
        return dados;
    };

    return {
        processo: processoAtual.numero,
        fornecedor: {
            id: usuarioAtual.usuarioId,
            nome: usuarioAtual.nome
        },
        dados: {
            razaoSocial: document.getElementById('razaoSocial').value,
            cnpj: document.getElementById('cnpj').value,
            endereco: document.getElementById('endereco').value,
            cidade: document.getElementById('cidade').value,
            telefone: document.getElementById('telefone').value,
            email: document.getElementById('email').value,
            respTecnico: document.getElementById('respTecnico').value,
            crea: document.getElementById('crea').value
        },
        tecnica: {
            objetoConcorrencia: document.getElementById('objetoConcorrencia').value,
            metodologia: document.getElementById('metodologia').value,
            prazoExecucao: document.getElementById('prazoExecucao').value,
            garantias: document.getElementById('garantias').value,
            equipe: coletarTabela('equipeTable'),
            experiencia: coletarTabela('experienciaTable')
        },
        comercial: {
            valorTotal: document.getElementById('valorTotal').value,
            validadeProposta: document.getElementById('validadeProposta').value,
            condicoesPagamento: document.getElementById('condicoesPagamento').value,
            custos: coletarTabela('custosTable')
        }
    };
}

// ===== RESUMO DA PROPOSTA =====
function gerarResumo() {
    const dados = coletarDados();
    
    let html = `
        <div class="resumo-section">
            <h3>📋 Dados da Empresa</h3>
            <div class="resumo-item">
                <strong>Razão Social:</strong> ${dados.dados.razaoSocial || 'Não informado'}
            </div>
            <div class="resumo-item">
                <strong>CNPJ:</strong> ${dados.dados.cnpj || 'Não informado'}
            </div>
            <div class="resumo-item">
                <strong>E-mail:</strong> ${dados.dados.email || 'Não informado'}
            </div>
            <div class="resumo-item">
                <strong>Telefone:</strong> ${dados.dados.telefone || 'Não informado'}
            </div>
        </div>
        
        <div class="resumo-section">
            <h3>🔧 Proposta Técnica</h3>
            <div class="resumo-item">
                <strong>Prazo de Execução:</strong> ${dados.tecnica.prazoExecucao || 'Não informado'}
            </div>
            <div class="resumo-item">
                <strong>Garantias:</strong> ${dados.tecnica.garantias || 'Não informado'}
            </div>
            <div class="resumo-item">
                <strong>Equipe Técnica:</strong> ${dados.tecnica.equipe.length} profissional(is)
            </div>
            <div class="resumo-item">
                <strong>Experiências Anteriores:</strong> ${dados.tecnica.experiencia.length} obra(s)
            </div>
        </div>
        
        <div class="resumo-section">
            <h3>💰 Proposta Comercial</h3>
            <div class="resumo-item">
                <strong>Valor Total:</strong> ${dados.comercial.valorTotal || 'Não informado'}
            </div>
            <div class="resumo-item">
                <strong>Validade da Proposta:</strong> ${dados.comercial.validadeProposta || 'Não informado'}
            </div>
            <div class="resumo-item">
                <strong>Condições de Pagamento:</strong> ${dados.comercial.condicoesPagamento || 'Não informado'}
            </div>
            <div class="resumo-item">
                <strong>Itens da Planilha:</strong> ${dados.comercial.custos.length} item(ns)
            </div>
        </div>
    `;
    
    // Verificar se todos os campos obrigatórios estão preenchidos
    const camposObrigatorios = [
        dados.dados.razaoSocial,
        dados.dados.cnpj,
        dados.dados.email,
        dados.tecnica.objetoConcorrencia,
        dados.tecnica.metodologia,
        dados.tecnica.prazoExecucao,
        dados.comercial.valorTotal
    ];
    
    const tudoPreenchido = camposObrigatorios.every(campo => campo && campo.trim() !== '');
    
    if (tudoPreenchido) {
        html += `
            <div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: center;">
                <strong>✅ Proposta completa e pronta para envio!</strong>
            </div>
        `;
    } else {
        html += `
            <div style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: center;">
                <strong>⚠️ Atenção: Alguns campos obrigatórios não foram preenchidos.</strong>
            </div>
        `;
    }
    
    document.getElementById('resumoProposta').innerHTML = html;
}

// ===== ENVIO DA PROPOSTA =====
async function enviarProposta() {
    // Validar todos os campos obrigatórios
    const camposObrigatorios = [
        { id: 'razaoSocial', nome: 'Razão Social' },
        { id: 'cnpj', nome: 'CNPJ' },
        { id: 'email', nome: 'E-mail' },
        { id: 'objetoConcorrencia', nome: 'Descrição do Objeto' },
        { id: 'metodologia', nome: 'Metodologia' },
        { id: 'prazoExecucao', nome: 'Prazo de Execução' },
        { id: 'valorTotal', nome: 'Valor Total' }
    ];
    
    let tudoPreenchido = true;
    let camposFaltando = [];
    
    for (const campo of camposObrigatorios) {
        const elemento = document.getElementById(campo.id);
        if (!elemento || !elemento.value.trim()) {
            tudoPreenchido = false;
            camposFaltando.push(campo.nome);
            if (elemento) {
                elemento.style.borderColor = '#e74c3c';
            }
        }
    }
    
    if (!tudoPreenchido) {
        mostrarMensagem(`Por favor, preencha os seguintes campos obrigatórios:<br>• ${camposFaltando.join('<br>• ')}`, 'error');
        return;
    }
    
    // Confirmar envio
    if (!confirm('Tem certeza que deseja enviar a proposta?\n\nApós o envio, não será possível fazer alterações.')) {
        return;
    }
    
    // Coletar dados
    const dados = coletarDados();
    const protocolo = gerarProtocolo();
    
    // Criar objeto da proposta
    const proposta = {
        protocolo: protocolo,
        processo: processoAtual.numero,
        fornecedor: {
            id: usuarioAtual.usuarioId,
            nome: usuarioAtual.nome,
            empresa: dados.dados.razaoSocial,
            cnpj: dados.dados.cnpj,
            email: dados.dados.email
        },
        dados: dados,
        dataEnvio: new Date().toISOString(),
        status: 'enviada',
        valorTotal: dados.comercial.valorTotal,
        prazoExecucao: dados.tecnica.prazoExecucao
    };
    
    mostrarMensagem('<span class="loading"></span> Enviando proposta...', 'info');
    
    try {
        // Salvar proposta no localStorage
        const propostas = JSON.parse(localStorage.getItem('propostas') || '[]');
        propostas.push(proposta);
        localStorage.setItem('propostas', JSON.stringify(propostas));
        
        // Atualizar contador de propostas do processo
        const processos = JSON.parse(localStorage.getItem('processos') || '[]');
        const processoIndex = processos.findIndex(p => p.numero === processoAtual.numero);
        
        if (processoIndex !== -1) {
            processos[processoIndex].propostas = (processos[processoIndex].propostas || 0) + 1;
            localStorage.setItem('processos', JSON.stringify(processos));
        }
        
        // Criar notificação para o comprador
        if (window.SistemaNotificacoes && processoAtual.criadoPor) {
            SistemaNotificacoes.notificarPropostaRecebida(proposta, processoAtual.criadoPor);
        }
        
        // Registrar atividade no log do Auth
        if (window.Auth && Auth.registrarLog) {
            Auth.registrarLog(usuarioAtual.usuarioId, 'envio_proposta', {
                protocolo: protocolo,
                processo: processoAtual.numero,
                valor: dados.comercial.valorTotal
            });
        }
        
        // Tentar enviar para API (se disponível)
        try {
            const response = await fetch(`${API_URL}/api/enviar-proposta`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(proposta)
            });
            
            if (response.ok) {
                console.log('Proposta enviada para servidor com sucesso');
            }
        } catch (error) {
            console.log('Servidor offline, mas proposta salva localmente:', error);
        }
        
        // Limpar rascunho
        localStorage.removeItem(`proposta_rascunho_${usuarioAtual.usuarioId}_${processoAtual.numero}`);
        
        // Mostrar mensagem de sucesso
        mostrarMensagem(`
            <div style="text-align: center;">
                <h3 style="color: #155724; margin-bottom: 15px;">✅ Proposta Enviada com Sucesso!</h3>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p><strong>Protocolo:</strong> ${protocolo}</p>
                    <p><strong>Data/Hora:</strong> ${new Date().toLocaleString('pt-BR')}</p>
                    <p><strong>Valor:</strong> ${dados.comercial.valorTotal}</p>
                </div>
                <p style="margin-top: 15px;">Um e-mail de confirmação será enviado para ${dados.dados.email}</p>
            </div>
        `, 'success');
        
        // Adicionar botões de ação após 2 segundos
        setTimeout(() => {
            const mensagemDiv = document.getElementById('mensagem');
            mensagemDiv.innerHTML += `
                <div style="margin-top: 20px; text-align: center;">
                    <button onclick="window.location.href='dashboard-fornecedor.html'" 
                            style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: 600; margin-right: 10px;">
                        🏠 Voltar ao Dashboard
                    </button>
                    <button onclick="window.print()" 
                            style="background: #17a2b8; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: 600;">
                        🖨️ Imprimir Comprovante
                    </button>
                </div>
            `;
        }, 2000);
        
    } catch (error) {
        console.error('Erro ao enviar proposta:', error);
        mostrarMensagem('Erro ao enviar proposta. Por favor, tente novamente.', 'error');
    }
}

function gerarProtocolo() {
    const data = new Date();
    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, '0');
    const dia = String(data.getDate()).padStart(2, '0');
    const hora = String(data.getHours()).padStart(2, '0');
    const minuto = String(data.getMinutes()).padStart(2, '0');
    const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    
    return `PROP-${ano}${mes}${dia}-${hora}${minuto}-${random}`;
}

// ===== PREVIEW =====
function gerarPreview() {
    const dados = coletarDados();
    const protocolo = 'PREVIEW-' + Date.now();
    
    const preview = window.open('', '_blank');
    preview.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Preview - Proposta ${protocolo}</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    color: #333;
                }
                h1, h2, h3 { color: #2c3e50; }
                table { 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin: 20px 0; 
                }
                th, td { 
                    border: 1px solid #ddd; 
                    padding: 8px; 
                    text-align: left; 
                }
                th { 
                    background: #3498db; 
                    color: white; 
                }
                .section { 
                    margin: 30px 0; 
                    page-break-inside: avoid; 
                }
                .header { 
                    text-align: center; 
                    margin-bottom: 40px; 
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 20px;
                }
                .footer { 
                    text-align: center; 
                    margin-top: 60px; 
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                }
                .info-box {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 10px 0;
                }
                @media print {
                    .no-print { display: none; }
                    body { margin: 20px; }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>PROPOSTA TÉCNICA E COMERCIAL</h1>
                <div class="info-box">
                    <p><strong>Processo:</strong> ${processoAtual.numero}</p>
                    <p><strong>Objeto:</strong> ${processoAtual.objeto}</p>
                    <p><strong>Data:</strong> ${new Date().toLocaleDateString('pt-BR')}</p>
                </div>
            </div>
            
            <div class="section">
                <h2>1. DADOS DA EMPRESA</h2>
                <div class="info-box">
                    <p><strong>Razão Social:</strong> ${dados.dados.razaoSocial}</p>
                    <p><strong>CNPJ:</strong> ${dados.dados.cnpj}</p>
                    <p><strong>Endereço:</strong> ${dados.dados.endereco}</p>
                    <p><strong>Cidade:</strong> ${dados.dados.cidade}</p>
                    <p><strong>Telefone:</strong> ${dados.dados.telefone}</p>
                    <p><strong>E-mail:</strong> ${dados.dados.email}</p>
                    <p><strong>Responsável Técnico:</strong> ${dados.dados.respTecnico} - ${dados.dados.crea}</p>
                </div>
            </div>
            
            <div class="section">
                <h2>2. PROPOSTA TÉCNICA</h2>
                <h3>2.1. Objeto</h3>
                <p>${dados.tecnica.objetoConcorrencia}</p>
                
                <h3>2.2. Metodologia de Execução</h3>
                <p>${dados.tecnica.metodologia.replace(/\n/g, '<br>')}</p>
                
                <h3>2.3. Prazo de Execução</h3>
                <p>${dados.tecnica.prazoExecucao}</p>
                
                <h3>2.4. Garantias</h3>
                <p>${dados.tecnica.garantias || 'Conforme edital'}</p>
                
                ${dados.tecnica.equipe.length > 0 ? `
                    <h3>2.5. Equipe Técnica</h3>
                    <table>
                        <tr>
                            <th>Nome</th>
                            <th>Função</th>
                            <th>Registro</th>
                        </tr>
                        ${dados.tecnica.equipe.map(membro => `
                            <tr>
                                <td>${membro[0]}</td>
                                <td>${membro[1]}</td>
                                <td>${membro[2]}</td>
                            </tr>
                        `).join('')}
                    </table>
                ` : ''}
                
                ${dados.tecnica.experiencia.length > 0 ? `
                    <h3>2.6. Experiência da Empresa</h3>
                    <table>
                        <tr>
                            <th>Obra/Serviço</th>
                            <th>Cliente</th>
                            <th>Ano</th>
                        </tr>
                        ${dados.tecnica.experiencia.map(exp => `
                            <tr>
                                <td>${exp[0]}</td>
                                <td>${exp[1]}</td>
                                <td>${exp[2]}</td>
                            </tr>
                        `).join('')}
                    </table>
                ` : ''}
            </div>
            
            <div class="section">
                <h2>3. PROPOSTA COMERCIAL</h2>
                
                <div class="info-box" style="background: #e8f5e9;">
                    <h3 style="margin: 0 0 10px 0;">Valor Total da Proposta</h3>
                    <p style="font-size: 24px; font-weight: bold; margin: 0; color: #27ae60;">
                        ${dados.comercial.valorTotal}
                    </p>
                </div>
                
                <p><strong>Validade da Proposta:</strong> ${dados.comercial.validadeProposta}</p>
                
                <h3>3.1. Condições de Pagamento</h3>
                <p>${dados.comercial.condicoesPagamento || 'Conforme edital'}</p>
                
                ${dados.comercial.custos.length > 0 ? `
                    <h3>3.2. Planilha de Custos</h3>
                    <table>
                        <tr>
                            <th>Item</th>
                            <th>Descrição</th>
                            <th>Qtd</th>
                            <th>Valor Unit.</th>
                            <th>Total</th>
                        </tr>
                        ${dados.comercial.custos.map(item => `
                            <tr>
                                <td>${item[0]}</td>
                                <td>${item[1]}</td>
                                <td>${item[2]}</td>
                                <td>${item[3]}</td>
                                <td>${item[4]}</td>
                            </tr>
                        `).join('')}
                    </table>
                ` : ''}
            </div>
            
            <div class="footer">
                <p>_______________________________________</p>
                <p><strong>${dados.dados.razaoSocial}</strong></p>
                <p>CNPJ: ${dados.dados.cnpj}</p>
                <p>${dados.dados.respTecnico} - ${dados.dados.crea}</p>
            </div>
            
            <div class="no-print" style="text-align: center; margin-top: 40px;">
                <button onclick="window.print()" 
                        style="padding: 10px 20px; font-size: 16px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    🖨️ Imprimir
                </button>
                <button onclick="window.close()" 
                        style="padding: 10px 20px; font-size: 16px; margin-left: 10px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer;">
                    ❌ Fechar
                </button>
            </div>
        </body>
        </html>
    `);
}

// ===== AUTO-SAVE E RASCUNHO =====
function iniciarAutoSave() {
    setInterval(() => {
        if (usuarioAtual && processoAtual) {
            const dados = coletarDados();
            const rascunhoKey = `proposta_rascunho_${usuarioAtual.usuarioId}_${processoAtual.numero}`;
            localStorage.setItem(rascunhoKey, JSON.stringify(dados));
            console.log('Rascunho salvo automaticamente');
        }
    }, 30000); // Salvar a cada 30 segundos
}

function verificarRascunho() {
    if (!usuarioAtual || !processoAtual) return;
    
    const rascunhoKey = `proposta_rascunho_${usuarioAtual.usuarioId}_${processoAtual.numero}`;
    const rascunho = localStorage.getItem(rascunhoKey);
    
    if (rascunho) {
        if (confirm('Foi encontrado um rascunho salvo desta proposta.\n\nDeseja recuperá-lo?')) {
            try {
                carregarRascunho(JSON.parse(rascunho));
                mostrarMensagem('✅ Rascunho recuperado com sucesso!', 'success');
            } catch (error) {
                console.error('Erro ao carregar rascunho:', error);
                mostrarMensagem('Erro ao recuperar rascunho.', 'error');
            }
        }
    }
}

function carregarRascunho(dados) {
    // Carregar dados cadastrais
    if (dados.dados) {
        Object.keys(dados.dados).forEach(key => {
            const element = document.getElementById(key);
            if (element) element.value = dados.dados[key];
        });
    }
    
    // Carregar dados técnicos
    if (dados.tecnica) {
        Object.keys(dados.tecnica).forEach(key => {
            const element = document.getElementById(key);
            if (element && typeof dados.tecnica[key] === 'string') {
                element.value = dados.tecnica[key];
            }
        });
        
        // Carregar tabelas
        if (dados.tecnica.equipe && dados.tecnica.equipe.length > 0) {
            carregarTabela('equipeTable', dados.tecnica.equipe);
        }
        
        if (dados.tecnica.experiencia && dados.tecnica.experiencia.length > 0) {
            carregarTabela('experienciaTable', dados.tecnica.experiencia);
        }
    }
    
    // Carregar dados comerciais
    if (dados.comercial) {
        Object.keys(dados.comercial).forEach(key => {
            const element = document.getElementById(key);
            if (element && typeof dados.comercial[key] === 'string') {
                element.value = dados.comercial[key];
            }
        });
        
        // Carregar planilha de custos
        if (dados.comercial.custos && dados.comercial.custos.length > 0) {
            carregarTabela('custosTable', dados.comercial.custos);
            calcularTotalGeral();
        }
    }
}

function carregarTabela(tableId, dados) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;
    
    // Limpar tabela existente
    tbody.innerHTML = '';
    
    // Adicionar dados
    dados.forEach((rowData, index) => {
        const newRow = tbody.insertRow();
        
        if (tableId === 'equipeTable') {
            newRow.innerHTML = `
                <td><input type="text" value="${rowData[0] || ''}" placeholder="Nome completo"></td>
                <td><input type="text" value="${rowData[1] || ''}" placeholder="Função"></td>
                <td><input type="text" value="${rowData[2] || ''}" placeholder="CREA/CAU"></td>
                <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
            `;
        } else if (tableId === 'experienciaTable') {
            newRow.innerHTML = `
                <td><input type="text" value="${rowData[0] || ''}" placeholder="Descrição da obra"></td>
                <td><input type="text" value="${rowData[1] || ''}" placeholder="Nome do cliente"></td>
                <td><input type="number" value="${rowData[2] || ''}" placeholder="2024" min="1900" max="2030"></td>
                <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
            `;
        } else if (tableId === 'custosTable') {
            newRow.innerHTML = `
                <td><input type="text" value="${index + 1}" readonly style="text-align: center;"></td>
                <td><input type="text" value="${rowData[1] || ''}" placeholder="Descrição do item/serviço"></td>
                <td><input type="number" value="${rowData[2] || ''}" placeholder="1" min="0" step="0.01" onchange="calcularTotal(this)"></td>
                <td><input type="text" value="${rowData[3] || ''}" placeholder="R$ 0,00" onblur="formatarValorUnitario(this)" onchange="calcularTotal(this)"></td>
                <td><input type="text" value="${rowData[4] || ''}" placeholder="R$ 0,00" readonly style="background: #f8f9fa;"></td>
                <td><button type="button" class="remove-btn" onclick="removeRowComCalculo(this)">×</button></td>
            `;
        }
    });
}

// ===== UTILITÁRIOS =====
function mostrarMensagem(texto, tipo) {
    const mensagemDiv = document.getElementById('mensagem');
    mensagemDiv.className = tipo === 'error' ? 'error-message' : tipo === 'success' ? 'success-message' : 'info-message';
    mensagemDiv.innerHTML = texto;
    mensagemDiv.style.display = 'block';
    
    // Scroll para mensagem
    mensagemDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    // Auto ocultar após alguns segundos (exceto mensagens de info com loading)
    if (tipo !== 'info' || !texto.includes('loading')) {
        setTimeout(() => {
            // Não ocultar se tiver botões
            if (!mensagemDiv.innerHTML.includes('button')) {
                mensagemDiv.style.display = 'none';
            }
        }, tipo === 'error' ? 5000 : 10000);
    }
}

// ===== EVENTOS GLOBAIS =====
// Prevenir perda de dados ao sair da página
window.addEventListener('beforeunload', function (e) {
    if (usuarioAtual && processoAtual) {
        const dados = coletarDados();
        // Verificar se há dados preenchidos
        const temDados = Object.values(dados.dados).some(val => val && val.trim() !== '') ||
                        Object.values(dados.tecnica).some(val => val && typeof val === 'string' && val.trim() !== '') ||
                        Object.values(dados.comercial).some(val => val && typeof val === 'string' && val.trim() !== '');
        
        if (temDados) {
            const rascunhoKey = `proposta_rascunho_${usuarioAtual.usuarioId}_${processoAtual.numero}`;
            localStorage.setItem(rascunhoKey, JSON.stringify(dados));
            
            // Mostrar aviso de saída
            e.preventDefault();
            e.returnValue = 'Você tem alterações não salvas. Deseja realmente sair?';
            return e.returnValue;
        }
    }
});

// ===== MÁSCARAS E VALIDAÇÕES =====
// Adicionar máscara de CNPJ
document.addEventListener('DOMContentLoaded', function() {
    const cnpjInput = document.getElementById('cnpj');
    if (cnpjInput) {
        cnpjInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 14) value = value.substr(0, 14);
            
            // Aplicar máscara
            if (value.length > 2) {
                value = value.replace(/^(\d{2})(\d)/, '$1.$2');
            }
            if (value.length > 6) {
                value = value.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
            }
            if (value.length > 10) {
                value = value.replace(/^(\d{2})\.(\d{3})\.(\d{3})(\d)/, '$1.$2.$3/$4');
            }
            if (value.length > 15) {
                value = value.replace(/^(\d{2})\.(\d{3})\.(\d{3})\/(\d{4})(\d)/, '$1.$2.$3/$4-$5');
            }
            
            e.target.value = value;
        });
    }
    
    // Adicionar máscara de telefone
    const telefoneInput = document.getElementById('telefone');
    if (telefoneInput) {
        telefoneInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 11) value = value.substr(0, 11);
            
            // Aplicar máscara
            if (value.length > 0) {
                value = value.replace(/^(\d{2})(\d)/, '($1) $2');
            }
            if (value.length > 7) {
                value = value.replace(/^(\(\d{2}\) \d{4})(\d)/, '$1-$2');
            }
            if (value.length > 12) {
                value = value.replace(/^(\(\d{2}\) \d)(\d{4})(\d{4})/, '($1) $2-$3');
            }
            
            e.target.value = value;
        });
    }
});

console.log('Portal de Propostas - Scripts carregados com sucesso!');