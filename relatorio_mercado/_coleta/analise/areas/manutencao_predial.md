# Manutenção predial (integrada) — estudo de mercado de licitações

Empresa-alvo: engenharia de GO com engenheiro mecânico e eletricista, técnicos/mecânicos de
refrigeração, eletricistas, 2 caminhões munck e veículos leves. **Não tem** equipe própria de
pedreiro, pintor ou encanador. Foco em contratos de mão de obra + deslocamento + materiais
baratos, pagos por medição mensal, baixo investimento.

Fonte dos dados: `W/analise/casos.jsonl` (90 casos que batem em `manutencao_predial`, em `areas`
ou `area_principal` — 49 em GO, 41 em vizinhos), 43 dos 90 com texto de edital/TR já baixado em
`W/textos`, `W/custos/custos/referencias.json` e `W/analise/PREMISSAS_COMUNS.md` (acesso
27/09/2026).

## 1. Revisão da classificação — o achado central desta área

A área "manutenção predial integrada" só interessa à empresa quando o **núcleo elétrica +
climatização** é relevante (≥ ~40% do valor). Como a heurística automática (`casos.py`) não mede
essa fração, cada um dos 90 casos foi revisado manualmente, com uma cadeia de evidência de
qualidade decrescente: (1) valor real por item do PNCP quando os itens são discriminados por
disciplina; (2) frequência de palavras-chave de disciplina no texto integral do edital/TR
(quando baixado); (3) disciplinas citadas no objeto da compra; (4) sem evidência — tratado
conservadoramente como `fora_escopo`.

**Resultado: dos 49 casos de GO, apenas 2 (4%) têm núcleo elétrica+climatização comprovadamente
≥ 40%.** Os outros 47 foram excluídos:

| Motivo de exclusão | GO | Vizinhos |
|---|---:|---:|
| `fora_escopo` (núcleo < 40% ou sem evidência de núcleo relevante) | 29 | 18 |
| `fornecimento_puro` (aquisição pura de material) | 12 | 11 |
| `equipamento_alto` | 3 | 2 |
| `mencao_passagem` | 2 | 0 |
| `obra_grande` | 1 | 0 |
| **Total excluído** | **47** | **31** |
| **Total incluído** | **2** | **10** |

**Por que tão poucos casos são incluídos:** ao ler os editais/TRs disponíveis, o padrão mais
comum de "manutenção predial" no mercado público de GO é **dominado por civil** (pedreiro,
servente, pintor, serralheiro, carpinteiro) e por **serviços de limpeza/copeiragem/jardinagem**
disfarçados de "conservação predial" — exatamente os serviços que a empresa-alvo **não** tem
equipe própria para executar. Três achados importantes:

1. **Falso-positivo recorrente:** vários processos com objeto mencionando "conservação predial"
   são, na prática, contratos de **limpeza/copeiragem/jardinagem** (ex.: 3 processos da Justiça
   Eleitoral de GO, ~R$ 10 milhões somados), sem qualquer papel para eletricista ou técnico de
   climatização — núcleo = 0%.
2. **Único caso com planilha real de postos de trabalho** (SEINFRA-GO,
   `35840659000130_2026_27`, R$ 3,66 milhões, 17 itens com valor unitário por posto) revelou um
   núcleo real de apenas **12,8%** — muito abaixo do que a frequência textual (o método usado nos
   2 casos incluídos) teria sugerido (47,9% pelo mesmo método). Isso é um **sinal de alerta**: os
   2 casos incluídos de GO (núcleo estimado em 52,2% e 56,3% por frequência textual, não por
   planilha de custos) podem estar **superestimados**.
3. **Casos que são obra, aquisição de material ou automação nova** foram corretamente excluídos
   (ex.: reforma/ampliação/demolição de R$ 17,1 milhões em Senador Canedo → `obra_grande`;
   sistema de automação predial novo da ALEMT/SENAPREV → `equipamento_alto`).

Também **reclassificamos** 4 casos da heurística automática: 2 tiveram o motivo corrigido de
`fornecimento_puro` para `fora_escopo` (são serviços reais de mão de obra mal cadastrados como
material pelo órgão, mas com núcleo 0% — civil/pintura puros), e 3 foram reclassificados de
excluído para incluído (2 por serem manutenção elétrica real mal cadastrada como material, 1 por
ser o mesmo processo de manutenção de climatização já incluído em `climatizacao.json`).

## 2. Indicadores (recalculados com a classificação revisada)

| Indicador | GO | Vizinhos |
|---|---:|---:|
| Casos incluídos (amostra detalhada) | **2** | **10** |
| Volume/ano — índice de busca completo (aceitos ÷ 2 anos) | ~24/ano | ~111/ano |
| Valor total estimado (amostra incluída) | R$ 39.089.712,38 | R$ 31.067.164,08 |
| Ticket mediano | R$ 19.544.856,19 | R$ 626.638,22 |
| Desconto — mediana | 15,8% | 15,5% |
| Desconto — Q1 / Q3 | 15,4% / 16,1% | 6,9% / 26,2% |
| Descontos suspeitos descartados (<0% ou >90%) | 0 de 2 | 0 de 9 |
| % deserta ou fracassada | 0% | 0% |
| % exclusiva ME/EPP | 0% | 0% |
| % exclusiva parcial ME/EPP | 0% | 10% |
| % contrato continuado | 0% | 60% |
| % pontual | 100% | 40% |

**Atenção:** a amostra de GO incluída é de **apenas 2 casos** — os números de ticket/desconto de
GO não são estatisticamente robustos, servem só como sinal pontual. A de vizinhos (10 casos)
também é pequena. O volume/ano do índice de busca (~24/ano em GO) é muito maior que os casos
incluídos porque **a maioria dos processos que batem em "manutenção predial" na busca textual são
fora_escopo** (limpeza, civil puro, obras, ou fornecimento de material) — não existe um volume de
24 processos/ano relevantes para a empresa-alvo em GO.

Descontos observados (15-16%) são **bem menores** que os das áreas de núcleo puro (ex.:
climatização, mediana 44,3% em GO) — sinal de margens mais conservadas nesta área, provavelmente
pelo risco trabalhista de mão de obra alocada e pela garantia contratual quase sempre exigida.

**Nº de participantes:** o PNCP não publica esse número; ficou `null` em todos os casos.

## 3. Casos exemplares de GO

| Categoria | Órgão/Município | Valor estimado | Status | Link PNCP |
|---|---|---:|---|---|
| Incluído — dedicação exclusiva, núcleo elétrica ~52% | TRT da 18ª Região (comarcas do interior) | R$ 1.880.859,16 | **Incluído** | [link](https://pncp.gov.br/app/editais/00509968000148/2025/160) |
| Incluído — maior contrato da amostra, 6 lotes regionais | TJGO (comarcas do interior) | R$ 37.208.853,22 | **Incluído** | [link](https://pncp.gov.br/app/editais/01409580000138/2026/387) |
| Ilustrativo — 100% civil, zero elétrica/climatização | Município de São Domingos-GO | R$ 1.472.292,35 | Excluído (`fora_escopo`) | [link](https://pncp.gov.br/app/editais/01068014000100/2026/132) |
| Ilustrativo — limiar de obra grande | Município de Senador Canedo-GO | R$ 17.123.285,63 | Excluído (`obra_grande`) | [link](https://pncp.gov.br/app/editais/25107525000151/2025/160) |
| Ilustrativo — falso-positivo (é limpeza/jardinagem) | TSE — Justiça Eleitoral de GO | R$ 4.862.877,21 | Excluído (`fora_escopo`) | [link](https://pncp.gov.br/app/editais/00509018000113/2025/1112) |

Detalhes (resumo, vencedor, núcleo estimado) em `manutencao_predial.json > exemplares`.

## 4. Margem em 3 casos típicos

**Premissas de custo comuns** (fonte: `PREMISSAS_COMUNS.md` + `referencias.json`,
acesso 2026-09-27): eletricista/técnico de refrigeração carregado R$ 6.486,97/mês; ajudante
carregado R$ 3.542,26/mês; periculosidade NR-10 +30% sobre salário-base do eletricista;
engenheiro RT R$ 23.324,24/mês em tempo integral; BDI (TCU 2622/2013, composição "Construção de
Edifícios"): preço com lucro = custo×1,2624; preço de lucro zero = custo×1,1754.
**Subcontratação da parte civil** modelada com margem de repasse de 15% (estimativa declarada
pelo enunciado do estudo, sem base de mercado verificada): a empresa fatura ao cliente o valor de
mercado do bloco civil/hidráulica, mas paga ao subcontratado 85% desse valor.

| Caso | Escopo | Núcleo | Custo direto próprio | Preço venda modelado (c/ repasse civil) | Preço lucro zero total | Vencedor real | Classificação |
|---|---|---:|---:|---:|---:|---:|---|
| A — TRT-18 (GO) | Manutenção predial c/ dedicação exclusiva, comarcas do interior | 52,2% | R$ 429.615 | R$ 1.345.319 | R$ 1.187.497 | R$ 1.628.592 | **Folgado** |
| B — TJGO, 1 lote regional (GO) | Manutenção predial + jardinagem, 6 lotes de ~R$ 6,2 mi cada | 56,3% | R$ 1.001.275 | R$ 3.974.054 | R$ 3.480.436 | R$ 5.181.333 | **Folgado** (alta incerteza de escopo — item genérico) |
| C — EBC/DF (vizinho) | Climatização predial + AC veicular + refrigeração, sem parte civil | 99,5% | R$ 292.346 | R$ 369.057 (preço c/ BDI, sem repasse) | R$ 343.623 | R$ 350.667 | **Apertado** |

**Leitura importante:** os 2 casos de GO (A e B) aparentam "folgados", mas dependem de uma
estimativa de núcleo por **frequência textual**, não por planilha de custos real — e o único caso
com planilha real (SEINFRA-GO, fora da amostra de margem por ter núcleo de apenas 12,8%) sugere
que essa estimativa pode superestimar o núcleo real. O caso C (núcleo comprovado por item, sem
necessidade de subcontratação civil) teve margem **apertada** apesar do núcleo puro — o desconto
vencedor (44%) foi mais agressivo que nos casos de GO. Detalhes completos em
`manutencao_predial.json > margem`.

## 5. Investimento inicial

Conforme `PREMISSAS_COMUNS.md`: folha de 2 meses + estoque inicial + mobilização + garantia de 5%
do valor anual. Nesta área, quando há **dedicação exclusiva de mão de obra com subcontratação da
parte civil**, soma-se um componente extra: **capital de giro para pagar o subcontratado antes de
receber a medição do órgão** (2 meses de defasagem).

| Porte | Total estimado | Classe |
|---|---:|---|
| Pequeno (lote/contrato municipal continuado, ~R$150-700 mil/ano, pouca subcontratação) | R$ 30.000 a R$ 80.000 | Baixo |
| Médio (tipo TRT-18, ~R$1,5-2 milhões/ano, dedicação exclusiva + subcontratação civil) | R$ 200.000 a R$ 330.000 | Alto |
| Grande (tipo lote regional TJGO, ~R$1,2 milhão/ano/lote, múltiplas comarcas) | R$ 300.000 a R$ 500.000 | Alto |

Note que, diferente das áreas de núcleo puro (climatização/elétrica predial, onde o investimento
"pequeno/médio" costumava ficar abaixo de R$ 150 mil), aqui a **subcontratação da parte civil
eleva o porte de investimento para "alto" já no caso médio**, por causa do capital de giro
necessário para pagar o subcontratado adiantado.

## 6. Regras práticas de lance

- Amostra de GO extremamente pequena (2 casos) — os quartis de desconto (15,4%-16,1%) não são
  estatisticamente robustos.
- A amostra de vizinhos (10 casos) mostra desconto mediano de 15,5% (Q1 6,9%, Q3 26,2%) —
  consistentemente menor que áreas de núcleo puro, sinal de margens mais conservadoras nesta área.
- **Dedicação exclusiva de mão de obra é frequente** (observada nos 2 únicos casos incluídos de
  GO) — isso **impede a opção pelo Simples Nacional** (configura cessão de mão de obra para fins
  tributários, confirmado literalmente no TR do TRT-18) e **obriga garantia contratual**
  (diferente de climatização, onde a garantia era frequentemente dispensada em contratos sem
  dedicação exclusiva).
- **O maior achado:** ~59% dos processos de "manutenção predial integrada" em GO foram excluídos
  por falta de evidência de núcleo relevante — muitos são limpeza/copeiragem/jardinagem
  disfarçados de "conservação predial", ou contratos genuinamente dominados por civil e
  hidráulica, exatamente o padrão que a empresa-alvo não tem equipe própria para executar.
- Quando existe planilha real de postos de trabalho (único caso observado com esse detalhe), o
  núcleo medido caiu para 12,8% — recomenda-se **sempre pedir/ler a planilha de postos completa**
  antes de decidir participar de um processo específico desta área, mesmo quando o objeto parece
  favorável.
- Munck/guindauto/cesto aéreo: **não encontrado** em nenhum dos textos lidos para esta área —
  mesmo padrão de climatização. Os 2 munck da empresa tendem a ficar ociosos aqui.
- Subcontratação de postos individuais é operacionalmente mais simples quando **não** há
  dedicação exclusiva nominal fiscalizada; quando há, confirme se o edital permite subcontratação
  de posto ou exige vínculo direto da empresa vencedora.

## 7. Exigências de habilitação recorrentes

| Exigência | Recorrência | Evidência |
|---|---|---|
| CREA + Responsável Técnico com ART | 2/2 casos incluídos de GO e 4/8 textos verificados | TRT-18: "comprovar registro no CREA (...) comprovando atividade relacionada com o objeto" |
| Dedicação exclusiva de mão de obra (efeito tributário) | TRT-18 e ~10 outros objetos revisados | TRT-18: "a ME/EPP não poderão se beneficiar do Simples Nacional (...) configura cessão de mão de obra" |
| Garantia contratual (1º pagamento) | Exigida no caso detalhado lido (TRT-18) — diferente de climatização | TRT-18: "Será verificada, por ocasião do 1º pagamento, apresentação da garantia contratual" |
| Quadro de pessoal / postos nominais | Presente nos contratos com dedicação exclusiva | SEINFRA-GO: item "Prestação de Serviços de Eletricista" com valor próprio de R$391.338,24/5 anos |
| Munck/guindauto/cesto aéreo | **Não encontrado** em nenhum texto lido | — |
| Frota mínima / veículo | Baixa (1 menção genérica de "caminhão") | — |

## 8. Recomendação

**Classe: evitar como área autônoma / seletivo apenas caso a caso.**

O mercado de "manutenção predial integrada" em GO é majoritariamente dominado por civil e por
serviços de limpeza/jardinagem — apenas 2 de 49 casos de GO (4%) tiveram núcleo elétrica +
climatização comprovadamente relevante. Como a empresa-alvo não tem equipe própria de pedreiro,
pintor ou encanador, participar exigiria subcontratar a maior parte do escopo na maioria dos
processos reais, diluindo a vantagem competitiva (elétrica + climatização) e adicionando risco de
gestão de subcontratados — inclusive risco trabalhista solidário quando há dedicação exclusiva de
mão de obra. **Recomenda-se não perseguir esta área como linha de negócio própria**, manter o foco
nas áreas de núcleo puro (elétrica_predial, climatização, refrigeração), e avaliar
oportunisticamente, caso a caso, apenas processos cujo edital/TR discrimine explicitamente um
núcleo elétrica+climatização ≥ 40% com planilha de postos clara — exigindo due diligence da
planilha de custos **antes** de decidir participar, dado que a única vez em que encontramos uma
planilha real (SEINFRA-GO) revelou um núcleo de apenas 12,8%, muito abaixo do estimado por método
textual nos 2 casos hoje classificados como incluídos.

## Limitações

- O PNCP não publica número de participantes/licitantes; o campo fica `null` em todos os casos.
- Amostra de GO incluída é mínima (2 casos) — indicadores de ticket/desconto não são robustos.
  Amostra de vizinhos (10 casos) também é pequena e cobre só ~4,5% do volume aceito pelo índice de
  busca (222 aceitos/2 anos vs 41 casos detalhados).
- `nucleo_eletr_clim_pct` é uma cadeia de estimativas de qualidade decrescente (item real > texto
  integral > objeto > sem evidência) — nenhuma é uma planilha de custos oficial por disciplina. O
  único caso com planilha real (SEINFRA-GO) revelou núcleo de 12,8%, muito abaixo do que o método
  de frequência textual (usado nos 2 casos incluídos de GO, 52,2% e 56,3%) sugeriria — os 2 casos
  incluídos devem ser tratados com cautela adicional.
- Apenas 43 dos 90 casos tinham texto de edital/TR baixado no momento desta análise (coleta
  principal em andamento); os demais 47 foram classificados só pelo objeto do PNCP, o que
  provavelmente subestima o número de casos verdadeiramente incluídos.
- 4 casos foram reclassificados nesta revisão (3 de excluído para incluído, 2 tiveram o motivo
  corrigido de `fornecimento_puro` para `fora_escopo`) — ver campo `justificativa` de cada decisão
  em `manutencao_predial.json`.
- Caso `03501525000107_2025_110` tem `valor_estimado_total = R$0,00` (anomalia de cadastro,
  provável duplicata de `03501525000107_2026_15` do mesmo órgão) — mantido incluído para
  classificação, mas excluído do cálculo de ticket/desconto. Casos `24672727000183_2026_28` e
  `03773942000109_2026_20` têm valores inválidos (R$0,00 e R$5,00) e não contribuem para os
  indicadores.
- Dedicação exclusiva de mão de obra, frequente nesta área, impede a opção pelo Simples Nacional
  — diferente de outras áreas onde essa opção pode melhorar a margem real acima do modelo (BDI
  padrão, regime presumido) usado aqui.
- Margem de repasse de 15% na subcontratação da parte civil é uma estimativa declarada pelo
  enunciado do estudo, sem base de mercado verificada nesta pesquisa.
