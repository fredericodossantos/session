"""Linha de comando: python -m monitor_ac [opções]."""
from __future__ import annotations

import argparse
import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import __version__
from .api_client import ClientePNCP
from .coleta import Parametros, executar
from .config import carregar
from .persistencia import Historico
from .relatorio import publicar

RAIZ = Path(__file__).resolve().parent.parent


def _args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m monitor_ac",
        description="Busca no PNCP licitações abertas de ar-condicionado em Goiás (Estado e municípios).")
    p.add_argument("-d", "--dias", type=int, default=30,
                   help="janela em dias para a data-limite de propostas (padrão: 30)")
    p.add_argument("-m", "--municipio", metavar="IBGE",
                   help="código IBGE (7 dígitos) de um município, ex.: 5208707 (Goiânia)")
    p.add_argument("--somente-me-epp", action="store_true",
                   help="mostrar só licitações com benefício ME/EPP (exclusiva, cota ou parcial)")
    p.add_argument("--incluir-federal", action="store_true",
                   help="incluir órgãos federais sediados em Goiás")
    p.add_argument("--modalidades", help="lista de códigos separada por vírgula (sobrepõe o config)")
    p.add_argument("-c", "--config", default=str(RAIZ / "config.yaml"), help="arquivo YAML/JSON")
    p.add_argument("--salvar-bruto", action="store_true",
                   help="salvar as respostas brutas da API (para conferência dos campos)")
    p.add_argument("-v", "--verbose", action="store_true", help="log detalhado no console")
    p.add_argument("--version", action="version", version=__version__)
    a = p.parse_args(argv)
    if a.dias < 1:
        p.error("--dias deve ser >= 1")
    if a.municipio and not re.fullmatch(r"\d{7}", a.municipio):
        p.error("--municipio deve ter 7 dígitos (código IBGE)")
    if a.municipio and not a.municipio.startswith("52"):
        p.error("--municipio: códigos IBGE de Goiás começam com 52")
    return a


def _configurar_log(pasta: Path, verbose: bool) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    arquivo = RotatingFileHandler(pasta / "monitor.log", maxBytes=2_000_000, backupCount=5,
                                  encoding="utf-8")
    arquivo.setFormatter(fmt)
    arquivo.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    raiz = logging.getLogger()
    raiz.handlers[:] = [arquivo, console]
    raiz.setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.INFO)


def main(argv: list[str] | None = None) -> int:
    # Console do Windows: evita UnicodeEncodeError com acentos.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    a = _args(argv)
    config = carregar(a.config)
    _configurar_log(Path(config["saida"]["logs"]), a.verbose)
    log = logging.getLogger("monitor_ac")

    params = Parametros(
        dias=a.dias, municipio_ibge=a.municipio, somente_me_epp=a.somente_me_epp,
        incluir_federal=a.incluir_federal, salvar_bruto=a.salvar_bruto,
        modalidades=[int(x) for x in a.modalidades.split(",")] if a.modalidades else None)
    descricao = (f"prazo até {a.dias} dia(s)" + (f" · município {a.municipio}" if a.municipio else "")
                 + (" · somente ME/EPP" if a.somente_me_epp else ""))
    log.info("Início da execução: %s", vars(a))

    historico = Historico(config["saida"]["banco"])
    id_exec = historico.iniciar_execucao(vars(a))
    cliente = ClientePNCP(config["api"])
    try:
        res = executar(config, params, cliente, historico)
    except Exception:
        log.exception("Execução interrompida por erro inesperado")
        historico.finalizar_execucao(id_exec, status="erro", falhas=len(cliente.falhas))
        historico.fechar()
        print("Erro inesperado; detalhes em", Path(config["saida"]["logs"]) / "monitor.log")
        return 2

    if res.modalidades_com_falha and not res.encontradas and \
            len(res.modalidades_com_falha) == len(res.por_modalidade):
        historico.finalizar_execucao(id_exec, status="falhou", falhas=res.falhas)
        historico.fechar()
        print("Nenhuma consulta ao PNCP funcionou (API fora do ar ou sem rede). "
              "Relatório anterior mantido. Detalhes em",
              Path(config["saida"]["logs"]) / "monitor.log")
        return 2

    resumo = {"encontradas": res.encontradas, "filtradas": res.filtradas, "me_epp": res.me_epp,
              "exclusivas": res.exclusivas, "novas": res.novas, "falhas": res.falhas,
              "parametros": descricao}
    arquivos = publicar(res.registros, Path(config["saida"]["pasta"]), resumo)
    status = "ok" if not res.falhas else "parcial"
    historico.finalizar_execucao(id_exec, encontradas=res.encontradas, filtradas=res.filtradas,
                                 me_epp=res.me_epp, novas=res.novas, falhas=res.falhas, status=status)
    historico.fechar()

    print(f"Licitações abertas em GO retornadas pela API: {res.encontradas}")
    print(f"  no escopo (esfera/prazo/município):        {res.no_escopo}")
    print(f"  passaram no filtro de ar-condicionado:     {res.filtradas}")
    print(f"  com benefício ME/EPP:                      {res.me_epp} "
          f"(exclusivas: {res.exclusivas})")
    print(f"  no relatório: {len(res.registros)} · novas desde a última execução: {res.novas}")
    print(f"  requisições: {cliente.requisicoes} · falhas: {res.falhas}")
    if res.modalidades_com_falha:
        print(f"  ATENÇÃO: modalidades incompletas: {res.modalidades_com_falha}")
    print(f"CSV:  {arquivos['csv']}")
    print(f"HTML: {arquivos['html']}")
    log.info("Fim da execução: %s", resumo)
    return 0 if status == "ok" else 1
