# Iluminação pública — estudo de mercado (Goiás e vizinhos)

Manutenção corretiva e preventiva do parque de iluminação pública (troca de lâmpadas,
reatores e relés, ronda noturna), pequenas extensões de rede e poda/manutenção com
caminhão. Dados do PNCP coletados por `coletor.py` (coleta ainda em andamento em
2026-09-27), analisados em `W/analise/casos.jsonl` e complementados nesta análise com
o texto de 15 editais/TR de GO baixados manualmente e salvos em
`W/analise/areas/textos_ip/`.

**Amostra pequena — leia com cautela.** Dos 121 casos que bateram na palavra-chave
"iluminação pública" (95 em GO, 26 em vizinhos), a revisão manual manteve apenas
**8 casos em GO** e **5 em vizinhos** como genuinamente relacionados a manutenção/pequena
extensão de IP. A maioria dos 121 é falso positivo (eventos com "som, palco,
iluminação", decoração natalina, equipamento hospitalar "com iluminação LED") ou está
fora do escopo de manutenção corretiva (modernização/eficientização LED em massa,
fornecimento puro de material sem mão de obra).

## 1. Revisão da classificação

A heurística automática (`casos.py`) usa 4 motivos de exclusão: `equipamento_alto`,
`obra_grande`, `fornecimento_puro` e `mencao_passagem`. Ela é boa em separar
"fornecimento puro de material" de "manutenção com material embutido" quando o texto é
claro, mas erra sistematicamente em dois padrões que dominam esta área:

1. **Eventos com "som, palco, iluminação"** — a palavra "iluminação" aparece em
   praticamente toda contratação de estrutura para festas/rodeios/réveillon/natal, mas
   isso não é iluminação pública de vias. A heurística só pega esse padrão quando o
   objeto também menciona "gerador" (vira `equipamento_alto`) ou quando todos os itens
   vêm como material (`fornecimento_puro`); quando nenhum dos dois ocorre, o caso ficava
   **incluído por engano**.
2. **Modernização/eficientização de LED em massa** — quando o objeto é um único item
   de "empreitada global" (ex.: "fornecimento e instalação de luminárias LED"), a
   fração de material calculada às vezes fica em 0% (porque o único item foi
   classificado erroneamente como serviço), então a regra de `equipamento_alto`
   (fração de material > 40%) não dispara e o caso fica **incluído por engano** mesmo
   sendo modernização de grande porte.
3. Ao contrário, alguns registros de preços mistos ("fornecimento de material +
   locação de cesto aéreo") vieram com **todos os itens marcados como material** no
   PNCP (inclusive o item de locação de veículo, que é serviço), fazendo a heurística
   excluir por `fornecimento_puro` um caso que a empresa deveria considerar.

A tabela completa de decisões (121 casos, incluído/excluído, motivo e justificativa de
1 linha) está em `W/analise/areas/iluminacao_publica.json`, campo `decisoes`. Resumo:

| Grupo | Casos revisados | Incluídos (decisão final) | Principal motivo de exclusão |
|---|---|---|---|
| GO | 95 | **8** (8,4%) | `fornecimento_puro` (49), `mencao_passagem` (25 — a maioria eventos), `equipamento_alto` (12 — modernização LED/gerador), `obra_grande` (1) |
| Vizinhos (DF+MT+MS+TO+MG) | 26 | **5** (19,2%) | `mencao_passagem` (12), `fornecimento_puro` (8), `equipamento_alto` (1) |

Principais reclassificações feitas nesta revisão (detalhe completo no JSON):

- **Incluídos por engano → excluídos**: eficientização de LED de Jataí (R$16,2 mi),
  modernização de Mambaí (R$1,44 mi) e a grande adesão de Senador Canedo (R$15,0 mi,
  "empreitada global... fornecimentos de material – mão de obra – encargos –
  logística") — todas são modernização/eficientização de grande porte, não manutenção
  corretiva.
- **Excluídos por engano → incluídos**: locação de caminhão com escada giratória e
  cesto aéreo em Pontalina (o único item veio como "material" no PNCP, mas o objeto é
  claramente locação de veículo/serviço); o item de "locação de cesto aéreo com
  motorista" dentro do RP misto de Morro Agudo de Goiás (36% do valor do lote, também
  miscodificado como material); e dois processos de Corguinho/MS de "serviços
  continuados de manutenção preventiva e corretiva... da iluminação pública" (mão de
  obra, mas os 2 itens do PNCP vieram como material).

## 2. Indicadores finais (só casos incluídos)

| Indicador | GO (n=8) | Vizinhos (n=5) |
|---|---|---|
| Volume índice bruto (achados/ano, antes da revisão) | 91,5/ano | 196,0/ano |
| Valor estimado total (casos incluídos) | R$ 2.254.300,27 | R$ 2.597.016,27 |
| Valor homologado total (casos incluídos) | R$ 1.336.802,28 | R$ 2.076.360,70 |
| Ticket mediano (homologado) | R$ 149.400,00 | R$ 512.944,33 |
| Desconto — mediana / Q1 / Q3 | 19,4% / 5,6% / 32,5% | 7,8% / 0,0% / 24,5% |
| Descontos descartados (suspeitos, <0% ou >90%) | 0 | 0 |
| % deserta/fracassada | 0,0% | 0,0% |
| % exclusiva/parcial ME-EPP | 0,0% | 0,0% |
| % contínuo | 12,5% | 40,0% |

- **Nº de participantes**: o PNCP não publica esse dado; o campo `n_participantes`
  ficou `null` em **100%** dos 121 casos revisados (nenhum texto de edital/TR mencionou
  explicitamente "participaram N empresas"). Não há como calcular mediana de
  participantes nesta área.
- **Volume índice bruto**: vem de `selecao.jsonl` (índice de busca, antes da revisão
  manual), ÷2 para anualizar (janela de coleta de ~24 meses). GO: 183 achados
  aceitos em 24 meses → 91,5/ano. Vizinhos: 392 → 196,0/ano. Esse número mede o
  tamanho do funil de busca por palavra-chave, não o número real de oportunidades —
  como mostrado acima, a maior parte é falso positivo.
- **Exclusões por motivo** (todos os 121 casos, incluídos ou não): ver tabela da
  seção 1.
- **Veículo exigido** (amostra de 5 editais de GO com texto e objeto de veículo, dentre
  os 15 baixados): **60% aceitam explicitamente munck/guindauto com cesto acoplado**
  (Três Ranchos, Itaguari, e por indução Corumbaíba), **20% pedem plataforma articulada
  isolada mais específica** (Pontalina: giro 360°, altura útil ≥9 m, isolação ≥1 kV) e
  **20% não detalham** o tipo de içamento (Morro Agudo). Amostra pequena (n=5).

## 3. Casos exemplares (GO)

| Caso | Link PNCP | Veículo exigido |
|---|---|---|
| Corumbaíba — locação de caminhão com motorista + cesto aéreo hidráulico isolado, 1.000 h/ano | [01302603000100/2026/110](https://pncp.gov.br/app/editais/01302603000100/2026/110) | Cesto aéreo isolado, com motorista; edital cita falta de "veículo capaz de içar grandes estruturas" na frota própria (sugere aceitar guindaste/munck + cesto) |
| Três Ranchos — locação de caminhão Munck com cesto aéreo, sem operador, 240 diárias/ano | [01304286000161/2025/139](https://pncp.gov.br/app/editais/01304286000161/2025/139) | Exige expressamente "Caminhão MUNCK CESTO AÉREO": guindaste ≥10 m + cesto ≥130 kg — aceita munck+cesto |
| Itaguari — locação mensal contínua de caminhão com cesto aéreo, sem motorista | [24850109000186/2026/46](https://pncp.gov.br/app/editais/24850109000186/2026/46) | Guindauto com cesta aérea ≥12 m, 172 CV, diesel, ≥8 t carga — aceita munck/guindauto+cesto, sem operador |
| Pontalina — locação mensal de caminhão 3/4 com escada giratória e cesto aéreo articulado | [01791276000106/2026/62](https://pncp.gov.br/app/editais/01791276000106/2026/62) | Especificação mais restrita: cesto isolado ≥1 kV, carga ≥136 kgf, giro 360°, altura útil ≥9 m — não é claramente um munck genérico |
| Morro Agudo de Goiás — RP misto (58 itens material + 1 item locação de cesto aéreo c/ motorista) | [25043621000183/2026/128](https://pncp.gov.br/app/editais/25043621000183/2026/128) | "Cesto aéreo" sem especificação técnica detalhada no texto baixado; item de locação "com motorista" |

## 4. Margem em 5 casos típicos

**Premissas comuns**: custo direto do veículo pela referência de mercado
(`PREMISSAS_COMUNS.md`): caminhão munck R$ 213,33/h (GOINFRA T334, fev/2026, já inclui
operador) ou caminhão guindauto com cesto aéreo R$ 330,89/h (SICRO E9690/GO, já inclui
operador) — **usada como referência cheia e conservadora mesmo em contratos "sem
operador"**, porque não há decomposição oficial do CHP (posse/operação/mão de obra) 
disponível nesta sessão; a empresa, que já possui 2 munck amortizados, tende a ter
custo real menor. BDI de "Redes de Distribuição de Energia" (Acórdão TCU 2622/2013):
AC 5,92% + S+G 0,51% + R 1,48%, DF 1,07%, L médio 8,31%, T 8,65% → **BDI de lucro zero =
19,39%**, **BDI completo = 29,31%**. Nunca se usou a planilha de custos do próprio
edital como referência de custo.

| Caso | Escopo (premissa de horas) | Custo direto (referência cesto aéreo R$330,89/h) | Preço lucro zero | Preço com BDI | Valor estimado do edital | Homologado | Classificação |
|---|---|---:|---:|---:|---:|---:|---|
| Corumbaíba | 1.000 h/ano, com motorista | R$ 330.890 | R$ 395.093 | R$ 427.849 | R$ 194.580 | R$ 180.000 | **Prejuízo provável** |
| Três Ranchos | 240 diárias × 8h = diária R$2.647 | R$ 2.647/diária | R$ 3.160/diária | R$ 3.423/diária | R$ 867,42/diária | R$ 645,00/diária | **Prejuízo provável** |
| Itaguari | 88 h/mês (4h/dia × 22 dias) | R$ 29.118/mês | R$ 34.767/mês | R$ 37.658/mês | R$ 13.888,17/mês | R$ 12.000,00/mês | **Prejuízo provável** |
| Pontalina | 88 h/mês | R$ 29.118/mês | R$ 34.767/mês | R$ 37.658/mês | R$ 7.561,67/mês | R$ 7.561,00/mês | **Prejuízo provável** |
| Morro Agudo (item 59) | 3.000 h/ano, com motorista | R$ 992.670 | R$ 1.185.253 | R$ 1.283.925 | R$ 285.000 (estimado) | não capturado* | **Prejuízo provável (pelo estimado)** |

*Item 59 do lote de Morro Agudo não teve resultado individual capturado pela API do
PNCP (`itens_truncados=true`; só os 40 primeiros dos 59 itens têm valor homologado
salvo, embora o item conste como "Homologado" no detalhe bruto da compra).

**Leitura importante**: em 4 dos 5 casos, o próprio **valor estimado pelo edital** já
está abaixo do custo direto de referência (SICRO/GOINFRA), antes de qualquer desconto
de pregão — por exemplo, em Corumbaíba o preço de lucro zero (R$395.093) é cerca do
dobro do valor estimado (R$194.580). Isso não significa necessariamente que a empresa
teria prejuízo real: os valores de referência (SICRO/GOINFRA) descrevem equipamento
**novo, plenamente custeado por terceiros**; a empresa já possui 2 munck amortizados,
então seu custo marginal real (combustível + manutenção + motorista, sem novo capex)
tende a ser bem menor — mas a diferença é grande o bastante para exigir uma apuração
de custo real própria antes de ofertar qualquer desconto nesse nicho.

Sensibilidade (referência mais branda, munck sem cesto, R$213,33/h): Corumbaíba —
custo direto R$213.330/ano, ainda acima do homologado (R$180.000); Itaguari/Pontalina —
custo direto R$18.773/mês, ainda acima dos R$12.000 e R$7.561 homologados. A
classificação de "prejuízo provável" se mantém mesmo com a referência mais branda.

## 5. Investimento inicial típico

| Porte | Exemplo | Folha (2 meses) | Estoque inicial | Mobilização | Garantia (caução 5%) | Garantia (seguro-garantia 0,5–1,5% a.a.) | Total (caução) | Total (seguro) | Classe |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Pequeno | Locação mensal sem equipe própria (tipo Itaguari/Pontalina), ~R$150 mil/ano | R$ 7.623 | R$ 8.000 | R$ 1.500 | R$ 7.500 | R$ 750–1.125 | R$ 24.623 | ~R$ 17.998 | **Baixo** |
| Médio | Caminhão com motorista + cesto em tempo integral, eletricista/ajudante e fração de engenheiro (tipo Corumbaíba/Três Ranchos), ~R$180-210 mil/ano | R$ 35.322 | R$ 20.000 | R$ 5.000 | R$ 9.729 | R$ 973–1.459 | R$ 70.051 | ~R$ 61.538 | **Médio** |
| Grande | Contrato misto (material + locação de cesto) em maior escala, 2 eletricistas + 2 ajudantes + 2 motoristas + fração de engenheiro, ~R$1 milhão/ano | R$ 67.889 | R$ 90.000 | R$ 15.000 | R$ 50.000 | R$ 5.000–7.500 | R$ 222.889 | ~R$ 179.139 | **Alto (caução) / Médio-alto (seguro)** |

A forma de garantia muda a classe do porte "grande": com caução (5% imobilizado), fica
**alto** (>R$200 mil); com seguro-garantia (prêmio anual), fica perto do limite entre
médio e alto (~R$179 mil).

**Adaptação de cesto aéreo em munck já existente**: não foi encontrado nesta sessão um
preço de mercado publicado para o retrofit de um cesto aéreo isolado (NR-12, ~1 kV,
130-300 kgf) num chassi de munck já existente — os fabricantes pesquisados (Fibras
Cestos Aéreos, IW8, Auto Cranes/CuboGuia, Progresso Cargas) só fornecem orçamento sob
consulta. Um cesto simples não isolado (cabo duplo, sem certificação NR-12/1kV) foi
encontrado por ~R$6.100 (iw8.com.br), mas não é equivalente ao equipamento isolado
exigido nos editais — não deve ser usado como referência. Como ordem de grandeza
alternativa (não equivalente a um retrofit): um caminhão 0 km novo, já equipado de
fábrica com cesto aéreo articulado isolado duplo, foi estimado em R$747.666,67 pelo
Município de Jataí/GO ([01165729000180/2026/206](https://pncp.gov.br/app/editais/01165729000180/2026/206)).
Recomenda-se cotação formal com pelo menos 2 fabricantes antes de decidir pela
adaptação.

## 6. Regras práticas de lance

- Desconto típico em GO (amostra de 8 casos): **mediana 19,4%**, Q1 **5,6%**, Q3
  **32,5%** — sobre o valor já estimado pelo edital.
- Em 4 dos 5 casos analisados em detalhe, o próprio valor estimado do edital já estava
  abaixo do custo direto de referência formal (SICRO/GOINFRA) — ou seja, o risco não
  está apenas no desconto ofertado no pregão, mas no patamar de preço da própria
  administração, tipicamente ancorado no custo de pequenas locadoras informais da
  região.
- Regra derivada do cálculo de lucro zero: em Corumbaíba, o preço de lucro zero é
  ~2,0x o valor estimado do edital — sob a referência formal, seria preciso ofertar
  ACIMA do estimado (desconto negativo) para não operar no prejuízo. Nesse nicho
  específico de locação pura de veículo com cesto aéreo, o "desconto seguro" tende
  para zero (ou exige apuração de custo real próprio, abaixo da referência formal).
- Antes de ofertar qualquer desconto, apurar o custo MARGINAL real (combustível +
  manutenção + motorista, aproveitando os 2 munck já amortizados) e comparar
  diretamente com o valor estimado do edital — não com a referência SICRO/GOINFRA, que
  assume equipamento novo.
- Preferir contratos "sem motorista" (Itaguari, Pontalina) a "com motorista"
  (Corumbaíba) quando o preço estimado for parecido — a folha de motorista sozinha já
  custa ~R$3.811/mês por empregado (SETCEG 2026/2028 + encargos 69,28% + VA + EPI).
- Registros de preços mistos (material + locação de cesto, como Morro Agudo) tendem a
  ser mais atrativos que RPs de material puro, pois abrem espaço para cobrar o
  componente de serviço com o BDI de "Redes de Distribuição" (L médio 8,31%), em vez do
  BDI de mero fornecimento de material (11,10%-16,80%, sem lucro de serviço).

## 7. Exigências de habilitação recorrentes

| Exigência | Evidência (trecho) | Caso/Link |
|---|---|---|
| CREA/CAU (registro da empresa) | "Registro ou inscrição da empresa no Conselho Regional de Engenharia e Agronomia (Crea) ou Conselho de Arquitetura e Urbanismo (CAU)" | [Bom Jesus de Goiás](https://pncp.gov.br/app/editais/01149624000138/2026/88) |
| CREA — responsável técnico | "Certidão de Registro e Quitação do responsável técnico da empresa licitante junto ao CREA" | [Cocalzinho de Goiás](https://pncp.gov.br/app/editais/36985463000105/2026/19) |
| Atestado de capacidade técnica/operacional | "Atestado de Capacidade Técnica... que comprove ter o licitante executado, de forma satisfatória, contrato de locação de veículo pertinente" | [Pontalina](https://pncp.gov.br/app/editais/01791276000106/2026/62) |
| NR-10 / NR-12 / NR-35 (elétrica e altura) | "em conformidade com... Normas Regulamentadoras NR-10 e NR-12" / "em altura... designar somente trabalhadores com treinamento em NR-35" | [Jataí (compra caminhão)](https://pncp.gov.br/app/editais/01165729000180/2026/206) e [Jataí (eficientização LED)](https://pncp.gov.br/app/editais/01165729000180/2026/290) |
| ART/RRT de execução | "demonstre a Anotação de Responsabilidade Técnica – ART ou o Registro de Responsabilidade Técnica – RRT, relativo à execução dos serviços" | [Mambaí](https://pncp.gov.br/app/editais/01740463000152/2026/169) |
| Normas técnicas da concessionária (Equatorial-GO) | "Sua elaboração foi efetuada obedecendo às normas técnicas da Equatorial – NT-005, NT-006, NT-007 e NT-018" | [Bom Jesus de Goiás](https://pncp.gov.br/app/editais/01149624000138/2026/88) |

Não foi observada, nos 15 textos revisados, exigência de **registro prévio na
concessionária** como documento de habilitação — a menção à concessionária aparece
como norma técnica a seguir na execução do serviço, não como pré-requisito para
participar do certame.

## 8. Recomendação

**Classe: SELETIVO.**

O nicho de locação pura de caminhão com cesto aéreo para manutenção de IP em pequenos
municípios de GO mostra, na amostra revisada, preços de referência do próprio edital
já abaixo do custo direto formal (CLT completo + BDI) — mas a empresa já possui 2
caminhões munck amortizados, o que reduz seu custo marginal real bem abaixo dessa
referência formal. Vale disputar seletivamente esses contratos (de preferência "sem
motorista" ou com motorista já empregado) e os registros de preços mistos
(material + locação de cesto, como Morro Agudo), sempre apurando o custo marginal real
antes de ofertar desconto — evitando o nicho de modernização/eficientização LED e o de
fornecimento puro de material, que estão fora do modelo de negócio (mão de obra +
veículo) e do controle de custo da empresa.

## 9. Limitações

- Amostra muito pequena após revisão manual (8 casos GO + 5 vizinhos, de 121
  revisados) — qualquer mediana/quartil é direcional, não uma estimativa precisa.
- A maioria dos 121 casos coletados são falsos positivos de palavra-chave (eventos,
  decoração natalina, equipamento hospitalar) ou fora do escopo de manutenção
  corretiva (modernização LED em massa, fornecimento puro de material).
- O PNCP não publica número de participantes; o campo ficou nulo em 100% dos casos.
- A coleta (`coletor.py`) ainda estava em andamento em 2026-09-27; o universo desta
  análise (121 casos de IP) reflete só o que já havia sido baixado até essa data.
- Textos de edital/TR foram baixados manualmente nesta análise (fora do
  `coletor.py`) para 15 casos de GO priorizados por relevância; os outros 106 casos
  de IP não têm texto e suas exigências de veículo/habilitação são desconhecidas.
- Para o item 59 do caso de Morro Agudo de Goiás, o resultado individual (valor
  homologado) não foi capturado pela API do PNCP (itens truncados); só o valor
  estimado (R$95,00/h) pôde ser usado na análise de margem.
- Nenhum preço de mercado publicado foi encontrado para adaptação/retrofit de cesto
  aéreo isolado em munck existente; fornecedores só trabalham por orçamento.
- As referências de custo de veículo (SICRO E9690, GOINFRA munck) descrevem
  equipamento novo, plenamente custeado por terceiros; para a empresa (que já possui
  2 munck amortizados), o custo marginal real tende a ser menor — todas as
  classificações de margem usam a referência cheia como premissa conservadora,
  conforme instruído em `PREMISSAS_COMUNS.md`.
- Premissas de horas/mês (88h = 4h/dia mínimo GOINFRA × 22 dias) e de 8h/diária foram
  adotadas para converter contratos mensais/diárias em base horária comparável à
  referência SICRO/GOINFRA, na ausência de detalhamento oficial de utilização nos
  editais.
- Sem CPF ou nome de pessoa física em nenhum campo deste relatório.
