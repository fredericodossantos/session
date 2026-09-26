"""Carregamento do arquivo de configuração (YAML ou JSON)."""
from __future__ import annotations

import json
import logging
import math
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

PADRAO: dict[str, Any] = {
    "filtro": {
        "termos_inclusao": [],
        "termos_condicionais": [],
        "termos_exclusao": [],
    },
    "api": {
        "base_consulta": "https://pncp.gov.br/api/consulta",
        "base_pncp": "https://pncp.gov.br/api/pncp",
        "uf": "GO",
        "modalidades": [6, 7, 8, 4, 5, 12],
        "tamanho_pagina": 50,
        "intervalo_entre_requisicoes": 1.0,
        "timeout_conexao": 15,
        "timeout_leitura": 90,
        "tentativas": 5,
        "backoff_inicial": 2.0,
        "tamanho_pagina_itens": 500,
        "max_paginas": 1000,
        "max_paginas_itens": 1000,
    },
    "esferas": ["E", "M"],
    "sistemas_origem": {},
    "saida": {"pasta": "saida", "banco": "historico.db", "logs": "logs"},
}


def _mesclar(base: dict, extra: dict) -> dict:
    resultado = dict(base)
    for chave, valor in (extra or {}).items():
        if isinstance(valor, dict) and isinstance(resultado.get(chave), dict):
            resultado[chave] = _mesclar(resultado[chave], valor)
        else:
            resultado[chave] = valor
    return resultado


def carregar(caminho: str | Path) -> dict[str, Any]:
    caminho = Path(caminho)
    try:
        texto = caminho.read_text(encoding="utf-8-sig")
        if caminho.suffix.lower() == ".json":
            dados = json.loads(texto)
        else:
            dados = yaml.safe_load(texto) or {}
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Não foi possível ler a configuração {caminho}: {exc}") from exc
    if not isinstance(dados, dict):
        raise ValueError(f"{caminho}: a raiz da configuração deve ser um objeto/mapa")
    config = _mesclar(deepcopy(PADRAO), dados)
    for chave in ("filtro", "api", "saida"):
        if not isinstance(config.get(chave), dict):
            raise ValueError(f"{caminho}: '{chave}' deve ser um mapa")
    for chave in ("termos_inclusao", "termos_condicionais", "termos_exclusao"):
        valor = config["filtro"].get(chave)
        if not isinstance(valor, list) or any(not isinstance(x, str) for x in valor):
            raise ValueError(f"{caminho}: 'filtro.{chave}' deve ser uma lista de textos")
    if not any(x.strip() for x in config["filtro"]["termos_inclusao"]):
        raise ValueError(f"{caminho}: 'filtro.termos_inclusao' está vazio")
    if "campos" in config["filtro"]:
        # A classificação por palavras-chave sempre olhou só o objeto (ver
        # IMPLEMENTACAO_FASE_3.md); 'campos' nunca era lido para escolher outros campos.
        # Mantemos apenas o aviso para não quebrar config.yaml antigos.
        logging.warning("%s: 'filtro.campos' foi removida (a classificação usa somente o "
                        "objeto da contratação); o valor informado é ignorado.", caminho)
        del config["filtro"]["campos"]
    modalidades = config["api"].get("modalidades")
    if not isinstance(modalidades, list) or not modalidades:
        raise ValueError(f"{caminho}: 'api.modalidades' deve ser uma lista não vazia")
    if any(isinstance(x, bool) or not isinstance(x, int) for x in modalidades):
        raise ValueError(f"{caminho}: 'api.modalidades' deve conter códigos inteiros")
    modalidades = list(modalidades)
    if any(x <= 0 for x in modalidades) or len(set(modalidades)) != len(modalidades):
        raise ValueError(f"{caminho}: 'api.modalidades' deve conter códigos positivos e únicos")
    config["api"]["modalidades"] = modalidades
    for chave in ("base_consulta", "base_pncp"):
        valor = config["api"].get(chave)
        try:
            parsed = urlsplit(valor) if isinstance(valor, str) else None
            valido = parsed is not None and parsed.scheme in {"https", "http"} and bool(parsed.hostname)
        except ValueError:
            valido = False
        if not valido:
            raise ValueError(f"{caminho}: 'api.{chave}' deve ser uma URL HTTP(S)")
    inteiros = ("tamanho_pagina", "tentativas", "tamanho_pagina_itens",
                "max_paginas", "max_paginas_itens")
    for chave in inteiros:
        valor = config["api"].get(chave)
        if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
            raise ValueError(f"{caminho}: 'api.{chave}' deve ser inteiro positivo")
    if config["api"]["tamanho_pagina"] > 50:
        raise ValueError(f"{caminho}: 'api.tamanho_pagina' não pode exceder 50")
    if config["api"]["tentativas"] > 10:
        raise ValueError(f"{caminho}: 'api.tentativas' não pode exceder 10")
    for chave in ("max_paginas", "max_paginas_itens"):
        if config["api"][chave] > 10000:
            raise ValueError(f"{caminho}: 'api.{chave}' não pode exceder 10000")
    for chave in ("intervalo_entre_requisicoes", "backoff_inicial"):
        valor = config["api"].get(chave)
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < 0:
            raise ValueError(f"{caminho}: 'api.{chave}' deve ser não negativo")
    if "repetir_429" in config["api"]:
        # AC17: 429 nunca pode ter retry oculto. A opção nunca era lida pelo cliente
        # HTTP; mantemos apenas o aviso para não quebrar config.yaml antigos.
        logging.warning("%s: 'api.repetir_429' foi removida (AC17: 429 sempre interrompe "
                        "a modalidade e respeita Retry-After); o valor informado é ignorado.", caminho)
        del config["api"]["repetir_429"]
    for chave in ("timeout_conexao", "timeout_leitura"):
        valor = config["api"][chave]
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
            raise ValueError(f"{caminho}: 'api.{chave}' deve ser positivo e finito")
    esferas = config.get("esferas")
    if not isinstance(esferas, list) or any(not isinstance(x, str) or x not in {"E", "M", "F", "D"}
                                             for x in esferas):
        raise ValueError(f"{caminho}: 'esferas' deve conter apenas E, M, F ou D")
    uf = config["api"].get("uf")
    if not isinstance(uf, str) or len(uf) != 2 or not uf.isalpha():
        raise ValueError(f"{caminho}: 'api.uf' deve ser uma sigla de UF com duas letras")
    sistemas = config.get("sistemas_origem")
    if not isinstance(sistemas, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                             for k, v in sistemas.items()):
        raise ValueError(f"{caminho}: 'sistemas_origem' deve mapear textos para textos")
    for chave in ("pasta", "banco", "logs"):
        if not isinstance(config["saida"].get(chave), str) or not config["saida"][chave].strip():
            raise ValueError(f"{caminho}: 'saida.{chave}' deve ser um caminho não vazio")
    # Caminhos relativos são resolvidos a partir da pasta do arquivo de configuração,
    # para o programa funcionar igual quando chamado pelo Agendador de Tarefas.
    raiz = caminho.resolve().parent
    for chave in ("pasta", "banco", "logs"):
        p = Path(config["saida"][chave])
        if not p.is_absolute():
            p = raiz / (p if chave != "banco" else Path(config["saida"]["pasta"]) / p)
        config["saida"][chave] = str(p)
    return config
