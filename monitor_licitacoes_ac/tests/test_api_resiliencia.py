from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime

from monitor_ac.api_client import ClientePNCP, ErroAPI, ErroAPILimite
import requests


class Resposta:
    def __init__(self, status=200, corpo=None, headers=None):
        self.status_code = status
        self.content = b"" if corpo is None else json.dumps(corpo).encode()
        self.text = self.content.decode()
        self.headers = headers or {}
        self.url = "https://api.exemplo.test"
        self._corpo = corpo

    def json(self):
        return self._corpo


class Sessao:
    def __init__(self, respostas):
        self.respostas = iter(respostas)
        self.headers = {}
        self.chamadas = []
        self.fechada = False

    def get(self, url, params=None, timeout=None):
        self.chamadas.append((url, params))
        return next(self.respostas)

    def close(self):
        self.fechada = True


class TestResilienciaAPI(unittest.TestCase):
    def cliente(self, sessao, **cfg):
        base = {"base_consulta": "https://api.exemplo.test", "base_pncp": "https://api.exemplo.test",
                "intervalo_entre_requisicoes": 0, "tentativas": 2, "backoff_inicial": 0}
        base.update(cfg)
        esperas = []
        return ClientePNCP(base, sessao=sessao, dormir=esperas.append), esperas

    def test_formato_de_pagina_invalido_registra_falha(self):
        cli, _ = self.cliente(Sessao([Resposta(corpo={"data": {"x": 1}})]))
        with self.assertRaises(ErroAPI):
            list(cli.contratacoes_proposta(date.today(), 6))
        self.assertEqual(len(cli.falhas), 1)

    def test_detecta_pagina_repetida(self):
        registro = {"numeroControlePNCP": "x"}
        sessao = Sessao([Resposta(corpo={"data": [registro], "paginasRestantes": 2}),
                         Resposta(corpo={"data": [registro], "paginasRestantes": 1})])
        cli, _ = self.cliente(sessao)
        gen = cli.contratacoes_proposta(date.today(), 6)
        self.assertEqual(next(gen), registro)
        with self.assertRaises(ErroAPI):
            next(gen)

    def test_limite_de_paginas_finito(self):
        registro = {"id": 1}
        sessao = Sessao([Resposta(corpo={"data": [registro], "paginasRestantes": 2}),
                         Resposta(corpo={"data": [{"id": 2}], "paginasRestantes": 1})])
        cli, _ = self.cliente(sessao, max_paginas=1)
        with self.assertRaises(ErroAPI):
            list(cli.contratacoes_proposta(date.today(), 6))
        self.assertEqual(len(sessao.chamadas), 1)

    def test_retry_after_http_date(self):
        futuro = datetime.now(timezone.utc) + timedelta(seconds=30)
        sessao = Sessao([Resposta(429, {"erro": "limite"}, {"Retry-After": format_datetime(futuro, usegmt=True)}),
                         Resposta(204)])
        cli, esperas = self.cliente(sessao)
        with self.assertRaisesRegex(ErroAPILimite, r"aguarde \d+s"):
            cli.get_json("https://api.exemplo.test")
        self.assertEqual(esperas, [])
        self.assertEqual(len(sessao.chamadas), 1)

    def test_204_e_valido_e_sessao_injetada_nao_fecha(self):
        sessao = Sessao([Resposta(204)])
        cli, _ = self.cliente(sessao)
        self.assertEqual(list(cli.contratacoes_proposta(date.today(), 6)), [])
        cli.close()
        self.assertFalse(sessao.fechada)

    def test_http_200_vazio_nao_e_vazio_valido(self):
        cli, _ = self.cliente(Sessao([Resposta(200), Resposta(200)]))
        with self.assertRaises(ErroAPI):
            cli.get_json("https://api.exemplo.test")

    def test_itens_malformados_geram_erro(self):
        cli, _ = self.cliente(Sessao([Resposta(corpo={"data": "inválido"})]))
        with self.assertRaises(ErroAPI):
            cli.itens_contratacao("123", 2026, 1)

    def test_itens_pagina_curta_com_restantes_nao_trunca_classificacao(self):
        exclusiva = {"numeroItem": 1, "tipoBeneficio": 1}
        ampla = {"numeroItem": 2, "tipoBeneficio": 4}
        sessao = Sessao([Resposta(corpo={"data": [exclusiva], "numeroPagina": 1,
                                         "totalPaginas": 2, "paginasRestantes": 1}),
                         Resposta(corpo={"data": [ampla], "numeroPagina": 2,
                                         "totalPaginas": 2, "paginasRestantes": 0})])
        cli, _ = self.cliente(sessao, tamanho_pagina_itens=2)
        self.assertEqual(cli.itens_contratacao("123", 2026, 1), [exclusiva, ampla])

    def test_metadados_invalidos_rejeitados(self):
        for metadata in ({"paginasRestantes": True}, {"totalPaginas": 2.0},
                         {"paginasRestantes": -1}, {"numeroPagina": 2}):
            with self.subTest(metadata=metadata):
                corpo = {"data": [{"id": 1}], "totalPaginas": 1, "paginasRestantes": 0,
                         "numeroPagina": 1}
                corpo.update(metadata)
                cli, _ = self.cliente(Sessao([Resposta(corpo=corpo)]))
                with self.assertRaises(ErroAPI):
                    list(cli.contratacoes_proposta(date.today(), 6))

    def test_pagina_cheia_sem_metadados_e_invalida(self):
        cli, _ = self.cliente(Sessao([Resposta(corpo={"data": [{"id": 1}]})]))
        with self.assertRaises(ErroAPI):
            list(cli.contratacoes_proposta(date.today(), 6))

    def test_pagina_vazia_com_metadados_inconsistentes_e_rejeitada(self):
        casos = (
            {"numeroPagina": 1, "totalPaginas": 2, "paginasRestantes": 1, "totalRegistros": 0},
            {"numeroPagina": 1, "totalPaginas": 1, "paginasRestantes": 0, "totalRegistros": 4},
            {"numeroPagina": 2, "totalPaginas": 1, "paginasRestantes": 0, "totalRegistros": 0},
        )
        for metadados in casos:
            with self.subTest(metadados=metadados):
                cli, _ = self.cliente(Sessao([Resposta(corpo={"data": [], **metadados})]))
                with self.assertRaises(ErroAPI):
                    list(cli.contratacoes_proposta(date.today(), 6))
                cli, _ = self.cliente(Sessao([Resposta(corpo={"data": [], **metadados})]))
                with self.assertRaises(ErroAPI):
                    cli.itens_contratacao("123", 2026, 1)

    def test_retry_after_excessivo_aborta_sem_retry_prematuro(self):
        sessao = Sessao([Resposta(503, {"erro": "temporário"}, {"Retry-After": "3600"})])
        cli, _ = self.cliente(sessao)
        with self.assertRaisesRegex(ErroAPI, "excede limite"):
            cli.get_json("https://api.exemplo.test")
        self.assertEqual(len(sessao.chamadas), 1)

    def test_http_4xx_nao_repete(self):
        sessao = Sessao([Resposta(400, {"erro": "requisição inválida"})])
        cli, _ = self.cliente(sessao)
        with self.assertRaises(ErroAPI):
            cli.get_json("https://api.exemplo.test")
        self.assertEqual(len(sessao.chamadas), 1)

    def test_exaustao_5xx_e_rede_registra_erro(self):
        for respostas in ([Resposta(503), Resposta(503)],
                          [requests.ConnectionError("offline"), requests.Timeout("lento")]):
            class SessaoFalha(Sessao):
                def get(self, url, params=None, timeout=None):
                    self.chamadas.append((url, params))
                    resultado = next(self.respostas)
                    if isinstance(resultado, Exception):
                        raise resultado
                    return resultado
            sessao = SessaoFalha(respostas)
            cli, _ = self.cliente(sessao)
            with self.subTest(respostas=respostas), self.assertRaises(ErroAPI):
                cli.get_json("https://api.exemplo.test")
            self.assertEqual(len(sessao.chamadas), 2)
            self.assertEqual(len(cli.falhas), 1)

    def test_json_invalido_gera_erro_apos_retries(self):
        class JsonRuim(Resposta):
            def __init__(self):
                super().__init__(200, {"ok": True})
                self.content = b"{"
                self.text = "{"

            def json(self):
                raise ValueError("invalid json")
        sessao = Sessao([JsonRuim(), JsonRuim()])
        cli, _ = self.cliente(sessao)
        with self.assertRaises(ErroAPI):
            cli.get_json("https://api.exemplo.test")
        self.assertEqual(len(sessao.chamadas), 2)

    def test_itens_repetidos_sao_rejeitados(self):
        lote = [{"id": 1}, {"id": 2}]
        sessao = Sessao([Resposta(corpo={"data": lote, "numeroPagina": 1,
                                         "totalPaginas": 3, "paginasRestantes": 2}),
                         Resposta(corpo={"data": lote, "numeroPagina": 2,
                                         "totalPaginas": 3, "paginasRestantes": 1})])
        cli, _ = self.cliente(sessao, tamanho_pagina_itens=2)
        with self.assertRaises(ErroAPI):
            cli.itens_contratacao("123", 2026, 1)


if __name__ == "__main__":
    unittest.main()
