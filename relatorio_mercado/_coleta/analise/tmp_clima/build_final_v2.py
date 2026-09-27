import json

W='/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado'
T=f'{W}/analise/tmp_clima'

old = json.load(open(f'{W}/analise/areas/climatizacao.json'))
decisoes = json.load(open(f'{T}/decisoes_merged.json'))
indic = json.load(open(f'{T}/indicadores_v2.json'))

casos = {}
with open(f'{T}/clima_casos_v2.jsonl') as f:
    for line in f:
        c = json.loads(line)
        casos[c['id']] = c

# ---- indicadores ----
indicadores = {
    "go": indic["GO"],
    "vizinhos": indic["vizinhos"],
    "exclusoes_por_motivo_go": indic["exclusoes_GO"],
    "exclusoes_por_motivo_vizinhos": indic["exclusoes_vizinhos"],
    "observacao_n_participantes": old["indicadores"]["observacao_n_participantes"],
    "observacao_desconto": "O campo 'desconto' passou a ser o desconto por PRECO UNITARIO do 1o colocado, ponderado pelo valor estimado de cada item (metodo antigo, por VALOR TOTAL, esta em 'desconto_total' em casos.jsonl). Reduziu de 2 para 0 (GO) e manteve 1 (vizinhos) o numero de descontos suspeitos descartados: 2 casos de GO que tinham desconto_total negativo espurio (-54%, -66%, distorcao por mistura de itens com quantidades/lotes diferentes) passaram a ter desconto unitario positivo e coerente (31%, 16%) com o novo metodo.",
    "cobertura_amostra_detalhada": {
        "go": "92 de 92 casos aceitos no indice de busca (selecao.jsonl) tem detalhe baixado = 100% de cobertura.",
        "vizinhos": "43 de 450 casos aceitos no indice de busca (selecao.jsonl, DF+MT+MS+TO+MG) tem detalhe baixado = ~9,6% de cobertura -- amostra pequena, numeros de vizinhos continuam sendo apenas direcionais.",
    },
}

# ---- margem: mantido (valores base nao mudaram; so o campo 'desconto' unitario mudou, que e diferente do calculo de margem que usa valor_estimado/valor_homologado diretamente) ----
margem = old["margem"]
for m in margem:
    m["nota_atualizacao"] = "Valor estimado e homologado nao mudaram na atualizacao dos dados (27/09, pos-coleta); classificacao de margem mantida sem alteracao."

meta = dict(old["meta"])
meta.update({
    "gerado_em": "2026-09-27 (atualizado apos fim da coleta)",
    "n_casos_climatizacao_total": len(decisoes),
    "n_casos_go": sum(1 for d in decisoes if d["escopo"]=="GO"),
    "n_casos_vizinhos": sum(1 for d in decisoes if d["escopo"]!="GO"),
    "n_incluidos_go": indic["GO"]["n_casos"],
    "n_incluidos_vizinhos": indic["vizinhos"]["n_casos"],
    "n_casos_novos_pos_coleta": 18,
    "n_reclassificados_para_incluido_total": 24 + sum(1 for cid,(inc,mot,_) in [] for _ in []),  # placeholder, fixed below
    "observacao_coleta": "coletor.py terminou a coleta; W/analise/casos.jsonl foi regerado com 535 casos totais (todas as areas). 18 casos novos de climatizacao apareceram (1 GO, 8 TO, 9 MG), a maioria porque o texto/detalhe so ficou disponivel apos o fim da coleta. O campo 'desconto' tambem mudou de definicao (ver indicadores.observacao_desconto).",
})
# contagem correta de reclassificados (24 da rodada 1 + os desta rodada que vieram com motivo automatico != decisao final)
novos = json.load(open(f'{T}/decisoes_novos.json'))
n_reclass_novos = sum(1 for d in novos if False)  # calculado abaixo comparando com motivo original
# recalcula usando casos (motivo original vindo de exclusao.motivo) vs decisao final
n_reclass_novos = 0
for d in novos:
    orig_motivo = (casos[d['id']].get('exclusao') or {}).get('motivo')
    if d['incluido'] and orig_motivo is not None:
        n_reclass_novos += 1
meta["n_reclassificados_para_incluido_total"] = 24 + n_reclass_novos
meta["n_reclassificados_novos_desta_rodada"] = n_reclass_novos

final = {
    "area": "climatizacao",
    "meta": meta,
    "decisoes": decisoes,
    "indicadores": indicadores,
    "exemplares": old["exemplares"],
    "margem": margem,
    "investimento": old["investimento"],
    "regras_lance": None,  # preenchido abaixo
    "exigencias": old["exigencias"],
    "recomendacao": old["recomendacao"],
    "limitacoes": None,  # preenchido abaixo
}

regras_lance = [
    "Desconto tipico em GO, agora medido por PRECO UNITARIO ponderado (n=68, 0 descartados por suspeita): mediana 44,3%; 1o quartil 24,0%; 3o quartil 60,8% -- praticamente igual ao valor calculado pelo metodo antigo (a mudanca de metodologia so afetou 2 casos que tinham desconto total negativo espurio e passaram a ter desconto unitario positivo e coerente).",
    "Vizinhos (amostra ampliada para 31 casos incluidos, cobrindo agora DF/MT/MS/TO/MG): mediana 31,4%; Q1 23,3%; Q3 43,7% -- descontos tipicamente MENORES que em GO, mas amostra ainda pequena (~9,6% do indice de busca).",
    "Nos 5 casos de margem calculados (valores estimado/homologado nao mudaram com a atualizacao dos dados), o limite de risco (desconto maximo sem prejuizo, pelo preco de lucro zero) continua entre ~46% e ~47% para contratos com itens detalhados por aparelho/BTU (casos A e C) e entre ~81% e ~94% para Registros de Precos guarda-chuva com item unico e generico (casos B, D, E). NENHUM dos 5 casos de margem mudou de classificacao com a atualizacao (todos permanecem 'folgado', com o caso C ainda sendo o mais apertado, 5,5% acima do preco com BDI).",
    "Como a mediana observada em GO (44,3%) continua perto do limite de risco dos contratos item-a-item (~46-47%) e o 3o quartil (60,8%) continua ACIMA desse limite, a leitura da rodada anterior se confirma: boa parte dos lances vencedores em GO opera, pelo nosso modelo de custo, na faixa 'apertado' ou pior para contratos pequenos/medios detalhados por aparelho -- sinal de que concorrentes reais tem estrutura de custo mais enxuta ou aceitam margem muito fina.",
    "Ata de Registro de Precos (SRP) nao garante volume de contratacao: boa parte dos casos incluidos em GO e vizinhos e SRP (\"futura e eventual\") -- planeje o fluxo de caixa considerando consumo parcial da ata.",
    "Contratos sem dedicacao exclusiva de mao de obra frequentemente dispensam garantia contratual (observado em 2 dos 5 editais lidos integralmente -- Anapolis e TRE-GO): confirme essa clausula especifica de cada edital antes de reservar caixa para garantia.",
    "Servicos de climatizacao raramente exigem caminhao munck/guindauto com cesto aereo (nao encontrado em nenhum dos 5 editais lidos) -- diferente da area de iluminacao publica. Os 2 munck da empresa tendem a ficar ociosos nesta area, a menos que o contrato inclua remocao/instalacao de condensadoras em telhados/fachadas de dificil acesso.",
]
final["regras_lance"] = regras_lance

limitacoes = list(old["limitacoes"])
limitacoes[1] = ("Amostra de vizinhos (DF/MT/MS/TO/MG) segue pequena para conclusoes fortes: 43 casos com detalhe baixado (31 incluidos apos revisao) contra 450 casos aceitos pelo indice de busca em ~24 meses (~9,6% de cobertura). Os indicadores de vizinhos neste relatorio valem como sinal direcional, nao como estimativa robusta de mercado.")
limitacoes[2] = "Em GO a cobertura de detalhe e total (92 de 92 casos aceitos pelo indice de busca), entao os indicadores de GO sao os mais confiaveis do estudo."
limitacoes.append("Atualizacao pos-coleta (rodada 2): 18 casos novos de climatizacao apareceram apos o fim da coleta (1 GO, 8 TO, 9 MG); 14 foram incluidos (a maioria servico de manutencao mal cadastrado como Material) e 4 excluidos (aquisicao pura de equipamento/material). O campo 'desconto' passou a ser calculado por preco unitario ponderado (nao mais por valor total); isso corrigiu 2 descontos espurios negativos em GO mas nao mudou a leitura geral dos quartis nem a classificacao de nenhum dos 5 casos de margem.")
final["limitacoes"] = limitacoes

json.dump(final, open(f'{W}/analise/areas/climatizacao.json','w'), ensure_ascii=False, indent=2)
print("OK, decisoes:", len(final['decisoes']), "incluidos:", sum(1 for d in final['decisoes'] if d['incluido']))
print("n_reclassificados_novos_desta_rodada:", meta['n_reclassificados_novos_desta_rodada'])
print("n_reclassificados_total:", meta['n_reclassificados_para_incluido_total'])
