import json, statistics as st
from collections import Counter

W='/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado'
T=f'{W}/analise/tmp_clima'

with open(f'{T}/clima_casos_v2.jsonl') as f:
    casos = {json.loads(l)['id']: json.loads(l) for l in f}

decisoes = json.load(open(f'{T}/decisoes_merged.json'))

def quantile_inclusive(sorted_vals, q):
    n = len(sorted_vals)
    if n == 0: return None
    if n == 1: return sorted_vals[0]
    pos = q*(n-1); lo=int(pos); hi=min(lo+1,n-1); frac=pos-lo
    return sorted_vals[lo] + (sorted_vals[hi]-sorted_vals[lo])*frac

def compute(ids):
    rows = [casos[i] for i in ids]
    n = len(rows)
    valores = [r['valor_estimado_total'] for r in rows if r.get('valor_estimado_total')]
    valor_total = sum(valores)
    ticket_mediano = st.median(valores) if valores else None
    descontos = []
    for r in rows:
        d = r.get('desconto')
        if d is None or r.get('desconto_suspeito'):
            continue
        descontos.append(d)
    descontos.sort()
    n_deserta = sum(1 for r in rows if (r.get('itens') or {}).get('houve_deserta_ou_fracassada'))
    n_meepp_total = sum(1 for r in rows if (r.get('me_epp') or {}).get('exclusiva_total'))
    n_meepp_parcial = sum(1 for r in rows if (r.get('me_epp') or {}).get('exclusiva_parcial'))
    n_meepp_cota = sum(1 for r in rows if (r.get('me_epp') or {}).get('cota'))
    n_continuado = sum(1 for r in rows if r.get('tipo_contrato')=='continuado')
    n_pontual = sum(1 for r in rows if r.get('tipo_contrato')=='pontual')
    n_indefinido = sum(1 for r in rows if r.get('tipo_contrato')=='indefinido')
    return {
        "n_casos": n,
        "valor_total_estimado": round(valor_total,2),
        "ticket_mediano": round(ticket_mediano,2) if ticket_mediano else None,
        "n_amostra_ticket": len(valores),
        "desconto_mediana": quantile_inclusive(descontos,0.5),
        "desconto_q1": quantile_inclusive(descontos,0.25),
        "desconto_q3": quantile_inclusive(descontos,0.75),
        "n_amostra_desconto": len(descontos),
        "n_descontos_suspeitos_descartados": sum(1 for r in rows if r.get('desconto_suspeito')),
        "pct_deserta_ou_fracassada": round(n_deserta/n,4) if n else None,
        "pct_exclusiva_meepp": round(n_meepp_total/n,4) if n else None,
        "pct_exclusiva_parcial_meepp": round(n_meepp_parcial/n,4) if n else None,
        "pct_cota_meepp": round(n_meepp_cota/n,4) if n else None,
        "pct_continuado": round(n_continuado/n,4) if n else None,
        "pct_pontual": round(n_pontual/n,4) if n else None,
        "pct_indefinido": round(n_indefinido/n,4) if n else None,
    }

go_incl = [d['id'] for d in decisoes if d['incluido'] and d['escopo']=='GO']
viz_incl = [d['id'] for d in decisoes if d['incluido'] and d['escopo']!='GO']
print('GO incl:', len(go_incl), 'VIZ incl:', len(viz_incl))
go_stats = compute(go_incl)
viz_stats = compute(viz_incl)
print(json.dumps({'GO':go_stats,'vizinhos':viz_stats}, ensure_ascii=False, indent=2))

motivo_go = Counter(d['motivo'] for d in decisoes if d['escopo']=='GO' and not d['incluido'])
motivo_viz = Counter(d['motivo'] for d in decisoes if d['escopo']!='GO' and not d['incluido'])
print('exclusoes GO:', dict(motivo_go))
print('exclusoes VIZ:', dict(motivo_viz))

# breakdown vizinhos por UF (cobertura)
by_uf = Counter(c.get('escopo') for c in casos.values())
print('casos climatizacao por UF (total, antes de decisao):', dict(by_uf))

json.dump({'GO':go_stats,'vizinhos':viz_stats,
           'exclusoes_GO':dict(motivo_go),'exclusoes_vizinhos':dict(motivo_viz),
           'go_incl_ids':go_incl,'viz_incl_ids':viz_incl}, open(f'{T}/indicadores_v2.json','w'), ensure_ascii=False, indent=2)
