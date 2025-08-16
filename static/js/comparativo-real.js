/**
 * Sistema de Comparativo de Propostas - Baseado no Portal Real
 * Estrutura exata das tabelas do portal-propostas-novo.html
 */

class ComparativoPropostasReal {
    constructor() {
        this.currentProcess = null;
        this.currentTab = 'tecnica';
        this.proposals = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSampleData();
    }

    setupEventListeners() {
        // Tab switching
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.getAttribute('data-tab'));
            });
        });

        // Process selection
        const processSelect = document.getElementById('processSelect');
        if (processSelect) {
            processSelect.addEventListener('change', (e) => {
                this.loadProcess(e.target.value);
            });
        }

        // Export buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-primary')) {
                this.exportData();
            }
            if (e.target.closest('.btn-secondary')) {
                this.openFilters();
            }
        });
    }

    switchTab(tabName) {
        // Update button states
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content visibility
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');

        this.currentTab = tabName;
        this.updateAIInsights(tabName);
    }

    loadProcess(processId) {
        if (!processId) return;

        this.currentProcess = processId;
        this.showLoading();

        // Simulate API call
        setTimeout(() => {
            this.loadProposalData(processId);
            this.hideLoading();
        }, 1500);
    }

    loadProposalData(processId) {
        const processData = this.getSampleProcessData(processId);
        this.proposals = processData.proposals;
        
        this.updateCompanyHeaders();
        this.updateAllTables();
        this.updateAIInsights(this.currentTab);
    }

    updateCompanyHeaders() {
        const headers = document.querySelectorAll('.company-header');
        headers.forEach((header, index) => {
            if (this.proposals[index]) {
                header.textContent = this.proposals[index].dadosCadastrais.razaoSocial;
            }
        });
    }

    updateAllTables() {
        // Análise Técnica
        this.updateDadosCadastraisTable();
        this.updatePropostaTecnicaTable();
        this.updateServicosTecnicaTable();
        this.updateMaoObraTecnicaTable();
        this.updateMateriaisTecnicaTable();
        this.updateEquipamentosTecnicaTable();

        // Análise Comercial
        this.updateServicosComercialTable();
        this.updateMaoObraComercialTable();
        this.updateMateriaisComercialTable();
        this.updateEquipamentosComercialTable();
        this.updateBDITable();
        this.updateResumoFinanceiroTable();
    }

    // ===== TABELAS DE ANÁLISE TÉCNICA =====

    updateDadosCadastraisTable() {
        const tableBody = document.getElementById('dadosCadastraisTable');
        if (!tableBody) return;

        const items = [
            { label: 'Razão Social', key: 'razaoSocial' },
            { label: 'CNPJ', key: 'cnpj' },
            { label: 'Endereço', key: 'endereco' },
            { label: 'Cidade/UF', key: 'cidade' },
            { label: 'Telefone', key: 'telefone' },
            { label: 'E-mail', key: 'email' },
            { label: 'Responsável Técnico', key: 'respTecnico' },
            { label: 'CREA/CAU', key: 'crea' }
        ];

        this.buildTable(tableBody, items, 'dadosCadastrais');
    }

    updatePropostaTecnicaTable() {
        const tableBody = document.getElementById('propostaTecnicaTable');
        if (!tableBody) return;

        const items = [
            { label: 'Objeto da Concorrência', key: 'objetoConcorrencia', type: 'text' },
            { label: 'Serviços a Executar', key: 'escopoInclusos', type: 'text' },
            { label: 'Serviços Ocultos', key: 'escopoExclusos', type: 'text' },
            { label: 'Metodologia de Execução', key: 'metodologia', type: 'text' },
            { label: 'Plano de Execução', key: 'sequenciaExecucao', type: 'text' },
            { label: 'Prazo de Execução', key: 'prazoExecucao', type: 'text' },
            { label: 'Prazo de Mobilização', key: 'prazoMobilizacao', type: 'text' },
            { label: 'Garantias Oferecidas', key: 'garantias', type: 'text' },
            { label: 'Estrutura do Canteiro', key: 'estruturaCanteiro', type: 'text' },
            { label: 'Obrigações da Contratada', key: 'obrigacoesContratada', type: 'text' },
            { label: 'Obrigações da Contratante', key: 'obrigacoesContratante', type: 'text' }
        ];

        this.buildTable(tableBody, items, 'propostaTecnica');
    }

    updateServicosTecnicaTable() {
        const tableBody = document.getElementById('servicosTecnicaTable');
        if (!tableBody) return;

        // Coletar todos os serviços únicos de todas as propostas
        const servicosUnicos = new Set();
        this.proposals.forEach(proposal => {
            if (proposal.servicosTecnica) {
                proposal.servicosTecnica.forEach(servico => {
                    servicosUnicos.add(servico.descricao);
                });
            }
        });

        tableBody.innerHTML = '';
        
        Array.from(servicosUnicos).forEach(servicoDesc => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = servicoDesc;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const servico = proposal.servicosTecnica?.find(s => s.descricao === servicoDesc);
                if (servico) {
                    cell.innerHTML = `
                        <div><strong>Unidade:</strong> <span class="value-text">${servico.unidade}</span></div>
                        <div><strong>Quantidade:</strong> <span class="value-quantity">${servico.quantidade}</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    updateMaoObraTecnicaTable() {
        const tableBody = document.getElementById('maoObraTecnicaTable');
        if (!tableBody) return;

        // Coletar todas as funções únicas
        const funcoesUnicas = new Set();
        this.proposals.forEach(proposal => {
            if (proposal.maoObraTecnica) {
                proposal.maoObraTecnica.forEach(func => {
                    funcoesUnicas.add(func.funcao);
                });
            }
        });

        tableBody.innerHTML = '';
        
        Array.from(funcoesUnicas).forEach(funcao => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = funcao;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const func = proposal.maoObraTecnica?.find(f => f.funcao === funcao);
                if (func) {
                    cell.innerHTML = `
                        <div><strong>Quantidade:</strong> <span class="value-quantity">${func.quantidade}</span></div>
                        <div><strong>Tempo:</strong> <span class="value-text">${func.tempo} meses</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    updateMateriaisTecnicaTable() {
        const tableBody = document.getElementById('materiaisTecnicaTable');
        if (!tableBody) return;

        // Coletar todos os materiais únicos
        const materiaisUnicos = new Set();
        this.proposals.forEach(proposal => {
            if (proposal.materiaisTecnica) {
                proposal.materiaisTecnica.forEach(mat => {
                    materiaisUnicos.add(mat.material);
                });
            }
        });

        tableBody.innerHTML = '';
        
        Array.from(materiaisUnicos).forEach(material => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = material;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const mat = proposal.materiaisTecnica?.find(m => m.material === material);
                if (mat) {
                    cell.innerHTML = `
                        <div><strong>Especificação:</strong> <span class="value-text">${mat.especificacao}</span></div>
                        <div><strong>Unidade:</strong> <span class="value-text">${mat.unidade}</span></div>
                        <div><strong>Quantidade:</strong> <span class="value-quantity">${mat.quantidade}</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    updateEquipamentosTecnicaTable() {
        const tableBody = document.getElementById('equipamentosTecnicaTable');
        if (!tableBody) return;

        // Coletar todos os equipamentos únicos
        const equipamentosUnicos = new Set();
        this.proposals.forEach(proposal => {
            if (proposal.equipamentosTecnica) {
                proposal.equipamentosTecnica.forEach(eq => {
                    equipamentosUnicos.add(eq.equipamento);
                });
            }
        });

        tableBody.innerHTML = '';
        
        Array.from(equipamentosUnicos).forEach(equipamento => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = equipamento;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const eq = proposal.equipamentosTecnica?.find(e => e.equipamento === equipamento);
                if (eq) {
                    cell.innerHTML = `
                        <div><strong>Especificação:</strong> <span class="value-text">${eq.especificacao}</span></div>
                        <div><strong>Unidade:</strong> <span class="value-text">${eq.unidade}</span></div>
                        <div><strong>Quantidade:</strong> <span class="value-quantity">${eq.quantidade}</span></div>
                        <div><strong>Tempo:</strong> <span class="value-text">${eq.tempo} meses</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    // ===== TABELAS DE ANÁLISE COMERCIAL =====

    updateServicosComercialTable() {
        const tableBody = document.getElementById('servicosComercialTable');
        if (!tableBody) return;

        // Coletar todos os serviços únicos
        const servicosUnicos = new Set();
        this.proposals.forEach(proposal => {
            if (proposal.servicosComercial) {
                proposal.servicosComercial.forEach(servico => {
                    servicosUnicos.add(servico.descricao);
                });
            }
        });

        tableBody.innerHTML = '';
        
        Array.from(servicosUnicos).forEach(servicoDesc => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = servicoDesc;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const servico = proposal.servicosComercial?.find(s => s.descricao === servicoDesc);
                if (servico) {
                    cell.innerHTML = `
                        <div><strong>Unidade:</strong> <span class="value-text">${servico.unidade}</span></div>
                        <div><strong>Quantidade:</strong> <span class="value-quantity">${servico.quantidade}</span></div>
                        <div><strong>Preço Unit:</strong> <span class="value-monetary">${this.formatCurrency(servico.precoUnitario)}</span></div>
                        <div><strong>Total:</strong> <span class="value-total">${this.formatCurrency(servico.total)}</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    updateMaoObraComercialTable() {
        const tableBody = document.getElementById('maoObraComercialTable');
        if (!tableBody) return;

        // Coletar todas as funções únicas
        const funcoesUnicas = new Set();
        this.proposals.forEach(proposal => {
            if (proposal.maoObraComercial) {
                proposal.maoObraComercial.forEach(func => {
                    funcoesUnicas.add(func.funcao);
                });
            }
        });

        tableBody.innerHTML = '';
        
        Array.from(funcoesUnicas).forEach(funcao => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = funcao;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const func = proposal.maoObraComercial?.find(f => f.funcao === funcao);
                if (func) {
                    cell.innerHTML = `
                        <div><strong>Quantidade:</strong> <span class="value-quantity">${func.quantidade}</span></div>
                        <div><strong>Tempo:</strong> <span class="value-text">${func.tempo} meses</span></div>
                        <div><strong>Salário:</strong> <span class="value-monetary">${this.formatCurrency(func.salario)}</span></div>
                        <div><strong>Enc. Sociais:</strong> <span class="value-percentage">${func.encargos}%</span></div>
                        <div><strong>Total:</strong> <span class="value-total">${this.formatCurrency(func.total)}</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    updateMateriaisComercialTable() {
        const tableBody = document.getElementById('materiaisComercialTable');
        if (!tableBody) return;

        // Coletar todos os materiais únicos
        const materiaisUnicos = new Set();
        this.proposals.forEach(proposal => {
            if (proposal.materiaisComercial) {
                proposal.materiaisComercial.forEach(mat => {
                    materiaisUnicos.add(mat.material);
                });
            }
        });

        tableBody.innerHTML = '';
        
        Array.from(materiaisUnicos).forEach(material => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = material;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const mat = proposal.materiaisComercial?.find(m => m.material === material);
                if (mat) {
                    cell.innerHTML = `
                        <div><strong>Especificação:</strong> <span class="value-text">${mat.especificacao}</span></div>
                        <div><strong>Unidade:</strong> <span class="value-text">${mat.unidade}</span></div>
                        <div><strong>Quantidade:</strong> <span class="value-quantity">${mat.quantidade}</span></div>
                        <div><strong>Preço Unit:</strong> <span class="value-monetary">${this.formatCurrency(mat.precoUnitario)}</span></div>
                        <div><strong>Total:</strong> <span class="value-total">${this.formatCurrency(mat.total)}</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    updateEquipamentosComercialTable() {
        const tableBody = document.getElementById('equipamentosComercialTable');
        if (!tableBody) return;

        // Coletar todos os equipamentos únicos
        const equipamentosUnicos = new Set();
        this.proposals.forEach(proposal => {
            if (proposal.equipamentosComercial) {
                proposal.equipamentosComercial.forEach(eq => {
                    equipamentosUnicos.add(eq.equipamento);
                });
            }
        });

        tableBody.innerHTML = '';
        
        Array.from(equipamentosUnicos).forEach(equipamento => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = equipamento;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const eq = proposal.equipamentosComercial?.find(e => e.equipamento === equipamento);
                if (eq) {
                    cell.innerHTML = `
                        <div><strong>Especificação:</strong> <span class="value-text">${eq.especificacao}</span></div>
                        <div><strong>Quantidade:</strong> <span class="value-quantity">${eq.quantidade}</span></div>
                        <div><strong>Tempo:</strong> <span class="value-text">${eq.tempo} meses</span></div>
                        <div><strong>Preço/mês:</strong> <span class="value-monetary">${this.formatCurrency(eq.precoMensal)}</span></div>
                        <div><strong>Total:</strong> <span class="value-total">${this.formatCurrency(eq.total)}</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    updateBDITable() {
        const tableBody = document.getElementById('bdiTable');
        if (!tableBody) return;

        const bdiItems = [
            'Administração Central',
            'Seguros e Garantias',
            'Riscos',
            'Despesas Financeiras',
            'Lucro',
            'Tributos (ISS, PIS, COFINS)'
        ];

        tableBody.innerHTML = '';
        
        bdiItems.forEach(item => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = item;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const bdiItem = proposal.bdi?.find(b => b.item === item);
                if (bdiItem) {
                    cell.innerHTML = `
                        <div><strong>Percentual:</strong> <span class="value-percentage">${bdiItem.percentual}%</span></div>
                        <div><strong>Valor:</strong> <span class="value-monetary">${this.formatCurrency(bdiItem.valor)}</span></div>
                    `;
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    updateResumoFinanceiroTable() {
        const tableBody = document.getElementById('resumoFinanceiroTable');
        if (!tableBody) return;

        const resumoItems = [
            { label: 'Total Serviços', key: 'totalServicos' },
            { label: 'Total Mão de Obra', key: 'totalMaoObra' },
            { label: 'Total Materiais', key: 'totalMateriais' },
            { label: 'Total Equipamentos', key: 'totalEquipamentos' },
            { label: 'Custo Direto', key: 'custoDireto' },
            { label: 'BDI Total (%)', key: 'bdiPercentual' },
            { label: 'BDI Total (R$)', key: 'bdiValor' },
            { label: 'VALOR TOTAL DA PROPOSTA', key: 'valorTotal' }
        ];

        tableBody.innerHTML = '';
        
        resumoItems.forEach(item => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = item.label;
            if (item.key === 'valorTotal') {
                labelCell.style.background = 'linear-gradient(135deg, #e74c3c, #c0392b)';
                labelCell.style.fontSize = '1.1rem';
            }
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const value = proposal.resumoFinanceiro?.[item.key];
                if (value !== undefined) {
                    if (item.key === 'bdiPercentual') {
                        cell.innerHTML = `<span class="value-percentage">${value}%</span>`;
                    } else if (item.key === 'valorTotal') {
                        cell.innerHTML = `<span class="value-total">${this.formatCurrency(value)}</span>`;
                        cell.style.background = 'rgba(231, 76, 60, 0.1)';
                        cell.style.fontWeight = 'bold';
                    } else {
                        cell.innerHTML = `<span class="value-monetary">${this.formatCurrency(value)}</span>`;
                    }
                } else {
                    cell.innerHTML = '<span class="value-text">Não informado</span>';
                }
                
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    // ===== UTILITY FUNCTIONS =====

    buildTable(tableBody, items, dataSection) {
        tableBody.innerHTML = '';

        items.forEach(item => {
            const row = document.createElement('tr');
            
            // Label column
            const labelCell = document.createElement('td');
            labelCell.className = 'item-label';
            labelCell.textContent = item.label;
            row.appendChild(labelCell);

            // Proposal columns
            this.proposals.forEach(proposal => {
                const cell = document.createElement('td');
                cell.className = 'proposal-cell';
                
                const value = proposal[dataSection]?.[item.key];
                const formattedValue = this.formatValue(value, item.type);
                
                cell.innerHTML = formattedValue;
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });
    }

    formatValue(value, type) {
        if (value === undefined || value === null || value === '') {
            return '<span class="value-text">Não informado</span>';
        }

        switch (type) {
            case 'monetary':
                return `<span class="value-monetary">${this.formatCurrency(value)}</span>`;
            case 'percentage':
                return `<span class="value-percentage">${value}%</span>`;
            case 'quantity':
                return `<span class="value-quantity">${value}</span>`;
            case 'text':
            default:
                return `<span class="value-text">${value}</span>`;
        }
    }

    formatCurrency(value) {
        if (typeof value === 'number') {
            return new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(value);
        }
        return value;
    }

    updateAIInsights(tabType) {
        const insights = this.getAIInsights(tabType);
        
        document.getElementById('aiHighlight').textContent = insights.highlight;
        document.getElementById('aiAttention').textContent = insights.attention;
        document.getElementById('aiMarket').textContent = insights.market;
    }

    getAIInsights(tabType) {
        if (tabType === 'tecnica') {
            return {
                highlight: 'Empresa A apresenta metodologia mais detalhada e equipe técnica robusta com maior experiência em obras similares.',
                attention: 'Empresa C tem prazo muito otimista (120 dias) que pode indicar subdimensionamento. Empresa B não detalhou adequadamente a metodologia.',
                market: 'Tendência do mercado valoriza empresas com certificações ambientais e uso de tecnologia BIM para controle de qualidade.'
            };
        } else {
            return {
                highlight: 'Empresa A oferece melhor custo-benefício com BDI equilibrado (28%) e preços competitivos nos materiais.',
                attention: 'Empresa C tem valor 45% acima da média. BDI da Empresa B está muito baixo (22%) - verificar viabilidade.',
                market: 'Preços de materiais estão 8% acima da média histórica devido à alta do aço. Mão de obra especializada valorizada 12%.'
            };
        }
    }

    showLoading() {
        const containers = document.querySelectorAll('.comparison-container');
        containers.forEach(container => {
            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-spinner"></div>
                <div style="color: #64748b; font-weight: 600;">Carregando dados das propostas...</div>
            `;
            
            container.style.position = 'relative';
            container.appendChild(overlay);
        });
    }

    hideLoading() {
        document.querySelectorAll('.loading-overlay').forEach(overlay => {
            overlay.remove();
        });
    }

    exportData() {
        const currentTabName = this.currentTab === 'tecnica' ? 'Tecnica' : 'Comercial';
        
        // Generate export data based on current tab
        const data = this.generateExportData();
        const csv = this.convertToCSV(data);
        this.downloadCSV(csv, `Comparativo_${currentTabName}_${this.currentProcess}.csv`);
    }

    generateExportData() {
        const data = [];
        const tables = document.querySelectorAll(`#${this.currentTab} .comparison-table`);
        
        tables.forEach((table, tableIndex) => {
            if (tableIndex > 0) data.push([]); // Add separator between tables
            
            const rows = table.querySelectorAll('tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('th, td');
                const rowData = Array.from(cells).map(cell => 
                    cell.textContent.trim().replace(/\n/g, ' ').replace(/\s+/g, ' ')
                );
                data.push(rowData);
            });
        });
        
        return data;
    }

    convertToCSV(data) {
        return data.map(row => 
            row.map(cell => `"${cell}"`).join(',')
        ).join('\n');
    }

    downloadCSV(csv, filename) {
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    openFilters() {
        // Simple filter implementation
        const filters = [
            'Valor até R$ 3M',
            'Prazo até 180 dias',
            'Com certificação ISO',
            'BDI até 30%',
            'Experiência > 10 anos'
        ];
        
        const selectedFilters = [];

        filters.forEach(filter => {
            if (confirm(`Aplicar filtro: ${filter}?`)) {
                selectedFilters.push(filter);
            }
        });

        if (selectedFilters.length > 0) {
            alert(`Filtros aplicados: ${selectedFilters.join(', ')}`);
            // Here you would implement the actual filtering logic
        }
    }

    loadSampleData() {
        // Load default sample data
        this.proposals = this.getSampleProcessData('proc_001').proposals;
        this.updateCompanyHeaders();
        this.updateAllTables();
    }

    getSampleProcessData(processId) {
        const sampleData = {
            'proc_001': {
                name: 'Construção de Escola Municipal',
                proposals: [
                    {
                        dadosCadastrais: {
                            razaoSocial: 'Construtora Alpha LTDA',
                            cnpj: '12.345.678/0001-90',
                            endereco: 'Rua das Obras, 123',
                            cidade: 'São Paulo/SP',
                            telefone: '(11) 3456-7890',
                            email: 'contato@alpha.com.br',
                            respTecnico: 'João Silva',
                            crea: 'CREA-SP 123456'
                        },
                        propostaTecnica: {
                            objetoConcorrencia: 'Construção de escola municipal com 12 salas de aula, biblioteca, laboratório e quadra esportiva',
                            escopoInclusos: 'Fundação, estrutura, alvenaria, cobertura, instalações elétricas e hidráulicas, acabamentos',
                            escopoExclusos: 'Mobiliário escolar, equipamentos de laboratório',
                            metodologia: 'Execução por etapas: fundação, estrutura, vedações, instalações, acabamentos. Controle rigoroso de qualidade.',
                            sequenciaExecucao: 'Mobilização (15 dias), Fundação (30 dias), Estrutura (45 dias), Vedações (30 dias), Instalações (25 dias), Acabamentos (35 dias)',
                            prazoExecucao: '180 dias corridos',
                            prazoMobilizacao: '15 dias',
                            garantias: '5 anos para estrutura, 3 anos para instalações, 1 ano para acabamentos',
                            estruturaCanteiro: 'Escritório, almoxarifado, vestiários, refeitório, guarita',
                            obrigacoesContratada: 'Alimentação, transporte, energia, água, segurança',
                            obrigacoesContratante: 'Fornecimento do terreno, licenças ambientais'
                        },
                        servicosTecnica: [
                            { descricao: 'Escavação para fundação', unidade: 'm³', quantidade: 450 },
                            { descricao: 'Concreto estrutural', unidade: 'm³', quantidade: 380 },
                            { descricao: 'Alvenaria de vedação', unidade: 'm²', quantidade: 2800 },
                            { descricao: 'Cobertura metálica', unidade: 'm²', quantidade: 1200 },
                            { descricao: 'Instalações elétricas', unidade: 'ponto', quantidade: 150 }
                        ],
                        maoObraTecnica: [
                            { funcao: 'Engenheiro Civil', quantidade: 1, tempo: 6 },
                            { funcao: 'Mestre de Obras', quantidade: 2, tempo: 6 },
                            { funcao: 'Pedreiro', quantidade: 8, tempo: 5 },
                            { funcao: 'Servente', quantidade: 12, tempo: 6 },
                            { funcao: 'Eletricista', quantidade: 3, tempo: 2 }
                        ],
                        materiaisTecnica: [
                            { material: 'Concreto', especificacao: 'FCK 25 MPa', unidade: 'm³', quantidade: 380 },
                            { material: 'Aço CA-50', especificacao: '12mm', unidade: 'kg', quantidade: 15000 },
                            { material: 'Bloco cerâmico', especificacao: '14x19x29cm', unidade: 'und', quantidade: 25000 },
                            { material: 'Telha metálica', especificacao: 'Galvanizada', unidade: 'm²', quantidade: 1200 }
                        ],
                        equipamentosTecnica: [
                            { equipamento: 'Betoneira', especificacao: '400L', unidade: 'und', quantidade: 2, tempo: 4 },
                            { equipamento: 'Guindaste', especificacao: '20t', unidade: 'und', quantidade: 1, tempo: 2 },
                            { equipamento: 'Vibrador', especificacao: 'Imersão', unidade: 'und', quantidade: 4, tempo: 3 }
                        ],
                        servicosComercial: [
                            { descricao: 'Escavação para fundação', unidade: 'm³', quantidade: 450, precoUnitario: 25.50, total: 11475 },
                            { descricao: 'Concreto estrutural', unidade: 'm³', quantidade: 380, precoUnitario: 450.00, total: 171000 },
                            { descricao: 'Alvenaria de vedação', unidade: 'm²', quantidade: 2800, precoUnitario: 85.00, total: 238000 },
                            { descricao: 'Cobertura metálica', unidade: 'm²', quantidade: 1200, precoUnitario: 120.00, total: 144000 },
                            { descricao: 'Instalações elétricas', unidade: 'ponto', quantidade: 150, precoUnitario: 350.00, total: 52500 }
                        ],
                        maoObraComercial: [
                            { funcao: 'Engenheiro Civil', quantidade: 1, tempo: 6, salario: 12000, encargos: 80, total: 129600 },
                            { funcao: 'Mestre de Obras', quantidade: 2, tempo: 6, salario: 4500, encargos: 80, total: 97200 },
                            { funcao: 'Pedreiro', quantidade: 8, tempo: 5, salario: 2800, encargos: 80, total: 201600 },
                            { funcao: 'Servente', quantidade: 12, tempo: 6, salario: 1800, encargos: 80, total: 233280 },
                            { funcao: 'Eletricista', quantidade: 3, tempo: 2, salario: 3200, encargos: 80, total: 34560 }
                        ],
                        materiaisComercial: [
                            { material: 'Concreto', especificacao: 'FCK 25 MPa', unidade: 'm³', quantidade: 380, precoUnitario: 420.00, total: 159600 },
                            { material: 'Aço CA-50', especificacao: '12mm', unidade: 'kg', quantidade: 15000, precoUnitario: 6.80, total: 102000 },
                            { material: 'Bloco cerâmico', especificacao: '14x19x29cm', unidade: 'und', quantidade: 25000, precoUnitario: 1.20, total: 30000 },
                            { material: 'Telha metálica', especificacao: 'Galvanizada', unidade: 'm²', quantidade: 1200, precoUnitario: 45.00, total: 54000 }
                        ],
                        equipamentosComercial: [
                            { equipamento: 'Betoneira', especificacao: '400L', quantidade: 2, tempo: 4, precoMensal: 1200, total: 9600 },
                            { equipamento: 'Guindaste', especificacao: '20t', quantidade: 1, tempo: 2, precoMensal: 8000, total: 16000 },
                            { equipamento: 'Vibrador', especificacao: 'Imersão', quantidade: 4, tempo: 3, precoMensal: 300, total: 3600 }
                        ],
                        bdi: [
                            { item: 'Administração Central', percentual: 8.0, valor: 180000 },
                            { item: 'Seguros e Garantias', percentual: 1.5, valor: 33750 },
                            { item: 'Riscos', percentual: 2.0, valor: 45000 },
                            { item: 'Despesas Financeiras', percentual: 1.0, valor: 22500 },
                            { item: 'Lucro', percentual: 8.0, valor: 180000 },
                            { item: 'Tributos (ISS, PIS, COFINS)', percentual: 7.5, valor: 168750 }
                        ],
                        resumoFinanceiro: {
                            totalServicos: 616975,
                            totalMaoObra: 696240,
                            totalMateriais: 345600,
                            totalEquipamentos: 29200,
                            custoDireto: 1688015,
                            bdiPercentual: 28.0,
                            bdiValor: 630000,
                            valorTotal: 2850000
                        }
                    },
                    {
                        dadosCadastrais: {
                            razaoSocial: 'Engenharia Beta S/A',
                            cnpj: '98.765.432/0001-10',
                            endereco: 'Av. Construção, 456',
                            cidade: 'Rio de Janeiro/RJ',
                            telefone: '(21) 2345-6789',
                            email: 'propostas@beta.com.br',
                            respTecnico: 'Maria Santos',
                            crea: 'CREA-RJ 654321'
                        },
                        propostaTecnica: {
                            objetoConcorrencia: 'Construção de escola municipal conforme projeto arquitetônico fornecido',
                            escopoInclusos: 'Todos os serviços de construção civil conforme memorial descritivo',
                            escopoExclusos: 'Equipamentos e mobiliário',
                            metodologia: 'Execução tradicional com controle de qualidade básico',
                            sequenciaExecucao: 'Fundação, estrutura, vedações, cobertura, instalações, acabamentos',
                            prazoExecucao: '165 dias corridos',
                            prazoMobilizacao: '10 dias',
                            garantias: '3 anos para estrutura, 2 anos para instalações',
                            estruturaCanteiro: 'Escritório, almoxarifado, vestiários',
                            obrigacoesContratada: 'Alimentação, transporte básico',
                            obrigacoesContratante: 'Terreno, licenças, energia, água'
                        },
                        servicosTecnica: [
                            { descricao: 'Escavação para fundação', unidade: 'm³', quantidade: 420 },
                            { descricao: 'Concreto estrutural', unidade: 'm³', quantidade: 360 },
                            { descricao: 'Alvenaria de vedação', unidade: 'm²', quantidade: 2600 },
                            { descricao: 'Cobertura metálica', unidade: 'm²', quantidade: 1150 },
                            { descricao: 'Instalações elétricas', unidade: 'ponto', quantidade: 140 }
                        ],
                        maoObraTecnica: [
                            { funcao: 'Engenheiro Civil', quantidade: 1, tempo: 5.5 },
                            { funcao: 'Mestre de Obras', quantidade: 1, tempo: 5.5 },
                            { funcao: 'Pedreiro', quantidade: 6, tempo: 5 },
                            { funcao: 'Servente', quantidade: 10, tempo: 5.5 },
                            { funcao: 'Eletricista', quantidade: 2, tempo: 2 }
                        ],
                        materiaisTecnica: [
                            { material: 'Concreto', especificacao: 'FCK 20 MPa', unidade: 'm³', quantidade: 360 },
                            { material: 'Aço CA-50', especificacao: '10mm', unidade: 'kg', quantidade: 14000 },
                            { material: 'Bloco cerâmico', especificacao: '14x19x29cm', unidade: 'und', quantidade: 23000 },
                            { material: 'Telha metálica', especificacao: 'Galvanizada', unidade: 'm²', quantidade: 1150 }
                        ],
                        equipamentosTecnica: [
                            { equipamento: 'Betoneira', especificacao: '320L', unidade: 'und', quantidade: 1, tempo: 4 },
                            { equipamento: 'Guindaste', especificacao: '15t', unidade: 'und', quantidade: 1, tempo: 1.5 },
                            { equipamento: 'Vibrador', especificacao: 'Imersão', unidade: 'und', quantidade: 2, tempo: 3 }
                        ],
                        servicosComercial: [
                            { descricao: 'Escavação para fundação', unidade: 'm³', quantidade: 420, precoUnitario: 28.00, total: 11760 },
                            { descricao: 'Concreto estrutural', unidade: 'm³', quantidade: 360, precoUnitario: 480.00, total: 172800 },
                            { descricao: 'Alvenaria de vedação', unidade: 'm²', quantidade: 2600, precoUnitario: 90.00, total: 234000 },
                            { descricao: 'Cobertura metálica', unidade: 'm²', quantidade: 1150, precoUnitario: 125.00, total: 143750 },
                            { descricao: 'Instalações elétricas', unidade: 'ponto', quantidade: 140, precoUnitario: 380.00, total: 53200 }
                        ],
                        maoObraComercial: [
                            { funcao: 'Engenheiro Civil', quantidade: 1, tempo: 5.5, salario: 11000, encargos: 75, total: 106125 },
                            { funcao: 'Mestre de Obras', quantidade: 1, tempo: 5.5, salario: 4200, encargos: 75, total: 40425 },
                            { funcao: 'Pedreiro', quantidade: 6, tempo: 5, salario: 2900, encargos: 75, total: 152250 },
                            { funcao: 'Servente', quantidade: 10, tempo: 5.5, salario: 1750, encargos: 75, total: 168437.50 },
                            { funcao: 'Eletricista', quantidade: 2, tempo: 2, salario: 3100, encargos: 75, total: 21700 }
                        ],
                        materiaisComercial: [
                            { material: 'Concreto', especificacao: 'FCK 20 MPa', unidade: 'm³', quantidade: 360, precoUnitario: 400.00, total: 144000 },
                            { material: 'Aço CA-50', especificacao: '10mm', unidade: 'kg', quantidade: 14000, precoUnitario: 7.20, total: 100800 },
                            { material: 'Bloco cerâmico', especificacao: '14x19x29cm', unidade: 'und', quantidade: 23000, precoUnitario: 1.15, total: 26450 },
                            { material: 'Telha metálica', especificacao: 'Galvanizada', unidade: 'm²', quantidade: 1150, precoUnitario: 42.00, total: 48300 }
                        ],
                        equipamentosComercial: [
                            { equipamento: 'Betoneira', especificacao: '320L', quantidade: 1, tempo: 4, precoMensal: 1000, total: 4000 },
                            { equipamento: 'Guindaste', especificacao: '15t', quantidade: 1, tempo: 1.5, precoMensal: 7500, total: 11250 },
                            { equipamento: 'Vibrador', especificacao: 'Imersão', quantidade: 2, tempo: 3, precoMensal: 280, total: 1680 }
                        ],
                        bdi: [
                            { item: 'Administração Central', percentual: 6.0, valor: 150000 },
                            { item: 'Seguros e Garantias', percentual: 1.0, valor: 25000 },
                            { item: 'Riscos', percentual: 1.5, valor: 37500 },
                            { item: 'Despesas Financeiras', percentual: 0.8, valor: 20000 },
                            { item: 'Lucro', percentual: 6.0, valor: 150000 },
                            { item: 'Tributos (ISS, PIS, COFINS)', percentual: 6.7, valor: 167500 }
                        ],
                        resumoFinanceiro: {
                            totalServicos: 615510,
                            totalMaoObra: 488937.50,
                            totalMateriais: 319550,
                            totalEquipamentos: 16930,
                            custoDireto: 1440927.50,
                            bdiPercentual: 22.0,
                            bdiValor: 550000,
                            valorTotal: 3120000
                        }
                    },
                    {
                        dadosCadastrais: {
                            razaoSocial: 'Construtora Gamma Ltda',
                            cnpj: '11.222.333/0001-44',
                            endereco: 'Rua Inovação, 789',
                            cidade: 'Belo Horizonte/MG',
                            telefone: '(31) 3456-7890',
                            email: 'comercial@gamma.com.br',
                            respTecnico: 'Carlos Oliveira',
                            crea: 'CREA-MG 987654'
                        },
                        propostaTecnica: {
                            objetoConcorrencia: 'Construção de escola municipal sustentável com tecnologia avançada e certificação LEED',
                            escopoInclusos: 'Construção completa, sistemas inteligentes, energia solar, reuso de água',
                            escopoExclusos: 'Mobiliário, equipamentos de informática',
                            metodologia: 'Metodologia BIM 5D, lean construction, controle IoT, gestão sustentável',
                            sequenciaExecucao: 'Planejamento BIM, execução por módulos, controle automatizado',
                            prazoExecucao: '120 dias corridos',
                            prazoMobilizacao: '20 dias',
                            garantias: '10 anos para estrutura, 5 anos para instalações, 3 anos para sistemas',
                            estruturaCanteiro: 'Canteiro sustentável, escritório inteligente, área de treinamento',
                            obrigacoesContratada: 'Alimentação orgânica, transporte ecológico, energia limpa',
                            obrigacoesContratante: 'Terreno, licenças ambientais especiais'
                        },
                        servicosTecnica: [
                            { descricao: 'Escavação para fundação', unidade: 'm³', quantidade: 480 },
                            { descricao: 'Concreto estrutural', unidade: 'm³', quantidade: 400 },
                            { descricao: 'Alvenaria de vedação', unidade: 'm²', quantidade: 3000 },
                            { descricao: 'Cobertura metálica', unidade: 'm²', quantidade: 1300 },
                            { descricao: 'Instalações elétricas', unidade: 'ponto', quantidade: 180 }
                        ],
                        maoObraTecnica: [
                            { funcao: 'Engenheiro Civil', quantidade: 2, tempo: 4 },
                            { funcao: 'Mestre de Obras', quantidade: 3, tempo: 4 },
                            { funcao: 'Pedreiro', quantidade: 12, tempo: 4 },
                            { funcao: 'Servente', quantidade: 15, tempo: 4 },
                            { funcao: 'Eletricista', quantidade: 5, tempo: 2 }
                        ],
                        materiaisTecnica: [
                            { material: 'Concreto', especificacao: 'FCK 30 MPa Sustentável', unidade: 'm³', quantidade: 400 },
                            { material: 'Aço CA-50', especificacao: '16mm Reciclado', unidade: 'kg', quantidade: 18000 },
                            { material: 'Bloco cerâmico', especificacao: 'Ecológico 14x19x29cm', unidade: 'und', quantidade: 28000 },
                            { material: 'Telha metálica', especificacao: 'Solar Integrada', unidade: 'm²', quantidade: 1300 }
                        ],
                        equipamentosTecnica: [
                            { equipamento: 'Betoneira', especificacao: '500L Automatizada', unidade: 'und', quantidade: 3, tempo: 3 },
                            { equipamento: 'Guindaste', especificacao: '25t Inteligente', unidade: 'und', quantidade: 1, tempo: 3 },
                            { equipamento: 'Vibrador', especificacao: 'IoT Conectado', unidade: 'und', quantidade: 6, tempo: 3 }
                        ],
                        servicosComercial: [
                            { descricao: 'Escavação para fundação', unidade: 'm³', quantidade: 480, precoUnitario: 35.00, total: 16800 },
                            { descricao: 'Concreto estrutural', unidade: 'm³', quantidade: 400, precoUnitario: 650.00, total: 260000 },
                            { descricao: 'Alvenaria de vedação', unidade: 'm²', quantidade: 3000, precoUnitario: 120.00, total: 360000 },
                            { descricao: 'Cobertura metálica', unidade: 'm²', quantidade: 1300, precoUnitario: 180.00, total: 234000 },
                            { descricao: 'Instalações elétricas', unidade: 'ponto', quantidade: 180, precoUnitario: 450.00, total: 81000 }
                        ],
                        maoObraComercial: [
                            { funcao: 'Engenheiro Civil', quantidade: 2, tempo: 4, salario: 15000, encargos: 85, total: 222000 },
                            { funcao: 'Mestre de Obras', quantidade: 3, tempo: 4, salario: 5500, encargos: 85, total: 122100 },
                            { funcao: 'Pedreiro', quantidade: 12, tempo: 4, salario: 3500, encargos: 85, total: 311200 },
                            { funcao: 'Servente', quantidade: 15, tempo: 4, salario: 2200, encargos: 85, total: 244200 },
                            { funcao: 'Eletricista', quantidade: 5, tempo: 2, salario: 4000, encargos: 85, total: 74000 }
                        ],
                        materiaisComercial: [
                            { material: 'Concreto', especificacao: 'FCK 30 MPa Sustentável', unidade: 'm³', quantidade: 400, precoUnitario: 580.00, total: 232000 },
                            { material: 'Aço CA-50', especificacao: '16mm Reciclado', unidade: 'kg', quantidade: 18000, precoUnitario: 8.50, total: 153000 },
                            { material: 'Bloco cerâmico', especificacao: 'Ecológico 14x19x29cm', unidade: 'und', quantidade: 28000, precoUnitario: 1.80, total: 50400 },
                            { material: 'Telha metálica', especificacao: 'Solar Integrada', unidade: 'm²', quantidade: 1300, precoUnitario: 120.00, total: 156000 }
                        ],
                        equipamentosComercial: [
                            { equipamento: 'Betoneira', especificacao: '500L Automatizada', quantidade: 3, tempo: 3, precoMensal: 2000, total: 18000 },
                            { equipamento: 'Guindaste', especificacao: '25t Inteligente', quantidade: 1, tempo: 3, precoMensal: 12000, total: 36000 },
                            { equipamento: 'Vibrador', especificacao: 'IoT Conectado', quantidade: 6, tempo: 3, precoMensal: 500, total: 9000 }
                        ],
                        bdi: [
                            { item: 'Administração Central', percentual: 10.0, valor: 280000 },
                            { item: 'Seguros e Garantias', percentual: 2.5, valor: 70000 },
                            { item: 'Riscos', percentual: 3.0, valor: 84000 },
                            { item: 'Despesas Financeiras', percentual: 1.5, valor: 42000 },
                            { item: 'Lucro', percentual: 12.0, valor: 336000 },
                            { item: 'Tributos (ISS, PIS, COFINS)', percentual: 8.0, valor: 224000 }
                        ],
                        resumoFinanceiro: {
                            totalServicos: 951800,
                            totalMaoObra: 973500,
                            totalMateriais: 591400,
                            totalEquipamentos: 63000,
                            custoDireto: 2579700,
                            bdiPercentual: 37.0,
                            bdiValor: 1036000,
                            valorTotal: 4200000
                        }
                    }
                ]
            }
        };

        return sampleData[processId] || sampleData['proc_001'];
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.comparativoReal = new ComparativoPropostasReal();
});

