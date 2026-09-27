# -*- coding: utf-8 -*-
import json

path_json = "/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado/custos/custos/referencias.json"
path_md = "/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado/custos/custos/referencias.md"

with open(path_json, encoding="utf-8") as f:
    data = json.load(f)

meta = data["meta"]
regs = data["registros"]

lines = []
lines.append(f"# {meta['titulo']}")
lines.append("")
lines.append(f"Data de acesso padrão das fontes: **{meta['data_acesso_padrao']}**")
lines.append("")
lines.append("> " + meta["observacao_geral"].replace("\n", " "))
lines.append("")

# group by categoria, preserving order of first appearance
categorias = []
by_cat = {}
for r in regs:
    c = r["categoria"]
    if c not in by_cat:
        by_cat[c] = []
        categorias.append(c)
    by_cat[c].append(r)

lines.append("## Sumário de categorias")
lines.append("")
for c in categorias:
    lines.append(f"- {c} ({len(by_cat[c])} item(ns))")
lines.append("")

def fmt_valor(r):
    v = r["valor"]
    u = r["unidade"]
    if v is None:
        return "**não encontrado**"
    if isinstance(v, float):
        # 3 casas decimais (padrão ANP para combustível), removendo zero à direita
        # supérfluo (ex.: 7.040 -> 7,04; mantém 6.672 -> 6,672)
        s3 = f"{v:.3f}"
        if s3.endswith("0"):
            s3 = f"{v:.2f}"
        int_part, _, dec_part = s3.partition(".")
        # separador de milhar
        int_part = f"{int(int_part):,}".replace(",", ".")
        vs = f"{int_part},{dec_part}"
        return f"{vs} {u}".strip()
    return f"{v} {u}".strip()

for c in categorias:
    lines.append(f"## {c}")
    lines.append("")
    lines.append("| Item | Valor | Fonte | Trecho/Página | Confiabilidade | Observação |")
    lines.append("|---|---|---|---|---|---|")
    for r in by_cat[c]:
        item = r["item"].replace("|", "/")
        valor = fmt_valor(r).replace("|", "/")
        fonte = r["fonte_url"].replace("|", "/")
        # make fonte a markdown link when it looks like a URL
        if fonte.startswith("http"):
            fonte_md = f"[link]({fonte})"
        else:
            fonte_md = fonte
        trecho = r["trecho_ou_pagina"].replace("|", "/").replace("\n", " ")
        conf = r["confiabilidade"]
        obs = r["observacao"].replace("|", "/").replace("\n", " ")
        lines.append(f"| {item} | {valor} | {fonte_md} (acesso {r['data_acesso']}) | {trecho} | {conf} | {obs} |")
    lines.append("")

with open(path_md, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("linhas escritas:", len(lines))
