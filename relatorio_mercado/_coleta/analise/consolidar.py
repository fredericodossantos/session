"""Consolida as decisões das análises por área em casos_final.jsonl.

Cada caso recebe UMA área final (a primeira área, na ordem de PRIORIDADE, cuja análise o
incluiu); se nenhuma o incluiu, fica excluído com o motivo da área principal. O campo
`areas` passa a conter só a área final, para os indicadores e a planilha contarem cada
licitação uma única vez.
"""
from __future__ import annotations

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PRIORIDADE = ["iluminacao_publica", "munck", "refrigeracao", "eletrica_predial",
              "climatizacao", "manutencao_predial"]


def carregar_jsonl(caminho):
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main() -> int:
    casos = carregar_jsonl(os.path.join(AQUI, "casos.jsonl"))
    decisoes: dict[str, dict[str, dict]] = {}
    for area in PRIORIDADE:
        caminho = os.path.join(AQUI, "areas", f"{area}.json")
        if not os.path.exists(caminho):
            print(f"[consolidar] sem análise para {area}", file=sys.stderr)
            continue
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        for d in dados.get("decisoes", []):
            decisoes.setdefault(d["id"], {})[area] = d

    saida = []
    sem_decisao = 0
    for c in casos:
        por_area = decisoes.get(c["id"], {})
        if not por_area:
            sem_decisao += 1
            c["decisao_origem"] = "heuristica"
            saida.append(c)
            continue
        incluida = next((a for a in PRIORIDADE if por_area.get(a, {}).get("incluido")), None)
        if incluida:
            c["areas"] = [incluida]
            c["area_principal"] = incluida
            c["exclusao"] = dict(c.get("exclusao") or {}, motivo=None,
                                 evidencia=por_area[incluida].get("justificativa"))
        else:
            area = c.get("area_principal") if c.get("area_principal") in por_area else next(iter(por_area))
            d = por_area[area]
            c["areas"] = [area]
            c["area_principal"] = area
            c["exclusao"] = dict(c.get("exclusao") or {}, motivo=d.get("motivo") or "fora_escopo",
                                 evidencia=d.get("justificativa"))
        if por_area.get(c["area_principal"], {}).get("subarea"):
            c["subarea"] = por_area[c["area_principal"]]["subarea"]
        c["decisao_origem"] = "revisao_por_area"
        saida.append(c)

    with open(os.path.join(AQUI, "casos_final.jsonl"), "w", encoding="utf-8") as f:
        for c in saida:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    incl = sum(1 for c in saida if c["exclusao"]["motivo"] is None)
    print(f"[consolidar] {len(saida)} casos; incluídos {incl}; sem decisão manual {sem_decisao}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
