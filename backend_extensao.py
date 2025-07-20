# ===== EXTENSÃO DO BACKEND - NOVOS ENDPOINTS =====
# Este arquivo contém apenas os novos endpoints para os módulos TR
# Para integrar: copiar e colar no FINAL do backend_propostas.py

import os
import json
from datetime import datetime
from flask import jsonify, request

# ===== NOVOS ENDPOINTS PARA MÓDULOS ADICIONAIS =====

@app.route('/api/trs', methods=['GET'])
def listar_trs():
    """Listar Termos de Referência"""
    try:
        # Carregar TRs de arquivo JSON
        trs_file = 'data/trs.json'
        if os.path.exists(trs_file):
            with open(trs_file, 'r', encoding='utf-8') as f:
                trs = json.load(f)
        else:
            trs = []
        
        # Filtrar por usuário se especificado
        user_id = request.args.get('user_id')
        if user_id:
            trs = [tr for tr in trs if tr.get('criado_por') == user_id]
        
        return jsonify({'success': True, 'trs': trs, 'total': len(trs)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trs', methods=['POST'])
def criar_tr():
    """Criar novo Termo de Referência"""
    try:
        data = request.get_json()
        
        # Carregar TRs existentes
        trs_file = 'data/trs.json'
        if os.path.exists(trs_file):
            with open(trs_file, 'r', encoding='utf-8') as f:
                trs = json.load(f)
        else:
            trs = []
        
        # Criar novo TR
        novo_tr = {
            'id': f"TR-{len(trs) + 1:03d}",
            'titulo': data.get('titulo', ''),
            'objetivo': data.get('objetivo', ''),
            'situacao_atual': data.get('situacao_atual', ''),
            'problemas': data.get('problemas', ''),
            'necessidades': data.get('necessidades', ''),
            'modalidade': data.get('modalidade', 'concorrencia'),
            'especificacoes': data.get('especificacoes', ''),
            'normas': data.get('normas', ''),
            'prazo_execucao': data.get('prazo_execucao', 0),
            'prazo_garantia': data.get('prazo_garantia', 0),
            'servicos': data.get('servicos', []),
            'criado_por': data.get('criado_por', 'sistema'),
            'criado_em': datetime.now().isoformat(),
            'atualizado_em': datetime.now().isoformat(),
            'status': data.get('status', 'rascunho')
        }
        
        trs.append(novo_tr)
        
        # Salvar TRs
        os.makedirs('data', exist_ok=True)
        with open(trs_file, 'w', encoding='utf-8') as f:
            json.dump(trs, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'tr': novo_tr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trs/<tr_id>', methods=['GET'])
def obter_tr(tr_id):
    """Obter TR específico"""
    try:
        trs_file = 'data/trs.json'
        if os.path.exists(trs_file):
            with open(trs_file, 'r', encoding='utf-8') as f:
                trs = json.load(f)
            
            tr = next((t for t in trs if t['id'] == tr_id), None)
            if tr:
                return jsonify({'success': True, 'tr': tr})
            else:
                return jsonify({'success': False, 'error': 'TR não encontrado'})
        else:
            return jsonify({'success': False, 'error': 'Nenhum TR encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trs/<tr_id>', methods=['PUT'])
def atualizar_tr(tr_id):
    """Atualizar TR existente"""
    try:
        data = request.get_json()
        
        trs_file = 'data/trs.json'
        if os.path.exists(trs_file):
            with open(trs_file, 'r', encoding='utf-8') as f:
                trs = json.load(f)
        else:
            return jsonify({'success': False, 'error': 'TR não encontrado'})
        
        # Encontrar e atualizar TR
        for i, tr in enumerate(trs):
            if tr['id'] == tr_id:
                # Manter dados originais
                trs[i].update({
                    'titulo': data.get('titulo', tr['titulo']),
                    'objetivo': data.get('objetivo', tr['objetivo']),
                    'situacao_atual': data.get('situacao_atual', tr['situacao_atual']),
                    'problemas': data.get('problemas', tr.get('problemas', '')),
                    'necessidades': data.get('necessidades', tr.get('necessidades', '')),
                    'modalidade': data.get('modalidade', tr.get('modalidade', 'concorrencia')),
                    'especificacoes': data.get('especificacoes', tr.get('especificacoes', '')),
                    'normas': data.get('normas', tr.get('normas', '')),
                    'prazo_execucao': data.get('prazo_execucao', tr.get('prazo_execucao', 0)),
                    'prazo_garantia': data.get('prazo_garantia', tr.get('prazo_garantia', 0)),
                    'servicos': data.get('servicos', tr.get('servicos', [])),
                    'status': data.get('status', tr['status']),
                    'atualizado_em': datetime.now().isoformat()
                })
                
                # Salvar alterações
                with open(trs_file, 'w', encoding='utf-8') as f:
                    json.dump(trs, f, ensure_ascii=False, indent=2)
                
                return jsonify({'success': True, 'tr': trs[i]})
        
        return jsonify({'success': False, 'error': 'TR não encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trs/<tr_id>', methods=['DELETE'])
def excluir_tr(tr_id):
    """Excluir TR"""
    try:
        trs_file = 'data/trs.json'
        if os.path.exists(trs_file):
            with open(trs_file, 'r', encoding='utf-8') as f:
                trs = json.load(f)
        else:
            return jsonify({'success': False, 'error': 'TR não encontrado'})
        
        # Encontrar e remover TR
        trs_filtrados = [tr for tr in trs if tr['id'] != tr_id]
        
        if len(trs_filtrados) < len(trs):
            # TR foi removido
            with open(trs_file, 'w', encoding='utf-8') as f:
                json.dump(trs_filtrados, f, ensure_ascii=False, indent=2)
            
            return jsonify({'success': True, 'message': 'TR excluído com sucesso'})
        else:
            return jsonify({'success': False, 'error': 'TR não encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/requisitante/<user_id>')
def dashboard_requisitante(user_id):
    """Dashboard específico para requisitante"""
    try:
        # Carregar dados dos TRs
        trs_file = 'data/trs.json'
        if os.path.exists(trs_file):
            with open(trs_file, 'r', encoding='utf-8') as f:
                trs = json.load(f)
        else:
            trs = []
        
        # Filtrar TRs do usuário
        meus_trs = [tr for tr in trs if tr.get('criado_por') == user_id]
        trs_aprovados = [tr for tr in meus_trs if tr.get('status') == 'aprovado']
        
        # Simular dados de propostas em análise
        propostas_analise = 2
        pareceres_pendentes = 1
        
        dados = {
            'meus_trs': len(meus_trs),
            'trs_aprovados': len(trs_aprovados),
            'propostas_analise': propostas_analise,
            'pareceres_pendentes': pareceres_pendentes,
            'trs_recentes': meus_trs[-5:] if meus_trs else []
        }
        
        return jsonify({'success': True, 'dados': dados})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/comprador/<user_id>')
def dashboard_comprador(user_id):
    """Dashboard específico para comprador"""
    try:
        # Carregar dados dos TRs
        trs_file = 'data/trs.json'
        if os.path.exists(trs_file):
            with open(trs_file, 'r', encoding='utf-8') as f:
                trs = json.load(f)
        else:
            trs = []
        
        # Simular dados do comprador
        trs_pendentes = len([tr for tr in trs if tr.get('status') == 'analise'])
        concorrencias_ativas = 2
        propostas_recebidas = 8
        valor_total = 1250000
        
        dados = {
            'trs_pendentes': trs_pendentes,
            'concorrencias_ativas': concorrencias_ativas,
            'propostas_recebidas': propostas_recebidas,
            'valor_total': valor_total,
            'trs_para_analise': [tr for tr in trs if tr.get('status') in ['rascunho', 'analise']]
        }
        
        return jsonify({'success': True, 'dados': dados})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/propostas/tecnicas', methods=['GET'])
def listar_propostas_tecnicas():
    """Listar propostas técnicas (sem valores comerciais)"""
    try:
        # Simular dados de propostas técnicas
        propostas_tecnicas = [
            {
                'id': 'PROP-001',
                'fornecedor': 'Construtora ABC Ltda',
                'tr_id': 'TR-001',
                'metodologia': 'Metodologia construtiva com técnicas modernas...',
                'cronograma': '120 dias',
                'equipe_tecnica': 'Eng. João Silva (CREA 12345) + equipe de 15 profissionais',
                'experiencia': '10 obras similares nos últimos 5 anos',
                'certificacoes': 'ISO 9001, ISO 14001',
                'recebida_em': datetime.now().isoformat(),
                'status': 'analise_tecnica'
            },
            {
                'id': 'PROP-002',
                'fornecedor': 'Engenharia XYZ S.A.',
                'tr_id': 'TR-001',
                'metodologia': 'Abordagem sustentável com materiais eco-friendly...',
                'cronograma': '90 dias',
                'equipe_tecnica': 'Eng. Maria Santos (CREA 67890) + equipe especializada',
                'experiencia': '15 obras similares, incluindo projetos governamentais',
                'certificacoes': 'ISO 9001, PBQP-H',
                'recebida_em': datetime.now().isoformat(),
                'status': 'analise_tecnica'
            }
        ]
        
        return jsonify({'success': True, 'propostas': propostas_tecnicas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/propostas/<proposta_id>/parecer', methods=['POST'])
def emitir_parecer_tecnico(proposta_id):
    """Emitir parecer técnico sobre proposta"""
    try:
        data = request.get_json()
        
        parecer = {
            'id': f"PARECER-{proposta_id}",
            'proposta_id': proposta_id,
            'avaliacao_metodologia': data.get('avaliacao_metodologia', ''),
            'avaliacao_cronograma': data.get('avaliacao_cronograma', ''),
            'avaliacao_equipe': data.get('avaliacao_equipe', ''),
            'pontos_positivos': data.get('pontos_positivos', ''),
            'pontos_negativos': data.get('pontos_negativos', ''),
            'recomendacao': data.get('recomendacao', ''),  # aprovado/rejeitado/condicional
            'observacoes': data.get('observacoes', ''),
            'emitido_por': data.get('emitido_por', 'requisitante'),
            'emitido_em': datetime.now().isoformat()
        }
        
        # Salvar parecer
        pareceres_file = 'data/pareceres.json'
        if os.path.exists(pareceres_file):
            with open(pareceres_file, 'r', encoding='utf-8') as f:
                pareceres = json.load(f)
        else:
            pareceres = []
        
        pareceres.append(parecer)
        
        os.makedirs('data', exist_ok=True)
        with open(pareceres_file, 'w', encoding='utf-8') as f:
            json.dump(pareceres, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'parecer': parecer})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pareceres', methods=['GET'])
def listar_pareceres():
    """Listar pareceres técnicos"""
    try:
        pareceres_file = 'data/pareceres.json'
        if os.path.exists(pareceres_file):
            with open(pareceres_file, 'r', encoding='utf-8') as f:
                pareceres = json.load(f)
        else:
            pareceres = []
        
        # Filtrar por usuário se especificado
        user_id = request.args.get('user_id')
        if user_id:
            pareceres = [p for p in pareceres if p.get('emitido_por') == user_id]
        
        return jsonify({'success': True, 'pareceres': pareceres})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/concorrencias', methods=['GET'])
def listar_concorrencias():
    """Listar concorrências ativas"""
    try:
        # Simular dados de concorrências
        concorrencias = [
            {
                'id': 'CONC-001',
                'numero': '001/2025',
                'objeto': 'Reforma do Centro de Saúde Municipal',
                'modalidade': 'Concorrência',
                'valor_estimado': 850000.00,
                'prazo_proposta': '2025-02-15',
                'dias_restantes': 15,
                'status': 'aberta',
                'tr_id': 'TR-001'
            },
            {
                'id': 'CONC-002',
                'numero': '002/2025',
                'objeto': 'Construção de Quadra Poliesportiva',
                'modalidade': 'Tomada de Preços',
                'valor_estimado': 450000.00,
                'prazo_proposta': '2025-02-20',
                'dias_restantes': 20,
                'status': 'aberta',
                'tr_id': 'TR-002'
            },
            {
                'id': 'CONC-003',
                'numero': '003/2025',
                'objeto': 'Pavimentação de Ruas do Bairro Centro',
                'modalidade': 'Concorrência',
                'valor_estimado': 1200000.00,
                'prazo_proposta': '2025-02-25',
                'dias_restantes': 25,
                'status': 'aberta',
                'tr_id': 'TR-003'
            }
        ]
        
        return jsonify({'success': True, 'concorrencias': concorrencias})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/inicializar-dados', methods=['POST'])
def inicializar_dados_exemplo():
    """Inicializar dados de exemplo para demonstração"""
    try:
        # Criar diretório de dados
        os.makedirs('data', exist_ok=True)
        
        # TRs de exemplo
        trs_exemplo = [
            {
                'id': 'TR-001',
                'titulo': 'Reforma do Centro de Saúde Municipal',
                'objetivo': 'Reforma completa das instalações do Centro de Saúde para melhorar o atendimento à população',
                'situacao_atual': 'Instalações antigas com necessidade de modernização',
                'modalidade': 'concorrencia',
                'servicos': [
                    {'item': 1, 'descricao': 'Demolição de paredes internas', 'unidade': 'm²', 'quantidade': 150},
                    {'item': 2, 'descricao': 'Construção de novas paredes', 'unidade': 'm²', 'quantidade': 200},
                    {'item': 3, 'descricao': 'Instalação elétrica completa', 'unidade': 'vb', 'quantidade': 1}
                ],
                'criado_por': 'requisitante1',
                'criado_em': datetime.now().isoformat(),
                'status': 'aprovado'
            },
            {
                'id': 'TR-002',
                'titulo': 'Construção de Quadra Poliesportiva',
                'objetivo': 'Construção de quadra poliesportiva coberta para atividades esportivas da comunidade',
                'situacao_atual': 'Terreno disponível, necessidade de espaço esportivo',
                'modalidade': 'tomada_precos',
                'servicos': [
                    {'item': 1, 'descricao': 'Terraplanagem e fundação', 'unidade': 'm²', 'quantidade': 800},
                    {'item': 2, 'descricao': 'Estrutura metálica da cobertura', 'unidade': 'm²', 'quantidade': 600},
                    {'item': 3, 'descricao': 'Piso esportivo', 'unidade': 'm²', 'quantidade': 600}
                ],
                'criado_por': 'requisitante1',
                'criado_em': datetime.now().isoformat(),
                'status': 'analise'
            }
        ]
        
        # Salvar TRs
        with open('data/trs.json', 'w', encoding='utf-8') as f:
            json.dump(trs_exemplo, f, ensure_ascii=False, indent=2)
        
        # Pareceres de exemplo
        pareceres_exemplo = []
        with open('data/pareceres.json', 'w', encoding='utf-8') as f:
            json.dump(pareceres_exemplo, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': 'Dados de exemplo inicializados'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===== FIM DOS NOVOS ENDPOINTS =====

