#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Constantes, regexes e funcoes compartilhadas pelo pipeline de analise
(casos.py, indicadores.py, planilha.py).

Nao faz nenhuma chamada de rede e nao mexe em nada dentro de W/compras,
W/textos, W/*hits*.jsonl, W/selecao.jsonl ou W/stats.json -- so le.
"""

import json
import os
import re
import statistics
import unicodedata

# --------------------------------------------------------------------------
# Caminhos
# --------------------------------------------------------------------------

ANALISE_DIR = os.path.dirname(os.path.abspath(__file__))
W = os.path.dirname(ANALISE_DIR)  # pasta "mercado"

TESTE_DIR = os.path.join(W, "_teste_validacao")

CUSTOS_REFERENCIAS_PATH = os.path.join(W, "custos", "custos", "referencias.json")

AREAS = [
    "climatizacao",
    "refrigeracao",
    "iluminacao_publica",
    "eletrica_predial",
    "munck",
    "manutencao_predial",
]

UF_PRINCIPAL = "GO"
UFS_VIZINHAS = ["DF", "MT", "MS", "TO", "MG"]

ESFERA_MAP = {"F": "Federal", "E": "Estadual", "M": "Municipal", "D": "Distrital"}


def raiz_paths(raiz):
    """Dado um diretorio raiz (W ou W/_teste_validacao), devolve os caminhos
    dos arquivos/pastas que casos.py e indicadores.py precisam ler."""
    return {
        "compras_dir": os.path.join(raiz, "compras"),
        "textos_dir": os.path.join(raiz, "textos"),
        "selecao_path": os.path.join(raiz, "selecao.jsonl"),
        "go_hits_path": os.path.join(raiz, "go_hits.jsonl"),
    }


# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------

def strip_accents(s):
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s):
    """minusculo + sem acento -- usado so para TESTAR match de regex 'ascii',
    nunca para extrair trechos (trechos sempre vem do texto original)."""
    return strip_accents(s or "").lower()


def tipo_item(it):
    """'M' (material) ou 'S' (servico) para um item de compra.

    Usa o codigo 'materialOuServico' como base, mas corrige pelo texto de
    'materialOuServicoNome' quando os dois discordam -- ha orgaos no PNCP
    que classificam item de SERVICO com o codigo 'M' (ex.: "Servico de
    manutencao corretiva..." com materialOuServico='M' e
    materialOuServicoNome='Servico'). Isso evita que servicos de manutencao
    mal cadastrados sejam confundidos com fornecimento puro de material.
    """
    nome = norm(it.get("materialOuServicoNome"))
    if "servi" in nome:
        return "S"
    if "material" in nome:
        return "M"
    return it.get("materialOuServico")


def as_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def snippet(texto, match, antes=100, depois=180, limite=300):
    """Extrai um trecho curto (<= limite caracteres) do texto ORIGINAL ao
    redor de um re.Match, para servir de evidencia."""
    if texto is None or match is None:
        return None
    ini = max(0, match.start() - antes)
    fim = min(len(texto), match.end() + depois)
    trecho = texto[ini:fim].strip()
    trecho = re.sub(r"\s+", " ", trecho)
    if len(trecho) > limite:
        trecho = trecho[:limite].rstrip() + "…"
    return trecho


def find_bool_evidencia(texto, pattern):
    """Roda 'pattern' (compilado, IGNORECASE) no texto original; devolve
    (bool, trecho_evidencia|None)."""
    if not texto:
        return False, None
    m = pattern.search(texto)
    if not m:
        return False, None
    return True, snippet(texto, m)


# --------------------------------------------------------------------------
# area_principal -- prioridade do termo mais especifico para o mais generico.
# Repare que a regex de "climatizacao" do coletor.py tambem casa "refrigera"
# (proposital, para nao perder hits na fase de busca); aqui, para escolher
# UMA area principal por caso, usamos regexes mais estreitas e uma ordem de
# prioridade explicita, documentada no README.
# --------------------------------------------------------------------------

AREA_PRIORIDADE = [
    "munck",
    "iluminacao_publica",
    "refrigeracao",
    "climatizacao",
    "eletrica_predial",
    "manutencao_predial",
]

AREA_REGEX_ESPECIFICO = {
    "munck": re.compile(r"munck|guindauto|guindaste|i[cç]amento|cesto a[eé]reo|cesta a[eé]rea|plataforma elevat[oó]ria"),
    "iluminacao_publica": re.compile(r"ilumina[cç][aã]o p[uú]blica|parque de ilumina|rede de ilumina|ilumina[cç][aã]o (viaria|urbana)|luminaria|par[qk]ue.{0,15}ilumina"),
    "refrigeracao": re.compile(r"c[aâ]mara fria|bebedouro|freezer|geladeira|frigorifico|refrigerador(es)?\b"),
    "climatizacao": re.compile(r"ar[- ]condicionado|condicionador de ar|climatiza[cç][aã]o|\bsplit\b|\bpmoc\b"),
    "eletrica_predial": re.compile(r"el[eé]trica predial|instala[cç](oes|ões) el[eé]tricas|\bspda\b|para-raio|aterramento|subesta[cç][aã]o|termograf|quadro(s)? el[eé]trico"),
    "manutencao_predial": re.compile(r"manuten[cç][aã]o predial|predial integrada|predial preventiva"),
}


def area_principal(objeto, areas_encontradas):
    obj = objeto or ""
    for area in AREA_PRIORIDADE:
        rx = AREA_REGEX_ESPECIFICO.get(area)
        if rx and rx.search(obj):
            return area
    # nada bateu no objeto -- cai para a lista de areas em que o caso foi
    # encontrado na fase de indice (coletor.py), na mesma ordem de prioridade
    if areas_encontradas:
        for area in AREA_PRIORIDADE:
            if area in areas_encontradas:
                return area
        return sorted(areas_encontradas)[0]
    return None


# --------------------------------------------------------------------------
# tipo_contrato / vigencia_meses
# --------------------------------------------------------------------------

RX_CONTINUADO = re.compile(r"continuad")
RX_MESES_PARENT = re.compile(r"(\d{1,3})\s*\([^)]{0,25}\)\s*mes(es)?\b")
RX_MESES_SIMPLES = re.compile(r"(\d{1,3})\s*mes(es)?\b")
RX_MENSAL = re.compile(r"\bmensal\b|\bpor m[eê]s\b")
RX_PONTUAL = re.compile(r"\baquisi[cç][aã]o\b|\bfornecimento\b|\beventual\b|\bconforme a necessidade\b|\bsob demanda\b|\bregistro de pre[cç]os para eventual\b")


def extrai_vigencia_meses(*textos):
    for t in textos:
        if not t:
            continue
        m = RX_MESES_PARENT.search(t)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    for t in textos:
        if not t:
            continue
        m = RX_MESES_SIMPLES.search(t)
        if m:
            try:
                n = int(m.group(1))
                if 1 <= n <= 120:
                    return n
            except ValueError:
                pass
    return None


def classifica_tipo_contrato(objeto, itens, texto):
    partes = [objeto or ""]
    if texto:
        partes.append(texto[:20000])  # nao precisa varrer o documento inteiro
    unidades = " ".join(norm(it.get("unidadeMedida")) for it in (itens or []) if it.get("unidadeMedida"))
    partes.append(unidades)
    combinado = norm(" ".join(partes))

    sinal_continuado = bool(
        RX_CONTINUADO.search(combinado)
        or RX_MENSAL.search(combinado)
        or re.search(r"\bmes\b|\bmeses\b", unidades)
    )
    if sinal_continuado:
        return "continuado"
    if RX_PONTUAL.search(combinado):
        return "pontual"
    return "indefinido"


# --------------------------------------------------------------------------
# n_participantes (o PNCP nao publica; tenta extrair do texto do edital/TR)
# --------------------------------------------------------------------------

RX_PARTICIPANTES = [
    re.compile(r"participaram\s+(\d{1,4})\s*(empresas|licitantes|fornecedores|propon)"),
    re.compile(r"(\d{1,4})\s*(empresas|licitantes|fornecedores)\s+participar"),
    re.compile(r"(\d{1,4})\s*licitantes\b"),
]


def extrai_n_participantes(texto):
    if not texto:
        return None
    for rx in RX_PARTICIPANTES:
        m = rx.search(texto)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


# --------------------------------------------------------------------------
# exigencias tecnicas (so quando ha texto do edital/TR baixado)
# --------------------------------------------------------------------------

RX_CESTO_AEREO = re.compile(r"cesto a[eé]reo|cesta a[eé]rea")
RX_MUNCK_GUINDAUTO = re.compile(r"munck|guindauto|guindaste")
RX_MUNCK_COM_CESTO = re.compile(r"munck.{0,60}cesto|guindauto.{0,60}cesto|cesto.{0,60}acopl", re.IGNORECASE)
RX_FROTA_MINIMA = re.compile(
    r"(frota m[ií]nima[^.\n]{0,200}|no m[ií]nimo\s+\d+\s*(caminh[oõ]es|ve[ií]culos)[^.\n]{0,150}|"
    r"quantidade m[ií]nima de\s*(caminh[oõ]es|ve[ií]culos|equipamentos)[^.\n]{0,150})",
    re.IGNORECASE,
)
RX_PMOC_RT_CI = re.compile(r"\bpmoc\b|respons[aá]vel t[eé]cnico", re.IGNORECASE)
# ART/RRT (Anotacao/Registro de Responsabilidade Tecnica) so em maiusculas e
# sem ponto logo depois, pra nao confundir com "Art. 84" (citacao de lei).
RX_ART_RRT = re.compile(r"\bART\b(?!\.)|\bRRT\b(?!\.)")


class _RxPmocRt:
    """Combina as duas regras acima num objeto com .search() unico."""

    def search(self, texto):
        return RX_PMOC_RT_CI.search(texto) or RX_ART_RRT.search(texto)


RX_PMOC_RT = _RxPmocRt()
RX_ATESTADOS = re.compile(
    r"(atestado(s)?\s+de\s+capacidade\s+t[eé]cnica[^.\n]{0,200}|"
    r"comprova[cç][aã]o\s+de\s+(capacidade|qualifica[cç][aã]o)\s+t[eé]cnica[^.\n]{0,200}|"
    r"quantitativo(s)?\s+m[ií]nimo(s)?[^.\n]{0,150})",
    re.IGNORECASE,
)
RX_CREA_CFT = re.compile(r"\bcrea\b|\bcft\b|conselho regional de engenharia", re.IGNORECASE)


def extrai_exigencias(texto):
    tem_texto = texto is not None
    out = {"tem_texto": tem_texto}

    def bool_campo(rx):
        ok, ev = find_bool_evidencia(texto, rx)
        return {"valor": ok, "evidencia": ev}

    def trecho_campo(rx):
        if not texto:
            return {"trecho": None}
        m = rx.search(texto)
        if not m:
            return {"trecho": None}
        return {"trecho": snippet(texto, m)}

    out["cesto_aereo"] = bool_campo(RX_CESTO_AEREO)
    out["munck_guindauto"] = bool_campo(RX_MUNCK_GUINDAUTO)
    out["aceita_munck_com_cesto"] = bool_campo(RX_MUNCK_COM_CESTO)
    out["frota_minima"] = trecho_campo(RX_FROTA_MINIMA)
    out["pmoc_responsavel_tecnico"] = bool_campo(RX_PMOC_RT)
    out["atestados"] = trecho_campo(RX_ATESTADOS)
    out["crea_cft"] = bool_campo(RX_CREA_CFT)
    return out


# --------------------------------------------------------------------------
# exclusao (motivo + evidencia + revisao_manual)
# --------------------------------------------------------------------------

RX_MENCAO_PASSAGEM = re.compile(
    r"\bve[ií]culo(s)?\b|\b[oô]nibus\b|\bambul[aâ]ncia\b|\bmicro[- ]?[oô]nibus\b|"
    r"\bevento(s)?\b.{0,50}(gerador|ar condicionado)|(gerador|ar condicionado).{0,50}\bevento(s)?\b"
)
RX_EQUIP_ALTO = re.compile(
    r"\bgerador(es)?\b|grupo gerador|subesta[cç][aã]o (nova|completa)|\bchiller\b|\bvrf\b|"
    r"central de [aá]gua gelada|usina solar|energia solar fotovoltaica|placa(s)? solar"
)
RX_OBRA_GRANDE = re.compile(r"implanta[cç][aã]o|constru[cç][aã]o de|amplia[cç][aã]o de rede")

LIMIAR_OBRA_GRANDE = 1_500_000.0
LIMIAR_FRAC_MATERIAL_ALTO = 0.40
LIMIAR_FRAC_MATERIAL_REVISAO = (0.30, 0.40)


def avalia_exclusao(objeto, itens, valor_estimado_total, frac_material):
    obj_norm = norm(objeto)
    revisao_manual = False

    m = RX_MENCAO_PASSAGEM.search(obj_norm)
    if m:
        # evidencia extraida do objeto normalizado (sem acento) -- o match
        # foi encontrado nele, e o objeto original pode nao alinhar 1:1
        # apos a remocao de acentos.
        return {
            "motivo": "mencao_passagem",
            "evidencia": snippet(obj_norm, m),
            "revisao_manual": False,
        }

    itens_validos = [it for it in (itens or []) if tipo_item(it) in ("M", "S")]
    if itens_validos and all(tipo_item(it) == "M" for it in itens_validos):
        # sinal de conflito: objeto fala de servico mas todo item foi
        # classificado como material -- mantem a exclusao (regra literal)
        # mas marca para revisao manual.
        obj_fala_servico = bool(re.search(r"\bmanuten[cç]|\bservi[cç]o|presta[cç][aã]o de servi", obj_norm))
        return {
            "motivo": "fornecimento_puro",
            "evidencia": f"{len(itens_validos)} item(ns), todos classificados como material (sem servico).",
            "revisao_manual": obj_fala_servico,
        }

    if RX_OBRA_GRANDE.search(obj_norm) and valor_estimado_total is not None:
        if valor_estimado_total > LIMIAR_OBRA_GRANDE:
            return {
                "motivo": "obra_grande",
                "evidencia": f"objeto sugere implantacao/construcao/ampliacao e valor estimado "
                             f"R$ {valor_estimado_total:,.2f} > limiar de R$ {LIMIAR_OBRA_GRANDE:,.2f}.",
                "revisao_manual": False,
            }
        if valor_estimado_total > LIMIAR_OBRA_GRANDE * 0.6:
            revisao_manual = True

    m_equip = RX_EQUIP_ALTO.search(obj_norm)
    frac_alta = frac_material is not None and frac_material > LIMIAR_FRAC_MATERIAL_ALTO
    if m_equip or frac_alta:
        if m_equip:
            ev = snippet(obj_norm, m_equip)
        else:
            ev = f"fracao estimada em itens de material = {frac_material:.0%} (> {LIMIAR_FRAC_MATERIAL_ALTO:.0%})."
        return {"motivo": "equipamento_alto", "evidencia": ev, "revisao_manual": False}

    if frac_material is not None and LIMIAR_FRAC_MATERIAL_REVISAO[0] <= frac_material <= LIMIAR_FRAC_MATERIAL_REVISAO[1]:
        revisao_manual = True

    if not itens:
        revisao_manual = True

    return {"motivo": None, "evidencia": None, "revisao_manual": revisao_manual}


# --------------------------------------------------------------------------
# estatisticas (usadas por indicadores.py) -- median / quartis "inclusive"
# (mesmo metodo do QUARTILE.INC / PERCENTILE.INC do Excel e da Calc, para
# que os numeros batam com as formulas da planilha).
# --------------------------------------------------------------------------

def mediana(valores):
    vs = [v for v in valores if v is not None]
    if not vs:
        return None
    return statistics.median(vs)


def quartis(valores):
    """Devolve (q1, q3) pelo metodo 'inclusive' (R-7), igual ao
    QUARTILE.INC do Excel/LibreOffice. Precisa de pelo menos 2 valores."""
    vs = sorted(v for v in valores if v is not None)
    if len(vs) < 2:
        return (None, None) if len(vs) == 0 else (vs[0], vs[0])
    q1, _, q3 = statistics.quantiles(vs, n=4, method="inclusive")
    return (q1, q3)


def carregar_jsonl(path):
    out = []
    if not path or not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out
