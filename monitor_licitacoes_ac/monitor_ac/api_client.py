"""Cliente da API pública do PNCP (Consultas + itens da contratação).

Endpoints usados (Manual das APIs de Consultas do PNCP e Swagger oficial):

* ``GET {base_consulta}/v1/contratacoes/proposta`` - contratações com período de
  recebimento de propostas em aberto. Parâmetros: ``dataFinal`` (AAAAMMDD,
  obrigatório), ``codigoModalidadeContratacao`` (obrigatório na versão 1.0 do
  manual), ``pagina`` (obrigatório), ``tamanhoPagina``, ``uf``,
  ``codigoMunicipioIbge``, ``cnpj``. Resposta paginada:
  ``{data, totalRegistros, totalPaginas, numeroPagina, paginasRestantes, empty}``.
  Sem resultados, a API costuma responder HTTP 204 sem corpo.
* ``GET {base_pncp}/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens`` - itens
  da contratação, com ``tipoBeneficio``/``tipoBeneficioNome`` por item.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
from typing import Any, Callable, Iterator

import requests

log = logging.getLogger(__name__)

STATUS_REPETIR = {408, 425, 429, 500, 502, 503, 504}


class ErroAPI(Exception):
    """Falha definitiva de requisição (após todas as tentativas)."""


class ErroAPIInterrompida(ErroAPI):
    """A consulta foi cancelada ou atingiu seu prazo/orçamento operacional."""


class ErroAPILimite(ErroAPIInterrompida):
    """O PNCP limitou as requisições e encerra a execução atual."""


class ClientePNCP:
    def __init__(self, cfg_api: dict[str, Any], sessao: requests.Session | None = None,
                 dormir=time.sleep, monotonic=time.monotonic):
        self.cfg = cfg_api
        self._owns_session = sessao is None
        self.sessao = sessao if sessao is not None else requests.Session()
        self.sessao.headers.update({
            "Accept": "application/json",
            "User-Agent": "monitor-licitacoes-ac-go/1.0 (+uso pessoal; consultas publicas)",
        })
        self._dormir = dormir
        self._monotonic = monotonic
        self._ultima = 0.0
        self.falhas: list[str] = []
        self.requisicoes = 0

    def close(self) -> None:
        """Fecha a sessão apenas quando criada por este cliente."""
        if self._owns_session:
            self.sessao.close()

    def __enter__(self) -> "ClientePNCP":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _falha_formato(self, detalhe: str, url: str) -> ErroAPI:
        msg = f"Resposta inválida da API em {url}: {detalhe}"
        log.error(msg)
        self.falhas.append(msg)
        return ErroAPI(msg)

    @staticmethod
    def _retry_after(valor: str) -> float | None:
        """Interpreta Retry-After como delta em segundos ou data HTTP."""
        if not valor:
            return None
        try:
            segundos = float(valor.strip())
            return max(0.0, segundos) if segundos >= 0 else None
        except ValueError:
            pass
        try:
            dt = parsedate_to_datetime(valor)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _meta_inteiro(valor: Any, nome: str, minimo: int = 0) -> int:
        if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
            raise ValueError(f"'{nome}' deve ser inteiro >= {minimo}")
        return valor

    # ------------------------------------------------------------------ HTTP
    @staticmethod
    def _cancelado(cancelar: Any) -> bool:
        if cancelar is None:
            return False
        if callable(cancelar):
            return bool(cancelar())
        is_set = getattr(cancelar, "is_set", None)
        return bool(is_set()) if is_set else bool(cancelar)

    def _validar_execucao(self, deadline_monotonic: float | None, cancelar: Any) -> float | None:
        if self._cancelado(cancelar):
            raise ErroAPIInterrompida("Consulta cancelada; nenhuma nova requisição será iniciada")
        restante = None if deadline_monotonic is None else deadline_monotonic - self._monotonic()
        if restante is not None and restante <= 0:
            raise ErroAPIInterrompida("Prazo global da consulta esgotado; nenhuma nova requisição será iniciada")
        return restante

    def _esperar(self, segundos: float, deadline_monotonic: float | None, cancelar: Any) -> None:
        """Espera cooperativamente. Uma requisição HTTP já iniciada não é interrompida."""
        restante = self._validar_execucao(deadline_monotonic, cancelar)
        if restante is not None:
            segundos = min(segundos, restante)
        if segundos <= 0:
            self._validar_execucao(deadline_monotonic, cancelar)
            return
        wait = getattr(cancelar, "wait", None) if cancelar is not None else None
        if callable(wait):
            wait(segundos)
        else:
            self._dormir(segundos)
        self._validar_execucao(deadline_monotonic, cancelar)

    def _aguardar_intervalo(self, deadline_monotonic: float | None = None,
                            cancelar: Any = None) -> None:
        self._validar_execucao(deadline_monotonic, cancelar)
        intervalo = float(self.cfg.get("intervalo_entre_requisicoes", 1.0))
        decorrido = self._monotonic() - self._ultima
        if self._ultima and decorrido < intervalo:
            self._esperar(intervalo - decorrido, deadline_monotonic, cancelar)

    def _get_json_controlado(self, url: str, params: dict[str, Any] | None, *,
                             deadline_monotonic: float | None, cancelar: Any,
                             max_tentativas: int | None,
                             ao_iniciar_tentativa: Callable[[], bool] | None) -> Any | None:
        """Mantém a chamada legada de get_json intacta quando não há controles novos."""
        controles = {}
        if deadline_monotonic is not None:
            controles["deadline_monotonic"] = deadline_monotonic
        if cancelar is not None:
            controles["cancelar"] = cancelar
        if max_tentativas is not None:
            controles["max_tentativas"] = max_tentativas
        if ao_iniciar_tentativa is not None:
            controles["ao_iniciar_tentativa"] = ao_iniciar_tentativa
        if not controles:
            return self.get_json(url, params)
        return self.get_json(url, params, **controles)

    @staticmethod
    def _emitir_pagina(callback: Callable[[dict[str, Any]], None] | None,
                       modalidade: int | None, pagina: int, corpo: dict[str, Any],
                       registros: list[dict[str, Any]]) -> None:
        if callback is None:
            return
        callback({"modalidade": modalidade, "pagina": pagina,
                  "registros": [dict(registro) for registro in registros],
                  "total_registros": corpo.get("totalRegistros"),
                  "total_paginas": corpo.get("totalPaginas"),
                  "paginas_restantes": corpo.get("paginasRestantes")})

    def get_json(self, url: str, params: dict[str, Any] | None = None, *,
                 deadline_monotonic: float | None = None, cancelar: Any = None,
                 max_tentativas: int | None = None,
                 ao_iniciar_tentativa: Callable[[], bool] | None = None) -> Any | None:
        """GET com timeout, retry e backoff exponencial. ``None`` representa somente HTTP 204."""
        agora = self._monotonic()
        liberacao = float(self.cfg.get("_retry_not_before_monotonic", 0.0))
        if liberacao > agora:
            restante = liberacao - agora
            msg = (f"Nova consulta bloqueada pelo limite 429 anterior; aguarde {restante:.0f}s "
                   "antes de iniciar outra consulta")
            log.error(msg)
            self.falhas.append(msg)
            raise ErroAPILimite(msg)
        if liberacao:
            self.cfg.pop("_retry_not_before_monotonic", None)
        tentativas = max(1, min(10, int(self.cfg.get("tentativas", 5))))
        if max_tentativas is not None:
            tentativas = min(tentativas, max(0, int(max_tentativas)))
        if tentativas == 0:
            raise ErroAPIInterrompida("Orçamento de tentativas da consulta esgotado")
        espera = float(self.cfg.get("backoff_inicial", 2.0))
        timeout = (float(self.cfg.get("timeout_conexao", 15)),
                   float(self.cfg.get("timeout_leitura", 90)))
        ultimo_erro = ""
        for tentativa in range(1, tentativas + 1):
            self._aguardar_intervalo(deadline_monotonic, cancelar)
            restante = self._validar_execucao(deadline_monotonic, cancelar)
            timeout_tentativa = timeout
            if restante is not None:
                if restante <= 0.002:
                    raise ErroAPIInterrompida("Prazo global insuficiente para iniciar outra requisição")
                # Requests usa timeouts separados para conexão/leitura; dividir
                # o orçamento restante mantém a soma configurada dentro do prazo.
                conexao = min(timeout[0], restante / 2)
                leitura = min(timeout[1], restante - conexao)
                timeout_tentativa = (max(0.001, conexao), max(0.001, leitura))
            self._ultima = self._monotonic()
            if ao_iniciar_tentativa is not None and not ao_iniciar_tentativa():
                raise ErroAPIInterrompida("Orçamento global de tentativas da consulta esgotado")
            self.requisicoes += 1
            try:
                resp = self.sessao.get(url, params=params, timeout=timeout_tentativa)
            except requests.RequestException as exc:
                ultimo_erro = f"{type(exc).__name__}: {exc}"
            else:
                if resp.status_code == 204:
                    return None
                if resp.status_code == 200:
                    try:
                        corpo = resp.json()
                        if corpo is None:
                            ultimo_erro = "JSON vazio ou null em resposta HTTP 200"
                        else:
                            return corpo
                    except ValueError:
                        ultimo_erro = f"JSON inválido: {resp.text[:200]!r}"
                elif resp.status_code in STATUS_REPETIR:
                    ultimo_erro = f"HTTP {resp.status_code}: {resp.text[:200]!r}"
                    if resp.status_code == 429:
                        retry_after = self._retry_after(resp.headers.get("Retry-After", ""))
                        if retry_after is not None and retry_after > 0:
                            liberacao = self._monotonic() + retry_after
                            self.cfg["_retry_not_before_monotonic"] = max(
                                liberacao, float(self.cfg.get("_retry_not_before_monotonic", 0.0)))
                        orientacao = (f" aguarde {retry_after:.0f}s antes de iniciar outra consulta."
                                      if retry_after is not None and retry_after > 0 else "")
                        msg = (f"HTTP 429 em {url}: limite de requisições atingido; "
                               f"execução interrompida sem retry automático.{orientacao}")
                        log.error(msg)
                        self.falhas.append(msg)
                        raise ErroAPILimite(msg)
                    retry_after = self._retry_after(resp.headers.get("Retry-After", ""))
                    if retry_after is not None:
                        if retry_after > 300:
                            msg = f"Retry-After de {retry_after:.0f}s excede limite operacional de 300s em {url}"
                            log.error(msg)
                            self.falhas.append(msg)
                            raise ErroAPI(msg)
                        espera = max(espera, retry_after)
                else:
                    # 4xx (exceto 408/425/429): parâmetro inválido etc. Não adianta repetir.
                    msg = f"HTTP {resp.status_code} em {resp.url}: {resp.text[:300]!r}"
                    log.error(msg)
                    self.falhas.append(msg)
                    raise ErroAPI(msg)
            if tentativa < tentativas:
                log.warning("Falha na tentativa %d/%d (%s) em %s %s; nova tentativa em %.0fs",
                            tentativa, tentativas, ultimo_erro, url, params or "", espera)
                self._esperar(espera, deadline_monotonic, cancelar)
                espera *= 2
        msg = f"Desistindo após {tentativas} tentativas: {url} {params or ''} -> {ultimo_erro}"
        log.error(msg)
        self.falhas.append(msg)
        raise ErroAPI(msg)

    # ------------------------------------------------------------- Consultas
    def contratacoes_proposta(self, data_final: date, modalidade: int | None,
                              uf: str | None = None,
                              municipio_ibge: str | None = None, *,
                              ao_receber_pagina: Callable[[dict[str, Any]], None] | None = None,
                              deadline_monotonic: float | None = None, cancelar: Any = None,
                              max_tentativas: int | None = None,
                              ao_iniciar_tentativa: Callable[[], bool] | None = None) -> Iterator[dict]:
        """Itera por todas as páginas de /v1/contratacoes/proposta."""
        url = f"{self.cfg['base_consulta'].rstrip('/')}/v1/contratacoes/proposta"
        pagina = 1
        max_paginas = max(1, min(10000, int(self.cfg.get("max_paginas", 1000))))
        vistas: set[str] = set()
        while True:
            if pagina > max_paginas:
                raise self._falha_formato(f"limite de {max_paginas} páginas excedido", url)
            params: dict[str, Any] = {
                "dataFinal": data_final.strftime("%Y%m%d"),
                "pagina": pagina,
                "tamanhoPagina": int(self.cfg.get("tamanho_pagina", 50)),
            }
            if modalidade is not None:
                params["codigoModalidadeContratacao"] = modalidade
            if uf:
                params["uf"] = uf
            if municipio_ibge:
                params["codigoMunicipioIbge"] = municipio_ibge
            corpo = self._get_json_controlado(url, params, deadline_monotonic=deadline_monotonic,
                                               cancelar=cancelar, max_tentativas=max_tentativas,
                                               ao_iniciar_tentativa=ao_iniciar_tentativa)
            if corpo is None:
                return
            if not isinstance(corpo, dict):
                raise self._falha_formato("esperado objeto JSON paginado", url)
            registros = corpo.get("data")
            if not isinstance(registros, list) or any(not isinstance(x, dict) for x in registros):
                raise self._falha_formato("campo 'data' deve ser lista de objetos", url)
            if not registros:
                try:
                    numero = corpo.get("numeroPagina")
                    paginas = corpo.get("totalPaginas")
                    restantes = corpo.get("paginasRestantes")
                    total_registros = corpo.get("totalRegistros")
                    if numero is not None and self._meta_inteiro(numero, "numeroPagina", 1) != pagina:
                        raise ValueError("'numeroPagina' diverge da página solicitada")
                    if paginas is not None:
                        paginas = self._meta_inteiro(paginas, "totalPaginas")
                    if restantes is not None:
                        restantes = self._meta_inteiro(restantes, "paginasRestantes")
                    if total_registros is not None:
                        total_registros = self._meta_inteiro(total_registros, "totalRegistros")
                    if (restantes is not None and restantes > 0) or (total_registros is not None and total_registros > 0):
                        raise ValueError("página vazia contradiz metadados que indicam registros restantes")
                    if paginas is not None and paginas > pagina:
                        raise ValueError("página vazia contradiz totalPaginas")
                except (TypeError, ValueError, OverflowError):
                    raise self._falha_formato("metadados inconsistentes em página vazia", url)
                self._emitir_pagina(ao_receber_pagina, modalidade, pagina, corpo, registros)
                return
            if registros:
                try:
                    assinatura = hashlib.sha256(json.dumps(registros, sort_keys=True, ensure_ascii=False,
                                                           default=str).encode()).hexdigest()
                except (TypeError, ValueError):
                    raise self._falha_formato("conteúdo de página não pode ser validado", url)
                if assinatura in vistas:
                    raise self._falha_formato(f"página repetida detectada (página {pagina})", url)
                vistas.add(assinatura)
            log.debug("modalidade=%s pagina=%d registros=%d total=%s", modalidade, pagina,
                      len(registros), corpo.get("totalRegistros") if isinstance(corpo, dict) else "?")
            if ao_receber_pagina is None:
                # Preserva o comportamento histórico dos geradores sem callback:
                # registros seguem disponíveis antes da validação de paginação.
                yield from registros
            total_paginas = corpo.get("totalPaginas")
            restantes = corpo.get("paginasRestantes")
            numero_pagina = corpo.get("numeroPagina")
            ultima_pagina = False
            try:
                if numero_pagina is not None and self._meta_inteiro(numero_pagina, "numeroPagina", 1) != pagina:
                    raise ValueError("'numeroPagina' diverge da página solicitada")
                if total_paginas is not None:
                    total_paginas = self._meta_inteiro(total_paginas, "totalPaginas", 1)
                if restantes is not None:
                    restantes = self._meta_inteiro(restantes, "paginasRestantes")
                    if restantes == 0:
                        if total_paginas is not None and pagina != total_paginas:
                            raise ValueError("paginasRestantes e totalPaginas inconsistentes")
                        ultima_pagina = True
                if total_paginas is not None:
                    if pagina > total_paginas:
                        raise ValueError("página atual excede totalPaginas")
                    if restantes is not None and restantes != total_paginas - pagina:
                        raise ValueError("paginasRestantes e totalPaginas inconsistentes")
                    if pagina >= total_paginas:
                        ultima_pagina = True
                elif restantes is None:
                    raise ValueError("faltam totalPaginas e paginasRestantes")
            except (TypeError, ValueError, OverflowError):
                raise self._falha_formato("metadados de paginação inválidos", url)
            self._emitir_pagina(ao_receber_pagina, modalidade, pagina, corpo, registros)
            if ao_receber_pagina is not None:
                yield from registros
            if ultima_pagina:
                return
            pagina += 1

    def itens_contratacao(self, cnpj: str, ano: int | str, sequencial: int | str, *,
                          deadline_monotonic: float | None = None, cancelar: Any = None,
                          max_tentativas: int | None = None,
                          ao_iniciar_tentativa: Callable[[], bool] | None = None) -> list[dict]:
        """Todos os itens de uma contratação (a API aceita paginação opcional)."""
        url = (f"{self.cfg['base_pncp'].rstrip('/')}/v1/orgaos/{cnpj}/compras/"
               f"{ano}/{sequencial}/itens")
        tamanho = int(self.cfg.get("tamanho_pagina_itens", 500))
        itens: list[dict] = []
        pagina = 1
        max_paginas = max(1, min(10000, int(self.cfg.get("max_paginas_itens", 1000))))
        vistas: set[str] = set()
        while True:
            if pagina > max_paginas:
                raise self._falha_formato(f"limite de {max_paginas} páginas de itens excedido", url)
            corpo = self._get_json_controlado(url, {"pagina": pagina, "tamanhoPagina": tamanho},
                                               deadline_monotonic=deadline_monotonic,
                                               cancelar=cancelar, max_tentativas=max_tentativas,
                                               ao_iniciar_tentativa=ao_iniciar_tentativa)
            if corpo is None:
                break
            if isinstance(corpo, dict):
                lote = corpo.get("data")
            else:
                lote = corpo
            if not isinstance(lote, list) or any(not isinstance(x, dict) for x in lote):
                raise self._falha_formato("itens devem ser lista de objetos", url)
            if lote:
                assinatura = hashlib.sha256(json.dumps(lote, sort_keys=True, ensure_ascii=False,
                                                       default=str).encode()).hexdigest()
                if assinatura in vistas:
                    raise self._falha_formato(f"página de itens repetida (página {pagina})", url)
                vistas.add(assinatura)
            itens.extend(lote)
            if not lote:
                if isinstance(corpo, dict):
                    try:
                        restantes_vazios = corpo.get("paginasRestantes")
                        total_vazios = corpo.get("totalPaginas")
                        numero_vazio = corpo.get("numeroPagina")
                        registros_vazios = corpo.get("totalRegistros")
                        if numero_vazio is not None and self._meta_inteiro(numero_vazio, "numeroPagina", 1) != pagina:
                            raise ValueError("'numeroPagina' diverge da página solicitada")
                        if restantes_vazios is not None:
                            restantes_vazios = self._meta_inteiro(restantes_vazios, "paginasRestantes")
                        if total_vazios is not None:
                            total_vazios = self._meta_inteiro(total_vazios, "totalPaginas")
                        if registros_vazios is not None:
                            registros_vazios = self._meta_inteiro(registros_vazios, "totalRegistros")
                        if ((restantes_vazios is not None and restantes_vazios > 0)
                                or (registros_vazios is not None and registros_vazios > 0)
                                or (total_vazios is not None and total_vazios > pagina)):
                            raise ValueError("página vazia contradiz metadados que indicam registros restantes")
                    except (TypeError, ValueError, OverflowError):
                        raise self._falha_formato("metadados inconsistentes em página vazia de itens", url)
                break
            if isinstance(corpo, dict):
                restantes = corpo.get("paginasRestantes")
                total = corpo.get("totalPaginas")
                numero = corpo.get("numeroPagina")
                try:
                    if numero is not None and self._meta_inteiro(numero, "numeroPagina", 1) != pagina:
                        raise ValueError("'numeroPagina' diverge da página solicitada")
                    if restantes is not None:
                        restantes = self._meta_inteiro(restantes, "paginasRestantes")
                    if total is not None:
                        total = self._meta_inteiro(total, "totalPaginas", 1)
                    if total is not None and pagina > total:
                        raise ValueError("página atual excede totalPaginas")
                    if total is not None and restantes is not None and restantes != total - pagina:
                        raise ValueError("paginasRestantes e totalPaginas inconsistentes")
                    if restantes is not None and restantes == 0:
                        if total is not None and pagina != total:
                            raise ValueError("paginasRestantes e totalPaginas inconsistentes")
                        break
                    if total is not None and pagina >= total:
                        break
                    if len(lote) < tamanho:
                        if restantes is not None and restantes > 0:
                            pagina += 1
                            continue
                        if total is not None and pagina < total:
                            pagina += 1
                            continue
                        break
                    if restantes is None and total is None:
                        raise ValueError("faltam metadados de paginação em página cheia")
                except (TypeError, ValueError, OverflowError):
                    raise self._falha_formato("metadados de paginação de itens inválidos", url)
            elif len(lote) < tamanho:
                break
            pagina += 1
        return itens
