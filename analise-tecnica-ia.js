// ===================================
// ANÁLISE TÉCNICA COM IA V2.0
// Para Requisitantes
// ===================================

const AnaliseTecnicaIA = {
    // Configurações da IA
    config: {
        scoreMinimo: 70,
        pesosAnalise: {
            metodologia: 0.30,
            equipe: 0.25,
            prazo: 0.20,
            experiencia: 0.15,
            certificacoes: 0.10
        }
    },
    
    // Inicializar módulo
    init: function() {
        this.injetarEstilos();
    },
    
    // Injetar estilos
    injetarEstilos: function() {
        const style = document.createElement('style');
        style.textContent = `
            .analise-ia-container {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
                margin: 20px 0;
            }
            
            .analise-ia-header {
                display: flex;
                align-items: center;
                gap: 15px;
                margin-bottom: 25px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e0e0e0;
            }
            
            .ia-icon {
                font-size: 48px;
                animation: float 3s ease-in-out infinite;
            }
            
            @keyframes float {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-10px); }
            }
            
            .analise-ia-titulo {
                flex: 1;
            }
            
            .analise-ia-titulo h3 {
                margin: 0;
                color: #2c3e50;
                font-size: 24px;
            }
            
            .analise-ia-titulo p {
                margin: 5px 0 0 0;
                color: #6c757d;
                font-size: 14px;
            }
            
            /* Score circular */
            .score-container {
                display: flex;
                gap: 30px;
                align-items: center;
                margin-bottom: 30px;
            }
            
            .score-circular {
                position: relative;
                width: 180px;
                height: 180px;
            }
            
            .score-svg {
                transform: rotate(-90deg);
            }
            
            .score-background {
                fill: none;
                stroke: #e0e0e0;
                stroke-width: 15;
            }
            
            .score-progress {
                fill: none;
                stroke-width: 15;
                stroke-linecap: round;
                transition: stroke-dashoffset 1s ease-in-out;
            }
            
            .score-text {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
            }
            
            .score-numero {
                font-size: 48px;
                font-weight: bold;
                color: #2c3e50;
            }
            
            .score-label {
                font-size: 14px;
                color: #6c757d;
            }
            
            /* Detalhes da análise */
            .analise-detalhes {
                flex: 1;
            }
            
            .criterio-item {
                background: #f8f9fa;
                padding: 15px 20px;
                border-radius: 10px;
                margin-bottom: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                transition: all 0.3s;
            }
            
            .criterio-item:hover {
                background: #e9ecef;
                transform: translateX(5px);
            }
            
            .criterio-info {
                display: flex;
                align-items: center;
                gap: 10px;
                flex: 1;
            }
            
            .criterio-icon {
                font-size: 24px;
            }
            
            .criterio-nome {
                font-weight: 600;
                color: #2c3e50;
            }
            
            .criterio-score {
                font-weight: bold;
                font-size: 18px;
                min-width: 50px;
                text-align: right;
            }
            
            .score-alto { color: #28a745; }
            .score-medio { color: #ffc107; }
            .score-baixo { color: #dc3545; }
            
            /* Alertas e sugestões */
            .alertas-container {
                margin-top: 30px;
            }
            
            .alerta-item {
                display: flex;
                align-items: start;
                gap: 15px;
                padding: 15px;
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 10px;
                margin-bottom: 10px;
            }
            
            .alerta-icon {
                font-size: 24px;
                color: #f39c12;
            }
            
            .alerta-content {
                flex: 1;
            }
            
            .alerta-titulo {
                font-weight: 600;
                color: #856404;
                margin-bottom: 5px;
            }
            
            .alerta-descricao {
                color: #856404;
                font-size: 14px;
            }
            
            /* Sugestões da IA */
            .sugestoes-container {
                background: #e3f2fd;
                border: 1px solid #90caf9;
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
            }
            
            .sugestoes-titulo {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 15px;
                color: #1565c0;
                font-weight: 600;
            }
            
            .sugestao-item {
                background: white;
                padding: 12px 15px;
                border-radius: 8px;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .sugestao-item:last-child {
                margin-bottom: 0;
            }
            
            /* Ações */
            .analise-acoes {
                display: flex;
                gap: 15px;
                margin-top: 30px;
                padding-top: 30px;
                border-top: 2px solid #e0e0e0;
            }
            
            .btn-ia {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .btn-aceitar {
                background: #28a745;
                color: white;
                flex: 1;
            }
            
            .btn-aceitar:hover {
                background: #218838;
                transform: translateY(-2px);
            }
            
            .btn-revisar {
                background: #6c757d;
                color: white;
                flex: 1;
            }
            
            .btn-revisar:hover {
                background: #5a6268;
                transform: translateY(-2px);
            }
            
            .btn-parecer {
                background: #007bff;
                color: white;
            }
            
            .btn-parecer:hover {
                background: #0056b3;
                transform: translateY(-2px);
            }
            
            /* Comparação lado a lado */
            .comparacao-container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 20px;
            }
            
            .comparacao-coluna {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
            }
            
            .comparacao-titulo {
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e0e0e0;
            }
            
            .comparacao-item {
                margin-bottom: 10px;
                padding: 8px;
                background: white;
                border-radius: 5px;
                font-size: 14px;
            }
            
            .match { background: #d4edda; }
            .no-match { background: #f8d7da; }
            .partial-match { background: #fff3cd; }
            
            /* Loading da análise */
            .analise-loading {
                text-align: center;
                padding: 60px;
            }
            
            .analise-loading-spinner {
                width: 60px;
                height: 60px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .analise-loading-text {
                color: #6c757d;
                font-size: 16px;
            }
            
            .analise-loading-steps {
                margin-top: 20px;
                text-align: left;
                display: inline-block;
            }
            
            .loading-step {
                color: #6c757d;
                margin: 5px 0;
                opacity: 0.5;
                transition: opacity 0.3s;
            }
            
            .loading-step.active {
                opacity: 1;
                color: #667eea;
                font-weight: 600;
            }
            
            .loading-step.completed {
                opacity: 1;
                color: #28a745;
            }
            
            .loading-step.completed::before {
                content: '✓ ';
            }
        `;
        document.head.appendChild(style);
    },
    
    // Analisar proposta técnica
    analisarProposta: async function(propostaTecnica, termoReferencia) {
        // Mostrar loading
        const container = document.createElement('div');
        container.className = 'analise-ia-container';
        container.innerHTML = this.renderizarLoading();
        
        // Adicionar ao DOM
        const targetElement = document.getElementById('analise-ia-resultado');
        if (targetElement) {
            targetElement.innerHTML = '';
            targetElement.appendChild(container);
        }
        
        // Simular etapas de análise
        await this.simularEtapasAnalise(container);
        
        // Executar análise
        const resultado = await this.executarAnalise(propostaTecnica, termoReferencia);
        
        // Renderizar resultado
        container.innerHTML = this.renderizarResultado(resultado, propostaTecnica, termoReferencia);
        
        return resultado;
    },
    
    // Simular etapas de análise
    simularEtapasAnalise: async function(container) {
        const etapas = [
            'Analisando metodologia proposta...',
            'Verificando qualificação da equipe...',
            'Comparando prazos de execução...',
            'Avaliando experiência anterior...',
            'Verificando certificações...',
            'Gerando score final...'
        ];
        
        for (let i = 0; i < etapas.length; i++) {
            await new Promise(resolve => setTimeout(resolve, 500));
            
            const steps = container.querySelectorAll('.loading-step');
            if (steps[i]) {
                steps[i].classList.add('active');
                
                if (i > 0) {
                    steps[i-1].classList.remove('active');
                    steps[i-1].classList.add('completed');
                }
            }
        }
        
        // Completar última etapa
        await new Promise(resolve => setTimeout(resolve, 500));
    },
    
    // Executar análise
    executarAnalise: async function(proposta, tr) {
        const analise = {
            scoreGeral: 0,
            criterios: {},
            alertas: [],
            sugestoes: [],
            timestamp: new Date().toISOString()
        };
        
        // 1. Analisar Metodologia
        analise.criterios.metodologia = this.analisarMetodologia(proposta.metodologia, tr.especificacoes);
        
        // 2. Analisar Equipe
        analise.criterios.equipe = this.analisarEquipe(proposta.equipe, tr.equipe_minima);
        
        // 3. Analisar Prazo
        analise.criterios.prazo = this.analisarPrazo(proposta.prazo, tr.prazo_maximo);
        
        // 4. Analisar Experiência
        analise.criterios.experiencia = this.analisarExperiencia(proposta.experiencia);
        
        // 5. Analisar Certificações
        analise.criterios.certificacoes = this.analisarCertificacoes(proposta.certificacoes);
        
        // Calcular score geral ponderado
        analise.scoreGeral = this.calcularScoreGeral(analise.criterios);
        
        // Gerar alertas
        analise.alertas = this.gerarAlertas(analise.criterios, proposta, tr);
        
        // Gerar sugestões
        analise.sugestoes = this.gerarSugestoes(analise);
        
        return analise;
    },
    
    // Analisar metodologia
    analisarMetodologia: function(metodologiaProposta, especificacoesTR) {
        // Simular análise de similaridade de texto
        const palavrasChave = this.extrairPalavrasChave(especificacoesTR);
        const palavrasEncontradas = palavrasChave.filter(palavra => 
            metodologiaProposta.toLowerCase().includes(palavra.toLowerCase())
        );
        
        const percentualCobertura = (palavrasEncontradas.length / palavrasChave.length) * 100;
        
        return {
            score: Math.round(percentualCobertura),
            detalhes: {
                palavrasChaveTotal: palavrasChave.length,
                palavrasEncontradas: palavrasEncontradas.length,
                cobertura: percentualCobertura
            }
        };
    },
    
    // Analisar equipe
    analisarEquipe: function(equipeProposta, equipeMinima) {
        if (!equipeProposta || equipeProposta.length === 0) {
            return { score: 0, detalhes: { status: 'Equipe não especificada' } };
        }
        
        // Verificar se atende requisitos mínimos
        let score = 80; // Base
        
        // Bonus por equipe maior
        if (equipeProposta.length > (equipeMinima?.length || 3)) {
            score += 10;
        }
        
        // Bonus por certificações da equipe
        const temCertificacao = equipeProposta.some(membro => 
            membro.certificacao || membro.crea || membro.cau
        );
        if (temCertificacao) {
            score += 10;
        }
        
        return {
            score: Math.min(score, 100),
            detalhes: {
                tamanhoEquipe: equipeProposta.length,
                certificada: temCertificacao
            }
        };
    },
    
    // Analisar prazo
    analisarPrazo: function(prazoProposta, prazoMaximo) {
        // Extrair números dos prazos
        const prazoPropostaNum = parseInt(prazoProposta) || 0;
        const prazoMaximoNum = parseInt(prazoMaximo) || 120;
        
        if (prazoPropostaNum <= prazoMaximoNum) {
            // Dentro do prazo
            const economia = ((prazoMaximoNum - prazoPropostaNum) / prazoMaximoNum) * 100;
            return {
                score: 90 + Math.min(economia / 10, 10), // Bonus por ser mais rápido
                detalhes: {
                    status: 'Dentro do prazo',
                    economia: `${economia.toFixed(1)}% mais rápido`
                }
            };
        } else {
            // Fora do prazo
            const excesso = ((prazoPropostaNum - prazoMaximoNum) / prazoMaximoNum) * 100;
            return {
                score: Math.max(70 - excesso, 0),
                detalhes: {
                    status: 'Acima do prazo',
                    excesso: `${excesso.toFixed(1)}% acima`
                }
            };
        }
    },
    
    // Analisar experiência
    analisarExperiencia: function(experiencias) {
        if (!experiencias || experiencias.length === 0) {
            return { score: 50, detalhes: { status: 'Sem experiências comprovadas' } };
        }
        
        let score = 70; // Base para ter experiência
        
        // Bonus por quantidade
        score += Math.min(experiencias.length * 5, 20);
        
        // Bonus por obras recentes
        const obrasRecentes = experiencias.filter(exp => {
            const ano = parseInt(exp.ano) || 0;
            return ano >= new Date().getFullYear() - 3;
        }).length;
        
        score += Math.min(obrasRecentes * 3, 10);
        
        return {
            score: Math.min(score, 100),
            detalhes: {
                totalObras: experiencias.length,
                obrasRecentes: obrasRecentes
            }
        };
    },
    
    // Analisar certificações
    analisarCertificacoes: function(certificacoes) {
        if (!certificacoes || certificacoes.length === 0) {
            return { score: 60, detalhes: { status: 'Sem certificações' } };
        }
        
        let score = 70;
        
        // Certificações importantes
        const certificacoesImportantes = ['ISO 9001', 'ISO 14001', 'PBQP-H'];
        const temImportantes = certificacoes.filter(cert => 
            certificacoesImportantes.some(imp => 
                cert.nome?.toUpperCase().includes(imp)
            )
        ).length;
        
        score += temImportantes * 10;
        
        return {
            score: Math.min(score, 100),
            detalhes: {
                total: certificacoes.length,
                importantes: temImportantes
            }
        };
    },
    
    // Calcular score geral
    calcularScoreGeral: function(criterios) {
        let scoreTotal = 0;
        let pesoTotal = 0;
        
        for (const [criterio, dados] of Object.entries(criterios)) {
            const peso = this.config.pesosAnalise[criterio] || 0.1;
            scoreTotal += dados.score * peso;
            pesoTotal += peso;
        }
        
        return Math.round(scoreTotal / pesoTotal);
    },
    
    // Gerar alertas
    gerarAlertas: function(criterios, proposta, tr) {
        const alertas = [];
        
        // Alertas por critério
        if (criterios.prazo.score < 80) {
            alertas.push({
                tipo: 'prazo',
                titulo: 'Prazo acima do esperado',
                descricao: `O prazo proposto está ${criterios.prazo.detalhes.excesso || '10%'} acima do máximo estabelecido no TR.`,
                severidade: 'media'
            });
        }
        
        if (criterios.metodologia.score < 70) {
            alertas.push({
                tipo: 'metodologia',
                titulo: 'Metodologia com baixa aderência',
                descricao: 'A metodologia proposta tem baixa correspondência com as especificações do TR.',
                severidade: 'alta'
            });
        }
        
        if (criterios.experiencia.score < 60) {
            alertas.push({
                tipo: 'experiencia',
                titulo: 'Experiência limitada',
                descricao: 'A empresa apresentou poucas obras similares ou experiência comprovada.',
                severidade: 'media'
            });
        }
        
        return alertas;
    },
    
    // Gerar sugestões
    gerarSugestoes: function(analise) {
        const sugestoes = [];
        
        if (analise.scoreGeral >= 85) {
            sugestoes.push('✅ Proposta técnica muito bem alinhada. Recomenda-se aprovação.');
            sugestoes.push('💡 Pequenos ajustes podem elevar ainda mais a qualidade.');
        } else if (analise.scoreGeral >= 70) {
            sugestoes.push('📋 Proposta aceitável. Considere solicitar esclarecimentos.');
            sugestoes.push('🔍 Revise os pontos críticos antes da aprovação final.');
        } else {
            sugestoes.push('⚠️ Proposta necessita melhorias significativas.');
            sugestoes.push('📝 Recomenda-se solicitar nova proposta ou diligências.');
        }
        
        // Sugestões específicas baseadas nos critérios
        for (const [criterio, dados] of Object.entries(analise.criterios)) {
            if (dados.score < 70) {
                switch(criterio) {
                    case 'metodologia':
                        sugestoes.push('📐 Solicite detalhamento da metodologia de execução.');
                        break;
                    case 'equipe':
                        sugestoes.push('👥 Verifique as qualificações profissionais da equipe.');
                        break;
                    case 'prazo':
                        sugestoes.push('⏱️ Negocie adequação do cronograma proposto.');
                        break;
                    case 'experiencia':
                        sugestoes.push('🏗️ Solicite comprovação adicional de experiência.');
                        break;
                    case 'certificacoes':
                        sugestoes.push('📜 Verifique validade das certificações apresentadas.');
                        break;
                }
            }
        }
        
        return sugestoes;
    },
    
    // Extrair palavras-chave
    extrairPalavrasChave: function(texto) {
        if (!texto) return [];
        
        // Palavras-chave comuns em especificações técnicas
        const palavrasImportantes = [
            'execução', 'qualidade', 'prazo', 'normas', 'segurança',
            'cronograma', 'fiscalização', 'material', 'mão de obra',
            'equipamento', 'técnica', 'NBR', 'ABNT', 'medição',
            'controle', 'inspeção', 'teste', 'ensaio', 'garantia'
        ];
        
        // Extrair palavras do texto
        const palavrasTexto = texto.toLowerCase()
            .split(/\s+/)
            .filter(palavra => palavra.length > 4);
        
        // Combinar com palavras importantes encontradas
        return palavrasImportantes.filter(palavra => 
            texto.toLowerCase().includes(palavra)
        );
    },
    
    // Renderizar loading
    renderizarLoading: function() {
        const etapas = [
            'Analisando metodologia proposta...',
            'Verificando qualificação da equipe...',
            'Comparando prazos de execução...',
            'Avaliando experiência anterior...',
            'Verificando certificações...',
            'Gerando score final...'
        ];
        
        return `
            <div class="analise-loading">
                <div class="analise-loading-spinner"></div>
                <div class="analise-loading-text">Analisando proposta técnica com IA...</div>
                <div class="analise-loading-steps">
                    ${etapas.map(etapa => 
                        `<div class="loading-step">${etapa}</div>`
                    ).join('')}
                </div>
            </div>
        `;
    },
    
    // Renderizar resultado
    renderizarResultado: function(resultado, proposta, tr) {
        const scoreClass = this.getScoreClass(resultado.scoreGeral);
        const scoreCor = this.getScoreCor(resultado.scoreGeral);
        
        return `
            <div class="analise-ia-header">
                <div class="ia-icon">🤖</div>
                <div class="analise-ia-titulo">
                    <h3>Análise Técnica com IA</h3>
                    <p>Avaliação automatizada da proposta técnica</p>
                </div>
            </div>
            
            <div class="score-container">
                ${this.renderizarScoreCircular(resultado.scoreGeral, scoreCor)}
                
                <div class="analise-detalhes">
                    ${this.renderizarCriterios(resultado.criterios)}
                </div>
            </div>
            
            ${resultado.alertas.length > 0 ? this.renderizarAlertas(resultado.alertas) : ''}
            
            ${this.renderizarSugestoes(resultado.sugestoes)}
            
            ${this.renderizarComparacao(proposta, tr)}
            
            <div class="analise-acoes">
                <button class="btn-ia btn-aceitar" onclick="AnaliseTecnicaIA.aceitarAnalise('${resultado.timestamp}')">
                    <span>✅</span> Aceitar Análise
                </button>
                <button class="btn-ia btn-revisar" onclick="AnaliseTecnicaIA.solicitarRevisao('${resultado.timestamp}')">
                    <span>👁️</span> Revisar Manualmente
                </button>
                <button class="btn-ia btn-parecer" onclick="AnaliseTecnicaIA.gerarParecer('${resultado.timestamp}')">
                    <span>📄</span> Gerar Parecer
                </button>
            </div>
        `;
    },
    
    // Renderizar score circular
    renderizarScoreCircular: function(score, cor) {
        const raio = 85;
        const circunferencia = 2 * Math.PI * raio;
        const offset = circunferencia - (score / 100) * circunferencia;
        
        return `
            <div class="score-circular">
                <svg class="score-svg" width="180" height="180">
                    <circle class="score-background" cx="90" cy="90" r="${raio}"/>
                    <circle class="score-progress" 
                            cx="90" cy="90" r="${raio}"
                            stroke="${cor}"
                            stroke-dasharray="${circunferencia}"
                            stroke-dashoffset="${offset}"/>
                </svg>
                <div class="score-text">
                    <div class="score-numero">${score}</div>
                    <div class="score-label">Score Geral</div>
                </div>
            </div>
        `;
    },
    
    // Renderizar critérios
    renderizarCriterios: function(criterios) {
        const icones = {
            metodologia: '📋',
            equipe: '👥',
            prazo: '⏱️',
            experiencia: '🏗️',
            certificacoes: '📜'
        };
        
        const nomes = {
            metodologia: 'Metodologia',
            equipe: 'Equipe Técnica',
            prazo: 'Prazo de Execução',
            experiencia: 'Experiência',
            certificacoes: 'Certificações'
        };
        
        return Object.entries(criterios).map(([key, dados]) => {
            const scoreClass = this.getScoreClass(dados.score);
            return `
                <div class="criterio-item">
                    <div class="criterio-info">
                        <span class="criterio-icon">${icones[key]}</span>
                        <span class="criterio-nome">${nomes[key]}</span>
                    </div>
                    <span class="criterio-score ${scoreClass}">${dados.score}%</span>
                </div>
            `;
        }).join('');
    },
    
    // Renderizar alertas
    renderizarAlertas: function(alertas) {
        return `
            <div class="alertas-container">
                <h4 style="color: #856404; margin-bottom: 15px;">⚠️ Pontos de Atenção</h4>
                ${alertas.map(alerta => `
                    <div class="alerta-item">
                        <div class="alerta-icon">⚠️</div>
                        <div class="alerta-content">
                            <div class="alerta-titulo">${alerta.titulo}</div>
                            <div class="alerta-descricao">${alerta.descricao}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    },
    
    // Renderizar sugestões
    renderizarSugestoes: function(sugestoes) {
        return `
            <div class="sugestoes-container">
                <div class="sugestoes-titulo">
                    <span>💡</span>
                    <span>Recomendações da IA</span>
                </div>
                ${sugestoes.map(sugestao => `
                    <div class="sugestao-item">${sugestao}</div>
                `).join('')}
            </div>
        `;
    },
    
    // Renderizar comparação
    renderizarComparacao: function(proposta, tr) {
        return `
            <div class="comparacao-container">
                <div class="comparacao-coluna">
                    <div class="comparacao-titulo">📋 Termo de Referência</div>
                    <div class="comparacao-item">Prazo: ${tr.prazo_maximo || '120 dias'}</div>
                    <div class="comparacao-item">Equipe mínima: ${tr.equipe_minima?.length || '3'} profissionais</div>
                    <div class="comparacao-item">Certificações: ${tr.certificacoes_obrigatorias || 'ISO 9001'}</div>
                </div>
                <div class="comparacao-coluna">
                    <div class="comparacao-titulo">📑 Proposta Técnica</div>
                    <div class="comparacao-item ${proposta.prazo <= tr.prazo_maximo ? 'match' : 'no-match'}">
                        Prazo: ${proposta.prazo || 'Não informado'}
                    </div>
                    <div class="comparacao-item ${proposta.equipe?.length >= (tr.equipe_minima?.length || 3) ? 'match' : 'no-match'}">
                        Equipe: ${proposta.equipe?.length || '0'} profissionais
                    </div>
                    <div class="comparacao-item ${proposta.certificacoes?.length > 0 ? 'match' : 'no-match'}">
                        Certificações: ${proposta.certificacoes?.length || '0'} apresentadas
                    </div>
                </div>
            </div>
        `;
    },
    
    // Helpers
    getScoreClass: function(score) {
        if (score >= 80) return 'score-alto';
        if (score >= 60) return 'score-medio';
        return 'score-baixo';
    },
    
    getScoreCor: function(score) {
        if (score >= 80) return '#28a745';
        if (score >= 60) return '#ffc107';
        return '#dc3545';
    },
    
    // Ações dos botões
    aceitarAnalise: function(timestamp) {
        alert(`Análise aceita! Timestamp: ${timestamp}\n\nA proposta será encaminhada para as próximas etapas.`);
        // Aqui você pode integrar com o sistema principal
    },
    
    solicitarRevisao: function(timestamp) {
        alert(`Revisão manual solicitada! Timestamp: ${timestamp}\n\nUm analista será designado para revisar a proposta.`);
        // Aqui você pode criar uma tarefa de revisão
    },
    
    gerarParecer: function(timestamp) {
        alert(`Gerando parecer técnico... Timestamp: ${timestamp}\n\nO documento será gerado em instantes.`);
        // Aqui você pode gerar um PDF ou documento do parecer
    },
    
    // Método auxiliar para integração
    analisarPropostaCompleta: function(dadosProposta) {
        // Estrutura esperada de dados
        const propostaTecnica = {
            metodologia: dadosProposta.metodologia || '',
            equipe: dadosProposta.equipe || [],
            prazo: dadosProposta.prazo || '',
            experiencia: dadosProposta.experiencia || [],
            certificacoes: dadosProposta.certificacoes || []
        };
        
        const termoReferencia = {
            especificacoes: dadosProposta.tr_especificacoes || '',
            equipe_minima: dadosProposta.tr_equipe_minima || [],
            prazo_maximo: dadosProposta.tr_prazo_maximo || '120 dias',
            certificacoes_obrigatorias: dadosProposta.tr_certificacoes || ''
        };
        
        return this.analisarProposta(propostaTecnica, termoReferencia);
    }
};

// Exemplo de uso
/*
// Dados de exemplo
const exemploPropostaTecnica = {
    metodologia: "Nossa metodologia segue as normas ABNT e NBR, com execução em fases, controle de qualidade rigoroso, inspeções periódicas e testes de materiais conforme especificações técnicas.",
    equipe: [
        { nome: "João Silva", funcao: "Engenheiro Civil", crea: "1234567" },
        { nome: "Maria Santos", funcao: "Arquiteta", cau: "A123456" },
        { nome: "Pedro Costa", funcao: "Técnico de Segurança", certificacao: "TST" }
    ],
    prazo: "90 dias",
    experiencia: [
        { obra: "Edifício Comercial XYZ", ano: "2023", valor: "R$ 5.000.000" },
        { obra: "Reforma Hospital ABC", ano: "2022", valor: "R$ 3.000.000" }
    ],
    certificacoes: [
        { nome: "ISO 9001:2015", validade: "2025" },
        { nome: "PBQP-H Nível A", validade: "2024" }
    ]
};

const exemploTermoReferencia = {
    especificacoes: "A execução deverá seguir rigorosamente as normas ABNT e NBR aplicáveis. É obrigatório o controle de qualidade dos materiais, com realização de testes e ensaios. A fiscalização será realizada semanalmente.",
    equipe_minima: [
        { funcao: "Engenheiro Civil" },
        { funcao: "Técnico de Segurança" }
    ],
    prazo_maximo: "120 dias"
};

// Inicializar e executar análise
AnaliseTecnicaIA.init();
AnaliseTecnicaIA.analisarProposta(exemploPropostaTecnica, exemploTermoReferencia);
*/