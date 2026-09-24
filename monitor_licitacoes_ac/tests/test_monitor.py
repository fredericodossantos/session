"""Testes offline (sem rede). Rode com:  python -m unittest discover -s tests -v

Os dados abaixo são FICTÍCIOS e seguem o formato documentado da API do PNCP;
servem apenas para testar a lógica do programa.
"""
from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from monitor_ac import filtros
from monitor_ac.api_client import ClientePNCP, ErroAPI
from monitor_ac.coleta import Parametros, executar
from monitor_ac.config import carregar
from monitor_ac.mapeamento import identificar_sistema, mapear
from monitor_ac.persistencia import Historico
from monitor_ac.relatorio import gerar_csv, gerar_html

RAIZ = Path(__file__).resolve().parent.parent
AGORA = datetime(2026, 9, 24, 10, 0)


def contratacao(seq, objeto, esfera="M", enc="2026-10-05T09:00:00", municipio="Município Exemplo",
                ibge="5200000", modalidade=6, link="https://www.licitanet.com.br/processo/1"):
    cnpj = f"{seq:014d}"
    return {
        "numeroControlePNCP": f"{cnpj}-1-{seq:06d}/2026",
        "anoCompra": 2026, "sequencialCompra": seq, "numeroCompra": str(seq), "processo": "P-1",
        "modalidadeId": modalidade, "modalidadeNome": "Pregão - Eletrônico",
        "modoDisputaNome": "Aberto", "situacaoCompraId": 1, "situacaoCompraNome": "Divulgada no PNCP",
        "objetoCompra": objeto, "informacaoComplementar": "", "srp": True,
        "valorTotalEstimado": 123456.78, "dataAberturaProposta": "2026-09-20T08:00:00",
        "dataEncerramentoProposta": enc, "dataPublicacaoPncp": "2026-09-19T10:00:00",
        "dataAtualizacao": "2026-09-19T10:00:00", "linkSistemaOrigem": link,
        "orgaoEntidade": {"cnpj": cnpj, "razaoSocial": f"ÓRGÃO FICTÍCIO {seq}", "poderId": "E",
                          "esferaId": esfera},
        "unidadeOrgao": {"codigoUnidade": "1", "nomeUnidade": "UNIDADE X", "codigoIbge": ibge,
                         "municipioNome": municipio, "ufSigla": "GO", "ufNome": "Goiás"},
    }


class Resp:
    def __init__(self, status, corpo=None, url=""):
        import json
        self.status_code = status
        self._corpo = corpo
        self.content = b"" if corpo is None else json.dumps(corpo).encode()
        self.text = self.content.decode()
        self.headers = {}
        self.url = url

    def json(self):
        return self._corpo


class SessaoFalsa:
    """Responde como a API: paginação em /proposta e itens por compra."""

    def __init__(self, paginas_por_mod, itens_por_seq, falhas_antes=0):
        self.paginas = paginas_por_mod
        self.itens = itens_por_seq
        self.falhas_antes = falhas_antes
        self.headers = {}
        self.chamadas = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append((url, dict(params or {})))
        if self.falhas_antes:
            self.falhas_antes -= 1
            return Resp(503, {"erro": "indisponível"}, url)
        if url.endswith("/v1/contratacoes/proposta"):
            paginas = self.paginas.get(params["codigoModalidadeContratacao"], [])
            if not paginas:
                return Resp(204, None, url)
            n = params["pagina"]
            return Resp(200, {"data": paginas[n - 1], "totalRegistros": sum(map(len, paginas)),
                              "totalPaginas": len(paginas), "numeroPagina": n,
                              "paginasRestantes": len(paginas) - n, "empty": False}, url)
        if url.endswith("/itens"):
            seq = int(url.split("/")[-2])
            return Resp(200, self.itens.get(seq, []), url)
        return Resp(404, {"message": "não encontrado"}, url)


def item(n, tipo):
    nomes = {1: "Participação exclusiva para ME/EPP", 3: "Cota reservada para ME/EPP",
             4: "Sem benefício", 5: "Não se aplica"}
    return {"numeroItem": n, "descricao": "item", "tipoBeneficio": tipo,
            "tipoBeneficioNome": nomes[tipo]}


class TestFiltro(unittest.TestCase):
    def setUp(self):
        self.f = filtros.FiltroPalavras(carregar(RAIZ / "config.yaml")["filtro"])

    def aceita(self, objeto):
        return self.f.avaliar({"objetoCompra": objeto}).aceito

    def test_normalizar(self):
        self.assertEqual(filtros.normalizar("Climatização  AR-CONDICIONADO"),
                         "climatizacao ar condicionado")

    def test_inclusoes(self):
        for objeto in ["Aquisição de AR-CONDICIONADO tipo split",
                       "Manutenção de condicionadores de ar da Secretaria",
                       "Serviços de CLIMATIZAÇÃO predial",
                       "Aquisição de climatizadores evaporativos",
                       "Elaboração e execução de PMOC",
                       "Manutenção de sistemas de refrigeração",
                       "Instalação de aparelhos Split Hi-Wall",
                       "Fornecimento de condicionador de ar 12.000 BTUs"]:
            self.assertTrue(self.aceita(objeto), objeto)

    def test_nao_inclui(self):
        for objeto in ["Manutenção preventiva e corretiva de elevadores",
                       "Aquisição de splitter óptico",
                       "Aquisição de gêneros alimentícios",
                       "Manutenção de ar condicionado automotivo da frota"]:
            self.assertFalse(self.aceita(objeto), objeto)

    def test_condicional_marca_termo(self):
        r = self.f.avaliar({"objetoCompra": "Manutenção preventiva e corretiva de ar condicionado"})
        self.assertTrue(r.aceito)
        self.assertIn("manutencao preventiva e corretiva", r.termos)


class TestBeneficio(unittest.TestCase):
    def test_classificacao(self):
        c = filtros.classificar_me_epp
        self.assertEqual(c([item(1, 1), item(2, 1)])[0], filtros.EXCLUSIVA)
        self.assertEqual(c([item(1, 1), item(2, 4)])[0], filtros.PARCIAL)
        self.assertEqual(c([item(1, 4), item(2, 3)])[0], filtros.COTA)
        self.assertEqual(c([item(1, 4), item(2, 5)])[0], filtros.AMPLA)
        self.assertEqual(c([])[0], filtros.NAO_INFORMADO)

    def test_variantes_de_campo(self):
        c = filtros.classificar_me_epp
        self.assertEqual(c([{"tipoBeneficioId": "1"}])[0], filtros.EXCLUSIVA)
        self.assertEqual(c([{"tipoBeneficio": {"id": 3}}])[0], filtros.COTA)
        self.assertEqual(c([{"tipoBeneficioNome": "Participação exclusiva para ME/EPP"}])[0],
                         filtros.EXCLUSIVA)


class TestCliente(unittest.TestCase):
    cfg = {"base_consulta": "https://x/api/consulta", "base_pncp": "https://x/api/pncp",
           "intervalo_entre_requisicoes": 0, "tentativas": 3, "backoff_inicial": 0.01}

    def test_paginacao_completa(self):
        paginas = {6: [[contratacao(1, "a")], [contratacao(2, "b")], [contratacao(3, "c")]]}
        s = SessaoFalsa(paginas, {})
        cli = ClientePNCP(self.cfg, sessao=s, dormir=lambda _: None)
        regs = list(cli.contratacoes_proposta(AGORA.date(), 6, uf="GO"))
        self.assertEqual([r["sequencialCompra"] for r in regs], [1, 2, 3])
        self.assertEqual(s.chamadas[0][1]["dataFinal"], "20260924")
        self.assertEqual(s.chamadas[0][1]["uf"], "GO")

    def test_204_vazio(self):
        cli = ClientePNCP(self.cfg, sessao=SessaoFalsa({}, {}), dormir=lambda _: None)
        self.assertEqual(list(cli.contratacoes_proposta(AGORA.date(), 6)), [])

    def test_retry(self):
        s = SessaoFalsa({6: [[contratacao(1, "a")]]}, {}, falhas_antes=2)
        esperas = []
        cli = ClientePNCP(self.cfg, sessao=s, dormir=esperas.append)
        self.assertEqual(len(list(cli.contratacoes_proposta(AGORA.date(), 6))), 1)
        self.assertEqual(len(esperas), 2)
        self.assertLess(esperas[0], esperas[1])  # backoff exponencial

    def test_desiste(self):
        s = SessaoFalsa({6: [[contratacao(1, "a")]]}, {}, falhas_antes=9)
        cli = ClientePNCP(self.cfg, sessao=s, dormir=lambda _: None)
        with self.assertRaises(ErroAPI):
            list(cli.contratacoes_proposta(AGORA.date(), 6))
        self.assertEqual(len(s.chamadas), 3)
        self.assertEqual(len(cli.falhas), 1)


class TestMapeamento(unittest.TestCase):
    def test_campos(self):
        r = mapear(contratacao(42, "Ar condicionado", esfera="E"), {"licitanet": "Licitanet"})
        self.assertEqual(r["esfera"], "Estadual")
        self.assertEqual(r["link_pncp"], f"https://pncp.gov.br/app/editais/{42:014d}/2026/42")
        self.assertEqual(r["sistema_origem"], "Licitanet")
        self.assertEqual(r["data_encerramento"], datetime(2026, 10, 5, 9, 0))

    def test_sistema_desconhecido_usa_dominio(self):
        self.assertEqual(identificar_sistema("https://www.exemplo.gov.br/x", {}), "exemplo.gov.br")


class TestExecucao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = carregar(RAIZ / "config.yaml")
        self.config["api"].update(intervalo_entre_requisicoes=0, backoff_inicial=0.01, tentativas=2)
        self.config["saida"]["pasta"] = self.tmp.name
        paginas = {
            6: [[contratacao(1, "Aquisição de ar-condicionado split", enc="2026-10-10T09:00:00"),
                 contratacao(2, "Aquisição de pneus")],
                [contratacao(3, "Manutenção preventiva e corretiva de condicionadores de ar",
                             esfera="E", enc="2026-09-28T09:00:00",
                             link="https://sislog.go.gov.br/x")],
                ],
            8: [[contratacao(4, "Climatização do auditório", esfera="F"),     # federal: fora
                 contratacao(5, "PMOC do prédio sede", enc="2027-03-01T09:00:00"),  # fora da janela
                 contratacao(1, "Aquisição de ar-condicionado split", enc="2026-10-10T09:00:00")]],
        }
        itens = {1: [item(1, 1), item(2, 1)], 3: [item(1, 4), item(2, 3)]}
        self.sessao = SessaoFalsa(paginas, itens)
        self.hist = Historico(Path(self.tmp.name) / "h.db")

    def tearDown(self):
        self.hist.fechar()
        self.tmp.cleanup()

    def rodar(self, **kw):
        cli = ClientePNCP(self.config["api"], sessao=self.sessao, dormir=lambda _: None)
        self.config["api"]["modalidades"] = [6, 8]
        return executar(self.config, Parametros(dias=30, **kw), cli, self.hist, agora=AGORA)

    def test_fluxo_completo(self):
        r = self.rodar()
        self.assertEqual(r.encontradas, 5)          # sem duplicar a nº 1
        self.assertEqual(r.filtradas, 2)            # 1 e 3
        self.assertEqual(r.me_epp, 2)
        self.assertEqual(r.exclusivas, 1)
        self.assertEqual(r.novas, 2)
        sit = {x["numero_controle"][-11:]: x["situacao_me_epp"] for x in r.registros}
        self.assertEqual(sit, {"000001/2026": filtros.EXCLUSIVA, "000003/2026": filtros.COTA})

        # Segunda execução: nada novo e itens vêm do cache (sem nova chamada a /itens).
        antes = sum(1 for u, _ in self.sessao.chamadas if u.endswith("/itens"))
        r2 = self.rodar()
        depois = sum(1 for u, _ in self.sessao.chamadas if u.endswith("/itens"))
        self.assertEqual(r2.novas, 0)
        self.assertEqual(antes, depois)

    def test_somente_me_epp_e_relatorios(self):
        self.sessao.itens[1] = [item(1, 4)]  # vira ampla participação
        r = self.rodar(somente_me_epp=True)
        self.assertEqual(len(r.registros), 1)
        csv_path = gerar_csv(r.registros, Path(self.tmp.name) / "r.csv")
        with csv_path.open(encoding="utf-8-sig") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        self.assertEqual(linhas[1][1], filtros.COTA)
        html_path = gerar_html(r.registros, Path(self.tmp.name) / "r.html", {"filtradas": 2})
        self.assertIn("SISLOG", html_path.read_text(encoding="utf-8"))

    def test_ordem_por_prazo(self):
        r = self.rodar()
        csv_path = gerar_csv(r.registros, Path(self.tmp.name) / "r.csv")
        with csv_path.open(encoding="utf-8-sig") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        self.assertEqual([l[2] for l in linhas[1:]], ["28/09/2026 09:00", "10/10/2026 09:00"])


if __name__ == "__main__":
    unittest.main()
