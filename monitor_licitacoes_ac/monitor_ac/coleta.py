"""Orquestra uma execução: consulta, filtra, classifica ME/EPP, grava histórico e relatório."""
from __future__ import annotations

import json
import hashlib
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from .api_client import ClientePNCP, ErroAPI, ErroAPIInterrompida, ErroAPILimite
from .filtros import (EXCLUSIVA, NAO_INFORMADO, SITUACOES_ME_EPP, FiltroPalavras,
                      ResultadoFiltro, avaliar_catalogo, corresponde_termos, classificar_me_epp)
from .catalogo import Catalogo, carregar_catalogo
from .mapeamento import chave_compra, mapear, parse_data
from .persistencia import Historico

log = logging.getLogger(__name__)
_RAIZ_COLETA = Path(__file__).resolve().parent.parent


@dataclass
class Parametros:
    dias: int = 30
    municipio_ibge: str | None = None
    somente_me_epp: bool = False
    incluir_federal: bool = False
    modalidades: list[int] | None = None
    salvar_bruto: bool = False
    esferas: list[str] | None = None
    palavras_chave: list[str] | None = None
    areas_atuacao: list[str] | None = None
    # None preserva o comportamento v1; uma lista seleciona o fluxo de catálogo v2.
    setores: list[str] | None = None
    servicos: list[str] = field(default_factory=list)
    subareas: dict[str, list[str]] = field(default_factory=dict)
    contextos: list[str] = field(default_factory=list)
    incluir_predial_generico: bool = False
    perfil: str | None = None
    compatibilidade_v1: dict[str, Any] | None = None
    catalogo: Catalogo | None = None


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
             historico: Historico, agora: datetime | None = None,
             progresso: Callable[[str, dict[str, Any]], None] | None = None,
             controles: dict[str, Any] | None = None) -> Resultado:
    agora = agora or datetime.now()
    limite = agora + timedelta(days=params.dias)
    cfg_api = config["api"]
    modalidades = params.modalidades or cfg_api["modalidades"]
    esferas = {e.upper() for e in (params.esferas or config.get("esferas", ["E", "M"]))}
    if params.incluir_federal:
        esferas.add("F")
    filtro = FiltroPalavras(config["filtro"])
    catalogo = params.catalogo
    if params.setores is not None and catalogo is None:
        cfg_catalogo = config.get("catalogo_areas")
        if cfg_catalogo:
            caminho_catalogo = Path(cfg_catalogo)
            if not caminho_catalogo.is_absolute():
                caminho_catalogo = Path(config.get("saida", {}).get("pasta", _RAIZ_COLETA)).resolve().parent / caminho_catalogo
            catalogo = carregar_catalogo(caminho_catalogo)
        else:
            catalogo = carregar_catalogo()
    filtros_v2 = {"setores": params.setores or [], "servicos": params.servicos,
                  "subareas": params.subareas, "contextos": params.contextos,
                  "palavras_chave": params.palavras_chave or [],
                  "incluir_predial_generico": params.incluir_predial_generico,
                  "perfil": params.perfil, "compatibilidade_v1": params.compatibilidade_v1}

    def avaliar_tecnico(bruto: dict) -> ResultadoFiltro:
        if params.setores is None:
            return filtro.avaliar(bruto)
        avaliado = avaliar_catalogo(bruto, filtros_v2, catalogo)
        if params.compatibilidade_v1 is not None:
            legado = filtro.avaliar(bruto)
            if not legado.aceito or not avaliado.aceito:
                return ResultadoFiltro(False, avaliado.termos, legado.motivo if not legado.aceito else avaliado.motivo)
            return ResultadoFiltro(True, list(dict.fromkeys(legado.termos + avaliado.termos)),
                                   evidencias=avaliado.evidencias)
        return avaliado
    res = Resultado()
    controles = controles or {}
    interrompida = False

    def kwargs_controlados(metodo: Any) -> dict[str, Any]:
        """Passa apenas controles aceitos, preservando clientes de teste/integrações antigas."""
        try:
            parametros_metodo = inspect.signature(metodo).parameters
        except (TypeError, ValueError):
            return {}
        return {nome: valor for nome, valor in controles.items()
                if nome in parametros_metodo and valor is not None}

    def avaliar_registro(bruto: dict, identidade: str) -> tuple[dict, Any] | None:
        """Aplica o escopo completo a um registro; reutilizado para avisar cedo."""
        reg = mapear(bruto, config.get("sistemas_origem", {}))
        if not reg["numero_controle"]:
            reg["numero_controle"] = identidade
        if not reg["uf"] or reg["uf"].upper() != str(cfg_api.get("uf", "GO")).upper():
            return None
        if not reg["esfera_id"] or reg["esfera_id"] not in esferas:
            return None
        if params.municipio_ibge and (not reg["codigo_ibge"] or reg["codigo_ibge"] != str(params.municipio_ibge)):
            return None
        enc = reg["data_encerramento"]
        if enc is None or not (agora <= enc <= limite):
            return None
        avaliacao = avaliar_tecnico(bruto)
        if not avaliacao.aceito:
            return None
        if params.setores is None and params.palavras_chave and not corresponde_termos(reg["objeto"], params.palavras_chave):
            return None
        if params.areas_atuacao and not corresponde_termos(reg["objeto"], params.areas_atuacao):
            return None
        reg["termos"] = avaliacao.termos
        if avaliacao.evidencias:
            reg["evidencias"] = avaliacao.evidencias
        return reg, avaliacao

    def identidade_de(reg: dict) -> str:
        chave = str(reg.get("numeroControlePNCP") or "").strip()
        if chave:
            return chave
        compra = chave_compra(reg)
        if compra:
            cnpj, ano, sequencial = compra
            return f"{cnpj}-1-{sequencial:06d}/{ano}"
        return "sem-controle:" + hashlib.sha256(
            json.dumps(reg, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()

    # 1) Coleta de todas as modalidades, sem duplicar.
    brutos: dict[str, dict] = {}
    preliminares: dict[str, int] = {}
    for mod in modalidades:
        n = 0
        pagina_exata = False
        def ao_receber_pagina(info: dict[str, Any]) -> None:
            if progresso:
                evento = dict(info)
                quantidade = evento.get("registros_pagina", evento.get("registros", 0))
                registros_pagina = len(quantidade) if isinstance(quantidade, list) else int(quantidade or 0)
                acumulado_modalidade = n + registros_pagina
                evento.setdefault("modalidade", mod)
                evento.setdefault("registros_pagina", registros_pagina)
                evento.pop("registros", None)
                evento.setdefault("registros_modalidade", acumulado_modalidade)
                evento.setdefault("requisicoes", cliente.requisicoes)
                evento.setdefault("falhas", len(cliente.falhas))
                evento.setdefault("encontradas", sum(res.por_modalidade.values()) + acumulado_modalidade)
                progresso("pagina", evento)
        try:
            metodo_coleta = cliente.contratacoes_proposta
            try:
                suporta_pagina = "ao_receber_pagina" in inspect.signature(metodo_coleta).parameters
            except (TypeError, ValueError):
                suporta_pagina = False
            kwargs_coleta = {"uf": cfg_api.get("uf"), "municipio_ibge": params.municipio_ibge}
            if suporta_pagina:
                kwargs_coleta["ao_receber_pagina"] = ao_receber_pagina
                pagina_exata = True
            kwargs_coleta.update(kwargs_controlados(metodo_coleta))
            for reg in metodo_coleta(limite.date(), mod, **kwargs_coleta):
                chave = identidade_de(reg)
                anterior = brutos.get(chave)
                if anterior is None or _atualizacao(reg) > _atualizacao(anterior):
                    brutos[chave] = reg
                    avaliado = avaliar_registro(reg, chave)
                    if avaliado:
                        mapeado, _ = avaliado
                        revisao = preliminares.get(chave, 0) + 1
                        preliminares[chave] = revisao
                        if progresso:
                            progresso("candidato", {"status": "beneficio_pendente", "identidade": chave,
                                                     "registros": dict(mapeado), "revisao": revisao})
                    elif chave in preliminares:
                        revisao = preliminares[chave] + 1
                        preliminares[chave] = revisao
                        if progresso:
                            progresso("candidato_retirado", {"identidade": chave, "revisao": revisao,
                                                               "motivo": "versão mais recente não corresponde aos filtros"})
                n += 1
                tamanho = max(1, int(cfg_api.get("tamanho_pagina", 50)))
                if progresso and not pagina_exata and n % tamanho == 0:
                    progresso("pagina", {"modalidade": mod, "pagina": n // tamanho,
                                          "registros_pagina": tamanho, "registros_modalidade": n,
                                          "estimada": True,
                                          "encontradas": sum(res.por_modalidade.values()) + n,
                                          "requisicoes": cliente.requisicoes, "falhas": len(cliente.falhas)})
        except ErroAPI as exc:
            if isinstance(exc, ErroAPIInterrompida):
                interrompida = True
                if isinstance(exc, ErroAPILimite):
                    res.modalidades_com_falha.append(mod)
                log.info("Coleta interrompida durante a modalidade %s: %s", mod, exc)
            else:
                res.modalidades_com_falha.append(mod)
                log.error("Modalidade %s ficou incompleta (ver erro acima).", mod)
        res.por_modalidade[mod] = n
        if progresso and not pagina_exata and n % max(1, int(cfg_api.get("tamanho_pagina", 50))):
            progresso("pagina", {"modalidade": mod,
                                  "pagina": (n // max(1, int(cfg_api.get("tamanho_pagina", 50)))) + 1,
                                  "registros_pagina": n % max(1, int(cfg_api.get("tamanho_pagina", 50))),
                                  "registros_modalidade": n, "final": True,
                                  "estimada": True,
                                  "encontradas": sum(res.por_modalidade.values()),
                                  "requisicoes": cliente.requisicoes, "falhas": len(cliente.falhas)})
        log.info("Modalidade %s: %d registro(s)", mod, n)
        if progresso:
            progresso("modalidade", {"modalidade": mod, "registros": n,
                                      "encontradas": sum(res.por_modalidade.values()),
                                      "requisicoes": cliente.requisicoes,
                                      "falhas": len(cliente.falhas)})
        if interrompida:
            break
    res.encontradas = len(brutos)

    # 2) Escopo (esfera, UF, município, prazo) e 3) palavras-chave.
    candidatos: list[tuple[dict, dict]] = []
    for identidade, bruto in brutos.items():
        reg = mapear(bruto, config.get("sistemas_origem", {}))
        if not reg["numero_controle"]:
            reg["numero_controle"] = identidade
        if not reg["uf"] or reg["uf"].upper() != str(cfg_api.get("uf", "GO")).upper():
            continue
        if not reg["esfera_id"] or reg["esfera_id"] not in esferas:
            continue
        if params.municipio_ibge and (not reg["codigo_ibge"] or reg["codigo_ibge"] != str(params.municipio_ibge)):
            continue
        enc = reg["data_encerramento"]
        if enc is None or not (agora <= enc <= limite):
            continue
        res.no_escopo += 1
        avaliacao = avaliar_tecnico(bruto)
        if not avaliacao.aceito:
            if avaliacao.termos:
                log.info("Descartada %s (%s): %s", reg["numero_controle"], avaliacao.motivo,
                         reg["objeto"][:120])
            continue
        if params.setores is None and params.palavras_chave and not corresponde_termos(reg["objeto"], params.palavras_chave):
            continue
        if params.areas_atuacao and not corresponde_termos(reg["objeto"], params.areas_atuacao):
            continue
        reg["termos"] = avaliacao.termos
        if avaliacao.evidencias:
            reg["evidencias"] = avaliacao.evidencias
        candidatos.append((bruto, reg))
    res.filtradas = len(candidatos)
    log.info("%d no escopo, %d passaram no filtro de palavras-chave", res.no_escopo, res.filtradas)

    # 4) Benefício ME/EPP a partir dos itens.
    dump: list[dict] = []
    for bruto, reg in candidatos:
        if interrompida:
            break
        itens: list[dict] = []
        cache = historico.beneficio_em_cache(reg["numero_controle"], reg["data_atualizacao"])
        if cache:
            reg["situacao_me_epp"], reg["contagem_itens"] = cache
            reg["origem_itens"] = "cache"
        else:
            chave = chave_compra(bruto)
            situacao, contagem = NAO_INFORMADO, {}
            reg["origem_itens"] = "indisponivel"
            if chave:
                try:
                    itens = cliente.itens_contratacao(*chave,
                                                      **kwargs_controlados(cliente.itens_contratacao))
                    situacao, contagem = classificar_me_epp(itens)
                    reg["origem_itens"] = "consulta"
                except ErroAPI as exc:
                    if isinstance(exc, ErroAPIInterrompida):
                        interrompida = True
                        log.info("Classificação de itens interrompida em %s: %s", reg["numero_controle"], exc)
                    else:
                        log.error("Itens indisponíveis para %s", reg["numero_controle"])
                        reg["origem_itens"] = "falha"
            reg["situacao_me_epp"], reg["contagem_itens"] = situacao, contagem
        if progresso:
            progresso("resultado", dict(reg))
        if params.salvar_bruto:
            dump.append({"contratacao": bruto,
                         "itens": itens if reg.get("origem_itens") == "consulta" else None,
                         "origem_itens": reg.get("origem_itens")})

    # 5) Somente ME/EPP (opcional), 6) histórico.
    # Grava todos os candidatos antes do filtro de apresentação ME/EPP.
    for _, reg in candidatos:
        if interrompida and reg.get("situacao_me_epp") == NAO_INFORMADO and reg.get("origem_itens") == "indisponivel":
            continue
        reg["estado"] = historico.registrar(reg)
    for _, reg in candidatos:
        if params.somente_me_epp and reg["situacao_me_epp"] not in SITUACOES_ME_EPP:
            continue
        res.registros.append(reg)
    res.me_epp = sum(1 for _, r in candidatos if r["situacao_me_epp"] in SITUACOES_ME_EPP)
    res.exclusivas = sum(1 for _, r in candidatos if r["situacao_me_epp"] == EXCLUSIVA)
    res.novas = sum(1 for r in res.registros if r["estado"] == "nova")
    res.falhas = len(cliente.falhas)

    if progresso:
        progresso("fim", {"encontradas": res.encontradas, "filtradas": res.filtradas,
                           "registros": len(res.registros), "requisicoes": cliente.requisicoes,
                           "falhas": res.falhas})

    if params.salvar_bruto:
        destino = Path(config["saida"]["pasta"]) / f"bruto_{agora:%Y%m%d_%H%M%S_%f}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        log.info("Respostas brutas salvas em %s", destino)
    return res


def _atualizacao(reg: dict) -> str:
    """Chave comparável para preferir a versão mais recente de uma compra."""
    valor = reg.get("dataAtualizacao") or reg.get("dataAtualizacaoGlobal") or ""
    data = parse_data(valor)
    return data.isoformat(timespec="microseconds") if data else str(valor)
