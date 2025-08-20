/**
 * Sistema de Integração entre Módulos
 * Conecta Requisitante -> Comprador -> Fornecedor
 */

// ========================================
// SISTEMA DE NOTIFICAÇÕES E CONFIRMAÇÕES
// ========================================

function criarNotificacao(modulo, dados) {
    const chave = `notificacoes_${modulo}`;
    let notificacoes = JSON.parse(localStorage.getItem(chave) || '[]');
    
    const notificacao = {
        id: Date.now().toString(),
        ...dados,
        lida: false,
        data: new Date().toISOString()
    };
    
    notificacoes.unshift(notificacao);
    localStorage.setItem(chave, JSON.stringify(notificacoes));
    
    // Mostrar alerta se usuário estiver online
    if (localStorage.getItem(`${modulo}_user`)) {
        mostrarAlertaNotificacao(notificacao);
    }
    
    return notificacao;
}

function mostrarAlertaNotificacao(notificacao) {
    const alert = document.createElement('div');
    alert.className = 'notificacao-popup';
    alert.innerHTML = `
        <div style="position: fixed; top: 20px; right: 20px; background: #28a745; color: white; 
                    padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 9999; max-width: 300px; animation: slideIn 0.3s ease;">
            <h4 style="margin: 0 0 5px 0; font-size: 16px;">🔔 ${notificacao.titulo}</h4>
            <p style="margin: 0; font-size: 14px;">${notificacao.mensagem}</p>
        </div>
    `;
    document.body.appendChild(alert);
    
    setTimeout(() => alert.remove(), 5000);
}

// ========================================
// MÓDULO REQUISITANTE
// ========================================

// Enviar TR para aprovação do Comprador
function enviarTRParaComprador(tr) {
    // Adicionar à fila de aprovação
    let trsPendentes = JSON.parse(localStorage.getItem('trs_pendentes_aprovacao') || '[]');
    
    const trParaAprovacao = {
        ...tr,
        status: 'PENDENTE_APROVACAO',
        dataEnvio: new Date().toISOString(),
        enviadoPor: JSON.parse(localStorage.getItem('requisitante_user'))?.nome || 'Requisitante'
    };
    
    trsPendentes.push(trParaAprovacao);
    localStorage.setItem('trs_pendentes_aprovacao', JSON.stringify(trsPendentes));
    
    // Atualizar status do TR original
    let trsRequisitante = JSON.parse(localStorage.getItem('termos_referencia') || '[]');
    const index = trsRequisitante.findIndex(t => t.id === tr.id);
    if (index !== -1) {
        trsRequisitante[index].status = 'PENDENTE_APROVACAO';
        localStorage.setItem('termos_referencia', JSON.stringify(trsRequisitante));
    }
    
    // Notificar comprador
    criarNotificacao('comprador', {
        tipo: 'novo_tr',
        titulo: '📋 Novo TR para Aprovação',
        mensagem: `TR ${tr.numeroTR} - ${tr.objeto}`,
        tr_id: tr.id
    });
    
    // Mostrar confirmação para requisitante
    mostrarConfirmacao('✅ TR enviado com sucesso para o setor de compras!');
    
    return true;
}

// Download TR em Word
function downloadTRWord(tr) {
    const conteudo = gerarConteudoTRWord(tr);
    const blob = new Blob([conteudo], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `TR_${tr.numeroTR}.doc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    mostrarConfirmacao('📄 Download do TR iniciado!');
}

function gerarConteudoTRWord(tr) {
    return `
        TERMO DE REFERÊNCIA
        
        Número: ${tr.numeroTR}
        Data: ${new Date(tr.dataCriacao).toLocaleDateString('pt-BR')}
        
        1. OBJETO
        ${tr.objeto}
        
        2. DESCRIÇÃO
        ${tr.descricaoObjeto}
        
        3. JUSTIFICATIVA
        ${tr.justificativa}
        
        4. ESPECIFICAÇÕES TÉCNICAS
        ${tr.especificacoesTecnicas}
        
        5. PRAZO DE EXECUÇÃO
        ${tr.prazoExecucao} dias
        
        6. LOCAL DE ENTREGA
        ${tr.localEntrega}
        
        7. CONDIÇÕES DE PAGAMENTO
        ${tr.condicoesPagamento}
        
        8. VALOR ESTIMADO
        R$ ${tr.valorEstimado ? parseFloat(tr.valorEstimado).toLocaleString('pt-BR', {minimumFractionDigits: 2}) : 'Não informado'}
        
        Status: ${tr.status}
        ${tr.parecerComprador ? '\nParecer do Comprador: ' + tr.parecerComprador : ''}
    `;
}

// ========================================
// MÓDULO COMPRADOR
// ========================================

// Aprovar TR e criar processo
function aprovarTRComprador(trId, parecer) {
    let trsPendentes = JSON.parse(localStorage.getItem('trs_pendentes_aprovacao') || '[]');
    const trIndex = trsPendentes.findIndex(tr => tr.id === trId);
    
    if (trIndex === -1) {
        mostrarErro('TR não encontrado!');
        return false;
    }
    
    const tr = trsPendentes[trIndex];
    
    // Mover para TRs aprovados
    let trsAprovados = JSON.parse(localStorage.getItem('trs_aprovados') || '[]');
    tr.status = 'APROVADO';
    tr.parecerComprador = parecer;
    tr.dataAprovacao = new Date().toISOString();
    tr.aprovadoPor = JSON.parse(localStorage.getItem('comprador_user'))?.nome || 'Comprador';
    
    trsAprovados.push(tr);
    trsPendentes.splice(trIndex, 1);
    
    // Salvar alterações
    localStorage.setItem('trs_aprovados', JSON.stringify(trsAprovados));
    localStorage.setItem('trs_pendentes_aprovacao', JSON.stringify(trsPendentes));
    
    // Notificar requisitante
    criarNotificacao('requisitante', {
        tipo: 'tr_aprovado',
        titulo: '✅ TR Aprovado!',
        mensagem: `Seu TR ${tr.numeroTR} foi aprovado pelo setor de compras`,
        tr_id: tr.id
    });
    
    mostrarConfirmacao('✅ TR aprovado com sucesso! Agora você pode criar um processo de compra.');
    
    return tr;
}

// Criar processo de compra
function criarProcessoCompra(dados) {
    const processo = {
        id: Date.now().toString(),
        numeroProcesso: `PROC-${new Date().getFullYear()}-${Date.now().toString().slice(-6)}`,
        ...dados,
        status: 'ABERTO',
        dataCriacao: new Date().toISOString(),
        criadoPor: JSON.parse(localStorage.getItem('comprador_user'))?.nome || 'Comprador',
        fornecedoresConvidados: [],
        propostas: []
    };
    
    let processos = JSON.parse(localStorage.getItem('processos_compra') || '[]');
    processos.push(processo);
    localStorage.setItem('processos_compra', JSON.stringify(processos));
    
    mostrarConfirmacao(`✅ Processo ${processo.numeroProcesso} criado com sucesso!`);
    
    return processo;
}

// Convidar fornecedores
function convidarFornecedores(processoId, fornecedoresIds) {
    let processos = JSON.parse(localStorage.getItem('processos_compra') || '[]');
    const processo = processos.find(p => p.id === processoId);
    
    if (!processo) {
        mostrarErro('Processo não encontrado!');
        return false;
    }
    
    // Gerar credenciais para fornecedores
    let credenciais = JSON.parse(localStorage.getItem('credenciais_fornecedores') || '[]');
    const fornecedores = JSON.parse(localStorage.getItem('fornecedores_cadastrados') || '[]');
    
    fornecedoresIds.forEach(fornId => {
        const fornecedor = fornecedores.find(f => f.id === fornId);
        if (fornecedor) {
            // Gerar credencial
            const credencial = {
                id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
                processoId: processoId,
                numeroProcesso: processo.numeroProcesso,
                fornecedorId: fornecedor.id,
                cnpj: fornecedor.cnpj,
                razaoSocial: fornecedor.razaoSocial,
                email: fornecedor.email,
                login: `forn_${fornecedor.cnpj.replace(/\D/g, '').slice(-6)}`,
                senha: gerarSenhaAleatoria(),
                ativo: true,
                dataCriacao: new Date().toISOString()
            };
            
            credenciais.push(credencial);
            
            // Adicionar ao processo
            processo.fornecedoresConvidados.push({
                id: fornecedor.id,
                nome: fornecedor.razaoSocial,
                cnpj: fornecedor.cnpj,
                credencial: credencial.login
            });
            
            // Notificar fornecedor (simulado)
            criarNotificacao('fornecedor_' + fornecedor.id, {
                tipo: 'convite_processo',
                titulo: '📧 Novo Convite para Processo',
                mensagem: `Você foi convidado para o processo ${processo.numeroProcesso}`,
                processo_id: processoId,
                credenciais: {
                    login: credencial.login,
                    senha: credencial.senha
                }
            });
        }
    });
    
    // Salvar alterações
    localStorage.setItem('credenciais_fornecedores', JSON.stringify(credenciais));
    localStorage.setItem('processos_compra', JSON.stringify(processos));
    
    mostrarConfirmacao(`✅ ${fornecedoresIds.length} fornecedor(es) convidado(s) com sucesso!`);
    
    return true;
}

// Receber proposta
function receberProposta(proposta) {
    let processos = JSON.parse(localStorage.getItem('processos_compra') || '[]');
    const processo = processos.find(p => p.id === proposta.processoId);
    
    if (!processo) return false;
    
    // Adicionar proposta ao processo
    processo.propostas = processo.propostas || [];
    processo.propostas.push({
        id: proposta.id,
        fornecedorId: proposta.fornecedorId,
        fornecedorNome: proposta.fornecedorNome,
        valor: proposta.valor,
        prazo: proposta.prazo,
        dataEnvio: proposta.dataEnvio
    });
    
    localStorage.setItem('processos_compra', JSON.stringify(processos));
    
    // Notificar comprador
    criarNotificacao('comprador', {
        tipo: 'nova_proposta',
        titulo: '📬 Nova Proposta Recebida',
        mensagem: `${proposta.fornecedorNome} enviou proposta para o processo ${processo.numeroProcesso}`,
        processo_id: processo.id,
        proposta_id: proposta.id
    });
    
    return true;
}

// ========================================
// MÓDULO FORNECEDOR
// ========================================

// Enviar proposta
function enviarPropostaFornecedor(dados) {
    const fornecedor = JSON.parse(localStorage.getItem('fornecedor_logado') || '{}');
    
    const proposta = {
        id: Date.now().toString(),
        ...dados,
        fornecedorId: fornecedor.id,
        fornecedorNome: fornecedor.razaoSocial,
        fornecedorCNPJ: fornecedor.cnpj,
        status: 'ENVIADA',
        dataEnvio: new Date().toISOString()
    };
    
    // Salvar proposta local do fornecedor
    let minhasPropostas = JSON.parse(localStorage.getItem('propostas_fornecedor_' + fornecedor.id) || '[]');
    minhasPropostas.push(proposta);
    localStorage.setItem('propostas_fornecedor_' + fornecedor.id, JSON.stringify(minhasPropostas));
    
    // Enviar para comprador
    receberProposta(proposta);
    
    // Confirmação para fornecedor
    mostrarConfirmacao('✅ Proposta enviada com sucesso! O setor de compras foi notificado.');
    
    return proposta;
}

// Visualizar processos disponíveis
function listarProcessosDisponiveis() {
    const fornecedor = JSON.parse(localStorage.getItem('fornecedor_logado') || '{}');
    const processos = JSON.parse(localStorage.getItem('processos_compra') || '[]');
    
    // Filtrar processos onde o fornecedor foi convidado
    return processos.filter(processo => {
        return processo.fornecedoresConvidados?.some(f => f.id === fornecedor.id);
    });
}

// ========================================
// FUNÇÕES AUXILIARES
// ========================================

function gerarSenhaAleatoria() {
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#';
    let senha = '';
    for (let i = 0; i < 8; i++) {
        senha += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return senha;
}

function mostrarConfirmacao(mensagem) {
    const div = document.createElement('div');
    div.innerHTML = `
        <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                    background: white; padding: 30px; border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2); z-index: 10000;
                    text-align: center; min-width: 300px;">
            <div style="color: #28a745; font-size: 48px; margin-bottom: 15px;">✅</div>
            <p style="color: #333; font-size: 16px; margin: 0;">${mensagem}</p>
            <button onclick="this.closest('div').remove()" 
                    style="margin-top: 20px; padding: 10px 30px; background: #28a745;
                           color: white; border: none; border-radius: 5px; cursor: pointer;">
                OK
            </button>
        </div>
    `;
    document.body.appendChild(div);
}

function mostrarErro(mensagem) {
    const div = document.createElement('div');
    div.innerHTML = `
        <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                    background: white; padding: 30px; border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2); z-index: 10000;
                    text-align: center; min-width: 300px;">
            <div style="color: #dc3545; font-size: 48px; margin-bottom: 15px;">❌</div>
            <p style="color: #333; font-size: 16px; margin: 0;">${mensagem}</p>
            <button onclick="this.closest('div').remove()" 
                    style="margin-top: 20px; padding: 10px 30px; background: #dc3545;
                           color: white; border: none; border-radius: 5px; cursor: pointer;">
                Fechar
            </button>
        </div>
    `;
    document.body.appendChild(div);
}

// ========================================
// CADASTRO DE FORNECEDORES
// ========================================

function cadastrarFornecedor(dados) {
    let fornecedores = JSON.parse(localStorage.getItem('fornecedores_cadastrados') || '[]');
    
    const novoFornecedor = {
        id: Date.now().toString(),
        ...dados,
        dataCadastro: new Date().toISOString(),
        ativo: true
    };
    
    fornecedores.push(novoFornecedor);
    localStorage.setItem('fornecedores_cadastrados', JSON.stringify(fornecedores));
    
    mostrarConfirmacao('✅ Fornecedor cadastrado com sucesso!');
    
    return novoFornecedor;
}

// Inicializar alguns fornecedores de exemplo
function inicializarFornecedoresPadrao() {
    const fornecedores = [
        {
            id: '1',
            razaoSocial: 'Tech Solutions Ltda',
            cnpj: '12.345.678/0001-90',
            email: 'contato@techsolutions.com',
            telefone: '(11) 3456-7890',
            endereco: 'Rua das Tecnologias, 123',
            ativo: true
        },
        {
            id: '2',
            razaoSocial: 'Construtora ABC',
            cnpj: '98.765.432/0001-10',
            email: 'comercial@construtorabc.com',
            telefone: '(11) 9876-5432',
            endereco: 'Av. das Construções, 456',
            ativo: true
        },
        {
            id: '3',
            razaoSocial: 'Serviços Gerais XYZ',
            cnpj: '11.222.333/0001-44',
            email: 'contato@servicosxyz.com',
            telefone: '(11) 2222-3333',
            endereco: 'Rua dos Serviços, 789',
            ativo: true
        }
    ];
    
    localStorage.setItem('fornecedores_cadastrados', JSON.stringify(fornecedores));
}

// Verificar e inicializar fornecedores na primeira execução
if (!localStorage.getItem('fornecedores_cadastrados')) {
    inicializarFornecedoresPadrao();
}

// Exportar funções para uso global
window.IntegracaoModulos = {
    // Requisitante
    enviarTRParaComprador,
    downloadTRWord,
    
    // Comprador
    aprovarTRComprador,
    criarProcessoCompra,
    convidarFornecedores,
    receberProposta,
    cadastrarFornecedor,
    
    // Fornecedor
    enviarPropostaFornecedor,
    listarProcessosDisponiveis,
    
    // Notificações
    criarNotificacao,
    mostrarConfirmacao,
    mostrarErro
};


console.log('✅ Sistema de integração carregado com sucesso!');
