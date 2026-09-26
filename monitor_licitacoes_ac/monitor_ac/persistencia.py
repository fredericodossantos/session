"""Histórico local em SQLite: o que já foi visto e o registro de cada execução."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .filtros import VERSAO_CLASSIFICACAO

ESQUEMA = """
CREATE TABLE IF NOT EXISTS licitacoes (
    numero_controle   TEXT PRIMARY KEY,
    primeira_vez      TEXT NOT NULL,
    ultima_vez        TEXT NOT NULL,
    data_atualizacao  TEXT,
    situacao_me_epp   TEXT,
    contagem_itens    TEXT,
    versao_classificacao INTEGER NOT NULL DEFAULT 1,
    dados             TEXT
);
CREATE TABLE IF NOT EXISTS mudancas_relevantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_controle TEXT NOT NULL,
    quando TEXT NOT NULL,
    campos TEXT NOT NULL,
    dados TEXT
);
CREATE TABLE IF NOT EXISTS execucoes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio            TEXT NOT NULL,
    fim               TEXT,
    parametros        TEXT,
    encontradas       INTEGER,
    filtradas         INTEGER,
    me_epp            INTEGER,
    novas             INTEGER,
    falhas            INTEGER,
    status            TEXT
);
"""


class Historico:
    def __init__(self, caminho: str | Path):
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(caminho))
        self.con.row_factory = sqlite3.Row
        try:
            # executescript executa COMMIT implícito antes do script; iniciar a
            # transação dentro dele mantém criação/migração no mesmo bloco.
            self.con.executescript("BEGIN IMMEDIATE;\n" + ESQUEMA)
            colunas = {r[1] for r in self.con.execute("PRAGMA table_info(licitacoes)")}
            if "versao_classificacao" not in colunas:
                self.con.execute(
                    "ALTER TABLE licitacoes ADD COLUMN versao_classificacao "
                    "INTEGER NOT NULL DEFAULT 1")
            self.con.commit()
        except Exception:
            try:
                self.con.rollback()
            finally:
                self.con.close()
            raise

    def fechar(self) -> None:
        self.con.close()

    # ------------------------------------------------------------ execuções
    def iniciar_execucao(self, parametros: dict[str, Any]) -> int:
        cur = self.con.execute(
            "INSERT INTO execucoes (inicio, parametros, status) VALUES (?, ?, 'em andamento')",
            (_agora(), json.dumps(parametros, ensure_ascii=False, default=str)))
        self.con.commit()
        return int(cur.lastrowid)

    def finalizar_execucao(self, id_exec: int, **totais: Any) -> None:
        self.con.execute(
            "UPDATE execucoes SET fim=?, encontradas=?, filtradas=?, me_epp=?, novas=?, "
            "falhas=?, status=? WHERE id=?",
            (_agora(), totais.get("encontradas"), totais.get("filtradas"), totais.get("me_epp"),
             totais.get("novas"), totais.get("falhas"), totais.get("status", "ok"), id_exec))
        self.con.commit()

    # ----------------------------------------------------------- licitações
    def buscar(self, numero_controle: str) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM licitacoes WHERE numero_controle=?",
                                (numero_controle,)).fetchone()

    def beneficio_em_cache(self, numero_controle: str,
                           data_atualizacao: str | None) -> tuple[str, dict] | None:
        """Reaproveita a classificação ME/EPP se a contratação não mudou desde a última vez."""
        linha = self.buscar(numero_controle)
        if (linha and data_atualizacao and linha["data_atualizacao"] == data_atualizacao
                and linha["situacao_me_epp"] and linha["situacao_me_epp"] != "Não informado"
                and linha["versao_classificacao"] == VERSAO_CLASSIFICACAO):
            try:
                contagem = json.loads(linha["contagem_itens"] or "{}")
            except (TypeError, json.JSONDecodeError):
                return None
            if (isinstance(contagem, dict) and isinstance(contagem.get("itens", 0), int)
                    and contagem.get("itens", 0) > 0 and not contagem.get("sem_info", 0)):
                return linha["situacao_me_epp"], contagem
        return None

    def registrar(self, reg: dict[str, Any]) -> str:
        """Grava/atualiza e devolve 'nova', 'atualizada' ou 'vista'."""
        agora = _agora()
        linha = self.buscar(reg["numero_controle"])
        campos_relevantes = ("objeto", "situacao_me_epp", "data_abertura", "data_encerramento",
                            "valor_estimado", "uf", "esfera", "municipio", "modalidade")
        mudancas = []
        if linha is None:
            estado = "nova"
        elif linha["data_atualizacao"] != reg.get("data_atualizacao"):
            estado = "atualizada"
        else:
            estado = "vista"
        if linha is not None:
            try:
                anterior = json.loads(linha["dados"] or "{}")
            except (TypeError, json.JSONDecodeError):
                anterior = {}
            if not isinstance(anterior, dict):
                anterior = {}
            mudancas = [campo for campo in campos_relevantes
                        if json.dumps(anterior.get(campo), ensure_ascii=False, default=str, sort_keys=True)
                        != json.dumps(reg.get(campo), ensure_ascii=False, default=str, sort_keys=True)]
            if mudancas:
                estado = "atualizada"
        self.con.execute(
            """INSERT INTO licitacoes (numero_controle, primeira_vez, ultima_vez, data_atualizacao,
                                       situacao_me_epp, contagem_itens, versao_classificacao, dados)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(numero_controle) DO UPDATE SET
                   ultima_vez=excluded.ultima_vez,
                   data_atualizacao=excluded.data_atualizacao,
                   situacao_me_epp=excluded.situacao_me_epp,
                   contagem_itens=excluded.contagem_itens,
                   versao_classificacao=excluded.versao_classificacao,
                   dados=excluded.dados""",
            (reg["numero_controle"], agora, agora, reg.get("data_atualizacao"),
             reg.get("situacao_me_epp"), json.dumps(reg.get("contagem_itens") or {}),
             VERSAO_CLASSIFICACAO, json.dumps(reg, ensure_ascii=False, default=str)))
        if mudancas:
            self.con.execute("INSERT INTO mudancas_relevantes (numero_controle, quando, campos, dados) VALUES (?, ?, ?, ?)",
                             (reg["numero_controle"], agora, json.dumps(mudancas),
                              json.dumps(reg, ensure_ascii=False, default=str)))
        self.con.commit()
        return estado


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")
