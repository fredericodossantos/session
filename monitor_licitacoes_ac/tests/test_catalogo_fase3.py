"""Regressões do catálogo e do contrato de filtros da Fase 3."""
from __future__ import annotations

import unittest
from pathlib import Path

from monitor_ac.catalogo import carregar_catalogo, migrar_filtros_v1
from monitor_ac.filtros import FiltroPalavras, avaliar_catalogo


RAIZ = Path(__file__).resolve().parents[1]


class CatalogoFase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogo = carregar_catalogo(RAIZ / "catalogo_areas.yaml")

    def avaliar(self, objeto, setores, servicos=None, contextos=None, subareas=None, **extras):
        return avaliar_catalogo({"objetoCompra": objeto}, {
            "setores": setores, "servicos": servicos or [], "contextos": contextos or [],
            "subareas": subareas or {}, "palavras_chave": [], **extras,
        }, self.catalogo)

    def test_catalogo_publico_tem_shape_estavel_e_iluminacao_selecionavel(self):
        publico = self.catalogo.publico()
        ip = next(s for s in publico["setores"] if s["id"] == "iluminacao_publica")
        self.assertEqual("Iluminação pública", ip["rotulo"])
        self.assertIn({"id": "ip_led", "rotulo": "Modernização para LED"}, ip["subareas"])
        self.assertIn("setores", next(p for p in publico["perfis"] if p["id"] == "eletrica"))
        self.assertIn("servicos", publico)
        self.assertIn("contextos", publico)
        self.assertIn("presets", publico)

    def test_iluminacao_publica_reconhece_sem_climatizacao_e_gatilhos_contextuais(self):
        resultado = self.avaliar("Modernização da iluminação pública com luminárias LED", ["iluminacao_publica"])
        self.assertTrue(resultado.aceito)
        self.assertEqual("iluminacao_publica", resultado.evidencias[0]["id"])

        self.assertTrue(self.avaliar("Telegestão do parque de iluminação pública", ["iluminacao_publica"]).aceito)
        self.assertTrue(self.avaliar("Fornecimento de luminárias para vias públicas", ["iluminacao_publica"]).aceito)
        self.assertTrue(self.avaliar("Modernização da iluminação pública com luminárias LED", ["iluminacao_publica"],
                                     subareas={"iluminacao_publica": ["ip_led"]}).aceito)

    def test_iluminacao_nao_casa_termos_genericos_fora_do_contexto(self):
        for objeto in ("Aquisição de painel de LED para eventos", "Instalação de postes para cercamento",
                       "Manutenção da rede de computadores", "Configuração de endereço IP"):
            with self.subTest(objeto=objeto):
                self.assertFalse(self.avaliar(objeto, ["iluminacao_publica"]).aceito)

    def test_setores_sao_ou_servicos_sao_ou_e_contexto_e_restritivo_se_escolhido(self):
        self.assertTrue(self.avaliar("Manutenção de subestação de média tensão", ["subestacoes"],
                                     ["manutencao", "laudos_inspecoes"]).aceito)
        self.assertFalse(self.avaliar("Manutenção de subestação de média tensão", ["subestacoes"],
                                      ["laudos_inspecoes"]).aceito)
        self.assertFalse(self.avaliar("Laudo das instalações elétricas em hospital", ["instalacoes_eletricas"],
                                      contextos=["industria"]).aceito)
        self.assertTrue(self.avaliar("Laudo das instalações elétricas em hospital", ["instalacoes_eletricas"],
                                     contextos=["saude", "industria"]).aceito)

    def test_casos_de_borda_do_catalogo(self):
        casos = [
            ("Elaboração de laudo de SPDA e aterramento elétrico", ["spda_aterramento"], ["laudos_inspecoes"], True),
            ("Fornecimento de gerador de energia para escola", ["energia_emergencia"], ["fornecimento"], True),
            ("Gerador de relatórios para sistema de informática", ["energia_emergencia"], [], False),
            ("Aquisição de aparelhos de ar-condicionado", ["climatizacao"], ["fornecimento"], True),
            ("Aquisição de splitter HDMI", ["climatizacao"], [], False),
            ("Contratação de PMOC", ["pmoc"], ["manutencao"], True),
            ("Instalação de câmara fria para alimentos", ["camaras_frias"], ["instalacao"], True),
            ("Aquisição de bomba para poço artesiano", ["agua_gelada"], [], False),
        ]
        for objeto, setores, servicos, esperado in casos:
            with self.subTest(objeto=objeto):
                self.assertEqual(esperado, self.avaliar(objeto, setores, servicos).aceito)

    def test_um_exemplo_positivo_para_cada_setor(self):
        positivos = {
            "climatizacao": "Aquisição de condicionadores de ar split",
            "pmoc": "Contratação de PMOC para prédio administrativo",
            "refrigeracao": "Manutenção de refrigeração industrial",
            "ventilacao_exaustao": "Instalação de ventilação mecânica",
            "agua_gelada": "Manutenção de chiller e central de água gelada",
            "camaras_frias": "Instalação de câmara fria para alimentos",
            "conforto_termico": "Solução para conforto térmico",
            "instalacoes_eletricas": "Laudo das instalações elétricas prediais",
            "paineis_comandos": "Manutenção de painel elétrico",
            "subestacoes": "Manutenção de subestação de média tensão",
            "energia_emergencia": "Fornecimento de grupo gerador para hospital",
            "spda_aterramento": "Laudo de SPDA e malha de aterramento",
            "automacao_predial": "Implantação de automação predial",
            "solar_fotovoltaica": "Instalação de usina solar fotovoltaica",
            "eficiencia_eletrica": "Correção de fator de potência em instalações",
            "iluminacao_publica": "Modernização do parque de iluminação pública",
            "climatizacao_infra_eletrica": "Climatização e infraestrutura elétrica de prédio",
            "automacao_hvac": "Automação e controle do sistema HVAC",
            "retrofit_predial": "Retrofit de prédio com modernização da instalação elétrica",
            "manutencao_integrada": "Manutenção predial integrada de sistemas elétricos",
            "ambientes_criticos": "Climatização e energia para data center",
        }
        for setor, objeto in positivos.items():
            with self.subTest(setor=setor):
                self.assertTrue(self.avaliar(objeto, [setor]).aceito)

    def test_subareas_de_iluminacao_restringem_evidencia_complementar(self):
        exemplos = {
            "ip_manutencao": "Manutenção de iluminação pública",
            "ip_expansao": "Expansão da rede de iluminação pública",
            "ip_led": "Modernização da iluminação pública com luminárias LED",
            "ip_telegestao": "Telegestão do parque de iluminação pública",
            "ip_eficiencia": "Eficientização do parque de iluminação pública",
            "ip_componentes": "Troca de postes da iluminação pública",
            "ip_projetos": "Projeto de iluminação pública",
            "ip_cadastro_gestao": "Cadastro e inventário do parque luminotécnico",
        }
        for subarea, objeto in exemplos.items():
            with self.subTest(subarea=subarea):
                filtros = {"setores": ["iluminacao_publica"], "servicos": [], "contextos": [],
                           "subareas": {"iluminacao_publica": [subarea]}, "palavras_chave": []}
                self.assertTrue(avaliar_catalogo({"objetoCompra": objeto}, filtros, self.catalogo).aceito)
        self.assertFalse(self.avaliar("Manutenção predial integrada", ["manutencao_integrada"]).aceito)
        com_aviso = self.avaliar("Manutenção predial integrada", ["manutencao_integrada"],
                                 incluir_predial_generico=True)
        self.assertTrue(com_aviso.aceito)
        self.assertIn("aviso", [e["tipo"] for e in com_aviso.evidencias])

    def test_exclusao_automotiva_e_local_ao_setor(self):
        self.assertFalse(self.avaliar("Manutenção de ar-condicionado automotivo da frota",
                                      ["climatizacao"]).aceito)
        misto = self.avaliar("Manutenção de iluminação pública e veículos da frota",
                             ["climatizacao", "iluminacao_publica"])
        self.assertTrue(misto.aceito)
        self.assertIn("iluminacao_publica", [e["id"] for e in misto.evidencias if e["tipo"] == "setor"])

    def test_perfil_e_subarea_nao_sao_palavras_procuradas(self):
        filtros = {"setores": ["subestacoes"], "servicos": [], "contextos": [],
                   "subareas": {}, "palavras_chave": [], "perfil": "eletrica"}
        self.assertTrue(avaliar_catalogo({"objetoCompra": "Manutenção de subestação"},
                                         filtros, self.catalogo).aceito)
        self.assertFalse(self.avaliar("Manutenção de subestação", ["subestacoes"],
                                      subareas={"subestacoes": ["id_inexistente"]}).aceito)

    def test_migracao_v1_preserva_ou_sem_modificar_entrada(self):
        legado = {"areas": ["manutencao", "pmoc", "refrigeracao"], "palavras_chave": ["hospital"]}
        copia = {k: (list(v) if isinstance(v, list) else v) for k, v in legado.items()}
        migrado = migrar_filtros_v1(legado)
        self.assertEqual(legado, copia)
        self.assertEqual(2, migrado["schema_version"])
        self.assertEqual([
            {"setores": ["climatizacao"], "servicos": ["manutencao"]},
            {"setores": ["pmoc"], "servicos": []},
            {"setores": ["refrigeracao"], "servicos": []},
        ], migrado["compatibilidade_v1"]["alternativas"])
        sem_areas = migrar_filtros_v1({"areas": []})
        self.assertEqual([{"setores": ["climatizacao"], "servicos": []}],
                         sem_areas["compatibilidade_v1"]["alternativas"])

    def test_filtro_migrado_avalia_ramos_v1_com_ou(self):
        migrado = migrar_filtros_v1({"areas": ["manutencao", "pmoc"]})
        filtros = {"setores": [], "servicos": [], "contextos": [], "subareas": {},
                   "palavras_chave": [], "compatibilidade_v1": migrado["compatibilidade_v1"]}
        self.assertTrue(avaliar_catalogo({"objetoCompra": "Manutenção de ar condicionado"},
                                         filtros, self.catalogo).aceito)
        self.assertTrue(avaliar_catalogo({"objetoCompra": "Contratação de PMOC"},
                                         filtros, self.catalogo).aceito)
        self.assertFalse(avaliar_catalogo({"objetoCompra": "Manutenção predial genérica"},
                                          filtros, self.catalogo).aceito)

    def test_caminho_legado_sem_setor_continua_com_filtro_climatizacao(self):
        legado = FiltroPalavras({"termos_inclusao": ["ar condicionado"], "termos_condicionais": [],
                                 "termos_exclusao": ["automotivo"]})
        self.assertTrue(legado.avaliar({"objetoCompra": "Aquisição de ar condicionado"}).aceito)
        self.assertFalse(legado.avaliar({"objetoCompra": "Ar condicionado automotivo"}).aceito)


if __name__ == "__main__":
    unittest.main()
