from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
import tempfile
import time

import requests

from monitor_ac.api_client import ClientePNCP, ErroAPI, ErroAPIInterrompida, ErroAPILimite
from monitor_ac.coleta import Parametros, executar
from monitor_ac.config import carregar
from monitor_ac.persistencia import Historico


class FalhaTransporte:
    def __init__(self):
        self.headers = {}
        self.chamadas = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append({"url": url, "timeout": timeout})
        raise requests.ConnectionError("falha simulada")


class WaitCancelavel:
    def __init__(self):
        self.cancelado = False
        self.esperas = []

    def is_set(self):
        return self.cancelado

    def wait(self, segundos):
        self.esperas.append(segundos)
        self.cancelado = True
        return True


class RespostaJSON:
    def __init__(self, corpo, status=200):
        self.status_code = status
        self.headers = {}
        self.url = "https://exemplo.invalid"
        self.text = ""
        self._corpo = corpo

    def json(self):
        return self._corpo


class TestLimitesClienteFase3(unittest.TestCase):
    def test_config_yaml_antigo_com_repetir_429_e_ignorado_com_aviso(self):
        # AC17: a opção nunca teve efeito (o cliente HTTP não a lia) e foi removida;
        # um config.yaml antigo que ainda a declare deve apenas gerar um aviso.
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "config.yaml"
            caminho.write_text(
                "filtro:\n  termos_inclusao: [climatizacao]\n"
                "api:\n  repetir_429: true\n"
                f"saida:\n  pasta: '{(Path(tmp) / 'saida').as_posix()}'\n",
                encoding="utf-8",
            )
            with self.assertLogs(level="WARNING") as captura:
                config = carregar(caminho)
            self.assertNotIn("repetir_429", config["api"])
            self.assertTrue(any("repetir_429" in mensagem for mensagem in captura.output))

    def test_config_yaml_antigo_com_filtro_campos_e_ignorado_com_aviso(self):
        # A classificação sempre usou somente o objeto da contratação; 'filtro.campos'
        # nunca escolhia outros campos e foi removida. Um config.yaml antigo que ainda a
        # declare deve apenas gerar um aviso, sem quebrar o carregamento.
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "config.yaml"
            caminho.write_text(
                "filtro:\n  termos_inclusao: [climatizacao]\n"
                "  campos: [objetoCompra, informacaoComplementar]\n"
                f"saida:\n  pasta: '{(Path(tmp) / 'saida').as_posix()}'\n",
                encoding="utf-8",
            )
            with self.assertLogs(level="WARNING") as captura:
                config = carregar(caminho)
            self.assertNotIn("campos", config["filtro"])
            self.assertTrue(any("filtro.campos" in mensagem for mensagem in captura.output))

    def test_429_interrompe_execucao_sem_retry_e_explica_retry_after(self):
        class Resposta429:
            status_code = 429
            headers = {"Retry-After": "45"}
            url = "https://exemplo.invalid"
            text = "rate limit"

        class Transporte:
            headers = {}

            def __init__(self):
                self.chamadas = 0

            def get(self, url, params=None, timeout=None):
                self.chamadas += 1
                return Resposta429()

        transporte = Transporte()
        esperas = []
        # AC17: 429 nunca tem retry oculto; "repetir_429" foi removida da configuração
        # (não era lida pelo cliente HTTP) e não precisa mais aparecer aqui.
        cliente = ClientePNCP({"tentativas": 5,
                               "intervalo_entre_requisicoes": 0}, sessao=transporte,
                              dormir=esperas.append)
        with self.assertRaisesRegex(ErroAPILimite, "aguarde 45s"):
            cliente.get_json("https://exemplo.invalid")
        self.assertEqual(transporte.chamadas, 1)
        self.assertEqual(esperas, [])
        self.assertEqual(len(cliente.falhas), 1)

    def test_retry_after_bloqueia_nova_coleta_ate_cooldown(self):
        agora = [5.0]

        class Resposta429:
            status_code = 429
            headers = {"Retry-After": "45"}
            url = "https://exemplo.invalid"
            text = "rate limit"

        class Resposta204:
            status_code = 204
            headers = {}
            url = "https://exemplo.invalid"

        class Transporte:
            headers = {}

            def __init__(self, resposta):
                self.resposta = resposta
                self.chamadas = 0

            def get(self, url, params=None, timeout=None):
                self.chamadas += 1
                return self.resposta

        config = {"tentativas": 5, "intervalo_entre_requisicoes": 0}
        primeira = Transporte(Resposta429())
        with self.assertRaises(ErroAPILimite):
            ClientePNCP(config, sessao=primeira, monotonic=lambda: agora[0]).get_json(
                "https://exemplo.invalid")
        segunda = Transporte(Resposta204())
        cliente_nova = ClientePNCP(config, sessao=segunda, monotonic=lambda: agora[0])
        with self.assertRaises(ErroAPILimite):
            cliente_nova.get_json("https://exemplo.invalid")
        self.assertEqual(segunda.chamadas, 0)
        agora[0] += 46
        self.assertIsNone(cliente_nova.get_json("https://exemplo.invalid"))
        self.assertEqual(segunda.chamadas, 1)

    def test_limite_local_de_tentativas_e_exato(self):
        transporte = FalhaTransporte()
        reservadas = []
        cliente = ClientePNCP({"tentativas": 5, "backoff_inicial": 0,
                               "intervalo_entre_requisicoes": 0}, sessao=transporte)
        def reservar():
            reservadas.append(True)
            return True
        with self.assertRaises(ErroAPI):
            cliente.get_json("https://exemplo.invalid", max_tentativas=2,
                             ao_iniciar_tentativa=reservar)
        self.assertEqual(len(transporte.chamadas), 2)
        self.assertEqual(len(reservadas), 2)

    def test_coleta_propaga_controles_e_429_para_toda_execucao(self):
        class Resposta429:
            status_code = 429
            headers = {"Retry-After": "60"}
            url = "https://exemplo.invalid"
            text = "rate limit"

        class Transporte:
            headers = {}

            def __init__(self):
                self.chamadas = []

            def get(self, url, params=None, timeout=None):
                self.chamadas.append((url, params))
                return Resposta429()

        with tempfile.TemporaryDirectory() as tmp:
            config = carregar(Path(__file__).resolve().parent.parent / "config.yaml")
            config["api"].update(intervalo_entre_requisicoes=0, modalidades=[6, 8])
            config["saida"]["pasta"] = tmp
            hist = Historico(Path(tmp) / "historico.db")
            try:
                transporte = Transporte()
                cliente = ClientePNCP(config["api"], sessao=transporte)
                contabilizadas = []

                def reservar():
                    contabilizadas.append(True)
                    return len(contabilizadas) <= 2

                resultado = executar(
                    config, Parametros(modalidades=[6, 8]), cliente, hist,
                    controles={"deadline_monotonic": time.monotonic() + 30,
                               "cancelar": lambda: False, "max_tentativas": 2,
                               "ao_iniciar_tentativa": reservar},
                )
                self.assertEqual(len(transporte.chamadas), 1)
                self.assertEqual(len(contabilizadas), 1)
                self.assertEqual(resultado.modalidades_com_falha, [6])
                self.assertEqual(resultado.falhas, 1)
            finally:
                hist.fechar()

    def test_cancelar_durante_backoff_impede_proxima_tentativa(self):
        transporte = FalhaTransporte()
        cancelar = WaitCancelavel()
        cliente = ClientePNCP({"tentativas": 5, "backoff_inicial": 4,
                               "intervalo_entre_requisicoes": 0}, sessao=transporte)
        with self.assertRaises(ErroAPIInterrompida):
            cliente.get_json("https://exemplo.invalid", cancelar=cancelar)
        self.assertEqual(len(transporte.chamadas), 1)
        self.assertEqual(cancelar.esperas, [4])

    def test_deadline_reduz_timeout_da_requisicao(self):
        agora = [5.0]

        class Resposta204:
            status_code = 204
            headers = {}
            url = "https://exemplo.invalid"

        class Transporte:
            headers = {}

            def __init__(self):
                self.timeout = None

            def get(self, url, params=None, timeout=None):
                self.timeout = timeout
                return Resposta204()

        transporte = Transporte()
        cliente = ClientePNCP({"timeout_conexao": 30, "timeout_leitura": 30,
                               "intervalo_entre_requisicoes": 0}, sessao=transporte,
                              monotonic=lambda: agora[0])
        self.assertIsNone(cliente.get_json("https://exemplo.invalid", deadline_monotonic=9.0))
        self.assertEqual(transporte.timeout, (2.0, 2.0))

    def test_prazo_vencido_nao_abre_conexao(self):
        transporte = FalhaTransporte()
        cliente = ClientePNCP({"intervalo_entre_requisicoes": 0}, sessao=transporte,
                              monotonic=lambda: 10.0)
        with self.assertRaises(ErroAPIInterrompida):
            cliente.get_json("https://exemplo.invalid", deadline_monotonic=10.0)
        self.assertEqual(transporte.chamadas, [])

    def test_orcamento_global_reserva_cada_tentativa_antes_da_chamada(self):
        transporte = FalhaTransporte()
        autorizadas = iter([True, False])
        cliente = ClientePNCP({"tentativas": 5, "backoff_inicial": 0,
                               "intervalo_entre_requisicoes": 0}, sessao=transporte)
        with self.assertRaises(ErroAPIInterrompida):
            cliente.get_json("https://exemplo.invalid", ao_iniciar_tentativa=lambda: next(autorizadas))
        self.assertEqual(len(transporte.chamadas), 1)

    def test_evento_de_pagina_validada_chega_antes_do_primeiro_registro(self):
        transporte = type("Transporte", (), {
            "headers": {},
            "get": lambda _self, *args, **kwargs: RespostaJSON({
                "data": [{"id": "um"}], "numeroPagina": 1, "totalPaginas": 1,
                "paginasRestantes": 0, "totalRegistros": 1
            }),
        })()
        cliente = ClientePNCP({"base_consulta": "https://exemplo.invalid",
                              "intervalo_entre_requisicoes": 0}, sessao=transporte,
                              monotonic=lambda: 10)
        eventos = []
        gerador = cliente.contratacoes_proposta(
            date(2026, 9, 26), 6,
            ao_receber_pagina=eventos.append,
            deadline_monotonic=20,
            cancelar=lambda: False,
            max_tentativas=3,
            ao_iniciar_tentativa=lambda: True,
        )
        primeiro = next(gerador)
        self.assertEqual(primeiro, {"id": "um"})
        self.assertEqual(eventos[0]["pagina"], 1)
        self.assertEqual(eventos[0]["registros"], [{"id": "um"}])
        self.assertEqual(eventos[0]["modalidade"], 6)

    def test_evento_nao_publica_pagina_com_metadados_invalidos(self):
        transporte = type("Transporte", (), {
            "headers": {},
            "get": lambda _self, *args, **kwargs: RespostaJSON({
                "data": [{"id": "um"}], "numeroPagina": 1, "totalPaginas": 3,
                "paginasRestantes": 0, "totalRegistros": 1
            }),
        })()
        cliente = ClientePNCP({"base_consulta": "https://exemplo.invalid",
                              "intervalo_entre_requisicoes": 0}, sessao=transporte,
                              monotonic=lambda: 10)
        eventos = []
        with self.assertRaises(ErroAPI):
            list(cliente.contratacoes_proposta(date(2026, 9, 26), 6,
                                               ao_receber_pagina=eventos.append))
        self.assertEqual(eventos, [])
