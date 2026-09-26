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
SUBCONTRATACAO = "Subcontratação ME/EPP"
AMPLA = "Ampla participação"
NAO_INFORMADO = "Não informado"

SITUACOES_ME_EPP = {EXCLUSIVA, COTA, PARCIAL, SUBCONTRATACAO}


def normalizar(texto: str | None) -> str:
    """Minúsculas, sem acentos, pontuação vira espaço, espaços colapsados."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return texto.strip()


def _corresponde_termos_regex_legacy(texto: str | None, termos: Iterable[str]) -> bool:
    """Retorna verdadeiro quando qualquer termo aparece como palavra no texto normalizado."""
    normalizado = normalizar(texto)
    for termo in termos:
        termo_normalizado = normalizar(termo)
        if termo_normalizado and re.search(r"\b" + re.escape(termo_normalizado) + r"\b", normalizado):
            return True
    return False


def corresponde_termos(texto: str | None, termos: Iterable[str]) -> bool:
    """Versão sem regex: compara palavras/frases inteiras no título normalizado."""
    normalizado = " " + normalizar(texto) + " "
    return any(
        termo_normalizado and (" " + termo_normalizado + " ") in normalizado
        for termo in termos
        for termo_normalizado in [normalizar(termo)]
    )


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
    evidencias: list[dict[str, str]] | None = None


class FiltroPalavras:
    def __init__(self, cfg_filtro: dict[str, Any]):
        self.campos = cfg_filtro.get("campos") or ["objetoCompra"]
        self.inclusao = _compilar(cfg_filtro.get("termos_inclusao") or [])
        self.condicionais = _compilar(cfg_filtro.get("termos_condicionais") or [])
        self.exclusao = _compilar(cfg_filtro.get("termos_exclusao") or [])

    def texto_de(self, contratacao: dict) -> str:
        # Relevância é determinada pelo título/objeto disponível no PNCP.
        # Campos auxiliares (complemento, órgão, unidade) não devem resgatar
        # um edital cujo objeto não contém os termos configurados.
        objeto = contratacao.get("objetoCompra") or contratacao.get("objeto") or ""
        return normalizar(objeto)

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


def _rx_catalogo(termo: str) -> re.Pattern | None:
    """Regex de frase inteira normalizada, aceitando flexão simples de plural."""
    t = normalizar(termo)
    if not t:
        return None
    partes = [re.escape(p) + r"(?:s|es)?" for p in t.split()]
    return re.compile(r"\b" + r"\s+".join(partes) + r"\b")


def _achados(texto: str, termos: Iterable[str]) -> list[tuple[str, str]]:
    achados = []
    for termo in termos:
        rx = _rx_catalogo(termo)
        if rx:
            encontrado = rx.search(texto)
            if encontrado:
                achados.append((termo, encontrado.group(0)))
    return achados


def _grupos_satisfeitos(texto: str, grupos: list[list[str]]) -> tuple[bool, list[tuple[str, str]]]:
    achados: list[tuple[str, str]] = []
    for grupo in grupos:
        opcoes = _achados(texto, grupo)
        if not opcoes:
            return False, []
        achados.append(opcoes[0])
    return bool(grupos), achados


def _corresponde_regra(texto: str, regra: dict) -> tuple[bool, list[tuple[str, str]]]:
    """Uma regra casa por termo direto, rota alternativa ou todos os grupos exigidos."""
    diretos = _achados(texto, regra.get("termos", []))
    if diretos:
        return True, [diretos[0]]
    for rota in regra.get("rotas", []):
        ok, achados = _grupos_satisfeitos(texto, rota.get("grupos_obrigatorios", []))
        if ok:
            return True, achados
    return _grupos_satisfeitos(texto, regra.get("grupos_obrigatorios", []))


def _avaliar_catalogo(texto: str, filtros: dict[str, Any], catalogo: Any) -> ResultadoFiltro:
    try:
        setores = catalogo.validar_ids("setores", filtros.get("setores", []))
        servicos = catalogo.validar_ids("servicos", filtros.get("servicos", []))
        contextos = catalogo.validar_ids("contextos", filtros.get("contextos", []))
        perfil = filtros.get("perfil")
        if perfil is not None:
            catalogo.validar_ids("perfis", [perfil], permitir_vazio=False)
    except ValueError as exc:
        return ResultadoFiltro(False, [], str(exc))
    subareas_por_setor = filtros.get("subareas") or {}
    if not isinstance(subareas_por_setor, dict):
        return ResultadoFiltro(False, [], "'subareas' deve ser um mapa")
    if any(sid not in setores for sid in subareas_por_setor):
        return ResultadoFiltro(False, [], "'subareas' só pode refinar setores selecionados")
    evidencias: list[dict[str, str]] = []
    setores_aceitos: list[str] = []
    for sid in setores:
        setor = catalogo.setor(sid)
        ok, termos = _corresponde_regra(texto, setor)
        generico = False
        if not ok and filtros.get("incluir_predial_generico") and sid == "manutencao_integrada":
            achados_genericos = _achados(texto, setor.get("permitir_generico", []))
            if achados_genericos:
                ok, termos, generico = True, [achados_genericos[0]], True
        if not ok:
            continue
        # Exclusões pertencem ao setor que as declara. Um setor independente,
        # como iluminação pública, ainda pode validar um objeto misto.
        if _achados(texto, setor.get("exclusoes", [])):
            continue
        escolhidas = subareas_por_setor.get(sid, [])
        subindice = {x["id"]: x for x in setor.get("subareas", [])}
        subarea_encontrada: tuple[str, list[tuple[str, str]]] | None = None
        if escolhidas:
            if not isinstance(escolhidas, list) or len(set(escolhidas)) != len(escolhidas) or any(
                    not isinstance(x, str) or x not in subindice for x in escolhidas):
                return ResultadoFiltro(False, [], f"Subáreas inválidas para '{sid}'")
            sub_ok = False
            for subid in escolhidas:
                subok, subtermos = _corresponde_regra(texto, subindice[subid])
                if subok:
                    sub_ok = True
                    subarea_encontrada = (subid, subtermos)
                    break
            if not sub_ok:
                continue
        setores_aceitos.append(sid)
        for termo, trecho in termos:
            evidencias.append({"tipo": "setor", "id": sid, "termo": termo, "trecho": trecho})
        if subarea_encontrada:
            subid, subtermos = subarea_encontrada
            for termo, trecho in subtermos:
                evidencias.append({"tipo": "subarea", "id": subid, "termo": termo, "trecho": trecho})
        if generico:
            evidencias.append({"tipo": "aviso", "id": "escopo_a_confirmar",
                               "termo": "Escopo a confirmar no edital", "trecho": termos[0][1]})
    if not setores_aceitos:
        return ResultadoFiltro(False, [], "nenhum setor técnico corresponde")

    # Serviço: qualquer serviço selecionado (OU) precisa ocorrer no objeto,
    # associado a um dos setores selecionados (setor já validado acima).
    if servicos:
        servicos_aceitos = []
        for vid in servicos:
            achados = _achados(texto, catalogo.servico(vid).get("termos", []))
            if not achados:
                for sid in setores_aceitos:
                    excecao = catalogo.setor(sid).get("servicos_excecao", {}).get(vid, [])
                    achados = _achados(texto, excecao)
                    if achados:
                        break
            if achados:
                servicos_aceitos.append(vid)
                evidencias.append({"tipo": "servico", "id": vid,
                                   "termo": achados[0][0], "trecho": achados[0][1]})
        if not servicos_aceitos:
            return ResultadoFiltro(False, [], "nenhum serviço selecionado corresponde")

    if contextos:
        contextos_ok = []
        for cid in contextos:
            achados = _achados(texto, catalogo.contexto(cid).get("termos", []))
            if achados:
                contextos_ok.append(cid)
                evidencias.append({"tipo": "contexto", "id": cid,
                                   "termo": achados[0][0], "trecho": achados[0][1]})
        if not contextos_ok:
            return ResultadoFiltro(False, [], "nenhum contexto selecionado corresponde")

    palavras = filtros.get("palavras_chave") or []
    if palavras:
        if not isinstance(palavras, list) or not any(_achados(texto, [p]) for p in palavras if isinstance(p, str)):
            return ResultadoFiltro(False, [], "nenhuma palavra-chave corresponde")
        achado = next((a for p in palavras if isinstance(p, str) for a in _achados(texto, [p])), None)
        if achado:
            evidencias.append({"tipo": "palavra_chave", "id": "", "termo": achado[0], "trecho": achado[1]})
    termos_saida = list(dict.fromkeys(e["termo"] for e in evidencias))
    return ResultadoFiltro(True, termos_saida, evidencias=evidencias)


def avaliar_catalogo(contratacao: dict, filtros: dict[str, Any], catalogo: Any) -> ResultadoFiltro:
    """Avalia regras v2 sobre ``objetoCompra`` e devolve evidências explicáveis."""
    original = str(contratacao.get("objetoCompra") or contratacao.get("objeto") or "")
    texto = normalizar(original)
    compat = filtros.get("compatibilidade_v1")
    if compat is None:
        resultado = _avaliar_catalogo(texto, filtros, catalogo)
    else:
        alternativas = compat.get("alternativas", []) if isinstance(compat, dict) else []
        resultado = ResultadoFiltro(False, [], "nenhuma alternativa v1 corresponde")
        for alternativa in alternativas:
            if not isinstance(alternativa, dict):
                continue
            termo_literal = alternativa.get("termo_literal") or []
            if termo_literal:
                encontrados = _achados(texto, termo_literal)
                if not encontrados:
                    continue
                ramo = ResultadoFiltro(True, [encontrados[0][0]], evidencias=[{
                    "tipo": "compatibilidade_v1", "id": "termo_literal",
                    "termo": encontrados[0][0], "trecho": encontrados[0][1]}])
            else:
                ramo_filtros = {"setores": alternativa.get("setores", []),
                                "servicos": alternativa.get("servicos", []), "contextos": [],
                                "subareas": {}, "palavras_chave": compat.get("palavras_chave", [])}
                ramo = _avaliar_catalogo(texto, ramo_filtros, catalogo)
            if ramo.aceito:
                resultado = ramo
                break
    if resultado.evidencias:
        for evidencia in resultado.evidencias:
            evidencia["catalogo_versao"] = catalogo.versao
            evidencia["trecho"] = _trecho_original(original, evidencia.get("trecho", ""))
    return resultado


def _trecho_original(original: str, trecho_normalizado: str) -> str:
    """Recupera a grafia original da menor sequência de palavras correspondente."""
    palavras = list(re.finditer(r"[^\W_]+", original, flags=re.UNICODE))
    alvo = normalizar(trecho_normalizado).split()
    if not alvo:
        return trecho_normalizado
    for tamanho in range(max(1, len(alvo) - 1), len(alvo) + 2):
        for inicio in range(0, len(palavras) - tamanho + 1):
            ini, fim = palavras[inicio].start(), palavras[inicio + tamanho - 1].end()
            candidato = original[ini:fim]
            if normalizar(candidato) == " ".join(alvo):
                return candidato
    return trecho_normalizado


def _codigo_beneficio(item: dict) -> int | None:
    """Lê o tipo de benefício do item aceitando as variações de nome já vistas na API."""
    for chave in ("tipoBeneficio", "tipoBeneficioId"):
        valor = item.get(chave)
        if isinstance(valor, dict):
            valor = valor.get("id") or valor.get("codigo")
        if valor not in (None, ""):
            if isinstance(valor, bool) or isinstance(valor, float):
                continue
            try:
                codigo = int(valor)
                if str(valor).strip() not in (str(codigo), f"+{codigo}"):
                    continue
                return codigo
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


VERSAO_CLASSIFICACAO = 2


def classificar_me_epp(itens: list[dict]) -> tuple[str, dict[str, int]]:
    """Classifica a contratação a partir dos itens.

    * todos os itens exclusivos ME/EPP            -> Exclusiva ME/EPP
    * alguns (não todos) itens exclusivos          -> Parcial
    * nenhum exclusivo, mas há item de cota        -> Cota reservada ME/EPP
    * nenhum item com benefício ME/EPP             -> Ampla participação
    * sem itens / benefício não informado          -> Não informado
    """
    contagem = {"itens": len(itens), "exclusivos": 0, "cota": 0, "subcontratacao": 0, "sem_info": 0}
    for item in itens:
        cod = _codigo_beneficio(item)
        if cod == BENEFICIO_EXCLUSIVA:
            contagem["exclusivos"] += 1
        elif cod == BENEFICIO_COTA:
            contagem["cota"] += 1
        elif cod == BENEFICIO_SUBCONTRATACAO:
            contagem["subcontratacao"] += 1
        elif cod in (BENEFICIO_SEM, BENEFICIO_NAO_SE_APLICA):
            pass
        else:
            contagem["sem_info"] += 1
    if not itens or contagem["sem_info"]:
        return NAO_INFORMADO, contagem
    if contagem["exclusivos"] == len(itens):
        return EXCLUSIVA, contagem
    if contagem["exclusivos"]:
        return PARCIAL, contagem
    if contagem["cota"]:
        return COTA, contagem
    if contagem["subcontratacao"]:
        return SUBCONTRATACAO, contagem
    return AMPLA, contagem
