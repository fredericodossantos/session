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
from .catalogo import ErroCatalogo, carregar_catalogo
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
                   help="mostrar só licitações com benefício ME/EPP (exclusiva, cota, parcial ou subcontratação)")
    p.add_argument("--incluir-federal", action="store_true",
                   help="incluir órgãos federais sediados em Goiás")
    p.add_argument("--modalidades", help="lista de códigos separada por vírgula (sobrepõe o config)")
    p.add_argument("--todas-modalidades", action="store_true",
                   help="autoriza explicitamente consultar todas as modalidades do config")
    p.add_argument("--setores", help="IDs de setores do catálogo separados por vírgula (ativa filtros v2)")
    p.add_argument("--servicos", help="IDs de serviços do catálogo separados por vírgula")
    p.add_argument("--contextos", help="IDs de contextos do catálogo separados por vírgula")
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
    if a.modalidades:
        try:
            codigos = [int(x.strip()) for x in a.modalidades.split(",")]
        except ValueError:
            p.error("--modalidades deve ser uma lista de códigos inteiros separados por vírgula")
        if not codigos or any(x <= 0 for x in codigos) or len(set(codigos)) != len(codigos):
            p.error("--modalidades deve conter códigos positivos, únicos e separados por vírgula")
    return a


def _configurar_log(pasta: Path, verbose: bool) -> tuple[list[logging.Handler], int, list[logging.Handler]]:
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
    anteriores = list(raiz.handlers)
    nivel_anterior = raiz.level
    raiz.handlers[:] = [arquivo, console]
    raiz.setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    return anteriores, nivel_anterior, [arquivo, console]


def main(argv: list[str] | None = None) -> int:
    # Console do Windows: evita UnicodeEncodeError com acentos.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    a = _args(argv)
    try:
        config = carregar(a.config)
        catalogo = None
        if a.setores is not None or a.servicos is not None or a.contextos is not None:
            catalogo_path = config.get("catalogo_areas")
            if catalogo_path:
                caminho_catalogo = Path(catalogo_path)
                if not caminho_catalogo.is_absolute():
                    caminho_catalogo = Path(a.config).resolve().parent / caminho_catalogo
            else:
                caminho_catalogo = Path(a.config).resolve().parent / "catalogo_areas.yaml"
            catalogo = carregar_catalogo(caminho_catalogo)
        handlers_log = _configurar_log(Path(config["saida"]["logs"]), a.verbose)
    except (OSError, ValueError, ErroCatalogo) as exc:
        print(f"Configuração inválida ou indisponível: {exc}", file=sys.stderr)
        return 2
    def ids_csv(valor: str | None, dimensao: str) -> list[str] | None:
        if valor is None:
            return None
        ids = [x.strip() for x in valor.split(",") if x.strip()]
        try:
            if catalogo is None:
                raise ErroCatalogo("Catálogo não carregado")
            return catalogo.validar_ids(dimensao, ids, permitir_vazio=False)
        except ErroCatalogo as exc:
            raise ErroCatalogo(f"{exc}") from exc
    try:
        setores = ids_csv(a.setores, "setores")
        servicos = ids_csv(a.servicos, "servicos") or []
        contextos = ids_csv(a.contextos, "contextos") or []
        if (servicos or contextos) and setores is None:
            raise ErroCatalogo("--servicos e --contextos exigem --setores")
    except ErroCatalogo as exc:
        print(f"Argumento inválido: {exc}", file=sys.stderr)
        return 2
    if not a.modalidades and not a.todas_modalidades:
        print("Nenhuma modalidade selecionada. Use a interface com 'web.bat' ou informe "
              "--modalidades 6,8. Para todas, use --todas-modalidades.", file=sys.stderr)
        return 2
    log = logging.getLogger("monitor_ac")

    params = Parametros(
        dias=a.dias, municipio_ibge=a.municipio, somente_me_epp=a.somente_me_epp,
        incluir_federal=a.incluir_federal, salvar_bruto=a.salvar_bruto,
        modalidades=[int(x.strip()) for x in a.modalidades.split(",")] if a.modalidades else None,
        setores=setores, servicos=servicos, contextos=contextos,
        catalogo=catalogo if setores is not None else None)
    descricao = (f"prazo até {a.dias} dia(s)" + (f" · município {a.municipio}" if a.municipio else "")
                 + (" · somente ME/EPP" if a.somente_me_epp else ""))
    log.info("Início da execução: %s", vars(a))

    historico = None
    cliente = None
    id_exec = None
    res = None
    try:
        historico = Historico(config["saida"]["banco"])
        id_exec = historico.iniciar_execucao(vars(a))
        cliente = ClientePNCP(config["api"])
        res = executar(config, params, cliente, historico)
        if res.modalidades_com_falha and not res.encontradas and \
                len(res.modalidades_com_falha) == len(res.por_modalidade):
            historico.finalizar_execucao(id_exec, status="falhou", falhas=res.falhas)
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

        print(f"Licitações abertas em GO retornadas pela API: {res.encontradas}")
        print(f"  no escopo (esfera/prazo/município):        {res.no_escopo}")
        print(f"  passaram no filtro técnico:                 {res.filtradas}")
        print(f"  com benefício ME/EPP:                      {res.me_epp} "
              f"(exclusivas: {res.exclusivas})")
        print(f"  no relatório: {len(res.registros)} · novas desde a última execução: {res.novas}")
        print(f"  requisições: {cliente.requisicoes} · falhas: {res.falhas}")
        if res.modalidades_com_falha:
            print(f"  ATENÇÃO: modalidades incompletas: {res.modalidades_com_falha}")
        print(f"CSV:  {arquivos['csv']}")
        print(f"HTML: {arquivos['html']}")
        print(f"XLSX: {arquivos['xlsx']}")
        log.info("Fim da execução: %s", resumo)
        return 0 if status == "ok" else 1
    except Exception as exc:
        log.exception("Execução interrompida por erro operacional")
        if historico is not None and id_exec is not None:
            try:
                historico.finalizar_execucao(id_exec, status="erro",
                                             falhas=len(cliente.falhas) if cliente else 0)
            except Exception:
                log.exception("Não foi possível registrar a falha no histórico")
        print(f"Erro operacional: {exc}. Detalhes em {Path(config['saida']['logs']) / 'monitor.log'}",
              file=sys.stderr)
        return 2
    finally:
        if cliente is not None:
            fechar = getattr(cliente, "close", None)
            if callable(fechar):
                try:
                    fechar()
                except Exception:
                    log.exception("Erro ao fechar a sessão HTTP")
        if historico is not None:
            try:
                historico.fechar()
            except Exception:
                log.exception("Erro ao fechar o histórico SQLite")
        if "handlers_log" in locals():
            anteriores, nivel_anterior, proprios = handlers_log
            raiz = logging.getLogger()
            raiz.handlers[:] = anteriores
            raiz.setLevel(nivel_anterior)
            for handler in proprios:
                try:
                    handler.close()
                except Exception:
                    pass
