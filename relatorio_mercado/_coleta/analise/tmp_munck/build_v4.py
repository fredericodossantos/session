# -*- coding: utf-8 -*-
import json
W = "/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado"

exemplares = [
 {"id": "01065846000172_2026_584","link": "https://pncp.gov.br/app/editais/01065846000172/2026/584","municipio": "Goianésia","resumo": "RP para 2 caminhões munck+cesto (idade mín. ≥2000); maior desconto observado em GO (59,5%). Texto do edital (agora disponível) confirma exigência de motorista categoria D + eletricista com NR35/NR12/NR10/SEP e altura de trabalho mínima de 13,5 m."},
 {"id": "01302603000100_2026_110","link": "https://pncp.gov.br/app/editais/01302603000100/2026/110","municipio": "Corumbaíba","resumo": "Locação por hora com motorista e cesto hidráulico, 1.000h estimadas; R$194,58/h → R$180,00/h homologado (7% desconto). Combustível por conta da contratada, já incluso no preço (mão de obra do operador e combustível no mesmo item)."},
 {"id": "25107517000105_2025_304","link": "https://pncp.gov.br/app/editais/25107517000105/2025/304","municipio": "Santa Fé de Goiás","resumo": "Guindauto+cesto (referência SICRO E9690, 10t/136kW) com operador, 2 itens: 'CHP' hora produtiva (R$405,63/h) e 'CHI' hora improdutiva (R$168,35/h = 41% da CHP) -- confirmado no próprio texto do edital, que cita a planilha SICRO literalmente."},
 {"id": "01612817000183_2025_830","link": "https://pncp.gov.br/app/editais/01612817000183/2025/830","municipio": "Vila Propício","resumo": "Pequena obra (R$140.520,31, abaixo do limiar de obra grande) de implantação de iluminação com substituição de postes. Texto confirma exigência de registro CREA/CAU para empresas de fora de GO -- único caso munck com exigência de CREA/CFT explícita."},
 {"id": "01068030000100_2026_205","link": "https://pncp.gov.br/app/editais/01068030000100/2026/205","municipio": "Silvânia","resumo": "RP com 2 itens/vencedores distintos: cesto aéreo 10t (relevante, R$10.275,00/mês homologado) + caminhão coletor de lixo (ruído) -- mostra como disputar só o item pertinente dentro de um edital misto."},
]

premissas_custo = {
 "mao_de_obra": {"piso_motorista_operador_munck_rs_mes": 1870.00, "fonte": "CCT SETCEG/Sindicato dos Motoristas-GO, carga 2026/2028", "encargos_sociais_mensalista_pct": 0.6928, "fonte_encargos": "SINAPI GO mensalista sem desoneração, vigência 01/2026", "vale_alimentacao_rs_mes": 495.88, "epi_uniforme_ferramentas_rs_mes": 150.00, "custo_mensal_por_operador": 3811.42, "memoria_calculo": "1.870,00 x (1+0,6928) + 495,88 + 150,00 = R$ 3.811,42/mês", "limitacao": "não há piso próprio de 'operador de munck' em GO; usa-se o piso genérico de motorista (SETCEG)."},
 "diesel": {"preco_s10_go_rs_litro": 7.232, "fonte_preco": "ANP, revenda GO, semana 20-26/09/2026", "consumo_operacao_l_h": 22.37, "fonte_consumo_operacao": "SINAPI 91633 (guindauto hidráulico 6,5t), componente 'materiais na operação'", "consumo_deslocamento_km_l": 3.0, "custo_operacao_rs_h": 161.76, "custo_deslocamento_rs_h": 84.61, "premissa_blend": "40% operação intensiva / 60% deslocamento-espera para uma 'hora genérica' (premissa do analista, inspirada na proporção CHP/CHI de Santa Fé de Goiás)", "custo_blended_rs_h": 115.47, "sensibilidade": "±25% no consumo muda o custo blended em ~±29 R$/h."},
 "manutencao_pneus_rs_h": {"valor": 26.39, "premissa": "estimativa: ~10%/ano do valor do bem (R$380.000) ÷ 120h/mês."},
 "seguro_licenciamento_rs_h": {"valor": 7.71, "premissa": "estimativa: ~2%/ano do valor do bem + licenciamento ÷ 120h/mês."},
 "depreciacao_rs_h": {"valor": 26.39, "valor_munck_usado_rs": 380000.00, "fonte_valor_usado": "busca de mercado (WebSearch 27/09/2026): anúncios de munck usado ~10t entre ~R$269 mil e ~R$420 mil (Mercado Livre, MF Rural, Trucadão, Mercado Máquinas).", "premissa": "base depreciável R$304.000 (80% de R$380 mil) ÷ 96 meses ÷ 120h/mês."},
 "base_de_horas_para_custos_fixos_por_hora": {"valor_h_mes": 120, "nota": "quando o edital declara jornada explícita (~176h/mês), os custos fixos foram reamortizados sobre essa base (ex.: Poxoréu na tabela de margem)."},
 "bdi": {"formula": "BDI = [(1+AC+S+G+R)(1+DF)(1+L)/(1-T)] - 1, Acórdão TCU 2622/2013", "composicao_usada": "Construção de Edifícios: AC 4,00%; S+G 0,80%; R 1,27%; DF 1,23%; L 7,40%; T 8,65%", "bdi_com_lucro_pct": 26.26, "bdi_lucro_zero_pct": 17.54},
 "classificacao_regra": "folgado: preço vencedor >= preço com BDI; apertado: entre lucro zero e preço com BDI; prejuízo provável: abaixo do lucro zero.",
 "nota_atualizacao": "Premissas de custo NÃO foram alteradas nesta atualização -- só o campo `desconto` do casos.jsonl mudou de definição, e não afetou nenhum valor de munck (ver indicadores.go.nota_metodologia_desconto). Os 3 novos casos de margem (Alvorada-TO, São Lourenço-MG, Deodápolis-MS) usam o MESMO modelo de custo do munck médio (8-12t); para os 2 últimos (munck de maior porte), isso provavelmente SUBESTIMA o custo real -- ver observação em cada linha de margem.",
}

investimento = json.load(open('/tmp/munck_build/investimento.json'))

regras_lance = [
 "Piso de hora quando o COMBUSTÍVEL é por conta da CONTRATADA (cenário mais comum): não ofertar abaixo de ~R$220/h (preço de lucro zero R$219,55/h); Corumbaíba (R$180/h) e, de forma mais marginal, Alvorada-TO (R$228,49/h, 'apertado') ilustram os riscos nessa faixa.",
 "Piso de hora quando o COMBUSTÍVEL é por conta do CONTRATANTE/MUNICÍPIO (confirmado em Goianésia-GO e Poxoréu-MT): custo direto cai para ~R$71/h, preço com BDI ~R$90/h -- muito mais espaço para descontos agressivos. SEMPRE checar essa cláusula antes de formar o preço.",
 "ATUALIZAÇÃO (recoleta com MS/MG/TO): a mediana da hora 'produtiva' fora de GO subiu de R$222,46/h (n=3) para R$314,00/h (n=8) com a chegada de casos de munck de maior capacidade (15t em Deodápolis-MS a R$429/h; 45 t/m em São Lourenço-MG a R$390/h). Ou seja, quanto maior a capacidade do munck exigida no edital, maior o preço/hora -- óbvio, mas agora confirmado com dado: a empresa deve informar a capacidade real dos seus 2 caminhões e mirar editais compatíveis, não necessariamente os de maior capacidade (que pagam mais/hora mas também exigem equipamento mais caro e provavelmente fora da frota atual).",
 "Desconto típico: GO mediana 14,0% [Q1 5,1%; Q3 42,5%] (n=12, sem alteração); vizinhos mediana 7,7% [Q1 3,0%; Q3 12,2%] (n=13, amostra maior e mais conservadora que a rodada anterior). Evitar descontos acima do 3º quartil de GO (~42%).",
 "Franquia mínima de horas: GOINFRA exige mín. de 4h/dia por chamado; jornadas contratuais observadas vão de 44h/semana (Goianésia) a 'até 8h/dia' (Poxoréu). Alvorada-TO tem franquia bem maior (983h no RP) -- pode justificar preço unitário menor por diluir custo fixo.",
 "Diária 'sem operador' (Três Ranchos, R$645/diária): o município fornece o motorista -- não computar mão de obra, mas confirmar quem paga o diesel.",
 "Preços 'hora produtiva' x 'hora improdutiva/deslocamento' (Santa Fé de Goiás, confirmado no texto como referência SICRO E9690 CHP/CHI): a hora improdutiva deve cobrir ao menos o custo de deslocamento (~R$156/h no modelo).",
 "Itens dentro de frotas mistas (Sapezal, Poxoréu, Juína-DAES em MT; Três Pontas-SAAE em MG): como os itens têm vencedor e preço próprios, é possível ofertar só no item de munck.",
]

exigencias = [
 {"tipo": "Capacidade de carga do munck (8-15 t nos casos médios, até 45 t/m nos de grande porte)", "recorrencia": "confirmado em todos os editais com item de munck detalhado", "evidencia": "Poxoréu: 'capacidade de carga mínima de 10 toneladas, lança...21,8m/18,8m'; Deodápolis-MS: 15 toneladas; São Lourenço-MG: 45 t/m, lança 20m, caminhão 3 eixos, PBT 23t (maior porte da amostra)."},
 {"tipo": "Altura de trabalho do cesto (quando aplicável)", "recorrencia": "confirmado no texto de Goianésia", "evidencia": "Goianésia (texto do edital, agora disponível): 'cesto aéreo com altura de trabalho de no mínimo 13,5 m'."},
 {"tipo": "Idade máx./ano de fabricação (varia muito por município)", "recorrencia": "4+ editais", "evidencia": "Goianésia: ano ≥2000; Silvânia: ano ≥2015; Poxoréu: ano ≥2010 (item munck)."},
 {"tipo": "NR-11/NR-12 (movimentação de cargas / segurança em máquinas)", "recorrencia": "3+ editais lidos integralmente", "evidencia": "Mineiros: 'curso de operador Munck – de acordo com a NR 11...e NR 12'; Poxoréu: idem + NR-06, NR-07, NR-01."},
 {"tipo": "NR-10/NR-35/NR-12 + SEP para o ELETRICISTA (não só o motorista)", "recorrencia": "confirmado no texto de Goianésia", "evidencia": "Goianésia (texto do edital): 'motorista devidamente habilitado categoria D e eletricista portador de certificações em NR35, NR12 e NR10 e SEP' -- ou seja, em contratos que envolvem troca de luminária/rede energizada, o edital pode exigir um SEGUNDO profissional (eletricista certificado), além do motorista/operador."},
 {"tipo": "CNH categoria compatível (C/D/E) + curso/qualificação de operador", "recorrencia": "todos os editais lidos", "evidencia": "Corumbaíba: CNH C/D/E; Santa Fé de Goiás (texto): 'operador devidamente habilitado e treinado, com comprovação de qualificação técnica para operação do cesto aéreo'."},
 {"tipo": "CREA/CFT (Conselho de Engenharia)", "recorrencia": "1 caso confirmado -- só quando o objeto é uma OBRA (não locação pura)", "evidencia": "Vila Propício (texto do edital): empresa de fora de GO 'deverá apresentar Certidão de Registro junto ao CREA...ou CAU'. Não aparece nos casos de locação pura de munck por hora/mês."},
 {"tipo": "Documentação do veículo (CRLV, seguro/apólice)", "recorrencia": "4+ editais", "evidencia": "Goianésia: CRLV + apólice de seguro vigente; Poxoréu: idem + CTB/CONTRAN."},
 {"tipo": "Responsabilidade pelo combustível -- VARIÁVEL por edital (achado central)", "recorrencia": "confirmado em 6 editais: 4 contratada, 2 contratante/município", "evidencia": "ver seção de margem; muda o custo direto por hora em mais de 50%. Para os 19 casos novos (MS/MG/TO), essa cláusula NÃO foi verificada nesta atualização (o campo 'exigencias' do casos.jsonl não cobre combustível) -- fica como limitação."},
 {"tipo": "Jornada/franquia (8h/dia, 44h/semana; ou franquias grandes tipo Alvorada-TO com 983h no RP)", "recorrencia": "3+ editais", "evidencia": "Goianésia e Poxoréu (ver regras de lance); Alvorada-TO tem uma das maiores franquias de horas da amostra."},
]

oportunidades = [
 {"id": "01738772000198_2025_18","link": "https://pncp.gov.br/app/editais/01738772000198/2025/18","area_classificada": "eletrica_predial","item_relevante": "SERVIÇO ESPECIALIZADO EM ALTURA PARA TROCA DE LUMINÁRIA PÚBLICA EM POSTE DE ATÉ 12 MT, REALIZADO COM CAMINHÃO TIPO CESTO AÉREO (1.377 unidades, R$169.825,41 no total)","observacao": "Contrato principal é fornecimento de material elétrico + mão de obra, mas contém item isolado e substancial de serviço com caminhão-cesto."},
 {"id": "18295329000192_2024_244","link": "https://pncp.gov.br/app/editais/18295329000192/2024/244","area_classificada": "eletrica_predial (MG)","item_relevante": "MOBILIZAÇÃO E DESMOBILIZAÇÃO DE CONTAINER...EM CAMINHÃO CARROCERIA COM GUINDAUTO (MUNCK), EXCLUSIVE LOCAÇÃO DO CAMINHÃO (R$1.941,55)","observacao": "NOVO (encontrado na recoleta): obra de cobertura de quadra que usa um munck para mobilização/transporte de container de canteiro de obras -- item pequeno, mas mostra outro nicho de demanda (apoio logístico a obras), não só iluminação pública."},
 {"observacao_metodologica": "Busca refinada ('caminhão'+'munck/guindauto/cesto' no mesmo trecho) foi reexecutada sobre o dataset completo pós-recoleta (535 arquivos de compras, ante 415 antes): de 9 hits brutos, 2 são oportunidades reais (acima) e 7 são ruído (scanner automotivo, palco/tenda de eventos, manutenção de iluminação sem munck). Segue sem confirmação nenhum caso de remanejamento de condensadoras/refrigeração com item de munck."},
]

recomendacao = {
 "classe": "seletivo",
 "justificativa": "Com a recoleta (MS/MG/TO incluídos), a amostra de vizinhos incluídos mais que dobrou (6→13), reforçando que a demanda por munck fora de GO é real e não um artefato de amostra pequena -- mas também confirma que, quanto maior a capacidade exigida (15t, 45 t/m), maior o preço por hora, então a empresa deve mirar contratos compatíveis com seus 2 caminhões (provavelmente porte médio, 8-12t) e não necessariamente os de maior valor/hora. A recomendação permanece SELETIVA: priorizar locação pura de munck/cesto item-a-item (não frotas mistas nem fornecimento de material), sempre checar a cláusula de combustível antes do lance (não verificada nos 19 casos novos), e usar como piso ~R$220/h (combustível por conta da empresa) ou ~R$90/h (combustível por conta do contratante).",
}

limitacoes = [
 "Amostra pequena em GO (12 casos incluídos, inalterada); vizinhos cresceu de 6 para 13 casos incluídos (29 brutos) com a recoleta -- ainda pequena para conclusões fortes, mas menos frágil que antes.",
 "n_participantes: null em todos os 46 casos (PNCP não publica esse dado).",
 "Metodologia de `desconto`: o novo campo (preço unitário do 1º colocado, ponderado por item) NÃO mudou nenhum valor de munck em relação ao método antigo (diferença máxima observada: 3e-16, ruído de ponto flutuante) -- todas as medianas/quartis de desconto continuam válidas.",
 "Cobertura de texto de edital (`exigencias.tem_texto`) subiu de 0/27 para 16/46 casos (12 dos 25 incluídos) com a recoleta -- as evidências de exigências agora combinam texto oficial extraído automaticamente E os 8 PDFs baixados manualmente na rodada anterior (2 ainda não convertidos, RTF disfarçado de .pdf).",
 "Responsabilidade pelo combustível: confirmada em 6 editais (4 rodada anterior); os 19 casos novos (MS/MG/TO) NÃO tiveram essa cláusula verificada nesta atualização -- tratada de forma conservadora (assumida por conta da contratada) nas linhas de margem novas.",
 "Margem de Deodápolis-MS (15t) e São Lourenço-MG (45 t/m): usam o MESMO modelo de custo do munck médio (8-12t) por falta de premissa específica para porte maior -- provavelmente SUBESTIMA o custo real desses 2 casos (diesel, manutenção e depreciação maiores em equipamento maior), então a folga de margem calculada para eles é otimista.",
 "Diesel: consumo em operação (22,37 L/h, SINAPI 91633) é de um guindauto de 6,5t; consumo em deslocamento (~3km/L) e a mistura 40/60 são estimativas do analista.",
 "Depreciação: valor do munck usado (R$380 mil) vem de busca de mercado em anúncios, não de uma cotação única.",
 "5 casos (3 da rodada anterior + 2 novos: Alvorada tem 1 item só então não é parcial, mas Três Pontas-SAAE-MG e outros de frota mista) foram tratados como 'parcialmente incluídos' -- o valor/desconto do CASO pode incluir itens fora do escopo.",
 "A busca de oportunidades em outras áreas foi reexecutada sobre o dataset completo pós-recoleta (535 arquivos); ainda não há confirmação de oportunidade em refrigeração/condensadoras.",
]

meta = {
 "gerado_em": "2026-09-27 (atualizado após fim da coleta)",
 "periodo_coleta": "2024-09-27 a 2026-09-27 (~24 meses)",
 "n_casos_munck_bruto": 46,
 "n_casos_go": 17, "n_casos_vizinhos": 29,
 "detalhe_vizinhos_por_uf": {"DF": 2, "MT": 8, "MS": 8, "MG": 8, "TO": 3},
 "n_incluidos_go": 12, "n_incluidos_vizinhos": 13,
 "atualizacao_pos_recoleta": "coletor.py terminou a coleta; casos.jsonl foi regerado com 535 casos totais (antes 415), incluindo 19 casos novos de munck em MS/MG/TO (UFs que antes não tinham nenhum caso detalhado). O campo `desconto` mudou de definição (agora por preço unitário do 1º colocado, ponderado pelo valor de cada item; método antigo preservado em `desconto_total`) -- verificado que NÃO altera nenhuma estatística de munck. `exigencias.tem_texto` também passou a `true` em 16/46 casos (W/textos agora populado).",
 "observacao_coleta": "8 PDFs de edital baixados manualmente na rodada anterior (2 não convertidos); a recoleta trouxe texto oficial extraído para boa parte dos casos de GO.",
}

full = {
 "area": "munck", "meta": meta,
 "decisoes": json.load(open(f'{W}/analise/tmp_munck/decisoes.json')),
 "indicadores": json.load(open(f'{W}/analise/tmp_munck/indicadores.json')),
 "precos_hora": json.load(open(f'{W}/analise/tmp_munck/precos_hora.json')),
 "exemplares": exemplares,
 "premissas_custo": premissas_custo,
 "margem": json.load(open(f'{W}/analise/tmp_munck/margem.json')),
 "investimento": investimento,
 "regras_lance": regras_lance,
 "exigencias": exigencias,
 "oportunidades_outras_areas": oportunidades,
 "recomendacao": recomendacao,
 "limitacoes": limitacoes,
}
out = f'{W}/analise/tmp_munck/munck_v2.json'
with open(out, 'w') as f:
    json.dump(full, f, ensure_ascii=False, indent=1)
print("wrote", out, len(json.dumps(full)), "bytes")
