// ========================================
// SISTEMA DE AUTENTICAÇÃO - ATUALIZADO PARA MULTI-COMPRADOR E NOVOS MÓDULOS
// Arquivo: auth.js
// ========================================

// Salve este arquivo como auth.js e inclua em todas as páginas protegidas:
// <script src="auth.js"></script>

const Auth = {
    // Verificar se usuário está autenticado
    verificarAutenticacao: function(tipoRequerido = null) {
        const sessao = sessionStorage.getItem('sessao_ativa');
        
        if (!sessao) {
            // Não autenticado
            window.location.href = 'index.html';
            return false;
        }
        
        try {
            const sessaoObj = JSON.parse(sessao);
            
            // Verificar expiração (30 minutos)
            const inicio = new Date(sessaoObj.inicio);
            const agora = new Date();
            const minutos = (agora - inicio) / 60000;
            
            if (minutos > 30) {
                // Sessão expirada
                this.logout('Sessão expirada. Faça login novamente.');
                return false;
            }
            
            // Verificar tipo de usuário se especificado
            if (tipoRequerido) {
                // Admin pode acessar tudo
                if (sessaoObj.tipo === 'admin') {
                    return sessaoObj;
                }
                
                // Verificar se o tipo corresponde
                if (Array.isArray(tipoRequerido)) {
                    if (!tipoRequerido.includes(sessaoObj.tipo)) {
                        alert('Você não tem permissão para acessar esta área.');
                        this.redirecionarPorTipo(sessaoObj.tipo);
                        return false;
                    }
                } else if (sessaoObj.tipo !== tipoRequerido) {
                    alert('Você não tem permissão para acessar esta área.');
                    this.redirecionarPorTipo(sessaoObj.tipo);
                    return false;
                }
            }
            
            // Atualizar última atividade
            sessaoObj.ultimaAtividade = new Date().toISOString();
            sessionStorage.setItem('sessao_ativa', JSON.stringify(sessaoObj));
            
            return sessaoObj;
            
        } catch (error) {
            console.error('Erro ao verificar sessão:', error);
            this.logout();
            return false;
        }
    },
    
    // Obter dados do usuário atual
    obterUsuarioAtual: function() {
        const sessao = sessionStorage.getItem('sessao_ativa');
        if (sessao) {
            return JSON.parse(sessao);
        }
        return null;
    },
    
    // Alias para compatibilidade
    getUsuarioAtual: function() {
        return this.obterUsuarioAtual();
    },
    
    // Fazer logout
    logout: function(mensagem = null) {
        const usuario = this.getUsuarioAtual();
        
        if (usuario) {
            // Registrar logout
            this.registrarLog(usuario.usuarioId, 'logout', 'sucesso');
        }
        
        // Limpar sessão
        sessionStorage.removeItem('sessao_ativa');
        
        // Redirecionar para login
        if (mensagem) {
            alert(mensagem);
        }
        
        window.location.href = 'index.html';
    },
    
    // Redirecionar baseado no tipo de usuário
    redirecionarPorTipo: function(tipo) {
        switch(tipo) {
            case 'admin':
                window.location.href = 'sistema-gestao-corrigido2.html';
                break;
            case 'comprador':
                window.location.href = 'sistema-gestao-corrigido2.html';
                break;
            case 'fornecedor':
                window.location.href = 'dashboard-fornecedor.html';
                break;
            case 'auditor':
                window.location.href = 'dashboard-auditor.html';
                break;
            default:
                window.location.href = 'index.html';
        }
    },
    
    // Registrar log de atividade
    registrarLog: function(usuarioId, acao, detalhes) {
        const logs = JSON.parse(localStorage.getItem('logs_atividade') || '[]');
        
        logs.push({
            usuarioId: usuarioId,
            acao: acao,
            detalhes: detalhes,
            timestamp: new Date().toISOString(),
            pagina: window.location.pathname
        });
        
        // Manter apenas últimos 5000 logs
        if (logs.length > 5000) {
            logs.shift();
        }
        
        localStorage.setItem('logs_atividade', JSON.stringify(logs));
    },
    
    // Adicionar informações do usuário ao header
    exibirInfoUsuario: function(elementId = 'infoUsuario') {
        const usuario = this.getUsuarioAtual();
        const elemento = document.getElementById(elementId);
        
        if (usuario && elemento) {
            let tipoExibicao = usuario.tipo;
            if (usuario.tipo === 'comprador') {
                tipoExibicao = usuario.nivelAcesso || 'Comprador';
                tipoExibicao = tipoExibicao.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            }
            
            elemento.innerHTML = `
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span style="color: #fff; opacity: 0.8;">Olá,</span>
                    <strong style="color: #fff;">${usuario.nome}</strong>
                    <span style="color: #fff; opacity: 0.8;">|</span>
                    <span style="color: #fff; font-size: 12px; opacity: 0.8;">${tipoExibicao}</span>
                    <span style="color: #fff; opacity: 0.8;">|</span>
                    <button onclick="Auth.logout()" style="background: rgba(255,255,255,0.2); border: none; color: #fff; cursor: pointer; font-weight: 600; padding: 5px 15px; border-radius: 5px; transition: all 0.3s;">
                        🚪 Sair
                    </button>
                </div>
            `;
        }
    },
    
    // Verificar permissões específicas - ATUALIZADO COM NOVOS MÓDULOS
    temPermissao: function(permissao) {
        const usuario = this.getUsuarioAtual();
        if (!usuario) return false;
        
        // Admin tem todas as permissões
        if (usuario.tipo === 'admin') return true;
        
        const permissoes = {
            admin: [
                'criar_processo',
                'editar_processo',
                'deletar_processo',
                'ver_todos_processos',
                'ver_todas_propostas',
                'gerar_relatorios',
                'gerenciar_usuarios',
                'criar_compradores',
                'criar_tr',
                'requisitante',
                'comprador'
            ],
            comprador: [
                'criar_processo',
                'editar_proprio_processo',
                'deletar_proprio_processo',
                'ver_proprios_processos',
                'ver_propostas_proprios_processos',
                'gerar_relatorios_proprios_processos',
                'criar_tr',
                'comprador'
            ],
            comprador_senior: [
                'criar_processo',
                'editar_proprio_processo',
                'deletar_proprio_processo',
                'ver_todos_processos',
                'ver_propostas_proprios_processos',
                'gerar_relatorios',
                'criar_tr',
                'comprador'
            ],
            gerente: [
                'criar_processo',
                'editar_processo',
                'aprovar_processo',
                'ver_todos_processos',
                'ver_todas_propostas',
                'gerar_relatorios',
                'criar_tr',
                'requisitante',
                'comprador'
            ],
            requisitante: [
                'criar_tr',
                'requisitante',
                'ver_processos_ativos',
                'ver_propostas_tecnicas'
            ],
            fornecedor: [
                'ver_processos_ativos',
                'enviar_proposta',
                'ver_proprias_propostas',
                'editar_propria_proposta'
            ],
            auditor: [
                'ver_todos_processos',
                'ver_todas_propostas',
                'gerar_relatorios'
            ]
        };
        
        // Para compradores, usar o nível de acesso específico
        let tipoPermissao = usuario.tipo;
        if (usuario.tipo === 'comprador' && usuario.nivelAcesso) {
            tipoPermissao = usuario.nivelAcesso;
            
            // Adicionar permissões específicas para requisitante
            if (usuario.nivelAcesso === 'requisitante') {
                const permissoesRequisitante = permissoes.requisitante || [];
                return permissoesRequisitante.includes(permissao);
            }
        }
        
        const permissoesUsuario = permissoes[tipoPermissao] || [];
        return permissoesUsuario.includes(permissao);
    },
    
    // Filtrar dados baseado no tipo de usuário
    filtrarDadosPorPermissao: function(dados, tipo) {
        const usuario = this.getUsuarioAtual();
        if (!usuario) return [];
        
        switch(tipo) {
            case 'processos':
                // Admin e gerente veem todos
                if (usuario.tipo === 'admin' || usuario.nivelAcesso === 'gerente' || usuario.nivelAcesso === 'comprador_senior') {
                    return dados;
                }
                
                // Requisitante vê processos relacionados aos seus TRs
                if (usuario.nivelAcesso === 'requisitante') {
                    // Por enquanto, vê todos os processos ativos
                    const agora = new Date();
                    return dados.filter(p => new Date(p.prazo) > agora);
                }
                
                // Comprador vê apenas seus processos
                if (usuario.tipo === 'comprador') {
                    return dados.filter(p => p.criadoPor === usuario.usuarioId);
                }
                
                // Fornecedor só vê processos ativos
                if (usuario.tipo === 'fornecedor') {
                    const agora = new Date();
                    return dados.filter(p => new Date(p.prazo) > agora);
                }
                
                return dados;
                
            case 'propostas':
                // Admin, gerente e auditor veem todas
                if (usuario.tipo === 'admin' || usuario.nivelAcesso === 'gerente' || usuario.tipo === 'auditor') {
                    return dados;
                }
                
                // Requisitante vê apenas propostas técnicas (sem valores)
                if (usuario.nivelAcesso === 'requisitante') {
                    // Filtrar apenas informações técnicas
                    return dados.map(proposta => {
                        const propostaTecnica = {...proposta};
                        // Remover informações comerciais
                        delete propostaTecnica.valor;
                        delete propostaTecnica.comercial;
                        return propostaTecnica;
                    });
                }
                
                // Comprador vê apenas propostas dos seus processos
                if (usuario.tipo === 'comprador') {
                    // Primeiro, pegar os processos do comprador
                    const processos = JSON.parse(localStorage.getItem('processos') || '[]');
                    const meusProcessos = processos
                        .filter(p => p.criadoPor === usuario.usuarioId)
                        .map(p => p.numero);
                    
                    // Filtrar propostas
                    return dados.filter(proposta => meusProcessos.includes(proposta.processo));
                }
                
                // Fornecedor só vê suas próprias propostas
                if (usuario.tipo === 'fornecedor') {
                    return dados.filter(p => p.cnpj === usuario.cnpj);
                }
                
                return dados;
                
            default:
                return dados;
        }
    },
    
    // Verificar se pode editar processo
    podeEditarProcesso: function(processo) {
        const usuario = this.getUsuarioAtual();
        if (!usuario) return false;
        
        // Admin e gerente podem editar qualquer processo
        if (usuario.tipo === 'admin' || usuario.nivelAcesso === 'gerente') {
            return true;
        }
        
        // Comprador só pode editar seus próprios processos
        if (usuario.tipo === 'comprador' && processo.criadoPor === usuario.usuarioId) {
            return true;
        }
        
        return false;
    },
    
    // Proteger elementos da página baseado em permissões
    protegerElementos: function() {
        const usuario = this.getUsuarioAtual();
        if (!usuario) return;
        
        // Esconder elementos baseado em data-permissao
        document.querySelectorAll('[data-permissao]').forEach(elemento => {
            const permissaoRequerida = elemento.getAttribute('data-permissao');
            if (!this.temPermissao(permissaoRequerida)) {
                elemento.style.display = 'none';
            }
        });
        
        // Desabilitar inputs se usuário for auditor
        if (usuario.tipo === 'auditor') {
            document.querySelectorAll('input, textarea, select, button[type="submit"]').forEach(elemento => {
                elemento.disabled = true;
            });
        }
        
        // Para requisitantes, esconder valores comerciais
        if (usuario.nivelAcesso === 'requisitante') {
            document.querySelectorAll('[data-comercial="true"]').forEach(elemento => {
                elemento.style.display = 'none';
            });
        }
    }
};

// ========================================
// COMO USAR ESTE SISTEMA ATUALIZADO
// ========================================

// 1. Para páginas que admin e compradores podem acessar:
/*
window.addEventListener('DOMContentLoaded', function() {
    const usuario = Auth.verificarAutenticacao(['admin', 'comprador']);
    if (usuario) {
        Auth.exibirInfoUsuario();
        Auth.protegerElementos();
        
        // Filtrar dados baseado no usuário
        const processos = Auth.filtrarDadosPorPermissao(todosProcessos, 'processos');
        const propostas = Auth.filtrarDadosPorPermissao(todasPropostas, 'propostas');
    }
});
*/

// 2. Para verificar se pode editar um processo:
/*
if (Auth.podeEditarProcesso(processo)) {
    // Mostrar botões de edição
}
*/

// 3. Para criar processo com rastreamento de proprietário:
/*
const novoProcesso = {
    // ... outros campos ...
    criadoPor: usuario.usuarioId,
    criadoEm: new Date().toISOString()
};
*/

// 4. Para proteger elementos específicos na página:
/*
<button data-permissao="criar_processo">Novo Processo</button>
<div data-permissao="gerenciar_usuarios">Menu de Usuários</div>
<span data-comercial="true">R$ 1.000,00</span>
*/
