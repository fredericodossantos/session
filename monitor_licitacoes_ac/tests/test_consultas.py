from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from monitor_ac.consultas import ConsultaOcupada, Consultas


class Relogio:
    def __init__(self, agora=10.0):
        self.agora = agora

    def __call__(self):
        return self.agora

    def avancar(self, segundos):
        self.agora += segundos


class TestConsultas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "historico.sqlite"
        self.clock = Relogio()
        self.consultas = Consultas(self.db, timeout_s=8, max_tentativas=2, monotonic=self.clock)

    def tearDown(self):
        self.tmp.cleanup()

    def test_admissao_exclusiva_callback_e_revisoes(self):
        eventos = []
        primeira = self.consultas.registrar({"areas": ["mecanica"]}, callback=eventos.append)
        segunda = self.consultas.registrar({"areas": ["eletrica"]})
        inicial = self.consultas.admitir(primeira)
        self.assertEqual(inicial["estado"], "executando")
        self.assertEqual(self.consultas.deadline(primeira), 18)
        with self.assertRaises(ConsultaOcupada):
            self.consultas.admitir(segunda)
        atualizado = self.consultas.atualizar(primeira, resultados=[{"id": "x"}], progresso={"pagina": 1})
        self.assertEqual(atualizado["revisao"], 2)
        self.assertEqual(eventos[-1]["resultados"], [{"id": "x"}])
        since = self.consultas.snapshot(primeira, since=1)
        self.assertEqual([e["revisao"] for e in since["atualizacoes"]], [2])
        final = self.consultas.finalizar(primeira)
        self.assertEqual(final["estado"], "concluida")
        self.assertEqual(self.consultas.admitir(segunda)["estado"], "executando")

    def test_cancelamento_limite_de_tentativas_e_prazo_sem_espera_real(self):
        consulta = self.consultas.registrar({})
        self.consultas.admitir(consulta)
        self.assertTrue(self.consultas.registrar_tentativa(consulta))
        self.assertTrue(self.consultas.registrar_tentativa(consulta))
        self.assertFalse(self.consultas.registrar_tentativa(consulta))
        self.assertTrue(self.consultas.deve_interromper(consulta))
        self.assertEqual(self.consultas.finalizar(consulta)["estado"], "tempo_limite")

        segunda = self.consultas.registrar({})
        self.consultas.admitir(segunda)
        self.consultas.request_cancel(segunda)
        self.assertFalse(self.consultas.registrar_tentativa(segunda))
        self.assertEqual(self.consultas.finalizar(segunda)["estado"], "cancelada")

        terceira = self.consultas.registrar({})
        self.consultas.admitir(terceira)
        self.clock.avancar(8)
        self.assertEqual(self.consultas.restante(terceira), 0)
        self.assertTrue(self.consultas.deve_interromper(terceira))
        self.assertEqual(self.consultas.finalizar(terceira)["estado"], "tempo_limite")

    def test_reinicio_marca_consulta_ativa_interrompida_e_preserva_snapshot(self):
        consulta = self.consultas.registrar({"termo": "painel"})
        self.consultas.admitir(consulta)
        self.consultas.atualizar(consulta, resultados=[{"id": "parcial"}])
        reiniciadas = Consultas(self.db, monotonic=self.clock)
        snapshot = reiniciadas.snapshot(consulta)
        self.assertEqual(snapshot["consulta"]["estado"], "interrompida")
        self.assertEqual(snapshot["consulta"]["resultados"], [{"id": "parcial"}])
        self.assertEqual(reiniciadas.deadline(consulta), None)

    def test_isolamento_de_contas_em_snapshot_historico_e_cancelamento(self):
        alice = self.consultas.registrar({"busca": "A"}, owner_id="alice@example.test")
        bob = self.consultas.registrar({"busca": "B"}, owner_id="bob@example.test")
        self.consultas.admitir(alice)

        with self.assertRaises(KeyError):
            self.consultas.snapshot(alice, owner_id="bob@example.test")
        with self.assertRaises(KeyError):
            self.consultas.request_cancel(alice, owner_id="bob@example.test")
        self.assertEqual([row["consulta_id"] for row in self.consultas.historico(owner_id="bob@example.test")],
                         [bob])
        self.assertEqual(self.consultas.historico(owner_id="alice@example.test")[0]["consulta_id"], alice)

        # A disputa continua global, mas a resposta não revela a identidade ou a consulta ocupante.
        with self.assertRaises(ConsultaOcupada) as exc:
            self.consultas.admitir(bob)
        self.assertNotIn(alice, str(exc.exception))
        self.assertNotIn("alice@example.test", str(exc.exception))
        self.assertEqual(self.consultas.snapshot(alice, owner_id="alice@example.test")["consulta"]["estado"],
                         "executando")

    def test_historico_paginado_com_offset_e_total_por_dono(self):
        alice_ids = {self.consultas.registrar({"n": i}, owner_id="alice@example.test") for i in range(5)}
        bob_id = self.consultas.registrar({"n": "bob"}, owner_id="bob@example.test")
        self.assertEqual(self.consultas.total_historico(owner_id="alice@example.test"), 5)
        self.assertEqual(self.consultas.total_historico(owner_id="bob@example.test"), 1)
        pagina1 = self.consultas.historico(limite=2, offset=0, owner_id="alice@example.test")
        pagina2 = self.consultas.historico(limite=2, offset=2, owner_id="alice@example.test")
        pagina3 = self.consultas.historico(limite=2, offset=4, owner_id="alice@example.test")
        self.assertEqual([len(pagina1), len(pagina2), len(pagina3)], [2, 2, 1])
        vistos = {row["consulta_id"] for row in pagina1 + pagina2 + pagina3}
        self.assertEqual(vistos, alice_ids)  # as três páginas cobrem tudo, sem repetição
        self.assertNotIn(bob_id, vistos)  # e nunca vazam o histórico de outro dono

    def test_migracao_aditiva_de_banco_antigo_define_owner_local(self):
        old_db = Path(self.tmp.name) / "legado.sqlite"
        with closing(sqlite3.connect(old_db)) as con:
            con.execute("""CREATE TABLE consultas_web (
                id TEXT PRIMARY KEY, estado TEXT NOT NULL, filtros TEXT NOT NULL,
                snapshot TEXT NOT NULL, revisao INTEGER NOT NULL DEFAULT 0,
                tentativas INTEGER NOT NULL DEFAULT 0, cancelamento INTEGER NOT NULL DEFAULT 0,
                motivo_limite TEXT, inicio TEXT NOT NULL, fim TEXT, atualizada TEXT NOT NULL
            )""")
            snap = {"consulta_id": "legada", "estado": "concluida", "revisao": 0}
            con.execute("INSERT INTO consultas_web VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        ("legada", "concluida", "{}", json.dumps(snap), 0, 0, 0,
                         None, "2026-09-26T00:00:00", None, "2026-09-26T00:00:00"))
            con.commit()
        migrado = Consultas(old_db, monotonic=self.clock)
        self.assertEqual(migrado.snapshot("legada")["consulta"]["estado"], "concluida")
        with closing(sqlite3.connect(old_db)) as con:
            owner = con.execute("SELECT owner_id FROM consultas_web WHERE id='legada'").fetchone()[0]
        self.assertEqual(owner, "local")
