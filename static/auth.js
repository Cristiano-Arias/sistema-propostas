// ========================================
// SISTEMA DE AUTENTICAÇÃO - VERSÃO ATUALIZADA
// Arquivo: auth-atualizado.js
// VERSÃO: 3.0 - ESTRUTURA REVISADA E CONFIRMADA
// ========================================

const Auth = {
    // Verificar se usuário está autenticado
    verificarAutenticacao: function(tipoRequerido = null) {
        const sessao = sessionStorage.getItem('sessao_ativa');
        
        if (!sessao) {
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
                this.logout('Sessão expirada. Faça login novamente.');
                return false;
            }
            
            // Verificar tipo de usuário se especificado
            if (tipoRequerido) {
                // Admin pode acessar tudo
                if (sessaoObj.tipo === 'admin') {
                    return sessaoObj;
                }
                
                // Verificar permissões específicas
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
            
            // Verificar notificações
            this.Notificacoes.verificarNovas();
            
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
    
    // MÉTODO ADICIONADO PARA COMPATIBILIDADE
    getUsuarioLogado: function() {
        return this.obterUsuarioAtual();
    },
    
    // Fazer logout
    logout: function(mensagem = null) {
        const usuario = this.obterUsuarioAtual();
        
        if (usuario) {
            this.registrarLog(usuario.usuarioId, 'logout', 'sucesso');
        }
        
        sessionStorage.removeItem('sessao_ativa');
        
        if (mensagem) {
            alert(mensagem);
        }
        
        window.location.href = 'index.html';
    },
    
    // Redirecionar baseado no tipo de usuário
    redirecionarPorTipo: function(tipo) {
        switch(tipo) {
            case 'admin':
                window.location.href = 'sistema-gestao-atualizado.html';
                break;
            case 'comprador':
                window.location.href = 'sistema-gestao-atualizado.html';
                break;
            case 'requisitante':
                window.location.href = 'sistema-gestao-atualizado.html';
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
    
    // Exibir informações do usuário no header
    exibirInfoUsuario: function(elementId = 'infoUsuario') {
        const usuario = this.obterUsuarioAtual();
        const elemento = document.getElementById(elementId);
        
        if (usuario && elemento) {
            let tipoExibicao = this.formatarTipoUsuario(usuario.tipo);
            
            // Adicionar badge de notificações
            const notificacoesNaoLidas = this.Notificacoes.contarNaoLidas();
            const badgeNotificacoes = notificacoesNaoLidas > 0 
                ? `<span id="badge-notificacoes" class="badge-notificacoes">${notificacoesNaoLidas}</span>` 
                : '';
            
            elemento.innerHTML = `
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span style="color: #fff; opacity: 0.8;">Olá,</span>
                    <strong style="color: #fff;">${usuario.nome}</strong>
                    <span style="color: #fff; opacity: 0.8;">|</span>
                    <span style="color: #fff; font-size: 12px; opacity: 0.8;">${tipoExibicao}</span>
                    <span style="color: #fff; opacity: 0.8;">|</span>
                    <button onclick="Auth.Notificacoes.togglePainel()" class="btn-notificacoes" style="position: relative; background: rgba(255,255,255,0.2); border: none; color: #fff; cursor: pointer; font-weight: 600; padding: 5px 15px; border-radius: 5px; transition: all 0.3s;">
                        🔔 ${badgeNotificacoes}
                    </button>
                    <button onclick="Auth.logout()" style="background: rgba(255,255,255,0.2); border: none; color: #fff; cursor: pointer; font-weight: 600; padding: 5px 15px; border-radius: 5px; transition: all 0.3s;">
                        🚪 Sair
                    </button>
                </div>
            `;
            
            // Adicionar estilos CSS para notificações
            this.adicionarEstilosNotificacoes();
        }
    },
    
    // Formatar tipo de usuário para exibição
    formatarTipoUsuario: function(tipo) {
        const tipos = {
            'admin': 'Administrador',
            'comprador': 'Comprador',
            'requisitante': 'Requisitante',
            'fornecedor': 'Fornecedor',
            'auditor': 'Auditor'
        };
        return tipos[tipo] || tipo;
    },
    
    // Adicionar estilos CSS para notificações
    adicionarEstilosNotificacoes: function() {
        if (!document.getElementById('notificacoes-styles')) {
            const style = document.createElement('style');
            style.id = 'notificacoes-styles';
            style.innerHTML = `
                .badge-notificacoes {
                    position: absolute;
                    top: -5px;
                    right: -5px;
                    background: #ff4444;
                    color: white;
                    border-radius: 50%;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-weight: bold;
                    min-width: 18px;
                    text-align: center;
                }
                
                .btn-notificacoes {
                    position: relative !important;
                }
                
                .painel-notificacoes {
                    position: fixed;
                    top: 70px;
                    right: 20px;
                    width: 400px;
                    max-height: 500px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.2);
                    display: none;
                    z-index: 1000;
                    overflow: hidden;
                }
                
                .painel-notificacoes.ativo {
                    display: block;
                }
                
                .painel-notificacoes-header {
                    background: #2c3e50;
                    color: white;
                    padding: 15px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .painel-notificacoes-body {
                    max-height: 400px;
                    overflow-y: auto;
                }
                
                .notificacao-item {
                    padding: 15px;
                    border-bottom: 1px solid #eee;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                
                .notificacao-item:hover {
                    background: #f8f9fa;
                }
                
                .notificacao-item.nao-lida {
                    background: #e3f2fd;
                    border-left: 4px solid #2196f3;
                }
                
                .notificacao-titulo {
                    font-weight: bold;
                    margin-bottom: 5px;
                    color: #2c3e50;
                }
                
                .notificacao-mensagem {
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 5px;
                }
                
                .notificacao-data {
                    color: #999;
                    font-size: 12px;
                }
            `;
            document.head.appendChild(style);
        }
    },
    
    // Verificar permissões específicas
    temPermissao: function(permissao) {
        const usuario = this.obterUsuarioAtual();
        if (!usuario) return false;
        
        // Admin tem todas as permissões
        if (usuario.tipo === 'admin') return true;
        
        // Mapeamento de permissões por tipo de usuário
        const permissoes = {
            admin: [
                'dashboard_geral', 'dashboard_requisitante', 'criar_tr', 'meus_trs', 'emitir_parecer',
                'dashboard_comprador', 'processos', 'cadastrar_processos', 'propostas', 'relatorios',
                'dashboard_fornecedor', 'meu_cadastro', 'processos_disponiveis', 'minhas_propostas', 'enviar_proposta',
                'usuarios'
            ],
            comprador: [
                'dashboard_geral', 'dashboard_comprador', 'processos', 'cadastrar_processos', 'propostas', 'relatorios'
            ],
            requisitante: [
                'dashboard_geral', 'dashboard_requisitante', 'criar_tr', 'meus_trs', 'emitir_parecer'
            ],
            fornecedor: [
                'dashboard_fornecedor', 'meu_cadastro', 'processos_disponiveis', 'minhas_propostas', 'enviar_proposta'
            ],
            auditor: [
                'dashboard_geral', 'processos', 'propostas', 'relatorios'
            ]
        };
        
        const permissoesUsuario = permissoes[usuario.tipo] || [];
        return permissoesUsuario.includes(permissao);
    },
    
    // Sistema de Notificações
    Notificacoes: {
        // Criar nova notificação
        criar: function(dados) {
            const notificacoes = JSON.parse(localStorage.getItem('notificacoes') || '[]');
            
            const novaNotificacao = {
                id: Date.now().toString(),
                tipo: dados.tipo || 'info',
                titulo: dados.titulo,
                mensagem: dados.mensagem,
                destinatario: dados.destinatario,
                destinatarioTipo: dados.destinatarioTipo,
                remetente: dados.remetente || 'Sistema',
                lida: false,
                data: new Date().toISOString(),
                acao: dados.acao || null,
                processoId: dados.processoId || null,
                metadata: dados.metadata || {}
            };
            
            notificacoes.unshift(novaNotificacao);
            
            // Manter apenas últimas 100 notificações por usuário
            const usuario = Auth.obterUsuarioAtual();
            if (usuario) {
                const minhasNotificacoes = notificacoes.filter(n => 
                    n.destinatario === usuario.usuarioId || 
                    n.destinatario === 'todos' ||
                    n.destinatarioTipo === usuario.tipo
                );
                if (minhasNotificacoes.length > 100) {
                    const idsParaManter = minhasNotificacoes.slice(0, 100).map(n => n.id);
                    const notificacoesFiltradas = notificacoes.filter(n => 
                        idsParaManter.includes(n.id) || 
                        (n.destinatario !== usuario.usuarioId && n.destinatario !== 'todos' && n.destinatarioTipo !== usuario.tipo)
                    );
                    localStorage.setItem('notificacoes', JSON.stringify(notificacoesFiltradas));
                    return;
                }
            }
            
            localStorage.setItem('notificacoes', JSON.stringify(notificacoes));
            Auth.Notificacoes.atualizarBadge();
        },
        
        // Obter notificações do usuário atual
        obterMinhas: function() {
            const usuario = Auth.obterUsuarioAtual();
            if (!usuario) return [];
            
            const todas = JSON.parse(localStorage.getItem('notificacoes') || '[]');
            
            return todas.filter(n => 
                n.destinatario === usuario.usuarioId || 
                n.destinatario === 'todos' ||
                n.destinatarioTipo === usuario.tipo
            ).sort((a, b) => new Date(b.data) - new Date(a.data));
        },
        
        // Contar não lidas
        contarNaoLidas: function() {
            return this.obterMinhas().filter(n => !n.lida).length;
        },
        
        // Marcar como lida
        marcarComoLida: function(notificacaoId) {
            const notificacoes = JSON.parse(localStorage.getItem('notificacoes') || '[]');
            const index = notificacoes.findIndex(n => n.id === notificacaoId);
            
            if (index !== -1) {
                notificacoes[index].lida = true;
                localStorage.setItem('notificacoes', JSON.stringify(notificacoes));
                this.atualizarBadge();
                this.atualizarPainel();
            }
        },
        
        // Marcar todas como lidas
        marcarTodasComoLidas: function() {
            const usuario = Auth.obterUsuarioAtual();
            if (!usuario) return;
            
            const notificacoes = JSON.parse(localStorage.getItem('notificacoes') || '[]');
            
            notificacoes.forEach(n => {
                if (n.destinatario === usuario.usuarioId || 
                    n.destinatario === 'todos' ||
                    n.destinatarioTipo === usuario.tipo) {
                    n.lida = true;
                }
            });
            
            localStorage.setItem('notificacoes', JSON.stringify(notificacoes));
            this.atualizarBadge();
            this.atualizarPainel();
        },
        
        // Atualizar badge
        atualizarBadge: function() {
            const badge = document.getElementById('badge-notificacoes');
            if (badge) {
                const count = this.contarNaoLidas();
                if (count > 0) {
                    badge.textContent = count > 99 ? '99+' : count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            }
        },
        
        // Toggle painel de notificações
        togglePainel: function() {
            let painel = document.getElementById('painel-notificacoes');
            
            if (!painel) {
                painel = document.createElement('div');
                painel.id = 'painel-notificacoes';
                painel.className = 'painel-notificacoes';
                document.body.appendChild(painel);
                
                // Fechar ao clicar fora
                document.addEventListener('click', function(e) {
                    if (!e.target.closest('.btn-notificacoes') && 
                        !e.target.closest('.painel-notificacoes')) {
                        painel.classList.remove('ativo');
                    }
                });
            }
            
            if (painel.classList.contains('ativo')) {
                painel.classList.remove('ativo');
            } else {
                this.atualizarPainel();
                painel.classList.add('ativo');
            }
        },
        
        // Atualizar conteúdo do painel
        atualizarPainel: function() {
            const painel = document.getElementById('painel-notificacoes');
            if (!painel) return;
            
            const notificacoes = this.obterMinhas();
            
            let html = `
                <div class="painel-notificacoes-header">
                    <h3 style="margin: 0;">🔔 Notificações</h3>
                    ${notificacoes.filter(n => !n.lida).length > 0 ? 
                        `<button onclick="Auth.Notificacoes.marcarTodasComoLidas()" 
                         style="background: none; border: 1px solid white; color: white; 
                         padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px;">
                         Marcar todas como lidas
                         </button>` : ''}
                </div>
                <div class="painel-notificacoes-body">
            `;
            
            if (notificacoes.length === 0) {
                html += `
                    <div style="padding: 30px; text-align: center; color: #999;">
                        <p>Nenhuma notificação no momento</p>
                    </div>
                `;
            } else {
                notificacoes.forEach(notif => {
                    const dataFormatada = new Date(notif.data).toLocaleString('pt-BR');
                    html += `
                        <div class="notificacao-item ${notif.lida ? '' : 'nao-lida'}" 
                             onclick="Auth.Notificacoes.clicarNotificacao('${notif.id}')">
                            <div class="notificacao-titulo">${notif.titulo}</div>
                            <div class="notificacao-mensagem">${notif.mensagem}</div>
                            <div class="notificacao-data">${dataFormatada}</div>
                        </div>
                    `;
                });
            }
            
            html += '</div>';
            painel.innerHTML = html;
        },
        
        // Clicar em notificação
        clicarNotificacao: function(notificacaoId) {
            this.marcarComoLida(notificacaoId);
            
            const notificacoes = this.obterMinhas();
            const notif = notificacoes.find(n => n.id === notificacaoId);
            if (notif && notif.acao && notif.acao.link) {
                window.location.href = notif.acao.link;
            }
        },
        
        // Verificar novas notificações
        verificarNovas: function() {
            const naoLidas = this.contarNaoLidas();
            this.atualizarBadge();
            
            // Mostrar alerta apenas se houver muitas notificações não lidas
            if (naoLidas > 5) {
                this.mostrarAlertaNotificacoes(naoLidas);
            }
        },
        
        // Mostrar alerta de notificações
        mostrarAlertaNotificacoes: function(count) {
            const alerta = document.createElement('div');
            alerta.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #3498db;
                color: white;
                padding: 15px 20px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                cursor: pointer;
                z-index: 1000;
                animation: slideIn 0.5s ease;
            `;
            alerta.innerHTML = `
                <strong>🔔 Você tem ${count} notificações não lidas</strong>
            `;
            alerta.onclick = () => {
                this.togglePainel();
                alerta.remove();
            };
            
            document.body.appendChild(alerta);
            
            // Remover após 5 segundos
            setTimeout(() => {
                if (alerta.parentNode) {
                    alerta.remove();
                }
            }, 5000);
        },
        
        // Notificar novo processo para fornecedores
        notificarNovoProcesso: function(processoId, fornecedorId, dadosProcesso) {
            this.criar({
                tipo: 'novo_processo',
                titulo: '📋 Novo Processo Disponível',
                mensagem: `${dadosProcesso.titulo} - Prazo: ${dadosProcesso.prazo}`,
                destinatario: fornecedorId,
                destinatarioTipo: 'fornecedor',
                acao: {
                    texto: 'Ver Detalhes',
                    link: `dashboard-fornecedor.html#processo/${processoId}`
                },
                processoId: processoId,
                metadata: {
                    numeroProcesso: dadosProcesso.numero,
                    valor: dadosProcesso.valor
                }
            });
        },
        
        // Notificar comprador sobre nova proposta
        notificarNovaProposta: function(processoId, compradorId, dadosProposta) {
            this.criar({
                tipo: 'nova_proposta',
                titulo: '📨 Nova Proposta Recebida',
                mensagem: `${dadosProposta.fornecedor} enviou proposta para ${dadosProposta.processo}`,
                destinatario: compradorId,
                acao: {
                    texto: 'Ver Proposta',
                    link: `sistema-gestao-atualizado.html#propostas`
                },
                processoId: processoId,
                metadata: {
                    fornecedorCNPJ: dadosProposta.cnpj,
                    valor: dadosProposta.valor
                }
            });
        }
    }
};

// Adicionar animações CSS
if (!document.getElementById('auth-animations')) {
    const style = document.createElement('style');
    style.id = 'auth-animations';
    style.innerHTML = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// Exportar para compatibilidade
window.Auth = Auth;
