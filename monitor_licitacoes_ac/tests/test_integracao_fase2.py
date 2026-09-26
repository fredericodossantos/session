"""Fluxos CLI offline, com coleta, SQLite e relatórios reais em diretório temporário."""
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from monitor_ac.api_client import ClientePNCP
from monitor_ac.cli import main
from tests.test_monitor import Resp, SessaoFalsa, contratacao, item


class SessaoParcial(SessaoFalsa):
    def get(self, url, params=None, timeout=None):
        if url.endswith('/proposta') and params['codigoModalidadeContratacao'] == 8:
            self.chamadas.append((url, dict(params)))
            return Resp(503, {'erro': 'falha simulada'}, url)
        return super().get(url, params, timeout)


class TestIntegracaoCLI(unittest.TestCase):
    def rodar(self, pasta, sessao):
        config = pasta / 'config.json'
        config.write_text(json.dumps({
            'filtro': {'termos_inclusao': ['ar condicionado']},
            'api': {'modalidades': [6, 8], 'intervalo_entre_requisicoes': 0,
                    'tentativas': 1, 'backoff_inicial': 0},
            'saida': {'pasta': 'saida', 'banco': 'historico.db', 'logs': 'logs'},
        }), encoding='utf-8')
        def cliente(cfg):
            return ClientePNCP(cfg, sessao=sessao, dormir=lambda _: None)
        with patch('monitor_ac.cli.ClientePNCP', side_effect=cliente), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            codigo = main(['--config', str(config), '--modalidades', '6,8'])
        with contextlib.closing(sqlite3.connect(pasta / 'saida' / 'historico.db')) as con:
            estado, fim = con.execute('SELECT status, fim FROM execucoes ORDER BY id DESC LIMIT 1').fetchone()
        self.assertTrue(fim)
        return codigo, estado

    def test_sucesso_publica_e_registra_execucao(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            registro = contratacao(1, 'Ar condicionado', enc=(datetime.now() + timedelta(days=2)).isoformat())
            codigo, estado = self.rodar(pasta, SessaoFalsa({6: [[registro]]}, {1: [item(1, 1)]}))
            self.assertEqual((codigo, estado), (0, 'ok'))
            self.assertIn('Exclusiva ME/EPP', (pasta / 'saida/ultimo.html').read_text(encoding='utf-8'))
            self.assertTrue((pasta / 'saida/ultimo.csv').read_bytes().startswith(b'\xef\xbb\xbf'))
            self.assertTrue((pasta / 'saida/ultimo.xlsx').read_bytes().startswith(b'PK'))

    def test_falha_total_preserva_ultimos(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            (pasta / 'saida').mkdir()
            for ext in ('html', 'csv', 'xlsx'):
                (pasta / f'saida/ultimo.{ext}').write_text('anterior', encoding='utf-8')
            codigo, estado = self.rodar(pasta, SessaoFalsa({}, {}, falhas_antes=10))
            self.assertEqual(codigo, 2)
            self.assertIn(estado, ('falhou', 'erro'))
            for ext in ('html', 'csv', 'xlsx'):
                self.assertEqual((pasta / f'saida/ultimo.{ext}').read_text(encoding='utf-8'), 'anterior')

    def test_falha_parcial_publica_aviso(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            codigo, estado = self.rodar(pasta, SessaoParcial({}, {}))
            self.assertEqual((codigo, estado), (1, 'parcial'))
            self.assertIn('incompleto', (pasta / 'saida/ultimo.html').read_text(encoding='utf-8'))

    def test_consulta_vazia_e_sucesso(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            codigo, estado = self.rodar(pasta, SessaoFalsa({}, {}))
            self.assertEqual((codigo, estado), (0, 'ok'))
            self.assertIn('Nenhuma licitação', (pasta / 'saida/ultimo.html').read_text(encoding='utf-8'))
