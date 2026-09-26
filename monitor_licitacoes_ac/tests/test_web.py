import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from threading import Thread
from http.server import ThreadingHTTPServer

from monitor_ac.acesso import AcessoNegado, Identidade
from monitor_ac.web import Estado, _apresentar_consulta, _handler_class, _preparar_compatibilidade_v1, main


class TestInterfaceWeb(unittest.TestCase):
    def test_filtros_v1_preservam_alternativas_ou_no_payload_web(self):
        payload = {"compatibilidade_v1": {"areas": ["pmoc", "manutencao"]},
                   "palavras_chave": ["hospital"]}
        _preparar_compatibilidade_v1(payload)
        alternativas = payload["compatibilidade_v1"]["alternativas"]
        self.assertEqual(alternativas, [
            {"setores": ["pmoc"], "servicos": []},
            {"setores": ["climatizacao"], "servicos": ["manutencao"]},
        ])
        self.assertEqual(payload["compatibilidade_v1"]["palavras_chave"], ["hospital"])

    def test_links_com_esquema_invalido_sao_anulados_na_consulta_publica(self):
        snapshot = {"consulta_id": "abc", "estado": "concluida",
                    "resultados": [{"numero_controle": "1",
                                    "link_pncp": "https://pncp.gov.br/app/editais/1/2026/1",
                                    "link_origem": "javascript:alert(1)",
                                    "linkSistemaOrigem": "javascript:alert(1)"}]}
        exibido = _apresentar_consulta(snapshot)
        registro = exibido["results"][0]
        self.assertEqual(registro["link_pncp"], "https://pncp.gov.br/app/editais/1/2026/1")
        self.assertEqual(registro["link_origem"], "")
        self.assertEqual(registro["linkSistemaOrigem"], "")

    def test_abertura_nova_interface_carrega_catalogo_sem_iniciar_consulta(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config)
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                pagina = urlopen(base + "/").read().decode("utf-8")
                self.assertIn("/static/app.css", pagina)
                self.assertIn("/static/app.js", pagina)
                self.assertIn("Iluminação pública", pagina)
                self.assertIn("Goiás", pagina)
                self.assertFalse(estado.running)
                opcoes = json.loads(urlopen(base + "/api/options").read())
                self.assertEqual(opcoes["uf"]["codigo"], "GO")
                self.assertIn("iluminacao_publica", [x["id"] for x in opcoes["catalog"]["setores"]])
                script = urlopen(base + "/static/app.js").read().decode("utf-8")
                self.assertIn("POST /api/start", script)
                req = Request(base + "/api/start", data=json.dumps({"modalidades": []}).encode(),
                              headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(Exception):
                    urlopen(req)
                self.assertFalse(estado.running)
                autenticado = Request(base + "/", headers={"Cf-Access-Authenticated-User-Email": "teste@example.com"})
                pagina_autenticada = urlopen(autenticado).read().decode("utf-8")
                self.assertNotIn("teste@example.com", pagina_autenticada)
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_modo_cloudflare_exige_jwt_validado_e_isola_buscas_por_identidade(self):
        class AutenticadorTeste:
            def autenticar(self, headers):
                token = headers.get("Cf-Access-Jwt-Assertion")
                if token == "alice-assinado":
                    return Identidade("alice@example.test", "alice-sub", {})
                if token == "bob-assinado":
                    return Identidade("bob@example.test", "bob-sub", {})
                raise AcessoNegado("Entre pelo Cloudflare Access para continuar.")

        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            saida = (Path(td) / "saida").as_posix()
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{saida}'\nacesso:\n  team_domain: https://equipe.cloudflareaccess.com\n  audience: teste\n", encoding="utf-8")
            estado = Estado(config, modo_acesso="cloudflare")
            estado.autenticador = AutenticadorTeste()
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                sem_sessao = Request(base + "/api/searches", headers={"Cf-Access-Authenticated-User-Email": "alice@example.test"})
                with self.assertRaises(HTTPError) as erro:
                    urlopen(sem_sessao)
                self.assertEqual(erro.exception.code, 401)
                self.assertIn("Cloudflare Access", erro.exception.read().decode("utf-8"))

                cabecalhos = {"Cf-Access-Jwt-Assertion": "alice-assinado", "Origin": base}
                req = Request(base + "/api/searches", data=json.dumps({"nome": "Manutenção", "filtros": {"areas": ["manutencao"]}}).encode(),
                              headers={**cabecalhos, "Content-Type": "application/json"}, method="POST")
                arquivo = json.loads(urlopen(req).read())["arquivo"]
                sessao = json.loads(urlopen(Request(base + "/api/session", headers=cabecalhos)).read())
                self.assertEqual(sessao["session"]["email"], "alice@example.test")

                bob = {"Cf-Access-Jwt-Assertion": "bob-assinado"}
                self.assertEqual(json.loads(urlopen(Request(base + "/api/searches", headers=bob)).read())["buscas"], [])
                with self.assertRaises(HTTPError) as erro:
                    urlopen(Request(base + "/api/searches/" + arquivo, headers=bob))
                self.assertEqual(erro.exception.code, 404)
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_modo_local_recusa_trafego_encaminhado_por_tunel_publico(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config)
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                # Host de loopback (é o que um urlopen comum manda): continua funcionando.
                self.assertEqual(urlopen(base + "/api/options").status, 200)
                self.assertEqual(urlopen(base + "/healthz").status, 200)

                # Host público (ex.: DNS rebinding, ou o hostname do túnel encaminhado por engano).
                host_publico = Request(base + "/api/options", headers={"Host": "licitacoes-ac.98fred.dev"})
                with self.assertRaises(HTTPError) as erro:
                    urlopen(host_publico)
                self.assertEqual(erro.exception.code, 403)

                # Cabeçalho típico de Cloudflare Tunnel/Access, mesmo com Host correto.
                cf_headers = Request(base + "/api/options", headers={"Cf-Connecting-Ip": "203.0.113.9"})
                with self.assertRaises(HTTPError) as erro:
                    urlopen(cf_headers)
                self.assertEqual(erro.exception.code, 403)

                # /healthz é a sonda usada pelo lançador e continua liberada mesmo sob esses cabeçalhos.
                sonda_1 = Request(base + "/healthz", headers={"Host": "licitacoes-ac.98fred.dev"})
                self.assertEqual(urlopen(sonda_1).status, 200)
                sonda_2 = Request(base + "/healthz", headers={"Cf-Connecting-Ip": "203.0.113.9"})
                self.assertEqual(urlopen(sonda_2).status, 200)
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_modo_local_com_host_nao_loopback_recusa_subir(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                main(["--config", str(config), "--modo-acesso", "local", "--host", "0.0.0.0"])

    def test_salva_carrega_e_exclui_busca(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config)
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                sem_nome = {"nome": "", "filtros": {}}
                req = Request(base + "/api/searches", data=json.dumps(sem_nome).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(HTTPError) as erro:
                    urlopen(req)
                self.assertEqual(erro.exception.code, 400)
                self.assertIn("Informe um nome", erro.exception.read().decode("utf-8"))
                payload = {"nome": "Manutenção Goiânia", "filtros": {"modalidades": [6], "esferas": ["E", "M"], "palavras_chave": ["hospital"]}}
                req = Request(base + "/api/searches", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
                salvo = json.loads(urlopen(req).read())
                self.assertTrue(salvo["ok"])
                with self.assertRaises(HTTPError) as erro:
                    urlopen(req)
                self.assertEqual(erro.exception.code, 409)
                self.assertIn("Já existe uma busca", erro.exception.read().decode("utf-8"))
                lista = json.loads(urlopen(base + "/api/searches").read())
                self.assertEqual(lista["buscas"][0]["nome"], "Manutenção Goiânia")
                detalhe = json.loads(urlopen(base + "/api/searches/" + salvo["arquivo"]).read())
                self.assertEqual(detalhe["filtros"]["modalidades"], [6])
                req = Request(base + "/api/searches/" + salvo["arquivo"], method="DELETE")
                self.assertTrue(json.loads(urlopen(req).read())["ok"])
                self.assertEqual(json.loads(urlopen(base + "/api/searches").read())["buscas"], [])
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
