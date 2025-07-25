// ===================================
// SISTEMA DE NOTIFICAÇÕES INTERNAS V2.0
// Substitui notificações por e-mail
// ===================================

const SistemaNotificacoes = {
    // Inicializar sistema
    init: function() {
        this.criarElementosUI();
        this.carregarNotificacoes();
        this.iniciarPolling();
        this.registrarEventos();
    },
    
    // Criar elementos de UI
    criarElementosUI: function() {
        // Badge no header
        const headerNotif = document.createElement('div');
        headerNotif.className = 'notificacao-badge-container';
        headerNotif.innerHTML = `
            <button class="btn-notificacoes" onclick="SistemaNotificacoes.togglePainel()">
                <span class="icon">🔔</span>
                <span class="badge-contador" id="notifCount">0</span>
            </button>
        `;
        
        // Inserir no header existente
        const header = document.querySelector('.header-content') || document.querySelector('.header');
        if (header) {
            header.appendChild(headerNotif);
        }
        
        // Painel de notificações
        const painel = document.createElement('div');
        painel.className = 'notificacao-painel';
        painel.id = 'notificacaoPainel';
        painel.innerHTML = `
            <div class="notificacao-header">
                <h3>Notificações</h3>
                <button class="btn-marcar-lidas" onclick="SistemaNotificacoes.marcarTodasLidas()">
                    Marcar todas como lidas
                </button>
            </div>
            <div class="notificacao-lista" id="notificacaoLista">
                <!-- Notificações serão inseridas aqui -->
            </div>
        `;
        document.body.appendChild(painel);
        
        // Estilos
        this.injetarEstilos();
    },
    
    // Injetar estilos CSS
    injetarEstilos: function() {
        const style = document.createElement('style');
        style.textContent = `
            /* Container do badge */
            .notificacao-badge-container {
                position: relative;
                margin-left: 20px;
            }
            
            /* Botão de notificações */
            .btn-notificacoes {
                background: rgba(255,255,255,0.2);
                border: none;
                padding: 8px 12px;
                border-radius: 8px;
                cursor: pointer;
                position: relative;
                color: white;
                font-size: 20px;
                transition: all 0.3s;
            }
            
            .btn-notificacoes:hover {
                background: rgba(255,255,255,0.3);
                transform: scale(1.05);
            }
            
            /* Badge contador */
            .badge-contador {
                position: absolute;
                top: -5px;
                right: -5px;
                background: #dc3545;
                color: white;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: bold;
                min-width: 18px;
                text-align: center;
                display: none;
            }
            
            .badge-contador.ativo {
                display: block;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }
            
            /* Painel de notificações */
            .notificacao-painel {
                position: fixed;
                top: 70px;
                right: 20px;
                width: 380px;
                max-height: 500px;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                display: none;
                z-index: 1000;
                overflow: hidden;
            }
            
            .notificacao-painel.ativo {
                display: block;
                animation: slideDown 0.3s ease-out;
            }
            
            @keyframes slideDown {
                from {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            /* Header do painel */
            .notificacao-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .notificacao-header h3 {
                margin: 0;
                font-size: 18px;
            }
            
            .btn-marcar-lidas {
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.3s;
            }
            
            .btn-marcar-lidas:hover {
                background: rgba(255,255,255,0.3);
            }
            
            /* Lista de notificações */
            .notificacao-lista {
                max-height: 400px;
                overflow-y: auto;
            }
            
            /* Item de notificação */
            .notificacao-item {
                padding: 15px 20px;
                border-bottom: 1px solid #f0f0f0;
                cursor: pointer;
                transition: all 0.3s;
                position: relative;
            }
            
            .notificacao-item:hover {
                background: #f8f9fa;
            }
            
            .notificacao-item.nao-lida {
                background: #e8f4f8;
                border-left: 4px solid #0ea5e9;
            }
            
            .notificacao-item .titulo {
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 5px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .notificacao-item .mensagem {
                color: #6c757d;
                font-size: 14px;
                margin-bottom: 5px;
            }
            
            .notificacao-item .tempo {
                color: #adb5bd;
                font-size: 12px;
            }
            
            .notificacao-item .acao {
		margin-top: 10px;
           }
           
           .notificacao-item .btn-acao {
               background: #667eea;
               color: white;
               border: none;
               padding: 6px 12px;
               border-radius: 5px;
               font-size: 13px;
               cursor: pointer;
               transition: all 0.3s;
           }
           
           .notificacao-item .btn-acao:hover {
               background: #5a67d8;
               transform: translateY(-1px);
           }
           
           /* Estado vazio */
           .notificacao-vazia {
               padding: 40px;
               text-align: center;
               color: #6c757d;
           }
           
           .notificacao-vazia img {
               width: 80px;
               opacity: 0.3;
               margin-bottom: 15px;
           }
           
           /* Tipos de notificação - ícones */
           .notif-icon {
               font-size: 20px;
               margin-right: 5px;
           }
           
           .notif-tipo-processo { color: #0ea5e9; }
           .notif-tipo-proposta { color: #10b981; }
           .notif-tipo-prazo { color: #f59e0b; }
           .notif-tipo-alerta { color: #ef4444; }
           .notif-tipo-sucesso { color: #22c55e; }
           
           /* Pop-up de nova notificação */
           .notificacao-popup {
               position: fixed;
               top: 20px;
               right: 20px;
               background: white;
               padding: 20px;
               border-radius: 10px;
               box-shadow: 0 10px 30px rgba(0,0,0,0.2);
               min-width: 300px;
               max-width: 400px;
               z-index: 2000;
               animation: slideInRight 0.5s ease-out;
               border-left: 4px solid #667eea;
           }
           
           @keyframes slideInRight {
               from {
                   transform: translateX(400px);
                   opacity: 0;
               }
               to {
                   transform: translateX(0);
                   opacity: 1;
               }
           }
           
           .notificacao-popup.saindo {
               animation: slideOutRight 0.5s ease-out;
           }
           
           @keyframes slideOutRight {
               from {
                   transform: translateX(0);
                   opacity: 1;
               }
               to {
                   transform: translateX(400px);
                   opacity: 0;
               }
           }
           
           /* Responsivo */
           @media (max-width: 768px) {
               .notificacao-painel {
                   width: calc(100% - 40px);
                   right: 20px;
                   left: 20px;
               }
               
               .notificacao-popup {
                   right: 10px;
                   left: 10px;
                   min-width: auto;
               }
           }
       `;
       document.head.appendChild(style);
   },
   
   // Carregar notificações do usuário
   carregarNotificacoes: function() {
       const usuario = this.obterUsuarioAtual();
       if (!usuario) return;
       
       const notificacoes = this.obterNotificacoesLocal(usuario.usuarioId);
       this.renderizarNotificacoes(notificacoes);
       this.atualizarBadge(notificacoes);
   },
   
   // Obter usuário atual
   obterUsuarioAtual: function() {
       const sessao = sessionStorage.getItem('sessao_ativa');
       return sessao ? JSON.parse(sessao) : null;
   },
   
   // Obter notificações do localStorage
   obterNotificacoesLocal: function(usuarioId) {
       const todasNotificacoes = JSON.parse(localStorage.getItem('notificacoes_sistema') || '[]');
       return todasNotificacoes
           .filter(n => n.destinatario === usuarioId)
           .sort((a, b) => new Date(b.data) - new Date(a.data));
   },
   
   // Salvar notificação
   salvarNotificacao: function(notificacao) {
       const notificacoes = JSON.parse(localStorage.getItem('notificacoes_sistema') || '[]');
       notificacoes.push(notificacao);
       localStorage.setItem('notificacoes_sistema', JSON.stringify(notificacoes));
   },
   
   // Criar nova notificação
   criarNotificacao: function(tipo, destinatario, titulo, mensagem, acao = null) {
       const notificacao = {
           id: 'notif_' + Date.now(),
           tipo: tipo,
           destinatario: destinatario,
           titulo: titulo,
           mensagem: mensagem,
           data: new Date().toISOString(),
           lida: false,
           acao: acao
       };
       
       this.salvarNotificacao(notificacao);
       
       // Se o destinatário está online, mostrar popup
       const usuarioAtual = this.obterUsuarioAtual();
       if (usuarioAtual && usuarioAtual.usuarioId === destinatario) {
           this.mostrarPopup(notificacao);
           this.carregarNotificacoes();
       }
       
       return notificacao;
   },
   
   // Renderizar lista de notificações
   renderizarNotificacoes: function(notificacoes) {
       const lista = document.getElementById('notificacaoLista');
       if (!lista) return;
       
       if (notificacoes.length === 0) {
           lista.innerHTML = `
               <div class="notificacao-vazia">
                   <div style="font-size: 48px; opacity: 0.3;">🔔</div>
                   <p>Nenhuma notificação</p>
               </div>
           `;
           return;
       }
       
       lista.innerHTML = notificacoes.map(notif => {
           const icon = this.obterIcone(notif.tipo);
           const tempo = this.formatarTempo(notif.data);
           
           return `
               <div class="notificacao-item ${notif.lida ? '' : 'nao-lida'}" 
                    onclick="SistemaNotificacoes.marcarComoLida('${notif.id}')">
                   <div class="titulo">
                       <span class="notif-icon notif-tipo-${notif.tipo}">${icon}</span>
                       ${notif.titulo}
                   </div>
                   <div class="mensagem">${notif.mensagem}</div>
                   <div class="tempo">${tempo}</div>
                   ${notif.acao ? `
                       <div class="acao">
                           <button class="btn-acao" onclick="SistemaNotificacoes.executarAcao('${notif.id}', event)">
                               ${notif.acao.texto}
                           </button>
                       </div>
                   ` : ''}
               </div>
           `;
       }).join('');
   },
   
   // Obter ícone por tipo
   obterIcone: function(tipo) {
       const icones = {
           'processo': '📋',
           'proposta': '📝',
           'prazo': '⏰',
           'alerta': '⚠️',
           'sucesso': '✅',
           'info': 'ℹ️'
       };
       return icones[tipo] || '🔔';
   },
   
   // Formatar tempo relativo
   formatarTempo: function(dataStr) {
       const data = new Date(dataStr);
       const agora = new Date();
       const diff = agora - data;
       
       const minutos = Math.floor(diff / 60000);
       const horas = Math.floor(diff / 3600000);
       const dias = Math.floor(diff / 86400000);
       
       if (minutos < 1) return 'Agora mesmo';
       if (minutos < 60) return `${minutos} min atrás`;
       if (horas < 24) return `${horas}h atrás`;
       if (dias < 7) return `${dias} dias atrás`;
       
       return data.toLocaleDateString('pt-BR');
   },
   
   // Atualizar badge
   atualizarBadge: function(notificacoes) {
       const naoLidas = notificacoes.filter(n => !n.lida).length;
       const badge = document.getElementById('notifCount');
       
       if (badge) {
           badge.textContent = naoLidas;
           badge.classList.toggle('ativo', naoLidas > 0);
       }
   },
   
   // Marcar como lida
   marcarComoLida: function(notifId) {
       const notificacoes = JSON.parse(localStorage.getItem('notificacoes_sistema') || '[]');
       const notif = notificacoes.find(n => n.id === notifId);
       
       if (notif && !notif.lida) {
           notif.lida = true;
           localStorage.setItem('notificacoes_sistema', JSON.stringify(notificacoes));
           this.carregarNotificacoes();
       }
   },
   
   // Marcar todas como lidas
   marcarTodasLidas: function() {
       const usuario = this.obterUsuarioAtual();
       if (!usuario) return;
       
       const notificacoes = JSON.parse(localStorage.getItem('notificacoes_sistema') || '[]');
       notificacoes.forEach(notif => {
           if (notif.destinatario === usuario.usuarioId) {
               notif.lida = true;
           }
       });
       
       localStorage.setItem('notificacoes_sistema', JSON.stringify(notificacoes));
       this.carregarNotificacoes();
   },
   
   // Toggle painel
   togglePainel: function() {
       const painel = document.getElementById('notificacaoPainel');
       if (painel) {
           painel.classList.toggle('ativo');
       }
   },
   
   // Executar ação da notificação
   executarAcao: function(notifId, event) {
       event.stopPropagation();
       
       const notificacoes = JSON.parse(localStorage.getItem('notificacoes_sistema') || '[]');
       const notif = notificacoes.find(n => n.id === notifId);
       
       if (notif && notif.acao && notif.acao.link) {
           window.location.href = notif.acao.link;
       }
   },
   
   // Mostrar popup de nova notificação
   mostrarPopup: function(notificacao) {
       const popup = document.createElement('div');
       popup.className = 'notificacao-popup';
       popup.innerHTML = `
           <div style="display: flex; justify-content: space-between; align-items: start;">
               <div style="flex: 1;">
                   <div style="font-weight: 600; margin-bottom: 5px;">
                       ${this.obterIcone(notificacao.tipo)} ${notificacao.titulo}
                   </div>
                   <div style="color: #6c757d; font-size: 14px;">
                       ${notificacao.mensagem}
                   </div>
               </div>
               <button onclick="this.parentElement.parentElement.classList.add('saindo'); setTimeout(() => this.parentElement.parentElement.remove(), 500)" 
                       style="background: none; border: none; font-size: 20px; cursor: pointer; color: #adb5bd;">
                   ×
               </button>
           </div>
           ${notificacao.acao ? `
               <button onclick="window.location.href='${notificacao.acao.link}'" 
                       style="margin-top: 10px; background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">
                   ${notificacao.acao.texto}
               </button>
           ` : ''}
       `;
       
       document.body.appendChild(popup);
       
       // Auto remover após 5 segundos
       setTimeout(() => {
           popup.classList.add('saindo');
           setTimeout(() => popup.remove(), 500);
       }, 5000);
   },
   
   // Polling para novas notificações (simular real-time)
   iniciarPolling: function() {
       // Verificar novas notificações a cada 30 segundos
       setInterval(() => {
           this.carregarNotificacoes();
       }, 30000);
   },
   
   // Registrar eventos globais
   registrarEventos: function() {
       // Fechar painel ao clicar fora
       document.addEventListener('click', (e) => {
           const painel = document.getElementById('notificacaoPainel');
           const btnNotif = document.querySelector('.btn-notificacoes');
           
           if (painel && painel.classList.contains('ativo')) {
               if (!painel.contains(e.target) && !btnNotif.contains(e.target)) {
                   painel.classList.remove('ativo');
               }
           }
       });
   },
   
   // ===== MÉTODOS ESPECÍFICOS PARA EVENTOS DO SISTEMA =====
   
   // Notificar novo processo
   notificarNovoProcesso: function(processo, fornecedoresIds) {
       fornecedoresIds.forEach(fornecedorId => {
           this.criarNotificacao(
               'processo',
               fornecedorId,
               `Novo Processo: ${processo.numero}`,
               `${processo.objeto} - Prazo: ${new Date(processo.prazo).toLocaleDateString('pt-BR')}`,
               {
                   texto: 'Ver Detalhes',
                   link: `/dashboard-fornecedor.html#processo/${processo.numero}`
               }
           );
       });
   },
   
   // Notificar prazo próximo
   notificarPrazoProximo: function(processo, fornecedorId) {
       this.criarNotificacao(
           'prazo',
           fornecedorId,
           `⏰ Prazo Próximo!`,
           `O processo ${processo.numero} vence em 3 dias. Envie sua proposta!`,
           {
               texto: 'Enviar Proposta',
               link: `/portal-propostas-novo.html?processo=${processo.numero}`
           }
       );
   },
   
   // Notificar proposta recebida (para comprador)
   notificarPropostaRecebida: function(proposta, compradorId) {
       this.criarNotificacao(
           'proposta',
           compradorId,
           `Nova Proposta Recebida`,
           `${proposta.empresa} enviou proposta para o processo ${proposta.processo}`,
           {
               texto: 'Analisar',
               link: `/sistema-gestao-corrigido2.html#propostas/${proposta.protocolo}`
           }
       );
   },
   
   // Notificar TR criado (para comprador)
   notificarTRCriado: function(tr, compradorId) {
       this.criarNotificacao(
           'processo',
           compradorId,
           `Novo TR para Análise`,
           `TR "${tr.titulo}" foi criado e aguarda sua análise`,
           {
               texto: 'Analisar TR',
               link: `/sistema-gestao-corrigido2.html#tr/${tr.id}`
           }
       );
   },
   
   // Notificar parecer técnico emitido
   notificarParecerEmitido: function(parecer, compradorId) {
       this.criarNotificacao(
           'info',
           compradorId,
           `Parecer Técnico Emitido`,
           `Parecer técnico para a proposta ${parecer.proposta} foi emitido`,
           {
               texto: 'Ver Parecer',
               link: `/sistema-gestao-corrigido2.html#parecer/${parecer.id}`
           }
       );
   }
};

// ===== INTEGRAÇÃO COM SISTEMA EXISTENTE =====

// Substituir chamadas de email por notificações
const IntegracaoNotificacoes = {
   // Ao criar processo e convidar fornecedores
   aoConvidarFornecedores: function(processo, fornecedoresIds) {
       // Ao invés de enviar email
       SistemaNotificacoes.notificarNovoProcesso(processo, fornecedoresIds);
   },
   
   // Ao receber proposta
   aoReceberProposta: function(proposta) {
       // Identificar compradores do processo
       const processo = this.obterProcesso(proposta.processo);
       if (processo && processo.criadoPor) {
           SistemaNotificacoes.notificarPropostaRecebida(proposta, processo.criadoPor);
       }
   },
   
   // Verificar prazos (executar diariamente)
   verificarPrazosProximos: function() {
       const processos = JSON.parse(localStorage.getItem('processos') || '[]');
       const agora = new Date();
       const tresDias = new Date();
       tresDias.setDate(tresDias.getDate() + 3);
       
       processos.forEach(processo => {
           const prazo = new Date(processo.prazo);
           
           if (prazo > agora && prazo <= tresDias) {
               // Buscar fornecedores convidados
               const fornecedores = this.obterFornecedoresProcesso(processo.numero);
               
               fornecedores.forEach(fornecedor => {
                   // Verificar se já tem proposta
                   if (!this.temProposta(fornecedor.id, processo.numero)) {
                       SistemaNotificacoes.notificarPrazoProximo(processo, fornecedor.id);
                   }
               });
           }
       });
   },
   
   // Métodos auxiliares
   obterProcesso: function(numeroProcesso) {
       const processos = JSON.parse(localStorage.getItem('processos') || '[]');
       return processos.find(p => p.numero === numeroProcesso);
   },
   
   obterFornecedoresProcesso: function(numeroProcesso) {
       // Buscar fornecedores convidados para o processo
       const convites = JSON.parse(localStorage.getItem('convites_processo') || '{}');
       return convites[numeroProcesso] || [];
   },
   
   temProposta: function(fornecedorId, numeroProcesso) {
       const propostas = JSON.parse(localStorage.getItem('propostas') || '[]');
       return propostas.some(p => 
           p.fornecedorId === fornecedorId && 
           p.processo === numeroProcesso
       );
   }
};

// Auto-inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
   document.addEventListener('DOMContentLoaded', () => {
       SistemaNotificacoes.init();
   });
} else {
   SistemaNotificacoes.init();
}

// Exportar para uso global
window.SistemaNotificacoes = SistemaNotificacoes;
window.IntegracaoNotificacoes = IntegracaoNotificacoes;