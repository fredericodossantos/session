"""Orquestra uma execução: consulta, filtra, classifica ME/EPP, grava histórico e relatório."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .api_client import ClientePNCP, ErroAPI
from .filtros import EXCLUSIVA, NAO_INFORMADO, SITUACOES_ME_EPP, FiltroPalavras, classificar_me_epp
from .mapeamento import chave_compra, mapear
from .persistencia import Historico

log = logging.getLogger(__name__)


@dataclass
class Parametros:
    dias: int = 30
    municipio_ibge: str | None = None
    somente_me_epp: bool = False
    incluir_federal: bool = False
    modalidades: list[int] | None = None
    salvar_bruto: bool = False


@dataclass
class Resultado:
    registros: list[dict] = field(default_factory=list)
    encontradas: int = 0
    no_escopo: int = 0
    filtradas: int = 0
    me_epp: int = 0
    exclusivas: int = 0
    novas: int = 0
    falhas: int = 0
    por_modalidade: dict[int, int] = field(default_factory=dict)
    modalidades_com_falha: list[int] = field(default_factory=list)


def executar(config: dict[str, Any], params: Parametros, cliente: ClientePNCP,
             historico: Historico, agora: datetime | None = None) -> Resultado:
    agora = agora or datetime.now()
    limite = agora + timedelta(days=params.dias)
    cfg_api = config["api"]
    modalidades = params.modalidades or cfg_api["modalidades"]
    esferas = {e.upper() for e in config.get("esferas", ["E", "M"])}
    if params.incluir_federal:
        esferas.add("F")
    filtro = FiltroPalavras(config["filtro"])
    res = Resultado()

    # 1) Coleta de todas as modalidades, sem duplicar.
    brutos: dict[str, dict] = {}
    for mod in modalidades:
        n = 0
        try:
            for reg in cliente.contratacoes_proposta(limite.date(), mod, uf=cfg_api.get("uf"),
                                                     municipio_ibge=params.municipio_ibge):
                chave = reg.get("numeroControlePNCP") or json.dumps(reg, sort_keys=True)[:200]
                brutos.setdefault(chave, reg)
                n += 1
        except ErroAPI:
            res.modalidades_com_falha.append(mod)
            log.error("Modalidade %s ficou incompleta (ver erro acima).", mod)
        res.por_modalidade[mod] = n
        log.info("Modalidade %s: %d registro(s)", mod, n)
    res.encontradas = len(brutos)

    # 2) Escopo (esfera, UF, município, prazo) e 3) palavras-chave.
    candidatos: list[tuple[dict, dict]] = []
    for bruto in brutos.values():
        reg = mapear(bruto, config.get("sistemas_origem", {}))
        if reg["uf"] and reg["uf"].upper() != str(cfg_api.get("uf", "GO")).upper():
            continue
        if reg["esfera_id"] and reg["esfera_id"] not in esferas:
            continue
        if params.municipio_ibge and reg["codigo_ibge"] and reg["codigo_ibge"] != str(params.municipio_ibge):
            continue
        enc = reg["data_encerramento"]
        if enc is not None and not (agora <= enc <= limite):
            continue
        res.no_escopo += 1
        avaliacao = filtro.avaliar(bruto)
        if not avaliacao.aceito:
            if avaliacao.termos:
                log.info("Descartada %s (%s): %s", reg["numero_controle"], avaliacao.motivo,
                         reg["objeto"][:120])
            continue
        reg["termos"] = avaliacao.termos
        candidatos.append((bruto, reg))
    res.filtradas = len(candidatos)
    log.info("%d no escopo, %d passaram no filtro de palavras-chave", res.no_escopo, res.filtradas)

    # 4) Benefício ME/EPP a partir dos itens.
    dump: list[dict] = []
    for bruto, reg in candidatos:
        itens: list[dict] = []
        cache = historico.beneficio_em_cache(reg["numero_controle"], reg["data_atualizacao"])
        if cache:
            reg["situacao_me_epp"], reg["contagem_itens"] = cache
        else:
            chave = chave_compra(bruto)
            situacao, contagem = NAO_INFORMADO, {}
            if chave:
                try:
                    itens = cliente.itens_contratacao(*chave)
                    situacao, contagem = classificar_me_epp(itens)
                except ErroAPI:
                    log.error("Itens indisponíveis para %s", reg["numero_controle"])
            reg["situacao_me_epp"], reg["contagem_itens"] = situacao, contagem
        if params.salvar_bruto:
            dump.append({"contratacao": bruto, "itens": itens})

    # 5) Somente ME/EPP (opcional), 6) histórico.
    for _, reg in candidatos:
        if params.somente_me_epp and reg["situacao_me_epp"] not in SITUACOES_ME_EPP:
            continue
        reg["estado"] = historico.registrar(reg)
        res.registros.append(reg)
    res.me_epp = sum(1 for _, r in candidatos if r["situacao_me_epp"] in SITUACOES_ME_EPP)
    res.exclusivas = sum(1 for _, r in candidatos if r["situacao_me_epp"] == EXCLUSIVA)
    res.novas = sum(1 for r in res.registros if r["estado"] == "nova")
    res.falhas = len(cliente.falhas)

    if params.salvar_bruto:
        destino = Path(config["saida"]["pasta"]) / f"bruto_{agora:%Y%m%d_%H%M}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        log.info("Respostas brutas salvas em %s", destino)
    return res
