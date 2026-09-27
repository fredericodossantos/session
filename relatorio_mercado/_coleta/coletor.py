#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coletor de dados do PNCP para estudo de mercado de licitacoes de engenharia
(manutencao de ar-condicionado, refrigeracao, iluminacao publica, eletrica
predial, caminhao munck).

So coleta dados brutos; nao analisa merito. Grava tudo de forma incremental
para permitir retomada em caso de queda.
"""

import argparse
import io
import json
import logging
import os
import re
import sys
import time
import traceback
import unicodedata
import zipfile
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

# --------------------------------------------------------------------------
# Configuracao geral
# --------------------------------------------------------------------------

W = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(W, "coletor.log")
STATS_PATH = os.path.join(W, "stats.json")
CHECKPOINT_PATH = os.path.join(W, "checkpoint.json")

GO_RAW_PATH = os.path.join(W, "go_hits_raw.jsonl")
VIZ_RAW_PATH = os.path.join(W, "viz_hits_raw.jsonl")
GO_HITS_PATH = os.path.join(W, "go_hits.jsonl")
VIZ_HITS_PATH = os.path.join(W, "viz_hits.jsonl")
SELECAO_PATH = os.path.join(W, "selecao.jsonl")
COMPRAS_DIR = os.path.join(W, "compras")
TEXTOS_DIR = os.path.join(W, "textos")
FALHAS_TEXTOS_PATH = os.path.join(TEXTOS_DIR, "falhas.jsonl")

os.makedirs(COMPRAS_DIR, exist_ok=True)
os.makedirs(TEXTOS_DIR, exist_ok=True)

BASE_SEARCH = "https://pncp.gov.br/api/search/"
BASE_DETALHE = "https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
BASE_ITENS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens"
BASE_RESULTADOS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{num_item}/resultados"
BASE_ARQUIVOS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos"
LINK_PUBLICO = "https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"

USER_AGENT = "estudo-mercado-licitacoes-go/1.0 (consultas publicas)"
HEADERS = {"User-Agent": USER_AGENT}

CUTOFF_DATE = "2024-09-27"  # periodo: 24 meses antes de 2026-09-27

UF_PRINCIPAL = "GO"
UFS_VIZINHAS = ["DF", "MT", "MS", "TO", "MG"]

MODALIDADES_COMPETITIVAS = {4, 5, 6, 7}
MODALIDADE_DISPENSA = 8

MAX_PAGINAS_GO = 15
MAX_PAGINAS_VIZ = 3
TAM_PAGINA = 100

MAX_CANDIDATOS_GO = 90
MAX_CANDIDATOS_VIZ = 8
MAX_ITENS_RESULTADO = 40
MAX_TEXTOS_POR_AREA = 30

MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024

EXEC_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".msi", ".com", ".scr", ".jar", ".ps1", ".vbs"}

TERMS = {
    "climatizacao": [
        "manutenção ar condicionado",
        "manutenção preventiva corretiva condicionadores de ar",
        "PMOC",
        "higienização ar condicionado",
        "instalação ar condicionado split",
        "climatização manutenção",
        "recarga gás ar condicionado",
    ],
    "refrigeracao": [
        "manutenção câmara fria",
        "manutenção refrigeração",
        "manutenção bebedouros",
        "manutenção refrigeradores freezers",
        "manutenção equipamentos de refrigeração",
    ],
    "iluminacao_publica": [
        "manutenção iluminação pública",
        "iluminação pública",
        "parque de iluminação pública",
        "ampliação rede iluminação pública",
    ],
    "eletrica_predial": [
        "manutenção elétrica predial",
        "manutenção instalações elétricas",
        "SPDA",
        "para-raios manutenção",
        "aterramento laudo",
        "manutenção subestação",
        "termografia",
        "quadros elétricos manutenção",
        "laudo instalações elétricas",
    ],
    "munck": [
        "locação caminhão munck",
        "caminhão guindauto",
        "caminhão munck com operador",
        "içamento",
        "implantação de postes",
        "caminhão cesto aéreo locação",
    ],
    "manutencao_predial": [
        "manutenção predial preventiva corretiva",
        "manutenção predial elétrica hidráulica",
        "manutenção predial integrada",
    ],
}

REGEX_AREA = {
    "climatizacao": re.compile(r"ar condicionado|condicionador|climatiz|split|pmoc|refrigera"),
    "iluminacao_publica": re.compile(r"ilumina"),
    "munck": re.compile(r"munck|guindauto|guindaste|icamento|poste|cesto aereo"),
    "eletrica_predial": re.compile(r"eletric|spda|para-raio|aterramento|subestac|termograf|quadro"),
    "refrigeracao": re.compile(r"camara fria|refrigera|bebedouro|freezer|geladeira|frigor"),
    "manutencao_predial": re.compile(r"manutencao predial|predial"),
}

NOISE_RE = re.compile(
    r"\bveiculo|\bonibus|\bambulancia|\bpneu|\bcombustivel|peca(s)? automotiv"
)

AREAS_TEXTO = {"iluminacao_publica", "munck", "climatizacao", "eletrica_predial", "manutencao_predial"}

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

logger = logging.getLogger("coletor")
logger.setLevel(logging.INFO)
_fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_fh)
logger.addHandler(_sh)

# --------------------------------------------------------------------------
# Estatisticas / checkpoint
# --------------------------------------------------------------------------

STATS = {
    "inicio": None,
    "fim": None,
    "http_requests": 0,
    "http_429": 0,
    "http_erros_definitivos": 0,
    "hits_go_por_area": {},
    "hits_viz_por_area_uf": {},
    "hits_go_total_dedup": 0,
    "hits_viz_total_dedup": 0,
    "candidatos_go_por_area": {},
    "candidatos_viz_por_area_uf": {},
    "compras_detalhadas": 0,
    "compras_com_erro": 0,
    "itens_total": 0,
    "resultados_total": 0,
    "textos_baixados_por_area": {},
    "textos_falhas": 0,
}


def salvar_stats():
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(STATS, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("falha ao salvar stats.json")


def carregar_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("checkpoint.json corrompido, recomecando checkpoint")
    return {"phase1_go_done": [], "phase1_viz_done": []}


def salvar_checkpoint(cp):
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(cp, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# HTTP com throttle (1 req/s) e retentativas
# --------------------------------------------------------------------------

_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)
_LAST_REQUEST_TS = [0.0]
MIN_INTERVAL = 1.0
RETRY_WAITS = [2, 4, 8, 16, 30, 60]


def _throttle():
    now = time.time()
    elapsed = now - _LAST_REQUEST_TS[0]
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _LAST_REQUEST_TS[0] = time.time()


def http_get(url, params=None, stream=False, timeout=60):
    """GET com throttle global, ate 6 retentativas em falha de rede, e espera
    em 429 conforme Retry-After (ou 120s). Retorna a Response ou None se
    esgotar as tentativas em erro definitivo (5xx persistente)."""
    attempt = 0
    while True:
        _throttle()
        STATS["http_requests"] += 1
        try:
            resp = _SESSION.get(url, params=params, timeout=timeout, stream=stream)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            if attempt >= len(RETRY_WAITS):
                logger.error("falha de rede definitiva em %s: %s", url, e)
                STATS["http_erros_definitivos"] += 1
                return None
            wait = RETRY_WAITS[attempt]
            logger.warning("falha de rede (%s) em %s; tentativa %d/6, esperando %ds",
                            e.__class__.__name__, url, attempt + 1, wait)
            time.sleep(wait)
            attempt += 1
            continue

        if resp.status_code == 429:
            STATS["http_429"] += 1
            retry_after = resp.headers.get("Retry-After")
            try:
                wait = int(float(retry_after))
            except (TypeError, ValueError):
                wait = 120
            logger.warning("HTTP 429 em %s; esperando %ds (Retry-After=%s)", url, wait, retry_after)
            time.sleep(wait)
            continue  # nao conta como tentativa, so espera e tenta de novo

        if resp.status_code >= 500:
            if attempt >= len(RETRY_WAITS):
                logger.error("HTTP %d definitivo em %s", resp.status_code, url)
                STATS["http_erros_definitivos"] += 1
                return resp
            wait = RETRY_WAITS[attempt]
            logger.warning("HTTP %d em %s; tentativa %d/6, esperando %ds",
                            resp.status_code, url, attempt + 1, wait)
            time.sleep(wait)
            attempt += 1
            continue

        return resp


def http_get_json(url, params=None):
    resp = http_get(url, params=params)
    if resp is None:
        return None, None
    if resp.status_code != 200:
        return None, resp
    try:
        return resp.json(), resp
    except ValueError:
        # corpo vazio/invalido apos 200 -- trata como falha de rede pontual
        logger.warning("JSON invalido em %s (status 200, corpo ilegivel)", url)
        return None, resp


# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------

def strip_accents(s):
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s):
    return strip_accents(s or "").lower()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# FASE 1 -- indice de busca
# --------------------------------------------------------------------------

def buscar_pagina(termo, uf, pagina):
    params = {
        "q": termo,
        "tipos_documento": "edital",
        "ordenacao": "-data",
        "pagina": pagina,
        "tam_pagina": TAM_PAGINA,
        "status": "encerradas",
        "ufs": uf,
    }
    data, resp = http_get_json(BASE_SEARCH, params=params)
    return data


def coletar_termo(area, termo, uf, max_paginas, raw_path):
    """Pagina a busca para (area, termo, uf) ate estourar o periodo ou
    max_paginas; grava cada item bruto em raw_path (JSONL, incremental)."""
    total_itens = 0
    pagina = 1
    with open(raw_path, "a", encoding="utf-8") as fout:
        while pagina <= max_paginas:
            data = buscar_pagina(termo, uf, pagina)
            if not data or "items" not in data:
                logger.warning("busca sem resultado utilizavel: area=%s termo=%r uf=%s pagina=%d",
                                area, termo, uf, pagina)
                break
            items = data.get("items") or []
            if not items:
                break
            for item in items:
                item["_area"] = area
                item["_termo"] = termo
                fout.write(json.dumps(item, ensure_ascii=False) + "\n")
            total_itens += len(items)
            ultima_data = items[-1].get("data_publicacao_pncp") or ""
            logger.info("busca area=%s termo=%r uf=%s pagina=%d itens=%d ultima_data=%s",
                        area, termo, uf, pagina, len(items), ultima_data)
            if ultima_data and ultima_data[:10] < CUTOFF_DATE:
                break
            if len(items) < TAM_PAGINA:
                break
            pagina += 1
    return total_itens


def fase1_indice(cp, apenas_termos=None, apenas_go=False):
    logger.info("=== FASE 1: indice de busca ===")
    # GO
    for area, termos in TERMS.items():
        for termo in termos:
            if apenas_termos and (area, termo) not in apenas_termos:
                continue
            key = f"{area}|{termo}|GO"
            if key in cp["phase1_go_done"]:
                logger.info("GO ja coletado, pulando: %s", key)
                continue
            n = coletar_termo(area, termo, "GO", MAX_PAGINAS_GO, GO_RAW_PATH)
            STATS["hits_go_por_area"][area] = STATS["hits_go_por_area"].get(area, 0) + n
            cp["phase1_go_done"].append(key)
            salvar_checkpoint(cp)
            salvar_stats()

    if apenas_go:
        _mesclar_hits(GO_RAW_PATH, GO_HITS_PATH, "go")
        return

    # UFs vizinhas
    for uf in UFS_VIZINHAS:
        for area, termos in TERMS.items():
            for termo in termos:
                if apenas_termos and (area, termo) not in apenas_termos:
                    continue
                key = f"{area}|{termo}|{uf}"
                if key in cp["phase1_viz_done"]:
                    logger.info("viz ja coletado, pulando: %s", key)
                    continue
                n = coletar_termo(area, termo, uf, MAX_PAGINAS_VIZ, VIZ_RAW_PATH)
                dkey = f"{area}|{uf}"
                STATS["hits_viz_por_area_uf"][dkey] = STATS["hits_viz_por_area_uf"].get(dkey, 0) + n
                cp["phase1_viz_done"].append(key)
                salvar_checkpoint(cp)
                salvar_stats()

    _mesclar_hits(GO_RAW_PATH, GO_HITS_PATH, "go")
    _mesclar_hits(VIZ_RAW_PATH, VIZ_HITS_PATH, "viz")


def _chave_hit(item):
    ncp = item.get("numero_controle_pncp")
    if ncp:
        return ncp
    return f"{item.get('orgao_cnpj')}_{item.get('ano')}_{item.get('numero_sequencial')}"


def _mesclar_hits(raw_path, out_path, escopo):
    if not os.path.exists(raw_path):
        logger.info("sem arquivo bruto para mesclar: %s", raw_path)
        return
    dedup = {}
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            k = _chave_hit(item)
            area = item.pop("_area", None)
            termo = item.pop("_termo", None)
            if k not in dedup:
                item["area_termos"] = []
                dedup[k] = item
            par = [area, termo]
            if par not in dedup[k]["area_termos"]:
                dedup[k]["area_termos"].append(par)
    with open(out_path, "w", encoding="utf-8") as fout:
        for item in dedup.values():
            fout.write(json.dumps(item, ensure_ascii=False) + "\n")
    logger.info("mesclagem %s: %d hits unicos gravados em %s", escopo, len(dedup), out_path)
    if escopo == "go":
        STATS["hits_go_total_dedup"] = len(dedup)
    else:
        STATS["hits_viz_total_dedup"] = len(dedup)
    salvar_stats()


# --------------------------------------------------------------------------
# FASE 2 -- selecao de candidatos
# --------------------------------------------------------------------------

def _avalia_candidato(item, area):
    """Retorna (aceito: bool, motivo: str)."""
    modalidade_raw = item.get("modalidade_licitacao_id")
    try:
        modalidade = int(modalidade_raw)
    except (TypeError, ValueError):
        modalidade = None
    if modalidade == MODALIDADE_DISPENSA:
        return False, "dispensa_somente_indice"
    if modalidade not in MODALIDADES_COMPETITIVAS:
        return False, f"modalidade_nao_competitiva:{modalidade_raw}"
    if not item.get("tem_resultado"):
        return False, "sem_resultado"
    if item.get("cancelado"):
        return False, "cancelado"
    data_pub = (item.get("data_publicacao_pncp") or "")[:10]
    if not data_pub or data_pub < CUTOFF_DATE:
        return False, "fora_do_periodo"
    desc = norm(item.get("description"))
    if NOISE_RE.search(desc):
        return False, "ruido_obvio"
    regex = REGEX_AREA.get(area)
    if regex is None or not regex.search(desc):
        return False, "regex_area_nao_bate"
    return True, "selecionado"


def fase2_selecao():
    logger.info("=== FASE 2: selecao de candidatos ===")
    candidatos_go = {}  # area -> list of item
    candidatos_viz = {}  # (area,uf) -> list of item

    with open(SELECAO_PATH, "w", encoding="utf-8") as fsel:
        if os.path.exists(GO_HITS_PATH):
            with open(GO_HITS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    item = json.loads(line)
                    areas = sorted(set(a for a, t in item.get("area_termos", []) if a))
                    for area in areas:
                        aceito, motivo = _avalia_candidato(item, area)
                        fsel.write(json.dumps({
                            "escopo": "GO", "area": area, "motivo": motivo,
                            "aceito": aceito,
                            "numero_controle_pncp": item.get("numero_controle_pncp"),
                            "orgao_cnpj": item.get("orgao_cnpj"), "ano": item.get("ano"),
                            "numero_sequencial": item.get("numero_sequencial"),
                            "data_publicacao_pncp": item.get("data_publicacao_pncp"),
                        }, ensure_ascii=False) + "\n")
                        if aceito:
                            candidatos_go.setdefault(area, []).append(item)

        if os.path.exists(VIZ_HITS_PATH):
            with open(VIZ_HITS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    item = json.loads(line)
                    uf = item.get("uf")
                    areas = sorted(set(a for a, t in item.get("area_termos", []) if a))
                    for area in areas:
                        aceito, motivo = _avalia_candidato(item, area)
                        fsel.write(json.dumps({
                            "escopo": uf, "area": area, "motivo": motivo,
                            "aceito": aceito,
                            "numero_controle_pncp": item.get("numero_controle_pncp"),
                            "orgao_cnpj": item.get("orgao_cnpj"), "ano": item.get("ano"),
                            "numero_sequencial": item.get("numero_sequencial"),
                            "data_publicacao_pncp": item.get("data_publicacao_pncp"),
                        }, ensure_ascii=False) + "\n")
                        if aceito:
                            candidatos_viz.setdefault((area, uf), []).append(item)

    # aplica limites, mais recentes primeiro
    selecionados = {}  # chave -> {"item":item, "areas":set(), "escopo":"GO"/uf}
    for area, itens in candidatos_go.items():
        itens_ordenados = sorted(itens, key=lambda x: x.get("data_publicacao_pncp") or "", reverse=True)
        top = itens_ordenados[:MAX_CANDIDATOS_GO]
        STATS["candidatos_go_por_area"][area] = len(top)
        for it in top:
            k = _chave_hit(it)
            if k not in selecionados:
                selecionados[k] = {"item": it, "areas": set(), "escopo": "GO"}
            selecionados[k]["areas"].add(area)

    for (area, uf), itens in candidatos_viz.items():
        itens_ordenados = sorted(itens, key=lambda x: x.get("data_publicacao_pncp") or "", reverse=True)
        top = itens_ordenados[:MAX_CANDIDATOS_VIZ]
        STATS["candidatos_viz_por_area_uf"][f"{area}|{uf}"] = len(top)
        for it in top:
            k = _chave_hit(it)
            if k not in selecionados:
                selecionados[k] = {"item": it, "areas": set(), "escopo": uf}
            selecionados[k]["areas"].add(area)

    salvar_stats()
    logger.info("selecao concluida: %d compras unicas candidatas (GO+viz)", len(selecionados))
    return selecionados


# --------------------------------------------------------------------------
# FASE 3 -- detalhe de cada candidato
# --------------------------------------------------------------------------

def _compra_path(cnpj, ano, seq):
    return os.path.join(COMPRAS_DIR, f"{cnpj}_{ano}_{seq}.json")


def buscar_itens(cnpj, ano, seq):
    itens = []
    pagina = 1
    while True:
        data, resp = http_get_json(BASE_ITENS.format(cnpj=cnpj, ano=ano, seq=seq),
                                    params={"pagina": pagina, "tamanhoPagina": 500})
        if data is None:
            break
        if isinstance(data, dict) and "itens" in data:
            lote = data.get("itens") or []
        else:
            lote = data if isinstance(data, list) else []
        itens.extend(lote)
        if len(lote) < 500:
            break
        pagina += 1
    return itens


def buscar_resultados(cnpj, ano, seq, num_item):
    data, resp = http_get_json(BASE_RESULTADOS.format(cnpj=cnpj, ano=ano, seq=seq, num_item=num_item))
    if data is None:
        return []
    lista = data if isinstance(data, list) else (data.get("resultados") if isinstance(data, dict) else [])
    lista = lista or []
    saneada = []
    for r in lista:
        r = dict(r)
        tipo_pessoa = (r.get("tipoPessoa") or r.get("tipoPessoaFornecedor") or "").upper()
        if tipo_pessoa == "PF" or tipo_pessoa == "F":
            r["niFornecedor"] = None
            r["nomeRazaoSocialFornecedor"] = "pessoa fisica"
        saneada.append(r)
    return saneada


def buscar_arquivos(cnpj, ano, seq):
    data, resp = http_get_json(BASE_ARQUIVOS.format(cnpj=cnpj, ano=ano, seq=seq))
    if data is None:
        return []
    return data if isinstance(data, list) else (data.get("arquivos") if isinstance(data, dict) else [])


def fase3_detalhes(selecionados):
    logger.info("=== FASE 3: detalhe das compras ===")
    total = len(selecionados)
    i = 0
    for k, info in selecionados.items():
        i += 1
        item = info["item"]
        cnpj = item.get("orgao_cnpj")
        ano = item.get("ano")
        seq = item.get("numero_sequencial")
        if not (cnpj and ano and seq):
            logger.warning("hit sem cnpj/ano/seq utilizavel, pulando: %s", k)
            continue
        out_path = _compra_path(cnpj, ano, seq)
        if os.path.exists(out_path):
            logger.info("[%d/%d] compra ja detalhada, pulando: %s", i, total, out_path)
            continue

        logger.info("[%d/%d] detalhando compra cnpj=%s ano=%s seq=%s areas=%s",
                    i, total, cnpj, ano, seq, sorted(info["areas"]))

        detalhe, resp = http_get_json(BASE_DETALHE.format(cnpj=cnpj, ano=ano, seq=seq))
        if detalhe is None:
            STATS["compras_com_erro"] += 1
            registro = {
                "hit": item, "areas": sorted(info["areas"]), "escopo": info["escopo"],
                "detalhe": None, "erro": "falha_ao_obter_detalhe",
                "itens": [], "resultados": {}, "arquivos": [],
                "link_pncp": LINK_PUBLICO.format(cnpj=cnpj, ano=ano, seq=seq),
                "data_acesso": now_iso(),
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(registro, f, ensure_ascii=False, indent=2)
            salvar_stats()
            continue

        itens = buscar_itens(cnpj, ano, seq)
        STATS["itens_total"] += len(itens)

        itens_com_resultado = [it for it in itens if it.get("temResultado")]
        itens_truncados = len(itens_com_resultado) > MAX_ITENS_RESULTADO
        itens_para_resultado = itens_com_resultado[:MAX_ITENS_RESULTADO]

        resultados = {}
        for it in itens_para_resultado:
            num_item = it.get("numeroItem")
            if num_item is None:
                continue
            res = buscar_resultados(cnpj, ano, seq, num_item)
            resultados[str(num_item)] = res
            STATS["resultados_total"] += len(res)

        arquivos = buscar_arquivos(cnpj, ano, seq)

        registro = {
            "hit": item,
            "areas": sorted(info["areas"]),
            "escopo": info["escopo"],
            "detalhe": detalhe,
            "itens": itens,
            "itens_truncados": itens_truncados,
            "resultados": resultados,
            "arquivos": arquivos,
            "link_pncp": LINK_PUBLICO.format(cnpj=cnpj, ano=ano, seq=seq),
            "data_acesso": now_iso(),
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(registro, f, ensure_ascii=False, indent=2)
        STATS["compras_detalhadas"] += 1
        salvar_stats()


# --------------------------------------------------------------------------
# FASE 4 -- textos dos editais (PDF)
# --------------------------------------------------------------------------

def _score_doc(a):
    t = norm(a.get("titulo") or "") + " " + norm(a.get("tipoDocumentoNome") or "")
    if "termo de referencia" in t:
        return 0
    if "edital" in t:
        return 1
    return 2


def escolher_documento(arquivos):
    candidatos = sorted(arquivos or [], key=_score_doc)
    for a in candidatos:
        if _score_doc(a) < 2 and a.get("url"):
            return a
    return None


def extrair_texto_pdf_bytes(data, origem=""):
    if PdfReader is None:
        raise RuntimeError("pypdf indisponivel")
    reader = PdfReader(io.BytesIO(data))
    partes = []
    for pagina in reader.pages:
        try:
            partes.append(pagina.extract_text() or "")
        except Exception:
            partes.append("")
    texto = "\n".join(partes)
    return texto


def extrair_texto_zip_bytes(data):
    partes = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for nome in z.namelist():
            if nome.lower().endswith(".pdf"):
                pdf_bytes = z.read(nome)
                try:
                    texto = extrair_texto_pdf_bytes(pdf_bytes, origem=nome)
                except Exception as e:
                    texto = f"[falha ao extrair {nome}: {e}]"
                partes.append(f"--- arquivo: {nome} ---\n{texto}")
    return "\n\n".join(partes)


def baixar_e_extrair(url):
    """Retorna (texto:str|None, motivo_falha:str|None)."""
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext in EXEC_EXTENSIONS:
        return None, f"extensao_bloqueada:{ext}"

    resp = http_get(url, stream=True)
    if resp is None:
        return None, "falha_download_rede"
    if resp.status_code != 200:
        return None, f"http_{resp.status_code}"

    content_length = resp.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > MAX_DOWNLOAD_BYTES:
                return None, "arquivo_maior_que_25mb"
        except ValueError:
            pass

    data = bytearray()
    try:
        for chunk in resp.iter_content(65536):
            if not chunk:
                continue
            data.extend(chunk)
            if len(data) > MAX_DOWNLOAD_BYTES:
                return None, "arquivo_maior_que_25mb_stream"
    except requests.exceptions.RequestException as e:
        return None, f"erro_stream:{e}"
    data = bytes(data)

    content_type = (resp.headers.get("Content-Type") or "").lower()

    if ext == ".rar" or data[:7] == b"Rar!\x1a\x07\x00" or data[:6] == b"Rar!\x1a\x07\x01":
        return None, "rar_nao_suportado"

    if ext == ".pdf" or "pdf" in content_type or data[:4] == b"%PDF":
        try:
            texto = extrair_texto_pdf_bytes(data)
        except Exception as e:
            return None, f"falha_extrair_pdf:{e}"
        return texto, None

    if ext == ".zip" or data[:2] == b"PK":
        try:
            texto = extrair_texto_zip_bytes(data)
        except zipfile.BadZipFile:
            return None, "zip_invalido"
        except Exception as e:
            return None, f"falha_extrair_zip:{e}"
        if not texto:
            return None, "zip_sem_pdf_interno"
        return texto, None

    return None, f"tipo_nao_suportado:{ext or content_type}"


def fase4_textos(selecionados):
    logger.info("=== FASE 4: textos dos editais ===")
    # apenas candidatos de GO, nas areas de interesse
    por_area = {}
    for k, info in selecionados.items():
        if info["escopo"] != "GO":
            continue
        for area in info["areas"]:
            if area in AREAS_TEXTO:
                por_area.setdefault(area, []).append(info["item"])

    with open(FALHAS_TEXTOS_PATH, "a", encoding="utf-8") as ffalhas:
        for area, itens in por_area.items():
            itens_ordenados = sorted(itens, key=lambda x: x.get("data_publicacao_pncp") or "", reverse=True)
            top = itens_ordenados[:MAX_TEXTOS_POR_AREA]
            logger.info("fase4 area=%s: %d candidatos (de %d)", area, len(top), len(itens))
            for item in top:
                cnpj = item.get("orgao_cnpj")
                ano = item.get("ano")
                seq = item.get("numero_sequencial")
                if not (cnpj and ano and seq):
                    continue
                txt_path = os.path.join(TEXTOS_DIR, f"{cnpj}_{ano}_{seq}.txt")
                if os.path.exists(txt_path):
                    logger.info("texto ja existe, pulando: %s", txt_path)
                    continue

                # reaproveita lista de arquivos ja salva na fase 3, se houver
                compra_path = _compra_path(cnpj, ano, seq)
                arquivos = None
                if os.path.exists(compra_path):
                    try:
                        with open(compra_path, "r", encoding="utf-8") as f:
                            registro = json.load(f)
                        arquivos = registro.get("arquivos")
                    except Exception:
                        arquivos = None
                if arquivos is None:
                    arquivos = buscar_arquivos(cnpj, ano, seq)

                doc = escolher_documento(arquivos)
                if doc is None:
                    motivo = "sem_documento_edital_ou_tr"
                    ffalhas.write(json.dumps({
                        "orgao_cnpj": cnpj, "ano": ano, "numero_sequencial": seq,
                        "area": area, "motivo": motivo,
                    }, ensure_ascii=False) + "\n")
                    STATS["textos_falhas"] += 1
                    salvar_stats()
                    continue

                logger.info("baixando doc area=%s cnpj=%s ano=%s seq=%s titulo=%r",
                            area, cnpj, ano, seq, doc.get("titulo"))
                texto, motivo = baixar_e_extrair(doc.get("url"))
                if texto is None:
                    ffalhas.write(json.dumps({
                        "orgao_cnpj": cnpj, "ano": ano, "numero_sequencial": seq,
                        "area": area, "motivo": motivo, "url": doc.get("url"),
                    }, ensure_ascii=False) + "\n")
                    STATS["textos_falhas"] += 1
                    salvar_stats()
                    continue

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(texto)
                STATS["textos_baixados_por_area"][area] = STATS["textos_baixados_por_area"].get(area, 0) + 1
                salvar_stats()


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true",
                         help="teste rapido: 1 termo (GO) e ate 2 compras detalhadas")
    args = parser.parse_args()

    STATS["inicio"] = now_iso()
    salvar_stats()

    cp = carregar_checkpoint()

    if args.test:
        logger.info("### MODO TESTE ###")
        apenas_termos = {("climatizacao", "manutenção ar condicionado")}
        fase1_indice(cp, apenas_termos=apenas_termos, apenas_go=True)
        selecionados = fase2_selecao()
        # limita a 2 no modo teste
        selecionados = dict(list(selecionados.items())[:2])
        fase3_detalhes(selecionados)
        fase4_textos(selecionados)
    else:
        fase1_indice(cp)
        selecionados = fase2_selecao()
        fase3_detalhes(selecionados)
        fase4_textos(selecionados)

    STATS["fim"] = now_iso()
    salvar_stats()
    logger.info("=== COLETA CONCLUIDA ===")
    logger.info("stats finais: %s", json.dumps(STATS, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.error("erro fatal no coletor:\n%s", traceback.format_exc())
        STATS["fim"] = now_iso()
        salvar_stats()
        raise
