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
from datetime import date
from typing import Any, Iterator

import requests

log = logging.getLogger(__name__)

STATUS_REPETIR = {408, 425, 429, 500, 502, 503, 504}


class ErroAPI(Exception):
    """Falha definitiva de requisição (após todas as tentativas)."""


class ClientePNCP:
    def __init__(self, cfg_api: dict[str, Any], sessao: requests.Session | None = None,
                 dormir=time.sleep):
        self.cfg = cfg_api
        self.sessao = sessao or requests.Session()
        self.sessao.headers.update({
            "Accept": "application/json",
            "User-Agent": "monitor-licitacoes-ac-go/1.0 (+uso pessoal; consultas publicas)",
        })
        self._dormir = dormir
        self._ultima = 0.0
        self.falhas: list[str] = []
        self.requisicoes = 0

    # ------------------------------------------------------------------ HTTP
    def _aguardar_intervalo(self) -> None:
        intervalo = float(self.cfg.get("intervalo_entre_requisicoes", 1.0))
        decorrido = time.monotonic() - self._ultima
        if self._ultima and decorrido < intervalo:
            self._dormir(intervalo - decorrido)

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any | None:
        """GET com timeout, retry e backoff exponencial. ``None`` = HTTP 204/corpo vazio."""
        tentativas = int(self.cfg.get("tentativas", 5))
        espera = float(self.cfg.get("backoff_inicial", 2.0))
        timeout = (float(self.cfg.get("timeout_conexao", 15)),
                   float(self.cfg.get("timeout_leitura", 90)))
        ultimo_erro = ""
        for tentativa in range(1, tentativas + 1):
            self._aguardar_intervalo()
            self._ultima = time.monotonic()
            self.requisicoes += 1
            try:
                resp = self.sessao.get(url, params=params, timeout=timeout)
            except requests.RequestException as exc:
                ultimo_erro = f"{type(exc).__name__}: {exc}"
            else:
                if resp.status_code == 204 or (resp.status_code == 200 and not resp.content.strip()):
                    return None
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except ValueError:
                        ultimo_erro = f"JSON inválido: {resp.text[:200]!r}"
                elif resp.status_code in STATUS_REPETIR:
                    ultimo_erro = f"HTTP {resp.status_code}: {resp.text[:200]!r}"
                    retry_after = resp.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        espera = max(espera, float(retry_after))
                else:
                    # 4xx (exceto 408/425/429): parâmetro inválido etc. Não adianta repetir.
                    msg = f"HTTP {resp.status_code} em {resp.url}: {resp.text[:300]!r}"
                    log.error(msg)
                    self.falhas.append(msg)
                    raise ErroAPI(msg)
            if tentativa < tentativas:
                log.warning("Falha na tentativa %d/%d (%s) em %s %s; nova tentativa em %.0fs",
                            tentativa, tentativas, ultimo_erro, url, params or "", espera)
                self._dormir(espera)
                espera *= 2
        msg = f"Desistindo após {tentativas} tentativas: {url} {params or ''} -> {ultimo_erro}"
        log.error(msg)
        self.falhas.append(msg)
        raise ErroAPI(msg)

    # ------------------------------------------------------------- Consultas
    def contratacoes_proposta(self, data_final: date, modalidade: int | None,
                              uf: str | None = None,
                              municipio_ibge: str | None = None) -> Iterator[dict]:
        """Itera por todas as páginas de /v1/contratacoes/proposta."""
        url = f"{self.cfg['base_consulta'].rstrip('/')}/v1/contratacoes/proposta"
        pagina = 1
        while True:
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
            corpo = self.get_json(url, params)
            if not corpo:
                return
            registros = (corpo.get("data") or []) if isinstance(corpo, dict) else corpo
            log.debug("modalidade=%s pagina=%d registros=%d total=%s", modalidade, pagina,
                      len(registros), corpo.get("totalRegistros") if isinstance(corpo, dict) else "?")
            yield from registros
            if not isinstance(corpo, dict) or not registros:
                return
            total_paginas = corpo.get("totalPaginas")
            restantes = corpo.get("paginasRestantes")
            if restantes is not None:
                if int(restantes) <= 0:
                    return
            elif total_paginas is None or pagina >= int(total_paginas):
                return
            pagina += 1

    def itens_contratacao(self, cnpj: str, ano: int | str, sequencial: int | str) -> list[dict]:
        """Todos os itens de uma contratação (a API aceita paginação opcional)."""
        url = (f"{self.cfg['base_pncp'].rstrip('/')}/v1/orgaos/{cnpj}/compras/"
               f"{ano}/{sequencial}/itens")
        tamanho = int(self.cfg.get("tamanho_pagina_itens", 500))
        itens: list[dict] = []
        pagina = 1
        while True:
            corpo = self.get_json(url, {"pagina": pagina, "tamanhoPagina": tamanho})
            if not corpo:
                break
            lote = corpo.get("data", []) if isinstance(corpo, dict) else corpo
            itens.extend(lote)
            if len(lote) < tamanho:
                break
            pagina += 1
        return itens
