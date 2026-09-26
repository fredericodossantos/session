"""Catálogo versionado de setores e adaptadores puros de filtros."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

VERSAO_SCHEMA_FILTROS = 2
VERSAO_CATALOGO_PADRAO = "1"
_RAIZ = Path(__file__).resolve().parent.parent


class ErroCatalogo(ValueError):
    """Catálogo malformado ou referência inválida."""


def carregar_catalogo(caminho: str | Path | None = None) -> "Catalogo":
    """Carrega e valida o catálogo YAML. O padrão é o arquivo ao lado de config.yaml."""
    path = Path(caminho) if caminho is not None else _RAIZ / "catalogo_areas.yaml"
    try:
        bruto = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ErroCatalogo(f"Não foi possível ler o catálogo {path}: {exc}") from exc
    if not isinstance(bruto, dict):
        raise ErroCatalogo("A raiz do catálogo deve ser um mapa")
    return Catalogo(bruto)


class Catalogo:
    def __init__(self, dados: dict[str, Any]):
        self.dados = deepcopy(dados)
        self.versao = str(dados.get("versao", "")).strip()
        if not self.versao:
            raise ErroCatalogo("Catálogo sem versão")
        for secao in ("setores", "servicos", "contextos", "perfis", "presets"):
            if not isinstance(dados.get(secao), list):
                raise ErroCatalogo(f"Catálogo: '{secao}' deve ser uma lista")
        self._indices: dict[str, dict[str, dict[str, Any]]] = {}
        for secao in ("setores", "servicos", "contextos", "perfis", "presets"):
            self._indices[secao] = self._indexar(secao, dados[secao])
        self._validar()

    @staticmethod
    def _indexar(nome: str, itens: list[dict]) -> dict[str, dict[str, Any]]:
        indice: dict[str, dict[str, Any]] = {}
        for item in itens:
            if not isinstance(item, dict):
                raise ErroCatalogo(f"Catálogo: item inválido em '{nome}'")
            ident = item.get("id")
            if not isinstance(ident, str) or not ident.strip():
                raise ErroCatalogo(f"Catálogo: item sem id em '{nome}'")
            if ident in indice:
                raise ErroCatalogo(f"Catálogo: id repetido em '{nome}': {ident}")
            if not isinstance(item.get("rotulo"), str) or not item["rotulo"].strip():
                raise ErroCatalogo(f"Catálogo: '{ident}' sem rótulo")
            indice[ident] = item
        return indice

    def _validar(self) -> None:
        servicos = self._indices["servicos"]
        setores = self._indices["setores"]
        for sid, setor in setores.items():
            termos = setor.get("termos", [])
            grupos = setor.get("grupos_obrigatorios", [])
            if not termos and not grupos and not setor.get("rotas") and not setor.get("permitir_generico"):
                raise ErroCatalogo(f"Setor '{sid}' não tem evidência de correspondência")
            self._validar_grupos(sid, termos, grupos)
            for rota in setor.get("rotas", []):
                if not isinstance(rota, dict):
                    raise ErroCatalogo(f"Rota de evidência inválida em '{sid}'")
                self._validar_grupos(sid, [], rota.get("grupos_obrigatorios", []))
            for servico in (setor.get("servicos_excecao") or {}):
                if servico not in servicos:
                    raise ErroCatalogo(f"Setor '{sid}' referencia serviço inexistente '{servico}'")
            vistos: set[str] = set()
            for sub in setor.get("subareas", []):
                if not isinstance(sub, dict) or not isinstance(sub.get("id"), str):
                    raise ErroCatalogo(f"Subárea inválida no setor '{sid}'")
                if sub["id"] in vistos:
                    raise ErroCatalogo(f"Subárea repetida no setor '{sid}': {sub['id']}")
                vistos.add(sub["id"])
                if not sub.get("termos") and not sub.get("grupos_obrigatorios"):
                    raise ErroCatalogo(f"Subárea '{sub['id']}' não tem evidência")
                self._validar_grupos(sub["id"], sub.get("termos", []),
                                     sub.get("grupos_obrigatorios", []))
        for nome in ("servicos", "contextos"):
            for ident, item in self._indices[nome].items():
                if not item.get("termos"):
                    raise ErroCatalogo(f"{nome[:-1].capitalize()} '{ident}' sem termos")
        for nome in ("perfis", "presets"):
            for ident, item in self._indices[nome].items():
                for sid in item.get("setores", []):
                    if sid not in setores:
                        raise ErroCatalogo(f"{nome[:-1].capitalize()} '{ident}' referencia setor inexistente '{sid}'")
                for servico in item.get("servicos", []):
                    if servico not in servicos:
                        raise ErroCatalogo(f"Preset '{ident}' referencia serviço inexistente '{servico}'")
                if item.get("perfil") and item["perfil"] not in self._indices["perfis"]:
                    raise ErroCatalogo(f"Preset '{ident}' referencia perfil inexistente '{item['perfil']}'")

    @staticmethod
    def _validar_grupos(ident: str, termos: Any, grupos: Any) -> None:
        if not isinstance(termos, list) or any(not isinstance(t, str) or not t.strip() for t in termos):
            raise ErroCatalogo(f"Evidências inválidas em '{ident}'")
        if not isinstance(grupos, list) or any(not isinstance(g, list) or not g or
                                                any(not isinstance(t, str) or not t.strip() for t in g)
                                                for g in grupos):
            raise ErroCatalogo(f"Grupos de evidência inválidos em '{ident}'")

    def validar_ids(self, secao: str, ids: list[str] | None, permitir_vazio: bool = True) -> list[str]:
        if secao not in self._indices:
            raise ErroCatalogo(f"Dimensão desconhecida: {secao}")
        if ids is None:
            ids = []
        if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
            raise ErroCatalogo(f"'{secao}' deve ser uma lista de IDs")
        if not permitir_vazio and not ids:
            raise ErroCatalogo(f"Selecione ao menos um item em '{secao}'")
        if len(set(ids)) != len(ids):
            raise ErroCatalogo(f"IDs repetidos em '{secao}'")
        desconhecidos = [i for i in ids if i not in self._indices[secao]]
        if desconhecidos:
            raise ErroCatalogo(f"IDs desconhecidos em '{secao}': {', '.join(desconhecidos)}")
        return list(ids)

    def publico(self) -> dict[str, Any]:
        """Formato estável e sem regras internas para GET /api/options."""
        setores = []
        for setor in self.dados["setores"]:
            setores.append({"id": setor["id"], "rotulo": setor["rotulo"],
                            "grupo": setor.get("grupo", "geral"),
                            "subareas": [{"id": s["id"], "rotulo": s["rotulo"]}
                                         for s in setor.get("subareas", [])]})
        resposta: dict[str, Any] = {
            "versao": self.versao,
            "setores": setores,
            "servicos": [{"id": x["id"], "rotulo": x["rotulo"]} for x in self.dados["servicos"]],
            "contextos": [{"id": x["id"], "rotulo": x["rotulo"]} for x in self.dados["contextos"]],
            "perfis": [{"id": x["id"], "rotulo": x["rotulo"], "setores": list(x.get("setores", []))}
                       for x in self.dados["perfis"]],
            "presets": [{k: deepcopy(v) for k, v in x.items() if k in {"id", "rotulo", "setores", "servicos", "perfil"}}
                        for x in self.dados["presets"]],
            "palavras_chave": deepcopy(self.dados.get("palavras_chave", {"modo": "frase_literal_qualquer"})),
        }
        return resposta

    def setor(self, ident: str) -> dict[str, Any]:
        return self._indices["setores"][ident]

    def servico(self, ident: str) -> dict[str, Any]:
        return self._indices["servicos"][ident]

    def contexto(self, ident: str) -> dict[str, Any]:
        return self._indices["contextos"][ident]


def migrar_filtros_v1(filtros: dict[str, Any]) -> dict[str, Any]:
    """Adapta um filtro antigo sem I/O e preserva OU entre critérios de ``areas``.

    A expressão antiga não cabe sempre no AND entre dimensões do formato v2;
    ``compatibilidade_v1.alternativas`` mantém seus ramos até conversão explícita.
    """
    if not isinstance(filtros, dict):
        raise ValueError("Filtros devem ser um mapa")
    if filtros.get("schema_version", 1) != 1:
        raise ValueError("A migração v1 aceita apenas filtros sem versão ou schema_version=1")
    original = deepcopy(filtros)
    areas = original.get("areas") or []
    if not isinstance(areas, list) or any(not isinstance(a, str) for a in areas):
        raise ValueError("'areas' legado deve ser uma lista de textos")
    servicos_antigos = {"instalacao", "manutencao", "fornecimento", "pecas"}
    alternativas: list[dict[str, list[str]]] = []
    if not areas:
        alternativas.append({"setores": ["climatizacao"], "servicos": []})
    else:
        for area in areas:
            if area in servicos_antigos:
                alternativas.append({"setores": ["climatizacao"], "servicos": [area]})
            elif area in {"pmoc", "refrigeracao"}:
                alternativas.append({"setores": [area], "servicos": []})
            else:
                # Área v1 era texto literal. Mantê-la como critério antigo é mais
                # seguro do que adivinhar um setor e ampliar a busca.
                alternativas.append({"termo_literal": [area]})
    convertido = {k: deepcopy(v) for k, v in original.items()
                  if k not in {"areas", "schema_version", "catalogo_versao"}}
    convertido.update({"schema_version": VERSAO_SCHEMA_FILTROS,
                       "catalogo_versao": VERSAO_CATALOGO_PADRAO,
                       "setores": [], "subareas": {}, "servicos": [], "contextos": [],
                       "perfil": None, "incluir_predial_generico": False,
                       "compatibilidade_v1": {"alternativas": alternativas,
                                                "palavras_chave": deepcopy(original.get("palavras_chave", [])),
                                                "filtro_original": original}})
    return convertido


# Nome curto mantido para consumidores que prefiram o infinitivo do contrato.
migrar_filtros = migrar_filtros_v1
