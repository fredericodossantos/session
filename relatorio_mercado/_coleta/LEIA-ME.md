# Dados brutos do estudo de mercado (PNCP, set/2024 a set/2026)

Todos os arquivos foram coletados em 27/09/2026 na API pública do PNCP e em fontes de custo.
Eles servem para refazer o estudo ou fazer outras análises. Nenhum arquivo traz CPF: nos
resultados de fornecedor pessoa física, o nome e o documento foram removidos na coleta.

## Licitações (PNCP)

| Arquivo | Conteúdo |
|---|---|
| `go_hits.jsonl` | Índice de busca de Goiás: 6.026 editais únicos (um JSON por linha, com os campos da busca do PNCP e `area_termos`, os termos que o encontraram). |
| `viz_hits.jsonl` | Mesmo índice para DF, MT, MS, TO e MG (9.632 editais; até 3 páginas por termo). |
| `*_raw.jsonl` | Os mesmos índices antes da deduplicação, página a página. |
| `selecao.jsonl`, `selecao_suplementar.jsonl` | Triagem automática de cada edital por área: aceito ou rejeitado, e o motivo (dispensa, fora do período, sem resultado etc.). |
| `compras/{cnpj}_{ano}_{seq}.json` | **535 compras detalhadas.** Cada arquivo tem:<br>• `hit`: dados da busca; `origem: "suplementar"` na 2ª rodada;<br>• `detalhe`: valores estimado e homologado, modalidade, SRP, datas, órgão;<br>• `itens`: descrição, quantidade, unidade, valores, situação, `tipoBeneficio` ME/EPP;<br>• `resultados`: por número de item, com vencedor, valor e porte;<br>• `arquivos`: documentos do edital;<br>• `link_pncp` e `data_acesso`. |
| `textos/{cnpj}_{ano}_{seq}.txt` | Texto extraído do Termo de Referência ou do Edital (161 arquivos). As falhas estão em `textos/falhas.jsonl`. |
| `stats*.json`, `*.log`, `checkpoint*.json` | Contagens, logs e estado de retomada da coleta. |
| `coletor.py`, `coletor_suplementar.py` | Scripts da coleta: rodam de novo e retomam de onde pararam. Respeitam 1 requisição por segundo. |

**Endpoints usados:**
- busca: `https://pncp.gov.br/api/search/?q=...&tipos_documento=edital&status=encerradas&ufs=GO`;
- detalhe: `https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}`;
- itens e resultados: `https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens[/{n}/resultados]`.

## Custos de referência

A pasta `custos/` guarda os PDFs e planilhas originais:
- CCTs de GO: construção civil, SEAC/SEACONS e SETCEG;
- SINAPI (livro de encargos, fev/2026);
- GOINFRA T334;
- SICRO;
- ANP;
- Acórdão TCU 2622/2013;
- Lei 14.133;
- Código Tributário de Goiânia.

Os valores extraídos, com fonte, data de acesso e confiabilidade, estão em `custos/custos/referencias.json` (e `.md`).

## Análise

A pasta `analise/` contém:

- **Scripts, na ordem de execução:**
  1. `casos.py` → `casos.jsonl`: um caso por compra, com desconto, ME/EPP, deserta, exigências e heurística de exclusão;
  2. `consolidar.py` → `casos_final.jsonl`: aplica as decisões dos analistas, uma área por caso;
  3. `indicadores.py` → `indicadores_final.json` / `.md`;
  4. `planilha.py` → `estudo_mercado.xlsx`, com fórmulas conferidas no LibreOffice;
  5. `relatorio.py` → `relatorio_mercado.html`.
- **Revisões e premissas:**
  - `areas/*.json`, `areas/*.md`: revisão caso a caso de cada área (decisões, margens, investimento, exigências);
  - `PREMISSAS_COMUNS.md`: premissas de custo usadas nas margens;
  - `README.md`: esquema detalhado dos campos de `casos.jsonl`.

**Para outra análise:** leia os JSON de `compras/` direto, ou parta de `analise/casos_final.jsonl`, que já tem os campos calculados e a classificação revisada.
