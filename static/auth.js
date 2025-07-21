// ========================================
// SISTEMA DE AUTENTICAÇÃO - ATUALIZADO PARA MULTI-COMPRADOR E NOVOS MÓDULOS
// Arquivo: auth.js
// VERSÃO: 2.0 - INCLUI SISTEMA DE NOTIFICAÇÕES
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
            
            // NOVO: Verificar notificações ao autenticar
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
            
            // NOVO: Adicionar badge de notificações
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
                    <!-- NOVO: Botão de notificações -->
                    <button onclick="Auth.Notificacoes.togglePainel()" class="btn-notificacoes" style="position: relative; background: rgba(255,255,255,0.2); border: none; color: #fff; cursor: pointer; font-weight: 600; padding: 5px 15px; border-radius: 5px; transition: all 0.3s;">
                        🔔 ${badgeNotificacoes}
                    </button>
                    <button onclick="Auth.logout()" style="background: rgba(255,255,255,0.2); border: none; color: #fff; cursor: pointer; font-weight: 600; padding: 5px 15px; border-radius: 5px; transition: all 0.3s;">
                        🚪 Sair
                    </button>
                </div>
            `;
            
            // NOVO: Adicionar estilos CSS para notificações (se ainda não existir)
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
                    
                    .notificacao-acao {
                        margin-top: 10px;
                    }
                    
                    .notificacao-acao button {
                        background: #3498db;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 12px;
                    }
                    
                    .notificacao-acao button:hover {
                        background: #2980b9;
                    }
                `;
                document.head.appendChild(style);
            }
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
    },
    
    // NOVO: Sistema de Notificações
    Notificacoes: {
        // Criar nova notificação
        criar: function(dados) {
            const notificacoes = JSON.parse(localStorage.getItem('notificacoes') || '[]');
            
            const novaNotificacao = {
                id: Date.now().toString(),
                tipo: dados.tipo || 'info', // novo_processo, proposta_recebida, prazo_proximo, etc
                titulo: dados.titulo,
                mensagem: dados.mensagem,
                destinatario: dados.destinatario, // usuarioId ou 'todos'
                destinatarioTipo: dados.destinatarioTipo, // fornecedor, comprador, etc
                remetente: dados.remetente || 'Sistema',
                lida: false,
                data: new Date().toISOString(),
                acao: dados.acao || null, // { texto: 'Ver Processo', link: '/processo/123' }
                processoId: dados.processoId || null,
                metadata: dados.metadata || {}
            };
            
            notificacoes.unshift(novaNotificacao);
            
            // Manter apenas últimas 100 notificações por usuário
            const usuario = Auth.getUsuarioAtual();
            if (usuario) {
                const minhasNotificacoes = notificacoes.filter(n => 
                    n.destinatario === usuario.usuarioId || 
                    n.destinatario === 'todos' ||
                    n.destinatarioTipo === usuario.tipo
                );
                if (minhasNotificacoes.length > 100) {
                    // Remover antigas
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
            
            // Atualizar badge se usuário estiver online
            Auth.Notificacoes.atualizarBadge();
        },
        
        // Obter notificações do usuário atual
        obterMinhas: function() {
            const usuario = Auth.getUsuarioAtual();
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
            const usuario = Auth.getUsuarioAtual();
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
                // Criar painel se não existir
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
                            ${notif.acao ? `
                                <div class="notificacao-acao">
                                    <button onclick="event.stopPropagation(); window.location.href='${notif.acao.link}'">
                                        ${notif.acao.texto}
                                    </button>
                                </div>
                            ` : ''}
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
            
            // Se tiver ação, executar
            const notificacoes = this.obterMinhas();
            const notif = notificacoes.find(n => n.id === notificacaoId);
            if (notif && notif.acao && notif.acao.link) {
                window.location.href = notif.acao.link;
            }
        },
        
        // Verificar novas notificações (mostrar alerta ao logar)
        verificarNovas: function() {
            const naoLidas = this.contarNaoLidas();
            if (naoLidas > 0) {
                // Mostrar alerta suave no canto da tela
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
                    <strong>🔔 Você tem ${naoLidas} notificação${naoLidas > 1 ? 'ões' : ''} não lida${naoLidas > 1 ? 's' : ''}</strong>
                `;
                alerta.onclick = () => {
                    this.togglePainel();
                    alerta.remove();
                };
                
                document.body.appendChild(alerta);
                
                // Remover após 5 segundos
                setTimeout(() => {
                    if (alerta.parentNode) {
                        alerta.style.animation = 'slideOut 0.5s ease';
                        setTimeout(() => alerta.remove(), 500);
                    }
                }, 5000);
                
                // Adicionar animação CSS se não existir
                if (!document.getElementById('notif-animations')) {
                    const style = document.createElement('style');
                    style.id = 'notif-animations';
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
            }
        },
        
        // NOVO: Notificações específicas para fornecedores
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
        
        // NOVO: Notificar comprador sobre nova proposta
        notificarNovaProposta: function(processoId, compradorId, dadosProposta) {
            this.criar({
                tipo: 'nova_proposta',
                titulo: '📨 Nova Proposta Recebida',
                mensagem: `${dadosProposta.fornecedor} enviou proposta para ${dadosProposta.processo}`,
                destinatario: compradorId,
                acao: {
                    texto: 'Ver Proposta',
                    link: `sistema-gestao-corrigido2.html#propostas/${processoId}`
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

// ========================================
// COMO USAR O SISTEMA DE NOTIFICAÇÕES
// ========================================

// 1. Para criar notificação quando fornecedor é convidado:
/*
// No sistema-gestao-corrigido2.html ao convidar fornecedor
Auth.Notificacoes.notificarNovoProcesso(
    processo.id,
    fornecedor.usuarioId,
    {
        titulo: processo.titulo,
        numero: processo.numero,
        prazo: processo.prazo,
        valor: processo.valor
    }
);
*/

// 2. Para notificar comprador sobre nova proposta:
/*
// No portal-propostas ao enviar proposta
Auth.Notificacoes.notificarNovaProposta(
    processo.id,
    processo.criadoPor,
    {
        fornecedor: fornecedor.razaoSocial,
        processo: processo.numero,
        cnpj: fornecedor.cnpj,
        valor: proposta.valor
    }
);
*/

// 3. Para notificação genérica:
/*
Auth.Notificacoes.criar({
    tipo: 'alerta',
    titulo: 'Prazo Próximo',
    mensagem: 'O processo LIC-2025-001 encerra em 2 dias',
    destinatario: usuario.usuarioId,
    acao: {
        texto: 'Ver Processo',
        link: 'dashboard.html#processo/123'
    }
});
*/

// 4. Para notificar todos os fornecedores:
/*
Auth.Notificacoes.criar({
    tipo: 'aviso',
    titulo: 'Manutenção Programada',
    mensagem: 'Sistema em manutenção dia 25/07 das 22h às 23h',
    destinatario: 'todos',
    destinatarioTipo: 'fornecedor'
});
*/

// ========================================
// EXEMPLO DE USO COMPLETO EM PÁGINA
// ========================================

/*
window.addEventListener('DOMContentLoaded', function() {
    const usuario = Auth.verificarAutenticacao(['admin', 'comprador']);
    if (usuario) {
        Auth.exibirInfoUsuario();
        Auth.protegerElementos();
        
        // Verificar e mostrar notificações
        Auth.Notificacoes.verificarNovas();
        
        // Atualizar badge periodicamente (opcional)
        setInterval(() => {
            Auth.Notificacoes.atualizarBadge();
        }, 30000); // A cada 30 segundos
    }
});
*/