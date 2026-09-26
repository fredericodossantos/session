"""Testes offline do JWT de sessão, sem depender do Cloudflare real."""
import base64
import hashlib
import json
import secrets
import unittest
from math import gcd

from monitor_ac.acesso import (
    AcessoNegado,
    AutenticadorCloudflare,
    ConfiguracaoAcessoInvalida,
    _SHA256_DIGEST_INFO,
)


def _b64(valor: bytes) -> str:
    return base64.urlsafe_b64encode(valor).rstrip(b"=").decode("ascii")


def _primo(bits: int = 512) -> int:
    bases = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    while True:
        n = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        d, s = n - 1, 0
        while d % 2 == 0:
            s += 1
            d //= 2
        for a in bases:
            x = pow(a, d, n)
            if x in (1, n - 1):
                continue
            for _ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                break
        else:
            return n


class TestAutenticadorCloudflare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = _primo()
        cls.q = _primo()
        while cls.q == cls.p:
            cls.q = _primo()
        cls.e = 65537
        phi = (cls.p - 1) * (cls.q - 1)
        while gcd(cls.e, phi) != 1:
            cls.q = _primo()
            phi = (cls.p - 1) * (cls.q - 1)
        cls.d = pow(cls.e, -1, phi)
        cls.n = cls.p * cls.q
        cls.kid = "fixture-fase3"
        cls.jwk = {"kty": "RSA", "alg": "RS256", "use": "sig", "kid": cls.kid,
                   "n": _b64(cls.n.to_bytes((cls.n.bit_length() + 7) // 8, "big")),
                   "e": _b64(cls.e.to_bytes((cls.e.bit_length() + 7) // 8, "big"))}

    @classmethod
    def token(cls, *, claims=None, kid=None, alterada=False):
        cabecalho = {"alg": "RS256", "kid": kid or cls.kid, "typ": "JWT"}
        payload = {"iss": "https://equipe.cloudflareaccess.com", "aud": ["audiencia-app"],
                   "sub": "usuario-123", "email": "Equipe@Example.com", "exp": 2000, "nbf": 900}
        payload.update(claims or {})
        partes = (_b64(json.dumps(cabecalho, separators=(",", ":")).encode()),
                  _b64(json.dumps(payload, separators=(",", ":")).encode()))
        mensagem = (partes[0] + "." + partes[1]).encode("ascii")
        digest_info = _SHA256_DIGEST_INFO + hashlib.sha256(mensagem).digest()
        tamanho = (cls.n.bit_length() + 7) // 8
        em = b"\x00\x01" + b"\xff" * (tamanho - len(digest_info) - 3) + b"\x00" + digest_info
        assinatura = pow(int.from_bytes(em, "big"), cls.d, cls.n).to_bytes(tamanho, "big")
        if alterada:
            assinatura = bytes([assinatura[0] ^ 1]) + assinatura[1:]
        return ".".join((*partes, _b64(assinatura)))

    def autenticador(self, carga=None):
        chamadas = []

        def loader(url):
            chamadas.append(url)
            return carga or {"keys": [type(self).jwk]}

        return AutenticadorCloudflare("https://equipe.cloudflareaccess.com", "audiencia-app",
                                      loader=loader, relogio=lambda: 1000,
                                      monotonic=lambda: 10), chamadas

    def test_autentica_assinatura_e_usa_somente_claims_assinados(self):
        auth, chamadas = self.autenticador()
        identidade = auth.autenticar({"Cf-Access-Jwt-Assertion": self.token(),
                                      "Cf-Access-Authenticated-User-Email": "falsario@example.net"})
        self.assertEqual(identidade.email, "equipe@example.com")
        self.assertEqual(identidade.subject, "usuario-123")
        self.assertEqual(len(chamadas), 1)

    def test_rejeita_ausencia_assinatura_invalida_e_kid_desconhecido(self):
        auth, _ = self.autenticador()
        with self.assertRaises(AcessoNegado):
            auth.autenticar({})
        with self.assertRaises(AcessoNegado):
            auth.autenticar({"Cf-Access-Jwt-Assertion": self.token(alterada=True)})
        auth, chamadas = self.autenticador()
        with self.assertRaises(AcessoNegado):
            auth.autenticar({"Cf-Access-Jwt-Assertion": self.token(kid="chave-estranha")})
        self.assertEqual(len(chamadas), 2)  # Atualização única ao encontrar uma chave nova.

    def test_rejeita_issuer_audiencia_e_validade_incorretos(self):
        casos = [({"iss": "https://outra.cloudflareaccess.com"}, 1000),
                 ({"aud": ["outra-app"]}, 1000),
                 ({"exp": 999}, 1000),
                 ({"exp": float("nan")}, 1000),
                 ({"nbf": 1001}, 1000),
                 ({"nbf": float("nan")}, 1000),
                 ({"email": "", "sub": ""}, 1000)]
        for claims, _ in casos:
            with self.subTest(claims=claims):
                auth, _ = self.autenticador()
                with self.assertRaises(AcessoNegado):
                    auth.autenticar({"Cf-Access-Jwt-Assertion": self.token(claims=claims)})

    def test_configuracao_protegida_exige_dominio_e_audiencia(self):
        with self.assertRaises(ConfiguracaoAcessoInvalida):
            AutenticadorCloudflare("http://equipe.cloudflareaccess.com", "audiencia-app")
        with self.assertRaises(ConfiguracaoAcessoInvalida):
            AutenticadorCloudflare("https://equipe.cloudflareaccess.com", "")


if __name__ == "__main__":
    unittest.main()
