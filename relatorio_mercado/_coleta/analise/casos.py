#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
casos.py -- gera casos.jsonl (uma linha por compra detalhada) a partir dos
arquivos de W/compras/*.json (formato gravado por coletor.py, fase 3/4).

So LE arquivos; nunca escreve em compras/, textos/, *hits*.jsonl,
selecao.jsonl ou stats.json.

Uso:
    python3 casos.py                         # roda em cima de W/compras (producao)
    python3 casos.py --raiz W/_teste_validacao --saida casos_teste.jsonl
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C


def _get(d, *keys, default=None):
    for k in keys:
        if d is None:
            return default
        d = d.get(k) if isinstance(d, dict) else None
    return default if d is None else d


def carrega_texto(textos_dir, caso_id):
    path = os.path.join(textos_dir, f"{caso_id}.txt")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def monta_caso(registro, caso_id, texto):
    hit = registro.get("hit") or {}
    detalhe = registro.get("detalhe")
    itens = registro.get("itens") or []
    resultados = registro.get("resultados") or {}
    areas = registro.get("areas") or []

    if detalhe is None:
        return None  # sem detalhe, nao da pra analisar (erro na coleta)

    objeto = detalhe.get("objetoCompra") or hit.get("description") or ""

    uf = _get(detalhe, "unidadeOrgao", "ufSigla") or hit.get("uf")
    municipio = _get(detalhe, "unidadeOrgao", "municipioNome") or hit.get("municipio_nome")
    orgao = _get(detalhe, "orgaoEntidade", "razaoSocial") or hit.get("orgao_nome")
    esfera_id = _get(detalhe, "orgaoEntidade", "esferaId")
    esfera = C.ESFERA_MAP.get(esfera_id) or hit.get("esfera_nome")
    data_publicacao = detalhe.get("dataPublicacaoPncp") or hit.get("data_publicacao_pncp")
    modalidade = detalhe.get("modalidadeNome") or hit.get("modalidade_licitacao_nome")
    srp = detalhe.get("srp")

    # -------------------- valores --------------------
    valor_estimado_total = C.as_float(detalhe.get("valorTotalEstimado"))
    soma_itens_estimado = sum(
        C.as_float(it.get("valorTotal")) or 0.0 for it in itens if C.as_float(it.get("valorTotal")) is not None
    )
    if valor_estimado_total is None:
        valor_estimado_total = soma_itens_estimado if itens else None

    # itens "com resultado" = mesmo conjunto para o qual coletor.py buscou
    # resultados (temResultado True); restringe aos numeros de item que de
    # fato aparecem no dicionario 'resultados' (cobre o caso de truncamento
    # por MAX_ITENS_RESULTADO).
    chaves_com_resultado = set(resultados.keys())
    itens_com_resultado = [
        it for it in itens
        if it.get("temResultado") and str(it.get("numeroItem")) in chaves_com_resultado
    ]
    estimado_dos_itens_com_resultado = None
    if itens_com_resultado:
        vals = [C.as_float(it.get("valorTotal")) for it in itens_com_resultado]
        vals = [v for v in vals if v is not None]
        estimado_dos_itens_com_resultado = sum(vals) if vals else None

    # soma dos resultados: None so quando nao ha NENHUM item com resultado
    # (dicionario 'resultados' vazio); se houver itens com resultado mas o
    # valor homologado deles somar zero (ex.: todos desertos/fracassados),
    # o zero e legitimo e nao deve cair no fallback do detalhe.
    if resultados:
        soma_resultados = 0.0
        for lista in resultados.values():
            for r in (lista or []):
                v = C.as_float(r.get("valorTotalHomologado"))
                if v is not None:
                    soma_resultados += v
    else:
        soma_resultados = None

    valor_homologado_total = soma_resultados
    if valor_homologado_total is None:
        valor_homologado_total = C.as_float(detalhe.get("valorTotalHomologado"))

    # Desconto pela soma dos totais (sensível a SRP com vários fornecedores registrados
    # no mesmo item e a quantidades homologadas parciais).
    desconto_total = None
    if (
        estimado_dos_itens_com_resultado is not None
        and estimado_dos_itens_com_resultado > 0
        and valor_homologado_total is not None
    ):
        desconto_total = 1.0 - (valor_homologado_total / estimado_dos_itens_com_resultado)

    # Desconto principal: preço unitário do 1º colocado de cada item contra o unitário
    # estimado, ponderado pelo valor estimado do item.
    itens_por_num = {str(it.get("numeroItem")): it for it in itens}
    num = den = 0.0
    for chave, lista in resultados.items():
        it = itens_por_num.get(str(chave))
        validos = [r for r in (lista or []) if not r.get("dataCancelamento")]
        if not it or not validos:
            continue
        primeiro = sorted(validos, key=lambda r: (r.get("ordemClassificacaoSrp") or 1,
                                                  r.get("sequencialResultado") or 1))[0]
        ue = C.as_float(it.get("valorUnitarioEstimado"))
        uh = C.as_float(primeiro.get("valorUnitarioHomologado"))
        peso = C.as_float(it.get("valorTotal")) or 0.0
        if ue and ue > 0 and uh is not None and peso > 0:
            num += peso * (1.0 - uh / ue)
            den += peso
    desconto_unitario = (num / den) if den > 0 else None

    desconto = desconto_unitario if desconto_unitario is not None else desconto_total
    desconto_suspeito = desconto is not None and (desconto < 0 or desconto > 0.9)

    # -------------------- itens / situacao --------------------
    n_itens = len(itens)
    n_homologados = n_desertos = n_fracassados = n_anulados_cancelados = n_outros_status = 0
    for it in itens:
        st = C.norm(it.get("situacaoCompraItemNome"))
        if "homologad" in st:
            n_homologados += 1
        elif "deserto" in st:
            n_desertos += 1
        elif "fracassad" in st:
            n_fracassados += 1
        elif "cancelad" in st or "anulad" in st or "revogad" in st:
            n_anulados_cancelados += 1
        else:
            n_outros_status += 1
    houve_deserta_ou_fracassada = n_desertos > 0 or n_fracassados > 0

    # -------------------- ME/EPP --------------------
    tipos_beneficio = [it.get("tipoBeneficio") for it in itens if it.get("tipoBeneficio") is not None]
    exclusiva_total = bool(tipos_beneficio) and all(tb == 1 for tb in tipos_beneficio)
    exclusiva_parcial = any(tb == 1 for tb in tipos_beneficio) and not exclusiva_total
    cota = any(tb == 3 for tb in tipos_beneficio)
    aplicou_beneficio_meepp = any(
        bool(r.get("aplicacaoBeneficioMeEpp"))
        for lista in resultados.values()
        for r in (lista or [])
    )

    # -------------------- vencedores --------------------
    vencedores_dedup = {}
    houve_pessoa_fisica = False
    for lista in resultados.values():
        for r in (lista or []):
            ni = r.get("niFornecedor")
            tipo_pessoa = (r.get("tipoPessoa") or "").upper()
            razao = r.get("nomeRazaoSocialFornecedor")
            if ni:
                if ni not in vencedores_dedup:
                    vencedores_dedup[ni] = {
                        "razao_social": razao,
                        "porte": r.get("porteFornecedorNome"),
                    }
            elif tipo_pessoa in ("PF", "F") or razao == "pessoa fisica":
                houve_pessoa_fisica = True
    vencedores = list(vencedores_dedup.values())
    if houve_pessoa_fisica:
        vencedores.append({"razao_social": "pessoa física", "porte": None})
    n_fornecedores_vencedores = len(vencedores_dedup) + (1 if houve_pessoa_fisica else 0)

    # -------------------- participantes / tipo contrato / vigencia --------------------
    n_participantes = C.extrai_n_participantes(texto)
    tipo_contrato = C.classifica_tipo_contrato(objeto, itens, texto)
    vigencia_meses = C.extrai_vigencia_meses(objeto, texto)

    # -------------------- exigencias --------------------
    exigencias = C.extrai_exigencias(texto)

    # -------------------- frac_material --------------------
    total_itens_valor = sum(
        v for v in (C.as_float(it.get("valorTotal")) for it in itens) if v is not None
    )
    total_material_valor = sum(
        v for it in itens
        if C.tipo_item(it) == "M"
        for v in [C.as_float(it.get("valorTotal"))]
        if v is not None
    )
    frac_material = (total_material_valor / total_itens_valor) if total_itens_valor > 0 else None

    # -------------------- area_principal --------------------
    principal = C.area_principal(objeto, areas)

    # -------------------- exclusao --------------------
    exclusao = C.avalia_exclusao(objeto, itens, valor_estimado_total, frac_material)
    if not exclusao["revisao_manual"]:
        # sinaliza tambem quando faltam dados criticos para as contas principais
        if valor_estimado_total is None or (itens_com_resultado and desconto is None):
            exclusao = dict(exclusao)
            exclusao["revisao_manual"] = True

    caso = {
        "id": caso_id,
        "link_pncp": registro.get("link_pncp"),
        "data_acesso": registro.get("data_acesso"),
        "uf": uf,
        "municipio": municipio,
        "orgao": orgao,
        "esfera": esfera,
        "data_publicacao": data_publicacao,
        "modalidade": modalidade,
        "objeto": objeto,
        "srp": srp,
        "escopo": registro.get("escopo"),  # "GO" ou a UF vizinha (DF/MT/MS/TO/MG)
        "areas": sorted(areas),
        "area_principal": principal,
        "valor_estimado_total": valor_estimado_total,
        "valor_homologado_total": valor_homologado_total,
        "estimado_dos_itens_com_resultado": estimado_dos_itens_com_resultado,
        "desconto_unitario": desconto_unitario,
        "desconto_total": desconto_total,
        "desconto": desconto,
        "desconto_suspeito": desconto_suspeito,
        "itens": {
            "n_itens": n_itens,
            "n_com_resultado": len(itens_com_resultado),
            "n_homologados": n_homologados,
            "n_desertos": n_desertos,
            "n_fracassados": n_fracassados,
            "n_anulados_cancelados": n_anulados_cancelados,
            "n_outros_status": n_outros_status,
            "houve_deserta_ou_fracassada": houve_deserta_ou_fracassada,
            "itens_truncados": bool(registro.get("itens_truncados")),
        },
        "me_epp": {
            "exclusiva_total": exclusiva_total,
            "exclusiva_parcial": exclusiva_parcial,
            "cota": cota,
            "aplicou_beneficio_meepp": aplicou_beneficio_meepp,
        },
        "n_fornecedores_vencedores": n_fornecedores_vencedores,
        "vencedores": vencedores,
        "n_participantes": n_participantes,
        "tipo_contrato": tipo_contrato,
        "vigencia_meses": vigencia_meses,
        "exigencias": exigencias,
        "frac_material": frac_material,
        "exclusao": exclusao,
    }
    return caso


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default=C.W,
                    help="pasta com compras/ e textos/ (default: W, producao). "
                         "Use W/_teste_validacao para a amostra de teste.")
    ap.add_argument("--saida", default=None,
                    help="arquivo de saida .jsonl (default: casos.jsonl, ou "
                         "casos_teste.jsonl se --raiz apontar para _teste_validacao)")
    args = ap.parse_args()

    raiz = os.path.abspath(args.raiz)
    paths = C.raiz_paths(raiz)
    compras_dir = paths["compras_dir"]
    textos_dir = paths["textos_dir"]

    if args.saida:
        saida = args.saida if os.path.isabs(args.saida) else os.path.join(C.ANALISE_DIR, args.saida)
    else:
        eh_teste = os.path.normpath(raiz) == os.path.normpath(C.TESTE_DIR)
        saida = os.path.join(C.ANALISE_DIR, "casos_teste.jsonl" if eh_teste else "casos.jsonl")

    arquivos = sorted(glob.glob(os.path.join(compras_dir, "*.json")))
    print(f"[casos.py] raiz={raiz}")
    print(f"[casos.py] {len(arquivos)} arquivo(s) em {compras_dir}")

    n_ok = 0
    n_sem_detalhe = 0
    n_erro = 0
    with open(saida, "w", encoding="utf-8") as fout:
        for path in arquivos:
            caso_id = os.path.splitext(os.path.basename(path))[0]
            try:
                with open(path, "r", encoding="utf-8") as f:
                    registro = json.load(f)
            except Exception as e:
                print(f"[casos.py] AVISO: falha ao ler {path}: {e}", file=sys.stderr)
                n_erro += 1
                continue

            if registro.get("detalhe") is None:
                n_sem_detalhe += 1
                continue

            texto = carrega_texto(textos_dir, caso_id)
            try:
                caso = monta_caso(registro, caso_id, texto)
            except Exception as e:
                print(f"[casos.py] AVISO: falha ao montar caso {caso_id}: {e}", file=sys.stderr)
                n_erro += 1
                continue

            if caso is None:
                n_sem_detalhe += 1
                continue

            fout.write(json.dumps(caso, ensure_ascii=False) + "\n")
            n_ok += 1

    print(f"[casos.py] casos gravados: {n_ok}")
    print(f"[casos.py] sem detalhe (erro na coleta, ignorados): {n_sem_detalhe}")
    print(f"[casos.py] erros de processamento: {n_erro}")
    print(f"[casos.py] saida: {saida}")


if __name__ == "__main__":
    main()
