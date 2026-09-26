"""Ciclo de vida durável das consultas PNCP da aplicação web.

O módulo é independente do servidor HTTP para que este possa fornecer as
funções do worker sem criar dependência circular.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ESTADOS_TERMINAIS = {"concluida", "parcial", "cancelada", "tempo_limite", "falha", "interrompida"}
ESTADOS_ATIVOS = {"aguardando", "executando"}


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str, sort_keys=True)


class ConsultaError(RuntimeError):
    """Erro de estado ou entrada no gerenciador de consultas."""


class ConsultaOcupada(ConsultaError):
    """Já existe uma execução PNCP ativa."""


class Consultas:
    """Registra consultas e fornece admissão exclusiva, snapshots e limites.

    `caminho_db` pode apontar para o SQLite legado. Tabelas novas são isoladas
    em `consultas_web` e `consultas_eventos`; persistencia.Historico não precisa
    ser alterado. Ao construir o gerenciador, execuções que ficaram ativas no
    processo anterior são marcadas como interrompidas, sem retomada externa.
    """

    def __init__(self, caminho_db: str | Path, *, timeout_s: float = 120,
                 max_tentativas: int = 60, monotonic: Callable[[], float] = time.monotonic):
        self.caminho_db = str(caminho_db)
        Path(self.caminho_db).parent.mkdir(parents=True, exist_ok=True)
        self.timeout_s = float(timeout_s)
        self.max_tentativas = int(max_tentativas)
        if self.timeout_s <= 0 or self.max_tentativas <= 0:
            raise ValueError("timeout_s e max_tentativas devem ser positivos")
        self._monotonic = monotonic
        self._lock = threading.RLock()
        self._runtime: dict[str, dict[str, Any]] = {}
        with self._db() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS consultas_web (
                    id TEXT PRIMARY KEY, estado TEXT NOT NULL, filtros TEXT NOT NULL,
                    snapshot TEXT NOT NULL, revisao INTEGER NOT NULL DEFAULT 0,
                    tentativas INTEGER NOT NULL DEFAULT 0, cancelamento INTEGER NOT NULL DEFAULT 0,
                    motivo_limite TEXT, inicio TEXT NOT NULL, fim TEXT, atualizada TEXT NOT NULL,
                    owner_id TEXT NOT NULL DEFAULT 'local'
                );
                CREATE TABLE IF NOT EXISTS consultas_eventos (
                    consulta_id TEXT NOT NULL, revisao INTEGER NOT NULL,
                    criado TEXT NOT NULL, snapshot TEXT NOT NULL,
                    PRIMARY KEY (consulta_id, revisao),
                    FOREIGN KEY (consulta_id) REFERENCES consultas_web(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_consultas_web_estado ON consultas_web(estado);
            """)
            # Migração aditiva para bancos criados antes do isolamento por usuário.
            colunas = {row[1] for row in con.execute("PRAGMA table_info(consultas_web)")}
            if "owner_id" not in colunas:
                con.execute("ALTER TABLE consultas_web ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local'")
            con.execute("CREATE INDEX IF NOT EXISTS ix_consultas_web_owner_inicio "
                        "ON consultas_web(owner_id, inicio DESC)")
            for row in con.execute("SELECT id,snapshot,revisao FROM consultas_web "
                                   "WHERE estado IN ('aguardando','executando')").fetchall():
                fim = _agora()
                snapshot = json.loads(row["snapshot"])
                revision = row["revisao"] + 1
                snapshot.update(estado="interrompida", revisao=revision, fim=fim)
                con.execute("UPDATE consultas_web SET estado='interrompida', revisao=?, snapshot=?, fim=?, atualizada=? WHERE id=?",
                            (revision, _json(snapshot), fim, fim, row["id"]))
                con.execute("INSERT INTO consultas_eventos VALUES (?, ?, ?, ?)",
                            (row["id"], revision, fim, _json(snapshot)))

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.caminho_db, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    @contextmanager
    def _db(self):
        con = self._connect()
        try:
            with con:
                yield con
        finally:
            con.close()

    def registrar(self, filtros: dict[str, Any], *, callback: Callable[[dict[str, Any]], None] | None = None,
                  catalogo_versao: str | None = None, owner_id: str = "local") -> str:
        """Cria um ID estável com estado aguardando; não inicia uma thread."""
        if not isinstance(filtros, dict):
            raise ValueError("filtros deve ser um objeto")
        owner_id = self._validar_owner(owner_id)
        consulta_id = str(uuid.uuid4())
        agora = _agora()
        snapshot = {"consulta_id": consulta_id, "estado": "aguardando", "revisao": 0,
                    "filtros": filtros, "catalogo_versao": catalogo_versao,
                    "inicio": agora, "fim": None, "tentativas": 0,
                    "resultados": [], "falhas": [], "progresso": {}}
        with self._lock, self._db() as con:
            con.execute("INSERT INTO consultas_web (id, estado, filtros, snapshot, inicio, atualizada, owner_id) "
                        "VALUES (?, 'aguardando', ?, ?, ?, ?, ?)",
                        (consulta_id, _json(filtros), _json(snapshot), agora, agora, owner_id))
            self._runtime[consulta_id] = {"callback": callback, "deadline": None}
        return consulta_id

    def admitir(self, consulta_id: str) -> dict[str, Any]:
        """Admite uma única execução e inicia seu prazo monotônico."""
        with self._lock, self._db() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM consultas_web WHERE id=?", (consulta_id,)).fetchone()
            if row is None:
                raise KeyError(consulta_id)
            if row["estado"] != "aguardando":
                raise ConsultaError(f"consulta não pode ser admitida no estado {row['estado']}")
            ocupada = con.execute("SELECT id FROM consultas_web WHERE estado='executando' LIMIT 1").fetchone()
            if ocupada:
                raise ConsultaOcupada("já existe uma consulta em execução")
            inicio = _agora()
            snapshot = json.loads(row["snapshot"])
            snapshot.update(estado="executando", inicio_execucao=inicio)
            snapshot["revisao"] = row["revisao"] + 1
            deadline = self._monotonic() + self.timeout_s
            con.execute("UPDATE consultas_web SET estado='executando', revisao=?, snapshot=?, atualizada=? WHERE id=?",
                        (snapshot["revisao"], _json(snapshot), inicio, consulta_id))
            con.execute("INSERT INTO consultas_eventos VALUES (?, ?, ?, ?)",
                        (consulta_id, snapshot["revisao"], inicio, _json(snapshot)))
            runtime = self._runtime.setdefault(consulta_id, {"callback": None})
            runtime["deadline"] = deadline
        self._notificar(consulta_id, snapshot)
        return snapshot

    def atualizar(self, consulta_id: str, *, snapshot: dict[str, Any] | None = None,
                  callback: Callable[[dict[str, Any]], None] | None = None, **campos: Any) -> dict[str, Any]:
        """Publica uma revisão persistida; campos mesclam sobre o snapshot atual."""
        with self._lock, self._db() as con:
            row = con.execute("SELECT * FROM consultas_web WHERE id=?", (consulta_id,)).fetchone()
            if row is None:
                raise KeyError(consulta_id)
            if row["estado"] not in ESTADOS_ATIVOS:
                raise ConsultaError("consulta já finalizada")
            atual = json.loads(row["snapshot"])
            if snapshot is not None:
                if not isinstance(snapshot, dict):
                    raise ValueError("snapshot deve ser um objeto")
                atual.update(snapshot)
            atual.update(campos)
            revisao = row["revisao"] + 1
            atual.update(consulta_id=consulta_id, estado=row["estado"], revisao=revisao)
            agora = _agora()
            con.execute("UPDATE consultas_web SET revisao=?, snapshot=?, atualizada=? WHERE id=?",
                        (revisao, _json(atual), agora, consulta_id))
            con.execute("INSERT INTO consultas_eventos VALUES (?, ?, ?, ?)",
                        (consulta_id, revisao, agora, _json(atual)))
            if callback is not None:
                self._runtime.setdefault(consulta_id, {})["callback"] = callback
        self._notificar(consulta_id, atual)
        return atual

    def snapshot(self, consulta_id: str, since: int | None = None, *,
                 owner_id: str = "local") -> dict[str, Any]:
        """Retorna revisão atual e eventos posteriores a `since` (cursor inclusivo)."""
        owner_id = self._validar_owner(owner_id)
        with self._db() as con:
            row = con.execute("SELECT snapshot, revisao FROM consultas_web WHERE id=? AND owner_id=?",
                              (consulta_id, owner_id)).fetchone()
            if row is None:
                raise KeyError(consulta_id)
            atual = json.loads(row["snapshot"])
            if since is None:
                return {"consulta": atual, "revisao": row["revisao"], "atualizacoes": []}
            eventos = con.execute("SELECT revisao, snapshot FROM consultas_eventos "
                                  "WHERE consulta_id=? AND revisao>? ORDER BY revisao", (consulta_id, int(since)))
            return {"consulta": atual, "revisao": row["revisao"],
                    "atualizacoes": [{"revisao": r["revisao"], "snapshot": json.loads(r["snapshot"])}
                                     for r in eventos]}

    def historico(self, limite: int = 50, *, owner_id: str = "local") -> list[dict[str, Any]]:
        """Lista snapshots recentes para tela de histórico/retomada após reload."""
        limite = max(1, min(500, int(limite)))
        owner_id = self._validar_owner(owner_id)
        with self._db() as con:
            rows = con.execute("SELECT snapshot FROM consultas_web WHERE owner_id=? "
                               "ORDER BY inicio DESC LIMIT ?", (owner_id, limite))
            return [json.loads(row["snapshot"]) for row in rows]

    def request_cancel(self, consulta_id: str, *, owner_id: str = "local") -> dict[str, Any]:
        """Solicita cancelamento cooperativo, idempotente e sem matar a thread."""
        owner_id = self._validar_owner(owner_id)
        with self._lock, self._db() as con:
            row = con.execute("SELECT * FROM consultas_web WHERE id=? AND owner_id=?",
                              (consulta_id, owner_id)).fetchone()
            if row is None:
                raise KeyError(consulta_id)
            if row["estado"] == "aguardando":
                con.execute("UPDATE consultas_web SET estado='cancelada', cancelamento=1, fim=?, atualizada=? WHERE id=?",
                            (_agora(), _agora(), consulta_id))
                atual = json.loads(row["snapshot"])
                revisao = row["revisao"] + 1
                atual.update(estado="cancelada", revisao=revisao, fim=_agora(), cancelamento_solicitado=True)
                con.execute("UPDATE consultas_web SET revisao=?, snapshot=? WHERE id=?", (revisao, _json(atual), consulta_id))
                con.execute("INSERT INTO consultas_eventos VALUES (?, ?, ?, ?)", (consulta_id, revisao, _agora(), _json(atual)))
            elif row["estado"] == "executando":
                con.execute("UPDATE consultas_web SET cancelamento=1, atualizada=? WHERE id=?", (_agora(), consulta_id))
                atual = json.loads(row["snapshot"])
                atual["cancelamento_solicitado"] = True
                revisao = row["revisao"] + 1
                atual["revisao"] = revisao
                con.execute("UPDATE consultas_web SET revisao=?, snapshot=? WHERE id=?", (revisao, _json(atual), consulta_id))
                con.execute("INSERT INTO consultas_eventos VALUES (?, ?, ?, ?)", (consulta_id, revisao, _agora(), _json(atual)))
            else:
                atual = json.loads(row["snapshot"])
        self._notificar(consulta_id, atual)
        return atual

    def deadline(self, consulta_id: str) -> float | None:
        with self._lock:
            return self._runtime.get(consulta_id, {}).get("deadline")

    def restante(self, consulta_id: str) -> float:
        fim = self.deadline(consulta_id)
        return max(0.0, fim - self._monotonic()) if fim is not None else 0.0

    def registrar_tentativa(self, consulta_id: str) -> bool:
        """Conta uma tentativa HTTP apenas se ainda couber no orçamento."""
        with self._lock, self._db() as con:
            row = con.execute("SELECT * FROM consultas_web WHERE id=?", (consulta_id,)).fetchone()
            if row is None:
                raise KeyError(consulta_id)
            if row["estado"] != "executando" or row["cancelamento"] or self.restante(consulta_id) <= 0:
                return False
            if row["tentativas"] >= self.max_tentativas:
                con.execute("UPDATE consultas_web SET motivo_limite='tentativas' WHERE id=?", (consulta_id,))
                return False
            n = row["tentativas"] + 1
            snapshot = json.loads(row["snapshot"])
            revision = row["revisao"] + 1
            snapshot.update(tentativas=n, revisao=revision)
            agora = _agora()
            con.execute("UPDATE consultas_web SET tentativas=?, revisao=?, snapshot=?, atualizada=? WHERE id=?",
                        (n, revision, _json(snapshot), agora, consulta_id))
            con.execute("INSERT INTO consultas_eventos VALUES (?, ?, ?, ?)",
                        (consulta_id, revision, agora, _json(snapshot)))
        self._notificar(consulta_id, snapshot)
        return True

    def deve_interromper(self, consulta_id: str) -> bool:
        with self._db() as con:
            row = con.execute("SELECT estado,cancelamento,tentativas,motivo_limite FROM consultas_web WHERE id=?",
                              (consulta_id,)).fetchone()
            if row is None:
                raise KeyError(consulta_id)
            if row["estado"] != "executando" or row["cancelamento"] or row["motivo_limite"]:
                return True
            if self.restante(consulta_id) <= 0:
                with con:
                    con.execute("UPDATE consultas_web SET motivo_limite='tempo' WHERE id=?", (consulta_id,))
                return True
            return row["tentativas"] >= self.max_tentativas

    def finalizar(self, consulta_id: str, estado: str = "concluida", *, falhas: list[Any] | None = None) -> dict[str, Any]:
        """Finaliza explicitamente; cancelamento/prazo/orçamento prevalecem."""
        permitidos = ESTADOS_TERMINAIS - {"interrompida"}
        if estado not in permitidos:
            raise ValueError(f"estado terminal inválido: {estado}")
        with self._lock, self._db() as con:
            row = con.execute("SELECT * FROM consultas_web WHERE id=?", (consulta_id,)).fetchone()
            if row is None:
                raise KeyError(consulta_id)
            if row["estado"] in ESTADOS_TERMINAIS:
                return json.loads(row["snapshot"])
            final = estado
            if row["cancelamento"]:
                final = "cancelada"
            elif row["motivo_limite"] == "tentativas" or row["tentativas"] >= self.max_tentativas:
                final = "tempo_limite"
            elif row["motivo_limite"] == "tempo" or (self.deadline(consulta_id) is not None and self.restante(consulta_id) <= 0):
                final = "tempo_limite"
            atual = json.loads(row["snapshot"])
            revisao = row["revisao"] + 1
            fim = _agora()
            atual.update(estado=final, revisao=revisao, fim=fim, tentativas=row["tentativas"])
            if falhas is not None:
                atual["falhas"] = falhas
            con.execute("UPDATE consultas_web SET estado=?, revisao=?, snapshot=?, fim=?, atualizada=? WHERE id=?",
                        (final, revisao, _json(atual), fim, fim, consulta_id))
            con.execute("INSERT INTO consultas_eventos VALUES (?, ?, ?, ?)", (consulta_id, revisao, fim, _json(atual)))
        self._notificar(consulta_id, atual)
        return atual

    def _notificar(self, consulta_id: str, snapshot: dict[str, Any]) -> None:
        with self._lock:
            cb = self._runtime.get(consulta_id, {}).get("callback")
        if cb:
            cb(dict(snapshot))

    @staticmethod
    def _validar_owner(owner_id: str) -> str:
        if not isinstance(owner_id, str) or not owner_id.strip():
            raise ValueError("owner_id deve ser uma identidade não vazia")
        return owner_id
