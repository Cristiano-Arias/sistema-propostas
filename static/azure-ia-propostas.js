/**
 * Azure IA - Análise Inteligente de Propostas
 * Módulo específico para análise das tabelas reais do portal de propostas
 */

class AzureIAPropostas {
    constructor() {
        this.azureEndpoint = null;
        this.azureKey = null;
        this.isConfigured = false;
        this.fallbackMode = true; // Modo simulado quando Azure não configurado
        
        // Tentar configurar automaticamente
        this.configuracaoAutomatica();
        this.init();
    }
    
    configuracaoAutomatica() {
        // Tentar usar configuração do AzureAI se disponível
        if (window.AzureAI && window.AzureAI.config) {
            const config = window.AzureAI.config;
            if (config.endpoint && config.apiKey) {
                this.azureEndpoint = config.endpoint;
                this.azureKey = config.apiKey;
                this.isConfigured = true;
                this.fallbackMode = false;
                console.log('✅ Azure IA configurado automaticamente via AzureAI');
                return true;
            }
        }
        
        // Configuração direta como fallback
        const endpoint = 'https://portalcompras.openai.azure.com';
        const key = '6Z0VYdgofYJMu32yWoaJfQtuocrVPKFi0sZhnBge7hluMgJXDVvuJQQJ99BHACYeBjFXJ3w3AAABACOGvaka';
        
        if (endpoint && key) {
            this.azureEndpoint = endpoint;
            this.azureKey = key;
            this.isConfigured = true;
            this.fallbackMode = false;
            console.log('✅ Azure IA configurado automaticamente com credenciais diretas');
            return true;
        }
        
        return false;
    }

    init() {
        this.checkAzureConfiguration();
    }

    checkAzureConfiguration() {
        // Se já foi configurado automaticamente, não fazer nada
        if (this.isConfigured) {
            console.log('Azure IA já está configurado e ativo');
            return;
        }
        
        // Verificar se Azure está configurado via window.azureConfig
        const azureConfig = window.azureConfig || {};
        
        if (azureConfig.endpoint && azureConfig.key) {
            this.azureEndpoint = azureConfig.endpoint;
            this.azureKey = azureConfig.key;
            this.isConfigured = true;
            this.fallbackMode = false;
            console.log('Azure IA configurado via azureConfig');
        } else {
            console.log('Azure IA não configurado - usando modo simulado');
            console.log('Use AzureIAPropostas.configurarAzure() para ativar');
            this.fallbackMode = true;
        }
    }

    async analisarPropostas(proposals, tabType = 'tecnica') {
        if (this.fallbackMode) {
            return this.analisarPropostasSimulado(proposals, tabType);
        }

        try {
            return await this.analisarPropostasAzure(proposals, tabType);
        } catch (error) {
            console.warn('Erro na análise Azure IA, usando modo simulado:', error);
            return this.analisarPropostasSimulado(proposals, tabType);
        }
    }

    async analisarPropostasAzure(proposals, tabType) {
        const analysisPrompt = this.buildAnalysisPrompt(proposals, tabType);
        
        // Garantir que não há barra dupla
        const endpoint = this.azureEndpoint.replace(/\/$/, ''); // Remove barra final se existir
        const deploymentName = window.AzureAI?.config?.deployment || 'gpt-35-turbo';
        const response = await fetch(`${endpoint}/openai/deployments/${deploymentName}/chat/completions?api-version=2024-08-01-preview`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'api-key': this.azureKey
            },
            body: JSON.stringify({
                messages: [
                    {
                        role: 'system',
                        content: 'Você é um especialista em análise de propostas licitatórias com foco em construção civil. Analise os dados fornecidos e forneça insights precisos e práticos.'
                    },
                    {
                        role: 'user',
                        content: analysisPrompt
                    }
                ],
                max_tokens: 1000,
                temperature: 0.3
            })
        });

        if (!response.ok) {
            throw new Error(`Azure API Error: ${response.status}`);
        }

        const data = await response.json();
        return this.parseAzureResponse(data.choices[0].message.content, tabType);
    }

    buildAnalysisPrompt(proposals, tabType) {
        let prompt = `Analise as seguintes propostas licitatórias para construção civil:\n\n`;

        proposals.forEach((proposal, index) => {
            prompt += `PROPOSTA ${index + 1}: ${proposal.dadosCadastrais?.razaoSocial || 'Empresa ' + (index + 1)}\n`;
            
            if (tabType === 'tecnica') {
                prompt += this.buildTechnicalPrompt(proposal);
            } else {
                prompt += this.buildCommercialPrompt(proposal);
            }
            
            prompt += '\n---\n\n';
        });

        if (tabType === 'tecnica') {
            prompt += `Forneça uma análise técnica focando em:
1. DESTAQUE PRINCIPAL: Qual proposta se destaca tecnicamente e por quê?
2. PONTOS DE ATENÇÃO: Riscos técnicos, prazos irreais, metodologias inadequadas
3. ANÁLISE DE MERCADO: Tendências tecnológicas e melhores práticas do setor

Responda em formato JSON:
{
  "highlight": "texto do destaque principal",
  "attention": "texto dos pontos de atenção", 
  "market": "texto da análise de mercado"
}`;
        } else {
            prompt += `Forneça uma análise comercial focando em:
1. DESTAQUE PRINCIPAL: Melhor custo-benefício, BDI equilibrado, preços competitivos
2. PONTOS DE ATENÇÃO: Valores muito altos/baixos, BDI suspeito, riscos financeiros
3. ANÁLISE DE MERCADO: Comparação com preços de mercado, tendências de custos

Responda em formato JSON:
{
  "highlight": "texto do destaque principal",
  "attention": "texto dos pontos de atenção",
  "market": "texto da análise de mercado"
}`;
        }

        return prompt;
    }

    buildTechnicalPrompt(proposal) {
        let prompt = '';
        
        // Dados técnicos
        if (proposal.propostaTecnica) {
            prompt += `Proposta Técnica:
- Metodologia: ${proposal.propostaTecnica.metodologia}
- Prazo: ${proposal.propostaTecnica.prazoExecucao}
- Garantias: ${proposal.propostaTecnica.garantias}
`;
        }

        // Serviços técnicos
        if (proposal.servicosTecnica) {
            prompt += `Serviços (${proposal.servicosTecnica.length} itens):
`;
            proposal.servicosTecnica.slice(0, 5).forEach(servico => {
                prompt += `- ${servico.descricao}: ${servico.quantidade} ${servico.unidade}\n`;
            });
        }

        // Mão de obra técnica
        if (proposal.maoObraTecnica) {
            prompt += `Mão de Obra (${proposal.maoObraTecnica.length} funções):
`;
            proposal.maoObraTecnica.slice(0, 5).forEach(func => {
                prompt += `- ${func.funcao}: ${func.quantidade} por ${func.tempo} meses\n`;
            });
        }

        return prompt;
    }

    buildCommercialPrompt(proposal) {
        let prompt = '';
        
        // Resumo financeiro
        if (proposal.resumoFinanceiro) {
            prompt += `Resumo Financeiro:
- Custo Direto: R$ ${proposal.resumoFinanceiro.custoDireto?.toLocaleString('pt-BR')}
- BDI: ${proposal.resumoFinanceiro.bdiPercentual}% (R$ ${proposal.resumoFinanceiro.bdiValor?.toLocaleString('pt-BR')})
- Valor Total: R$ ${proposal.resumoFinanceiro.valorTotal?.toLocaleString('pt-BR')}
`;
        }

        // BDI detalhado
        if (proposal.bdi) {
            prompt += `BDI Detalhado:
`;
            proposal.bdi.forEach(item => {
                prompt += `- ${item.item}: ${item.percentual}% (R$ ${item.valor?.toLocaleString('pt-BR')})\n`;
            });
        }

        // Serviços comerciais (amostra)
        if (proposal.servicosComercial) {
            prompt += `Serviços Comerciais (amostra):
`;
            proposal.servicosComercial.slice(0, 3).forEach(servico => {
                prompt += `- ${servico.descricao}: R$ ${servico.precoUnitario?.toLocaleString('pt-BR')}/${servico.unidade}\n`;
            });
        }

        return prompt;
    }

    parseAzureResponse(response, tabType) {
        try {
            // Tentar extrair JSON da resposta
            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }
        } catch (error) {
            console.warn('Erro ao parsear resposta Azure:', error);
        }

        // Fallback para resposta simulada
        return this.analisarPropostasSimulado([], tabType);
    }

    analisarPropostasSimulado(proposals, tabType) {
        if (tabType === 'tecnica') {
            return this.gerarAnaliseSimuladaTecnica(proposals);
        } else {
            return this.gerarAnaliseSimuladaComercial(proposals);
        }
    }

    gerarAnaliseSimuladaTecnica(proposals) {
        // Análise real baseada nos dados recebidos
        const analiseReal = this.analisarDadosReaisTecnicos(proposals);
        
        const insights = [
            {
                highlight: analiseReal.destaques,
                attention: analiseReal.divergencias,
                market: analiseReal.comparativo
            }
        ];
        
        return insights[0];
    }
    
    // Nova função para análise real
    analisarDadosReaisTecnicos(proposals) {
        if (!proposals || proposals.length === 0) {
            return {
                destaques: 'Aguardando propostas para análise.',
                divergencias: 'Nenhuma proposta disponível.',
                comparativo: 'Análise comparativa será exibida quando houver propostas.'
            };
        }
    
        // Análise de prazos reais
        const prazos = proposals.map(p => ({
            empresa: p.dadosCadastrais?.razaoSocial || 'Empresa',
            prazo: p.propostaTecnica?.prazoExecucao || 'Não informado'
        }));
        
        // Análise de metodologias
        const metodologias = proposals.map(p => ({
            empresa: p.dadosCadastrais?.razaoSocial,
            temMetodologia: !!p.propostaTecnica?.metodologia
        }));
    
        // Análise de serviços
        const quantidadeServicos = proposals.map(p => ({
            empresa: p.dadosCadastrais?.razaoSocial,
            totalServicos: p.servicosTecnica?.length || 0
        }));
    
        // Construir análise
        const menorPrazo = prazos.reduce((min, p) => p.prazo < min.prazo ? p : min);
        const maiorPrazo = prazos.reduce((max, p) => p.prazo > max.prazo ? p : max);
        
        const destaques = `${menorPrazo.empresa} oferece o menor prazo de execução (${menorPrazo.prazo}). ` +
                         `${quantidadeServicos[0].empresa} detalhou ${quantidadeServicos[0].totalServicos} serviços.`;
        
        const divergencias = `Variação de prazo entre propostas: ${menorPrazo.prazo} a ${maiorPrazo.prazo}. ` +
                            `${metodologias.filter(m => !m.temMetodologia).length} empresa(s) não detalharam metodologia.`;
        
        const comparativo = `Total de ${proposals.length} propostas analisadas. ` +
                           `Diferença de ${quantidadeServicos[0].totalServicos - quantidadeServicos[quantidadeServicos.length-1].totalServicos} itens entre propostas.`;
    
        return { destaques, divergencias, comparativo };
    }
            
    gerarAnaliseSimuladaComercial(proposals) {
        // Análise real baseada nos dados recebidos
        const analiseReal = this.analisarDadosReaisComerciais(proposals);
        
        return {
            highlight: analiseReal.destaques,
            attention: analiseReal.divergencias,
            market: analiseReal.comparativo
        };
    }
    
    // Nova função para análise comercial real
    analisarDadosReaisComerciais(proposals) {
        if (!proposals || proposals.length === 0) {
            return {
                destaques: 'Aguardando propostas comerciais.',
                divergencias: 'Nenhuma proposta disponível.',
                comparativo: 'Análise será exibida quando houver propostas.'
            };
        }
    
        // Extrair valores reais
        const valores = proposals.map(p => ({
            empresa: p.dadosCadastrais?.razaoSocial || 'Empresa',
            valor: p.resumoFinanceiro?.valorTotal || 0,
            bdi: p.resumoFinanceiro?.bdiPercentual || 0
        })).sort((a, b) => a.valor - b.valor);
    
        // Análise de BDI real
        const bdis = valores.map(v => v.bdi).filter(b => b > 0);
        const bdMin = Math.min(...bdis);
        const bdiMax = Math.max(...bdis);
    
        // Análise de serviços comerciais
        const servicosComerciais = proposals.map(p => ({
            empresa: p.dadosCadastrais?.razaoSocial,
            qtdServicos: p.servicosComercial?.length || 0,
            totalServicos: p.resumoFinanceiro?.totalServicos || 0
        }));
    
        // Calcular diferenças reais
        const menorValor = valores[0];
        const maiorValor = valores[valores.length - 1];
        const diferenca = ((maiorValor.valor - menorValor.valor) / menorValor.valor * 100).toFixed(1);
    
        const destaques = `${menorValor.empresa} apresenta o menor valor: ${this.formatarMoeda(menorValor.valor)}. ` +
                         `BDI varia de ${bdMin}% a ${bdiMax}% entre as propostas.`;
        
        const divergencias = `Diferença de ${diferenca}% entre maior e menor proposta. ` +
                            `${valores.filter(v => v.bdi < 20 || v.bdi > 30).length} empresa(s) com BDI fora da faixa 20-30%.`;
        
        const comparativo = `Valor médio das propostas: ${this.formatarMoeda(this.calcularMedia(valores.map(v => v.valor)))}. ` +
                           `${servicosComerciais[0].empresa} detalhou ${servicosComerciais[0].qtdServicos} serviços.`;
    
        return { destaques, divergencias, comparativo };
    }
    
    // Funções auxiliares
    formatarMoeda(valor) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }
    
    calcularMedia(valores) {
        return valores.reduce((a, b) => a + b, 0) / valores.length;
    }
            {
                highlight: 'Empresa B apresenta proposta mais econômica, mas BDI baixo (22%) pode indicar subdimensionamento de custos.',
                attention: 'Empresa C com valor muito alto pode estar superfaturada. Empresa A tem BDI dentro da média de mercado.',
                market: 'BDI médio do mercado está entre 25-30%. Valores abaixo de 20% são suspeitos, acima de 35% podem ser excessivos.'
            },
            {
                highlight: 'Empresa C justifica valor alto com tecnologia avançada e materiais sustentáveis, mas requer análise de ROI.',
                attention: 'Diferença de 47% entre menor e maior proposta é significativa. Empresa B pode ter omitido custos importantes.',
                market: 'Investimento em sustentabilidade pode gerar economia de 15-20% em operação, justificando custos iniciais maiores.'
            }
        ];

        const randomIndex = Math.floor(Math.random() * insights.length);
        return insights[randomIndex];
    }

    // Análises específicas por tabela
    async analisarTabelaServicos(proposals) {
        const servicos = this.extrairServicosUnicos(proposals);
        
        if (this.fallbackMode) {
            return {
                totalItens: servicos.length,
                maiorVariacao: this.calcularMaiorVariacao(proposals, 'servicosComercial'),
                recomendacao: 'Verificar itens com variação superior a 30% entre propostas'
            };
        }

        // Implementar análise Azure específica para serviços
        return await this.analisarTabelaAzure(proposals, 'servicos');
    }

    async analisarTabelaMaoObra(proposals) {
        const funcoes = this.extrairFuncoesUnicas(proposals);
        
        if (this.fallbackMode) {
            return {
                totalFuncoes: funcoes.length,
                custoMedioHora: this.calcularCustoMedioMaoObra(proposals),
                recomendacao: 'Atenção para encargos sociais muito baixos ou muito altos'
            };
        }

        return await this.analisarTabelaAzure(proposals, 'maoObra');
    }

    async analisarTabelaMateriais(proposals) {
        const materiais = this.extrairMateriaisUnicos(proposals);
        
        if (this.fallbackMode) {
            return {
                totalMateriais: materiais.length,
                variacao: 'Aço CA-50 com maior variação de preços entre propostas',
                recomendacao: 'Verificar especificações técnicas dos materiais'
            };
        }

        return await this.analisarTabelaAzure(proposals, 'materiais');
    }

    async analisarTabelaBDI(proposals) {
        const bdiMedio = this.calcularBDIMedio(proposals);
        
        if (this.fallbackMode) {
            return {
                bdiMedio: bdiMedio,
                faixaNormal: '25% - 30%',
                alertas: this.identificarBDISuspeitos(proposals)
            };
        }

        return await this.analisarTabelaAzure(proposals, 'bdi');
    }

    // Métodos auxiliares
    extrairServicosUnicos(proposals) {
        const servicos = new Set();
        proposals.forEach(proposal => {
            if (proposal.servicosComercial) {
                proposal.servicosComercial.forEach(servico => {
                    servicos.add(servico.descricao);
                });
            }
        });
        return Array.from(servicos);
    }

    extrairFuncoesUnicas(proposals) {
        const funcoes = new Set();
        proposals.forEach(proposal => {
            if (proposal.maoObraComercial) {
                proposal.maoObraComercial.forEach(func => {
                    funcoes.add(func.funcao);
                });
            }
        });
        return Array.from(funcoes);
    }

    extrairMateriaisUnicos(proposals) {
        const materiais = new Set();
        proposals.forEach(proposal => {
            if (proposal.materiaisComercial) {
                proposal.materiaisComercial.forEach(mat => {
                    materiais.add(mat.material);
                });
            }
        });
        return Array.from(materiais);
    }

    calcularBDIMedio(proposals) {
        let soma = 0;
        let count = 0;
        
        proposals.forEach(proposal => {
            if (proposal.resumoFinanceiro?.bdiPercentual) {
                soma += proposal.resumoFinanceiro.bdiPercentual;
                count++;
            }
        });
        
        return count > 0 ? (soma / count).toFixed(1) + '%' : 'N/A';
    }

    identificarBDISuspeitos(proposals) {
        const alertas = [];
        
        proposals.forEach((proposal, index) => {
            const bdi = proposal.resumoFinanceiro?.bdiPercentual;
            if (bdi) {
                if (bdi < 20) {
                    alertas.push(`Empresa ${index + 1}: BDI muito baixo (${bdi}%)`);
                } else if (bdi > 35) {
                    alertas.push(`Empresa ${index + 1}: BDI muito alto (${bdi}%)`);
                }
            }
        });
        
        return alertas;
    }

    calcularMaiorVariacao(proposals, tabela) {
        // Implementar cálculo de variação entre propostas
        return '35% em Concreto Estrutural';
    }

    calcularCustoMedioMaoObra(proposals) {
        // Implementar cálculo de custo médio
        return 'R$ 2.850/mês (com encargos)';
    }

    // Método para configurar Azure em runtime
    configurarAzure(endpoint, key) {
        // Validar e limpar endpoint
        if (!endpoint || !key) {
            console.error('❌ Endpoint e key são obrigatórios');
            return false;
        }
        
        // Remover barra final do endpoint
        this.azureEndpoint = endpoint.replace(/\/$/, '');
        this.azureKey = key;
        this.isConfigured = true;
        this.fallbackMode = false;
        
        console.log('✅ Azure IA configurado manualmente com sucesso');
        console.log('📍 Endpoint:', this.azureEndpoint);
        return true;
    }
    
    // Método para testar conexão Azure
    async testarConexao() {
        if (this.fallbackMode) {
            return { status: 'simulado', message: 'Modo simulado ativo' };
        }

    try {
            const endpoint = this.azureEndpoint.replace(/\/$/, '');
            const deploymentName = window.AzureAI?.config?.deployment || 'gpt-35-turbo';
            const url = `${endpoint}/openai/deployments/${deploymentName}/chat/completions?api-version=2024-08-01-preview`;
            console.log('🔗 Testando URL:', url);
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'api-key': this.azureKey
                },
                body: JSON.stringify({
                    messages: [{ role: 'user', content: 'teste' }],
                    max_tokens: 10
                })
            });

            if (response.ok) {
                return { status: 'conectado', message: 'Azure IA conectado com sucesso' };
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            return { status: 'erro', message: `Erro de conexão: ${error.message}` };
        }
    }

    // Método para obter estatísticas de uso
    obterEstatisticas() {
        return {
            modo: this.fallbackMode ? 'Simulado' : 'Azure IA',
            configurado: this.isConfigured,
            endpoint: this.azureEndpoint ? 'Configurado' : 'Não configurado',
            ultimaAnalise: new Date().toLocaleString('pt-BR')
        };
    }
}

// Exportar para uso global
window.AzureIAPropostas = AzureIAPropostas;

