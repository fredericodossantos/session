"""Histórico local em SQLite: o que já foi visto e o registro de cada execução."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

ESQUEMA = """
CREATE TABLE IF NOT EXISTS licitacoes (
    numero_controle   TEXT PRIMARY KEY,
    primeira_vez      TEXT NOT NULL,
    ultima_vez        TEXT NOT NULL,
    data_atualizacao  TEXT,
    situacao_me_epp   TEXT,
    contagem_itens    TEXT,
    dados             TEXT
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
        self.con.executescript(ESQUEMA)

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
        if (linha and linha["situacao_me_epp"] and linha["situacao_me_epp"] != "Não informado"
                and linha["data_atualizacao"] == data_atualizacao):
            return linha["situacao_me_epp"], json.loads(linha["contagem_itens"] or "{}")
        return None

    def registrar(self, reg: dict[str, Any]) -> str:
        """Grava/atualiza e devolve 'nova', 'atualizada' ou 'vista'."""
        agora = _agora()
        linha = self.buscar(reg["numero_controle"])
        if linha is None:
            estado = "nova"
        elif linha["data_atualizacao"] != reg.get("data_atualizacao"):
            estado = "atualizada"
        else:
            estado = "vista"
        self.con.execute(
            """INSERT INTO licitacoes (numero_controle, primeira_vez, ultima_vez, data_atualizacao,
                                       situacao_me_epp, contagem_itens, dados)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(numero_controle) DO UPDATE SET
                   ultima_vez=excluded.ultima_vez,
                   data_atualizacao=excluded.data_atualizacao,
                   situacao_me_epp=excluded.situacao_me_epp,
                   contagem_itens=excluded.contagem_itens,
                   dados=excluded.dados""",
            (reg["numero_controle"], agora, agora, reg.get("data_atualizacao"),
             reg.get("situacao_me_epp"), json.dumps(reg.get("contagem_itens") or {}),
             json.dumps(reg, ensure_ascii=False, default=str)))
        self.con.commit()
        return estado


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")
