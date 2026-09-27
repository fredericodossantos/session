"""Monta o relatório HTML a partir do resumo executivo e das seções por área (Markdown)."""
from __future__ import annotations

import os
import re

import markdown

AQUI = os.path.dirname(os.path.abspath(__file__))
SECOES = [
    ("climatizacao", "Climatização e PMOC"),
    ("refrigeracao", "Refrigeração comercial"),
    ("iluminacao_publica", "Iluminação pública"),
    ("eletrica_predial", "Elétrica predial"),
    ("munck", "Caminhão munck"),
    ("manutencao_predial", "Manutenção predial integrada"),
]

CSS = """
:root{--paper:#f5f7f6;--card:#ffffff;--ink:#17252a;--muted:#55666b;--line:#d5dedd;
--accent:#0e5c63;--accent-soft:#e3efef;--go:#2b7a4b;--go-soft:#e2f1e8;--sel:#a86d06;--sel-soft:#f7ecd6;
--no:#a63a2f;--no-soft:#f6e1de;--code:#eef2f1}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--paper:#10181b;--card:#172226;
--ink:#e4ecec;--muted:#9fb0b3;--line:#2c3b40;--accent:#5fb8bf;--accent-soft:#16363a;--go:#6cc592;--go-soft:#173526;
--sel:#e0a93f;--sel-soft:#3a2d12;--no:#ec8a7f;--no-soft:#3d1e1a;--code:#1d2a2e}}
:root[data-theme="dark"]{color-scheme:dark;--paper:#10181b;--card:#172226;--ink:#e4ecec;--muted:#9fb0b3;--line:#2c3b40;
--accent:#5fb8bf;--accent-soft:#16363a;--go:#6cc592;--go-soft:#173526;--sel:#e0a93f;--sel-soft:#3a2d12;--no:#ec8a7f;
--no-soft:#3d1e1a;--code:#1d2a2e}
body{background:var(--paper);color:var(--ink);font:16px/1.6 "Source Sans 3",system-ui,sans-serif;padding-inline:16px;padding-block:24px 64px}
.wrap{max-width:900px;margin:0 auto;display:flex;flex-direction:column;gap:28px}
h1,h2,h3,h4{font-family:"Archivo",system-ui,sans-serif;line-height:1.2;text-wrap:balance;margin:0}
h1{font-size:2rem;font-weight:700;letter-spacing:-.01em}
h2{font-size:1.45rem;font-weight:700;margin-top:.4em}
h3{font-size:1.12rem;font-weight:650;margin-top:1.2em}
h4{font-size:1rem;font-weight:650;margin-top:1em}
p,li{max-width:70ch}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.eyebrow{font:600 .75rem/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.lead{color:var(--muted);font-size:1.05rem;margin:.4em 0 0}
header{display:flex;flex-direction:column;gap:10px;border-bottom:2px solid var(--ink);padding-bottom:18px}
.meta{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--muted);font-size:.9rem}
nav{display:flex;flex-wrap:wrap;gap:8px}
nav a{font-size:.88rem;text-decoration:none;border:1px solid var(--line);background:var(--card);padding:4px 10px;border-radius:999px;color:var(--ink)}
section.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:22px 24px}
.table-wrap{overflow-x:auto;margin:.8em 0}
table{border-collapse:collapse;width:100%;font-size:.92rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:650;background:var(--accent-soft)}
code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.85em;background:var(--code);padding:1px 4px;border-radius:3px}
.pill{display:inline-block;font:600 .74rem/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.05em;text-transform:uppercase;padding:5px 8px;border-radius:4px;white-space:nowrap}
.atacar{background:var(--go-soft);color:var(--go)}.seletivo{background:var(--sel-soft);color:var(--sel)}.evitar{background:var(--no-soft);color:var(--no)}
details.area{background:var(--card);border:1px solid var(--line);border-radius:10px}
details.area>summary{cursor:pointer;list-style:none;padding:16px 22px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
details.area>summary::-webkit-details-marker{display:none}
details.area>summary h2{margin:0;font-size:1.25rem}
details.area>summary .hint{color:var(--muted);font-size:.85rem}
details.area[open]>summary{border-bottom:1px solid var(--line)}
.area-body{padding:6px 24px 22px}
blockquote{margin:1em 0;padding:8px 14px;border-left:3px solid var(--accent);background:var(--accent-soft);color:var(--ink)}
footer{color:var(--muted);font-size:.85rem}
@media (max-width:520px){section.card{padding:16px}.area-body{padding:4px 14px 16px}details.area>summary{padding:14px}}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
"""

FONTES = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700'
          '&family=IBM+Plex+Mono:wght@500;600&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap">')


def _normalizar_listas(texto: str) -> str:
    """Python-Markdown exige linha em branco antes de lista e 4 espaços para aninhar."""
    saida: list[str] = []
    item = re.compile(r"^\s*(?:[-*]|\d+\.)\s")
    for linha in texto.splitlines():
        recuo = len(linha) - len(linha.lstrip(" "))
        if 0 < recuo < 4 and linha.strip():
            linha = "    " + linha.lstrip(" ")
        anterior = saida[-1] if saida else ""
        if item.match(linha) and anterior.strip() and not item.match(anterior) \
                and not anterior.startswith("    ") and not linha.startswith("    "):
            saida.append("")
        saida.append(linha)
    return "\n".join(saida)


def md(texto: str) -> str:
    html = markdown.markdown(_normalizar_listas(texto), extensions=["tables", "sane_lists"])
    html = re.sub(r"<table>", '<div class="table-wrap"><table>', html)
    html = html.replace("</table>", "</table></div>")
    html = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', html)
    return html


def ler(nome: str) -> str:
    caminho = os.path.join(AQUI, "relatorio_partes", nome)
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def main() -> int:
    resumo = ler("resumo.md")
    classes = {}
    for linha in ler("ranking.txt").splitlines():
        if "|" in linha:
            area, classe = [x.strip() for x in linha.split("|", 1)]
            classes[area] = classe
    partes = []
    for chave, titulo in SECOES:
        caminho = os.path.join(AQUI, "relatorio_partes", f"{chave}.md")
        if not os.path.exists(caminho):
            continue
        classe = classes.get(chave, "seletivo")
        corpo = md(ler(f"{chave}.md"))
        partes.append(
            f'<details class="area" id="{chave}"><summary><h2>{titulo}</h2>'
            f'<span class="pill {classe}">{classe}</span></summary>'
            f'<div class="area-body">{corpo}</div></details>')
    nav = "".join(f'<a href="#{k}">{t}</a>' for k, t in SECOES
                  if os.path.exists(os.path.join(AQUI, "relatorio_partes", f"{k}.md")))
    finais = md(ler("finais.md"))
    html = f"""<title>Mercado de Manutenção GO</title>
{FONTES}
<style>{CSS}</style>
<div class="wrap">
<header>
<span class="eyebrow">Estudo de mercado · licitações públicas · 2024–2026</span>
<h1>Onde a empresa deve disputar licitações em Goiás</h1>
<p class="lead">Climatização, refrigeração, iluminação pública, elétrica predial, munck e manutenção predial:
volume, desconto vencedor, margem e investimento, com dados do PNCP.</p>
<div class="meta"><span>Dados: PNCP, editais encerrados de set/2024 a set/2026</span><span>Acesso: 27/09/2026</span>
<span>GO + amostra de DF, MT, MS, TO e MG</span></div>
<nav>{nav}<a href="#riscos">Riscos e limitações</a></nav>
</header>
<section class="card" id="resumo">{md(resumo)}</section>
{''.join(partes)}
<section class="card" id="riscos">{finais}</section>
<footer>Planilha com os dados brutos (um caso por linha, com link do PNCP) e os indicadores calculados por
fórmula: <code>estudo_mercado.xlsx</code>. Método, premissas e fontes de preço estão no fim de cada seção.</footer>
</div>
"""
    destino = os.path.join(AQUI, "relatorio_mercado.html")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[relatorio] {destino} ({len(html)//1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
