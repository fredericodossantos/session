import json

NOVOS = {
 "00508903000188_2026_1432": (False, "fornecimento_puro", "Aquisicao pura de materiais eletricos para adequacao de instalacoes (nao e manutencao/servico de climatizacao em si)."),
 "01138330000100_2027_1": (True, None, "Servico de manutencao preventiva/corretiva em climatizacao (central/compacto/split) com mao de obra, materiais e gas incluidos."),
 "01181169000158_2026_1": (True, None, "Contrato predial multi-oficio (eletrica, hidraulica, pintura, serralheria, refrigeracao, etc.); refrigeracao/climatizacao e um dos servicos cobertos, sem motivo de exclusao valido (nao e aquisicao pura, nao e obra grande, nao e equipamento de alto valor, nao e mencao de passagem) -- incluido, mas nota-se escopo multi-oficio no texto."),
 "01184383000168_2026_3": (True, None, "Servico de manutencao preventiva/corretiva com fornecimento de mao de obra, pecas e gas refrigerante em AC split (e outros eletrodomesticos)."),
 "01296363000189_2026_5": (True, None, "Servico de manutencao/instalacao/remocao/higienizacao de AC split com fornecimento de mao de obra, pecas e gas."),
 "01614862000177_2026_62": (True, None, "Servico de instalacao e manutencao preventiva/corretiva de ar condicionado."),
 "01795483000120_2026_17": (True, None, "Servico continuado (12 meses) de manutencao preventiva/corretiva de AC com mao de obra, materiais e gas."),
 "04842827000101_2026_52": (True, None, "Servico de manutencao/recarga/calibracao com laudo tecnico e elaboracao de PMOC em equipamentos de refrigeracao/climatizacao; itens mal cadastrados como Material pelo orgao (heuristica automatica reagiu a isso)."),
 "05487631000109_2026_97": (False, "fornecimento_puro", "Aquisicao de materiais e equipamentos diversos (ar condicionado, ventilador, lixeira etc.) para uma academia -- compra pura, multi-categoria, sem servico de manutencao."),
 "07248660000135_2026_44": (True, None, "Servico continuado de instalacao/desinstalacao/remanejamento/manutencao com reposicao integral de pecas em equipamentos de climatizacao."),
 "11675300000197_2026_3": (True, None, "Servico de manutencao preventiva/corretiva multi-equipamento (refrigeracao/climatizacao, eletrodomesticos, cozinha industrial etc.); climatizacao/refrigeracao e parte do escopo, sem motivo de exclusao valido -- incluido, mas nota-se escopo multi-equipamento no texto."),
 "12775985000106_2026_4": (True, None, "Servico de limpeza e manutencao de ar condicionado; itens mal cadastrados como Material pelo orgao (heuristica automatica reagiu a isso)."),
 "16907746000113_2026_81": (True, None, "Servico de instalacao e manutencao preventiva/corretiva em aparelhos de ar condicionado."),
 "18242792000176_2026_147": (True, None, "Servico de manutencao de aparelhos de ar condicionado em predios publicos municipais."),
 "18244376000107_2026_137": (False, "fornecimento_puro", "Aquisicao de materiais para manutencao de vias, pontes, sinalizacao, obras de pequeno porte e manutencao predial em geral; ar-condicionado e mencao secundaria entre dezenas de categorias de materiais de construcao -- compra pura, fora do escopo real de climatizacao."),
 "18338848000190_2026_57": (True, None, "Servico de manutencao corretiva/preventiva em AC e equipamentos de refrigeracao; itens mal cadastrados como Material pelo orgao (heuristica automatica reagiu a isso)."),
 "18423582000184_2026_119": (False, "equipamento_alto", "Aquisicao pura de aparelhos de ar condicionado (fracao em material = 77%), sem servico de manutencao associado."),
 "66229857000196_2026_54": (True, None, "Programa de PMOC com instalacao/desinstalacao/limpeza/manutencao preventiva e corretiva de condicionadores de ar -- servico continuado classico da area."),
}

with open('/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado/analise/tmp_clima/clima_casos_v2.jsonl') as f:
    casos = {json.loads(l)['id']: json.loads(l) for l in f}

decisoes_novos = []
for cid, (incluido, motivo, just) in NOVOS.items():
    c = casos[cid]
    decisoes_novos.append({
        "id": cid,
        "escopo": c.get("escopo"),
        "incluido": incluido,
        "motivo": motivo,
        "justificativa": just,
    })

json.dump(decisoes_novos, open('/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado/analise/tmp_clima/decisoes_novos.json','w'), ensure_ascii=False, indent=2)
print(len(decisoes_novos), "decisoes novas")
print('incluidos:', sum(1 for d in decisoes_novos if d['incluido']))
