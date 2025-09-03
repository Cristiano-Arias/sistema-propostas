// ============= COMPLETE FRONTEND JAVASCRIPT =============
// Sistema de Concorrência com fluxo correto

// Global Variables
let socket = null;
let currentUser = null;
let currentProcurement = null;
let currentTR = null;
let currentProposal = null;
let serviceItemsCount = 0;

// API Base URL
const API_BASE = window.location.origin + '/api';

// ============= INITIALIZATION =============
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// ============= AUTHENTICATION =============
async function checkAuth() {
    const token = localStorage.getItem('token');
    if (token) {
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                currentUser = await response.json();
                showDashboard();
            } else {
                throw new Error('Invalid token');
            }
        } catch (error) {
            localStorage.removeItem('token');
            showLogin();
        }
    } else {
        showLogin();
    }
}

function showLogin() {
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('dashboard').classList.remove('active');
}

function showDashboard() {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('dashboard').classList.add('active');
    
    // Update user info
    document.getElementById('userName').textContent = currentUser.full_name;
    document.getElementById('userRole').textContent = currentUser.role;
    
    // Setup dashboard based on role
    setupDashboard();
    
    // Connect WebSocket
    connectSocket();
}

function setupEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem('token', data.access_token);
                currentUser = data.user;
                showDashboard();
            } else {
                document.getElementById('loginError').textContent = data.error || 'Erro ao fazer login';
            }
        } catch (error) {
            document.getElementById('loginError').textContent = 'Erro de conexão';
        }
    });
}

function logout() {
    localStorage.removeItem('token');
    currentUser = null;
    if (socket) {
        socket.disconnect();
    }
    showLogin();
}

// ============= WEBSOCKET =============
function connectSocket() {
    socket = io({
        transports: ['websocket'],
        auth: {
            token: localStorage.getItem('token')
        }
    });
    
    socket.on('connect', () => {
        console.log('Socket connected:', socket.id);
        
        // Join user room
        socket.emit('join_user', { user_id: currentUser.id });
        
        // Join role room
        socket.emit('join_role', { role: currentUser.role });
    });
    
    setupSocketListeners();
}

function setupSocketListeners() {
    // TR Events
    socket.on('tr.created', (data) => {
        if (currentUser.role === 'COMPRADOR') {
            showNotification('Novo TR', `TR "${data.titulo}" foi criado`);
            loadPendingTRs();
        }
    });
    
    socket.on('tr.saved', (data) => {
        showNotification('Termo de Referência', 'TR foi atualizado');
        refreshCurrentView();
    });
    
    socket.on('tr.submitted', (data) => {
        if (currentUser.role === 'COMPRADOR') {
            showNotification('Novo TR para Aprovação', `TR "${data.titulo}" foi submetido`);
            loadPendingTRs();
        }
    });
    
    socket.on('tr.approval_result', (data) => {
        if (currentUser.role === 'REQUISITANTE') {
            const status = data.approved ? 'aprovado' : 'rejeitado';
            showNotification('Resultado da Aprovação', `Seu TR foi ${status}`);
            loadMyTRs();
        }
    });
    
    // Procurement Events
    socket.on('procurement.created', (data) => {
        showNotification('Novo Processo', `Processo "${data.title}" foi criado`);
        refreshCurrentView();
    });
    
    socket.on('procurement.opened', (data) => {
        if (currentUser.role === 'FORNECEDOR') {
            showNotification('Processo Aberto', `"${data.title}" está recebendo propostas`);
            loadAvailableProcurements();
        }
    });
    
    socket.on('procurement.closed', (data) => {
        showNotification('Processo Fechado', `"${data.title}" foi fechado para análise`);
        refreshCurrentView();
    });
    
    // Invite Events
    socket.on('invite.sent', (data) => {
        showNotification('Convite Enviado', `Convite enviado para ${data.email}`);
    });
    
    socket.on('invite.received', (data) => {
        if (currentUser.role === 'FORNECEDOR') {
            showNotification('Novo Convite', `Você foi convidado para o processo "${data.title}"`);
            loadAvailableProcurements();
        }
    });
    
    socket.on('invite.accepted', (data) => {
        if (currentUser.role === 'COMPRADOR') {
            showNotification('Convite Aceito', `${data.supplier} aceitou o convite`);
        }
    });
    
    // Proposal Events
    socket.on('proposal.submitted', (data) => {
        if (currentUser.role === 'COMPRADOR') {
            showNotification('Nova Proposta', `${data.supplier} enviou uma proposta`);
            loadProposals();
        }
    });
    
    socket.on('proposal.updated', (data) => {
        showNotification('Proposta Atualizada', 'Uma proposta foi atualizada');
        refreshCurrentView();
    });
    
    socket.on('proposal.technical_reviewed', (data) => {
        const status = data.approved ? 'aprovada' : 'rejeitada';
        showNotification('Parecer Técnico', `Proposta foi ${status} tecnicamente`);
        refreshCurrentView();
    });
}

// ============= DASHBOARD SETUP =============
function setupDashboard() {
    const navTabs = document.getElementById('navTabs');
    const content = document.getElementById('content');
    
    navTabs.innerHTML = '';
    content.innerHTML = '';
    
    switch(currentUser.role) {
        case 'REQUISITANTE':
            setupRequisitanteDashboard();
            break;
        case 'COMPRADOR':
            setupCompradorDashboard();
            break;
        case 'FORNECEDOR':
            setupFornecedorDashboard();
            break;
    }
}

// ============= REQUISITANTE MODULE =============
function setupRequisitanteDashboard() {
    const navTabs = document.getElementById('navTabs');
    const content = document.getElementById('content');
    
    navTabs.innerHTML = `
        <button class="nav-tab active" onclick="switchTab('tr-create', this)">📝 Criar/Editar TR</button>
        <button class="nav-tab" onclick="switchTab('tr-list', this)">📋 Meus TRs</button>
        <button class="nav-tab" onclick="switchTab('technical-review', this)">🔍 Análise Técnica</button>
    `;
    
    content.innerHTML = `
        <div id="tr-create" class="tab-content active"></div>
        <div id="tr-list" class="tab-content"></div>
        <div id="technical-review" class="tab-content"></div>
    `;
    
    loadTRCreateForm();
    loadMyTRs();
    loadTechnicalProposals();
}

async function loadTRCreateForm() {
    const container = document.getElementById('tr-create');
    
    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">📝 Novo Termo de Referência</h3>
                <div>
                    <button class="btn btn-primary" onclick="saveTR()">💾 Salvar Rascunho</button>
                    <button class="btn btn-success" onclick="submitTR()">📤 Enviar para Aprovação</button>
                </div>
            </div>
            <form id="trForm">
                <h4>📋 Informações Gerais</h4>
                
                <div class="form-group">
                    <label>Título do TR *</label>
                    <input type="text" id="trTitulo" placeholder="Ex: TR para Contratação de Serviços de TI" required>
                </div>
                
                <div class="form-group">
                    <label>Objetivo *</label>
                    <textarea id="trObjetivo" rows="3" placeholder="Descreva o objetivo..." required></textarea>
                </div>
                
                <div class="form-group">
                    <label>Situação Atual</label>
                    <textarea id="trSituacaoAtual" rows="3" placeholder="Descreva a situação atual..."></textarea>
                </div>
                
                <div class="form-group">
                    <label>Descrição dos Serviços *</label>
                    <textarea id="trDescricaoServicos" rows="4" placeholder="Detalhe os serviços necessários..." required></textarea>
                </div>
                
                <div class="grid">
                    <div class="form-group">
                        <label>Orçamento Estimado *</label>
                        <input type="number" id="trOrcamento" step="0.01" placeholder="Ex: 50000.00" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Prazo Máximo de Execução *</label>
                        <input type="text" id="trPrazoMaximo" placeholder="Ex: 90 dias" required>
                    </div>
                </div>
                
                <h4>📍 Condições de Execução</h4>
                <div class="grid">
                    <div class="form-group">
                        <label>Local e Horário</label>
                        <input type="text" id="trLocalHorario" placeholder="Ex: Sede da empresa, 08h às 18h">
                    </div>
                    
                    <div class="form-group">
                        <label>Prazo de Execução</label>
                        <input type="text" id="trPrazoExecucao" placeholder="Ex: 90 dias">
                    </div>
                    
                    <div class="form-group">
                        <label>Garantia</label>
                        <input type="text" id="trGarantia" placeholder="Ex: 12 meses">
                    </div>
                </div>
                
                <h4>📊 Planilha de Serviços</h4>
                <div class="service-items-table">
                    <div class="service-item-row service-item-header">
                        <div>Ordem</div>
                        <div>Código</div>
                        <div>Descrição</div>
                        <div>Unidade</div>
                        <div>Quantidade</div>
                        <div></div>
                        <div>Ações</div>
                    </div>
                    <div id="serviceItemsList"></div>
                </div>
                <button type="button" class="btn btn-secondary" onclick="addServiceItem()">➕ Adicionar Item</button>
                
                <h4>📑 Informações Complementares</h4>
                <div class="form-group">
                    <label>Normas a Observar</label>
                    <textarea id="trNormas" rows="2" placeholder="Normas técnicas aplicáveis..."></textarea>
                </div>
                
                <div class="form-group">
                    <label>Matriz de Responsabilidades</label>
                    <textarea id="trMatriz" rows="3" placeholder="Defina as responsabilidades..."></textarea>
                </div>
                
                <div class="form-group">
                    <label>Segurança e Saúde do Trabalho</label>
                    <textarea id="trSST" rows="2" placeholder="Requisitos de SST..."></textarea>
                </div>
            </form>
        </div>
    `;
    
    // Add initial service item
    addServiceItem();
    
    // Load existing TR if editing
    if (currentTR && currentTR.id) {
        loadTRData(currentTR);
    }
}

async function loadTRData(tr) {
    // Fill form with TR data
    document.getElementById('trTitulo').value = tr.titulo || '';
    document.getElementById('trObjetivo').value = tr.objetivo || '';
    document.getElementById('trSituacaoAtual').value = tr.situacao_atual || '';
    document.getElementById('trDescricaoServicos').value = tr.descricao_servicos || '';
    document.getElementById('trOrcamento').value = tr.orcamento_estimado || '';
    document.getElementById('trPrazoMaximo').value = tr.prazo_maximo_execucao || '';
    document.getElementById('trLocalHorario').value = tr.local_horario_trabalhos || '';
    document.getElementById('trPrazoExecucao').value = tr.prazo_execucao || '';
    document.getElementById('trGarantia').value = tr.garantia || '';
    document.getElementById('trNormas').value = tr.normas_observar || '';
    document.getElementById('trMatriz').value = tr.matriz_responsabilidades || '';
    document.getElementById('trSST').value = tr.sst || '';
    
    // Load service items
    if (tr.service_items && tr.service_items.length > 0) {
        loadServiceItems(tr.service_items);
    }
}

function loadServiceItems(items) {
    const container = document.getElementById('serviceItemsList');
    container.innerHTML = '';
    serviceItemsCount = 0;
    
    if (items.length === 0) {
        addServiceItem();
    } else {
        items.forEach(item => {
            addServiceItem(item);
        });
    }
}

function addServiceItem(item = {}) {
    const container = document.getElementById('serviceItemsList');
    serviceItemsCount++;
    const itemId = `item_${serviceItemsCount}`;
    
    const row = document.createElement('div');
    row.className = 'service-item-row';
    row.id = itemId;
    row.innerHTML = `
        <input type="number" class="service-item-input" value="${item.item_ordem || serviceItemsCount}" 
               data-field="item_ordem" min="1">
        <input type="text" class="service-item-input" value="${item.codigo || ''}" 
               placeholder="COD-${serviceItemsCount}" data-field="codigo">
        <input type="text" class="service-item-input" value="${item.descricao || ''}" 
               placeholder="Descrição do serviço" data-field="descricao" required>
        <select class="service-item-input" data-field="unid">
            <option value="UN" ${item.unid === 'UN' ? 'selected' : ''}>UN</option>
            <option value="M2" ${item.unid === 'M2' ? 'selected' : ''}>M²</option>
            <option value="M3" ${item.unid === 'M3' ? 'selected' : ''}>M³</option>
            <option value="KG" ${item.unid === 'KG' ? 'selected' : ''}>KG</option>
            <option value="HR" ${item.unid === 'HR' ? 'selected' : ''}>HR</option>
            <option value="MES" ${item.unid === 'MES' ? 'selected' : ''}>MÊS</option>
        </select>
        <input type="number" class="service-item-input" value="${item.qtde || 1}" 
               step="0.001" min="0.001" data-field="qtde">
        <div></div>
        <button onclick="removeServiceItem('${itemId}')" class="btn btn-danger" 
                ${serviceItemsCount === 1 ? 'disabled' : ''}>🗑️</button>
    `;
    
    container.appendChild(row);
}

function removeServiceItem(itemId) {
    const element = document.getElementById(itemId);
    if (element && document.querySelectorAll('.service-item-row').length > 2) {
        element.remove();
    }
}

async function saveTR() {
    const titulo = document.getElementById('trTitulo').value;
    if (!titulo) {
        alert('Por favor, informe o título do TR');
        return;
    }
    
    const serviceItems = [];
    document.querySelectorAll('#serviceItemsList .service-item-row').forEach((row, index) => {
        const inputs = row.querySelectorAll('.service-item-input');
        const item = {};
        inputs.forEach(input => {
            const field = input.dataset.field;
            if (field === 'qtde' || field === 'item_ordem') {
                item[field] = parseFloat(input.value) || 0;
            } else {
                item[field] = input.value;
            }
        });
        if (item.descricao) {
            serviceItems.push(item);
        }
    });
    
    if (serviceItems.length === 0) {
        alert('Adicione pelo menos um item de serviço');
        return;
    }
    
    const trData = {
        titulo: titulo,
        objetivo: document.getElementById('trObjetivo').value,
        situacao_atual: document.getElementById('trSituacaoAtual').value,
        descricao_servicos: document.getElementById('trDescricaoServicos').value,
        orcamento_estimado: parseFloat(document.getElementById('trOrcamento').value) || 0,
        prazo_maximo_execucao: document.getElementById('trPrazoMaximo').value,
        local_horario_trabalhos: document.getElementById('trLocalHorario').value,
        prazo_execucao: document.getElementById('trPrazoExecucao').value,
        garantia: document.getElementById('trGarantia').value,
        normas_observar: document.getElementById('trNormas').value,
        matriz_responsabilidades: document.getElementById('trMatriz').value,
        sst: document.getElementById('trSST').value,
        planilha_servico: serviceItems
    };
    
    try {
        const url = currentTR && currentTR.id ? `/tr/${currentTR.id}` : '/tr/create-independent';
        const method = currentTR && currentTR.id ? 'PUT' : 'POST';
        
        const response = await fetchAPI(url, {
            method: method,
            body: JSON.stringify(trData)
        });
        
        if (response.ok) {
            const result = await response.json();
            currentTR = result;
            showNotification('✅ Sucesso', 'TR salvo com sucesso!');
        } else {
            const error = await response.json();
            showNotification('❌ Erro', error.error || 'Erro ao salvar TR');
        }
    } catch (error) {
        console.error('Error saving TR:', error);
        showNotification('❌ Erro', 'Erro ao salvar TR');
    }
}

async function submitTR() {
    if (!currentTR || !currentTR.id) {
        alert('Salve o TR antes de enviar para aprovação');
        return;
    }
    
    // Validate required fields
    if (!document.getElementById('trTitulo').value ||
        !document.getElementById('trObjetivo').value || 
        !document.getElementById('trDescricaoServicos').value ||
        !document.getElementById('trOrcamento').value ||
        !document.getElementById('trPrazoMaximo').value) {
        alert('Preencha todos os campos obrigatórios');
        return;
    }
    
    if (confirm('Deseja enviar o TR para aprovação do comprador?\n\nApós o envio, o TR não poderá ser editado até receber o parecer.')) {
        try {
            const response = await fetchAPI(`/tr/${currentTR.id}/submit`, {
                method: 'POST'
            });
            
            if (response.ok) {
                showNotification('✅ Sucesso', 'TR enviado para aprovação!');
                loadMyTRs();
                document.getElementById('trForm').reset();
                currentTR = null;
                switchTab('tr-list');
            } else {
                const error = await response.json();
                showNotification('❌ Erro', error.error || 'Erro ao enviar TR');
            }
        } catch (error) {
            console.error('Error submitting TR:', error);
            showNotification('❌ Erro', 'Erro ao enviar TR');
        }
    }
}

async function loadMyTRs() {
    const container = document.getElementById('tr-list');
    container.innerHTML = '<div class="spinner"></div>';
    
    try {
        const response = await fetchAPI('/tr/my-trs');
        const trs = await response.json();
        
        if (trs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📋</div>
                    <div class="empty-state-title">Nenhum TR encontrado</div>
                    <div class="empty-state-text">Crie um novo TR na aba "Criar/Editar TR"</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📋 Meus Termos de Referência</h3>
                </div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Título do TR</th>
                            <th>Status</th>
                            <th>Orçamento</th>
                            <th>Prazo</th>
                            <th>Criado em</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${trs.map(tr => `
                            <tr>
                                <td><strong>${tr.titulo || 'Sem título'}</strong></td>
                                <td><span class="status-badge status-${tr.status.toLowerCase()}">${tr.status}</span></td>
                                <td>R$ ${(tr.orcamento_estimado || 0).toLocaleString('pt-BR')}</td>
                                <td>${tr.prazo_maximo_execucao || '-'}</td>
                                <td>${new Date(tr.created_at).toLocaleDateString('pt-BR')}</td>
                                <td>
                                    <button class="btn btn-primary" onclick="viewTR(${tr.id})">👁️ Ver</button>
                                    ${tr.status === 'RASCUNHO' || tr.status === 'REJEITADO' ? 
                                        `<button class="btn btn-warning" onclick="editTR(${tr.id})">✏️ Editar</button>` : ''}
                                    ${tr.procurement_id ? 
                                        `<button class="btn btn-info" onclick="viewProcurement(${tr.procurement_id})">📁 Processo</button>` : ''}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (error) {
        console.error('Error loading TRs:', error);
        container.innerHTML = '<div class="error">Erro ao carregar TRs</div>';
    }
}

async function loadTechnicalProposals() {
    const container = document.getElementById('technical-review');
    container.innerHTML = '<div class="spinner"></div>';
    
    try {
        const proposalsToReview = await fetchAPI('/tr/proposals-for-review').then(r => r.json());
        
        if (proposalsToReview.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔍</div>
                    <div class="empty-state-title">Nenhuma proposta para análise</div>
                    <div class="empty-state-text">Propostas técnicas aparecerão aqui quando enviadas pelos fornecedores</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">🔍 Propostas para Análise Técnica</h3>
                </div>
                <div class="grid">
                    ${proposalsToReview.map(prop => `
                        <div class="card">
                            <div class="card-header">
                                <div>
                                    <div class="card-title">${prop.supplier.name}</div>
                                    <small>${prop.supplier.organization || 'Sem organização'}</small>
                                </div>
                                <span class="status-badge status-${prop.status.toLowerCase()}">${prop.status}</span>
                            </div>
                            <p><strong>Processo:</strong> ${prop.procurement_title}</p>
                            <p><strong>Enviada em:</strong> ${prop.submitted_at ? new Date(prop.submitted_at).toLocaleDateString('pt-BR') : 'N/A'}</p>
                            ${prop.technical_score ? `<p><strong>Nota Técnica:</strong> ${prop.technical_score}/100</p>` : ''}
                            <button class="btn btn-primary" onclick="reviewTechnicalProposal(${prop.procurement_id}, ${prop.id})">
                                ${prop.technical_review ? '📝 Revisar Parecer' : '🔍 Analisar'}
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading proposals:', error);
        container.innerHTML = '<div class="error">Erro ao carregar propostas</div>';
    }
}

async function reviewTechnicalProposal(procId, proposalId) {
    try {
        const proposal = await fetchAPI(`/proposals/${proposalId}`).then(r => r.json());
        
        const modalContent = `
            <h4>Análise Técnica da Proposta</h4>
            <div class="form-group">
                <label><strong>Fornecedor:</strong></label>
                <p>${proposal.supplier.name} - ${proposal.supplier.organization || 'N/A'}</p>
            </div>
            
            <div class="form-group">
                <label><strong>Descrição Técnica:</strong></label>
                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                    ${proposal.technical_description || 'Não fornecida'}
                </div>
            </div>
            
            <h5>Itens da Proposta</h5>
            <table class="table">
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Descrição</th>
                        <th>Qtd Solicitada</th>
                        <th>Qtd Proposta</th>
                        <th>Observações</th>
                    </tr>
                </thead>
                <tbody>
                    ${proposal.items.map(item => `
                        <tr>
                            <td>${item.item_ordem}</td>
                            <td>${item.descricao}</td>
                            <td>${item.qty_baseline}</td>
                            <td>${item.qty_proposed}</td>
                            <td>${item.technical_notes || '-'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            
            <div class="form-group">
                <label>Parecer Técnico *</label>
                <textarea id="technicalReview" rows="4" placeholder="Descreva sua análise técnica...">${proposal.technical_review || ''}</textarea>
            </div>
            
            <div class="form-group">
                <label>Nota Técnica (0-100) *</label>
                <input type="number" id="technicalScore" min="0" max="100" value="${proposal.technical_score || 75}">
            </div>
            
            <div class="form-group">
                <label>Decisão *</label>
                <select id="technicalDecision">
                    <option value="">Selecione...</option>
                    <option value="true">✅ Aprovar Tecnicamente</option>
                    <option value="false">❌ Reprovar Tecnicamente</option>
                </select>
            </div>
            
            <div class="btn-group">
                <button class="btn btn-primary" onclick="saveTechnicalReview(${procId}, ${proposalId})">💾 Salvar Parecer</button>
                <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
            </div>
        `;
        
        openModal('🔍 Análise Técnica', modalContent);
    } catch (error) {
        console.error('Error loading proposal:', error);
        showNotification('❌ Erro', 'Erro ao carregar proposta');
    }
}

async function saveTechnicalReview(procId, proposalId) {
    const review = document.getElementById('technicalReview').value;
    const score = parseInt(document.getElementById('technicalScore').value);
    const decision = document.getElementById('technicalDecision').value;
    
    if (!review || !score || !decision) {
        alert('Preencha todos os campos obrigatórios');
        return;
    }
    
    try {
        const response = await fetchAPI(`/tr/technical-review`, {
            method: 'POST',
            body: JSON.stringify({
                proposal_id: proposalId,
                technical_review: review,
                technical_score: score,
                approved: decision === 'true'
            })
        });
        
        if (response.ok) {
            showNotification('✅ Sucesso', 'Parecer técnico registrado!');
            closeModal();
            loadTechnicalProposals();
        } else {
            const error = await response.json();
            showNotification('❌ Erro', error.error || 'Erro ao salvar parecer');
        }
    } catch (error) {
        console.error('Error saving review:', error);
        showNotification('❌ Erro', 'Erro ao salvar parecer');
    }
}

async function editTR(trId) {
    try {
        const tr = await fetchAPI(`/tr/${trId}`).then(r => r.json());
        currentTR = tr;
        switchTab('tr-create');
        loadTRData(tr);
    } catch (error) {
        console.error('Error loading TR:', error);
        showNotification('❌ Erro', 'Erro ao carregar TR');
    }
}

// ============= COMPRADOR MODULE =============
function setupCompradorDashboard() {
    const navTabs = document.getElementById('navTabs');
    const content = document.getElementById('content');
    
    navTabs.innerHTML = `
        <button class="nav-tab active" onclick="switchTab('tr-approval', this)">✅ TRs para Aprovar</button>
        <button class="nav-tab" onclick="switchTab('procurements', this)">📁 Processos</button>
        <button class="nav-tab" onclick="switchTab('invites', this)">📧 Convites</button>
        <button class="nav-tab" onclick="switchTab('proposals-analysis', this)">📊 Propostas</button>
        <button class="nav-tab" onclick="switchTab('comparison', this)">🤖 Análise IA</button>
    `;
    
    content.innerHTML = `
        <div id="tr-approval" class="tab-content active"></div>
        <div id="procurements" class="tab-content"></div>
        <div id="invites" class="tab-content"></div>
        <div id="proposals-analysis" class="tab-content"></div>
        <div id="comparison" class="tab-content"></div>
    `;
    
    loadPendingTRs();
    loadProcurements();
    loadInvitesManagement();
    loadProposals();
    loadComparison();
}

async function loadPendingTRs() {
    const container = document.getElementById('tr-approval');
    if (!container) return;
    
    container.innerHTML = '<div class="spinner"></div>';
    
    try {
        const trs = await fetchAPI('/tr/pending-approval').then(r => r.json());
        const approvedTRs = await fetchAPI('/tr/approved-without-process').then(r => r.json());
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">✅ Gestão de TRs</h3>
                </div>
                
                ${approvedTRs.length > 0 ? `
                    <div class="section">
                        <h4>📋 TRs Aprovados sem Processo</h4>
                        <div class="grid">
                            ${approvedTRs.map(tr => `
                                <div class="card" style="border: 2px solid #4CAF50;">
                                    <div class="card-header">
                                        <div class="card-title">${tr.titulo}</div>
                                        <span class="status-badge status-aprovado">APROVADO</span>
                                    </div>
                                    <p><strong>Requisitante:</strong> ${tr.creator_name}</p>
                                    <p><strong>Orçamento:</strong> R$ ${(tr.orcamento_estimado || 0).toLocaleString('pt-BR')}</p>
                                    <p><strong>Prazo:</strong> ${tr.prazo_maximo_execucao}</p>
                                    <button class="btn btn-success" onclick="createProcessFromTR(${tr.id})">
                                        📁 Criar Processo
                                    </button>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${trs.length > 0 ? `
                    <div class="section">
                        <h4>⏳ TRs Pendentes de Aprovação</h4>
                        <div class="grid">
                            ${trs.map(tr => `
                                <div class="card">
                                    <div class="card-header">
                                        <div class="card-title">${tr.titulo || 'TR sem título'}</div>
                                        <span class="status-badge status-submetido">AGUARDANDO</span>
                                    </div>
                                    <p><strong>Requisitante:</strong> ${tr.creator_name}</p>
                                    <p><strong>Orçamento:</strong> R$ ${(tr.orcamento_estimado || 0).toLocaleString('pt-BR')}</p>
                                    <p><strong>Prazo:</strong> ${tr.prazo_maximo_execucao || 'Não especificado'}</p>
                                    <p><strong>Submetido em:</strong> ${new Date(tr.submitted_at).toLocaleDateString('pt-BR')}</p>
                                    <div class="btn-group">
                                        <button class="btn btn-primary" onclick="reviewTR(${tr.id})">📋 Analisar TR</button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                ${trs.length === 0 && approvedTRs.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state-icon">✅</div>
                        <div class="empty-state-title">Nenhum TR pendente</div>
                        <div class="empty-state-text">TRs submetidos aparecerão aqui para aprovação</div>
                    </div>
                ` : ''}
            </div>
        `;
    } catch (error) {
        console.error('Error loading TRs:', error);
        container.innerHTML = '<div class="error">Erro ao carregar TRs</div>';
    }
}

async function createProcessFromTR(trId) {
    try {
        const tr = await fetchAPI(`/tr/${trId}`).then(r => r.json());
        
        const modalContent = `
            <h4>📁 Criar Processo de Concorrência</h4>
            <div class="info-box" style="background: #e8f5e9; padding: 10px; margin-bottom: 15px; border-radius: 5px;">
                <strong>TR Base:</strong> ${tr.titulo}<br>
                <strong>Orçamento:</strong> R$ ${(tr.orcamento_estimado || 0).toLocaleString('pt-BR')}<br>
                <strong>Prazo:</strong> ${tr.prazo_maximo_execucao}
            </div>
            
            <div class="form-group">
                <label>Título do Processo *</label>
                <input type="text" id="procTitle" value="${tr.titulo}" placeholder="Ex: Contratação de Serviços de TI">
            </div>
            
            <div class="form-group">
                <label>Descrição do Processo</label>
                <textarea id="procDescription" rows="3" placeholder="Descrição do processo...">${tr.objetivo || ''}</textarea>
            </div>
            
            <div class="form-group">
                <label>Prazo para Recebimento de Propostas</label>
                <input type="datetime-local" id="procDeadline" min="${new Date().toISOString().slice(0,16)}">
            </div>
            
            <div class="btn-group">
                <button class="btn btn-success" onclick="saveProcessFromTR(${trId})">💾 Criar Processo</button>
                <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
            </div>
        `;
        
        openModal('📁 Criar Processo', modalContent);
    } catch (error) {
        console.error('Error:', error);
        showNotification('❌ Erro', 'Erro ao carregar TR');
    }
}

async function saveProcessFromTR(trId) {
    const title = document.getElementById('procTitle').value;
    const description = document.getElementById('procDescription').value;
    const deadline = document.getElementById('procDeadline').value;
    
    if (!title) {
        alert('Título do processo é obrigatório');
        return;
    }
    
    try {
        const response = await fetchAPI('/procurement/from-tr', {
            method: 'POST',
            body: JSON.stringify({
                tr_id: trId,
                title: title,
                description: description,
                deadline_proposals: deadline
            })
        });
        
        if (response.ok) {
            showNotification('✅ Sucesso', 'Processo criado com sucesso!');
            closeModal();
            loadPendingTRs();
            loadProcurements();
        } else {
            const error = await response.json();
            showNotification('❌ Erro', error.error || 'Erro ao criar processo');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('❌ Erro', 'Erro ao criar processo');
    }
}

async function reviewTR(trId) {
    try {
        const tr = await fetchAPI(`/tr/${trId}`).then(r => r.json());
        
        const modalContent = `
            <div style="max-height: 70vh; overflow-y: auto;">
                <h4>📋 Análise do Termo de Referência</h4>
                
                <div class="form-group">
                    <label><strong>Título:</strong></label>
                    <p>${tr.titulo || 'Sem título'}</p>
                </div>
                
                <div class="grid">
                    <div class="form-group">
                        <label><strong>Orçamento Estimado:</strong></label>
                        <p>R$ ${(tr.orcamento_estimado || 0).toLocaleString('pt-BR')}</p>
                    </div>
                    <div class="form-group">
                        <label><strong>Prazo Máximo:</strong></label>
                        <p>${tr.prazo_maximo_execucao || 'Não especificado'}</p>
                    </div>
                </div>
                
                <div class="form-group">
                    <label><strong>Objetivo:</strong></label>
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                        ${tr.objetivo || 'Não informado'}
                    </div>
                </div>
                
                <div class="form-group">
                    <label><strong>Descrição dos Serviços:</strong></label>
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                        ${tr.descricao_servicos || 'Não informado'}
                    </div>
                </div>
                
                ${tr.service_items && tr.service_items.length > 0 ? `
                    <h5>Planilha de Serviços</h5>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th>Descrição</th>
                                <th>Unid</th>
                                <th>Qtd</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${tr.service_items.map(item => `
                                <tr>
                                    <td>${item.item_ordem}</td>
                                    <td>${item.descricao}</td>
                                    <td>${item.unid}</td>
                                    <td>${item.qtde}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : ''}
                
                <hr>
                
                <div class="form-group">
                    <label>Parecer do Comprador</label>
                    <textarea id="approvalComments" rows="3" placeholder="Comentários sobre o TR..."></textarea>
                </div>
                
                <div class="btn-group">
                    <button class="btn btn-success" onclick="approveTR(${tr.id})">✅ Aprovar TR</button>
                    <button class="btn btn-danger" onclick="rejectTR(${tr.id})">❌ Rejeitar</button>
                    <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
                </div>
            </div>
        `;
        
        openModal('📋 Análise de TR', modalContent);
    } catch (error) {
        console.error('Error loading TR:', error);
        showNotification('❌ Erro', 'Erro ao carregar TR');
    }
}

async function approveTR(trId) {
    const comments = document.getElementById('approvalComments').value;
    
    try {
        const response = await fetchAPI(`/tr/${trId}/approve`, {
            method: 'POST',
            body: JSON.stringify({
                approved: true,
                comments: comments || ''
            })
        });
        
        if (response.ok) {
            showNotification('✅ Sucesso', 'TR aprovado! Agora você pode criar o processo.');
            closeModal();
            loadPendingTRs();
        } else {
            const error = await response.json();
            showNotification('❌ Erro', error.error || 'Erro ao aprovar TR');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('❌ Erro', 'Erro ao aprovar TR');
    }
}

async function rejectTR(trId) {
    const comments = document.getElementById('approvalComments').value;
    
    if (!comments) {
        alert('Por favor, informe o motivo da rejeição');
        return;
    }
    
    if (confirm('Tem certeza que deseja rejeitar este TR?')) {
        try {
            const response = await fetchAPI(`/tr/${trId}/approve`, {
                method: 'POST',
                body: JSON.stringify({
                    approved: false,
                    comments: comments
                })
            });
            
            if (response.ok) {
                showNotification('✅ Sucesso', 'TR rejeitado');
                closeModal();
                loadPendingTRs();
            } else {
                const error = await response.json();
                showNotification('❌ Erro', error.error || 'Erro ao rejeitar TR');
            }
        } catch (error) {
            console.error('Error rejecting TR:', error);
            showNotification('❌ Erro', 'Erro ao rejeitar TR');
        }
    }
}

async function loadProcurements() {
    const container = document.getElementById('procurements');
    if (!container) return;
    
    container.innerHTML = '<div class="spinner"></div>';
    
    try {
        const procurements = await fetchAPI('/procurements').then(r => r.json());
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📁 Processos de Concorrência</h3>
                </div>
                ${procurements.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state-icon">📋</div>
                        <div class="empty-state-title">Nenhum processo encontrado</div>
                        <div class="empty-state-text">Aprove um TR e crie um processo na aba "TRs para Aprovar"</div>
                    </div>
                ` : `
                    <table class="table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Título</th>
                                <th>Status</th>
                                <th>Orçamento</th>
                                <th>Prazo Propostas</th>
                                <th>Criado em</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${procurements.map(proc => `
                                <tr>
                                    <td>#${proc.id}</td>
                                    <td><strong>${proc.title}</strong></td>
                                    <td><span class="status-badge status-${proc.status.toLowerCase()}">${proc.status}</span></td>
                                    <td>R$ ${(proc.orcamento_disponivel || 0).toLocaleString('pt-BR')}</td>
                                    <td>${proc.deadline_proposals ? new Date(proc.deadline_proposals).toLocaleDateString('pt-BR') : '-'}</td>
                                    <td>${new Date(proc.created_at).toLocaleDateString('pt-BR')}</td>
                                    <td>
                                        <button class="btn btn-primary" onclick="viewProcurement(${proc.id})">👁️</button>
                                        ${proc.status === 'TR_APROVADO' ? 
                                            `<button class="btn btn-success" onclick="openProcurementModal(${proc.id})">📢 Abrir</button>` : ''}
                                        ${proc.status === 'ABERTO' ? 
                                            `<button class="btn btn-warning" onclick="closeProcurement(${proc.id})">🔒 Fechar</button>` : ''}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `}
            </div>
        `;
    } catch (error) {
        console.error('Error loading procurements:', error);
        container.innerHTML = '<div class="error">Erro ao carregar processos</div>';
    }
}

// Continua com resto das funções...
async function openProcurementModal(procId) {
    const modalContent = `
        <div class="form-group">
            <label>Prazo para Propostas (opcional)</label>
            <input type="datetime-local" id="procDeadline" min="${new Date().toISOString().slice(0,16)}">
        </div>
        <div class="btn-group">
            <button class="btn btn-success" onclick="openProcurement(${procId})">📢 Abrir Processo</button>
            <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
        </div>
    `;
    
    openModal('📢 Abrir Processo para Propostas', modalContent);
}

async function openProcurement(procId) {
    const deadline = document.getElementById('procDeadline').value;
    
    try {
        const response = await fetchAPI(`/procurements/${procId}/open`, {
            method: 'POST',
            body: JSON.stringify({ deadline })
        });
        
        if (response.ok) {
            showNotification('✅ Sucesso', 'Processo aberto para propostas!');
            closeModal();
            loadProcurements();
        } else {
            const error = await response.json();
            showNotification('❌ Erro', error.error || 'Erro ao abrir processo');
        }
    } catch (error) {
        console.error('Error opening procurement:', error);
        showNotification('❌ Erro', 'Erro ao abrir processo');
    }
}

async function closeProcurement(procId) {
    if (confirm('Deseja fechar o processo para análise?\n\nNão serão aceitas novas propostas após o fechamento.')) {
        try {
            const response = await fetchAPI(`/procurements/${procId}/close`, {
                method: 'POST'
            });
            
            if (response.ok) {
                showNotification('✅ Sucesso', 'Processo fechado para análise!');
                loadProcurements();
            } else {
                const error = await response.json();
                showNotification('❌ Erro', error.error || 'Erro ao fechar processo');
            }
        } catch (error) {
            console.error('Error closing procurement:', error);
            showNotification('❌ Erro', 'Erro ao fechar processo');
        }
    }
}

async function loadInvitesManagement() {
    const container = document.getElementById('invites');
    if (!container) return;
    
    container.innerHTML = '<div class="spinner"></div>';
    
    try {
        const procurements = await fetchAPI('/procurements').then(r => r.json());
        const openProcs = procurements.filter(p => p.status === 'ABERTO');
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📧 Gerenciar Convites</h3>
                </div>
                <div class="form-group">
                    <label>Selecione o Processo</label>
                    <select id="inviteProcurement" onchange="loadProcurementInvites()">
                        <option value="">Selecione um processo aberto...</option>
                        ${openProcs.map(p => `
                            <option value="${p.id}">${p.title}</option>
                        `).join('')}
                    </select>
                </div>
                <div id="invitesList"></div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading invites:', error);
        container.innerHTML = '<div class="error">Erro ao carregar convites</div>';
    }
}

async function loadProcurementInvites() {
    const procId = document.getElementById('inviteProcurement').value;
    const container = document.getElementById('invitesList');
    
    if (!procId) {
        container.innerHTML = '';
        return;
    }
    
    try {
        const invites = await fetchAPI(`/procurements/${procId}/invites`).then(r => r.json());
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h4>Convites Enviados</h4>
                    <button class="btn btn-primary" onclick="sendInviteModal(${procId})">📧 Enviar Convite</button>
                </div>
                ${invites.length === 0 ? 
                    '<p>Nenhum convite enviado ainda</p>' :
                    `<table class="table">
                        <thead>
                            <tr>
                                <th>Email</th>
                                <th>Status</th>
                                <th>Enviado em</th>
                                <th>Aceito em</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${invites.map(inv => `
                                <tr>
                                    <td>${inv.email}</td>
                                    <td><span class="status-badge status-${inv.accepted ? 'aprovado' : 'pendente'}">${inv.accepted ? 'Aceito' : 'Pendente'}</span></td>
                                    <td>${new Date(inv.created_at).toLocaleDateString('pt-BR')}</td>
                                    <td>${inv.accepted_at ? new Date(inv.accepted_at).toLocaleDateString('pt-BR') : '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>`
                }
            </div>
        `;
    } catch (error) {
        console.error('Error loading invites:', error);
        container.innerHTML = '<div class="error">Erro ao carregar convites</div>';
    }
}

async function sendInviteModal(procId) {
    const modalContent = `
        <div class="form-group">
            <label>Email do Fornecedor *</label>
            <input type="email" id="inviteEmail" placeholder="fornecedor@empresa.com" required>
        </div>
        <div class="btn-group">
            <button class="btn btn-primary" onclick="sendInvite(${procId})">📧 Enviar Convite</button>
            <button class="btn btn-secondary" onclick="closeModal()">Cancelar</button>
        </div>
    `;
    
    openModal('📧 Enviar Convite', modalContent);
}

async function sendInvite(procId) {
    const email = document.getElementById('inviteEmail').value;
    
    if (!email) {
        alert('Informe o email do fornecedor');
        return;
    }
    
    try {
        const response = await fetchAPI(`/procurements/${procId}/invite`, {
            method: 'POST',
            body: JSON.stringify({ email })
        });
        
        if (response.ok) {
            showNotification('✅ Sucesso', `Convite enviado para ${email}`);
            closeModal();
            loadProcurementInvites();
        } else {
            const error = await response.json();
            showNotification('❌ Erro', error.error || 'Erro ao enviar convite');
        }
    } catch (error) {
        console.error('Error sending invite:', error);
        showNotification('❌ Erro', 'Erro ao enviar convite');
    }
}

async function loadProposals() {
    const container = document.getElementById('proposals-analysis');
    if (!container) return;
    
    container.innerHTML = '<div class="spinner"></div>';
    
    try {
        const procurements = await fetchAPI('/procurements').then(r => r.json());
        
        let allProposals = [];
        for (const proc of procurements) {
            if (proc.status === 'ABERTO' || proc.status === 'ANALISE_TECNICA' || proc.status === 'ANALISE_COMERCIAL') {
                try {
                    const proposals = await fetchAPI(`/procurements/${proc.id}/proposals`).then(r => r.json());
                    proposals.forEach(p => {
                        p.procurement_title = proc.title;
                        p.procurement_id = proc.id;
                    });
                    allProposals = allProposals.concat(proposals);
                } catch (err) {
                    console.log('No proposals for', proc.id);
                }
            }
        }
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📊 Propostas Recebidas</h3>
                </div>
                ${allProposals.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state-icon">📊</div>
                        <div class="empty-state-title">Nenhuma proposta recebida</div>
                        <div class="empty-state-text">As propostas aparecerão aqui quando enviadas pelos fornecedores</div>
                    </div>
                ` : `
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Processo</th>
                                <th>Fornecedor</th>
                                <th>Status</th>
                                <th>Nota Técnica</th>
                                <th>Valor Total</th>
                                <th>Enviada em</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${allProposals.map(prop => `
                                <tr>
                                    <td>${prop.procurement_title}</td>
                                    <td>
                                        <strong>${prop.supplier.name}</strong><br>
                                        <small>${prop.supplier.organization || ''}</small>
                                    </td>
                                    <td><span class="status-badge status-${prop.status.toLowerCase()}">${prop.status}</span></td>
                                    <td>${prop.technical_score ? `${prop.technical_score}/100` : '-'}</td>
                                    <td>${prop.total_value ? `R$ ${prop.total_value.toLocaleString('pt-BR')}` : '-'}</td>
                                    <td>${prop.submitted_at ? new Date(prop.submitted_at).toLocaleDateString('pt-BR') : '-'}</td>
                                    <td>
                                        <button class="btn btn-primary" onclick="viewProposal(${prop.id})">👁️ Ver</button>
                                        ${prop.status === 'ENVIADA' ? 
                                            `<button class="btn btn-info" onclick="sendToTechnicalReview(${prop.procurement_id}, ${prop.id})">🔍 Enviar p/ Análise</button>` : ''}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `}
            </div>
        `;
    } catch (error) {
        console.error('Error loading proposals:', error);
        container.innerHTML = '<div class="error">Erro ao carregar propostas</div>';
    }
}

async function loadComparison() {
    const container = document.getElementById('comparison');
    if (!container) return;
    
    container.innerHTML = '<div class="spinner"></div>';
    
    try {
        const procurements = await fetchAPI('/procurements').then(r => r.json());
        const procsWithProposals = procurements.filter(p => 
            p.status === 'ANALISE_TECNICA' || p.status === 'ANALISE_COMERCIAL'
        );
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">🤖 Análise Comparativa com IA</h3>
                </div>
                <div class="form-group">
                    <label>Selecione o Processo para Análise</label>
                    <select id="comparisonProcurement" onchange="loadProcurementComparison()">
                        <option value="">Selecione um processo...</option>
                        ${procsWithProposals.map(p => `
                            <option value="${p.id}">${p.title}</option>
                        `).join('')}
                    </select>
                </div>
                <div id="comparisonResult"></div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading comparison:', error);
        container.innerHTML = '<div class="error">Erro ao carregar análise</div>';
    }
}

// ============= FORNECEDOR MODULE =============
function setupFornecedorDashboard() {
    const navTabs = document.getElementById('navTabs');
    const content = document.getElementById('content');
    
    navTabs.innerHTML = `
        <button class="nav-tab active" onclick="switchTab('available-procurements', this)">📢 Processos Disponíveis</button>
        <button class="nav-tab" onclick="switchTab('my-proposals', this)">📄 Minhas Propostas</button>
        <button class="nav-tab" onclick="switchTab('create-proposal', this)">✍️ Criar Proposta</button>
    `;
    
    content.innerHTML = `
        <div id="available-procurements" class="tab-content active"></div>
        <div id="my-proposals" class="tab-content"></div>
        <div id="create-proposal" class="tab-content"></div>
    `;
    
    loadAvailableProcurements();
    loadMyProposals();
    loadProposalForm();
}

async function loadAvailableProcurements() {
    const container = document.getElementById('available-procurements');
    if (!container) return;
    
    container.innerHTML = '<div class="spinner"></div>';
    
    try {
        const procurements = await fetchAPI('/procurements').then(r => r.json());
        const available = procurements.filter(p => p.status === 'ABERTO' || p.status === 'ANALISE_TECNICA');
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📢 Processos Abertos para Propostas</h3>
                </div>
                ${available.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state-icon">📢</div>
                        <div class="empty-state-title">Nenhum processo disponível</div>
                        <div class="empty-state-text">Novos processos aparecerão aqui quando disponíveis</div>
                    </div>
                ` : `
                    <div class="grid">
                        ${available.map(proc => `
                            <div class="card">
                                <div class="card-header">
                                    <div class="card-title">${proc.title}</div>
                                    <span class="status-badge status-aberto">ABERTO</span>
                                </div>
                                <p>${proc.description || 'Sem descrição'}</p>
                                <p><strong>Prazo:</strong> ${proc.deadline ? new Date(proc.deadline).toLocaleDateString('pt-BR') : 'Sem prazo definido'}</p>
                                <div class="btn-group">
                                    <button class="btn btn-primary" onclick="viewTRForProposal(${proc.id})">📋 Ver TR</button>
                                    <button class="btn btn-success" onclick="createProposalFor(${proc.id})">✍️ Criar Proposta</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `}
            </div>
        `;
    } catch (error) {
        console.error('Error loading procurements:', error);
        container.innerHTML = '<div class="error">Erro ao carregar processos</div>';
    }
}

async function loadMyProposals() {
    const container = document.getElementById('my-proposals');
    if (!container) return;
    
    container.innerHTML = '<div class="spinner"></div>';
    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📄</div>
            <div class="empty-state-title">Nenhuma proposta enviada</div>
            <div class="empty-state-text">Suas propostas aparecerão aqui</div>
        </div>
    `;
}

async function loadProposalForm() {
    const container = document.getElementById('create-proposal');
    if (!container) return;
    
    const procurements = await fetchAPI('/procurements').then(r => r.json());
    const available = procurements.filter(p => p.status === 'ABERTO');
    
    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">✍️ Nova Proposta</h3>
                <div>
                    <button class="btn btn-primary" onclick="saveProposal()">💾 Salvar Rascunho</button>
                    <button class="btn btn-success" onclick="submitProposal()">📤 Enviar Proposta</button>
                </div>
            </div>
            <form id="proposalForm">
                <div class="form-group">
                    <label>Processo *</label>
                    <select id="proposalProcurement" onchange="loadTRForProposal()" required>
                        <option value="">Selecione um processo...</option>
                        ${available.map(p => `
                            <option value="${p.id}">${p.title}</option>
                        `).join('')}
                    </select>
                </div>
                
                <div id="trDetails" style="display:none;">
                    <h4>📋 Termo de Referência</h4>
                    <div class="card" style="background: #f8f9fa;">
                        <div id="trContent"></div>
                    </div>
                </div>
                
                <h4>📝 Proposta Técnica</h4>
                <div class="form-group">
                    <label>Descrição Técnica da Solução *</label>
                    <textarea id="technicalDescription" rows="5" placeholder="Descreva detalhadamente sua solução técnica..." required></textarea>
                </div>
                
                <h4>💰 Proposta Comercial</h4>
                <div class="grid">
                    <div class="form-group">
                        <label>Condições de Pagamento *</label>
                        <input type="text" id="paymentConditions" placeholder="Ex: 30/60/90 dias" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Prazo de Entrega *</label>
                        <input type="text" id="deliveryTime" placeholder="Ex: 45 dias úteis" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Garantia *</label>
                        <input type="text" id="warrantyTerms" placeholder="Ex: 12 meses" required>
                    </div>
                </div>
                
                <h4>📊 Itens e Preços</h4>
                <div id="proposalItemsContainer"></div>
            </form>
        </div>
    `;
}

// ============= UTILITY FUNCTIONS =============
function switchTab(tabId, tabElement) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    const selectedTab = document.getElementById(tabId);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Update nav tabs
    if (tabElement) {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        tabElement.classList.add('active');
    }
}

function openModal(title, content) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = content;
    document.getElementById('modal').classList.add('active');
}

function closeModal() {
    document.getElementById('modal').classList.remove('active');
}

function showNotification(title, body) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerHTML = `
        <div class="notification-title">${title}</div>
        <div class="notification-body">${body}</div>
    `;
    
    document.getElementById('notifications').appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function refreshCurrentView() {
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab) {
        const tabId = activeTab.id;
        switch(tabId) {
            case 'procurements':
                loadProcurements();
                break;
            case 'tr-list':
                loadMyTRs();
                break;
            case 'technical-review':
                loadTechnicalProposals();
                break;
            case 'tr-approval':
                loadPendingTRs();
                break;
            case 'proposals-analysis':
                loadProposals();
                break;
            case 'available-procurements':
                loadAvailableProcurements();
                break;
            case 'my-proposals':
                loadMyProposals();
                break;
        }
    }
}

async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };
    
    if (options.body && typeof options.body !== 'string') {
        options.body = JSON.stringify(options.body);
    }
    
    return fetch(`${API_BASE}${endpoint}`, { ...defaultOptions, ...options });
}

// Stubs for missing functions
async function viewProcurement(procId) {
    console.log('View procurement', procId);
}

async function reviewTR(procId) {
    console.log('Review TR', procId);
}

async function loadProcurementInvites() {
    console.log('Load procurement invites');
}

async function loadProcurementComparison() {
    console.log('Load procurement comparison');
}

async function viewProposal(proposalId) {
    console.log('View proposal', proposalId);
}

async function viewTR(procId) {
    console.log('View TR', procId);
}

async function editTR(procId) {
    switchTab('tr-create');
    document.getElementById('trProcurement').value = procId;
    loadTR();
}

async function viewTRForProposal(procId) {
    console.log('View TR for proposal', procId);
}

async function createProposalFor(procId) {
    switchTab('create-proposal');
    document.getElementById('proposalProcurement').value = procId;
    loadTRForProposal();
}

async function loadTRForProposal() {
    console.log('Load TR for proposal');
}

async function saveProposal() {
    console.log('Save proposal');
}

async function submitProposal() {
    console.log('Submit proposal');
}

// Click outside modal to close
if (document.getElementById('modal')) {
    document.getElementById('modal').addEventListener('click', (e) => {
        if (e.target.id === 'modal') {
            closeModal();
        }
    });
}

// Export for debugging
window.debugApp = {
    currentUser: () => currentUser,
    socket: () => socket,
    fetchAPI,
    showNotification
};
