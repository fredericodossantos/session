#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coletor SUPLEMENTAR de dados do PNCP -- gap-filling para as areas
eletrica_predial, refrigeracao, manutencao_predial e iluminacao_publica,
cuja amostra da coleta principal (coletor.py) ficou pequena ou dominada
por ruido (compra pura de material, ar-condicionado, eventos/decoracao).

So GO, so os termos novos definidos em TERMOS_SUP, com filtro de
relevancia mais rigido do que o coletor.py original. NAO altera
coletor.py nem os arquivos que ele gera (go_hits*.jsonl, viz_hits*.jsonl,
selecao.jsonl, stats.json, checkpoint.json, coletor.log) -- so ACRESCENTA
compras novas em W/compras/ e textos novos em W/textos/, alem de escrever
seus proprios arquivos de log/selecao/stats/checkpoint com sufixo
"_suplementar".

Varias funcoes abaixo sao copias adaptadas das equivalentes em
coletor.py (throttle HTTP, extracao de texto de PDF/ZIP, etc.) -- ver
coletor.py para a versao original/comentada.
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
LOG_PATH = os.path.join(W, "coletor_suplementar.log")
STATS_PATH = os.path.join(W, "stats_suplementar.json")
CHECKPOINT_PATH = os.path.join(W, "checkpoint_suplementar.json")
RAW_HITS_PATH = os.path.join(W, "sup_hits_raw.jsonl")

SELECAO_ORIGINAL_PATH = os.path.join(W, "selecao.jsonl")
SELECAO_SUP_PATH = os.path.join(W, "selecao_suplementar.jsonl")
COMPRAS_DIR = os.path.join(W, "compras")
TEXTOS_DIR = os.path.join(W, "textos")
FALHAS_TEXTOS_PATH = os.path.join(TEXTOS_DIR, "falhas_suplementar.jsonl")

os.makedirs(COMPRAS_DIR, exist_ok=True)
os.makedirs(TEXTOS_DIR, exist_ok=True)

BASE_SEARCH = "https://pncp.gov.br/api/search/"
BASE_DETALHE = "https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}"
BASE_ITENS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens"
BASE_RESULTADOS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{num_item}/resultados"
BASE_ARQUIVOS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos"
LINK_PUBLICO = "https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"

USER_AGENT = "estudo-mercado-licitacoes-go/1.0 (consultas publicas, coleta suplementar)"
HEADERS = {"User-Agent": USER_AGENT}

CUTOFF_DATE = "2024-09-27"  # periodo: 24 meses antes de 2026-09-27
UF_ALVO = "GO"

MODALIDADES_COMPETITIVAS = {4, 5, 6, 7}

MAX_PAGINAS_TERMO = 10
TAM_PAGINA = 100

MAX_NOVOS_POR_AREA = 40
MAX_ITENS_RESULTADO = 40
MIN_DIVERSIDADE_ELETRICA = 8  # SPDA/aterramento e subestacao/termografia/laudo

MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
EXEC_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".msi", ".com", ".scr", ".jar", ".ps1", ".vbs"}

# --------------------------------------------------------------------------
# TERMOS suplementares por area (todos buscados so em GO)
# --------------------------------------------------------------------------

TERMOS_SUP = {
    "eletrica_predial": [
        "manutenção preventiva e corretiva instalações elétricas",
        "prestação de serviços manutenção elétrica",
        "manutenção do sistema de proteção contra descargas atmosféricas",
        "SPDA laudo",
        "SPDA instalação",
        "aterramento manutenção",
        "manutenção de subestação",
        "manutenção preventiva subestação",
        "termografia",
        "laudo elétrico NR-10",
        "adequação elétrica",
        "manutenção de quadros elétricos",
        "manutenção de grupo gerador",
    ],
    "refrigeracao": [
        "manutenção câmara fria",
        "manutenção de câmaras frigoríficas",
        "manutenção de bebedouros",
        "manutenção de refrigeradores",
        "manutenção freezers",
        "manutenção balcão refrigerado",
        "manutenção de equipamentos de cozinha industrial refrigeração",
    ],
    "manutencao_predial": [
        "manutenção predial preventiva e corretiva",
        "manutenção predial com fornecimento de materiais",
        "serviços de manutenção predial elétrica hidráulica",
    ],
    "iluminacao_publica": [
        "manutenção do parque de iluminação pública",
        "manutenção preventiva e corretiva iluminação pública",
        "serviços de manutenção de iluminação pública com fornecimento de materiais",
        "manutenção da rede de iluminação pública",
        "ampliação e manutenção de iluminação pública",
        "caminhão cesto aéreo iluminação pública",
    ],
}

# areas para as quais baixamos texto do edital/TR dos casos novos
AREAS_TEXTO_SUP = {"eletrica_predial", "refrigeracao", "manutencao_predial", "iluminacao_publica"}

# --------------------------------------------------------------------------
# Regex de filtro (mais rigido que o coletor.py original)
# --------------------------------------------------------------------------

# exige sinal de SERVICO na descricao (regra geral)
REGEX_SERVICO_GERAL = re.compile(
    r"manuten|servic|laudo|instalac|conserto|reparo|adequac|inspec|termograf|execuc"
)
# override especifico para iluminacao_publica (pedido do coordenador:
# tambem aceita ampliacao/extensao de rede como sinal de servico)
REGEX_SERVICO_ILUMINACAO = re.compile(r"manuten|servic|ampliac|extens|reparo")

# rejeita compra pura de material/equipamento (inicio da descricao), a
# menos que a mesma descricao tambem fale de servico/instalacao/manutencao
REGEX_COMPRA_PURA = re.compile(
    r"^(aquisicao|compra|fornecimento) de (material|materiais|equipamento|equipamentos|pecas|produtos)"
)
REGEX_TEM_SERVICO_GENUINO = re.compile(r"servic|instalac|manuten")

# regex de area (mais estritas que as do coletor.py original, por pedido
# especifico do estudo)
REGEX_AREA_SUP = {
    "eletrica_predial": re.compile(
        r"eletric|spda|para-raio|aterramento|subestac|termograf|quadro|gerador"
    ),
    "refrigeracao": re.compile(
        r"camara fria|frigor|refrigerador|freezer|bebedouro|balcao refrigerado|refrigera"
    ),
    "manutencao_predial": re.compile(r"manutencao predial|predial"),
    "iluminacao_publica": re.compile(r"iluminacao publica|parque de iluminacao|rede de iluminacao"),
}

# refrigeracao: rejeita quando o nucleo do objeto e so ar-condicionado
REGEX_AR_CONDICIONADO_PURO = re.compile(r"ar condicionado|condicionador|split")
REGEX_REFRIGERACAO_NUCLEO = re.compile(r"camara|bebedouro|refrigerador|freezer|frigor")

# iluminacao_publica: ruido de evento/decoracao/som (rejeita) e sinal de
# modernizacao/eficientizacao LED (nao rejeita, so marca a parte)
REGEX_ILUM_RUIDO = re.compile(r"evento|show|festa|natal|natalin|decorac|palco|\bsom\b")
REGEX_ILUM_LED = re.compile(r"\bled\b|eficientiza")

# diversidade dentro de eletrica_predial
REGEX_ELETRICA_SPDA = re.compile(r"spda|aterramento|para-raio")
REGEX_ELETRICA_SUBESTACAO = re.compile(r"subestac|termograf|laudo")

# --------------------------------------------------------------------------
# Logging (arquivo proprio -- nao mexe em coletor.log)
# --------------------------------------------------------------------------

logger = logging.getLogger("coletor_suplementar")
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
    "hits_por_termo": {},
    "hits_dedup_por_area": {},
    "candidatos_aceitos_por_area": {},
    "candidatos_novos_por_area": {},          # aceitos e ainda nao em W/compras
    "candidatos_novos_selecionados_por_area": {},  # apos cap de 40 (+diversidade)
    "eletrica_diversidade": {},
    "iluminacao_led_modernizacao": 0,
    "compras_detalhadas": 0,
    "compras_ja_existentes_puladas": 0,
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
        logger.exception("falha ao salvar stats_suplementar.json")


def carregar_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("checkpoint_suplementar.json corrompido, recomecando")
    return {"busca_done": []}


def salvar_checkpoint(cp):
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(cp, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# HTTP com throttle (1 req/s) e retentativas -- copiado de coletor.py
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
            continue

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


def _chave_hit(item):
    ncp = item.get("numero_controle_pncp")
    if ncp:
        return ncp
    return f"{item.get('orgao_cnpj')}_{item.get('ano')}_{item.get('numero_sequencial')}"


def _cnpj_ano_seq(item):
    return f"{item.get('orgao_cnpj')}_{item.get('ano')}_{item.get('numero_sequencial')}"


def _compra_path(cnpj, ano, seq):
    return os.path.join(COMPRAS_DIR, f"{cnpj}_{ano}_{seq}.json")


# --------------------------------------------------------------------------
# FASE A -- busca (so GO, so termos suplementares)
# --------------------------------------------------------------------------

def buscar_pagina(termo, pagina):
    params = {
        "q": termo,
        "tipos_documento": "edital",
        "ordenacao": "-data",
        "pagina": pagina,
        "tam_pagina": TAM_PAGINA,
        "status": "encerradas",
        "ufs": UF_ALVO,
    }
    data, resp = http_get_json(BASE_SEARCH, params=params)
    return data


def coletar_termo(area, termo, raw_fout):
    total = 0
    pagina = 1
    while pagina <= MAX_PAGINAS_TERMO:
        data = buscar_pagina(termo, pagina)
        if not data or "items" not in data:
            logger.warning("busca sem resultado utilizavel: area=%s termo=%r pagina=%d", area, termo, pagina)
            break
        items = data.get("items") or []
        if not items:
            break
        for item in items:
            item["_area"] = area
            item["_termo"] = termo
            raw_fout.write(json.dumps(item, ensure_ascii=False) + "\n")
        total += len(items)
        ultima_data = items[-1].get("data_publicacao_pncp") or ""
        logger.info("busca area=%s termo=%r pagina=%d itens=%d ultima_data=%s",
                    area, termo, pagina, len(items), ultima_data)
        if ultima_data and ultima_data[:10] < CUTOFF_DATE:
            break
        if len(items) < TAM_PAGINA:
            break
        pagina += 1
    return total


def fase_busca(cp):
    logger.info("=== FASE A: busca (termos suplementares, GO) ===")
    with open(RAW_HITS_PATH, "a", encoding="utf-8") as raw_fout:
        for area, termos in TERMOS_SUP.items():
            for termo in termos:
                key = f"{area}|{termo}"
                if key in cp["busca_done"]:
                    logger.info("termo ja coletado, pulando: %s", key)
                    continue
                n = coletar_termo(area, termo, raw_fout)
                STATS["hits_por_termo"][key] = n
                cp["busca_done"].append(key)
                salvar_checkpoint(cp)
                salvar_stats()


def carregar_e_mesclar_hits():
    """Le RAW_HITS_PATH inteiro e devolve dict area -> {chave: item}, com
    item['area_termos'] = lista de [area,termo] que o acharam (so entre os
    termos suplementares desta area; um mesmo aviso pode aparecer sob mais
    de uma area se bateu termos de areas diferentes)."""
    por_area = {}
    if not os.path.exists(RAW_HITS_PATH):
        return por_area
    with open(RAW_HITS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            area = item.pop("_area", None)
            termo = item.pop("_termo", None)
            k = _chave_hit(item)
            bucket = por_area.setdefault(area, {})
            if k not in bucket:
                item["area_termos"] = []
                bucket[k] = item
            par = [area, termo]
            if par not in bucket[k]["area_termos"]:
                bucket[k]["area_termos"].append(par)
    for area, bucket in por_area.items():
        STATS["hits_dedup_por_area"][area] = len(bucket)
    salvar_stats()
    return por_area


# --------------------------------------------------------------------------
# FASE B -- filtro de relevancia + selecao com cap de 40 (e diversidade)
# --------------------------------------------------------------------------

def _avalia_base(item):
    modalidade_raw = item.get("modalidade_licitacao_id")
    try:
        modalidade = int(modalidade_raw)
    except (TypeError, ValueError):
        modalidade = None
    if modalidade not in MODALIDADES_COMPETITIVAS:
        return False, f"modalidade_nao_competitiva:{modalidade_raw}"
    if not item.get("tem_resultado"):
        return False, "sem_resultado"
    if item.get("cancelado"):
        return False, "cancelado"
    data_pub = (item.get("data_publicacao_pncp") or "")[:10]
    if not data_pub or data_pub < CUTOFF_DATE:
        return False, "fora_do_periodo"
    return True, "base_ok"


def _avalia_relevancia(desc, area):
    """desc ja normalizada (sem acento, minuscula). Devolve
    (ok, motivo, led_modernizacao:bool)."""
    servico_rx = REGEX_SERVICO_ILUMINACAO if area == "iluminacao_publica" else REGEX_SERVICO_GERAL
    if not servico_rx.search(desc):
        return False, "sem_sinal_servico", False

    if area == "iluminacao_publica" and REGEX_ILUM_RUIDO.search(desc):
        return False, "ruido_evento_decoracao", False

    if REGEX_COMPRA_PURA.match(desc) and not REGEX_TEM_SERVICO_GENUINO.search(desc):
        return False, "compra_pura_rejeitada", False

    area_rx = REGEX_AREA_SUP.get(area)
    if area_rx is None or not area_rx.search(desc):
        return False, "regex_area_nao_bate", False

    if area == "refrigeracao":
        if REGEX_AR_CONDICIONADO_PURO.search(desc) and not REGEX_REFRIGERACAO_NUCLEO.search(desc):
            return False, "nucleo_ar_condicionado_puro", False

    led = area == "iluminacao_publica" and bool(REGEX_ILUM_LED.search(desc))
    return True, "selecionado", led


def _carregar_aceitos_originais():
    """Le W/selecao.jsonl (gerado pelo coletor.py original) e devolve
    dict area -> set(chave) dos itens em GO com aceito=true, para nao
    contar de novo o mesmo aviso no indice/volume anualizado."""
    aceitos = {}
    if not os.path.exists(SELECAO_ORIGINAL_PATH):
        logger.warning("selecao.jsonl original nao encontrado; nenhuma deduplicacao de indice sera feita")
        return aceitos
    with open(SELECAO_ORIGINAL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("escopo") != "GO" or not row.get("aceito"):
                continue
            area = row.get("area")
            ncp = row.get("numero_controle_pncp")
            if ncp:
                chave = ncp
            else:
                chave = f"{row.get('orgao_cnpj')}_{row.get('ano')}_{row.get('numero_sequencial')}"
            aceitos.setdefault(area, set()).add(chave)
    return aceitos


def _grupo_diversidade_eletrica(desc):
    if REGEX_ELETRICA_SPDA.search(desc):
        return "spda"
    if REGEX_ELETRICA_SUBESTACAO.search(desc):
        return "subestacao"
    return "outro"


def fase_selecao(por_area_hits, existentes_em_compras):
    """Aplica filtro de relevancia + regra base, grava selecao_suplementar.jsonl
    (uma linha por (area,hit) avaliado) e devolve dict:
        area -> lista de itens ACEITOS e NOVOS (nao em W/compras), ordenados
        do mais recente para o mais antigo, ja limitados a MAX_NOVOS_POR_AREA
        (com diversidade garantida para eletrica_predial)."""
    aceitos_originais = _carregar_aceitos_originais()
    selecionados_por_area = {}

    with open(SELECAO_SUP_PATH, "a", encoding="utf-8") as fsel:
        for area, bucket in por_area_hits.items():
            candidatos_novos_aceitos = []
            for k, item in bucket.items():
                ok_base, motivo_base = _avalia_base(item)
                desc = norm(item.get("description"))
                led = False
                if ok_base:
                    ok_relev, motivo_relev, led = _avalia_relevancia(desc, area)
                else:
                    ok_relev, motivo_relev = False, None

                aceito = ok_base and ok_relev
                motivo = motivo_relev if (ok_base and not ok_relev) else (motivo_base if not ok_base else "selecionado")

                ja_contado = False
                if aceito and k in aceitos_originais.get(area, set()):
                    ja_contado = True
                    aceito = False
                    motivo = "ja_contado_selecao_original"

                cnpj_ano_seq = _cnpj_ano_seq(item)
                ja_em_compras = cnpj_ano_seq in existentes_em_compras

                row = {
                    "escopo": "GO",
                    "area": area,
                    "motivo": motivo,
                    "aceito": aceito,
                    "numero_controle_pncp": item.get("numero_controle_pncp"),
                    "orgao_cnpj": item.get("orgao_cnpj"),
                    "ano": item.get("ano"),
                    "numero_sequencial": item.get("numero_sequencial"),
                    "data_publicacao_pncp": item.get("data_publicacao_pncp"),
                    "origem": "suplementar",
                    "area_termos": [par for par in item.get("area_termos", []) if par[0] == area],
                    "ja_existe_em_compras": ja_em_compras,
                    "ja_contado_no_indice_original": ja_contado,
                }
                if area == "iluminacao_publica":
                    row["led_modernizacao"] = led
                    if aceito and led:
                        STATS["iluminacao_led_modernizacao"] += 1
                fsel.write(json.dumps(row, ensure_ascii=False) + "\n")

                if aceito:
                    STATS["candidatos_aceitos_por_area"][area] = STATS["candidatos_aceitos_por_area"].get(area, 0) + 1
                    if not ja_em_compras:
                        candidatos_novos_aceitos.append(item)

            STATS["candidatos_novos_por_area"][area] = len(candidatos_novos_aceitos)
            candidatos_novos_aceitos.sort(key=lambda x: x.get("data_publicacao_pncp") or "", reverse=True)

            if area == "eletrica_predial":
                selecionados = _seleciona_com_diversidade_eletrica(candidatos_novos_aceitos)
            else:
                selecionados = candidatos_novos_aceitos[:MAX_NOVOS_POR_AREA]

            STATS["candidatos_novos_selecionados_por_area"][area] = len(selecionados)
            selecionados_por_area[area] = selecionados
            logger.info("selecao area=%s: %d aceitos, %d novos (fora de W/compras), %d selecionados (cap %d)",
                        area, STATS["candidatos_aceitos_por_area"].get(area, 0),
                        len(candidatos_novos_aceitos), len(selecionados), MAX_NOVOS_POR_AREA)
            salvar_stats()

    return selecionados_por_area


def _seleciona_com_diversidade_eletrica(itens_ordenados):
    """itens_ordenados: mais recente primeiro. Garante ate
    MIN_DIVERSIDADE_ELETRICA casos de SPDA/aterramento/para-raios e ate
    MIN_DIVERSIDADE_ELETRICA casos de subestacao/termografia/laudo (se
    existirem), preenchendo o resto ate MAX_NOVOS_POR_AREA pelos mais
    recentes."""
    spda, subestacao, outros = [], [], []
    for it in itens_ordenados:
        grupo = _grupo_diversidade_eletrica(norm(it.get("description")))
        if grupo == "spda":
            spda.append(it)
        elif grupo == "subestacao":
            subestacao.append(it)
        else:
            outros.append(it)

    STATS["eletrica_diversidade"] = {
        "disponiveis_spda": len(spda),
        "disponiveis_subestacao": len(subestacao),
        "disponiveis_outros": len(outros),
    }

    selecionados = []
    chaves_selecionadas = set()

    def _add(lista, limite):
        n = 0
        for it in lista:
            if n >= limite:
                break
            k = _chave_hit(it)
            if k in chaves_selecionadas:
                continue
            selecionados.append(it)
            chaves_selecionadas.add(k)
            n += 1

    _add(spda, MIN_DIVERSIDADE_ELETRICA)
    _add(subestacao, MIN_DIVERSIDADE_ELETRICA)

    # preenche o resto pelos mais recentes (qualquer grupo), ate o cap
    for it in itens_ordenados:
        if len(selecionados) >= MAX_NOVOS_POR_AREA:
            break
        k = _chave_hit(it)
        if k in chaves_selecionadas:
            continue
        selecionados.append(it)
        chaves_selecionadas.add(k)

    # reordena por data desc pra manter o criterio "mais recentes primeiro"
    selecionados.sort(key=lambda x: x.get("data_publicacao_pncp") or "", reverse=True)
    STATS["eletrica_diversidade"]["selecionados_spda"] = sum(
        1 for it in selecionados if _grupo_diversidade_eletrica(norm(it.get("description"))) == "spda")
    STATS["eletrica_diversidade"]["selecionados_subestacao"] = sum(
        1 for it in selecionados if _grupo_diversidade_eletrica(norm(it.get("description"))) == "subestacao")
    return selecionados[:MAX_NOVOS_POR_AREA]


# --------------------------------------------------------------------------
# FASE C -- detalhe de cada candidato novo (mesmo formato de W/compras)
# --------------------------------------------------------------------------

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


def fase_detalhes(selecionados_por_area):
    logger.info("=== FASE C: detalhe das compras novas ===")
    # uniao das compras selecionadas (uma compra pode ter sido selecionada
    # por mais de uma area, ex.: eletrica_predial e manutencao_predial)
    unificado = {}  # cnpj_ano_seq -> {"item":item, "areas":set()}
    for area, itens in selecionados_por_area.items():
        for item in itens:
            cnpj_ano_seq = _cnpj_ano_seq(item)
            if cnpj_ano_seq not in unificado:
                unificado[cnpj_ano_seq] = {"item": item, "areas": set()}
            unificado[cnpj_ano_seq]["areas"].add(area)

    total = len(unificado)
    i = 0
    for cnpj_ano_seq, info in unificado.items():
        i += 1
        item = dict(info["item"])
        item["origem"] = "suplementar"
        cnpj = item.get("orgao_cnpj")
        ano = item.get("ano")
        seq = item.get("numero_sequencial")
        if not (cnpj and ano and seq):
            logger.warning("hit sem cnpj/ano/seq utilizavel, pulando: %s", cnpj_ano_seq)
            continue

        out_path = _compra_path(cnpj, ano, seq)
        if os.path.exists(out_path):
            logger.info("[%d/%d] compra ja existe em W/compras, pulando: %s", i, total, out_path)
            STATS["compras_ja_existentes_puladas"] += 1
            continue

        logger.info("[%d/%d] detalhando compra NOVA cnpj=%s ano=%s seq=%s areas=%s",
                    i, total, cnpj, ano, seq, sorted(info["areas"]))

        detalhe, resp = http_get_json(BASE_DETALHE.format(cnpj=cnpj, ano=ano, seq=seq))
        if detalhe is None:
            STATS["compras_com_erro"] += 1
            registro = {
                "hit": item, "areas": sorted(info["areas"]), "escopo": "GO",
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
            "escopo": "GO",
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

    return unificado


# --------------------------------------------------------------------------
# FASE D -- textos (TR preferido, senao Edital) dos casos novos
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


def extrair_texto_pdf_bytes(data):
    if PdfReader is None:
        raise RuntimeError("pypdf indisponivel")
    reader = PdfReader(io.BytesIO(data))
    partes = []
    for pagina in reader.pages:
        try:
            partes.append(pagina.extract_text() or "")
        except Exception:
            partes.append("")
    return "\n".join(partes)


def extrair_texto_zip_bytes(data):
    partes = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for nome in z.namelist():
            if nome.lower().endswith(".pdf"):
                pdf_bytes = z.read(nome)
                try:
                    texto = extrair_texto_pdf_bytes(pdf_bytes)
                except Exception as e:
                    texto = f"[falha ao extrair {nome}: {e}]"
                partes.append(f"--- arquivo: {nome} ---\n{texto}")
    return "\n\n".join(partes)


def baixar_e_extrair(url):
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


def fase_textos(unificado):
    logger.info("=== FASE D: textos dos editais/TR (casos novos) ===")
    with open(FALHAS_TEXTOS_PATH, "a", encoding="utf-8") as ffalhas:
        for cnpj_ano_seq, info in unificado.items():
            areas_interesse = info["areas"] & AREAS_TEXTO_SUP
            if not areas_interesse:
                continue
            item = info["item"]
            cnpj = item.get("orgao_cnpj")
            ano = item.get("ano")
            seq = item.get("numero_sequencial")
            if not (cnpj and ano and seq):
                continue

            txt_path = os.path.join(TEXTOS_DIR, f"{cnpj_ano_seq}.txt")
            if os.path.exists(txt_path):
                logger.info("texto ja existe, pulando: %s", txt_path)
                continue

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
                ffalhas.write(json.dumps({
                    "orgao_cnpj": cnpj, "ano": ano, "numero_sequencial": seq,
                    "areas": sorted(areas_interesse), "motivo": "sem_documento_edital_ou_tr",
                }, ensure_ascii=False) + "\n")
                STATS["textos_falhas"] += 1
                salvar_stats()
                continue

            logger.info("baixando doc areas=%s cnpj=%s ano=%s seq=%s titulo=%r",
                        sorted(areas_interesse), cnpj, ano, seq, doc.get("titulo"))
            texto, motivo = baixar_e_extrair(doc.get("url"))
            if texto is None:
                ffalhas.write(json.dumps({
                    "orgao_cnpj": cnpj, "ano": ano, "numero_sequencial": seq,
                    "areas": sorted(areas_interesse), "motivo": motivo, "url": doc.get("url"),
                }, ensure_ascii=False) + "\n")
                STATS["textos_falhas"] += 1
                salvar_stats()
                continue

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(texto)
            for area in areas_interesse:
                STATS["textos_baixados_por_area"][area] = STATS["textos_baixados_por_area"].get(area, 0) + 1
            salvar_stats()


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()

    STATS["inicio"] = now_iso()
    salvar_stats()

    cp = carregar_checkpoint()

    logger.info("=== COLETA SUPLEMENTAR: inicio ===")
    logger.info("areas=%s", sorted(TERMOS_SUP.keys()))

    fase_busca(cp)
    por_area_hits = carregar_e_mesclar_hits()

    existentes_em_compras = {
        os.path.splitext(fn)[0] for fn in os.listdir(COMPRAS_DIR) if fn.endswith(".json")
    }
    logger.info("compras ja existentes em W/compras (main coletor + rodadas anteriores): %d",
                len(existentes_em_compras))

    selecionados_por_area = fase_selecao(por_area_hits, existentes_em_compras)
    unificado = fase_detalhes(selecionados_por_area)
    fase_textos(unificado)

    STATS["fim"] = now_iso()
    salvar_stats()
    logger.info("=== COLETA SUPLEMENTAR CONCLUIDA ===")
    logger.info("stats finais: %s", json.dumps(STATS, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.error("erro fatal no coletor suplementar:\n%s", traceback.format_exc())
        STATS["fim"] = now_iso()
        salvar_stats()
        raise
