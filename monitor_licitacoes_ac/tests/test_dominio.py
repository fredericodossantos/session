from __future__ import annotations

import tempfile
import sqlite3
import unittest
from datetime import datetime
from pathlib import Path

from monitor_ac import filtros
from monitor_ac.mapeamento import identificar_sistema, mapear, parse_data
from monitor_ac.catalogo import carregar_catalogo
from monitor_ac.persistencia import Historico
from tests.test_monitor import AGORA, SessaoFalsa, contratacao, item
from monitor_ac.api_client import ClientePNCP
from monitor_ac.coleta import Parametros, executar
from monitor_ac.config import carregar

RAIZ = Path(__file__).resolve().parent.parent


class TestClassificacaoConservadora(unittest.TestCase):
    def test_desconhecido_nao_prova_ampla_nem_exclusividade(self):
        self.assertEqual(filtros.classificar_me_epp([item(1, 4), {"tipoBeneficio": 99}])[0], filtros.NAO_INFORMADO)
        self.assertEqual(filtros.classificar_me_epp([item(1, 1), {"tipoBeneficio": 99}])[0], filtros.NAO_INFORMADO)

    def test_subcontratacao_e_beneficio_apresentavel(self):
        situacao, contagem = filtros.classificar_me_epp([{"tipoBeneficio": 2}])
        self.assertEqual(situacao, filtros.SUBCONTRATACAO)
        self.assertIn(situacao, filtros.SITUACOES_ME_EPP)
        self.assertEqual(contagem["subcontratacao"], 1)

    def test_codigo_de_tipo_invalido(self):
        for tipo in (True, 1.5, "99"):
            self.assertEqual(filtros.classificar_me_epp([{"tipoBeneficio": tipo}])[0], filtros.NAO_INFORMADO)

    def test_palavra_chave_casa_somente_o_titulo(self):
        self.assertTrue(filtros.corresponde_termos("Manutenção de split hospitalar", ["hospitalar"]))
        self.assertFalse(filtros.corresponde_termos("Manutenção de splitter óptico", ["split"]))

    def test_filtro_legado_usa_somente_objeto(self):
        filtro = filtros.FiltroPalavras({"campos": ["objetoCompra", "informacaoComplementar"],
                                         "termos_inclusao": ["climatização"]})
        self.assertFalse(filtro.avaliar({"objetoCompra": "Iluminação pública com luminárias LED",
                                         "informacaoComplementar": "Também inclui climatização"}).aceito)
        self.assertTrue(filtro.avaliar({"objetoCompra": "Manutenção de climatização"}).aceito)

    def test_climatizacao_nao_captura_iluminacao_publica(self):
        catalogo = carregar_catalogo(RAIZ / "catalogo_areas.yaml")
        ilum = {"objetoCompra": "Modernização da iluminação pública com luminárias LED"}
        clima = {"objetoCompra": "Aquisição de aparelhos de ar-condicionado"}
        self.assertFalse(filtros.avaliar_catalogo(ilum, {"setores": ["climatizacao"]}, catalogo).aceito)
        self.assertTrue(filtros.avaliar_catalogo(ilum, {"setores": ["iluminacao_publica"]}, catalogo).aceito)
        self.assertTrue(filtros.avaliar_catalogo(clima, {"setores": ["climatizacao"]}, catalogo).aceito)


class TestDatasBrasilia(unittest.TestCase):
    def test_offsets_sao_convertidos_incluindo_microsegundos(self):
        self.assertEqual(parse_data("2026-09-24T15:00:00+00:00"), datetime(2026, 9, 24, 12))
        self.assertEqual(parse_data("2026-09-24T12:00:00.123456-03:00"),
                         datetime(2026, 9, 24, 12, 0, 0, 123456))
        self.assertEqual(parse_data("2026-09-24T12:00:00"), datetime(2026, 9, 24, 12))

    def test_url_malformada_nao_quebra_mapeamento(self):
        self.assertEqual(identificar_sistema("https://[", {}), "")

    def test_mapeamento_preserva_dados_ausentes_como_desconhecidos(self):
        reg = mapear({"objetoCompra": "Teste", "orgaoEntidade": {}, "unidadeOrgao": {}}, {})
        self.assertIsNone(reg["srp"])
        self.assertIsNone(reg["data_encerramento"])
        self.assertEqual(reg["uf"], "")
        self.assertEqual(reg["esfera_id"], "")

    def test_mapeamento_nao_converte_texto_false_em_true(self):
        self.assertIs(mapear({"srp": "false"}, {})["srp"], False)


class TestCacheEColeta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hist = Historico(Path(self.tmp.name) / "h.sqlite")
        self.cfg = carregar(RAIZ / "config.yaml")
        self.cfg["api"].update(modalidades=[6], intervalo_entre_requisicoes=0, tentativas=1)
        self.cfg["saida"]["pasta"] = self.tmp.name

    def tearDown(self):
        self.hist.fechar()
        self.tmp.cleanup()

    def test_cache_sem_data_desconhecido_ou_versao_antiga_e_invalido(self):
        reg = {"numero_controle": "id", "data_atualizacao": None, "situacao_me_epp": filtros.COTA,
               "contagem_itens": {"itens": 1, "cota": 1}}
        self.hist.registrar(reg)
        self.assertIsNone(self.hist.beneficio_em_cache("id", None))
        reg["numero_controle"] = "id2"
        reg["situacao_me_epp"] = filtros.NAO_INFORMADO
        reg["data_atualizacao"] = "2026-09-20"
        self.hist.registrar(reg)
        self.assertIsNone(self.hist.beneficio_em_cache("id2", "2026-09-20"))
        reg.update(numero_controle="id3", situacao_me_epp=filtros.COTA,
                   contagem_itens={"itens": 1, "cota": 1})
        self.hist.registrar(reg)
        self.hist.con.execute("UPDATE licitacoes SET versao_classificacao=1 WHERE numero_controle='id3'")
        self.hist.con.commit()
        self.assertIsNone(self.hist.beneficio_em_cache("id3", "2026-09-20"))

    def test_migracao_preserva_registro_e_invalida_cache(self):
        caminho = Path(self.tmp.name) / "antigo.sqlite"
        con = sqlite3.connect(caminho)
        con.execute("""CREATE TABLE licitacoes (
            numero_controle TEXT PRIMARY KEY, primeira_vez TEXT NOT NULL, ultima_vez TEXT NOT NULL,
            data_atualizacao TEXT, situacao_me_epp TEXT, contagem_itens TEXT, dados TEXT)""")
        con.execute("INSERT INTO licitacoes VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("legado", "inicio", "agora", "2026-09-20", filtros.COTA,
                     '{"itens": 1, "cota": 1}', '{"objeto":"legado"}'))
        con.commit()
        con.close()
        legado = Historico(caminho)
        try:
            self.assertEqual(legado.buscar("legado")["dados"], '{"objeto":"legado"}')
            self.assertIsNone(legado.beneficio_em_cache("legado", "2026-09-20"))
        finally:
            legado.fechar()

    def test_mudanca_sem_data_preserva_primeira_aparicao_e_registra_evento(self):
        reg = {"numero_controle": "sem-data", "data_atualizacao": None, "objeto": "objeto A",
               "situacao_me_epp": filtros.COTA, "contagem_itens": {"itens": 1, "cota": 1}}
        self.hist.registrar(reg)
        primeira = self.hist.buscar("sem-data")["primeira_vez"]
        self.assertEqual(self.hist.registrar(dict(reg, objeto="objeto B")), "atualizada")
        self.assertEqual(self.hist.buscar("sem-data")["primeira_vez"], primeira)
        evento = self.hist.con.execute("SELECT campos FROM mudancas_relevantes WHERE numero_controle='sem-data'").fetchone()
        self.assertIn("objeto", evento["campos"])

    def test_registra_candidato_excluido_da_apresentacao(self):
        bruto = contratacao(21, "Aquisição de climatização", enc="2026-10-02T09:00:00")
        sessao = SessaoFalsa({6: [[bruto]]}, {21: [item(1, 4)]})
        cli = ClientePNCP(self.cfg["api"], sessao=sessao, dormir=lambda _: None)
        resultado = executar(self.cfg, Parametros(dias=30, somente_me_epp=True), cli, self.hist, agora=AGORA)
        self.assertEqual(resultado.registros, [])
        self.assertIsNotNone(self.hist.buscar(bruto["numeroControlePNCP"]))

    def test_esfera_e_palavra_chave_restringem_resultado(self):
        a = contratacao(26, "Manutenção de split hospitalar", esfera="E", enc="2026-10-02T09:00:00")
        b = contratacao(27, "Manutenção de split escolar", esfera="M", enc="2026-10-02T09:00:00")
        sessao = SessaoFalsa({6: [[a, b]]}, {26: [item(1, 4)], 27: [item(1, 4)]})
        cli = ClientePNCP(self.cfg["api"], sessao=sessao, dormir=lambda _: None)
        resultado = executar(self.cfg, Parametros(dias=30, esferas=["E"], palavras_chave=["hospitalar"],
                                                  areas_atuacao=["manutencao"]),
                             cli, self.hist, agora=AGORA)
        self.assertEqual([r["numero_controle"] for r in resultado.registros], [a["numeroControlePNCP"]])

    def test_dados_de_escopo_ausentes_nao_passam(self):
        bruto = contratacao(23, "Aquisição de climatização", enc="2026-10-02T09:00:00")
        bruto["unidadeOrgao"].pop("ufSigla")
        bruto.pop("dataEncerramentoProposta")
        sessao = SessaoFalsa({6: [[bruto]]}, {})
        cli = ClientePNCP(self.cfg["api"], sessao=sessao, dormir=lambda _: None)
        resultado = executar(self.cfg, Parametros(dias=30), cli, self.hist, agora=AGORA)
        self.assertEqual(resultado.registros, [])
        self.assertEqual(resultado.no_escopo, 0)

    def test_sem_numero_controle_tem_identidades_distintas(self):
        a = contratacao(24, "Aquisição de ar-condicionado A", enc="2026-10-02T09:00:00")
        b = contratacao(25, "Aquisição de ar-condicionado B", enc="2026-10-02T09:00:00")
        for bruto in (a, b):
            bruto.pop("numeroControlePNCP")
        sessao = SessaoFalsa({6: [[a, b]]}, {})
        cli = ClientePNCP(self.cfg["api"], sessao=sessao, dormir=lambda _: None)
        resultado = executar(self.cfg, Parametros(dias=30), cli, self.hist, agora=AGORA)
        self.assertEqual(len(resultado.registros), 2)
        self.assertNotEqual(resultado.registros[0]["numero_controle"], resultado.registros[1]["numero_controle"])

    def test_identidade_sem_numero_converge_com_controle_pncp(self):
        numerada = contratacao(26, "Aquisição de ar-condicionado", enc="2026-10-02T09:00:00")
        sem_numero = dict(numerada)
        sem_numero.pop("numeroControlePNCP")
        sessao = SessaoFalsa({6: [[sem_numero, numerada]]}, {})
        cli = ClientePNCP(self.cfg["api"], sessao=sessao, dormir=lambda _: None)
        resultado = executar(self.cfg, Parametros(dias=30), cli, self.hist, agora=AGORA)
        self.assertEqual(len(resultado.registros), 1)
        self.assertEqual(resultado.registros[0]["numero_controle"], numerada["numeroControlePNCP"])

    def test_dedup_escolhe_versao_mais_recente(self):
        antiga = contratacao(22, "Aquisição de ar-condicionado", enc="2026-10-02T09:00:00")
        nova = dict(antiga, objetoCompra="Aquisição de ar-condicionado atualizado", dataAtualizacao="2026-09-23T10:00:00")
        antiga["dataAtualizacao"] = "2026-09-20T10:00:00"
        sessao = SessaoFalsa({6: [[antiga, nova]]}, {22: [{"tipoBeneficio": 2}]})
        cli = ClientePNCP(self.cfg["api"], sessao=sessao, dormir=lambda _: None)
        resultado = executar(self.cfg, Parametros(dias=30), cli, self.hist, agora=AGORA)
        self.assertEqual(len(resultado.registros), 1)
        self.assertIn("atualizado", resultado.registros[0]["objeto"])
        self.assertEqual(resultado.registros[0]["situacao_me_epp"], filtros.SUBCONTRATACAO)
        resultado2 = executar(self.cfg, Parametros(dias=30), cli, self.hist, agora=AGORA)
        self.assertEqual(resultado2.registros[0]["estado"], "vista")


if __name__ == "__main__":
    unittest.main()
