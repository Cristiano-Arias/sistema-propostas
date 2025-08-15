// azure-config.js
const AzureAI = {
    // Configurações
    config: {
        endpoint: 'https://portalcompras.openai.azure.com',
        apiKey: '6Z0VYdgofYJMu32yWoaJfQtuocrVPKFi0sZhnBge7hluMgJXDVvuJQQJ99BHACYeBjFXJ3w3AAABACOGvaka',
        deployment: 'gpt-35-turbo',
        apiVersion: '2024-08-01-preview'
    },

    // Inicializar configuração do localStorage
    init() {
        const savedConfig = localStorage.getItem('azure_ai_config');
        if (savedConfig) {
            this.config = JSON.parse(savedConfig);
            return true;
        }
        return false;
    },

    // Salvar configuração
    saveConfig(endpoint, apiKey, deployment) {
        this.config.endpoint = endpoint;
        this.config.apiKey = apiKey;
        this.config.deployment = deployment || 'gpt-4';
        localStorage.setItem('azure_ai_config', JSON.stringify(this.config));
    },

    // Testar conexão
    async testConnection() {
        if (!this.config.endpoint || !this.config.apiKey) {
            throw new Error('Configuração Azure AI incompleta');
        }

        try {
            const response = await fetch(`${this.config.endpoint}openai/deployments/${this.config.deployment}/chat/completions?api-version=${this.config.apiVersion}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'api-key': this.config.apiKey
                },
                body: JSON.stringify({
                    messages: [{
                        role: 'user',
                        content: 'Teste de conexão'
                    }],
                    max_tokens: 10
                })
            });

            return response.ok;
        } catch (error) {
            console.error('Erro ao testar conexão:', error);
            return false;
        }
    },

    // Analisar propostas com IA
    async analisarPropostas(propostas, processo) {
        if (!this.config.endpoint || !this.config.apiKey) {
            throw new Error('Configure o Azure AI primeiro');
        }

        const prompt = this.construirPrompt(propostas, processo);

        try {
            const response = await fetch(`${this.config.endpoint}openai/deployments/${this.config.deployment}/chat/completions?api-version=${this.config.apiVersion}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'api-key': this.config.apiKey
                },
                body: JSON.stringify({
                    messages: [
                        {
                            role: 'system',
                            content: `Você é um especialista em licitações públicas brasileiras. 
                                     Analise propostas considerando: economicidade, legalidade, 
                                     vantajosidade e conformidade com o TR. 
                                     Forneça análises objetivas e recomendações fundamentadas.`
                        },
                        {
                            role: 'user',
                            content: prompt
                        }
                    ],
                    max_tokens: 2000,
                    temperature: 0.3
                })
            });

            if (!response.ok) {
                throw new Error(`Erro API: ${response.status}`);
            }

            const data = await response.json();
            return this.processarResposta(data.choices[0].message.content, propostas);

        } catch (error) {
            console.error('Erro na análise AI:', error);
            // Fallback para análise local
            return this.analiseLocal(propostas, processo);
        }
    },

    // Construir prompt para análise
    construirPrompt(propostas, processo) {
        return `
Analise as seguintes propostas para o processo licitatório:

DADOS DO PROCESSO:
- Número: ${processo.numeroProcesso}
- TR: ${processo.trVinculado?.titulo || 'N/A'}
- Valor Estimado: R$ ${parseFloat(processo.trVinculado?.valorEstimado || 0).toLocaleString('pt-BR')}
- Modalidade: ${processo.modalidade}

PROPOSTAS RECEBIDAS:
${propostas.map((p, i) => `
${i + 1}. ${p.fornecedor.razaoSocial} (CNPJ: ${p.fornecedor.cnpj})
   - Valor: R$ ${parseFloat(p.propostaComercial?.valorTotal || p.valor || 0).toLocaleString('pt-BR')}
   - Prazo: ${p.propostaTecnica?.prazoExecucao || p.prazoExecucao || 'N/A'}
   - Experiência: ${p.propostaTecnica?.experiencia || 'Não informado'}
   - Metodologia: ${p.propostaTecnica?.metodologia || 'Não informado'}
   - Condições Pagamento: ${p.propostaComercial?.condicoesPagamento || '30 dias'}
`).join('\n')}

Por favor, forneça:
1. ANÁLISE COMERCIAL: Compare valores, identifique economicidade e riscos de inexequibilidade
2. ANÁLISE TÉCNICA: Avalie capacidade técnica, prazos e metodologias
3. CONFORMIDADE: Verifique aderência ao TR
4. RISCOS: Identifique riscos em cada proposta
5. PONTUAÇÃO: Atribua nota de 0-100 para cada proposta
6. RECOMENDAÇÃO: Indique a melhor proposta com justificativa

Formato da resposta: JSON estruturado.`;
    },

    // Processar resposta da IA
    processarResposta(respostaTexto, propostas) {
        try {
            // Tentar extrair JSON da resposta
            const jsonMatch = respostaTexto.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0]);
            }

            // Se não encontrar JSON, processar texto
            return {
                analiseComercial: this.extrairSecao(respostaTexto, 'ANÁLISE COMERCIAL'),
                analiseTecnica: this.extrairSecao(respostaTexto, 'ANÁLISE TÉCNICA'),
                conformidade: this.extrairSecao(respostaTexto, 'CONFORMIDADE'),
                riscos: this.extrairRiscos(respostaTexto),
                pontuacoes: this.extrairPontuacoes(respostaTexto, propostas),
                recomendacao: this.extrairSecao(respostaTexto, 'RECOMENDAÇÃO'),
                timestamp: new Date().toISOString()
            };

        } catch (error) {
            console.error('Erro ao processar resposta:', error);
            return this.analiseLocal(propostas);
        }
    },

    // Extrair seção do texto
    extrairSecao(texto, titulo) {
        const regex = new RegExp(`${titulo}[:\s]*([^\\n]+(?:\\n(?![A-Z]+:)[^\\n]+)*)`, 'i');
        const match = texto.match(regex);
        return match ? match[1].trim() : '';
    },

    // Extrair riscos
    extrairRiscos(texto) {
        const secaoRiscos = this.extrairSecao(texto, 'RISCOS');
        const riscos = {};
        
        // Tentar extrair riscos por fornecedor
        const linhas = secaoRiscos.split('\n');
        linhas.forEach(linha => {
            const match = linha.match(/(\d+)\.\s*([^:]+):\s*(.+)/);
            if (match) {
                riscos[`fornecedor_${match[1]}`] = match[3].trim();
            }
        });

        return riscos;
    },

    // Extrair pontuações
    extrairPontuacoes(texto, propostas) {
        const pontuacoes = {};
        
        propostas.forEach((proposta, index) => {
            const regex = new RegExp(`${index + 1}[^\\d]*(\\d+)\\s*pontos`, 'i');
            const match = texto.match(regex);
            pontuacoes[proposta.id] = match ? parseInt(match[1]) : 0;
        });

        return pontuacoes;
    },

    // Análise local (fallback)
    analiseLocal(propostas, processo) {
        const analise = {
            timestamp: new Date().toISOString(),
            tipo: 'local',
            propostas: []
        };

        // Análise automática local
        propostas.forEach(proposta => {
            const valor = parseFloat(proposta.propostaComercial?.valorTotal || proposta.valor || 0);
            const valorEstimado = parseFloat(processo?.trVinculado?.valorEstimado || 1);
            const percentual = (valor / valorEstimado) * 100;

            let pontuacao = 0;
            let riscos = [];

            // Análise de preço
            if (percentual <= 70) {
                riscos.push('Preço muito baixo - verificar exequibilidade');
                pontuacao += 20;
            } else if (percentual <= 90) {
                pontuacao += 40;
            } else if (percentual <= 100) {
                pontuacao += 30;
            } else if (percentual <= 110) {
                pontuacao += 20;
            } else {
                riscos.push('Preço acima do estimado');
                pontuacao += 10;
            }

            // Análise técnica
            if (proposta.propostaTecnica?.experiencia) pontuacao += 20;
            if (proposta.propostaTecnica?.metodologia) pontuacao += 20;
            if (proposta.propostaTecnica?.equipeTecnica) pontuacao += 20;

            analise.propostas.push({
                id: proposta.id,
                fornecedor: proposta.fornecedor.razaoSocial,
                pontuacao: pontuacao,
                riscos: riscos,
                recomendado: false
            });
        });

        // Definir recomendação
        analise.propostas.sort((a, b) => b.pontuacao - a.pontuacao);
        if (analise.propostas.length > 0) {
            analise.propostas[0].recomendado = true;
        }

        analise.recomendacao = `Recomenda-se ${analise.propostas[0]?.fornecedor || 'N/A'} 
                                com pontuação de ${analise.propostas[0]?.pontuacao || 0} pontos.`;

        return analise;
    }
};


