# Pipeline de análise -- estudo de mercado de licitações (GO + vizinhos)

Este diretório (`W/analise/`) contém o pipeline que transforma os dados
brutos coletados do PNCP por `coletor.py` em casos analisados, indicadores
por área/UF e uma planilha `.xlsx` para leitura humana. **Só lê** dados de
`W/compras`, `W/textos`, `W/selecao.jsonl`, `W/go_hits.jsonl` e
`W/custos/custos/referencias.json` -- nunca escreve nem apaga nada nessas
pastas, e não interfere com o processo `coletor.py` (que pode continuar
rodando em paralelo).

## Arquivos

- `common.py` -- constantes, regexes e funções compartilhadas (não roda sozinho).
- `casos.py` -- gera `casos.jsonl` (um caso detalhado por linha).
- `indicadores.py` -- lê `casos.jsonl` + `selecao.jsonl` e gera `indicadores.json` / `indicadores.md`.
- `planilha.py` -- gera `planilha.xlsx` a partir de `casos.jsonl` + `indicadores.json` + `referencias.json`.

## Como rodar

Ordem: `casos.py` → `indicadores.py` → `planilha.py`.

### Contra a amostra de teste (`W/_teste_validacao`)

```bash
cd W/analise
python3 casos.py --raiz ../_teste_validacao --saida casos_teste.jsonl
python3 indicadores.py --casos casos_teste.jsonl \
    --selecao ../_teste_validacao/selecao.jsonl \
    --saida-prefixo indicadores_teste
python3 planilha.py --casos casos_teste.jsonl \
    --indicadores indicadores_teste.json \
    --saida planilha_teste.xlsx
```

### Contra os dados reais (`W/compras`, produção -- pode rodar mesmo com o
coletor ainda em andamento; nesse caso reflete apenas o que já foi
coletado até o momento)

```bash
cd W/analise
python3 casos.py            # le W/compras, grava casos.jsonl
python3 indicadores.py      # le casos.jsonl + W/selecao.jsonl, grava indicadores.json/.md
python3 planilha.py         # le casos.jsonl + indicadores.json + referencias.json, grava planilha.xlsx
```

Quando a coleta terminar (ou a qualquer momento, para acompanhar o
progresso), basta rodar os três scripts de novo sem argumentos: eles
releem tudo do zero e sobrescrevem as saídas em `W/analise/`.

`planilha.py` tenta recalcular a planilha gerada com `soffice --headless`
(LibreOffice) e compara cada célula de `indicadores_por_area` com
`indicadores.json`, imprimindo `N OK, M divergentes`. Se o LibreOffice não
estiver instalado, ele avisa e pula a validação (a planilha ainda é
gerada normalmente; abra num Excel/Calc real para conferir as fórmulas).
Rodando neste ambiente (LibreOffice 24.2), a validação bateu 100% tanto na
amostra de teste quanto nos casos reais já coletados (168 células
conferidas, 0 divergências, nas duas rodadas).

## Esquema de `casos.jsonl` (um objeto JSON por linha)

| campo | tipo | descrição |
|---|---|---|
| `id` | string | `cnpj_ano_seq` (nome do arquivo em `W/compras`) |
| `link_pncp` | string | link público da compra no PNCP |
| `data_acesso` | string (ISO) | quando o `coletor.py` baixou o detalhe |
| `uf`, `municipio`, `orgao`, `esfera` | string | do detalhe da compra (com *fallback* pro hit do índice) |
| `data_publicacao` | string (ISO) | `dataPublicacaoPncp` |
| `modalidade` | string | nome da modalidade de licitação |
| `objeto` | string | `objetoCompra` completo |
| `srp` | bool | se é sistema de registro de preços |
| `escopo` | string | `"GO"` ou a UF vizinha (`DF`/`MT`/`MS`/`TO`/`MG`) em que o caso foi coletado |
| `areas` | list[string] | todas as áreas em que o caso bateu na fase de índice do `coletor.py` |
| `area_principal` | string\|null | uma única área, por prioridade de regex (ver abaixo) |
| `valor_estimado_total` | float\|null | `valorTotalEstimado` do detalhe, ou soma dos itens se vier nulo |
| `valor_homologado_total` | float\|null | soma de `valorTotalHomologado` de todos os resultados, ou `valorTotalHomologado` do detalhe se não houver nenhum resultado |
| `estimado_dos_itens_com_resultado` | float\|null | soma de `valorTotal` (estimado) só dos itens que aparecem no dicionário de resultados (mesmo recorte usado no `valor_homologado_total`, inclusive quando `itens_truncados=true`) |
| `desconto` | float\|null | `1 - homologado/estimado_dos_itens_com_resultado`, comparando só o recorte de itens com resultado |
| `desconto_suspeito` | bool | `true` se `desconto < 0` ou `> 0.9` |
| `itens` | object | `n_itens`, `n_com_resultado`, `n_homologados`, `n_desertos`, `n_fracassados`, `n_anulados_cancelados`, `n_outros_status`, `houve_deserta_ou_fracassada`, `itens_truncados` |
| `me_epp` | object | `exclusiva_total` (todo item `tipoBeneficio==1`), `exclusiva_parcial` (mistura), `cota` (algum item `tipoBeneficio==3`), `aplicou_beneficio_meepp` (algum resultado com `aplicacaoBeneficioMeEpp=true`) |
| `n_fornecedores_vencedores` | int | nº de fornecedores distintos (PJ por CNPJ + 1 se houve alguma pessoa física -- ver limitação abaixo) |
| `vencedores` | list[{razao_social, porte}] | fornecedores vencedores; pessoa física aparece só como `{"razao_social": "pessoa física", "porte": null}`, sem nome nem CPF |
| `n_participantes` | int\|null | extraído do texto do edital/TR por regex (o PNCP não publica esse número); quase sempre `null` |
| `tipo_contrato` | `"continuado"`\|`"pontual"`\|`"indefinido"` | heurística sobre objeto+itens+texto |
| `vigencia_meses` | int\|null | extraído por regex do objeto/texto |
| `exigencias` | object | ver abaixo -- só preenchido quando há texto do edital/TR baixado (`tem_texto`) |
| `frac_material` | float\|null | fração do valor estimado dos itens que é material (não serviço) |
| `exclusao` | object | `motivo` (`null` ou um dos 4 motivos), `evidencia` (trecho), `revisao_manual` (bool) |

### `exigencias` (sub-objeto)

- `tem_texto`: bool -- se havia `.txt` do edital/TR para este caso.
- `cesto_aereo`, `munck_guindauto`, `aceita_munck_com_cesto`,
  `pmoc_responsavel_tecnico`, `crea_cft`: cada um é
  `{"valor": bool, "evidencia": trecho|null}` (trecho ≤ 300 caracteres).
- `frota_minima`, `atestados`: cada um é `{"trecho": trecho|null}` (o
  próprio trecho já serve de sinal + evidência).

### `area_principal` -- prioridade

Quando o objeto bate em mais de uma regex de área, a ordem de prioridade
(mais específico → mais genérico) é:
`munck > iluminacao_publica > refrigeracao > climatizacao > eletrica_predial > manutencao_predial`.
Se nada bater no objeto, cai para a primeira área da lista `areas` (na
mesma ordem de prioridade).

### `exclusao.motivo` -- ordem de avaliação

1. `mencao_passagem` -- objeto fala de veículo/ônibus/ambulância, ou de
   gerador/ar-condicionado só "de passagem" num evento.
2. `fornecimento_puro` -- todos os itens são material (usa
   `materialOuServicoNome` como critério, corrigindo o código
   `materialOuServico` quando os dois discordam -- ver limitações).
3. `obra_grande` -- objeto sugere implantação/construção/ampliação de
   rede **e** valor estimado > R$ 1,5 milhão.
4. `equipamento_alto` -- objeto menciona gerador, subestação
   nova/completa, chiller, VRF, central de água gelada, usina/energia
   solar, **ou** a fração em material (`frac_material`) > 40%.

Se nenhum motivo bater, `motivo` fica `null` (caso incluído). `revisao_manual`
é ligado à parte, em qualquer caso, quando: a fração de material fica
entre 30% e 40% (zona cinzenta), o objeto fala de "manutenção/serviço" mas
todos os itens foram classificados como material (conflito de sinal),
faltam itens para avaliar, o valor estimado está acima de 60% do limiar de
obra grande sem cruzar o limiar, ou faltam dados para calcular
`valor_estimado_total`/`desconto` quando havia itens com resultado.

## Indicadores (`indicadores.json` / `.md`)

Calculados **só com casos não excluídos** (`exclusao.motivo is null`), por
área e por grupo de UF (`"GO"` vs `"vizinhos"` = DF+MT+MS+TO+MG somados; o
arquivo também traz um detalhe por UF individual). Um caso que bate em mais
de uma área conta para cada uma (mesmo critério usado por `coletor.py` ao
gravar `selecao.jsonl`), para que `volume_ano_indice_aceitos` (vindo do
índice de busca) e `n_casos_detalhados` (vindo dos casos analisados) sejam
comparáveis.

- `volume_ano` = (nº de linhas `aceito=true` em `selecao.jsonl` para aquela
  área/grupo) ÷ 2 -- o período coletado é de ~24 meses (2024-09-27 a
  2026-09-27), então dividir por 2 anualiza.
- `ticket_mediano`, `desconto_mediana/q1/q3`, `mediana_participantes`:
  mediana e quartis pelo método "inclusive" (igual ao `QUARTILE.INC` /
  `PERCENTILE.INC` do Excel/Calc -- por isso batem com as fórmulas da
  planilha).
- `pct_*`: fração dos casos incluídos daquela área/grupo com a
  característica (deserta/fracassada, exclusiva ME/EPP, contínuo etc.).
- `exclusoes_por_area_motivo`: usa **todos** os casos (incluídos ou não).

## Planilha (`planilha.xlsx`)

- **dados_brutos**: um caso por linha (todas, incluídas ou não), link do
  PNCP como hiperlink, e uma coluna `incluido` (1/0) espelhando
  `exclusao.motivo is null`.
- **indicadores_por_area**: uma linha por (área, grupo_uf), com os mesmos
  indicadores de `indicadores.json` calculados **por fórmula do Excel**
  sobre `dados_brutos` (`SUMIFS`/`COUNTIFS` para somas/contagens/%, e
  `AGGREGATE(12,...)` / `AGGREGATE(17,...)` -- com o prefixo `_xlfn.`
  necessário para essas funções "novas" funcionarem tanto no Excel quanto
  no LibreOffice Calc quando o arquivo é escrito por `openpyxl` -- para
  mediana e quartis, ignorando erros/texto via divisão condicional). A
  coluna `volume_ano_indice` é a única exceção: vem copiada de
  `indicadores.json`, porque depende de `selecao.jsonl` (índice de busca),
  que não faz parte de `dados_brutos`.
- **exclusoes**: contagem por área e motivo, também por fórmula
  (`COUNTIFS`).
- **custos_referencia**: dump de `W/custos/custos/referencias.json`.
- **fontes**: URLs únicas de `referencias.json` + `data_acesso`.

## Limitações conhecidas das heurísticas

- **`n_participantes`**: o PNCP não publica esse número. Só é preenchido
  quando o texto do edital/TR menciona explicitamente algo como
  "participaram N empresas" -- na prática, quase sempre fica `null`.
- **`n_fornecedores_vencedores`** quando há pessoa física: o
  `coletor.py` já anonimiza pessoa física (não grava CNPJ/nome), então
  não dá para saber se duas ocorrências de "pessoa física" no mesmo caso
  são a mesma pessoa ou pessoas diferentes. A contagem soma **no máximo
  +1** para todas as pessoas físicas do caso (aproximação conservadora,
  documentada no próprio código).
- **`tipo_contrato`/`vigencia_meses`**: dependem de o texto do edital/TR
  ter sido baixado (`coletor.py` só baixa texto para as áreas
  `iluminacao_publica`, `munck`, `climatizacao`, `eletrica_predial`,
  `manutencao_predial` -- **não** para `refrigeracao`) e de a linguagem
  ser uma das reconhecidas pela regex. Muitos casos legitimamente
  contínuos vão cair em `"indefinido"` por falta de sinal textual.
- **`materialOuServico`**: o campo do PNCP às vezes está errado (ex.: um
  item de "Serviço de manutenção corretiva..." cadastrado com o código
  `M`/"Material" pelo próprio órgão). `tipo_item()` em `common.py` usa o
  texto de `materialOuServicoNome` para tentar corrigir o código quando
  os dois discordam, mas quando o órgão erra os dois campos ao mesmo
  tempo (como no exemplo acima) a heurística não tem como saber -- por
  isso o caso é sinalizado com `revisao_manual=true` quando o objeto fala
  de manutenção/serviço mas todos os itens vieram como material.
- **regex de exigências/área/tipo_contrato**: são baseadas em palavras-chave
  em português, sem normalização perfeita de acento em todos os casos (os
  trechos de evidência de `mencao_passagem`/`equipamento_alto` são
  extraídos do texto já sem acento, por simplicidade -- ainda legível,
  mas não é uma cópia literal do objeto original).
- **`obra_grande`**/**`equipamento_alto`**: limiares (R$ 1,5 milhão; 40%
  do valor em material) são os definidos no enunciado do estudo; casos
  perto do limiar (a partir de 60% dele) são sinalizados com
  `revisao_manual=true`.
- **Textos do PNCP ainda em coleta**: em produção, `W/textos` pode estar
  vazio ou parcial enquanto `coletor.py` roda (ele baixa texto na fase 4,
  depois de detalhar as compras na fase 3). Isso é normal e não é um bug
  do pipeline de análise -- rodar `casos.py`/`indicadores.py`/`planilha.py`
  de novo depois que a coleta avançar melhora a cobertura de
  `exigencias`/`tipo_contrato`/`n_participantes`.

## Teste realizado

- Amostra `_teste_validacao` (2 compras detalhadas): `casos_teste.jsonl`,
  `indicadores_teste.json/.md`, `planilha_teste.xlsx` -- gerados e
  conferidos (168/168 células de fórmula batendo com `indicadores.json`
  após recálculo no LibreOffice).
- Dados reais parciais em `W/compras` (coleta em andamento no momento do
  desenvolvimento): mesma bateria rodada sobre os casos já disponíveis,
  mesma conferência 100% ok. Um caso real revelou a inconsistência de
  `materialOuServico` descrita acima, o que levou ao ajuste de
  `tipo_item()`/`revisao_manual` documentado nesta seção.
