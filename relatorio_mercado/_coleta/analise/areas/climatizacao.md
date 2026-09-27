# Climatização — estudo de mercado de licitações (GO + vizinhos)

Empresa-alvo: engenharia de GO com engenheiro mecânico e eletricista, técnicos/mecânicos de
refrigeração, eletricistas, 2 caminhões munck e veículos leves. Foco em contratos de
mão de obra + deslocamento + materiais baratos, pagos por medição mensal, baixo investimento.

Fonte dos dados: `W/analise/casos.jsonl` (117 casos de climatização, GO + vizinhos),
`W/custos/custos/referencias.json` e `W/analise/PREMISSAS_COMUNS.md`. A coleta (`coletor.py`)
ainda estava em andamento no momento desta análise (27/09/2026); `W/textos` estava vazio para
climatização, por isso 5 editais/TRs foram baixados manualmente via API de arquivos do PNCP
(limite do enunciado) para checar exigências de habilitação.

## 1. Revisão da classificação heurística

A heurística automática (`casos.py`) julgou 117 casos de climatização (91 em GO, 26 em
vizinhos). Revisamos manualmente todo caso excluído (`exclusao.motivo` preenchido) e todo caso
com `revisao_manual=true`, lendo o objeto completo e, quando necessário, os itens do
`W/compras/{id}.json`.

**24 casos foram reclassificados de excluído → incluído** (22 em GO, 2 em vizinhos), por dois
padrões recorrentes:

1. **Itens de serviço cadastrados como "Material" pelo órgão** (16 casos). Ex.: contratos de
   "manutenção preventiva e corretiva com fornecimento de peças e instalação" em que todos os
   itens do PNCP vieram com `materialOuServico=M`, embora o objeto seja claramente um serviço
   continuado de mão de obra + peças por demanda. Conforme a diretriz do estudo ("manutenção com
   fornecimento de peças por demanda é serviço"), esses casos foram incluídos.
2. **A heurística reagiu à palavra "VRF"/"chiller"/"implantação" descrevendo manutenção de um
   sistema JÁ EXISTENTE, não fornecimento de equipamento novo** (7 casos de `equipamento_alto`
   + 1 de `obra_grande`). Ex.: "serviços continuados de manutenção preventiva e corretiva dos
   sistemas centrais de ar-condicionado com chillers... por 5 anos" é manutenção, não compra de
   chiller; "implantação de PMOC" é a implantação de um *documento/plano de gestão*, não de uma
   obra.

Por outro lado, **confirmamos a exclusão** de 40 casos que são genuinamente aquisição pura de
aparelhos/materiais (ex.: "aquisição de ar-condicionado 24.000 BTUs para a Secretaria de
Educação", emendas parlamentares de compra e instalação de um único aparelho em uma escola,
registros de preços de compra de climatizadores/bebedouros), 8 casos de fornecimento +
instalação de chiller/VRF novo ou fração de material real > 40% sem sinal de manutenção
continuada, 1 caso de obra grande genuína (implantação de rede, não PMOC) e 1 caso de menção de
passagem (um "container climatizado" dentro de um serviço de gestão documental, nada a ver com
climatização).

**Resultado final:** de 117 casos de climatização, **85 foram incluídos** (68 em GO, 17 em
vizinhos) e 32 excluídos. O arquivo `climatizacao.json` traz a decisão (`incluido`, `motivo`,
`justificativa` de 1 linha) para cada um dos 117 casos.

| Motivo de exclusão (casos confirmados, após revisão) | GO | Vizinhos |
|---|---:|---:|
| `fornecimento_puro` (compra pura de aparelhos/materiais) | 19 | 4 |
| `equipamento_alto` (fornecimento+instalação de chiller/VRF novo, ou fração material real >40%) | 4 | 4 |
| `obra_grande` | 0 | 0 |
| `mencao_passagem` | 0 | 1 |
| **Total excluído** | **23** | **9** |

## 2. Indicadores finais (recalculados com a classificação revisada)

**Cobertura da amostra:** em GO, `casos.jsonl` tem 91 processos detalhados de climatização
contra 92 aceitos pelo índice de busca (`selecao.jsonl`) — cobertura de ~99%, alta confiança.
Em vizinhos (DF+MT+MS+TO+MG), há apenas **26 processos detalhados** contra **~450
aceitos pelo índice** (~225/ano) — cobertura de só ~11,6%. **Os números de "vizinhos" abaixo
são direcionais, não uma estimativa robusta de mercado** (amostra pequena).

| Indicador | GO | Vizinhos |
|---|---:|---:|
| Casos incluídos (amostra detalhada) | 68 | 17 |
| Volume/ano — índice de busca completo (aceitos ÷ 2 anos) | ~46/ano | ~225/ano |
| Valor total estimado (soma da amostra detalhada incluída) | R$ 68.981.675,34 | R$ 24.701.139,22 |
| Ticket mediano | R$ 495.312,09 | R$ 626.638,22 |
| Desconto — mediana | 44,34% | 32,56% |
| Desconto — 1º quartil (Q1) | 24,67% | 14,03% |
| Desconto — 3º quartil (Q3) | 60,23% | 43,00% |
| Descontos suspeitos descartados (<0% ou >90%) | 2 de 68 | 1 de 17 |
| % deserta ou fracassada (algum item) | 5,88% | 11,76% |
| % exclusiva ME/EPP (todo o objeto) | 5,88% | 11,76% |
| % exclusiva parcial ME/EPP | 5,88% | 11,76% |
| % contrato continuado (sinal textual) | 14,71% | 11,76% |
| % pontual | 41,18% | 58,82% |
| % indefinido (sem sinal textual de vigência) | 44,12% | 29,41% |

**Nº de participantes:** o PNCP não publica esse número; o campo fica `null` em praticamente
todos os casos. Nenhum dos 5 editais/TRs lidos integralmente nesta análise mencionava
explicitamente uma contagem de participantes.

**Nota sobre `% continuado`/`% indefinido`:** a área de climatização é uma das que recebem
download de texto do edital/TR (ao contrário de `refrigeracao`), mas como a coleta de textos
ainda não havia rodado no momento desta análise, `tipo_contrato` ficou `"indefinido"` para 44%
dos casos de GO por falta de sinal textual — na prática, muitos desses são contratos continuados
(o objeto já fala em "serviços continuados", mas a regex de vigência não encontrou o número de
meses). Isso deve melhorar quando `W/textos` for populado.

## 3. Casos exemplares de GO

| Categoria | Órgão/Município | Valor estimado | Valor homologado | Link PNCP |
|---|---|---:|---:|---|
| Contrato continuado por aparelho (frequência definida) | FMEB — Palmeiras de Goiás | R$ 310.149,30 | R$ 197.900,00 | [link](https://pncp.gov.br/app/editais/55262249000167/2025/40) |
| PMOC | Município de Anápolis | R$ 2.466.726,24 | R$ 937.000,00 | [link](https://pncp.gov.br/app/editais/01067479000146/2026/118) |
| Instalação/manutenção por demanda (equipamento normalmente já do órgão) | Fundo Municipal de Saúde — Bela Vista de Goiás | R$ 359.134,17 | R$ 215.000,00 | [link](https://pncp.gov.br/app/editais/08083086000175/2026/13) |
| ME/EPP exclusivo + PMOC | TRE-GO (6 Fóruns/Cartórios do interior) | R$ 43.789,78 | R$ 17.330,00 | [link](https://pncp.gov.br/app/editais/00509018000113/2026/494) |
| Grande porte — sistemas centrais (chiller/VRF) | Assembleia Legislativa de GO | R$ 6.750.000,00 | R$ 4.155.000,00 | [link](https://pncp.gov.br/app/editais/01409580000138/2025/11) |

Detalhes (resumo do objeto, vencedor, porte) estão em `climatizacao.json > exemplares`.

## 4. Margem em 5 casos típicos

**Premissas de custo comuns** (fonte: `PREMISSAS_COMUNS.md` + `referencias.json`,
acesso 2026-09-27):

- Equipe técnico + ajudante, custo mensal carregado (salário-base × 1,6928 de encargos + R$
  495,88 de VA + R$ 150 de EPI): **R$ 6.486,97/mês** (técnico) + **R$ 3.542,26/mês**
  (ajudante) = **R$ 10.029,23/mês de equipe**, ÷ 220 h/mês = **R$ 45,59/hora-equipe**
  (técnico+ajudante juntos).
- Engenheiro RT (Lei 4.950-A, R$ 13.778,50/mês carregado com encargos = R$ 23.324,24/mês em
  tempo integral); fração de dedicação de 8% a 20% conforme a complexidade do contrato.
- Gás refrigerante: R$ 81,63/kg (R410A, média Multifrio/Frigelar) e R$ 74,53/kg (R22, média de
  3 fontes).
- Capacitor de partida: R$ 33,50/unidade (média da faixa R$22-45 informada).
- Tubo de cobre 1/4": R$ 14,80/metro.
- Veículo leve: R$ 1,20/km.
- BDI (fórmula TCU 2622/2013, composição "Construção de Edifícios", AC 4,00%/S+G 0,80%/R
  1,27%/DF 1,23%/L 7,40%/T 8,65%): **preço com lucro = custo direto × 1,2624**; **preço de
  lucro zero = custo direto × 1,1754**.
- **Limitação importante:** não há preço de referência nas fontes coletadas para placa
  eletrônica, turbina/motoventilador, hélice de motor ventilador e peças específicas de
  chiller/VRF — nesses itens só a mão de obra da troca foi custeada, o que faz os cálculos
  abaixo **subestimarem o custo real** nessas linhas específicas (a classificação "folgado" é
  então um piso otimista, não uma garantia). O compressor usa como proxy um compressor
  doméstico de geladeira 1/4HP (única referência disponível), o que também tende a subestimar
  compressores maiores.

| Caso | Escopo interpretado | Custo direto | Preço lucro zero | Preço c/ BDI | Homologado | Classificação |
|---|---|---:|---:|---:|---:|---|
| A — Palmeiras de Goiás | 151 aparelhos, preventiva 2x/ano + corretiva/recarga/instalação sob demanda | R$ 141.529,61 | R$ 166.356,80 | R$ 178.667,21 | R$ 197.900,00 | **Folgado** |
| B — TRE-GO (6 comarcas) | ~3 aparelhos/comarca × 2 visitas PMOC/ano (premissa; item do PNCP é um lote genérico por comarca) | R$ 7.008,18 | R$ 8.237,56 | R$ 8.847,14 | R$ 17.330,00 | **Folgado** |
| C — Bela Vista de Goiás | 29 itens de instalação/manutenção por demanda (6k-60k BTU), incl. 900 higienizações/ano no teto do RP | R$ 161.383,28 | R$ 189.693,21 | R$ 203.730,51 | R$ 215.000,00 | **Folgado** (margem apertada: só 5,5% acima do preço com BDI) |
| D — Anápolis (PMOC) | Item único genérico; premissa de ~400 aparelhos no parque público (alta incerteza) | R$ 132.345,78 | R$ 155.561,94 | R$ 167.073,53 | R$ 937.000,00 | **Folgado** |
| E — Assembleia Legislativa GO (chiller/VRF) | Sistemas centrais por 5 anos, item único genérico; escopo modelado por analogia (equipe reforçada em dedicação parcial) | R$ 497.300,74 | R$ 584.537,47 | R$ 627.793,25 | R$ 4.155.000,00 | **Folgado** (mas com incerteza de escopo alta — ver limitações) |

**Leitura importante:** os casos A e C (itens detalhados por aparelho/BTU, típicos da maioria
dos contratos municipais) têm margem de segurança MUITO menor que B/D/E (item único e
genérico, típico de Registros de Preços "guarda-chuva" de órgãos maiores). Isso reflete que o
valor estimado desses RPs guarda-chuva costuma ser muito mais folgado em relação ao custo real
— mas com maior incerteza de escopo (ver seção 6).

## 5. Investimento inicial típico

Conforme `PREMISSAS_COMUNS.md`: folha de 2 meses (pagamento cai perto do dia 60) + estoque
inicial de materiais + mobilização (EPI/uniformes/ferramentas) + garantia de 5% do valor anual
(caução imobiliza o valor; seguro-garantia custa prêmio de 0,5%-1,5% ao ano).

| Porte | Componentes (faixa) | Total estimado | Classe |
|---|---|---:|---|
| Pequeno (ex.: PMOC/continuado em 1 órgão pequeno, ~R$150-400 mil/ano — casos A/B) | Folha 2 meses R$20-35 mil; estoque R$5-10 mil; mobilização R$3-6 mil; garantia caução R$7,5-20 mil (ou seguro R$75-300/ano de prêmio) | **R$ 35.000 a R$ 70.000** | **Baixo** |
| Médio (ex.: contrato continuado ~R$300 mil a R$1,5 milhão/ano — caso C) | Folha 2 meses R$30-60 mil; estoque R$15-30 mil; mobilização R$6-12 mil; garantia caução R$15-75 mil (ou seguro R$150-1.125/ano) | **R$ 65.000 a R$ 130.000** | **Médio** |
| Grande (ex.: contrato estadual plurianual com chiller/VRF, ~R$1 milhão+/ano — casos D/E) | Folha 2 meses R$60-150 mil; estoque R$40-100 mil (peças de chiller sem referência própria — limitação); mobilização R$15-30 mil; garantia caução R$50-250 mil+ (ou seguro R$500-3.750+/ano) | **R$ 200.000 a R$ 400.000+** | **Alto** |

## 6. Regras práticas de lance

- **Desconto típico em GO** (casos incluídos, descontos não suspeitos, n=66): mediana **44,3%**,
  Q1 **24,7%**, Q3 **60,2%**.
- **Limite de risco (derivado do cálculo de lucro zero):** nos contratos com itens detalhados
  por aparelho/BTU (a maioria dos municipais pequenos/médios de GO — casos A e C), o desconto
  máximo sem entrar em prejuízo provável ficou entre **~46% e ~47%** sobre o valor estimado do
  PNCP. Como a mediana observada em GO (44,3%) já está perto desse limite e o 3º quartil
  (60,2%) está **acima** dele, boa parte dos lances vencedores em GO opera, pelo nosso modelo
  de custo, na faixa "apertado" ou pior — sinal de que concorrentes reais têm estrutura de custo
  mais enxuta (informalidade, menor encargo efetivo, escala) ou aceitam margem muito fina.
- Já em Registros de Preços "guarda-chuva" com item único e genérico (casos B, D, E, típicos de
  órgãos estaduais/federais ou municípios maiores), o valor estimado costuma ser muito mais
  folgado em relação ao custo real, permitindo descontos de até 80%-90% e ainda assim preço
  acima do lucro zero — mas a incerteza sobre o escopo real (quantidade de aparelhos,
  complexidade dos sistemas) é maior, exigindo visita técnica antes de definir o lance.
- **Ata de Registro de Preços não garante volume:** ~40-50% dos casos incluídos em GO são SRP
  ("futura e eventual"); o valor efetivamente executado pode ficar bem abaixo do valor
  estimado/homologado registrado.
- **Garantia contratual às vezes é dispensada:** em 2 dos 5 editais lidos integralmente
  (Anápolis e TRE-GO), a garantia contratual foi expressamente dispensada por o serviço não
  exigir dedicação exclusiva de mão de obra — confirme essa cláusula em cada edital antes de
  reservar caixa para garantia.
- **Munck raramente é exigido nesta área:** não encontramos exigência de caminhão
  munck/guindauto/cesto aéreo em nenhum dos 5 editais lidos — diferente de iluminação pública.
  Os 2 munck da empresa tendem a ficar ociosos nesta área específica, salvo contratos que
  envolvam remoção/instalação de condensadoras em telhados/fachadas de difícil acesso.

## 7. Exigências de habilitação recorrentes (amostra de 5 editais/TRs lidos)

| Exigência | Recorrência na amostra | Evidência (trecho) |
|---|---|---|
| Registro no CREA/CFT/CRT + indicação de Responsável Técnico com ART/TRT | 3 dos 3 editais de maior porte (Anápolis, TRE-GO, ALEGO) | ALEGO: *"Certidão de registro ou inscrição da empresa participante junto ao CREA (...) contendo a relação dos seus responsáveis técnicos (RT's)"* |
| PMOC elaborado por engenheiro mecânico/técnico mecânico (RT) com CAT | 3 dos 3 editais de maior porte; ausente nos 2 editais menores por-item | ALEGO: *"Declaração da empresa (...) indicando 01 engenheiro mecânico ou técnico mecânico para responder como responsável técnico (...) responsável pela elaboração do PMOC (...) através de atestados (...) acompanhados das (...) CAT emitidas pelo CREA/CONFEA"* |
| Atestado de capacidade técnica (qualitativo) | 5 de 5 editais lidos; **nenhum** trouxe percentual/quantidade mínima explícita do objeto no atestado | Bela Vista: *"Comprovação através de no mínimo de 01 (um) atestado técnico (...) comprovando que a licitante forneceu de maneira satisfatória (...) produtos semelhantes"* |
| Garantia contratual dispensada (serviço sem dedicação exclusiva) | 2 de 5 editais | Anápolis: *"Não haverá exigência de garantia contratual da execução."*; TRE-GO: *"(...) não requerem a disponibilização de mão-de-obra dedicada, não será exigida a prestação de garantia contratual."* |
| Frota mínima/veículo | Exigência leve (posse de veículo identificado, sem quantidade mínima) | Bela Vista: *"Para o transporte dos equipamentos a Contratada deverá possuir veículo devidamente identificado (...)"* |
| Munck/guindauto/cesto aéreo | **Não encontrado** em nenhum dos 5 editais | — |

*Amostra pequena (5 editais): a coleta automática de textos ainda não havia baixado nenhum
arquivo de climatização no momento desta análise; os PDFs acima foram baixados manualmente via
API de arquivos do PNCP (limite de 5, com 2s entre requisições).*

## 8. Recomendação

**Classe: seletivo.**

O volume de GO é real e recorrente (68 casos incluídos na amostra detalhada, ~R$ 69 milhões
estimados, a maioria contratos continuados de manutenção com mão de obra e peças por demanda —
perfil que casa com a estrutura da empresa), mas a mediana de desconto observada (44,3%) já se
aproxima do limite de lucro zero modelado (~46%-47%) nos contratos item-a-item mais comuns, e
quase metade das exclusões confirmadas é aquisição pura de equipamento — que a empresa deve
evitar. Recomenda-se mirar contratos continuados por aparelho/PMOC com itens detalhados (tipo
casos A/C), ser mais cauteloso (por causa da incerteza de escopo) em RPs "guarda-chuva" com
item único e genérico (tipo B/D), e reforçar a qualificação técnica (RT com CAT específico)
antes de disputar contratos de chiller/VRF de grande porte (tipo E), que exigem capacitação
acima do piso de refrigeração predial padrão.

## Limitações

- O PNCP não publica número de participantes/licitantes; o campo fica `null` salvo menção
  explícita no texto do edital/TR (não observada nos 5 textos lidos).
- Amostra de vizinhos é pequena: 26 casos detalhados contra ~450/2anos aceitos pelo índice de
  busca (~11,6% de cobertura) — números de vizinhos são direcionais.
- 24 casos foram reclassificados de excluído para incluído nesta revisão manual (ver seção 1 e
  campo `justificativa` de cada decisão em `climatizacao.json`).
- Peças sem preço de referência nas fontes coletadas (placa eletrônica, turbina/motoventilador,
  hélice, peças de chiller) fazem os cálculos de margem subestimarem o custo real nessas linhas
  específicas.
- Compressor de ar-condicionado usa proxy fraco (compressor doméstico de geladeira 1/4HP).
- Casos B, D, E têm item único e genérico no PNCP — o escopo (nº de aparelhos, complexidade)
  foi estimado por analogia/porte do órgão, com alta incerteza explícita.
- Só 5 editais/TRs foram lidos manualmente (limite do enunciado); achados da seção 7 valem para
  essa amostra pequena.
- Dois pares de casos (`02218683000183_2026_206`/`_263` e `02382836000123_2026_105`/`_106`)
  parecem ser republicações/correções do mesmo processo — mantidos como registros separados
  (números de controle PNCP distintos), o que pode inflar levemente a contagem de volume/ano
  para esses 2 órgãos.
- Simples Nacional (anexo III/IV) pode reduzir a carga tributária efetiva da empresa e melhorar
  a margem real acima do que este modelo (BDI padrão, regime presumido) calcula.
