"""Geração do CSV e do relatório HTML (pensado para leitura no celular)."""
from __future__ import annotations

import csv
import html
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .filtros import COTA, EXCLUSIVA, PARCIAL

COLUNAS = [
    ("novo", "Novo"),
    ("situacao_me_epp", "Situação ME/EPP"),
    ("data_encerramento", "Data-limite propostas"),
    ("data_abertura", "Início recebimento propostas"),
    ("orgao", "Órgão"),
    ("unidade", "Unidade"),
    ("municipio", "Município"),
    ("codigo_ibge", "Código IBGE"),
    ("esfera", "Esfera"),
    ("modalidade", "Modalidade"),
    ("numero_compra", "Nº compra"),
    ("objeto", "Objeto"),
    ("valor_estimado", "Valor total estimado (R$)"),
    ("situacao_compra", "Situação da compra"),
    ("itens", "Itens (exclusivos/cota/total)"),
    ("numero_controle", "Nº controle PNCP"),
    ("link_pncp", "Link PNCP"),
    ("sistema_origem", "Sistema de origem"),
    ("link_origem", "Link sistema de origem"),
    ("termos", "Termos encontrados"),
]


def ordenar(registros: list[dict]) -> list[dict]:
    return sorted(registros, key=lambda r: (r["data_encerramento"] or datetime.max, r["orgao"]))


def fmt_data(d: datetime | None) -> str:
    return d.strftime("%d/%m/%Y %H:%M") if d else ""


def fmt_moeda(v: Any) -> str:
    if v in (None, ""):
        return ""
    try:
        s = f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _itens_txt(r: dict) -> str:
    c = r.get("contagem_itens") or {}
    if not c.get("itens"):
        return ""
    return f"{c.get('exclusivos', 0)}/{c.get('cota', 0)}/{c.get('itens', 0)}"


def _valor_csv(r: dict, chave: str) -> str:
    if chave == "novo":
        return {"nova": "NOVA", "atualizada": "ATUALIZADA"}.get(r.get("estado", ""), "")
    if chave in ("data_encerramento", "data_abertura"):
        return fmt_data(r.get(chave))
    if chave == "valor_estimado":
        return fmt_moeda(r.get(chave))
    if chave == "itens":
        return _itens_txt(r)
    if chave == "termos":
        return ", ".join(r.get("termos") or [])
    return str(r.get(chave) if r.get(chave) is not None else "")


def gerar_csv(registros: list[dict], caminho: Path) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig + ';' abre direto no Excel em português.
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([titulo for _, titulo in COLUNAS])
        for r in ordenar(registros):
            w.writerow([_valor_csv(r, chave) for chave, _ in COLUNAS])
    return caminho


CSS = """
:root{--bg:#f4f6f8;--card:#fff;--tx:#1d2733;--mut:#5b6875;--bd:#dde3e9;--ex:#0f7b3f;--exbg:#e6f6ec;
--cota:#8a5a00;--cotabg:#fff4dc;--par:#1f5fa8;--parbg:#e7f0fb;--novo:#c62828;--link:#0b57d0}
@media (prefers-color-scheme:dark){:root{--bg:#12171d;--card:#1b222b;--tx:#e6edf3;--mut:#9aa7b4;--bd:#2c3642;
--ex:#5fd08f;--exbg:#10301f;--cota:#f0c05a;--cotabg:#33280f;--par:#7fb2f0;--parbg:#132740;--novo:#ff7373;--link:#8ab4f8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);
font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:16px}
h1{font-size:1.25rem;margin:0 0 4px}.sub{color:var(--mut);font-size:.85rem;margin:0 0 12px}
.resumo{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin:0 0 16px}
.resumo div{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:8px 10px}
.resumo b{display:block;font-size:1.3rem}.resumo span{color:var(--mut);font-size:.8rem}
.card{background:var(--card);border:1px solid var(--bd);border-left:6px solid var(--bd);border-radius:10px;
padding:12px 14px;margin:0 0 12px;overflow-wrap:anywhere}
.card.ex{border-left-color:var(--ex);background:linear-gradient(90deg,var(--exbg),var(--card) 40%)}
.card.cota{border-left-color:var(--cota)}.card.par{border-left-color:var(--par)}
.topo{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:6px}
.tag{font-size:.75rem;font-weight:600;padding:2px 8px;border-radius:999px;border:1px solid var(--bd);color:var(--mut)}
.tag.ex{background:var(--ex);color:var(--card);border-color:var(--ex)}
.tag.cota{background:var(--cotabg);color:var(--cota);border-color:var(--cota)}
.tag.par{background:var(--parbg);color:var(--par);border-color:var(--par)}
.tag.novo{background:var(--novo);color:#fff;border-color:var(--novo)}
.prazo{font-weight:700;margin-left:auto}.prazo.urg{color:var(--novo)}
.obj{margin:4px 0 8px}.org{font-weight:600}.mut{color:var(--mut);font-size:.85rem}
dl{display:grid;grid-template-columns:max-content 1fr;gap:2px 10px;margin:6px 0;font-size:.88rem}
dt{color:var(--mut)}dd{margin:0}
.links a{display:inline-block;margin:6px 10px 0 0;color:var(--link);font-weight:600;text-decoration:none}
.vazio{padding:24px;text-align:center;color:var(--mut)}
"""


def _classe(situacao: str) -> str:
    return {EXCLUSIVA: "ex", COTA: "cota", PARCIAL: "par"}.get(situacao, "")


def gerar_html(registros: list[dict], caminho: Path, resumo: dict[str, Any]) -> Path:
    e = html.escape
    agora = datetime.now()
    cards = []
    for r in ordenar(registros):
        cls = _classe(r["situacao_me_epp"])
        enc = r.get("data_encerramento")
        urgente = enc is not None and (enc - agora).total_seconds() < 3 * 86400
        rotulo = ("★ " if cls == "ex" else "") + (r["situacao_me_epp"] or "—")
        tags = [f'<span class="tag {cls}">{e(rotulo)}</span>']
        if r.get("estado") == "nova":
            tags.insert(0, '<span class="tag novo">NOVA</span>')
        elif r.get("estado") == "atualizada":
            tags.insert(0, '<span class="tag">atualizada</span>')
        tags.append(f'<span class="tag">{e(r["esfera"])}</span>')
        links = []
        if r["link_pncp"]:
            links.append(f'<a href="{e(r["link_pncp"])}" target="_blank" rel="noopener">Edital no PNCP</a>')
        if r["link_origem"]:
            nome = r["sistema_origem"] or "Sistema de origem"
            links.append(f'<a href="{e(r["link_origem"])}" target="_blank" rel="noopener">{e(nome)}</a>')
        detalhes = [
            ("Município", r["municipio"]),
            ("Modalidade", r["modalidade"] + (f" nº {r['numero_compra']}" if r["numero_compra"] else "")),
            ("Valor estimado", ("R$ " + fmt_moeda(r["valor_estimado"])) if fmt_moeda(r["valor_estimado"]) else "não informado"),
            ("Propostas", f"{fmt_data(r['data_abertura'])} até {fmt_data(enc)}"),
            ("Itens", _itens_txt(r) and f"{_itens_txt(r)} (exclusivos/cota/total)"),
            ("Situação", r["situacao_compra"]),
            ("Nº PNCP", r["numero_controle"]),
        ]
        dl = "".join(f"<dt>{e(k)}</dt><dd>{e(str(v))}</dd>" for k, v in detalhes if v)
        cards.append(f"""<article class="card {cls}">
<div class="topo">{''.join(tags)}<span class="prazo{' urg' if urgente else ''}">⏰ {e(fmt_data(enc) or 's/ data')}</span></div>
<div class="org">{e(r['orgao'])}</div>
<div class="mut">{e(r['unidade'])}</div>
<p class="obj">{e(r['objeto'])}</p>
<dl>{dl}</dl>
<div class="links">{''.join(links)}</div>
</article>""")
    blocos_resumo = "".join(
        f"<div><b>{e(str(v))}</b><span>{e(k)}</span></div>" for k, v in [
            ("encontradas (GO)", resumo.get("encontradas", 0)),
            ("no filtro", resumo.get("filtradas", 0)),
            ("com benefício ME/EPP", resumo.get("me_epp", 0)),
            ("exclusivas ME/EPP", resumo.get("exclusivas", 0)),
            ("novas", resumo.get("novas", 0)),
        ])
    aviso = ""
    if resumo.get("falhas"):
        aviso = (f'<p class="mut">⚠ {resumo["falhas"]} requisição(ões) falharam; '
                 "veja o log. O resultado pode estar incompleto.</p>")
    corpo = "".join(cards) or '<p class="vazio">Nenhuma licitação encontrada com os filtros atuais.</p>'
    documento = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Licitações ar-condicionado GO</title><style>{CSS}</style></head>
<body><main>
<h1>Licitações de ar-condicionado — Goiás</h1>
<p class="sub">Gerado em {e(fmt_data(agora))} · fonte: PNCP · {e(resumo.get('parametros', ''))}</p>
<section class="resumo">{blocos_resumo}</section>{aviso}
{corpo}
</main></body></html>"""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(documento, encoding="utf-8")
    return caminho


def publicar(registros: list[dict], pasta: Path, resumo: dict[str, Any]) -> dict[str, Path]:
    """Gera arquivos com data/hora e cópias 'ultimo.*' (fáceis de abrir/agendar)."""
    carimbo = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = gerar_csv(registros, pasta / f"licitacoes_ac_go_{carimbo}.csv")
    html_path = gerar_html(registros, pasta / f"licitacoes_ac_go_{carimbo}.html", resumo)
    shutil.copyfile(csv_path, pasta / "ultimo.csv")
    shutil.copyfile(html_path, pasta / "ultimo.html")
    return {"csv": csv_path, "html": html_path}
