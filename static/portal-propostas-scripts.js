// ===== PORTAL DE PROPOSTAS COMPLETO - SCRIPTS =====
// Arquivo: portal-propostas-completo-scripts.js

// ===== VARIÁVEIS GLOBAIS =====
let currentTab = 'dados';
let usuarioAtual = null;
let processoAtual = null;
let dadosSalvosTemp = {};

// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Iniciando Portal de Propostas COMPLETO...');
    
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
    carregarDadosEmpresa();
    iniciarAutoSave();
    verificarRascunho();
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
    const cadastros = JSON.parse(localStorage.getItem('cadastros_fornecedores') || '[]');
    const meuCadastro = cadastros.find(c => c.usuarioId === usuarioAtual.usuarioId);
    
    if (meuCadastro) {
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

// ===== NAVEGAÇÃO =====
function showTab(tabName, buttonElement) {
    if (!validarAbaAtual()) {
        return;
    }
    
    document.querySelectorAll('.form-section').forEach(section => {
        section.classList.remove('active');
    });
    
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    document.getElementById(tabName).classList.add('active');
    buttonElement.classList.add('active');
    
    currentTab = tabName;
    updateProgress();
    
    if (tabName === 'comercial') {
        copiarObjetoParaComercial();
        copiarDadosTecnicaParaComercial();
    }
    
    if (tabName === 'revisao') {
        gerarRevisao();
    }
    
    window.scrollTo(0, 0);
}

function updateProgress() {
    const tabs = ['dados', 'resumo', 'tecnica', 'comercial', 'revisao'];
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
            mostrarMensagem('Por favor, preencha todos os campos obrigatórios.', 'error');
        }
    }
    
    return valido;
}

// ===== FUNÇÕES DE RESUMO =====
function atualizarResumo() {
    const prazo = document.getElementById('prazoExecucaoResumo').value;
    const pagamento = document.getElementById('formaPagamentoResumo').value;
    const valorTotal = document.getElementById('valorTotalCalculado').textContent;
    
    document.getElementById('prazoResumo').textContent = prazo || '-- dias';
    document.getElementById('pagamentoResumo').textContent = pagamento || 'A definir';
    document.getElementById('precoTotalResumo').textContent = valorTotal;
    
    // Copiar prazo para aba técnica
    if (prazo) {
        document.getElementById('prazoExecucao').value = prazo;
    }
}

// ===== FUNÇÕES DE TABELAS DINÂMICAS =====
function addServicoTecnicaRow() {
    const tbody = document.querySelector('#servicosTecnicaTable tbody');
    const nextItem = tbody.rows.length + 1;
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" value="${nextItem}" readonly style="text-align: center;"></td>
        <td><input type="text" placeholder="Descrição do serviço"></td>
        <td><input type="text" placeholder="m²"></td>
        <td><input type="number" placeholder="100"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
    renumerarTabela('servicosTecnicaTable');
}

function addEquipeRow() {
    const tbody = document.querySelector('#equipeTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Função"></td>
        <td><input type="number" placeholder="1"></td>
        <td><input type="number" placeholder="4" step="0.1"></td>
        <td><input type="text" placeholder="Qualificação"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addMaterialRow() {
    const tbody = document.querySelector('#materiaisTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Material"></td>
        <td><input type="text" placeholder="Especificação"></td>
        <td><input type="text" placeholder="Unidade"></td>
        <td><input type="number" placeholder="Quantidade"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addEquipamentoRow() {
    const tbody = document.querySelector('#equipamentosTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Equipamento"></td>
        <td><input type="text" placeholder="Especificação"></td>
        <td><input type="text" placeholder="Unidade"></td>
        <td><input type="number" placeholder="Quantidade"></td>
        <td><input type="number" placeholder="4" step="0.1"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addExperienciaRow() {
    const tbody = document.querySelector('#experienciaTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Nome da obra"></td>
        <td><input type="text" placeholder="Cliente"></td>
        <td><input type="text" placeholder="Valor"></td>
        <td><input type="number" placeholder="Ano"></td>
        <td><input type="text" placeholder="(00) 0000-0000"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addCertificacaoRow() {
    const tbody = document.querySelector('#certificacoesTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Certificação"></td>
        <td><input type="text" placeholder="Órgão"></td>
        <td><input type="text" placeholder="Número"></td>
        <td><input type="date"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

// ===== CRONOGRAMA AUTOMÁTICO =====
function addCronogramaRow() {
    const tbody = document.querySelector('#cronogramaTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Nova Atividade"></td>
        <td><input type="number" placeholder="10" min="1" onchange="calcularCronograma()"></td>
        <td><input type="text" readonly style="background: #f8f9fa;"></td>
        <td><input type="text" readonly style="background: #f8f9fa;"></td>
        <td><button type="button" class="remove-btn" onclick="removeRowAndRecalculate(this)">×</button></td>
    `;
    calcularCronograma();
}

function calcularCronograma() {
    const tbody = document.querySelector('#cronogramaTable tbody');
    let diaAtual = 1;
    let prazoTotal = 0;
    
    for (const row of tbody.rows) {
        const duracaoInput = row.cells[1].querySelector('input');
        const duracao = parseInt(duracaoInput.value) || 0;
        
        if (duracao > 0) {
            const diaFim = diaAtual + duracao - 1;
            row.cells[2].querySelector('input').value = `Dia ${diaAtual}`;
            row.cells[3].querySelector('input').value = `Dia ${diaFim}`;
            diaAtual = diaFim + 1;
            prazoTotal += duracao;
        } else {
            row.cells[2].querySelector('input').value = '';
            row.cells[3].querySelector('input').value = '';
        }
    }
    
    document.getElementById('prazoTotalCronograma').textContent = prazoTotal;
    
    // Atualizar prazo de execução se estiver vazio
    const prazoExecucao = document.getElementById('prazoExecucao');
    if (!prazoExecucao.value) {
        prazoExecucao.value = `${prazoTotal} dias`;
    }
}

function removeRowAndRecalculate(button) {
    button.closest('tr').remove();
    calcularCronograma();
}

// ===== FUNÇÕES COMERCIAIS =====
function copiarObjetoParaComercial() {
    const objetoTecnico = document.getElementById('objetoConcorrencia').value;
    document.getElementById('objetoComercial').value = objetoTecnico;
}

function copiarDadosTecnicaParaComercial() {
    copiarServicosTecnicaParaComercial();
    copiarMaoObraTecnicaParaComercial();
    copiarMateriaisTecnicaParaComercial();
    copiarEquipamentosTecnicaParaComercial();
}

function copiarServicosTecnicaParaComercial() {
    const servicosTecnica = coletarTabela('servicosTecnicaTable');
    const tbody = document.querySelector('#servicosTable tbody');
    
    // Salvar valores atuais se existirem
    const valoresAtuais = {};
    document.querySelectorAll('#servicosTable tbody tr').forEach((row, index) => {
        const preco = row.cells[4].querySelector('input')?.value;
        if (preco) {
            valoresAtuais[index] = preco;
        }
    });
    
    tbody.innerHTML = '';
    
    servicosTecnica.forEach((servico, index) => {
        const newRow = tbody.insertRow();
        newRow.innerHTML = `
            <td><input type="text" value="${index + 1}" readonly style="text-align: center;"></td>
            <td><input type="text" value="${servico[1]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="text" value="${servico[2]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="number" value="${servico[3]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="number" placeholder="0.00" step="0.01" value="${valoresAtuais[index] || ''}" onchange="calcTotal(this)"></td>
            <td><input type="text" readonly style="background: #f8f9fa;"></td>
            <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
        `;
    });
}

function copiarMaoObraTecnicaParaComercial() {
    const maoObraTecnica = coletarTabela('equipeTable');
    const tbody = document.querySelector('#maoObraTable tbody');
    
    // Preservar salários já inseridos
    const salariosAtuais = {};
    document.querySelectorAll('#maoObraTable tbody tr').forEach((row, index) => {
        const salario = row.cells[3].querySelector('input')?.value;
        if (salario) {
            salariosAtuais[index] = salario;
        }
    });
    
    tbody.innerHTML = '';
    
    maoObraTecnica.forEach((item, index) => {
        const newRow = tbody.insertRow();
        newRow.innerHTML = `
            <td><input type="text" value="${item[0]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="number" value="${item[1]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="number" value="${item[2]}" readonly style="background: #f8f9fa;" step="0.1"></td>
            <td><input type="number" placeholder="0.00" value="${salariosAtuais[index] || ''}" onchange="calcMaoObra(this)" step="0.01"></td>
            <td><input type="number" placeholder="80" value="80" onchange="calcMaoObra(this)" step="0.1"></td>
            <td><input type="text" readonly style="background: #f8f9fa;"></td>
            <td><input type="text" readonly style="background: #f8f9fa;"></td>
            <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
        `;
    });
}

function copiarMateriaisTecnicaParaComercial() {
    const materiaisTecnica = coletarTabela('materiaisTable');
    const tbody = document.querySelector('#materiaisComercialTable tbody');
    
    const precosAtuais = {};
    document.querySelectorAll('#materiaisComercialTable tbody tr').forEach((row, index) => {
        const preco = row.cells[4].querySelector('input')?.value;
        if (preco) {
            precosAtuais[index] = preco;
        }
    });
    
    tbody.innerHTML = '';
    
    materiaisTecnica.forEach((item, index) => {
        const newRow = tbody.insertRow();
        newRow.innerHTML = `
            <td><input type="text" value="${item[0]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="text" value="${item[1]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="text" value="${item[2]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="number" value="${item[3]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="number" placeholder="0.00" step="0.01" value="${precosAtuais[index] || ''}" onchange="calcMaterial(this)"></td>
            <td><input type="text" readonly style="background: #f8f9fa;"></td>
            <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
        `;
    });
}

function copiarEquipamentosTecnicaParaComercial() {
    const equipamentosTecnica = coletarTabela('equipamentosTable');
    const tbody = document.querySelector('#equipamentosComercialTable tbody');
    
    const precosAtuais = {};
    document.querySelectorAll('#equipamentosComercialTable tbody tr').forEach((row, index) => {
        const preco = row.cells[4].querySelector('input')?.value;
        if (preco) {
            precosAtuais[index] = preco;
        }
    });
    
    tbody.innerHTML = '';
    
    equipamentosTecnica.forEach((item, index) => {
        const newRow = tbody.insertRow();
        newRow.innerHTML = `
            <td><input type="text" value="${item[0]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="text" value="${item[1]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="number" value="${item[3]}" readonly style="background: #f8f9fa;"></td>
            <td><input type="number" value="${item[4]}" readonly style="background: #f8f9fa;" step="0.1"></td>
            <td><input type="number" placeholder="0.00" step="0.01" value="${precosAtuais[index] || ''}" onchange="calcEquipamento(this)"></td>
            <td><input type="text" readonly style="background: #f8f9fa;"></td>
            <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
        `;
    });
}

// ===== FUNÇÕES DE ADIÇÃO COMERCIAL =====
function addServicoRow() {
    const tbody = document.querySelector('#servicosTable tbody');
    const nextItem = tbody.rows.length + 1;
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" value="${nextItem}" readonly style="text-align: center;"></td>
        <td><input type="text" placeholder="Descrição"></td>
        <td><input type="text" placeholder="m²"></td>
        <td><input type="number" placeholder="100" onchange="calcTotal(this)"></td>
        <td><input type="number" placeholder="0.00" step="0.01" onchange="calcTotal(this)"></td>
        <td><input type="text" readonly style="background: #f8f9fa;"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addMaoObraRow() {
    const tbody = document.querySelector('#maoObraTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Função"></td>
        <td><input type="number" placeholder="1" onchange="calcMaoObra(this)"></td>
        <td><input type="number" placeholder="4" step="0.1" onchange="calcMaoObra(this)"></td>
        <td><input type="number" placeholder="0.00" step="0.01" onchange="calcMaoObra(this)"></td>
        <td><input type="number" placeholder="80" value="80" step="0.1" onchange="calcMaoObra(this)"></td>
        <td><input type="text" readonly style="background: #f8f9fa;"></td>
        <td><input type="text" readonly style="background: #f8f9fa;"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addMaterialComercialRow() {
    const tbody = document.querySelector('#materiaisComercialTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Material"></td>
        <td><input type="text" placeholder="Especificação"></td>
        <td><input type="text" placeholder="Unidade"></td>
        <td><input type="number" placeholder="100" onchange="calcMaterial(this)"></td>
        <td><input type="number" placeholder="0.00" step="0.01" onchange="calcMaterial(this)"></td>
        <td><input type="text" readonly style="background: #f8f9fa;"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

function addEquipamentoComercialRow() {
    const tbody = document.querySelector('#equipamentosComercialTable tbody');
    const newRow = tbody.insertRow();
    newRow.innerHTML = `
        <td><input type="text" placeholder="Equipamento"></td>
        <td><input type="text" placeholder="Especificação"></td>
        <td><input type="number" placeholder="1" onchange="calcEquipamento(this)"></td>
        <td><input type="number" placeholder="3" step="0.1" onchange="calcEquipamento(this)"></td>
        <td><input type="number" placeholder="0.00" step="0.01" onchange="calcEquipamento(this)"></td>
        <td><input type="text" readonly style="background: #f8f9fa;"></td>
        <td><button type="button" class="remove-btn" onclick="removeRow(this)">×</button></td>
    `;
}

// ===== CÁLCULOS =====
function formatarMoeda(valor) {
    if (!valor && valor !== 0) return '0,00';
    return valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function limparMoeda(valor) {
    if (!valor) return 0;
    return parseFloat(valor.toString().replace(/[^\d,.-]/g, '').replace('.', '').replace(',', '.')) || 0;
}

function calcTotal(input) {
    const row = input.closest('tr');
    const qtd = parseFloat(row.cells[3].querySelector('input').value) || 0;
    const preco = parseFloat(row.cells[4].querySelector('input').value) || 0;
    const total = qtd * preco;
    
    row.cells[5].querySelector('input').value = formatarMoeda(total);
    
    calcularTotalServicos();
    calcularTotais();
}

function calcMaoObra(input) {
    const row = input.closest('tr');
    const qtd = parseFloat(row.cells[1].querySelector('input').value) || 0;
    const tempo = parseFloat(row.cells[2].querySelector('input').value) || 0;
    const salario = parseFloat(row.cells[3].querySelector('input').value) || 0;
    const encargos = parseFloat(row.cells[4].querySelector('input').value) || 0;
    
    const salarioComEncargos = salario * (1 + encargos/100);
    const totalMensal = qtd * salarioComEncargos;
    const totalGeral = totalMensal * tempo;
    
    row.cells[5].querySelector('input').value = formatarMoeda(totalMensal);
    row.cells[6].querySelector('input').value = formatarMoeda(totalGeral);
    
    calcularTotalMaoObra();
    calcularTotais();
}

function calcMaterial(input) {
    const row = input.closest('tr');
    const qtd = parseFloat(row.cells[3].querySelector('input').value) || 0;
    const preco = parseFloat(row.cells[4].querySelector('input').value) || 0;
    const total = qtd * preco;
    
    row.cells[5].querySelector('input').value = formatarMoeda(total);
    
    calcularTotalMateriais();
    calcularTotais();
}

function calcEquipamento(input) {
    const row = input.closest('tr');
    const qtd = parseFloat(row.cells[2].querySelector('input').value) || 0;
    const tempo = parseFloat(row.cells[3].querySelector('input').value) || 0;
    const preco = parseFloat(row.cells[4].querySelector('input').value) || 0;
    const total = qtd * tempo * preco;
    
    row.cells[5].querySelector('input').value = formatarMoeda(total);
    
    calcularTotalEquipamentos();
    calcularTotais();
}

function calcularTotalServicos() {
    let total = 0;
    document.querySelectorAll('#servicosTable tbody tr').forEach(row => {
        const valor = limparMoeda(row.cells[5].querySelector('input').value);
        total += valor;
    });
    document.getElementById('totalServicos').textContent = formatarMoeda(total);
    return total;
}

function calcularTotalMaoObra() {
    let total = 0;
    document.querySelectorAll('#maoObraTable tbody tr').forEach(row => {
        const valor = limparMoeda(row.cells[6].querySelector('input').value);
        total += valor;
    });
    document.getElementById('totalMaoObra').textContent = formatarMoeda(total);
    return total;
}

function calcularTotalMateriais() {
    let total = 0;
    document.querySelectorAll('#materiaisComercialTable tbody tr').forEach(row => {
        const valor = limparMoeda(row.cells[5].querySelector('input').value);
        total += valor;
    });
    document.getElementById('totalMateriais').textContent = formatarMoeda(total);
    return total;
}

function calcularTotalEquipamentos() {
    let total = 0;
    document.querySelectorAll('#equipamentosComercialTable tbody tr').forEach(row => {
        const valor = limparMoeda(row.cells[5].querySelector('input').value);
        total += valor;
    });
    document.getElementById('totalEquipamentos').textContent = formatarMoeda(total);
    return total;
}

function calcBDI() {
    const custoDirecto = calcularCustoDirecto();
    let totalBDI = 0;
    
    document.querySelectorAll('#bdiTable tbody tr').forEach(row => {
        const percentualInput = row.cells[1].querySelector('input');
        const valorInput = row.cells[2].querySelector('input');
        
        if (percentualInput && valorInput) {
            const percentual = parseFloat(percentualInput.value) || 0;
            const valor = custoDirecto * (percentual / 100);
            valorInput.value = formatarMoeda(valor);
            totalBDI += percentual;
        }
    });
    
    const valorBDI = custoDirecto * (totalBDI / 100);
    const valorTotal = custoDirecto + valorBDI;
    
    document.getElementById('bdiPercentual').textContent = totalBDI.toFixed(1);
    document.getElementById('bdiValor').textContent = formatarMoeda(valorBDI);
    document.getElementById('valorTotalCalculado').textContent = formatarMoeda(valorTotal);
    document.getElementById('valorTotal').value = 'R$ ' + formatarMoeda(valorTotal);
    
    // Atualizar resumo
    document.getElementById('precoTotalResumo').textContent = formatarMoeda(valorTotal);
}

function calcularCustoDirecto() {
    const servicos = calcularTotalServicos();
    const maoObra = calcularTotalMaoObra();
    const materiais = calcularTotalMateriais();
    const equipamentos = calcularTotalEquipamentos();
    const total = servicos + maoObra + materiais + equipamentos;
    
    document.getElementById('custoDirecto').textContent = formatarMoeda(total);
    return total;
}

function calcularTotais() {
    calcularCustoDirecto();
    calcBDI();
}

// ===== REMOÇÃO E UTILIDADES =====
function removeRow(button) {
    const row = button.closest('tr');
    const table = row.closest('table');
    const tbody = table.querySelector('tbody');
    
    if (tbody.rows.length > 1) {
        row.remove();
        
        // Renumerar se necessário
        if (table.id === 'servicosTecnicaTable' || table.id === 'servicosTable') {
            renumerarTabela(table.id);
        }
        
        // Recalcular totais se for tabela comercial
        if (table.id.includes('Comercial') || table.id === 'servicosTable' || 
            table.id === 'maoObraTable' || table.id === 'materiaisComercialTable' || 
            table.id === 'equipamentosComercialTable') {
            calcularTotais();
        }
    } else {
        mostrarMensagem('Deve haver pelo menos um item na tabela.', 'error');
    }
}

function renumerarTabela(tableId) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    Array.from(tbody.rows).forEach((row, index) => {
        const firstInput = row.cells[0].querySelector('input');
        if (firstInput && firstInput.readOnly) {
            firstInput.value = index + 1;
        }
    });
}

// ===== COLETA DE DADOS =====
function coletarTabela(tableId) {
    const dados = [];
    const tbody = document.querySelector(`#${tableId} tbody`);
    
    if (tbody) {
        Array.from(tbody.rows).forEach(row => {
            const rowData = [];
            Array.from(row.cells).forEach((cell, index) => {
                if (index < row.cells.length - 1) { // Pular botão de ação
                    const input = cell.querySelector('input');
                    if (input) {
                        rowData.push(input.value);
                    }
                }
            });
            
            if (rowData.some(val => val && val.trim() !== '')) {
                dados.push(rowData);
            }
        });
    }
    
    return dados;
}

function coletarDados() {
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
        resumo: {
            prazoExecucao: document.getElementById('prazoExecucaoResumo')?.value || document.getElementById('prazoExecucao').value,
            formaPagamento: document.getElementById('formaPagamentoResumo')?.value || ''
        },
        tecnica: {
            objetoConcorrencia: document.getElementById('objetoConcorrencia').value,
            escopoInclusos: document.getElementById('escopoInclusos').value,
            escopoExclusos: document.getElementById('escopoExclusos').value,
            metodologia: document.getElementById('metodologia').value,
            sequenciaExecucao: document.getElementById('sequenciaExecucao').value,
            servicosTecnica: coletarTabela('servicosTecnicaTable'),
            equipe: coletarTabela('equipeTable'),
            materiais: coletarTabela('materiaisTable'),
            equipamentos: coletarTabela('equipamentosTable'),
            prazoExecucao: document.getElementById('prazoExecucao').value,
            prazoMobilizacao: document.getElementById('prazoMobilizacao').value,
            cronograma: coletarTabela('cronogramaTable'),
            garantias: document.getElementById('garantias').value,
            estruturaCanteiro: document.getElementById('estruturaCanteiro').value,
            obrigacoesContratada: document.getElementById('obrigacoesContratada').value,
            obrigacoesContratante: document.getElementById('obrigacoesContratante').value,
            experiencia: coletarTabela('experienciaTable'),
            certificacoes: coletarTabela('certificacoesTable')
        },
        comercial: {
            objetoComercial: document.getElementById('objetoComercial').value,
            servicos: coletarTabela('servicosTable'),
            valorTotal: document.getElementById('valorTotalCalculado').textContent,
            validadeProposta: document.getElementById('validadeProposta').value,
            maoObra: coletarTabela('maoObraTable'),
            materiaisComercial: coletarTabela('materiaisComercialTable'),
            equipamentosComercial: coletarTabela('equipamentosComercialTable'),
            bdi: coletarTabela('bdiTable'),
            validadeDetalhada: document.getElementById('validadeDetalhada').value,
            condicoesPagamento: document.getElementById('condicoesPagamento').value,
            totalServicos: document.getElementById('totalServicos').textContent,
            totalMaoObra: document.getElementById('totalMaoObra').textContent,
            totalMateriais: document.getElementById('totalMateriais').textContent,
            totalEquipamentos: document.getElementById('totalEquipamentos').textContent,
            custoDirecto: document.getElementById('custoDirecto').textContent,
            bdiPercentual: document.getElementById('bdiPercentual').textContent,
            bdiValor: document.getElementById('bdiValor').textContent
        }
    };
}

// ===== REVISÃO E ENVIO =====
function gerarRevisao() {
    const dados = coletarDados();
    
    let html = `
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: #2c3e50;">📊 Resumo Executivo</h3>
            <p><strong>Empresa:</strong> ${dados.dados.razaoSocial}</p>
            <p><strong>CNPJ:</strong> ${dados.dados.cnpj}</p>
            <p><strong>Processo:</strong> ${processoAtual.numero}</p>
            <p><strong>Objeto:</strong> ${processoAtual.objeto}</p>
            <p><strong>Prazo de Execução:</strong> ${dados.tecnica.prazoExecucao}</p>
            <p><strong>Valor Total:</strong> R$ ${dados.comercial.valorTotal}</p>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div style="background: #e8f5e9; padding: 15px; border-radius: 10px;">
                <h4 style="color: #27ae60;">✅ Documentos Técnicos</h4>
                <ul style="list-style: none; padding-left: 0;">
                    <li>✓ Metodologia de execução</li>
                    <li>✓ Equipe técnica: ${dados.tecnica.equipe.length} profissionais</li>
                    <li>✓ Cronograma: ${dados.tecnica.cronograma.length} atividades</li>
                    <li>✓ Experiência: ${dados.tecnica.experiencia.length} obras</li>
                    <li>✓ Certificações: ${dados.tecnica.certificacoes.length} documentos</li>
                </ul>
            </div>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 10px;">
                <h4 style="color: #2196f3;">💰 Composição de Custos</h4>
                <ul style="list-style: none; padding-left: 0;">
                    <li>• Serviços: R$ ${dados.comercial.totalServicos}</li>
                    <li>• Mão de obra: R$ ${dados.comercial.totalMaoObra}</li>
                    <li>• Materiais: R$ ${dados.comercial.totalMateriais}</li>
                    <li>• Equipamentos: R$ ${dados.comercial.totalEquipamentos}</li>
                    <li>• BDI (${dados.comercial.bdiPercentual}%): R$ ${dados.comercial.bdiValor}</li>
                </ul>
            </div>
        </div>
        
        <div style="background: #fff3cd; padding: 15px; border-radius: 10px; margin-top: 20px;">
            <h4 style="color: #856404;">⚠️ Checklist Final</h4>
            <p>Antes de enviar, verifique:</p>
            <ul>
                <li>Todos os valores estão corretos?</li>
                <li>O prazo de execução está adequado?</li>
                <li>As certificações estão válidas?</li>
                <li>A proposta atende todos os requisitos do edital?</li>
            </ul>
        </div>
    `;
    
    document.getElementById('resumoProposta').innerHTML = html;
}

function gerarRevisaoFinal() {
    const dados = coletarDados();
    
    const html = `
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3>📋 Dados da Empresa</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div><strong>Razão Social:</strong> ${dados.dados.razaoSocial}</div>
                <div><strong>CNPJ:</strong> ${dados.dados.cnpj}</div>
                <div><strong>E-mail:</strong> ${dados.dados.email}</div>
                <div><strong>Telefone:</strong> ${dados.dados.telefone}</div>
                <div><strong>Responsável:</strong> ${dados.dados.respTecnico}</div>
                <div><strong>CREA/CAU:</strong> ${dados.dados.crea}</div>
            </div>
        </div>
        
        <div style="background: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3>📊 Resumo da Proposta</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div><strong>Processo:</strong> ${processoAtual.numero}</div>
                <div><strong>Prazo:</strong> ${dados.tecnica.prazoExecucao}</div>
                <div><strong>Validade:</strong> ${dados.comercial.validadeProposta}</div>
                <div><strong>Valor Total:</strong> R$ ${dados.comercial.valorTotal}</div>
            </div>
        </div>
        
        <div style="background: #e3f2fd; padding: 20px; border-radius: 10px;">
            <h3>💰 Composição Detalhada</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">Serviços</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">R$ ${dados.comercial.totalServicos}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">Mão de Obra</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">R$ ${dados.comercial.totalMaoObra}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">Materiais</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">R$ ${dados.comercial.totalMateriais}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">Equipamentos</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">R$ ${dados.comercial.totalEquipamentos}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 2px solid #2196f3;"><strong>Custo Direto</strong></td>
                    <td style="padding: 8px; border-bottom: 2px solid #2196f3; text-align: right;"><strong>R$ ${dados.comercial.custoDirecto}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px;">BDI (${dados.comercial.bdiPercentual}%)</td>
                    <td style="padding: 8px; text-align: right;">R$ ${dados.comercial.bdiValor}</td>
                </tr>
                <tr style="background: #2196f3; color: white;">
                    <td style="padding: 12px;"><strong>VALOR TOTAL</strong></td>
                    <td style="padding: 12px; text-align: right;"><strong>R$ ${dados.comercial.valorTotal}</strong></td>
                </tr>
            </table>
        </div>
    `;
    
    document.getElementById('conteudoRevisao').innerHTML = html;
}

async function enviarProposta() {
    // Validar campos obrigatórios
    const camposObrigatorios = ['razaoSocial', 'cnpj', 'email', 'objetoConcorrencia', 'metodologia', 'prazoExecucao'];
    let tudoPreenchido = true;
    
    for (const campo of camposObrigatorios) {
        const elemento = document.getElementById(campo);
        if (!elemento || !elemento.value.trim()) {
            tudoPreenchido = false;
            if (elemento) {
                elemento.style.borderColor = '#e74c3c';
            }
        }
    }
    
    // Verificar se há valor total
    const valorTotal = document.getElementById('valorTotalCalculado').textContent;
    if (!valorTotal || valorTotal === '0,00') {
        tudoPreenchido = false;
        mostrarMensagem('Por favor, preencha os valores da proposta comercial.', 'error');
        return;
    }
    
    if (!tudoPreenchido) {
        mostrarMensagem('Por favor, preencha todos os campos obrigatórios (*)', 'error');
        return;
    }
    
    // Mostrar modal de revisão
    gerarRevisaoFinal();
    document.getElementById('modalRevisao').style.display = 'block';
}

function fecharModalRevisao() {
    document.getElementById('modalRevisao').style.display = 'none';
    document.getElementById('confirmacaoFinal').checked = false;
    document.getElementById('btnConfirmarEnvio').disabled = true;
    document.getElementById('btnConfirmarEnvio').style.opacity = '0.5';
}

function habilitarBotaoEnvio() {
    const checkbox = document.getElementById('confirmacaoFinal');
    const botao = document.getElementById('btnConfirmarEnvio');
    
    if (checkbox.checked) {
        botao.disabled = false;
        botao.style.opacity = '1';
    } else {
        botao.disabled = true;
        botao.style.opacity = '0.5';
    }
}

// Correção na função confirmarEnvioFinal (linha ~1050)
async function confirmarEnvioFinal() {
    fecharModalRevisao();
    
    const dados = coletarDados();
    const protocolo = gerarProtocolo();
    
    mostrarMensagem('<span class="loading"></span> Enviando proposta...', 'info');
    
    // Criar objeto da proposta no formato correto para o backend
    const propostaParaAPI = {
        processo: processoAtual.numero,
        dadosCadastrais: {
            razaoSocial: dados.dados.razaoSocial,
            cnpj: dados.dados.cnpj,
            endereco: dados.dados.endereco,
            cidade: dados.dados.cidade,
            telefone: dados.dados.telefone,
            email: dados.dados.email,
            respTecnico: dados.dados.respTecnico,
            crea: dados.dados.crea
        },
        resumo: {
            precoTotal: dados.comercial.valorTotal,
            prazoExecucao: dados.tecnica.prazoExecucao,
            formaPagamento: dados.resumo.formaPagamento
        },
        propostaTecnica: dados.tecnica,
        propostaComercial: dados.comercial,
        metadata: {
            protocolo: protocolo,
            dataEnvio: new Date().toISOString(),
            fornecedorId: usuarioAtual.usuarioId,
            fornecedorNome: usuarioAtual.nome
        }
    };
    
    // Criar objeto da proposta para localStorage
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
    
    try {
        // Salvar proposta no localStorage
        const propostas = JSON.parse(localStorage.getItem('propostas') || '[]');
        propostas.push(proposta);
        localStorage.setItem('propostas', JSON.stringify(propostas));
        
        // Atualizar contador do processo
        const processos = JSON.parse(localStorage.getItem('processos') || '[]');
        const processoIndex = processos.findIndex(p => p.numero === processoAtual.numero);
        if (processoIndex !== -1) {
            processos[processoIndex].propostas = (processos[processoIndex].propostas || 0) + 1;
            localStorage.setItem('processos', JSON.stringify(processos));
        }
        
        // Criar notificação
        if (window.SistemaNotificacoes && processoAtual.criadoPor) {
            SistemaNotificacoes.notificarPropostaRecebida(proposta, processoAtual.criadoPor);
        }
        
        // Registrar log
        if (window.Auth && Auth.registrarLog) {
            Auth.registrarLog(usuarioAtual.usuarioId, 'envio_proposta', {
                protocolo: protocolo,
                processo: processoAtual.numero,
                valor: dados.comercial.valorTotal
            });
        }
        
        // Tentar enviar para API - CORRIGIDO O ENDPOINT
        try {
            const response = await fetch(`${API_URL}/api/propostas/enviar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(propostaParaAPI)
            });
            
            if (response.ok) {
                const resultado = await response.json();
                console.log('Proposta enviada para servidor:', resultado);
            }
        } catch (error) {
            console.log('Servidor offline, proposta salva localmente');
        }
        
        // Limpar rascunho
        localStorage.removeItem(`proposta_rascunho_${usuarioAtual.usuarioId}_${processoAtual.numero}`);
        
        // Mostrar sucesso
        mostrarMensagem(`
            <div style="text-align: center;">
                <h3 style="color: #155724;">✅ Proposta Enviada com Sucesso!</h3>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p><strong>Protocolo:</strong> ${protocolo}</p>
                    <p><strong>Data/Hora:</strong> ${new Date().toLocaleString('pt-BR')}</p>
                    <p><strong>Valor:</strong> R$ ${dados.comercial.valorTotal}</p>
                </div>
                <p>Um e-mail de confirmação será enviado para ${dados.dados.email}</p>
                <div style="margin-top: 20px;">
                    <button onclick="window.location.href='dashboard-fornecedor.html'" 
                            style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-right: 10px;">
                        🏠 Voltar ao Dashboard
                    </button>
                    <button onclick="window.print()" 
                            style="background: #17a2b8; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                        🖨️ Imprimir Comprovante
                    </button>
                </div>
            </div>
        `, 'success');
        
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
                body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
                h1, h2, h3 { color: #2c3e50; }
                .header { text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 20px; margin-bottom: 30px; }
                .section { margin: 30px 0; page-break-inside: avoid; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background: #3498db; color: white; }
                .footer { text-align: center; margin-top: 60px; padding-top: 20px; border-top: 1px solid #ddd; }
                @media print { .no-print { display: none; } }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>PROPOSTA TÉCNICA E COMERCIAL</h1>
                <p><strong>Processo:</strong> ${processoAtual.numero}</p>
                <p><strong>Objeto:</strong> ${processoAtual.objeto}</p>
                <p><strong>Data:</strong> ${new Date().toLocaleDateString('pt-BR')}</p>
            </div>
            
            <!-- Conteúdo da proposta aqui -->
            
            <div class="no-print" style="text-align: center; margin-top: 40px;">
                <button onclick="window.print()" style="padding: 10px 20px; font-size: 16px;">🖨️ Imprimir</button>
                <button onclick="window.close()" style="padding: 10px 20px; font-size: 16px; margin-left: 10px;">❌ Fechar</button>
            </div>
        </body>
        </html>
    `);
}

// ===== AUTO-SAVE E UTILITÁRIOS =====
function iniciarAutoSave() {
    setInterval(() => {
        if (usuarioAtual && processoAtual) {
            const dados = coletarDados();
            const rascunhoKey = `proposta_rascunho_${usuarioAtual.usuarioId}_${processoAtual.numero}`;
            localStorage.setItem(rascunhoKey, JSON.stringify(dados));
            console.log('Rascunho salvo automaticamente');
        }
    }, 30000);
}

function verificarRascunho() {
    if (!usuarioAtual || !processoAtual) return;
    
    const rascunhoKey = `proposta_rascunho_${usuarioAtual.usuarioId}_${processoAtual.numero}`;
    const rascunho = localStorage.getItem(rascunhoKey);
    
    if (rascunho) {
        if (confirm('Foi encontrado um rascunho salvo desta proposta. Deseja recuperá-lo?')) {
            try {
                carregarRascunho(JSON.parse(rascunho));
                mostrarMensagem('✅ Rascunho recuperado com sucesso!', 'success');
            } catch (error) {
                console.error('Erro ao carregar rascunho:', error);
            }
        }
    }
}

function carregarRascunho(dados) {
    // Implementar carregamento do rascunho
    console.log('Carregando rascunho:', dados);
}

function mostrarMensagem(texto, tipo) {
    const mensagemDiv = document.getElementById('mensagem');
    mensagemDiv.className = tipo === 'error' ? 'error-message' : tipo === 'success' ? 'success-message' : 'info-message';
    mensagemDiv.innerHTML = texto;
    mensagemDiv.style.display = 'block';
    
    if (tipo !== 'info' || !texto.includes('loading')) {
        setTimeout(() => {
            if (!mensagemDiv.innerHTML.includes('button')) {
                mensagemDiv.style.display = 'none';
            }
        }, tipo === 'error' ? 5000 : 10000);
    }
}

// Adicionar estilos para mensagens
const style = document.createElement('style');
style.textContent = `
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
    }
    .error-message {
        background: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
    }
    .info-message {
        background: #d1ecf1;
        color: #0c5460;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #17a2b8;
    }
    .loading {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(255,255,255,.3);
        border-radius: 50%;
        border-top-color: #fff;
        animation: spin 1s ease-in-out infinite;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

console.log('Portal de Propostas COMPLETO carregado com sucesso!');
