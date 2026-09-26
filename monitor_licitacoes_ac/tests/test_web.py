import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from threading import Lock, Thread
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


    def test_status_incremental_traz_so_mudancas_desde_since_e_aceita_sinonimos(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config)
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                consulta_id = estado.consultas.registrar({"modalidades": [6]}, owner_id="local")
                estado.consultas.admitir(consulta_id)

                cheio = json.loads(urlopen(base + f"/api/status?consulta_id={consulta_id}").read())
                self.assertEqual(cheio["consulta_id"], consulta_id)
                self.assertIn("results", cheio)
                self.assertNotIn("atualizacoes", cheio)
                revisao_inicial = cheio["revisao"]

                estado.consultas.atualizar(consulta_id, resultados=[], candidatos=[],
                                           evento={"tipo": "candidato", "candidato": {"id": "c1", "objeto": "Ar-condicionado"}})
                estado.consultas.atualizar(consulta_id, resultados=[], candidatos=[],
                                           evento={"tipo": "candidato_retirado", "identidade": "c1"})

                # `id` continua aceito como sinônimo de `consulta_id`.
                incremental = json.loads(urlopen(base + f"/api/status?id={consulta_id}&since={revisao_inicial}").read())
                self.assertNotIn("results", incremental)
                self.assertNotIn("candidatos", incremental)
                tipos = [item["tipo"] for item in incremental["atualizacoes"]]
                self.assertEqual(tipos, ["candidato", "candidato_retirado"])
                self.assertEqual(incremental["atualizacoes"][0]["candidato"]["id"], "c1")
                self.assertEqual(incremental["atualizacoes"][1]["identidade"], "c1")
                nova_revisao = incremental["revisao"]
                self.assertGreater(nova_revisao, revisao_inicial)

                # Sem novidade desde a última revisão vista: ainda incremental, mas vazio.
                parado = json.loads(urlopen(base + f"/api/status?consulta_id={consulta_id}&since={nova_revisao}").read())
                self.assertEqual(parado["atualizacoes"], [])
                self.assertNotIn("results", parado)

                # `since` à frente da revisão atual não pode ser aplicado: cai para o modo completo.
                fallback = json.loads(urlopen(base + f"/api/status?consulta_id={consulta_id}&since={nova_revisao + 50}").read())
                self.assertIn("results", fallback)
                self.assertNotIn("atualizacoes", fallback)

                req_invalido = Request(base + f"/api/status?consulta_id={consulta_id}&since=abc")
                with self.assertRaises(HTTPError) as erro:
                    urlopen(req_invalido)
                self.assertEqual(erro.exception.code, 400)
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_options_expoe_catalogo_de_246_municipios_de_goias(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config)
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                opcoes = json.loads(urlopen(base + "/api/options").read())
                municipios = opcoes["municipios"]
                self.assertEqual(len(municipios), 246)
                por_codigo = {m["codigo_ibge"]: m["nome"] for m in municipios}
                self.assertEqual(por_codigo["5208707"], "Goiânia")
                self.assertEqual(por_codigo["5200050"], "Abadia de Goiás")
                self.assertIn("5221858", por_codigo)
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_start_recusa_municipio_fora_de_goias(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config)
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"

                def tentar(municipio):
                    payload = {"modalidades": [6], "esferas": ["E"], "municipio": municipio}
                    req = Request(base + "/api/start", data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
                    with self.assertRaises(HTTPError) as erro:
                        urlopen(req)
                    self.assertEqual(erro.exception.code, 400)
                    return json.loads(erro.exception.read().decode("utf-8"))["error"]

                # Código de outra UF (São Paulo): formato rejeitado antes de olhar o catálogo.
                self.assertIn("Goiás", tentar("3550308"))
                # 7 dígitos começando com 52, mas inexistente no catálogo de GO.
                self.assertIn("catálogo", tentar("5299999"))
                self.assertFalse(estado.running)
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_cabecalho_csp_presente_na_pagina_e_na_api(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config)
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                pagina = urlopen(base + "/")
                self.assertIn("script-src 'self'", pagina.headers.get("Content-Security-Policy", ""))
                api_resp = urlopen(base + "/api/options")
                self.assertIn("default-src 'self'", api_resp.headers.get("Content-Security-Policy", ""))
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_history_pagina_isolamento_por_dono_e_limite_maximo(self):
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
                for i in range(4):
                    estado.consultas.registrar({"n": i}, owner_id="alice-sub")
                estado.consultas.registrar({"n": "bob"}, owner_id="bob-sub")
                alice = {"Cf-Access-Jwt-Assertion": "alice-assinado"}
                bob = {"Cf-Access-Jwt-Assertion": "bob-assinado"}

                pagina1 = json.loads(urlopen(Request(base + "/api/history?pagina=1&por_pagina=3", headers=alice)).read())
                self.assertEqual(pagina1["total"], 4)
                self.assertEqual(len(pagina1["execucoes"]), 3)
                self.assertTrue(pagina1["tem_proxima"])
                pagina2 = json.loads(urlopen(Request(base + "/api/history?pagina=2&por_pagina=3", headers=alice)).read())
                self.assertEqual(len(pagina2["execucoes"]), 1)
                self.assertFalse(pagina2["tem_proxima"])

                # por_pagina acima do limite sensato (50) é limitado no servidor.
                grande = json.loads(urlopen(Request(base + "/api/history?por_pagina=999", headers=alice)).read())
                self.assertEqual(grande["por_pagina"], 50)

                # O histórico de um dono nunca aparece para o outro.
                so_bob = json.loads(urlopen(Request(base + "/api/history", headers=bob)).read())
                self.assertEqual(so_bob["total"], 1)
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_origem_ausente_ou_divergente_e_rejeitada_no_modo_cloudflare(self):
        # AC33: defesa contra CSRF no modo público — uma alteração (POST/DELETE) só é
        # aceita com `Origin` presente e igual ao `Host` da requisição (ver `_origem_valida`).
        class AutenticadorTeste:
            def autenticar(self, headers):
                if headers.get("Cf-Access-Jwt-Assertion") == "alice-assinado":
                    return Identidade("alice@example.test", "alice-sub", {})
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
                payload = json.dumps({"nome": "Busca CSRF", "filtros": {}}).encode()

                # Sem cabeçalho Origin: recusado, mesmo com sessão válida.
                sem_origin = Request(base + "/api/searches", data=payload,
                                     headers={"Content-Type": "application/json",
                                             "Cf-Access-Jwt-Assertion": "alice-assinado"}, method="POST")
                with self.assertRaises(HTTPError) as erro:
                    urlopen(sem_origin)
                self.assertEqual(erro.exception.code, 403)
                self.assertIn("Origem", erro.exception.read().decode("utf-8"))

                # Origin de outro site: recusado.
                origem_alheia = Request(base + "/api/searches", data=payload,
                                        headers={"Content-Type": "application/json",
                                                "Cf-Access-Jwt-Assertion": "alice-assinado",
                                                "Origin": "https://site-malicioso.example"}, method="POST")
                with self.assertRaises(HTTPError) as erro:
                    urlopen(origem_alheia)
                self.assertEqual(erro.exception.code, 403)

                # Nenhuma das tentativas deixou arquivo salvo.
                buscas = json.loads(urlopen(Request(base + "/api/searches",
                                                    headers={"Cf-Access-Jwt-Assertion": "alice-assinado"})).read())
                self.assertEqual(buscas["buscas"], [])

                # Origin igual ao Host: aceito.
                com_origin = Request(base + "/api/searches", data=payload,
                                     headers={"Content-Type": "application/json",
                                             "Cf-Access-Jwt-Assertion": "alice-assinado",
                                             "Origin": base}, method="POST")
                self.assertTrue(json.loads(urlopen(com_origin).read())["ok"])
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_modo_publico_aceita_trafego_de_tunel_sem_login(self):
        # O modo publico expõe o app sem autenticação (decisão explícita do dono), mas
        # continua aceitando o tráfego encaminhado pelo túnel (Host do domínio público e
        # cabeçalhos Cf-*) que o modo local recusaria.
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config, modo_acesso="publico")
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                tunel = Request(base + "/api/options", headers={"Host": "licitacoes-ac.98fred.dev",
                                                                 "Cf-Connecting-Ip": "203.0.113.9"})
                self.assertEqual(urlopen(tunel).status, 200)
                sonda = Request(base + "/healthz", headers={"Host": "licitacoes-ac.98fred.dev",
                                                             "Cf-Connecting-Ip": "203.0.113.9"})
                resposta = json.loads(urlopen(sonda).read())
                self.assertEqual(resposta["access_mode"], "publico")
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_origem_e_verificada_tambem_no_modo_publico(self):
        # No modo publico não há login, mas a checagem de Origin (CSRF) continua ativa
        # para alterações (POST/DELETE) — igual ao modo cloudflare.
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config, modo_acesso="publico")
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                payload = json.dumps({"nome": "Busca publica", "filtros": {}}).encode()

                sem_origin = Request(base + "/api/searches", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
                with self.assertRaises(HTTPError) as erro:
                    urlopen(sem_origin)
                self.assertEqual(erro.exception.code, 403)

                origem_alheia = Request(base + "/api/searches", data=payload,
                                        headers={"Content-Type": "application/json",
                                                "Origin": "https://site-malicioso.example"}, method="POST")
                with self.assertRaises(HTTPError) as erro:
                    urlopen(origem_alheia)
                self.assertEqual(erro.exception.code, 403)

                com_origin = Request(base + "/api/searches", data=payload,
                                     headers={"Content-Type": "application/json", "Origin": base}, method="POST")
                self.assertTrue(json.loads(urlopen(com_origin).read())["ok"])
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)

    def test_modo_publico_com_host_nao_loopback_recusa_subir(self):
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                main(["--config", str(config), "--modo-acesso", "publico", "--host", "0.0.0.0"])

    def test_gravacao_concorrente_do_mesmo_nome_tem_um_sucesso_e_um_conflito(self):
        # AC20: duas gravações concorrentes do mesmo nome nunca sobrescrevem
        # silenciosamente uma a outra (criação exclusiva em `_arquivo_busca`/O_EXCL).
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "config.yaml"
            config.write_text(f"filtro:\n  termos_inclusao: [climatizacao]\nsaida:\n  pasta: '{(Path(td) / 'saida').as_posix()}'\n", encoding="utf-8")
            estado = Estado(config)
            servidor = ThreadingHTTPServer(("127.0.0.1", 0), _handler_class(estado))
            thread = Thread(target=servidor.serve_forever, daemon=True); thread.start()
            try:
                base = f"http://127.0.0.1:{servidor.server_port}"
                resultados: list[int] = []
                lock_resultados = Lock()

                def salvar(indice):
                    payload = json.dumps({"nome": "Busca concorrente",
                                          "filtros": {"indice": indice}}).encode()
                    req = Request(base + "/api/searches", data=payload,
                                  headers={"Content-Type": "application/json"}, method="POST")
                    try:
                        codigo = urlopen(req).status
                    except HTTPError as erro:
                        codigo = erro.code
                    with lock_resultados:
                        resultados.append(codigo)

                threads = [Thread(target=salvar, args=(i,)) for i in range(8)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=5)

                self.assertEqual(resultados.count(201), 1, resultados)
                self.assertEqual(resultados.count(409), 7, resultados)
                lista = json.loads(urlopen(base + "/api/searches").read())
                self.assertEqual(len(lista["buscas"]), 1)
                # O arquivo salvo é íntegro (JSON válido), não uma mistura de duas escritas.
                detalhe = json.loads(urlopen(base + "/api/searches/" + lista["buscas"][0]["arquivo"]).read())
                self.assertIn(detalhe["filtros"]["indice"], range(8))
            finally:
                servidor.shutdown(); servidor.server_close(); thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
