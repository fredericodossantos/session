"""Carregamento do arquivo de configuração (YAML ou JSON)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

PADRAO: dict[str, Any] = {
    "filtro": {
        "campos": ["objetoCompra"],
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
    texto = caminho.read_text(encoding="utf-8")
    if caminho.suffix.lower() == ".json":
        dados = json.loads(texto)
    else:
        dados = yaml.safe_load(texto) or {}
    config = _mesclar(PADRAO, dados)
    if not config["filtro"]["termos_inclusao"]:
        raise ValueError(f"{caminho}: 'filtro.termos_inclusao' está vazio")
    # Caminhos relativos são resolvidos a partir da pasta do arquivo de configuração,
    # para o programa funcionar igual quando chamado pelo Agendador de Tarefas.
    raiz = caminho.resolve().parent
    for chave in ("pasta", "banco", "logs"):
        p = Path(config["saida"][chave])
        if not p.is_absolute():
            p = raiz / (p if chave != "banco" else Path(config["saida"]["pasta"]) / p)
        config["saida"][chave] = str(p)
    return config
