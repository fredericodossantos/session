"""Autenticação local ou validação do JWT emitido pelo Cloudflare Access."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)
_SHA256_DIGEST_INFO = bytes.fromhex("3031300d060960864801650304020105000420")


class AcessoNegado(Exception):
    """Sessão ausente, expirada ou não emitida para este app."""


class ConfiguracaoAcessoInvalida(ValueError):
    """O modo protegido não tem a configuração necessária para iniciar."""


@dataclass(frozen=True)
class Identidade:
    email: str
    subject: str
    claims: dict[str, Any]


def _b64url(texto: str) -> bytes:
    if (not texto or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-=" for c in texto)
            or "=" in texto[:-2]):
        raise ValueError("base64url inválido")
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _json_segmento(texto: str) -> dict[str, Any]:
    valor = json.loads(_b64url(texto))
    if not isinstance(valor, dict):
        raise ValueError("segmento JWT não é um objeto")
    return valor


def _rsa_sha256_verificar(jwk: dict[str, Any], mensagem: bytes, assinatura: bytes) -> bool:
    """Confere uma assinatura RS256 com os parâmetros RSA publicados em um JWK."""
    if jwk.get("kty") != "RSA" or jwk.get("alg", "RS256") != "RS256":
        return False
    if jwk.get("use", "sig") != "sig" or "verify" not in jwk.get("key_ops", ["verify"]):
        return False
    n = int.from_bytes(_b64url(str(jwk["n"])), "big")
    e = int.from_bytes(_b64url(str(jwk["e"])), "big")
    tamanho = (n.bit_length() + 7) // 8
    if tamanho < 128 or len(assinatura) != tamanho:
        return False
    valor_assinado = int.from_bytes(assinatura, "big")
    if valor_assinado >= n:
        return False
    bloco = pow(valor_assinado, e, n).to_bytes(tamanho, "big")
    digest = _SHA256_DIGEST_INFO + hashlib.sha256(mensagem).digest()
    preenchimento = tamanho - len(digest) - 3
    if preenchimento < 8:
        return False
    esperado = b"\x00\x01" + (b"\xff" * preenchimento) + b"\x00" + digest
    return hmac.compare_digest(bloco, esperado)


class AutenticadorCloudflare:
    """Valida Cf-Access-Jwt-Assertion, assinatura, emissor e audiência.

    `loader` existe para testes offline. Em produção, as chaves vêm do endpoint
    HTTPS oficial do time Cloudflare Access e ficam em cache por cinco minutos.
    """

    def __init__(self, team_domain: str, audience: str,
                 loader: Callable[[str], dict[str, Any]] | None = None,
                 relogio: Callable[[], float] = time.time,
                 monotonic: Callable[[], float] = time.monotonic):
        partes = urlsplit(str(team_domain).strip())
        if (partes.scheme != "https" or not partes.hostname or partes.path or
                partes.query or partes.fragment or partes.username or partes.password):
            raise ConfiguracaoAcessoInvalida("O domínio da equipe Cloudflare deve ser uma URL HTTPS sem caminho.")
        if not audience or not str(audience).strip():
            raise ConfiguracaoAcessoInvalida("A audiência da aplicação Cloudflare Access é obrigatória.")
        self.team_domain = str(team_domain).strip().rstrip("/")
        self.audience = str(audience).strip()
        self._loader = loader or self._carregar_chaves
        self._relogio = relogio
        self._monotonic = monotonic
        self._lock = threading.Lock()
        self._keys: list[dict[str, Any]] = []
        self._keys_expiram = 0.0

    @staticmethod
    def _carregar_chaves(url: str) -> dict[str, Any]:
        resposta = requests.get(url, timeout=(3.0, 5.0))
        resposta.raise_for_status()
        dado = resposta.json()
        if not isinstance(dado, dict) or not isinstance(dado.get("keys"), list):
            raise ValueError("JWKS do Cloudflare Access em formato inválido")
        return dado

    def _obter_chaves(self, renovar: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            if renovar or self._monotonic() >= self._keys_expiram:
                documento = self._loader(self.team_domain + "/cdn-cgi/access/certs")
                chaves = documento.get("keys") if isinstance(documento, dict) else None
                if not isinstance(chaves, list) or not chaves or any(not isinstance(k, dict) for k in chaves):
                    raise ValueError("JWKS do Cloudflare Access sem chaves válidas")
                self._keys = chaves
                self._keys_expiram = self._monotonic() + 300.0
            return list(self._keys)

    def autenticar(self, headers: Any) -> Identidade:
        token = headers.get("Cf-Access-Jwt-Assertion") if hasattr(headers, "get") else None
        if not token:
            raise AcessoNegado("Entre pelo Cloudflare Access para continuar.")
        if not isinstance(token, str) or len(token) > 16_384:
            raise AcessoNegado("Token de acesso inválido.")
        try:
            partes = token.split(".")
            if len(partes) != 3:
                raise ValueError("JWT deve ter três segmentos")
            cabecalho = _json_segmento(partes[0])
            claims = _json_segmento(partes[1])
            assinatura = _b64url(partes[2])
            mensagem = (partes[0] + "." + partes[1]).encode("ascii")
        except (binascii.Error, UnicodeError, ValueError, TypeError) as exc:
            raise AcessoNegado("Token de acesso inválido.") from exc
        kid = cabecalho.get("kid")
        if cabecalho.get("alg") != "RS256" or not isinstance(kid, str) or cabecalho.get("crit"):
            raise AcessoNegado("Assinatura do token não aceita.")
        try:
            chaves = self._obter_chaves()
            candidatas = [k for k in chaves if k.get("kid") == kid]
            if not candidatas:
                chaves = self._obter_chaves(renovar=True)
                candidatas = [k for k in chaves if k.get("kid") == kid]
            assinatura_valida = any(_rsa_sha256_verificar(k, mensagem, assinatura) for k in candidatas)
        except (KeyError, TypeError, ValueError, requests.RequestException) as exc:
            log.warning("Não foi possível validar a identidade do Cloudflare Access: %s", exc)
            raise AcessoNegado("Não foi possível verificar a sessão. Tente entrar novamente.") from exc
        if not assinatura_valida:
            raise AcessoNegado("Assinatura do token de acesso inválida.")
        agora = self._relogio()
        try:
            exp = float(claims["exp"])
            inicio = float(claims["nbf"]) if "nbf" in claims else None
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise AcessoNegado("Token de acesso sem validade temporal reconhecida.") from exc
        if (not math.isfinite(exp) or exp <= agora or
                (inicio is not None and (not math.isfinite(inicio) or inicio > agora))):
            raise AcessoNegado("Sessão expirada ou ainda não válida. Entre novamente.")
        if claims.get("iss") != self.team_domain:
            raise AcessoNegado("Token emitido por outra equipe Cloudflare.")
        aud = claims.get("aud")
        audiencias = [aud] if isinstance(aud, str) else aud if isinstance(aud, list) else []
        if self.audience not in audiencias:
            raise AcessoNegado("Token não pertence a esta aplicação.")
        email = claims.get("email")
        subject = claims.get("sub")
        if not isinstance(email, str) or not email.strip() or not isinstance(subject, str) or not subject.strip():
            raise AcessoNegado("Identidade sem e-mail ou identificador válido.")
        # O principal vem somente dos claims assinados; não confiamos no cabeçalho de e-mail.
        return Identidade(email=email.strip().casefold(), subject=subject, claims=claims)
