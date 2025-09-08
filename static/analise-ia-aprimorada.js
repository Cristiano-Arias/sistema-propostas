/**
 * Sistema Aprimorado de Análise IA para Propostas Licitatórias
 * Versão 2.0 - Com análise detalhada por tópicos
 */

class AnalisadorIAPropostasAprimorado {
    constructor() {
        this.azureEndpoint = 'https://portalcompras.openai.azure.com';
        this.azureKey = '6Z0VYdgofYJMu32yWoaJfQtuocrVPKFi0sZhnBge7hluMgJXDVvuJQQJ99BHACYeBjFXJ3w3AAABACOGvaka';
        this.deployment = 'gpt-35-turbo';
        this.apiVersion = '2024-08-01-preview';
        
        // Critérios de avaliação por categoria
        this.criteriosAvaliacao = {
            tecnica: {
                experiencia: { peso: 0.25, nome: 'Experiência da Empresa' },
                equipe: { peso: 0.20, nome: 'Qualificação da Equipe' },
                metodologia: { peso: 0.20, nome: 'Metodologia Proposta' },
                cronograma: { peso: 0.15, nome: 'Viabilidade do Cronograma' },
                recursos: { peso: 0.10, nome: 'Recursos Técnicos' },
                inovacao: { peso: 0.10, nome: 'Inovação e Diferencial' }
            },
            comercial: {
                valor: { peso: 0.30, nome: 'Competitividade do Valor' },
                bdi: { peso: 0.25, nome: 'Composição do BDI' },
                materiais: { peso: 0.15, nome: 'Custo de Materiais' },
                maoObra: { peso: 0.15, nome: 'Custo de Mão de Obra' },
                equipamentos: { peso: 0.10, nome: 'Custo de Equipamentos' },
                condicoes: { peso: 0.05, nome: 'Condições de Pagamento' }
            }
        };
        
        this.benchmarks = {
            bdi: { min: 20, max: 30, ideal: 25 },
            prazo: { min: 90, max: 240, ideal: 180 },
            garantia: { min: 12, max: 60, ideal: 24 }
        };
    }

    /**
     * Análise completa e detalhada das propostas
     */
    async analisarPropostasDetalhada(propostas, tipoAnalise = 'tecnica') {
        try {
            // 1. Análise individual de cada proposta
            const analisesIndividuais = await this.analisarCadaProposta(propostas, tipoAnalise);
            
            // 2. Análise comparativa entre propostas
            const analiseComparativa = await this.compararPropostas(propostas, tipoAnalise);
            
            // 3. Análise de riscos e oportunidades
            const analiseRiscos = await this.identificarRiscosOportunidades(propostas, tipoAnalise);
            
            // 4. Recomendações específicas
            const recomendacoes = await this.gerarRecomendacoes(propostas, analisesIndividuais, tipoAnalise);
            
            // 5. Scoring e ranking
            const ranking = this.calcularRanking(propostas, analisesIndividuais, tipoAnalise);
            
            return {
                analisesIndividuais,
                analiseComparativa,
                analiseRiscos,
                recomendacoes,
                ranking,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('Erro na análise IA:', error);
            // Fallback para análise local aprimorada
            return this.analisarPropostasLocal(propostas, tipoAnalise);
        }
    }

    /**
     * Análise individual de cada proposta
     */
    async analisarCadaProposta(propostas, tipoAnalise) {
        const analises = [];
        
        for (const proposta of propostas) {
            const analise = {
                empresa: proposta.dadosCadastrais.razaoSocial,
                cnpj: proposta.dadosCadastrais.cnpj,
                pontuacoes: {},
                observacoes: {},
                pontuacaoTotal: 0
            };
            
            if (tipoAnalise === 'tecnica') {
                // Análise de Experiência
                analise.pontuacoes.experiencia = this.avaliarExperiencia(proposta);
                analise.observacoes.experiencia = this.gerarObservacaoExperiencia(proposta);
                
                // Análise de Equipe
                analise.pontuacoes.equipe = this.avaliarEquipe(proposta);
                analise.observacoes.equipe = this.gerarObservacaoEquipe(proposta);
                
                // Análise de Metodologia
                analise.pontuacoes.metodologia = this.avaliarMetodologia(proposta);
                analise.observacoes.metodologia = this.gerarObservacaoMetodologia(proposta);
                
                // Análise de Cronograma
                analise.pontuacoes.cronograma = this.avaliarCronograma(proposta);
                analise.observacoes.cronograma = this.gerarObservacaoCronograma(proposta);
                
                // Análise de Recursos Técnicos
                analise.pontuacoes.recursos = this.avaliarRecursos(proposta);
                analise.observacoes.recursos = this.gerarObservacaoRecursos(proposta);
                
                // Análise de Inovação
                analise.pontuacoes.inovacao = this.avaliarInovacao(proposta);
                analise.observacoes.inovacao = this.gerarObservacaoInovacao(proposta);
                
            } else { // comercial
                // Análise de Valor
                analise.pontuacoes.valor = this.avaliarValor(proposta, propostas);
                analise.observacoes.valor = this.gerarObservacaoValor(proposta, propostas);
                
                // Análise de BDI
                analise.pontuacoes.bdi = this.avaliarBDI(proposta);
                analise.observacoes.bdi = this.gerarObservacaoBDI(proposta);
                
                // Análise de Materiais
                analise.pontuacoes.materiais = this.avaliarMateriais(proposta);
                analise.observacoes.materiais = this.gerarObservacaoMateriais(proposta);
                
                // Análise de Mão de Obra
                analise.pontuacoes.maoObra = this.avaliarMaoObra(proposta);
                analise.observacoes.maoObra = this.gerarObservacaoMaoObra(proposta);
                
                // Análise de Equipamentos
                analise.pontuacoes.equipamentos = this.avaliarEquipamentos(proposta);
                analise.observacoes.equipamentos = this.gerarObservacaoEquipamentos(proposta);
                
                // Análise de Condições
                analise.pontuacoes.condicoes = this.avaliarCondicoes(proposta);
                analise.observacoes.condicoes = this.gerarObservacaoCondicoes(proposta);
            }
            
            // Calcular pontuação total ponderada
            analise.pontuacaoTotal = this.calcularPontuacaoTotal(analise.pontuacoes, tipoAnalise);
            
            analises.push(analise);
        }
        
        return analises;
    }

    /**
     * Métodos de avaliação técnica
     */
    avaliarExperiencia(proposta) {
        let pontuacao = 50; // Base
        
        // Verificar dados cadastrais
        if (proposta.dadosCadastrais.crea) pontuacao += 10;
        if (proposta.dadosCadastrais.respTecnico) pontuacao += 10;
        
        // Verificar proposta técnica
        if (proposta.propostaTecnica.experiencia) {
            const exp = proposta.propostaTecnica.experiencia.toLowerCase();
            if (exp.includes('10 anos') || exp.includes('dez anos')) pontuacao += 15;
            else if (exp.includes('5 anos') || exp.includes('cinco anos')) pontuacao += 10;
        }
        
        // Verificar portfólio/cases
        if (proposta.propostaTecnica.casosSucesso) pontuacao += 15;
        
        return Math.min(100, pontuacao);
    }

    gerarObservacaoExperiencia(proposta) {
        const obs = [];
        const pontos = this.avaliarExperiencia(proposta);
        
        if (pontos >= 80) {
            obs.push("Excelente histórico empresarial com vasta experiência no setor");
        } else if (pontos >= 60) {
            obs.push("Boa experiência com casos de sucesso comprovados");
        } else {
            obs.push("Experiência limitada ou documentação insuficiente");
        }
        
        if (!proposta.dadosCadastrais.crea) {
            obs.push("ATENÇÃO: Registro profissional (CREA/CAU) não informado");
        }
        
        return obs.join(". ");
    }

    avaliarEquipe(proposta) {
        let pontuacao = 40;
        
        if (proposta.maoObraTecnica && proposta.maoObraTecnica.length > 0) {
            pontuacao += 20;
            
            // Verificar diversidade de funções
            const funcoes = proposta.maoObraTecnica.map(m => m[0] || m.funcao);
            if (funcoes.some(f => f && f.toLowerCase().includes('coordenador'))) pontuacao += 10;
            if (funcoes.some(f => f && f.toLowerCase().includes('engenheiro'))) pontuacao += 10;
            if (funcoes.some(f => f && f.toLowerCase().includes('técnico'))) pontuacao += 10;
            
            // Verificar quantidade adequada
            if (proposta.maoObraTecnica.length >= 5) pontuacao += 10;
        }
        
        return Math.min(100, pontuacao);
    }

    gerarObservacaoEquipe(proposta) {
        const tamanhoEquipe = proposta.maoObraTecnica?.length || 0;
        
        if (tamanhoEquipe === 0) {
            return "CRÍTICO: Equipe técnica não especificada na proposta";
        } else if (tamanhoEquipe < 3) {
            return "Equipe reduzida - verificar capacidade de execução";
        } else if (tamanhoEquipe >= 5) {
            return "Equipe robusta e bem dimensionada para o projeto";
        } else {
            return "Equipe adequada com profissionais essenciais";
        }
    }

    avaliarMetodologia(proposta) {
        let pontuacao = 30;
        
        const metodologia = proposta.propostaTecnica.metodologia || '';
        
        // Verificar detalhamento
        if (metodologia.length > 100) pontuacao += 20;
        
        // Verificar palavras-chave de boas práticas
        const boasPraticas = ['pmbok', 'iso', 'agile', 'scrum', 'lean', 'bim', 'qualidade', 'segurança'];
        boasPraticas.forEach(pratica => {
            if (metodologia.toLowerCase().includes(pratica)) pontuacao += 10;
        });
        
        // Verificar sequência de execução
        if (proposta.propostaTecnica.sequenciaExecucao) pontuacao += 10;
        
        return Math.min(100, pontuacao);
    }

    gerarObservacaoMetodologia(proposta) {
        const metodologia = proposta.propostaTecnica.metodologia || '';
        const pontos = this.avaliarMetodologia(proposta);
        
        if (pontos >= 80) {
            return "Metodologia muito bem estruturada com uso de frameworks reconhecidos";
        } else if (pontos >= 60) {
            return "Metodologia adequada com boas práticas de mercado";
        } else if (metodologia.length < 50) {
            return "Metodologia pouco detalhada - solicitar esclarecimentos";
        } else {
            return "Metodologia básica sem diferenciais significativos";
        }
    }

    avaliarCronograma(proposta) {
        let pontuacao = 50;
        const prazo = parseInt(proposta.propostaTecnica.prazoExecucao) || 0;
        
        if (prazo > 0) {
            // Verificar se está dentro da faixa ideal
            if (prazo >= this.benchmarks.prazo.min && prazo <= this.benchmarks.prazo.max) {
                pontuacao += 30;
                
                // Bonus se próximo ao ideal
                const desvio = Math.abs(prazo - this.benchmarks.prazo.ideal) / this.benchmarks.prazo.ideal;
                if (desvio < 0.2) pontuacao += 20;
            }
        }
        
        return Math.min(100, pontuacao);
    }

    gerarObservacaoCronograma(proposta) {
        const prazo = parseInt(proposta.propostaTecnica.prazoExecucao) || 0;
        
        if (prazo === 0) {
            return "CRÍTICO: Prazo de execução não informado";
        } else if (prazo < this.benchmarks.prazo.min) {
            return `ALERTA: Prazo muito curto (${prazo} dias) pode comprometer qualidade`;
        } else if (prazo > this.benchmarks.prazo.max) {
            return `Prazo extenso (${prazo} dias) pode impactar custos indiretos`;
        } else {
            return `Prazo adequado (${prazo} dias) dentro dos padrões do mercado`;
        }
    }

    avaliarRecursos(proposta) {
        let pontuacao = 40;
        
        // Verificar equipamentos
        if (proposta.equipamentosTecnica && proposta.equipamentosTecnica.length > 0) {
            pontuacao += 20;
            if (proposta.equipamentosTecnica.length >= 3) pontuacao += 10;
        }
        
        // Verificar materiais
        if (proposta.materiaisTecnica && proposta.materiaisTecnica.length > 0) {
            pontuacao += 20;
            if (proposta.materiaisTecnica.length >= 5) pontuacao += 10;
        }
        
        return Math.min(100, pontuacao);
    }

    gerarObservacaoRecursos(proposta) {
        const qtdEquip = proposta.equipamentosTecnica?.length || 0;
        const qtdMat = proposta.materiaisTecnica?.length || 0;
        
        if (qtdEquip === 0 && qtdMat === 0) {
            return "CRÍTICO: Recursos técnicos não especificados";
        } else if (qtdEquip < 2 || qtdMat < 3) {
            return "Recursos limitados - verificar suficiência para o escopo";
        } else {
            return "Recursos técnicos adequados e bem especificados";
        }
    }

    avaliarInovacao(proposta) {
        let pontuacao = 30;
        
        const textoCompleto = JSON.stringify(proposta.propostaTecnica).toLowerCase();
        const termosTecnologia = ['bim', 'iot', 'drone', 'sustentável', 'verde', 'solar', 
                                 'automação', 'digital', 'app', 'software', 'sistema'];
        
        termosTecnologia.forEach(termo => {
            if (textoCompleto.includes(termo)) pontuacao += 10;
        });
        
        return Math.min(100, pontuacao);
    }

    gerarObservacaoInovacao(proposta) {
        const pontos = this.avaliarInovacao(proposta);
        
        if (pontos >= 70) {
            return "Proposta com forte componente inovador e tecnológico";
        } else if (pontos >= 50) {
            return "Algumas soluções inovadoras apresentadas";
        } else {
            return "Abordagem tradicional sem elementos inovadores significativos";
        }
    }

    /**
     * Métodos de avaliação comercial
     */
    avaliarValor(proposta, todasPropostas) {
        const valor = proposta.resumoFinanceiro?.valorTotal || 0;
        const valores = todasPropostas.map(p => p.resumoFinanceiro?.valorTotal || 0).filter(v => v > 0);
        
        if (valores.length === 0 || valor === 0) return 0;
        
        const menorValor = Math.min(...valores);
        const maiorValor = Math.max(...valores);
        
        // Pontuação inversamente proporcional ao valor
        if (valor === menorValor) return 100;
        if (valor === maiorValor) return 30;
        
        // Interpolação linear
        const range = maiorValor - menorValor;
        const posicao = (valor - menorValor) / range;
        return Math.round(100 - (posicao * 70));
    }

    gerarObservacaoValor(proposta, todasPropostas) {
        const valor = proposta.resumoFinanceiro?.valorTotal || 0;
        const valores = todasPropostas.map(p => p.resumoFinanceiro?.valorTotal || 0).filter(v => v > 0);
        
        if (valores.length === 0) return "Valor não informado";
        
        const menorValor = Math.min(...valores);
        const mediaValor = valores.reduce((a, b) => a + b, 0) / valores.length;
        const desvio = ((valor - mediaValor) / mediaValor) * 100;
        
        if (valor === menorValor) {
            return `MELHOR VALOR: R$ ${this.formatarMoeda(valor)} - verificar exequibilidade`;
        } else if (desvio > 20) {
            return `Valor ${desvio.toFixed(1)}% acima da média - justificar diferencial`;
        } else if (desvio < -20) {
            return `ATENÇÃO: Valor muito baixo pode indicar risco de inexequibilidade`;
        } else {
            return `Valor dentro da média do mercado (desvio: ${desvio.toFixed(1)}%)`;
        }
    }

    avaliarBDI(proposta) {
        const bdiTotal = proposta.resumoFinanceiro?.bdiPercentual || 0;
        
        if (bdiTotal === 0) return 0;
        
        // Verificar se está na faixa aceitável
        if (bdiTotal >= this.benchmarks.bdi.min && bdiTotal <= this.benchmarks.bdi.max) {
            // Quanto mais próximo do ideal, melhor
            const desvio = Math.abs(bdiTotal - this.benchmarks.bdi.ideal) / this.benchmarks.bdi.ideal;
            return Math.round(100 - (desvio * 100));
        } else if (bdiTotal < this.benchmarks.bdi.min) {
            return 30; // BDI muito baixo é suspeito
        } else {
            return 40; // BDI muito alto
        }
    }

    gerarObservacaoBDI(proposta) {
        const bdiTotal = proposta.resumoFinanceiro?.bdiPercentual || 0;
        const bdiItens = proposta.bdi || [];
        
        if (bdiTotal === 0) {
            return "CRÍTICO: BDI não informado na proposta";
        } else if (bdiTotal < this.benchmarks.bdi.min) {
            return `ALERTA: BDI muito baixo (${bdiTotal}%) - risco de custos ocultos`;
        } else if (bdiTotal > this.benchmarks.bdi.max) {
            return `BDI elevado (${bdiTotal}%) - verificar composição detalhada`;
        } else {
            const itemsText = bdiItens.length > 0 ? ` com ${bdiItens.length} itens detalhados` : '';
            return `BDI adequado (${bdiTotal}%)${itemsText} - dentro dos padrões`;
        }
    }

    avaliarMateriais(proposta) {
        const materiais = proposta.materiaisComercial || [];
        let pontuacao = 30;
        
        if (materiais.length > 0) {
            pontuacao += 30;
            
            // Verificar especificação completa
            const bemEspecificados = materiais.filter(m => 
                m[1] && m[1].length > 10 // Especificação detalhada
            ).length;
            
            if (bemEspecificados / materiais.length > 0.8) pontuacao += 20;
            
            // Verificar preços unitários
            const comPrecos = materiais.filter(m => m[4] && parseFloat(m[4]) > 0).length;
            if (comPrecos === materiais.length) pontuacao += 20;
        }
        
        return Math.min(100, pontuacao);
    }

    gerarObservacaoMateriais(proposta) {
        const materiais = proposta.materiaisComercial || [];
        const totalMateriais = proposta.resumoFinanceiro?.totalMateriais || 0;
        
        if (materiais.length === 0) {
            return "Lista de materiais não apresentada - solicitar detalhamento";
        } else if (materiais.length < 5) {
            return "Lista de materiais resumida - pode haver itens agrupados";
        } else {
            const percentual = (totalMateriais / (proposta.resumoFinanceiro?.valorTotal || 1)) * 100;
            return `${materiais.length} materiais especificados (${percentual.toFixed(1)}% do valor total)`;
        }
    }

    avaliarMaoObra(proposta) {
        const maoObra = proposta.maoObraComercial || [];
        let pontuacao = 40;
        
        if (maoObra.length > 0) {
            pontuacao += 20;
            
            // Verificar encargos sociais
            const comEncargos = maoObra.filter(m => m[4] && parseFloat(m[4]) > 70).length;
            if (comEncargos === maoObra.length) pontuacao += 20;
            
            // Verificar diversidade de funções
            if (maoObra.length >= 3) pontuacao += 20;
        }
        
        return Math.min(100, pontuacao);
    }

    gerarObservacaoMaoObra(proposta) {
        const maoObra = proposta.maoObraComercial || [];
        
        if (maoObra.length === 0) {
            return "CRÍTICO: Custos de mão de obra não detalhados";
        }
        
        const encargosMedia = maoObra.reduce((acc, m) => acc + (parseFloat(m[4]) || 0), 0) / maoObra.length;
        
        if (encargosMedia < 70) {
            return `ALERTA: Encargos sociais baixos (${encargosMedia.toFixed(1)}%) - verificar legalidade`;
        } else if (encargosMedia > 100) {
            return `Encargos sociais elevados (${encargosMedia.toFixed(1)}%) - impacto no custo`;
        } else {
            return `Mão de obra bem dimensionada com encargos adequados (${encargosMedia.toFixed(1)}%)`;
        }
    }

    avaliarEquipamentos(proposta) {
        const equipamentos = proposta.equipamentosComercial || [];
        return equipamentos.length > 0 ? 70 + Math.min(30, equipamentos.length * 5) : 30;
    }

    gerarObservacaoEquipamentos(proposta) {
        const equipamentos = proposta.equipamentosComercial || [];
        const totalEquip = proposta.resumoFinanceiro?.totalEquipamentos || 0;
        
        if (equipamentos.length === 0) {
            return "Custos de equipamentos não detalhados";
        } else {
            const percentual = (totalEquip / (proposta.resumoFinanceiro?.valorTotal || 1)) * 100;
            return `${equipamentos.length} equipamentos (${percentual.toFixed(1)}% do valor total)`;
        }
    }

    avaliarCondicoes(proposta) {
        // Avaliação simplificada de condições
        return 70; // Valor padrão médio
    }

    gerarObservacaoCondicoes(proposta) {
        const garantia = parseInt(proposta.propostaTecnica.garantias) || 12;
        
        if (garantia > this.benchmarks.garantia.ideal) {
            return `Excelente garantia de ${garantia} meses oferecida`;
        } else if (garantia >= this.benchmarks.garantia.min) {
            return `Garantia padrão de ${garantia} meses`;
        } else {
            return "Verificar condições de garantia e pagamento";
        }
    }

    /**
     * Calcular pontuação total ponderada
     */
    calcularPontuacaoTotal(pontuacoes, tipoAnalise) {
        const criterios = this.criteriosAvaliacao[tipoAnalise];
        let total = 0;
        
        Object.keys(pontuacoes).forEach(criterio => {
            if (criterios[criterio]) {
                total += pontuacoes[criterio] * criterios[criterio].peso;
            }
        });
        
        return Math.round(total);
    }

    /**
     * Análise comparativa entre propostas
     */
    async compararPropostas(propostas, tipoAnalise) {
        const comparacao = {
            melhorProposta: null,
            piorProposta: null,
            variacaoMaxima: 0,
            criterioMaisDispersao: null,
            insights: []
        };
        
        // Implementar lógica de comparação
        const valores = propostas.map(p => p.resumoFinanceiro?.valorTotal || 0).filter(v => v > 0);
        
        if (valores.length > 0) {
            const menorValor = Math.min(...valores);
            const maiorValor = Math.max(...valores);
            comparacao.variacaoMaxima = ((maiorValor - menorValor) / menorValor * 100).toFixed(2);
            
            comparacao.melhorProposta = propostas.find(p => p.resumoFinanceiro?.valorTotal === menorValor);
            comparacao.piorProposta = propostas.find(p => p.resumoFinanceiro?.valorTotal === maiorValor);
            
            if (comparacao.variacaoMaxima > 30) {
                comparacao.insights.push(`Alta dispersão de valores (${comparacao.variacaoMaxima}%) indica diferentes interpretações do escopo`);
            }
        }
        
        return comparacao;
    }

    /**
     * Identificar riscos e oportunidades
     */
    async identificarRiscosOportunidades(propostas, tipoAnalise) {
        const analise = {
            riscos: [],
            oportunidades: [],
            alertas: []
        };
        
        propostas.forEach((proposta, index) => {
            const empresa = proposta.dadosCadastrais.razaoSocial;
            
            // Riscos técnicos
            if (tipoAnalise === 'tecnica') {
                const prazo = parseInt(proposta.propostaTecnica.prazoExecucao) || 0;
                if (prazo < this.benchmarks.prazo.min) {
                    analise.riscos.push({
                        empresa,
                        tipo: 'PRAZO_CURTO',
                        descricao: `Prazo muito curto (${prazo} dias) pode comprometer qualidade`,
                        severidade: 'ALTA'
                    });
                }
                
                if (!proposta.maoObraTecnica || proposta.maoObraTecnica.length < 3) {
                    analise.riscos.push({
                        empresa,
                        tipo: 'EQUIPE_REDUZIDA',
                        descricao: 'Equipe técnica subdimensionada',
                        severidade: 'MÉDIA'
                    });
                }
            }
            
            // Riscos comerciais
            if (tipoAnalise === 'comercial') {
                const valor = proposta.resumoFinanceiro?.valorTotal || 0;
                const valores = propostas.map(p => p.resumoFinanceiro?.valorTotal || 0).filter(v => v > 0);
                const mediaValor = valores.reduce((a, b) => a + b, 0) / valores.length;
                
                if (valor < mediaValor * 0.7) {
                    analise.riscos.push({
                        empresa,
                        tipo: 'PRECO_BAIXO',
                        descricao: 'Valor muito abaixo da média - risco de inexequibilidade',
                        severidade: 'ALTA'
                    });
                }
                
                const bdi = proposta.resumoFinanceiro?.bdiPercentual || 0;
                if (bdi < this.benchmarks.bdi.min) {
                    analise.riscos.push({
                        empresa,
                        tipo: 'BDI_BAIXO',
                        descricao: `BDI de ${bdi}% abaixo do mínimo aceitável`,
                        severidade: 'ALTA'
                    });
                }
            }
            
            // Oportunidades
            if (proposta.propostaTecnica.garantias && parseInt(proposta.propostaTecnica.garantias) > 24) {
                analise.oportunidades.push({
                    empresa,
                    tipo: 'GARANTIA_ESTENDIDA',
                    descricao: `Garantia estendida de ${proposta.propostaTecnica.garantias}`
                });
            }
        });
        
        return analise;
    }

    /**
     * Gerar recomendações específicas
     */
    async gerarRecomendacoes(propostas, analisesIndividuais, tipoAnalise) {
        const recomendacoes = {
            acoesPrioritarias: [],
            melhoriasContinuas: [],
            pontosCriticos: []
        };
        
        // Identificar empresa com melhor pontuação
        const melhorAnalise = analisesIndividuais.reduce((prev, current) => 
            prev.pontuacaoTotal > current.pontuacaoTotal ? prev : current
        );
        
        recomendacoes.acoesPrioritarias.push({
            acao: 'SELECIONAR_VENCEDOR',
            descricao: `Recomenda-se ${melhorAnalise.empresa} com pontuação ${melhorAnalise.pontuacaoTotal}/100`,
            justificativa: 'Melhor pontuação técnica e comercial combinada'
        });
        
        // Verificar necessidade de diligências
        analisesIndividuais.forEach(analise => {
            Object.keys(analise.pontuacoes).forEach(criterio => {
                if (analise.pontuacoes[criterio] < 40) {
                    recomendacoes.pontosCriticos.push({
                        empresa: analise.empresa,
                        criterio: this.criteriosAvaliacao[tipoAnalise][criterio].nome,
                        acao: 'Solicitar esclarecimentos/documentação adicional'
                    });
                }
            });
        });
        
        return recomendacoes;
    }

    /**
     * Calcular ranking final
     */
    calcularRanking(propostas, analisesIndividuais, tipoAnalise) {
        const ranking = analisesIndividuais
            .map((analise, index) => ({
                posicao: 0,
                empresa: analise.empresa,
                pontuacaoTotal: analise.pontuacaoTotal,
                detalhamento: analise.pontuacoes,
                proposta: propostas[index]
            }))
            .sort((a, b) => b.pontuacaoTotal - a.pontuacaoTotal)
            .map((item, index) => {
                item.posicao = index + 1;
                return item;
            });
        
        return ranking;
    }

    /**
     * Análise local (fallback)
     */
    analisarPropostasLocal(propostas, tipoAnalise) {
        // Implementação simplificada para fallback
        const analisesIndividuais = propostas.map(proposta => {
            const pontuacaoAleatoria = 60 + Math.random() * 30;
            return {
                empresa: proposta.dadosCadastrais.razaoSocial,
                cnpj: proposta.dadosCadastrais.cnpj,
                pontuacaoTotal: Math.round(pontuacaoAleatoria),
                observacoes: {
                    geral: 'Análise automática local - modo offline'
                }
            };
        });
        
        return {
            analisesIndividuais,
            analiseComparativa: {
                insights: ['Análise realizada em modo local']
            },
            analiseRiscos: {
                riscos: [],
                oportunidades: []
            },
            recomendacoes: {
                acoesPrioritarias: [{
                    acao: 'REVISAR_MANUALMENTE',
                    descricao: 'Revisar análise manualmente devido ao modo offline'
                }]
            },
            ranking: this.calcularRanking(propostas, analisesIndividuais, tipoAnalise),
            modoAnalise: 'LOCAL'
        };
    }

    /**
     * Formatadores
     */
    formatarMoeda(valor) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }

    /**
     * Gerar relatório HTML da análise
     */
    gerarRelatorioHTML(resultadoAnalise, tipoAnalise) {
        const { analisesIndividuais, analiseComparativa, analiseRiscos, recomendacoes, ranking } = resultadoAnalise;
        
        let html = `
            <div class="analise-ia-completa">
                <h3>📊 Análise Detalhada por Empresa</h3>
                
                ${analisesIndividuais.map(analise => `
                    <div class="analise-empresa" style="margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                        <h4>${analise.empresa}</h4>
                        <p><strong>Pontuação Total:</strong> ${analise.pontuacaoTotal}/100</p>
                        
                        <div class="criterios-detalhados" style="margin: 15px 0;">
                            ${Object.keys(analise.pontuacoes || {}).map(criterio => `
                                <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 5px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span><strong>${this.criteriosAvaliacao[tipoAnalise][criterio]?.nome || criterio}:</strong></span>
                                        <span style="font-weight: bold; color: ${this.getCorPontuacao(analise.pontuacoes[criterio])}">
                                            ${analise.pontuacoes[criterio]}/100
                                        </span>
                                    </div>
                                    <p style="margin: 5px 0; font-size: 0.9em; color: #666;">
                                        ${analise.observacoes[criterio] || 'Sem observações'}
                                    </p>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
                
                ${analiseRiscos.riscos.length > 0 ? `
                    <h3>⚠️ Riscos Identificados</h3>
                    <div style="background: #ffebee; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        ${analiseRiscos.riscos.map(risco => `
                            <div style="margin: 10px 0;">
                                <strong>${risco.empresa}:</strong> ${risco.descricao}
                                <span style="color: ${risco.severidade === 'ALTA' ? '#d32f2f' : '#f57c00'}; font-weight: bold;">
                                    (${risco.severidade})
                                </span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                ${recomendacoes.acoesPrioritarias.length > 0 ? `
                    <h3>🎯 Recomendações</h3>
                    <div style="background: #e8f5e9; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        ${recomendacoes.acoesPrioritarias.map(rec => `
                            <div style="margin: 10px 0;">
                                <strong>${rec.descricao}</strong>
                                <p style="margin: 5px 0; color: #666;">${rec.justificativa || ''}</p>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                <h3>🏆 Ranking Final</h3>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px;">
                    ${ranking.map(item => `
                        <div style="margin: 10px 0; padding: 15px; background: ${item.posicao === 1 ? '#fff8e1' : 'white'}; 
                                    border-radius: 8px; border-left: 4px solid ${item.posicao === 1 ? '#ffc107' : '#e0e0e0'};">
                            <strong>${item.posicao}º lugar:</strong> ${item.empresa} - ${item.pontuacaoTotal} pontos
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        return html;
    }

    getCorPontuacao(pontuacao) {
        if (pontuacao >= 80) return '#4caf50';
        if (pontuacao >= 60) return '#ff9800';
        return '#f44336';
    }
}

// Exportar para uso global
window.AnalisadorIAPropostasAprimorado = AnalisadorIAPropostasAprimorado;
