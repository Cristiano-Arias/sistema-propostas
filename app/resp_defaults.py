# Fixed items + 4 extra rows
FIXED_RESP_ITEMS = [
    ("alvara_construcao", "Alvará de construção das obras"),
    ("licenciamento_obras", "Licenciamento das obras"),
    ("memorial_projetos", "Disponibilização de memorial descritivo e projetos detalhados"),
    ("habite_se", "Certificado de Vistoria e Conclusão de Obras - HABITE-SE"),
    ("alvara_art_no_canteiro", "O alvará, o projeto aprovado e as ARTs permanecerão no local da obra, mantidos em perfeito estado de conservação"),
    ("alimentacao_refeitorio", "Alimentação / Refeitório"),
    ("exames_admissionais", "Exames Admissionais dos funcionários"),
    ("ferramentas", "Ferramentas necessárias para a realização das atividades"),
    ("uniformes", "Uniformes padrão para funcionários"),
    ("epi_epc", "EPI e EPC para funcionários"),
    ("materiais_consumo", "Materiais de consumo diversos (escritório e limpeza)"),
    ("transporte_obra", "Transporte até a obra"),
    ("canteiro_salas", "Canteiro de Obras/Salas"),
    ("insumos_diversos", "Insumos diversos"),
    ("energia_eletrica", "Fornecimento de energia elétrica"),
    ("agua_potavel", "Fornecimento de água potável"),
    ("telefonia", "Telefonia"),
    ("instalacoes_sanitarias", "Instalações sanitárias"),
    ("primeiros_socorros", "Ponto de atendimento de primeiros socorros para acidentados"),
    ("sinalizacao_seg", "Comunicação visual e sinalização de segurança"),
    ("placa_obra", "Placa da Obra"),
    ("limpeza_canteiro", "Manter a ordem, arrumação e limpeza do canteiro de obras"),
    ("integracao", "Integração"),
    ("treinamentos_diversos", "Treinamentos Diversos"),
    ("dds_dss", "Diálogo de saúde e segurança ocupacional - DSS"),
]

def default_responsibility_matrix():
    rows = []
    for key, label in FIXED_RESP_ITEMS:
        rows.append({
            "key": key,
            "label": label,
            "aplicavel": None,
            "responsavel": None,
            "observacoes": "",
            "anexos": []
        })
    for i in range(1, 5):
        rows.append({
            "key": f"extra_{i}",
            "label": f"Extra {i}",
            "aplicavel": None,
            "responsavel": None,
            "observacoes": "",
            "anexos": [],
            "livre": True
        })
    return rows
