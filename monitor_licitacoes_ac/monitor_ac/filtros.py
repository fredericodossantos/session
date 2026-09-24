"""Filtro por palavras-chave e classificação ME/EPP."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

# Tabela de domínio "Tipo de Benefício" do PNCP.
BENEFICIO_EXCLUSIVA = 1
BENEFICIO_SUBCONTRATACAO = 2
BENEFICIO_COTA = 3
BENEFICIO_SEM = 4
BENEFICIO_NAO_SE_APLICA = 5

EXCLUSIVA = "Exclusiva ME/EPP"
COTA = "Cota reservada ME/EPP"
PARCIAL = "Parcial"
AMPLA = "Ampla participação"
NAO_INFORMADO = "Não informado"

SITUACOES_ME_EPP = {EXCLUSIVA, COTA, PARCIAL}


def normalizar(texto: str | None) -> str:
    """Minúsculas, sem acentos, pontuação vira espaço, espaços colapsados."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return texto.strip()


def _compilar(termos: Iterable[str]) -> list[tuple[str, re.Pattern]]:
    saida = []
    for termo in termos:
        t = normalizar(termo)
        if not t:
            continue
        partes = [re.escape(p) for p in t.split()]
        # Início de palavra + plural simples opcional no fim de cada palavra.
        corpo = r"\s+".join(p + r"(?:s|es)?" for p in partes)
        saida.append((termo, re.compile(r"\b" + corpo + r"\b")))
    return saida


@dataclass
class ResultadoFiltro:
    aceito: bool
    termos: list[str]
    motivo: str = ""


class FiltroPalavras:
    def __init__(self, cfg_filtro: dict[str, Any]):
        self.campos = cfg_filtro.get("campos") or ["objetoCompra"]
        self.inclusao = _compilar(cfg_filtro.get("termos_inclusao") or [])
        self.condicionais = _compilar(cfg_filtro.get("termos_condicionais") or [])
        self.exclusao = _compilar(cfg_filtro.get("termos_exclusao") or [])

    def texto_de(self, contratacao: dict) -> str:
        return " ".join(normalizar(contratacao.get(c)) for c in self.campos)

    def avaliar(self, contratacao: dict) -> ResultadoFiltro:
        texto = self.texto_de(contratacao)
        achados = [t for t, rx in self.inclusao if rx.search(texto)]
        if not achados:
            return ResultadoFiltro(False, [], "sem termo de climatização")
        excl = [t for t, rx in self.exclusao if rx.search(texto)]
        if excl:
            return ResultadoFiltro(False, achados, "termo de exclusão: " + ", ".join(excl))
        achados += [t for t, rx in self.condicionais if rx.search(texto)]
        return ResultadoFiltro(True, achados)


def _codigo_beneficio(item: dict) -> int | None:
    """Lê o tipo de benefício do item aceitando as variações de nome já vistas na API."""
    for chave in ("tipoBeneficio", "tipoBeneficioId"):
        valor = item.get(chave)
        if isinstance(valor, dict):
            valor = valor.get("id") or valor.get("codigo")
        if valor not in (None, ""):
            try:
                return int(valor)
            except (TypeError, ValueError):
                pass
    nome = normalizar(item.get("tipoBeneficioNome"))
    if "exclusiva" in nome:
        return BENEFICIO_EXCLUSIVA
    if "cota" in nome:
        return BENEFICIO_COTA
    if "subcontratacao" in nome:
        return BENEFICIO_SUBCONTRATACAO
    if "sem beneficio" in nome:
        return BENEFICIO_SEM
    if "nao se aplica" in nome:
        return BENEFICIO_NAO_SE_APLICA
    return None


def classificar_me_epp(itens: list[dict]) -> tuple[str, dict[str, int]]:
    """Classifica a contratação a partir dos itens.

    * todos os itens exclusivos ME/EPP            -> Exclusiva ME/EPP
    * alguns (não todos) itens exclusivos          -> Parcial
    * nenhum exclusivo, mas há item de cota        -> Cota reservada ME/EPP
    * nenhum item com benefício ME/EPP             -> Ampla participação
    * sem itens / benefício não informado          -> Não informado
    """
    contagem = {"itens": len(itens), "exclusivos": 0, "cota": 0, "sem_info": 0}
    for item in itens:
        cod = _codigo_beneficio(item)
        if cod == BENEFICIO_EXCLUSIVA:
            contagem["exclusivos"] += 1
        elif cod == BENEFICIO_COTA:
            contagem["cota"] += 1
        elif cod is None:
            contagem["sem_info"] += 1
    if not itens or contagem["sem_info"] == len(itens):
        return NAO_INFORMADO, contagem
    if contagem["exclusivos"] == len(itens):
        return EXCLUSIVA, contagem
    if contagem["exclusivos"]:
        return PARCIAL, contagem
    if contagem["cota"]:
        return COTA, contagem
    return AMPLA, contagem
