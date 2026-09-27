# Estudo de mercado -- Refrigeracao (GO + vizinhos)

Manutencao de camaras frias, refrigeradores comerciais, freezers e bebedouros.
Dados do PNCP, periodo de coleta ~24 meses (2024-09-27 a 2026-09-27), coleta em
andamento no momento desta analise. Empresa de referencia: engenharia de GO
com engenheiro mecanico e eletricista, tecnicos/mecanicos de refrigeracao,
eletricistas, 2 caminhoes munck e veiculos leves -- foco em contratos de mao
de obra + deslocamento + materiais baratos, pagos por medicao mensal, com
baixo investimento inicial.

## 1. Revisao da classificacao

O pipeline automatico capturou **43 casos** que bateram na area "refrigeracao"
(por `area_principal` ou por constarem na lista `areas`): 19 em GO, 8 no DF, 8
no MT e 8 no MS.

**Achado central desta revisao:** a maior parte desses 43 casos **nao e
nucleo de refrigeracao comercial** -- e climatizacao predial (ar-condicionado
central, splits, PMOC), que usa a palavra "refrigeracao" apenas de passagem no
objeto ou no nome de um sistema (ex.: "sistema de refrigeracao e exaustao" de
um predio publico, que na leitura do edital se revelou um chiller central de
ar-condicionado). Foi necessario ir alem do heuristico automatico de 4
motivos e adicionar uma quinta categoria informal, **`fora_do_nucleo`**, para
os casos em que os ITENS do PNCP (nao so o titulo do objeto) mostram que o
valor e dominado por ar-condicionado/climatizacao, sem camara fria, freezer,
bebedouro ou balcao refrigerado como nucleo real.

Tambem foram corrigidas 4 exclusoes automaticas por leitura direta dos itens
brutos e/ou do edital:

- **3 reversoes de "equipamento_alto"/"fornecimento_puro" para incluido**:
  quando o item aparece cadastrado como "Material" no PNCP mas a descricao e
  claramente um servico (ex.: "SERVICO DE MANUTENCAO...", "Prestacao de
  servico de Limpeza, higienizacao..."), ou quando a peca e fornecida **por
  demanda** dentro de um servico de manutencao (bebedouro, geladeira,
  freezer) -- que a premissa do estudo classifica como SERVICO, nao compra de
  equipamento novo.
- **1 reversao de incluido para excluido**: o caso do TRT da 18a Regiao
  (00509968000148/2024/4438), que o pipeline automatico havia incluido como
  refrigeracao (objeto fala em "sistemas de refrigeracao"), foi excluido apos
  a leitura do edital completo (baixado via API do PNCP), que exige atestado
  de execucao em "sistema de ar-condicionado central de expansao indireta com
  condensacao a ar" -- ou seja, e climatizacao central de grande porte, nao
  refrigeracao comercial.

### Resultado final

| | GO | vizinhos (DF+MT+MS) |
|---|---|---|
| Casos capturados pelo indice | 19 | 24 |
| **Incluidos (nucleo confirmado)** | **5** | **7** |
| Excluidos | 14 | 17 |

**Exclusoes por motivo (todos os 43 casos):**

| motivo | GO | vizinhos |
|---|---|---|
| fora_do_nucleo (climatizacao predominante, informal) | 11 | 14 |
| fornecimento_puro | 2 | 3 |
| equipamento_alto | 1 | 0 |
| obra_grande | 0 | 0 |
| mencao_passagem | 0 | 0 |

A lista completa das 43 decisoes (id, incluido, motivo, justificativa de 1
linha) esta em `refrigeracao.json` -> `decisoes`.

## 2. Indicadores finais (so casos incluidos)

| metrica | GO (n=5) | vizinhos (n=7) |
|---|---|---|
| Volume/ano (indice bruto de selecao.jsonl, pre-revisao)* | 9,5 | 69,5 |
| Valor total estimado | R$ 3.318.061 | R$ 5.819.163 |
| Ticket mediano | R$ 561.035 | R$ 823.950 |
| Desconto mediana [Q1; Q3] (n valido) | 12,65% [7,33%; 23,47%] (n=4) | 30,52% [20,85%; 38,48%] (n=6) |
| % deserta/fracassada | 0,0% | 0,0% |
| % com beneficio ME/EPP | 0,0% | 14,3% |
| % continuado / pontual / indefinido | 0% / 80% / 20% | 14,3% / 42,9% / 42,9% |
| Numero de participantes | nao publicado pelo PNCP (campo sempre nulo) | idem |

*O indice "volume/ano" vem de `selecao.jsonl` (contagem automatica por regex,
antes da revisao manual de nucleo) e **superestima** o volume real de
refrigeracao comercial, pelo mesmo motivo do achado central acima: a maioria
do que a regex capturou e climatizacao. Trate esse numero como teto, nao como
volume real esperado.

Um desconto foi excluido do calculo por ser suspeito em cada grupo: GO
(01740463000152_2026_118, -0,36%, negativo) e vizinhos
(03560440000191_2026_25, o campo `valor_estimado_total` do PNCP veio quebrado
em R$0,02, gerando um "desconto" absurdo -- o caso continua incluido, mas so
o valor homologado deve ser usado como referencia).

**Leitura pratica**: a amostra e pequena (5 e 7 casos). O volume real de
refrigeracao comercial pura em GO parece bem menor do que o indice sugere --
a maior parte da demanda de "manutencao de ar-condicionado e refrigeracao"
publicada em editais de GO e, na pratica, climatizacao predial.

## 3. Casos exemplares de GO

| # | Orgao / objeto | Link PNCP | Valor est. | Homologado | Desconto |
|---|---|---|---|---|---|
| 1 | Camara Municipal de Goiania -- manutencao (mao de obra exclusiva) de ar-condicionado, bebedouros, refrigeradores e cortinas de ar | [00001727000193/2025/22](https://pncp.gov.br/app/editais/00001727000193/2025/22) | R$ 758.998 | R$ 685.000 | 9,75% |
| 2 | Municipio de Goiania -- SRP, ar-condicionado (~74%) e bebedouros (~26%) | [01740463000152/2026/118](https://pncp.gov.br/app/editais/01740463000152/2026/118) | R$ 329.769 | R$ 330.969 | -0,36% (suspeito) |
| 3 | Fundo Municipal de Saude de Catalao -- SRP, manutencao de refrigeracao + pecas por demanda (bebedouros, purificadores, maquinas de lavar) | [03532661000156/2025/13](https://pncp.gov.br/app/editais/03532661000156/2025/13) | R$ 1.512.774 (rec. R$929.313) | R$ 490.515 | 47,22% |
| 4 | Municipio de Senador Canedo -- SRP multi-lote (eletrodomesticos diversos; refrigeracao ~31% do valor) | [25107525000151/2024/237](https://pncp.gov.br/app/editais/25107525000151/2024/237) | R$ 561.035 | R$ 473.754 | 15,56% |
| 5 | Municipio de Senador Canedo -- SRP, lote unico com refrigerador/frigobar/freezer/bebedouro (~78% do lote) | [25107525000151/2025/369](https://pncp.gov.br/app/editais/25107525000151/2025/369) | R$ 155.486 | R$ 155.400 | 0,06% |

## 4. Margem em casos tipicos

Premissas comuns (fonte: `PREMISSAS_COMUNS.md` e `referencias.json`, acesso
2026-09-27): tecnico de refrigeracao R$3.450,55/mes; ajudante R$1.711,00/mes;
encargos mensalista sem desoneracao 69,28%; vale-alimentacao R$495,88/mes;
EPI/uniforme/ferramentas R$150/mes por empregado; 220h/mes. Isso da um custo
de equipe (1 tecnico + 1 ajudante) de **R$45,59/hora**. Veiculo leve
R$1,20/km. Engenheiro RT (8h) R$13.778,50/mes, rateado por fracao de tempo.

**BDI** (Acordao TCU 2622/2013, composicao "Construcao de Edificios", usada
para climatizacao/refrigeracao): AC 4,00%; S+G 0,80%; R 1,27%; DF 1,23%; L
7,40%; Tributos 8,65%. Preco de lucro zero = custo direto x **1,17542**;
preco com BDI = custo direto x **1,26240** (BDI de 17,54% e 26,24%,
respectivamente).

| Caso | Escopo modelado | Custo direto/ano | Preco lucro zero | Preco c/ BDI | Homologado | Desconto praticado | Classificacao |
|---|---|---:|---:|---:|---:|---:|---|
| Camara Municipal de Goiania | Posto fixo, 2 tecnicos + 1 ajudante + 10% eng. RT | R$ 244.816 | R$ 287.762 | R$ 309.056 | R$ 685.000 | 9,75% | **Folgado** |
| Senador Canedo (lotes refrigeracao, 2024_237) | 350 atendimentos/ano, 1h equipe cada | R$ 53.623 | R$ 63.029 | R$ 67.693 | R$ 148.185* | 15,56% | **Folgado** |
| Senador Canedo (lote unico, 2025_369) | 259 atendimentos/ano, 1h equipe cada | R$ 41.830 | R$ 49.168 | R$ 52.807 | R$ 155.400 | 0,06% | **Folgado** |
| Catalao (itens de servico, 2025_13) | 1.095 atendimentos/ano, 1,5h equipe cada | R$ 212.354 | R$ 249.606 | R$ 268.077 | R$ 195.773* | 47,22% | **Prejuizo provavel** |

*Valores homologados marcados com `*` sao aproximacoes proporcionais (ver
premissas de cada caso e limitacoes).

**Notas por caso:**

1. **Camara Municipal de Goiania**: contrato pontual de 12 meses com "mao de
   obra exclusiva" (equipe dedicada). Premissa conservadora de 2
   tecnicos+1 ajudante (nao foi possivel ler o edital completo -- veio em
   `.rar` que nao pode ser extraido nesta sessao). Mesmo dobrando a equipe
   (sensibilidade), o preco com BDI (~R$618 mil) fica abaixo do homologado
   (R$685 mil) -- margem robusta.
2. **Senador Canedo (multi-lote)**: recorte de 3 lotes (geladeira, purificador,
   bebedouro industrial), 350 atendimentos/ano. Homologado proporcional
   estimado aplicando o desconto do processo (15,56%) so a esse subconjunto
   -- aproximacao, pois o desconto pode nao ser uniforme entre os 15 lotes.
3. **Senador Canedo (lote unico)**: desconto quase nulo (0,06%) mas margem
   calculada e folgada -- sugere baixa concorrencia (unica vencedora ME), nao
   preco apertado. Lote pequeno tende a atrair pouca disputa.
4. **Catalao**: unico caso com classificacao de risco. E um SRP por ordem de
   servico com pecas e mao de obra misturadas; o desconto do processo
   (47,22%, medido no recorte com resultado) supera o limite de risco
   calculado para esse modelo de contrato (~32,7% -- ver secao 6). Se o
   desconto incidiu igualmente sobre servico e peca (nao sabemos a
   composicao exata por item, dado truncado no PNCP), o preco de mao de obra
   fica abaixo do custo direto modelado.

## 5. Investimento inicial (conforme PREMISSAS_COMUNS)

Componentes: (1) folha de 2 meses (pagamento por medicao com liquidacao em
ate 30 dias -- 1o recebimento perto do dia 60); (2) estoque inicial de
materiais de reposicao; (3) mobilizacao (uniformes, EPI, ferramentas
faltantes); (4) garantia de 5% do valor anual, em duas formas -- caucao
(valor imobilizado) ou seguro-garantia (premio anual de 0,5% a 1,5% do
valor garantido).

| Porte | Equipe | Folha 2 meses | Estoque | Mobilizacao | Garantia (caucao 5%) | Garantia (seguro, 0,5-1,5%/ano) | Total via caucao | Total via seguro | Classe |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Pequeno (~R$155 mil/ano) | 1 tecnico + 1 ajudante | R$ 20.058 | R$ 4.000 | R$ 3.300 | R$ 7.774 | R$ 777 a R$ 2.332 | **R$ 35.133** | **R$ 28.913** | Baixo |
| Medio (~R$700 mil/ano) | 2 tecnicos + 1 ajudante | R$ 33.032 | R$ 8.000 | R$ 6.450 | R$ 35.000 | R$ 3.500 a R$ 10.500 | **R$ 82.482** | **R$ 54.482** | Medio |
| Grande (~R$1,8 milhao/ano) | 4 tecnicos + 2 ajudantes + 15% eng. RT | R$ 70.198 | R$ 20.000 | R$ 15.900 | R$ 90.000 | R$ 9.000 a R$ 27.000 | **R$ 196.098** | **R$ 124.098** | Medio (via caucao, no limite de R$200 mil) / Medio (via seguro) |

**Observacao**: mesmo no porte grande, usar seguro-garantia em vez de caucao
mantem o investimento na classe "medio" com folga (R$124 mil vs. R$196 mil
via caucao, que fica no limite do teto de "medio"). Para uma empresa que
quer baixo investimento, seguro-garantia e a opcao mais compativel.

## 6. Regras praticas de lance

- **Desconto tipico em GO** (casos incluidos, n=4 validos): mediana **12,65%**,
  quartis **[7,33%; 23,47%]**. Em vizinhos (n=6 validos): mediana 30,52%,
  quartis [20,85%; 38,48%] -- mais agressivo, mas amostra pequena e
  heterogenea entre UFs.
- **Risco depende do modelo de contrato**:
  - Posto fixo / mao de obra dedicada (ex.: Camara Municipal): o preco de
    lucro zero so e alcancado com desconto acima de **~62%** -- ha bastante
    folga tipica nesse formato de orcamento publico.
  - SRP por ordem de servico com peca+mao de obra e atendimentos de baixo
    valor unitario (ex.: Catalao): o limite de risco cai para **~33%** --
    acima disso, ha risco real de prejuizo.
- **Regra pratica conservadora**: nao dar mais de 25-30% de desconto em SRPs
  por OS com peso relevante de peca e deslocamento por atendimento pequeno (o
  Q3 de GO, 23,47%, e um teto razoavel de referencia). Em contratos de posto
  fixo/equipe dedicada, ha espaco para descontos maiores (ate a faixa de
  40-50%) sem entrar em prejuizo, segundo os casos calculados.
- **Ata de Registro de Precos nao garante volume**: 4 dos 5 casos de GO e 4
  dos 7 de vizinhos incluidos sao SRP -- o orgao pode nao chamar a
  quantidade total registrada; nao precificar como se o volume do edital
  fosse garantido.
- **Fluxo de caixa em postos fixos**: a folha da equipe dedicada e um custo
  fixo mensal, independente do volume de atendimentos naquele mes.

## 7. Exigencias de habilitacao recorrentes

Como o coletor automatico nao baixa texto de edital para a area
"refrigeracao" (so para climatizacao/eletrica predial/manutencao
predial/iluminacao publica/munck), as exigencias abaixo vem da leitura manual
de 2 PDFs baixados via API de arquivos do PNCP (dentro do limite de 5
autorizados): o edital de Catalao (caso efetivamente incluido na area) e o
do TRT da 18a Regiao (caso excluido apos a leitura, mas usado aqui como
indicio complementar do padrao regional de engenharia predial em GO).

| Exigencia | Evidencia |
|---|---|
| Atestado de capacidade tecnica (execucao anterior semelhante) | Presente nos dois editais lidos |
| Registro/CAT no CREA + responsavel tecnico | Edital TRT-18: exige Certidao de Registro no CREA + Certidao de Acervo Tecnico |
| Vistoria tecnica previa obrigatoria | Edital TRT-18: "a licitante devera vistoriar os locais... mediante previo agendamento" |
| Qualificacao economico-financeira (indices LG/SG/LC >= 1 ou patrimonio liquido minimo) | Edital TRT-18: indices contabeis ou ate 10% do valor estimado em patrimonio liquido |
| Garantia contratual -- varia conforme o orgao | TRT-18 exige garantia verificada no 1o pagamento; Catalao DISPENSA expressamente ("carater de pronta entrega") |
| Certidoes negativas padrao (falencia, tributaria, trabalhista, FGTS) | Presentes em ambos os editais, padrao de pregao eletronico |

Como a empresa ja tem engenheiro mecanico e eletricista no quadro, os
requisitos de CREA/atestado tecnico tendem a ser cumpriveis sem custo
adicional relevante.

## 8. Recomendacao

**Classe: SELETIVO.**

O volume real de refrigeracao comercial pura (camara fria, refrigeradores,
freezers, bebedouros, balcoes) em GO e pequeno (5 casos incluidos em ~2 anos,
~R$3,3 milhoes/ano em valor estimado) -- a maior parte do que aparece como
"refrigeracao" nos editais e, na pratica, climatizacao predial (fora do
nucleo definido para este estudo). Os casos genuinos mostram margem
majoritariamente folgada (3 de 4 casos calculados) e investimento inicial
baixo/medio, compativel com o perfil da empresa. Recomenda-se atacar
seletivamente contratos cujo OBJETO E ITENS (nao so o titulo) confirmem
nucleo de refrigeracao comercial, e evitar SRPs por ordem de servico com
desconto agressivo (acima de 30-35%) que misturem peca e mao de obra, onde o
caso de Catalao mostrou risco real de prejuizo.

## Limitacoes

- Amostra pequena: 5 casos em GO e 7 em vizinhos apos a revisao de nucleo (de
  43 capturados pelo indice de area).
- A maioria dos 43 casos capturados e climatizacao (ar-condicionado predial),
  nao refrigeracao comercial -- corrigido com a categoria informal
  `fora_do_nucleo` (25 dos 31 excluidos).
- 3 exclusoes automaticas (equipamento_alto/fornecimento_puro) revertidas
  apos leitura de itens brutos: peca por demanda dentro de servico de
  manutencao e SERVICO, nao compra de equipamento.
- 1 caso (TRT-18) que o automatico incluia foi excluido apos leitura do
  edital completo -- e climatizacao central, nao refrigeracao comercial.
- `n_participantes`: o PNCP nao publica esse dado; sempre nulo nos 12 casos
  incluidos.
- O coletor nao baixa texto de edital para "refrigeracao"; as exigencias de
  habilitacao vieram de 2 PDFs lidos manualmente (limite de 5 autorizado).
- 1 dos 3 PDFs baixados veio em `.rar` e nao pode ser extraido nesta sessao
  (ferramenta disponivel nao suporta o formato) -- o caso da Camara Municipal
  de Goiania foi modelado com premissa de equipe sem confirmacao textual.
- Casos com `itens_truncados=true` (ex.: Catalao) tem cobertura parcial dos
  itens no PNCP -- o calculo de margem usa aproximacao proporcional de
  desconto, sinalizada explicitamente.
- Um caso incluido (03560440000191_2026_25, MS) tem valor estimado quebrado
  no PNCP (R$0,02) -- usado so o valor homologado como referencia.
- Todos os custos vem de `referencias.json`/`PREMISSAS_COMUNS.md`, com fonte
  e data de acesso citadas (2026-09-27); nenhuma planilha de custos do
  proprio edital foi usada como referencia de custo.
- A coleta (`coletor.py`) ainda estava em andamento durante esta analise.
