"""Converte um registro bruto da API em uma linha do relatório."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

ESFERAS = {"E": "Estadual", "M": "Municipal", "F": "Federal", "D": "Distrital"}

# Número de controle PNCP: {cnpj}-1-{sequencial}/{ano}, ex. 01234567000189-1-000042/2026
RX_CONTROLE = re.compile(r"^(\d{14})-\d+-(\d+)/(\d{4})$")
FUSO_BRASILIA = timedelta(hours=-3)


def parse_data(valor: Any) -> datetime | None:
    """Datas da API vêm como 'AAAA-MM-DDTHH:MM:SS' (horário de Brasília, sem fuso)."""
    if not valor:
        return None
    texto = str(valor).strip()
    try:
        dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone(FUSO_BRASILIA))
        return dt.replace(tzinfo=None)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, fmt)
            except ValueError:
                continue
        return None


def chave_compra(bruto: dict) -> tuple[str, int, int] | None:
    """(cnpj, ano, sequencial) para montar o link e consultar os itens."""
    orgao = bruto.get("orgaoEntidade") or {}
    cnpj = orgao.get("cnpj")
    ano = bruto.get("anoCompra")
    seq = bruto.get("sequencialCompra")
    if cnpj and ano and seq:
        try:
            return str(cnpj), int(ano), int(seq)
        except (TypeError, ValueError):
            pass
    m = RX_CONTROLE.match(str(bruto.get("numeroControlePNCP") or ""))
    if m:
        return m.group(1), int(m.group(3)), int(m.group(2))
    return None


def link_pncp(bruto: dict) -> str:
    chave = chave_compra(bruto)
    if not chave:
        return ""
    cnpj, ano, seq = chave
    return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"


def identificar_sistema(link: str, mapa: dict[str, str]) -> str:
    if not link:
        return ""
    try:
        host = (urlparse(link if "://" in link else "https://" + link).netloc or link).lower()
    except ValueError:
        return ""
    alvo = host + " " + link.lower()
    for fragmento, nome in mapa.items():
        if fragmento.lower() in alvo:
            return nome
    return host.removeprefix("www.")


def _booleano_opcional(valor: Any) -> bool | None:
    """Converte campos booleanos conhecidos e conserva valores ausentes/inválidos como desconhecidos."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int) and valor in (0, 1):
        return bool(valor)
    if isinstance(valor, str):
        normalizado = valor.strip().lower()
        if normalizado in {"true", "1", "sim", "s"}:
            return True
        if normalizado in {"false", "0", "nao", "não", "n"}:
            return False
    return None


def mapear(bruto: dict, mapa_sistemas: dict[str, str]) -> dict[str, Any]:
    orgao = bruto.get("orgaoEntidade") or {}
    unidade = bruto.get("unidadeOrgao") or {}
    link_origem = (bruto.get("linkSistemaOrigem") or "").strip()
    abertura = parse_data(bruto.get("dataAberturaProposta"))
    encerramento = parse_data(bruto.get("dataEncerramentoProposta"))
    return {
        "numero_controle": bruto.get("numeroControlePNCP") or "",
        "orgao": orgao.get("razaoSocial") or orgao.get("razaosocial") or "",
        "unidade": unidade.get("nomeUnidade") or "",
        "cnpj": orgao.get("cnpj") or "",
        "municipio": unidade.get("municipioNome") or "",
        "codigo_ibge": str(unidade.get("codigoIbge") or ""),
        "uf": unidade.get("ufSigla") or "",
        "esfera": ESFERAS.get(str(orgao.get("esferaId") or "").upper(), orgao.get("esferaId") or ""),
        "esfera_id": str(orgao.get("esferaId") or "").upper(),
        "objeto": " ".join(str(bruto.get("objetoCompra") or "").split()),
        "modalidade": bruto.get("modalidadeNome") or "",
        "modalidade_id": bruto.get("modalidadeId"),
        "modo_disputa": bruto.get("modoDisputaNome") or "",
        "situacao_compra": bruto.get("situacaoCompraNome") or "",
        "numero_compra": f"{bruto.get('numeroCompra') or ''}/{bruto.get('anoCompra') or ''}".strip("/"),
        "processo": bruto.get("processo") or "",
        "srp": _booleano_opcional(bruto.get("srp")),
        "valor_estimado": bruto.get("valorTotalEstimado"),
        "data_abertura": abertura,
        "data_encerramento": encerramento,
        "data_publicacao": parse_data(bruto.get("dataPublicacaoPncp")),
        "data_atualizacao": str(bruto.get("dataAtualizacao") or bruto.get("dataAtualizacaoGlobal") or ""),
        "link_pncp": link_pncp(bruto),
        "link_origem": link_origem,
        "sistema_origem": identificar_sistema(link_origem, mapa_sistemas),
        "situacao_me_epp": "",
        "contagem_itens": {},
        "termos": [],
        "estado": "",
    }
