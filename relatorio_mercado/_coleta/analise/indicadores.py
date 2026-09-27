#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
indicadores.py -- le casos.jsonl (gerado por casos.py) + selecao.jsonl
(gerado por coletor.py) e calcula indicadores por area e por UF (GO
separado dos vizinhos), usando SO os casos nao excluidos.

So LE arquivos.

Uso:
    python3 indicadores.py
    python3 indicadores.py --casos casos_teste.jsonl \
        --selecao ../_teste_validacao/selecao.jsonl \
        --saida-prefixo indicadores_teste
"""

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

PERIODO_INICIO = "2024-09-27"
PERIODO_FIM = "2026-09-27"
DIVISOR_ANUALIZACAO = 2.0  # periodo de ~24 meses = 2 anos


def grupo_uf(escopo):
    if escopo == C.UF_PRINCIPAL:
        return "GO"
    if escopo in C.UFS_VIZINHAS:
        return "vizinhos"
    return None


def pct(lst, pred):
    if not lst:
        return None
    return sum(1 for c in lst if pred(c)) / len(lst)


def calc_metrics(casos_grupo, n_indice_aceitos):
    n_casos = len(casos_grupo)
    volume_ano_indice = (n_indice_aceitos / DIVISOR_ANUALIZACAO) if n_indice_aceitos is not None else None

    valores = [c["valor_estimado_total"] for c in casos_grupo if c.get("valor_estimado_total") is not None]
    valor_total_estimado = sum(valores) if valores else None
    ticket_mediano = C.mediana(valores)

    participantes = [c["n_participantes"] for c in casos_grupo if c.get("n_participantes") is not None]
    mediana_participantes = C.mediana(participantes)

    descontos = [c["desconto"] for c in casos_grupo if c.get("desconto") is not None]
    desconto_q1, desconto_q3 = C.quartis(descontos)

    return {
        "n_casos_detalhados": n_casos,
        "volume_ano_indice_aceitos": n_indice_aceitos,
        "volume_ano": volume_ano_indice,
        "valor_total_estimado": valor_total_estimado,
        "ticket_mediano": ticket_mediano,
        "n_amostra_ticket": len(valores),
        "mediana_participantes": mediana_participantes,
        "n_amostra_participantes": len(participantes),
        "desconto_mediana": C.mediana(descontos),
        "desconto_q1": desconto_q1,
        "desconto_q3": desconto_q3,
        "n_amostra_desconto": len(descontos),
        "pct_deserta_ou_fracassada": pct(casos_grupo, lambda c: c["itens"]["houve_deserta_ou_fracassada"]),
        "pct_exclusiva_meepp": pct(casos_grupo, lambda c: c["me_epp"]["exclusiva_total"]),
        "pct_exclusiva_parcial_meepp": pct(casos_grupo, lambda c: c["me_epp"]["exclusiva_parcial"]),
        "pct_cota_meepp": pct(casos_grupo, lambda c: c["me_epp"]["cota"]),
        "pct_continuado": pct(casos_grupo, lambda c: c["tipo_contrato"] == "continuado"),
        "pct_pontual": pct(casos_grupo, lambda c: c["tipo_contrato"] == "pontual"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--casos", default=os.path.join(C.ANALISE_DIR, "casos.jsonl"))
    ap.add_argument("--selecao", default=os.path.join(C.W, "selecao.jsonl"))
    ap.add_argument("--selecao-suplementar", default=None,
                     help="selecao_suplementar.jsonl (coletor_suplementar.py), mesclada na "
                          "selecao principal para contar 'aceito=true' no volume/ano. "
                          "Default: W/selecao_suplementar.jsonl, mas so quando --selecao "
                          "ficou no valor de producao (W/selecao.jsonl); em qualquer outro "
                          "--selecao (ex.: amostra de teste) o default vira None (nao mescla).")
    ap.add_argument("--saida-prefixo", default="indicadores")
    args = ap.parse_args()

    casos = C.carregar_jsonl(args.casos)
    selecao = C.carregar_jsonl(args.selecao)

    selecao_sup_path = args.selecao_suplementar
    if selecao_sup_path is None and os.path.normpath(args.selecao) == os.path.normpath(os.path.join(C.W, "selecao.jsonl")):
        selecao_sup_path = os.path.join(C.W, "selecao_suplementar.jsonl")
    selecao_sup = C.carregar_jsonl(selecao_sup_path) if selecao_sup_path else []
    if selecao_sup:
        print(f"[indicadores.py] selecao SUPLEMENTAR carregada: {len(selecao_sup)} linhas (de {selecao_sup_path})")
        selecao = selecao + selecao_sup

    print(f"[indicadores.py] casos carregados: {len(casos)} (de {args.casos})")
    print(f"[indicadores.py] selecao carregada: {len(selecao)} linhas (de {args.selecao}"
          f"{' + suplementar' if selecao_sup else ''})")

    incluidos = [c for c in casos if c["exclusao"]["motivo"] is None]
    excluidos = [c for c in casos if c["exclusao"]["motivo"] is not None]
    print(f"[indicadores.py] casos incluidos={len(incluidos)} excluidos={len(excluidos)}")

    # -------------------- volume no indice (selecao.jsonl, aceito=True) -----
    idx_go_uf = {}   # (area, uf_exato) -> count
    for row in selecao:
        if not row.get("aceito"):
            continue
        area = row.get("area")
        uf_exato = row.get("escopo")
        idx_go_uf[(area, uf_exato)] = idx_go_uf.get((area, uf_exato), 0) + 1

    def n_indice(area, grupo):
        if grupo == "GO":
            return idx_go_uf.get((area, "GO"))
        total = 0
        achou = False
        for uf in C.UFS_VIZINHAS:
            if (area, uf) in idx_go_uf:
                achou = True
                total += idx_go_uf[(area, uf)]
        return total if achou else None

    def n_indice_uf(area, uf):
        return idx_go_uf.get((area, uf))

    # -------------------- agrupamento dos casos --------------------
    resultado = {
        "meta": {
            "gerado_em": date.today().isoformat(),
            "casos_arquivo": os.path.abspath(args.casos),
            "selecao_arquivo": os.path.abspath(args.selecao),
            "selecao_suplementar_arquivo": os.path.abspath(selecao_sup_path) if selecao_sup else None,
            "periodo": {"inicio": PERIODO_INICIO, "fim": PERIODO_FIM, "divisor_anualizacao": DIVISOR_ANUALIZACAO},
            "n_casos_total": len(casos),
            "n_casos_incluidos": len(incluidos),
            "n_casos_excluidos": len(excluidos),
            "observacao": (
                "Indicadores calculados SO com casos nao excluidos (exclusao.motivo is None). "
                "'volume_ano_indice_aceitos' vem de selecao.jsonl (aceito=true, apos filtro de "
                "modalidade/periodo/regex do coletor.py) dividido por 2 (periodo de ~24 meses). "
                "Um caso que bateu em mais de uma area (campo 'areas') conta para cada area em que "
                "aparece, do mesmo jeito que o indice de selecao conta -- por isso os dois numeros "
                "sao comparaveis, mas a soma das areas pode superar o numero de arquivos unicos."
            ),
        },
        "por_area_grupo": {},       # area -> {"GO": {...}, "vizinhos": {...}}
        "por_area_uf_detalhe": {},  # area -> {uf: {...}}  (GO + cada vizinha)
        "exclusoes_por_area_motivo": {},
        "revisao_manual_por_area": {},
    }

    for area in C.AREAS:
        casos_area = [c for c in incluidos if area in (c.get("areas") or [])]

        por_grupo = {}
        for grupo in ("GO", "vizinhos"):
            grupo_casos = [c for c in casos_area if grupo_uf(c.get("escopo")) == grupo]
            por_grupo[grupo] = calc_metrics(grupo_casos, n_indice(area, grupo))
        resultado["por_area_grupo"][area] = por_grupo

        por_uf = {}
        for uf in [C.UF_PRINCIPAL] + C.UFS_VIZINHAS:
            uf_casos = [c for c in casos_area if c.get("escopo") == uf]
            por_uf[uf] = calc_metrics(uf_casos, n_indice_uf(area, uf))
        resultado["por_area_uf_detalhe"][area] = por_uf

        # exclusoes (usa TODOS os casos da area, incluidos ou nao)
        todos_area = [c for c in casos if area in (c.get("areas") or [])]
        motivos = {}
        for c in todos_area:
            m = c["exclusao"]["motivo"]
            if m:
                motivos[m] = motivos.get(m, 0) + 1
        resultado["exclusoes_por_area_motivo"][area] = motivos
        resultado["revisao_manual_por_area"][area] = sum(1 for c in todos_area if c["exclusao"]["revisao_manual"])

    saida_json = os.path.join(C.ANALISE_DIR, f"{args.saida_prefixo}.json")
    with open(saida_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"[indicadores.py] escrito {saida_json}")

    saida_md = os.path.join(C.ANALISE_DIR, f"{args.saida_prefixo}.md")
    escreve_md(resultado, saida_md)
    print(f"[indicadores.py] escrito {saida_md}")


def _fmt(v, casas=2, pct_=False, moeda=False):
    if v is None:
        return "-"
    if pct_:
        return f"{v * 100:.1f}%"
    if moeda:
        return f"R$ {v:,.0f}".replace(",", ".")
    if isinstance(v, float):
        return f"{v:.{casas}f}"
    return str(v)


def escreve_md(resultado, path):
    linhas = []
    meta = resultado["meta"]
    linhas.append("# Indicadores do estudo de mercado de licitacoes (GO + vizinhos)\n")
    linhas.append(f"Gerado em: {meta['gerado_em']}  ")
    linhas.append(f"Periodo: {meta['periodo']['inicio']} a {meta['periodo']['fim']}  ")
    linhas.append(f"Casos totais: {meta['n_casos_total']} | incluidos: {meta['n_casos_incluidos']} | "
                   f"excluidos: {meta['n_casos_excluidos']}\n")
    linhas.append(f"> {meta['observacao']}\n")

    for area, grupos in resultado["por_area_grupo"].items():
        linhas.append(f"\n## {area}\n")
        linhas.append("| metrica | GO | vizinhos (DF/MT/MS/TO/MG) |")
        linhas.append("|---|---|---|")
        m_go, m_vz = grupos["GO"], grupos["vizinhos"]
        linhas.append(f"| volume/ano (indice, aceitos/2) | {_fmt(m_go['volume_ano'])} | {_fmt(m_vz['volume_ano'])} |")
        linhas.append(f"| nº casos detalhados | {m_go['n_casos_detalhados']} | {m_vz['n_casos_detalhados']} |")
        linhas.append(f"| valor total estimado | {_fmt(m_go['valor_total_estimado'], moeda=True)} | {_fmt(m_vz['valor_total_estimado'], moeda=True)} |")
        linhas.append(f"| ticket mediano | {_fmt(m_go['ticket_mediano'], moeda=True)} | {_fmt(m_vz['ticket_mediano'], moeda=True)} |")
        linhas.append(f"| mediana participantes (n amostra) | {_fmt(m_go['mediana_participantes'])} ({m_go['n_amostra_participantes']}) | {_fmt(m_vz['mediana_participantes'])} ({m_vz['n_amostra_participantes']}) |")
        linhas.append(f"| desconto mediana [Q1;Q3] (n) | {_fmt(m_go['desconto_mediana'], pct_=True)} [{_fmt(m_go['desconto_q1'], pct_=True)};{_fmt(m_go['desconto_q3'], pct_=True)}] ({m_go['n_amostra_desconto']}) | {_fmt(m_vz['desconto_mediana'], pct_=True)} [{_fmt(m_vz['desconto_q1'], pct_=True)};{_fmt(m_vz['desconto_q3'], pct_=True)}] ({m_vz['n_amostra_desconto']}) |")
        linhas.append(f"| % deserta/fracassada | {_fmt(m_go['pct_deserta_ou_fracassada'], pct_=True)} | {_fmt(m_vz['pct_deserta_ou_fracassada'], pct_=True)} |")
        linhas.append(f"| % exclusiva ME/EPP (total/parcial/cota) | {_fmt(m_go['pct_exclusiva_meepp'], pct_=True)}/{_fmt(m_go['pct_exclusiva_parcial_meepp'], pct_=True)}/{_fmt(m_go['pct_cota_meepp'], pct_=True)} | {_fmt(m_vz['pct_exclusiva_meepp'], pct_=True)}/{_fmt(m_vz['pct_exclusiva_parcial_meepp'], pct_=True)}/{_fmt(m_vz['pct_cota_meepp'], pct_=True)} |")
        linhas.append(f"| % continuado / % pontual | {_fmt(m_go['pct_continuado'], pct_=True)} / {_fmt(m_go['pct_pontual'], pct_=True)} | {_fmt(m_vz['pct_continuado'], pct_=True)} / {_fmt(m_vz['pct_pontual'], pct_=True)} |")

        excl = resultado["exclusoes_por_area_motivo"].get(area) or {}
        if excl:
            linhas.append("\nExclusoes nesta area: " + ", ".join(f"{k}={v}" for k, v in sorted(excl.items())))
        revisao = resultado["revisao_manual_por_area"].get(area, 0)
        linhas.append(f"\nCasos sinalizados para revisao manual nesta area: {revisao}")

        linhas.append("\n<details><summary>detalhe por UF</summary>\n")
        linhas.append("| UF | volume/ano | nº casos | valor total est. | ticket mediano |")
        linhas.append("|---|---|---|---|---|")
        for uf, m in resultado["por_area_uf_detalhe"][area].items():
            linhas.append(f"| {uf} | {_fmt(m['volume_ano'])} | {m['n_casos_detalhados']} | {_fmt(m['valor_total_estimado'], moeda=True)} | {_fmt(m['ticket_mediano'], moeda=True)} |")
        linhas.append("\n</details>\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


if __name__ == "__main__":
    main()
