# Munck — estudo de mercado de licitações (GO + vizinhos)

Empresa-alvo: engenharia de GO com engenheiro mecânico e eletricista, técnicos/mecânicos de
refrigeração, eletricistas, **2 caminhões munck** e veículos leves. Foco em contratos de
mão de obra + deslocamento + materiais baratos, pagos por medição mensal, baixo investimento.

> **Atualização pós-coleta (27/09/2026):** o `coletor.py` terminou e `casos.jsonl` foi regerado
> (535 casos totais, antes 415), trazendo **19 casos novos de munck em MS/MG/TO** (UFs que antes
> não tinham nenhum caso detalhado) e populando `W/textos` para boa parte dos casos de GO. O
> campo `desconto` também mudou de definição (agora por **preço unitário do 1º colocado,
> ponderado pelo valor de cada item**; o método antigo ficou em `desconto_total`). Verificamos:
> **essa mudança de método não alterou nenhuma estatística de munck** (diferença máxima
> observada entre os dois métodos: 3×10⁻¹⁶, ruído de ponto flutuante — a maioria dos casos de
> munck tem 1 item por processo, onde os dois métodos coincidem por construção). Todas as
> seções abaixo já refletem a classificação e os indicadores atualizados; onde algo mudou de
> fato (por causa dos casos novos, não do método de desconto), isso está marcado com **NOVO**.

Fonte dos dados: `W/analise/casos.jsonl` (46 casos brutos de munck, GO + vizinhos),
`W/compras/{id}.json`, `W/custos/custos/referencias.json` e `W/analise/PREMISSAS_COMUNS.md`.
Arquivos intermediários desta atualização ficam em `W/analise/tmp_munck/` (scratch próprio,
para não conflitar com outros agentes trabalhando em paralelo no mesmo `W/analise/areas/`).

## 1. Revisão da classificação heurística

Dos 46 casos brutos (17 GO + 2 DF + 8 MT + **8 MS[NOVO]** + **8 MG[NOVO]** + **3 TO[NOVO]**),
revisamos manualmente **todos**, lendo objeto + itens de `W/compras/{id}.json` (e o texto do
edital, quando disponível). Resultado final: **25 incluídos (12 GO + 13 vizinhos)**, 21
excluídos.

Os 27 casos de GO/DF/MT já haviam sido revisados na rodada anterior (sem mudanças). Dos 19
casos novos (MS/MG/TO):

- **4 incluídos como locação pura de munck** (Alvorada-TO, Deodápolis-MS, São Lourenço-MG,
  e o item de munck dentro do RP de Três Pontas-SAAE-MG).
- **2 reclassificados de excluído→incluído**: obras pequenas de implantação de postes com
  fornecimento de material E mão de obra (Santa Rita do Pardo-MS, Rio Verde de Mato Grosso-MS),
  mesmo padrão do caso GO "Vila Propício" já usado como exemplar.
- **1 já corretamente incluído** pela heurística (Mundo Novo-MS, item coretamente codificado
  como Serviço).
- **1 reclassificado de incluído→excluído**: obra de urbanização geral (pavimentação, calçadas,
  paisagismo) de São Bento do Tocantins, onde iluminação/postes é item incidental dentro de uma
  obra civil ampla, não um serviço de munck.
- **11 confirmados como fora de escopo**: 2 casos de aquisição de **poliguindaste** (equipamento
  de guincho/basculamento para caçambas estacionárias de lixo — categoria diferente do
  guindauto/munck de içamento), 1 aquisição de caminhão zero-km com guindaste tipo Munck
  (compra de bem), 1 aquisição de acessórios de içamento (cintas/manilhas), 1 aquisição de
  containers com içamento só como logística de instalação, 1 obra de rede elétrica de média
  tensão (subestação/transformadores, não poste isolado), 1 obra de UBS com postes de iluminação
  incidentais, 1 obra grande de pavimentação com postes (>R$1,5 mi), 1 aquisição de blocos de
  concreto (a "alça de içamento" é característica do produto, não serviço), 1 aquisição de
  implementos agrícolas (guincho agrícola, equipamento diferente), 1 caso totalmente fora de
  escopo (materiais/medicamentos veterinários — falso positivo de indexação).

| Motivo de exclusão (confirmado após revisão) | GO | Vizinhos |
|---|---:|---:|
| `fornecimento_puro` | 2 | 7 |
| `fora_escopo` | 3 | 7 |
| `obra_grande` | 0 | 1 |
| `equipamento_alto` | 0 | 1 |
| **Total excluído** | **5** | **16** |

## 2. Indicadores finais (recalculados com a classificação revisada e o novo `desconto`)

| Indicador | GO | Vizinhos |
|---|---:|---:|
| Casos incluídos | 12 (sem mudança) | **13** (era 6) |
| Valor total estimado | R$ 4.789.966,65 | **R$ 9.981.951,77** (era R$ 8,27 mi) |
| Valor total homologado | R$ 2.862.049,99 | **R$ 8.555.418,89** |
| Ticket mediano (estimado) | R$ 200.606,40 | **R$ 237.792,00** (era R$ 1,26 mi — caiu bastante com os novos casos, que são majoritariamente contratos de munck puro de porte pequeno/médio, não frotas mistas gigantes) |
| Desconto — mediana | 14,0% (sem mudança) | **7,7%** (era 9,6%) |
| Desconto — Q1 | 5,1% | **3,0%** (era 7,9%) |
| Desconto — Q3 | 42,5% | **12,2%** (era 24,4%) |
| Descontos suspeitos descartados | 0 de 12 | 0 de 13 |
| % deserta/fracassada (nível de caso) | 0,0% | 0,0% |
| % exclusiva ME/EPP (total) | 0,0% | 7,7% |
| % exclusiva parcial ME/EPP | 0,0% | 15,4% |
| % continuado | 25,0%* | 7,7% |
| % pontual | 66,7%* | 69,2% |
| % indefinido | 8,3%* | 23,1% |

\* *Os percentuais de GO por tipo de contrato mudaram sensivelmente em relação à rodada anterior
(antes: 16,7% continuado / 16,7% pontual / 66,7% indefinido) — não por causa do método de
desconto, mas porque `W/textos` agora está populado para GO e o `tipo_contrato`/`vigencia_meses`
puderam ser extraídos do texto real do edital em vez de ficarem "indefinido" por falta de sinal.*

> **Nº de participantes:** confirmado null em **todos os 46 casos** (PNCP não publica).

> **O que mudou de fato (não é só o método de desconto):** o ticket mediano de vizinhos caiu de
> R$1,26 milhão para R$237.792 porque a amostra deixou de ser dominada por RPs de frota mista
> gigantes (Sapezal, Poxoréu, Juína-DAES) e passou a incluir vários contratos de munck puro de
> porte pequeno/médio em MS/MG/TO. O desconto mediano de vizinhos também caiu (9,6%→7,7%),
> refletindo esses contratos de item único e concorrência mais restrita (municípios pequenos).

### Preço unitário vencedor — hora/diária/mês de munck, vs. referências

| Categoria | GO — vencedor | Vizinhos — vencedor | Referência de mercado |
|---|---|---|---|
| Hora "produtiva"/operando | R$180,00 / R$295,00 / R$405,63 (mediana R$295,00, n=3, **sem mudança**) | **R$222,46 / R$222,46 / R$228,49 / R$288,00 / R$340,00 / R$390,00 / R$390,00 / R$429,00 (mediana R$314,00 [Q1 R$226,98; Q3 R$390,00], n=8 — era n=3, mediana R$222,46)** | GOINFRA (GO): R$213,33/h. SICRO E9690 (cesto, GO): R$330,89/h |
| Hora "improdutiva"/deslocamento | R$168,35 (n=1) | — | — |
| Diária (sem operador) | R$645,00 (n=1) | — | — |
| Mensal | mediana R$12.000 [Q1 R$9.883; Q3 R$19.639] (n=7, sem mudança) | R$34.333,33 (n=1, sem mudança) | — |
| Por operação (içamento pontual) | — | R$6.900 / R$7.300 / R$8.866,85 (n=3) | — |
| Outlier descartado | — | R$64,00/h (Juína-DAES, desconto de 85%) | — |

**NOVO:** a mediana da hora "produtiva" fora de GO **subiu de R$222,46/h para R$314,00/h** com a
chegada de casos de maior capacidade: **Deodápolis-MS** (munck/guindauto de **15 toneladas**,
R$429,00/h) e **São Lourenço-MG** (munck de **grande porte, 45 t/m, lança de 20 m**, R$390,00/h).
Isso confirma, com dado real, que quanto maior a capacidade exigida no edital, maior o preço por
hora — e sugere que a empresa deve mirar contratos compatíveis com a capacidade dos seus 2
caminhões (provavelmente porte médio, 8-12t), e não necessariamente os de maior valor/hora, que
também exigem equipamento mais caro. A mediana de vizinhos (R$314/h) agora fica **47% acima** do
GOINFRA e **95%** do SICRO-cesto — mais alta que a de GO (38% acima do GOINFRA).

## 3. Casos exemplares (GO) — sem mudança na lista, evidências enriquecidas

| Caso | Município | Resumo |
|---|---|---|
| [Goianésia](https://pncp.gov.br/app/editais/01065846000172/2026/584) | Goianésia | RP para 2 caminhões munck+cesto; **NOVO**: texto do edital confirma altura mínima do cesto de 13,5 m e exigência de eletricista com NR35/NR12/NR10/SEP além do motorista. |
| [Corumbaíba](https://pncp.gov.br/app/editais/01302603000100/2026/110) | Corumbaíba | Locação por hora, R$180,00/h homologado; combustível por conta da contratada. |
| [Santa Fé de Goiás](https://pncp.gov.br/app/editais/25107517000105/2025/304) | Santa Fé de Goiás | **NOVO**: o texto do edital confirma que os 2 itens ("hora produtiva"/R$405,63 e "hora improdutiva"/R$168,35) são a referência SICRO E9690 (CHP/CHI) citada literalmente na planilha do edital. |
| [Vila Propício](https://pncp.gov.br/app/editais/01612817000183/2025/830) | Vila Propício | Obra pequena de implantação de iluminação com substituição de postes; **NOVO**: texto confirma exigência de CREA/CAU para empresas de fora de GO (único caso de munck com essa exigência, por ser uma "obra"). |
| [Silvânia](https://pncp.gov.br/app/editais/01068030000100/2026/205) | Silvânia | RP com 2 itens/vencedores distintos (cesto relevante + coletor de lixo, ruído). |

## 4. Margem em casos típicos (caminhão PRÓPRIO)

As **premissas de custo não mudaram** nesta atualização (mesma mão de obra, diesel, BDI etc. da
rodada anterior — ver tabela completa no `.json`, campo `premissas_custo`). Custo direto de
referência (munck médio 8-12t, 120h/mês): **R$186,77/h**; lucro zero **R$219,55/h**; preço com
BDI **R$235,82/h**.

### Tabela de margem (5 casos da rodada anterior + 3 novos)

| Caso | Preço vencedor | Combustível por conta de | Classificação |
|---|---:|---|---|
| Corumbaíba (GO) | R$180,00/h | contratada | **Prejuízo provável** |
| Mineiros-SAAE (GO) | R$295,00/h | contratada | **Folgado** |
| Santa Fé de Goiás (GO) — produtiva | R$405,63/h | contratada | **Folgado** |
| Santa Fé de Goiás (GO) — improdutiva | R$168,35/h | contratada | **Prejuízo provável (marginal)** |
| Sapezal (MT) | R$340,00/h | não confirmado (conservador) | **Folgado** |
| Poxoréu (MT) | R$34.333,33/mês (≈R$195,08/h) | **MUNICÍPIO** | **Folgado (bem confortável)** |
| **[NOVO] Alvorada (TO)** | R$228,49/h | não verificado | **Apertado** (maior franquia da amostra: 983h) |
| **[NOVO] São Lourenço (MG)** | R$390,00/h | não verificado | **Folgado** (mas munck de 45 t/m — custo real provavelmente maior que o modelo de munck médio; folga real menor que a calculada) |
| **[NOVO] Deodápolis (MS)** | R$429,00/h | não verificado | **Folgado** (munck de 15t — mesma ressalva) |

**Isso muda alguma conclusão de margem/regra?** Não na direção geral (o piso de R$220/h com
combustível por conta da empresa, ou R$90/h quando é do contratante, continua válido), mas
**reforça e refina** a regra: agora há evidência direta de que preço por hora escala com a
capacidade do munck. Para munck de 15t ou 45 t/m, o modelo de custo (calibrado para 8-12t)
provavelmente **subestima** o custo real (diesel, manutenção, depreciação de um equipamento
maior/mais caro) — então a folga de margem calculada para Deodápolis e São Lourenço é otimista;
tratamos essa ressalva explicitamente na tabela acima e no `.json`.

### Ponto de equilíbrio (sem mudança)

Custo fixo mensal por caminhão ≈ **R$7.903,09/mês**. Com o preço mediano combinado GO+vizinhos
atualizado (agora mais alto, dado o novo dado de vizinhos) e o custo variável do modelo, a conta
de "~68h/mês por caminhão (~136h/mês para os 2)" para cobrir custo fixo segue como referência
conservadora — se os preços praticados pela empresa ficarem perto da nova mediana de vizinhos
(R$314/h) em vez da mediana de GO (R$295/h), o breakeven cai (menos horas necessárias).

## 5. Investimento inicial — sem mudança

Ver tabela completa no `.json` (`investimento`): R$57 mil a R$144 mil conforme utilização
(seguro-garantia a caução), classe baixo a médio.

## 6. Regras práticas de lance

- Piso de hora com combustível por conta da CONTRATADA: **~R$220/h**. Piso com combustível por
  conta do CONTRATANTE: **~R$90/h**. Sempre checar essa cláusula antes de formar o lance.
- **NOVO**: quanto maior a capacidade do munck exigida (15t, 45 t/m), maior o preço/hora pago —
  mirar editais compatíveis com a capacidade real dos 2 caminhões da empresa, não os de maior
  valor/hora.
- Desconto típico: GO mediana 14,0% [Q1 5,1%; Q3 42,5%]; vizinhos mediana **7,7%** [Q1 3,0%; Q3
  12,2%] (atualizado, amostra maior e mais conservadora — municípios pequenos de MS/MG/TO
  concentram descontos baixos em itens de concorrência restrita).
- Franquia mínima de horas: GOINFRA exige mín. 4h/dia; jornadas contratuais variam de 44h/semana
  a franquias muito maiores (Alvorada-TO: 983h no RP).
- Diária "sem operador" e preços "hora produtiva x improdutiva": sem mudança (ver rodada
  anterior / seção 4).
- Itens dentro de frotas mistas: continuam disputáveis isoladamente (agora com mais um exemplo:
  Três Pontas-SAAE-MG).

## 7. Exigências recorrentes (agora com texto oficial de edital, não só PDFs manuais)

| Exigência | Evidência |
|---|---|
| Capacidade de carga (8-15t nos casos médios, até 45 t/m nos de grande porte) | Poxoréu (10t); Deodápolis-MS (15t); São Lourenço-MG (45 t/m, lança 20m) |
| Altura de trabalho do cesto | **NOVO**: Goianésia (texto do edital), "cesto aéreo com altura de trabalho de no mínimo 13,5 m" |
| Idade máx./ano de fabricação | Goianésia (≥2000); Silvânia (≥2015); Poxoréu (≥2010) |
| NR-11/NR-12 (motorista/operador) | Mineiros; Poxoréu |
| **NOVO** — NR-10/NR-35/NR-12 + SEP para o ELETRICISTA (2º profissional) | Goianésia (texto do edital): "motorista...categoria D e eletricista portador de certificações em NR35, NR12 e NR10 e SEP" — contratos de rede energizada podem exigir 2 profissionais, não só o motorista |
| CNH compatível + qualificação do operador | Corumbaíba; **NOVO** Santa Fé de Goiás (texto): "operador devidamente habilitado e treinado, com comprovação de qualificação técnica para operação do cesto aéreo" |
| **NOVO** — CREA/CFT | Só em Vila Propício (é uma "obra", não locação pura) — texto confirma exigência para empresas de fora de GO |
| CRLV + seguro do veículo | Goianésia; Poxoréu |
| Responsabilidade pelo combustível (VARIÁVEL) | 4 contratada / 2 contratante, confirmados; **os 19 casos novos de MS/MG/TO não tiveram essa cláusula verificada nesta atualização** — limitação explícita |
| Jornada/franquia | Goianésia; Poxoréu; **NOVO** Alvorada-TO (983h no RP, uma das maiores franquias da amostra) |

## 8. Recomendação

**Classe: SELETIVO (mantida, mas reforçada).** A amostra de vizinhos incluídos mais que dobrou
(6→13) com a recoleta, confirmando que a demanda por munck fora de GO é real, não um artefato de
amostra pequena. Ao mesmo tempo, os novos dados confirmam que preço/hora escala com capacidade —
mirar contratos compatíveis com os 2 caminhões da empresa (porte médio), priorizar locação pura
de munck/cesto item-a-item, e sempre checar a cláusula de combustível antes do lance (agora uma
limitação explícita para os 19 casos novos).

### Oportunidades para os munck em outras áreas

Reexecutamos a busca (`caminhão`+`munck/guindauto/cesto`) sobre o dataset completo pós-recoleta
(535 arquivos, ante 415): confirma o achado anterior (eletrica_predial-GO, R$169.825,41 em troca
de luminária com caminhão-cesto) e traz **1 achado novo**: em Minas Gerais, uma obra de cobertura
de quadra esportiva tem um item de "mobilização e desmobilização de container...em caminhão
carroceria com guindauto (munck)" (R$1.941,55) — mostra outro nicho de demanda (apoio logístico a
obras), além da iluminação pública. Segue sem confirmação qualquer oportunidade em
refrigeração/condensadoras.

## Limitações (atualizadas)

- Amostra de GO inalterada (12 casos); vizinhos cresceu de 6 para 13 incluídos — ainda pequena,
  mas menos frágil.
- `n_participantes`: null em 100% dos 46 casos.
- Mudança de método de `desconto` **confirmada sem efeito** nas estatísticas de munck.
- Cobertura de texto de edital subiu de 0/27 para 16/46 casos — evidências de exigências agora
  vêm de texto oficial + 8 PDFs manuais (2 ainda não convertidos).
- Responsabilidade pelo combustível **não verificada** nos 19 casos novos de MS/MG/TO.
- Margem de Deodápolis-MS (15t) e São Lourenço-MG (45 t/m) usa o modelo de custo do munck médio
  (8-12t) — provavelmente subestima o custo real desses 2 casos de maior porte.
- Diesel, manutenção/pneus, seguro/licenciamento e depreciação seguem como estimativas (ver
  premissas no `.json`), sem mudança em relação à rodada anterior.
- Casos "parcialmente incluídos" (valor/desconto do caso pode incluir itens fora do escopo):
  Silvânia e Morro Agudo (GO); Sapezal-129, Poxoréu, Juína-DAES e Três Pontas-SAAE (vizinhos).
