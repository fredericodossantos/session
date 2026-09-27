# Iluminação pública — estudo de mercado (Goiás e vizinhos)

**Atualização (rodada 2):** custo do veículo recalculado com o munck PRÓPRIO da empresa
(não mais locação de equipamento novo), novo método de `desconto` (preço unitário do
1º colocado, ponderado pelo valor de cada item), 1 compra suplementar de GO
classificada, e ampliação da estatística de exigência de veículo com os textos novos
da fase 4 da coleta.

Manutenção corretiva e preventiva do parque de IP, pequenas extensões de rede e
poda/manutenção com caminhão. Dados do PNCP (`W/analise/casos.jsonl`, 138 casos de IP:
95 GO + 43 vizinhos — TO e MG entraram na coleta), complementados com o texto de 15
editais/TR de GO baixados manualmente + 22 baixados pela fase 4 do coletor (37 textos
no total, todos em GO).

**Amostra pequena.** Após revisão manual: **9 casos incluídos em GO** e **8 em
vizinhos**, de 138 revisados — a maioria é falso positivo (eventos "som/palco/
iluminação", decoração natalina) ou fora do escopo (modernização LED em massa,
fornecimento puro de material).

## 1. Revisão da classificação

| Grupo | Casos revisados | Incluídos | Exclusões por motivo |
|---|---|---|---|
| GO | 95 | **9** | `fornecimento_puro` 49, `mencao_passagem` 25, `equipamento_alto` 12, `obra_grande` 1 |
| Vizinhos (TO+MG+DF+MT+MS) | 43 | **8** | `mencao_passagem` 15, `fornecimento_puro` 14, `equipamento_alto` 4, `obra_grande` 1 |

Novidade da rodada 2: a compra suplementar de GO (Buriti Alegre,
`01345909000144/2026/113`) foi reclassificada de excluída (`mencao_passagem`, engano da
heurística) para **incluída** — é um contrato contínuo de manutenção de IP com mão de
obra + veículo, o núcleo exato do modelo de negócio da empresa. Entre os 16 novos casos
de TO/MG, destaque para Coimbra/MG (manutenção corretiva/preventiva, miscodificada como
fornecimento) e o consórcio COMASF/MG (manutenção multimunicipal, valor 0,6% acima do
limiar de obra grande por causa de um item de telemetria/software, não de expansão de
rede) — ambos reclassificados para incluídos. Também reclassifiquei para excluídos 3
modernizações de LED em massa que a heurística havia deixado passar (Gurupi/TO R$5,0mi;
CIMVALES/MG R$102,7mi; Lagoa Santa/MG R$1,55mi, este último por cruzar o limiar de obra
grande). Decisão completa (138 casos) em `iluminacao_publica.json`, campo `decisoes`.

## 2. Indicadores finais (recalculados com o novo `desconto`)

| Indicador | GO (n=9) | Vizinhos (n=8) |
|---|---|---|
| Valor estimado total | R$ 3.037.357,99 | R$ 4.732.940,15 |
| Valor homologado total | R$ 1.788.602,28 | R$ 4.211.436,78 |
| Ticket mediano (homologado) | R$ 154.800,00 | R$ 555.405,36 |
| Desconto — mediana / Q1 / Q3 (novo método) | 25,2% / 7,5% / 42,3% | 0,0% / 0,0% / 8,4% |
| % deserta/fracassada | 0,0% | 0,0% |
| % ME/EPP | 0,0% | 12,5% |
| % contínuo | 33,3% | 25,0% |

- **Nº de participantes**: PNCP não publica; `null` em 100% dos 138 casos.
- **Método do desconto**: recalculado com o novo campo (preço unitário do 1º colocado,
  ponderado pelo valor de cada item), conforme instruído.

## 3. Exigência de veículo (ampliada com os textos novos)

37 dos 138 casos têm texto de edital/TR (todos em GO), mas só **6** tratam de
locação/exigência de veículo: **3 aceitam munck/guindauto com cesto acoplado**
(Três Ranchos — confirmado pelo campo automático `aceita_munck_com_cesto`; Itaguari —
confirmado só por leitura manual, grafia "cesta aérea" que o regex automático não
reconhece; Corumbaíba — por indução textual), **2 pedem veículo/plataforma isolada sem
ser necessariamente munck** (Pontalina; e o caso suplementar de Buriti Alegre, que
**marca explicitamente `aceita_munck_com_cesto=False`** e pede um veículo utilitário
leve com cesto isolado 46kV/136kg) e **1 não detalha** (Morro Agudo). Achado
importante: em Itaguari o edital põe o **combustível por conta do órgão** (cláusula
11.1), o que muda bastante a economia do contrato (ver seção 4).

## 4. Margem — CORREÇÃO DE PREMISSA (custo do munck próprio)

Custo do caminhão munck **próprio** da empresa (`munck.json/premissas_custo`, BDI
"Construção de Edifícios" já embutido nas colunas de lucro zero/BDI, conforme adendo
de `PREMISSAS_COMUNS.md`):

| Combustível por conta de | Custo direto | Preço lucro zero | Preço com BDI |
|---|---:|---:|---:|
| Contratada | R$ 186,77/h | R$ 219,55/h | R$ 235,82/h |
| Órgão | R$ 71,30/h | R$ 83,80/h | R$ 90,02/h |

A adaptação de cesto aéreo no munck **não** entra no custo por hora — é investimento a
cotar (sem preço de mercado publicado; ver seção 5).

| Caso | Premissa (quem paga combustível) | Custo direto | Lucro zero | BDI | Homologado | Classificação (rodada 2) | Classificação (rodada 1, referência SICRO) |
|---|---|---:|---:|---:|---:|---|---|
| Corumbaíba (1.000h/ano) | Contratada (confirmado) | R$ 186.770 | R$ 219.550 | R$ 235.820 | R$ 180.000 | **Prejuízo provável** (raspando o custo direto) | Prejuízo provável (extremo) |
| Três Ranchos (diária=8h) | Contratada (assumido) | R$ 1.494 | R$ 1.756 | R$ 1.887 | R$ 645 | **Prejuízo provável** | Prejuízo provável (extremo) |
| Itaguari (88h/mês) | **Órgão (confirmado, cláusula 11.1)** | R$ 6.274 | R$ 7.374 | R$ 7.922 | R$ 12.000 | **FOLGADO** | Prejuízo provável |
| Pontalina (88h/mês) | Contratada (assumido) / Órgão (sensibilidade) | R$ 16.436 / R$ 6.274 | R$ 19.320 / R$ 7.374 | R$ 20.752 / R$ 7.922 | R$ 7.561 | **Prejuízo (contratada) / Apertado (órgão)** | Prejuízo provável (extremo) |
| Morro Agudo item 59 (3.000h/ano) | Contratada (assumido) | R$ 560.310 | R$ 658.650 | R$ 707.460 | R$ 285.000 (estimado; homologado não capturado) | **Prejuízo provável** | Prejuízo provável (extremo) |

**Mudança central**: ao trocar a referência de "equipamento novo alugado" (SICRO,
R$330,89/h) pelo custo do munck **próprio** da empresa, a margem melhora muito —
Itaguari vira **folgado** só porque o combustível é do órgão. A cláusula de quem paga o
combustível é o fator que mais muda a classificação nesse nicho; deve ser conferida
antes de qualquer lance.

## 5. Investimento inicial (atualizado)

| Porte | Exemplo | Total (caução) | Total (seguro-garantia) | Classe |
|---|---|---:|---:|---|
| Pequeno | Locação mensal, combustível do órgão (tipo Itaguari), ~R$144 mil/ano | R$ 24.323 | ~R$ 18.023 | Baixo |
| Médio | Caminhão com motorista, combustível da contratada (tipo Corumbaíba/Três Ranchos), ~R$180-210 mil/ano | R$ 70.051 | ~R$ 61.538 | Médio |
| Grande | Contrato contínuo de mão de obra + veículo (tipo Buriti Alegre escalado), ~R$800 mil-1 milhão/ano | R$ 217.889 | ~R$ 178.514 | Alto (caução) / Médio-alto (seguro) |

**Adaptação de cesto aéreo em munck existente**: nenhum preço de mercado publicado foi
encontrado (fornecedores só cotam sob consulta). Entra como investimento a cotar
diretamente com fabricantes (Fibras Cestos Aéreos, IW8, Auto Cranes) — um caminhão 0km
já equipado de fábrica custou R$747.666,67 (Jataí/GO), mas serve só como teto de
referência, não como custo de adaptação.

## 6. Regras práticas de lance

- Desconto típico em GO (n=9, novo método): mediana 25,2%, Q1 7,5%, Q3 42,3%.
- **Regra prática central**: confirmar no edital quem paga o combustível antes de
  decidir o desconto — essa única cláusula muda a classificação entre "prejuízo
  provável" e "folgado"/"apertado" em pelo menos 2 dos 5 casos analisados.
- Contratos "sem motorista" com combustível do órgão (Itaguari) são os mais atrativos
  da amostra.
- RPs mistos (material + locação de cesto) e contratos contínuos de mão de obra +
  veículo (Buriti Alegre) tendem a ser mais atrativos que RPs de material puro.

## 7. Exigências de habilitação (com o achado novo de Buriti Alegre)

| Exigência | Evidência | Caso |
|---|---|---|
| CREA/CAU | "junto ao CREA ou ao CAU, em nome da licitante" | Buriti Alegre |
| Atestado com quantidade mínima de pontos de IP | "rede aérea energizada, no mínimo 1.452 pontos" | Buriti Alegre |
| Veículo com cesto aéreo isolado (espec. técnica) | "cesto aéreo... isolado 46KV, capacidade até 136 kg" | Buriti Alegre |
| Combustível por conta do contratante | "Arcar com o abastecimento do veículo durante todo o período" | Itaguari |
| Atestado de locação de veículo | "contrato de locação de veículo pertinente" | Pontalina |
| NR-10/NR-12/NR-35 | "NR-10 e NR-12" / "treinamento em NR-35" | Jataí |
| ART/RRT | "Anotação de Responsabilidade Técnica – ART ou RRT" | Mambaí |

## 8. Recomendação

**Classe: SELETIVO / atacar em subnicho.** Com o custo do munck próprio, o nicho de
locação de caminhão com cesto aéreo melhora bastante quando o combustível é do órgão
(Itaguari já é folgado). Atacar contratos com essa cláusula e o modelo de manutenção
contínua com mão de obra + veículo (Buriti Alegre); evitar modernização LED em massa e
fornecimento puro de material.

## 9. Limitações

- Amostra pequena (9 GO + 8 vizinhos de 138).
- PNCP não publica nº de participantes.
- Coleta em andamento; 37/138 casos têm texto, todos em GO.
- Item 59 de Morro Agudo sem resultado individual capturado (itens truncados).
- Quem paga combustível não está explícito em 3 dos 5 casos de margem (assumido
  "contratada" como premissa conservadora, com sensibilidade mostrada para Pontalina).
- Nenhum preço de retrofit de cesto aéreo em munck existente foi encontrado.
- Campo automático `aceita_munck_com_cesto` subestima aceitação real (não reconhece
  "cesta aérea" como variante de "cesto aéreo").
- Sem CPF ou nome de pessoa física em nenhum campo.
