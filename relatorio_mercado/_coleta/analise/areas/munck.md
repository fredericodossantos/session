# Munck — estudo de mercado de licitações (GO + vizinhos)

Empresa-alvo: engenharia de GO com engenheiro mecânico e eletricista, técnicos/mecânicos de
refrigeração, eletricistas, **2 caminhões munck** e veículos leves. Foco em contratos de
mão de obra + deslocamento + materiais baratos, pagos por medição mensal, baixo investimento.

Fonte dos dados: `W/analise/casos.jsonl` (27 casos brutos de munck, GO + vizinhos),
`W/compras/{id}.json` (itens e resultados brutos), `W/custos/custos/referencias.json` e
`W/analise/PREMISSAS_COMUNS.md`. A coleta (`coletor.py`) ainda estava em andamento no momento
desta análise (27/09/2026); `W/textos` estava vazio para munck (nenhum dos 27 casos tinha
`exigencias.tem_texto=true`). Para compensar, **8 editais foram baixados manualmente** via API
de arquivos do PNCP (2 s entre requisições, limite do enunciado); 6 foram extraídos com sucesso
(2 vieram em formato RTF disfarçado de `.pdf` e não puderam ser convertidos nesta rodada).

## 1. Revisão da classificação heurística

A heurística automática (`casos.py`) julgou 27 casos de munck (17 em GO, 10 em vizinhos:
2 DF + 8 MT), incluindo 9 em GO e 6 em vizinhos (motivo de exclusão único: `fornecimento_puro`,
11 casos no total). Revisamos manualmente **todos os 27 casos**, lendo o objeto completo e os
itens de `W/compras/{id}.json` (descrição, unidade, quantidade, valores e vencedor por item).

**Achados da revisão:**

1. **5 casos reclassificados de excluído → incluído** (3 em GO, 2 em MT), todos pelo mesmo
   padrão: o objeto é claramente uma **locação/serviço** ("locação mensal de caminhão...",
   "locação de caminhão tipo Munck...") mas o item foi codificado (erradamente) como
   `materialOuServico=M` pelo próprio órgão — limitação já documentada no `README.md` do
   pipeline. Em 2 desses casos (Morro Agudo de Goiás e Poxoréu) a inclusão é **parcial**: a
   maior parte dos itens do processo é, de fato, material ou equipamento fora do escopo, mas há
   **1 item específico e isolado de locação de munck/cesto**, com vencedor e preço próprios, que
   pode ser disputado separadamente.
2. **2 casos reclassificados de incluído → excluído** (`fora_escopo`): um contrato de
   manutenção predial contínua de grande porte do MPU-DF (item homologado único é "Ar
   Condicionado - Manutenção Sistema Central"; nenhum item de munck real — provável falso
   positivo pela palavra "plataforma elevatória" no objeto) e um RP de Sorriso-MT cujo objeto
   cita munck mas cujo **único item efetivamente licitado** é um caminhão hidrojato para
   limpeza de bueiros (sem item de munck disputável).
3. **5 casos confirmados como ruído puro** (`fora_escopo`): registros de preços de medicamentos
   e materiais odontológicos/hospitalares de 3 municípios/órgãos diferentes — falsos positivos
   de indexação, sem qualquer relação com munck.
4. **3 casos confirmados como `fornecimento_puro`** genuíno: aquisição de guincho agrícola +
   kit roll-on/roll-off (EMBRAPA), aquisição de caminhão **zero-quilômetro** com cesto (Jataí —
   é compra de bem, não locação de serviço) e obra de fornecimento/instalação de postes e
   luminárias para um campo de futebol (Juruena-MT).
5. Em 3 casos de MT (Sapezal-129, Poxoréu, Juína-DAES), o munck aparece **misturado em uma
   frota/pacote de serviços muito maior** (pipa, escavadeira, rolo compactador, cavalo mecânico,
   jardinagem, hidrojato, solda etc.). Como os itens de cada RP têm vencedor e preço próprios,
   tratamos esses casos como **incluídos** (o item de munck é genuinamente disputável em
   separado), mas os indicadores de valor/ticket do CASO não devem ser lidos como "tamanho de um
   contrato de munck" — ver alerta na seção 2.

**Resultado final:** de 27 casos brutos, **18 foram incluídos** (12 em GO, 6 em vizinhos) e 9
excluídos. O arquivo `munck.json` traz a decisão (`incluido`, `motivo`, `justificativa` de 1
linha) para cada um dos 27 casos.

| Motivo de exclusão (confirmado após revisão) | GO | Vizinhos |
|---|---:|---:|
| `fornecimento_puro` (compra de bem, não locação de serviço) | 2 | 1 |
| `fora_escopo` (falso positivo de indexação / item real não é munck) | 3 | 3 |
| **Total excluído** | **5** | **4** |

## 2. Indicadores finais (recalculados com a classificação revisada)

O índice de busca (`selecao.jsonl`) aponta um volume de **~8 casos/ano em GO** e **~38,5
casos/ano nos vizinhos** (DF+MT+MS+TO+MG); a amostra detalhada (`casos.jsonl`) trouxe 17
processos em GO e 10 em vizinhos no período de ~24 meses — cobertura razoável em GO, mas
**amostra pequena em ambos os grupos**: qualquer mediana/quartil abaixo deve ser lido como ordem
de grandeza, não como estimativa robusta.

| Indicador | GO | Vizinhos |
|---|---:|---:|
| Casos incluídos (amostra detalhada) | 12 | 6 |
| Valor total estimado (soma da amostra incluída) | R$ 4.789.966,65 | R$ 8.273.654,35 |
| Valor total homologado | R$ 2.862.049,99 | R$ 7.062.198,68 |
| Ticket mediano (estimado) | R$ 200.606,40 | R$ 1.260.763,75 |
| Desconto — mediana | 14,0% | 9,6% |
| Desconto — 1º quartil (Q1) | 5,1% | 7,9% |
| Desconto — 3º quartil (Q3) | 42,5% | 24,4% |
| Descontos suspeitos descartados (<0% ou >90%) | 0 de 12 | 0 de 6 |
| % deserta ou fracassada (nível de caso) | 0,0% | 0,0% |
| % exclusiva ME/EPP (total) | 0,0% | 16,7% |
| % exclusiva parcial ME/EPP | 0,0% | 0,0% |
| % contrato continuado (sinal textual) | 16,7% | 16,7% |
| % pontual | 16,7% | 50,0% |
| % indefinido (sem sinal textual de vigência) | 66,7% | 33,3% |

> **Nº de participantes:** o PNCP **não publica** esse número. O campo `n_participantes` ficou
> `null` em **todos os 27 casos** de munck, inclusive nos 8 editais lidos integralmente.

> **Alerta de leitura — vizinhos:** boa parte do valor/ticket agregado de vizinhos vem de RPs
> multi-serviço (frota mista) em que o munck é só 1 de vários itens — ex.: Sapezal-129 (MT),
> R$ 3,15 milhões no total, mas só 2 dos 7 itens são de munck (e nenhum teve vencedor); Juína-DAES
> (MT), R$ 1,85 milhão em 33 itens, dos quais só 1 é munck. **O ticket mediano de vizinhos
> (R$ 1,26 milhão) não representa o tamanho típico de um contrato de munck** — os valores
> unitários reais e disputáveis estão na seção 3 (preços por hora/diária/mês).

### Preço unitário vencedor — hora/diária/mês de munck, vs. referências

| Categoria | GO — vencedor | Vizinhos — vencedor | Referência de mercado |
|---|---|---|---|
| Hora "produtiva"/operando | R$ 180,00 / R$ 295,00 / R$ 405,63 (mediana R$ 295,00, n=3) | R$ 222,46 / R$ 222,46 / R$ 340,00 (mediana R$ 222,46, n=3) | GOINFRA (GO, T334 fev/2026, cód. 072080, mín. 4h/dia, já c/ operador): **R$ 213,33/h**. SICRO E9690 (guindauto+cesto, GO): **R$ 330,89/h** |
| Hora "improdutiva"/deslocamento | R$ 168,35 (n=1, Santa Fé de Goiás — 41% da hora produtiva do mesmo edital) | — | — |
| Diária (sem operador) | R$ 645,00 (n=1, Três Ranchos) | — | — |
| Mensal | R$ 7.561 a R$ 23.590, mediana **R$ 12.000** [Q1 R$ 9.883; Q3 R$ 19.639] (n=7) | R$ 34.333,33 (n=1, Poxoréu) | — |
| Por operação (içamento pontual) | — | R$ 6.900 / R$ 7.300 / R$ 8.866,85 (mediana R$ 7.300, n=3, Aeronáutica-DF) | — |
| **Outlier descartado** | — | R$ 64,00/h (Juína-DAES: estimado R$434,00/h, desconto de 85% — economicamente inviável, nem cobre o diesel) | — |
| **Desertos (sem vencedor)** | — | 2 itens de munck do RP de Sapezal-129 (estimados R$378,75/h e R$12,33/km) ficaram sem oferta, enquanto os demais itens da mesma frota (pipa, escavadeira, cavalo mecânico) foram homologados | — |

A mediana da "hora produtiva" em GO (R$ 295/h) fica **38% acima** do GOINFRA e **89%** do SICRO
com cesto; nos vizinhos (R$ 222,46/h) fica só **4% acima** do GOINFRA e **67%** do SICRO.

## 3. Casos exemplares (GO)

| Caso | Município | Resumo |
|---|---|---|
| [Goianésia](https://pncp.gov.br/app/editais/01065846000172/2026/584) | Goianésia | RP para 2 caminhões munck+cesto (idade mín. bem permissiva, ano ≥2000); maior desconto observado em GO (59,5%), de R$ 58.229,60 para R$ 23.530–23.590/mês por caminhão. |
| [Corumbaíba](https://pncp.gov.br/app/editais/01302603000100/2026/110) | Corumbaíba | Locação por hora com motorista e cesto hidráulico, 1.000 h estimadas; R$ 194,58/h → R$ 180,00/h homologado (7% desconto); exige CNH C/D/E; combustível por conta da contratada. |
| [Santa Fé de Goiás](https://pncp.gov.br/app/editais/25107517000105/2025/304) | Santa Fé de Goiás | Guindauto+cesto (10 t/136 kW) com operador, precificado em "hora produtiva" (R$ 405,63) e "hora improdutiva/deslocamento" (R$ 168,35 = 41% da produtiva) — modelo raro na amostra; vencedor único, sem desconto. |
| [Vila Propício](https://pncp.gov.br/app/editais/01612817000183/2025/830) | Vila Propício | Pequena obra (R$ 140.520,31, abaixo do limiar de obra grande) de implantação de iluminação com **substituição de postes** — exemplo direto do escopo do estudo. Desconto de 53%. |
| [Silvânia](https://pncp.gov.br/app/editais/01068030000100/2026/205) | Silvânia | RP com 2 itens/vencedores distintos: cesto aéreo 10t (R$ 20.553,47→R$ 10.275,00/mês, relevante) + caminhão coletor de lixo (ruído) — mostra como disputar só o item pertinente. |

## 4. Margem em casos típicos (caminhão PRÓPRIO)

### Premissas de custo (fontes citadas; ver `premissas_custo` no JSON)

| Componente | Valor | Fonte / premissa |
|---|---:|---|
| Motorista/operador munck (piso + 69,28% encargos + VA + EPI) | **R$ 3.811,42/mês** | CCT SETCEG 2026/2028 (R$1.870,00) + SINAPI-GO encargos + CCT construção civil GO (VA) + estimativa (EPI) |
| Diesel S10 (ANP-GO, semana 20–26/09/2026) | **R$ 7,232/L** | ANP, dado primário oficial |
| Consumo em operação (guindaste sob carga) | **22,37 L/h** | SINAPI 91633 (guindauto hidráulico 6,5t), componente "materiais na operação" |
| Consumo em deslocamento | ~3 km/L (**estimativa**, sem fonte direta) | análogo à estimativa de veículo leve das premissas comuns |
| Diesel — hora "genérica" (mix 40% operação / 60% deslocamento, premissa do analista) | **R$ 115,47/h** | — |
| Manutenção + pneus | R$ 26,39/h (**estimativa**: ~10%/ano do valor do bem) | regra de bolso de mercado |
| Seguro + licenciamento | R$ 7,71/h (**estimativa**: ~2%/ano + taxas) | regra de bolso de mercado |
| Munck usado (10 t, referência de depreciação) | **R$ 380.000** | busca de mercado (Mercado Livre/MF Rural/Trucadão/Mercado Máquinas, 27/09/2026); anúncios variam de ~R$269 mil a ~R$420 mil para porte semelhante |
| Depreciação (base 80% do valor, 96 meses) | R$ 26,39/h | — |
| BDI (Construção de Edifícios, TCU 2622/2013; AC4,00%+S/G0,80%+R1,27%+DF1,23%+L7,40%; T8,65%) | **26,26%** (lucro zero: 17,54%) | premissas comuns |

Custos fixos e variáveis foram amortizados sobre **120 h/mês** por caminhão como base padrão
(ou 176 h/mês quando o próprio edital declarava a jornada — ver casos individuais).

### Achado central: quem paga o combustível muda tudo

Dos 6 editais lidos integralmente, **4 colocam o combustível por conta da contratada**
(Corumbaíba, Mineiros, Santa Fé de Goiás, e implícito em Três Ranchos) e **2 por conta do
contratante/município** (Goianésia — *"as despesas com combustível... serão de
responsabilidade da administração municipal"*; Poxoréu — *"sendo obrigação do município apenas
o combustível"*). Isso muda o custo direto por hora em **mais de 50%** — é o item mais
importante a checar em cada edital antes de formar preço.

### Tabela de margem

| Caso | Preço vencedor | Combustível por conta de | Custo direto | Lucro zero | Preço c/ BDI | Classificação |
|---|---:|---|---:|---:|---:|---|
| [Corumbaíba](https://pncp.gov.br/app/editais/01302603000100/2026/110) | R$ 180,00/h | contratada (confirmado) | R$ 186,77/h | R$ 219,55/h | R$ 235,82/h | **Prejuízo provável** |
| [Mineiros-SAAE](https://pncp.gov.br/app/editais/02316487000141/2025/44) | R$ 295,00/h | contratada (confirmado) | R$ 186,77/h | R$ 219,55/h | R$ 235,82/h | **Folgado** |
| [Santa Fé de Goiás](https://pncp.gov.br/app/editais/25107517000105/2025/304) — produtiva | R$ 405,63/h | contratada (confirmado) | R$ 233,06/h | R$ 273,94/h | R$ 294,32/h | **Folgado** |
| [Santa Fé de Goiás](https://pncp.gov.br/app/editais/25107517000105/2025/304) — improdutiva | R$ 168,35/h | contratada (confirmado) | R$ 155,91/h | R$ 183,24/h | R$ 196,83/h | **Prejuízo provável (marginal)** |
| [Sapezal-MT](https://pncp.gov.br/app/editais/01614225000109/2026/171) | R$ 340,00/h | não confirmado (assumido contratada, conservador) | R$ 186,77/h | R$ 219,55/h | R$ 235,82/h | **Folgado** |
| [Poxoréu-MT](https://pncp.gov.br/app/editais/03408911000140/2026/23) | R$ 34.333,33/mês (≈R$ 195,08/h a 176h/mês) | **MUNICÍPIO** (confirmado) | R$ 71,30/h | R$ 83,81/h | R$ 90,02/h | **Folgado (bem confortável)** |

### Ponto de equilíbrio (break-even) dos 2 caminhões

Custo fixo mensal por caminhão (mão de obra + seguro/licenciamento + depreciação) ≈
**R$ 7.903,09/mês**. Usando o preço mediano observado (GO+vizinhos combinados, ~R$ 258,73/h) e o
custo variável (diesel blended + manutenção, R$ 141,86/h), a margem de contribuição é de
**R$ 116,87/h**. São necessárias **~68 horas faturadas/mês por caminhão** (**~136 h/mês para os
2 munck juntos**) só para cobrir o custo fixo — qualquer hora além disso já contribui para o
lucro.

## 5. Investimento inicial

Como os 2 caminhões **já existem**, o investimento inicial é dominado por capital de giro (2
meses de folha+diesel, já que o pagamento por medição mensal cai ~30 dias depois, então o 1º
recebimento chega perto do dia 60) e pela garantia contratual — não pela compra de equipamento.

| Cenário | Total (via caução) | Total (via seguro-garantia) | Classe |
|---|---:|---:|---|
| Utilização baixa (~60–80 h/mês/caminhão, perfil típico dos municípios pequenos de GO) | R$ 64.000 a R$ 100.000 | R$ 57.000 a R$ 89.500 | baixo a médio |
| Utilização alta (~120 h/mês/caminhão) | R$ 118.000 a R$ 144.000 | R$ 104.500 a R$ 123.000 | médio |

No cenário de maior utilização, o total **ultrapassa a faixa "baixo"** (até R$ 50 mil) das
premissas comuns e entra em "médio" (R$ 50–200 mil) — usar seguro-garantia em vez de caução
ajuda a manter o total mais baixo.

## 6. Regras práticas de lance

- **Piso de hora quando o combustível é por conta da CONTRATADA** (o cenário mais comum: 4 de 6
  editais lidos): não ofertar abaixo de **~R$ 220/h** (preço de lucro zero R$ 219,55/h); o caso
  de Corumbaíba (R$ 180/h) ilustra o risco de prejuízo nesse cenário.
- **Piso de hora quando o combustível é por conta do CONTRATANTE/MUNICÍPIO** (confirmado em
  Goianésia-GO e Poxoréu-MT): custo direto cai para **~R$ 71/h**, preço com BDI **~R$ 90/h** —
  muito mais espaço para descontos agressivos. **Sempre ler essa cláusula antes de formar o
  preço** — é o maior fator isolado de variação de margem encontrado nesta análise.
- **Desconto típico:** GO mediana 14,0% [Q1 5,1%; Q3 42,5%]; vizinhos mediana 9,6% [Q1 7,9%;
  Q3 24,4%]. Evitar descontos acima do 3º quartil de GO (~42%), que no modelo de custo já se
  aproxima ou cruza o preço de lucro zero.
- **Franquia mínima de horas:** GOINFRA exige mín. de 4h/dia por chamado; jornadas contratuais
  observadas vão de "8h/dia seg-sex + 4h sáb" (44h/semana, Goianésia) a "até 8h/dia" (Poxoréu).
- **Diária "sem operador"** (Três Ranchos, R$ 645/diária): o município fornece o motorista — não
  computar mão de obra na composição, mas confirmar por escrito quem paga o diesel.
- **Preços "hora produtiva" x "hora improdutiva/deslocamento"** (Santa Fé de Goiás): ao ofertar
  nesse formato, garantir que a hora improdutiva cubra ao menos o custo de deslocamento (~R$156/h
  no modelo) — não usar o mesmo piso da produtiva para as duas.
- **Itens dentro de frotas mistas** (Sapezal, Poxoréu, Juína-DAES, em MT): como os itens têm
  vencedor e preço próprios, é possível ofertar **só no item de munck**, sem se comprometer com
  o pacote inteiro — mas checar regras de julgamento por lote/grupo.

## 7. Exigências recorrentes (evidência dos 6 editais lidos)

| Exigência | Recorrência | Evidência |
|---|---|---|
| Capacidade de carga (8–10 t, lança 18–22 m) | 6 de 6 | Poxoréu: "capacidade de carga mínima de 10 toneladas, lança com alcance vertical de 21,8 m e horizontal de 18,8 m... gancho olhal de 5 a 7,2 toneladas" |
| Idade máx./ano de fabricação (varia muito) | 4 de 6 | Goianésia: ano ≥2000 (permissivo); Silvânia: ano ≥2015; Poxoréu: ano ≥2010 (item munck) e "não superior a 10 anos" (outro item da mesma frota) |
| NR-11 (movimentação/içamento de cargas) e NR-12 (segurança em máquinas) | 3 de 6 | Mineiros: "curso de operador Munck – de acordo com a NR 11... e NR 12"; Poxoréu: idem + NR-06, NR-07, NR-01 (PGR/GRO) |
| NR-10 / NR-35 (rede energizada / altura), quando aplicável | 1–2 de 6 | Goianésia: eletricista com "certificações em NR35, NR12 e NR10 e SEP" |
| CNH compatível (C/D/E) + curso de operador | 6 de 6 | Corumbaíba: "CNH com habilitação mínima categoria C, D ou E"; Poxoréu: "CNH categoria compatível e/ou curso técnico específico" |
| CRLV + seguro do veículo em dia | 4 de 6 | Goianésia: "CRLV atualizado..., apólice de seguro vigente..."; Poxoréu: idem + CTB/CONTRAN |
| **Responsabilidade pelo combustível — VARIÁVEL** | 6 de 6 (2 contratante / 4 contratada) | ver seção 4 — achado central da análise |
| Jornada/franquia (8h/dia, 44h/semana) | 3 de 6 | Goianésia e Poxoréu (ver seção 6) |

## 8. Recomendação

**Classe: SELETIVO.** O volume é pequeno em número de casos (12 em GO, 6 em vizinhos, amostra
pequena), mas o perfil casa bem com o negócio (locação por hora/diária/mês, poucas exigências
além de NR-11/12 e CNH, ativos já existentes). A margem, porém, depende de um fator pouco visível
de antemão — quem paga o combustível — que muda o custo direto por hora em mais de 50%. Mirar RPs
municipais de locação **pura** de munck/cesto (não frotas mistas nem fornecimento de material),
**ler a cláusula de combustível antes do lance**, e evitar descontos acima do 3º quartil histórico
de GO (~42%).

### Oportunidades para os munck em outras áreas

Busca por `munck|guindauto|cesto|poste` nas descrições de item de **todos** os casos de outras
áreas retornou 82 ocorrências, mas a esmagadora maioria é ruído: "poste" como **material**
(poste de aço/concreto/eucalipto à venda, cinta/braço para poste) e "cesto" como **cesto de
lixo** ou tambor de máquina de lavar — sem relação com locação de munck. Refinando para exigir
"caminhão"+"munck/guindauto/cesto" no mesmo trecho, restou só:

- **[Eletrica predial — GO](https://pncp.gov.br/app/editais/01738772000198/2025/18):**
  contrato de fornecimento de material elétrico + mão de obra que contém um item isolado e
  substancial — *"SERVIÇO ESPECIALIZADO EM ALTURA PARA TROCA DE LUMINÁRIA PÚBLICA EM POSTE DE
  ATÉ 12 MT, REALIZADO COM CAMINHÃO TIPO CESTO AÉREO"* (1.377 unidades, R$ 169.825,41 no total,
  ~R$ 123,33/unidade) — poderia ser oferecido isoladamente ou como subcontratação.

Não foi encontrado, na amostra coletada até agora, nenhum caso de remanejamento de condensadoras
ou de refrigeração com item de munck/guindauto/cesto (o exemplo citado no enunciado do estudo não
teve ocorrência confirmada nos dados disponíveis).

## Limitações

- Amostra pequena em todas as quebras (12 casos incluídos em GO, 6 em vizinhos) — leia
  medianas/quartis como ordem de grandeza.
- `n_participantes`: null em 100% dos 27 casos (PNCP não publica esse dado).
- Indicadores agregados de "vizinhos" mesclam munck puro com frotas mistas — não usar
  valor/ticket de caso como proxy de "tamanho de contrato de munck" (ver seção 2).
- `exigencias.tem_texto=false` em 100% dos casos de munck no `casos.jsonl`; as evidências de
  exigências/combustível vieram de 6 PDFs de edital baixados manualmente (2 RTFs disfarçados de
  `.pdf`, de Nova Santa Helena-MT e Sapezal-171-MT, não puderam ser convertidos nesta rodada).
- Consumo de diesel em operação (22,37 L/h, SINAPI 91633) é de um guindauto de 6,5t — pode
  não representar bem um munck de 8-12t; consumo em deslocamento (~3 km/L) e a mistura
  40%/60% operação/deslocamento são estimativas do analista, sem fonte direta (sensibilidade de
  ±25% mostrada nas premissas).
- Valor do munck usado (R$ 380.000, para depreciação) vem de busca de mercado em anúncios
  (Mercado Livre, MF Rural, Trucadão, Mercado Máquinas), não de uma cotação única — faixa
  observada de ~R$269 mil a ~R$420 mil para porte semelhante.
- Manutenção+pneus e seguro/licenciamento são estimativas de regra de bolso do setor, sem fonte
  documental direta em `referencias.json`.
- Responsabilidade pelo combustível só confirmada nos 6 editais lidos; para os demais 21 casos
  (inclusive o usado na margem de Sapezal-MT) foi assumida, de forma conservadora, por conta da
  contratada — pode subestimar a margem real desses casos.
- 5 casos foram tratados como "parcialmente incluídos" (Silvânia, Morro Agudo de Goiás, Sapezal-
  129, Poxoréu, Juína-DAES): o valor/desconto do CASO inclui itens fora do escopo — os valores
  unitários do item específico de munck (seções 3 e 4) são a referência mais confiável.
