# -*- coding: utf-8 -*-
import json

W = "/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado"

decisoes_raw = json.load(open(f'{W}/analise/tmp_munck/decisoes_completas.json'))
resumo = json.load(open(f'{W}/analise/tmp_munck/resumo_v2.json'))

casos = {}
with open(f'{W}/analise/casos.jsonl') as f:
    for line in f:
        c = json.loads(line)
        if c['id'] in decisoes_raw:
            casos[c['id']] = c
assert len(casos) == 46

decisoes = []
for cid, (incluido, motivo, justificativa) in decisoes_raw.items():
    decisoes.append({
        "id": cid, "escopo": casos[cid]['escopo'], "link": casos[cid].get('link_pncp'),
        "incluido": incluido, "motivo": motivo, "justificativa": justificativa,
    })
decisoes.sort(key=lambda d: (d['escopo']!='GO', d['escopo'], d['id']))

indicadores = {
 "go": {
   "n_casos_total": resumo['GO']['n_total'], "n_incluidos": resumo['GO']['n_incluidos'], "n_excluidos": resumo['GO']['n_excluidos'],
   "valor_estimado_total": round(resumo['GO']['valor_estimado_total'],2), "valor_homologado_total": round(resumo['GO']['valor_homologado_total'],2),
   "ticket_mediano_estimado": round(resumo['GO']['ticket_mediano'],2), "n_amostra_ticket": resumo['GO']['n_ticket'],
   "desconto_mediana": round(resumo['GO']['desconto_mediana'],4), "desconto_q1": round(resumo['GO']['desconto_q1'],4), "desconto_q3": round(resumo['GO']['desconto_q3'],4),
   "n_amostra_desconto": resumo['GO']['n_desconto'], "descontos_suspeitos_descartados": resumo['GO']['descontos_suspeitos'],
   "pct_deserta_ou_fracassada": resumo['GO']['pct_deserta'], "pct_exclusiva_meepp_total": resumo['GO']['pct_meepp_total'], "pct_exclusiva_meepp_parcial": resumo['GO']['pct_meepp_parcial'],
   "pct_continuado": resumo['GO']['pct_continuado'], "pct_pontual": resumo['GO']['pct_pontual'], "pct_indefinido": resumo['GO']['pct_indefinido'],
   "exclusoes_por_motivo": {"fornecimento_puro": 2, "fora_escopo": 3},
   "nota_metodologia_desconto": "Igual ao relatorio anterior: nos casos de GO (majoritariamente 1 item por processo), o novo metodo de desconto (por preco unitario do 1o colocado, ponderado pelo valor de cada item) produz os MESMOS valores do metodo antigo (diferenca maxima observada: 3e-16, ruido de ponto flutuante) -- nenhuma estatistica de GO mudou.",
 },
 "vizinhos": {
   "n_casos_total": resumo['vizinhos']['n_total'], "n_incluidos": resumo['vizinhos']['n_incluidos'], "n_excluidos": resumo['vizinhos']['n_excluidos'],
   "valor_estimado_total": round(resumo['vizinhos']['valor_estimado_total'],2), "valor_homologado_total": round(resumo['vizinhos']['valor_homologado_total'],2),
   "ticket_mediano_estimado": round(resumo['vizinhos']['ticket_mediano'],2), "n_amostra_ticket": resumo['vizinhos']['n_ticket'],
   "desconto_mediana": round(resumo['vizinhos']['desconto_mediana'],4), "desconto_q1": round(resumo['vizinhos']['desconto_q1'],4), "desconto_q3": round(resumo['vizinhos']['desconto_q3'],4),
   "n_amostra_desconto": resumo['vizinhos']['n_desconto'], "descontos_suspeitos_descartados": resumo['vizinhos']['descontos_suspeitos'],
   "pct_deserta_ou_fracassada": resumo['vizinhos']['pct_deserta'], "pct_exclusiva_meepp_total": resumo['vizinhos']['pct_meepp_total'], "pct_exclusiva_meepp_parcial": resumo['vizinhos']['pct_meepp_parcial'],
   "pct_continuado": resumo['vizinhos']['pct_continuado'], "pct_pontual": resumo['vizinhos']['pct_pontual'], "pct_indefinido": resumo['vizinhos']['pct_indefinido'],
   "exclusoes_por_motivo": {"fora_escopo": 7, "obra_grande": 1, "fornecimento_puro": 7, "equipamento_alto": 1},
   "alerta_leitura": "Vizinhos agora inclui DF+MT+MS+MG+TO (antes so DF+MT). Amostra de vizinhos incluidos saltou de 6 para 13 casos apos a recoleta (novos casos de MS/MG/TO). Ainda ha RPs multi-servico (frota mista) em que o munck e so 1 de varios itens (Sapezal-129, Juina-DAES, Tres Pontas-SAAE-MG); o ticket mediano de vizinhos (R$237.792) ficou mais proximo de GO que na rodada anterior, mas ainda mistura munck puro com obras pequenas de implantacao de postes -- ver precos_hora para os valores unitarios reais.",
 },
 "observacao_n_participantes": "O PNCP nao publica esse numero; ficou null em todos os 46 casos de munck.",
}

precos_hora = {
 "referencias_mercado": {
   "goinfra_go_t334_fev2026": {"valor": 213.33, "unidade": "R$/hora", "fonte": "GOINFRA Tabela 334, fev/2026, codigo 072080"},
   "sicro_e9690_cesto": {"valor": 330.89, "unidade": "R$/hora", "fonte": "SICRO/DNIT via buscadorsicro.com.br"},
   "sicro_e9686_sem_cesto": {"valor": 352.92, "unidade": "R$/hora", "fonte": "SICRO/DNIT"},
 },
 "go": {
   "hora_produtiva_operando": {"valores_vencedor": [180.00, 295.00, 405.63], "mediana": 295.00, "min": 180.00, "max": 405.63, "n": 3,
     "casos": ["Corumbaiba (R$180,00/h)", "Mineiros-SAAE (R$295,00/h)", "Santa Fe de Goias (guindauto+cesto SICRO E9690, hora produtiva/CHP, R$405,63/h -- confirmado no texto: planilha cita 'E9690 SICRO...CHP 360 R$405,63')"]},
   "hora_improdutiva_deslocamento": {"valores_vencedor": [168.35], "n": 1, "caso": "Santa Fe de Goias, hora improdutiva/CHI (41% da CHP do mesmo edital, mesma fonte SICRO E9690)"},
   "diaria_sem_operador": {"valores_vencedor": [645.00], "n": 1, "caso": "Tres Ranchos"},
   "mensal": {"valores_vencedor": [23530.00, 23590.00, 15747.22, 10275.00, 7561.00, 9490.00, 12000.00], "mediana": 12000.00, "q1": 9882.50, "q3": 19638.61, "n": 7,
     "casos": ["Goianesia (2 caminhoes)", "Itaguaru", "Silvania", "Pontalina", "Itapirapua", "Itaguari"]},
   "observacao": "Sem alteracao em relacao a rodada anterior -- GO nao recebeu casos novos na recoleta.",
 },
 "vizinhos": {
   "hora_produtiva_operando": {
     "valores_vencedor": [222.46, 222.46, 228.49, 288.00, 340.00, 390.00, 390.00, 429.00],
     "mediana": 314.00, "q1": 226.98, "q3": 390.00, "min": 222.46, "max": 429.00, "n": 8,
     "casos": [
       "Nova Santa Helena-MT: cesto aereo linha viva (R$222,46/h) e munck 8t c/ eletricista (R$222,46/h)",
       "Alvorada-TO: munck+cesto isolado com motorista (R$228,49/h, 983h -- maior volume de horas da amostra)",
       "Tres Pontas-SAAE-MG: item de munck dentro de RP de frota mista (R$288,00/h)",
       "Sapezal-171-MT: munck+cesto isolado com operador (R$340,00/h)",
       "Sao Lourenco-MG: munck de GRANDE porte 45 t/m, lanca 20m (R$390,00/h, 2 itens: ampla concorrencia + cota ME/EPP, mesmo preco)",
       "Deodapolis-MS: munck/guindauto 15 toneladas (R$429,00/h -- maior capacidade e maior preco da amostra)",
     ],
     "nota": "Amostra saltou de n=3 (rodada anterior) para n=8 com a recoleta (novos casos de MS/MG/TO). A mediana subiu de R$222,46/h para R$314,00/h -- ver secao 'o que mudou' no relatorio.",
     "outlier_descartado": {"valor": 64.00, "caso": "Juina-DAES/MT (desconto de 85%, economicamente inviavel)"},
     "desertos_sem_vencedor": {"caso": "Sapezal-129-MT: 2 itens de munck ficaram sem vencedor"},
   },
   "mensal": {"valores_vencedor": [34333.33], "n": 1, "caso": "Poxoreu-MT"},
   "por_operacao_icamento_unico": {"valores_vencedor": [6900.00, 7300.00, 8866.85], "mediana": 7300.00, "n": 3, "caso": "Aeronautica-DF"},
 },
 "observacao_geral": "Amostra pequena em todas as quebras -- tratar medianas como ordem de grandeza. A mediana de 'hora produtiva' de vizinhos (R$314/h, n=8) ficou 47% acima do GOINFRA (R$213,33/h) e 95% do SICRO-cesto (R$330,89/h) -- mais alta que a de GO (R$295/h, 38% acima do GOINFRA). Isso sugere que fora de GO (onde a referencia publica GOINFRA parece ancorar os precos) os municipios pagam um premio maior pelo munck.",
}

with open(f'{W}/analise/tmp_munck/precos_hora.json','w') as f: json.dump(precos_hora, f, ensure_ascii=False, indent=1)
with open(f'{W}/analise/tmp_munck/indicadores.json','w') as f: json.dump(indicadores, f, ensure_ascii=False, indent=1)
with open(f'{W}/analise/tmp_munck/decisoes.json','w') as f: json.dump(decisoes, f, ensure_ascii=False, indent=1)
print("OK", len(decisoes))
