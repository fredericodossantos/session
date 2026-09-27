# Eletrica predial -- estudo de mercado (GO + vizinhos)
*Gerado em 2026-09-27. Periodo de coleta: 2024-09-27 a 2026-09-27 (~24 meses). coletor.py ainda em execucao no momento desta analise; W/textos estava vazio para eletrica_predial (8 arquivos baixados manualmente via API de arquivos do PNCP, com 2s entre requisicoes, para checar exigencias de habilitacao e detalhar 4 dos casos de margem).*
## Resumo executivo
Dos **115 casos** que bateram na area eletrica_predial nos dados ja coletados (91 em GO, 24 em UFs vizinhas -- DF/MT/MS), so **11 foram confirmados como servico real de eletrica predial** apos revisao manual (4 em GO, 7 em vizinhos). A esmagadora maioria (**83 casos, 72%**) e `fornecimento_puro`: registros de precos para AQUISICAO de material eletrico (cabo, disjuntor, lampada etc.), sem contratacao de mao de obra -- fora do escopo de uma empresa que presta servico. Os indicadores abaixo, portanto, valem como **sinal direcional**, nao como estatistica robusta (amostra muito pequena).
## 1. Revisao da classificacao
Cada um dos 115 casos foi conferido individualmente (objeto + itens do compra bruto, e em alguns casos os proprios PDFs do edital). Principais achados da revisao:

- **12 casos** que a heuristica automatica havia marcado como incluidos foram **reclassificados para excluidos** -- a maioria porque o objeto mencionava 'manutencao/eletrica' mas o contrato real era outra coisa (evento, decoracao natalina, elevadores, equipamento medico-hospitalar, motoniveladora, pocos artesianos, obra civil geral com eletrica so incidental, ou usina solar nova).
- **2 casos** que a heuristica havia marcado como `equipamento_alto` (por citar 'gerador'/'subestacao' no objeto) foram **reclassificados para incluidos** -- porque o contrato e de **manutencao** de subestacao/gerador/nobreak **ja existente** (dentro do escopo explicito do estudo), nao implantacao nova. A regra automatica nao distingue manutencao de implantacao so pela palavra-chave.
- Um caso emblematico do erro do tipo 'objeto engana': **01065846000172_2026_72** (adesao a ata do IFSP) tinha objeto que falava em 'manutencao predial ... sistemas eletricos ... fornecimento de materiais e mao de obra', mas ao abrir os 57 itens reais do compra bruto, quase tudo era filmagem, hospedagem, cracha, coffee break, seguranca e tendas de evento -- so 1 item de R$10 mil (de R$2,71 milhoes) tocava eletrica ('ponto eletrico para tomada e extensao'). Excluido por `mencao_passagem`.

A tabela completa de decisoes (115 linhas: id, incluido, motivo, subarea, justificativa) esta no arquivo `eletrica_predial.json`, campo `decisoes`.
### Subareas dos casos incluidos
| Subarea | GO | Vizinhos | Total |
|---|---|---|---|
| Manutencao eletrica predial continua | 1 | 4 | 5 |
| Subestacao existente (manutencao) | 1 | 3 | 4 |
| Adequacoes pontuais | 2 | 0 | 2 |
| SPDA/aterramento | 0 | 0 | 0 |
| Laudos/termografia | 0 | 0 | 0 |

*SPDA/aterramento e laudos/termografia nao tiveram nenhum caso incluido isoladamente na amostra atual (aparecem apenas como item dentro de reformas maiores que foram excluidas por `obra_grande`).*
### Motivos de exclusao (todos os 115 casos)
| Motivo | GO | Vizinhos |
|---|---|---|
| Equipamento de alto valor (gerador/usina nova/subestacao nova/>40% material) | 9 | 1 |
| Fora de escopo (nicho tecnico distinto) | 3 | 2 |
| Fornecimento puro (aquisicao de material) | 69 | 14 |
| Mencao de passagem (fora de escopo real) | 3 | 0 |
| Obra grande (>R$1,5 mi, civil geral) | 3 | 0 |

## 2. Indicadores finais (casos incluidos apos revisao)
| Indicador | GO | Vizinhos (MT+DF+MS) |
|---|---|---|
| N casos incluidos | 4 | 7 |
| Valor total estimado (amostra) | R$ 3.093.768,55 | R$ 18.301.554,41 |
| Ticket mediano | R$ 650.790,09 | R$ 1.100.097,63 |
| Desconto mediana | 7.3% | 6.9% |
| Desconto 1o quartil | 6.7% | 5.7% |
| Desconto 3o quartil | 9.7% | 17.7% |
| N amostra desconto (validos) | 4 | 7 |
| % deserta/fracassada | 0.0% | 0.0% |
| % com beneficio ME/EPP | 0.0% | 28.6% |
| % continuado | 0.0% | 28.6% |
| % pontual | 25.0% | 57.1% |
| % indefinido (sem sinal textual) | 75.0% | 14.3% |

**Nenhum desconto suspeito** (< 0% ou > 90%) apareceu nos 11 casos incluidos -- nada foi descartado por esse criterio.

*Contexto de volume (nao reclassificado, so indice de busca bruto): 108 casos/ano aceitos pelo indice em GO e 406 nos vizinhos -- a maioria e fornecimento_puro, ver secao 1.*

### Subareas (amostra combinada GO+vizinhos, n>=5 apenas para manutencao continua)
| Subarea | N | Valor total estimado | Ticket mediano | Desconto mediana | % continuado |
|---|---|---|---|---|---|
| Manutencao eletrica predial continua | 5 | R$ 15.360.602,35 | R$ 205.402,61 | 7.0% | 20.0% |
| Subestacao existente (manutencao) | 4 | R$ 4.733.140,43 | R$ 1.212.996,19 | 6.6% | 25.0% |
| Adequacoes pontuais | 2 | R$ 1.301.580,18 | R$ 650.790,09 | 11.0% | 0.0% |

*Apenas `manutencao_continua` atinge o piso de 5 casos pedido no enunciado (exatamente n=5, combinando GO e vizinhos); as outras duas subareas com casos incluidos (subestacao_existente n=4, adequacoes_pontuais n=2) ficam abaixo do piso e sao mostradas so para referencia qualitativa.*

**Numero de participantes:** O PNCP nao publica numero de participantes/licitantes por processo. Nos 8 PDFs de edital lidos integralmente nesta analise (2s entre requisicoes, API de arquivos do PNCP), nenhum trazia contagem explicita de participantes no corpo do texto -- o campo fica null em todos os 11 casos incluidos.

## 3. Casos exemplares (GO)
### [COMANDO DO EXERCITO -- Jataí/GO](https://pncp.gov.br/app/editais/00394452000103/2025/16511)
*Subarea: Manutencao eletrica predial continua*

> Registro de Preços pelo prazo de 12 (doze) meses, para eventual contratação de serviços de manutenção de rede elétrica, para atender as necessidades do 41º Batalhão de Infantaria Mecanizado.

- Valor estimado: R$ 34.606,85 | Homologado: R$ 32.186,00 | Desconto: 7.0%
- Registro de precos de 12 meses do 41o Batalhao de Infantaria Mecanizado (Jatai/GO) para manutencao de rede eletrica ate 69kV -- reparo com abertura/fechamento de rede e troca de elo fusivel, pago por evento (36 "unidades"/ano), com SLA de 2h para chegada e 12h para restabelecimento. Contrato pequeno (R$34,6 mil estimado), exige ART por servico prestado.

### [UNIVERSIDADE FEDERAL DE JATAI -- Jataí/GO](https://pncp.gov.br/app/editais/35840659000130/2025/13)
*Subarea: Subestacao existente (manutencao)*

> Contratação de serviços contínuos de MANUTENÇÃO PREVENTIVA E CORRETIVA DE REDE ELÉTRICA DE MÉDIA TENSÃO E ILUMINAÇÃO PÚBLICA

- Valor estimado: R$ 1.757.581,52 | Homologado: R$ 1.625.205,66 | Desconto: 7.5%
- Servico continuo da Universidade Federal de Jatai (GO) para manutencao preventiva (posto mensal, 12 parcelas) e corretiva por catalogo de pecas/servicos unitarios (15.992 "unidades" possiveis, pagas so quando usadas) de rede eletrica de media tensao e iluminacao publica do campus. Vencedora: empresa de eletrica/engenharia. Bom exemplo de contrato "guarda-chuva" com catalogo de precos unitarios.

### [ESTADO DE GOIAS -- Goiânia/GO](https://pncp.gov.br/app/editais/01409580000138/2025/1971)
*Subarea: Adequacoes pontuais*

> Contratação de empresa especializada em engenharia civil para execução de serviços de reparação e manutenção da Delegacia Regional de Fiscalização, na Cidade de Goiás, compreendendo serviços compostos por reparo e manutenção na cobertura, estacionamento, pinturas externas e internas, sistemas elétricos e de ares-condicionados, revitalização de piso interno e paisagismo.

- Valor estimado: R$ 504.910,59 | Homologado: R$ 424.000,00 | Desconto: 16.0%
- Contratacao pontual do Estado de Goias para reparo/manutencao de delegacia regional em Cidade de Goias: cobertura, estacionamento, pinturas, sistemas eletricos e de ar-condicionado, piso e paisagismo, como item unico de "Manutencoes de Engenharia, manutencao predial". Vencedora: empresa de engenharia (M2 Engenharia). Exemplo de adequacao pontual multi-disciplinar com eletrica como um dos componentes.

### [MUNICIPIO DE ITABERAI -- Itaberaí/GO](https://pncp.gov.br/app/editais/02451938000153/2025/346)
*Subarea: Adequacoes pontuais*

> Construção de cobertura para espaço de vivência e reforma de instalaçõees elétricas na Escola Padre Elígio

- Valor estimado: R$ 796.669,59 | Homologado: R$ 749.000,00 | Desconto: 6.0%
- Contratacao pontual do Municipio de Itaberai (GO) para construcao de cobertura de espaco de vivencia e reforma de instalacoes eletricas na Escola Padre Eligio, item unico de servico. Vencedora: empresa de engenharia (SWS Engenharia). Adequacao pontual de menor porte (R$796,7 mil estimado, R$749 mil homologado).

## 4. Margem em casos tipicos
Custo direto calculado com as premissas de `PREMISSAS_COMUNS.md` (nunca com a planilha de custos do proprio edital). (BDI lucro zero 17,54%; BDI com lucro 26,24% -- formula do Acordao TCU 2622/2013, AC 4,00% + S/G 0,80% + R 1,27%, DF 1,23%, L 7,40%, T 8,65%).

### [33683822000173_2026_45](https://pncp.gov.br/app/editais/33683822000173/2026/45) -- PREJUIZO PROVAVEL
**Escopo interpretado:** 1 eletricista em dedicacao exclusiva, 44h/semana, para manutencao preventiva/corretiva/preditiva eletrica e hidraulica continua (item unico, R$6.900,00/mes estimado).

**Premissas de custo:** Eletricista SEAC-GO/SEACONS R$3.450,55/mes + periculosidade NR-10 30% + encargos mensalista sem desoneracao 69,28% (SINAPI-GO 01/2026) + vale-alimentacao R$495,88/mes + EPI/ferramentas R$150/mes. BDI 'Construcao de Edificios' (lucro zero 17,54%; com lucro 26,24%).

| | Mensal |
|---|---|
| Custo direto | R$ 8.239,30 |
| Preco de lucro zero | R$ 9.684,64 |
| Preco com BDI | R$ 10.401,30 |
| Valor estimado PNCP | R$ 6.900,00 |
| Valor homologado | R$ 6.500,00 |
| Desconto do vencedor sobre estimado (PNCP) | 5.8% |
| Desconto maximo sem prejuizo (sobre estimado) | -40.4% |

**Observacoes:** O valor de referencia do PNCP (R$6.900/mes) e o homologado (R$6.500/mes, vencedor pessoa fisica/ME individual) ficam ABAIXO do preco de custo direto (R$8.239/mes) so da folha do eletricista, antes de qualquer BDI. Ou seja: para uma empresa que contrata eletricista via CLT com todos os encargos das premissas, este tipo de posto unico e estruturalmente deficitario mesmo sem desconto algum (desconto de risco negativo, -40%). O contrato so fecha a conta para um MEI/autonomo que e o proprio prestador (sem encargos patronais completos sobre si mesmo) -- e de fato o vencedor real e uma pessoa fisica (ME). Empresas maiores devem EVITAR postos unicos de baixo valor mensal como este, a menos que consigam diluir o eletricista em varios contratos simultaneos na mesma regiao.

### [00394452000103_2025_16511](https://pncp.gov.br/app/editais/00394452000103/2025/16511) -- FOLGADO
**Escopo interpretado:** Manutencao de rede eletrica ate 69kV do 41o BIM (Jatai/GO): reparo com abertura/fechamento de rede e troca de elo fusivel, por evento, com SLA (2h para chegar, 12h para restabelecer). Modelado como ~3 eventos/mes (36 unidades/12 meses), cada evento com eletricista+ajudante por 4h (deslocamento+execucao) + 40km de veiculo leve.

**Premissas de custo:** Eletricista e ajudante nas premissas comuns (custo/hora = custo mensal carregado / 220h). Veiculo leve R$1,20/km (ANP-GO fev/2026 + manutencao). Nao ha detalhamento de material no item do PNCP; assumimos que o elo fusivel e pecas menores estao diluidos no valor unitario (nao modelamos material a parte -- ver limitacoes).

| | Mensal |
|---|---|
| Custo direto | R$ 786,63 |
| Preco de lucro zero | R$ 924,62 |
| Preco com BDI | R$ 993,04 |
| Valor estimado PNCP | R$ 2.883,90 |
| Valor homologado | R$ 2.682,17 |
| Desconto do vencedor sobre estimado (PNCP) | 7.0% |
| Desconto maximo sem prejuizo (sobre estimado) | 67.9% |

**Observacoes:** Contrato pequeno mas com boa folga: mesmo com o SLA de resposta rapida (2h), o custo direto por evento (R$262) fica bem abaixo do valor unitario medio do PNCP (~R$961 estimado / ~R$894 homologado). Classificado 'folgado'. Risco principal nao e de preco, e sim de escala minima (contrato de R$34,6 mil/ano cobre custo fixo de deslocamento e prontidao apenas se a empresa ja atender outros contratos na mesma regiao de Jatai).

### [35840659000130_2025_13](https://pncp.gov.br/app/editais/35840659000130/2025/13) -- FOLGADO
**Escopo interpretado:** Item 1 do contrato continuado da UFJ (Jatai/GO): 'Manutencao Preventiva' de rede eletrica de media tensao e iluminacao publica do campus, pago como posto mensal fixo (12 parcelas de R$18.601,45). Modelado como equipe dedicada em tempo integral: 1 eletricista + 1 ajudante + veiculo leve (rondas no campus, ~300km/mes).

**Premissas de custo:** Mesmas premissas de mao de obra do caso anterior, equipe em tempo integral (nao fracionada). Nao inclui o item 2 do mesmo contrato (catalogo de manutencao corretiva por pecas/servicos unitarios, pago so sob demanda -- nao modelado por falta de detalhamento de quantidades reais consumidas).

| | Mensal |
|---|---|
| Custo direto | R$ 12.141,56 |
| Preco de lucro zero | R$ 14.271,44 |
| Preco com BDI | R$ 15.327,52 |
| Valor estimado PNCP | R$ 18.601,45 |
| Valor homologado | R$ 18.601,45 |
| Desconto do vencedor sobre estimado (PNCP) | 7.5% |
| Desconto maximo sem prejuizo (sobre estimado) | 23.3% |

**Observacoes:** Contrato 'folgado': mesmo com equipe completa em tempo integral, o custo direto (R$12.142/mes) fica bem abaixo do preco com BDI (R$15.328/mes) e da receita do item (R$18.601/mes, desconto 0% -- venceu pelo valor estimado). Margem confortavel neste item; o item 2 (catalogo por demanda) e onde o risco de execucao mora, pois paga apenas o que for efetivamente usado.

### [15457856000168_2026_85](https://pncp.gov.br/app/editais/15457856000168/2026/85) -- FOLGADO
**Escopo interpretado:** Manutencao preventiva/preditiva/corretiva com fornecimento de pecas/insumos por demanda de subestacao de energia, grupo gerador, banco de capacitores, reservatorio de diesel e equipamentos de protecao do Bioparque do Pantanal (Campo Grande/MS) -- item unico, R$1.100.097,63/ano (R$91.675/mes). Modelado como equipe reforcada: 2 eletricistas + 1 ajudante + engenheiro eletricista em 20% de dedicacao (para laudos/ART/inspecoes de subestacao) + veiculo leve + 15% da receita reservado para pecas/insumos (premissa, dado que o objeto explicita fornecimento por demanda).

**Premissas de custo:** Engenheiro fracionado (Lei 4.950-A/66, R$13.778,50/mes para 8h, aqui 20% de dedicacao) + encargos mensalista 69,28%. Reserva de material de 15% da receita mensal e premissa nossa (nao ha detalhamento de pecas no PNCP); trata-se de uma estimativa conservadora para um ativo critico (subestacao + gerador de emergencia de um parque com animais vivos).

| | Mensal |
|---|---|
| Custo direto | R$ 39.036,93 |
| Preco de lucro zero | R$ 45.884,80 |
| Preco com BDI | R$ 49.280,28 |
| Valor estimado PNCP | R$ 91.674,80 |
| Valor homologado | R$ 91.674,80 |
| Desconto do vencedor sobre estimado (PNCP) | 0.0% |
| Desconto maximo sem prejuizo (sobre estimado) | 49.9% |

**Observacoes:** Classificado 'folgado' com boa margem mesmo com equipe reforcada e reserva de material -- mas o objeto sugere um ativo critico (energia de emergencia para bioparque com animais vivos), que tipicamente exige plantao/sobreaviso 24x7 e engenheiro com registro de responsavel tecnico permanente para subestacao, que NAO modelamos aqui (ver limitacoes). Trate esta margem como um LIMITE SUPERIOR: uma proposta real deveria orcar cobertura de emergencia fora do horario comercial antes de tratar este contrato como 'folgado' com confianca.

## 5. Investimento inicial
Nao ha referencia de preco de camera termografica em custos/custos/referencias.json nem em nenhuma fonte coletada nesta sessao para este estudo -- por isso NAO incluimos um numero de camera termografica no investimento acima (nao vamos inventar um preco sem fonte). A subarea de laudos/termografia nao teve nenhum caso incluido na amostra coletada ate agora (0 casos), entao tambem nao ha um contrato real para calibrar esse investimento. Recomendacao pratica: antes de decidir investir em camera termografica, cotar em pelo menos 2 fornecedores (ex.: linhas FLIR E4/E6 ou equivalentes nacionais) e tratar esse valor como investimento a parte, especifico do contrato de laudos/termografia visado.

| Porte | Folha 2 meses | Estoque materiais | Mobilizacao | Garantia (caucao 5%) | Total (caucao) | Classe | Garantia (seguro-garantia, uso 1%) | Total (seguro) | Classe |
|---|---|---|---|---|---|---|---|---|---|
| pequeno (ex.: 1 eletricista dedicado, contrato ~R$82,8 mil/ano, tipo Caso 1) | R$ 16.478,60 | R$ 1.802,38 | R$ 300,00 | R$ 4.140,00 | R$ 22.720,98 | baixo | R$ 828,00 (faixa R$ 414,00 a R$ 1.242,00) | R$ 19.408,98 | baixo |
| medio (eletricista+ajudante+fracao de engenheiro, contrato ~R$500 mil/ano) | R$ 30.560,39 | R$ 15.363,90 | R$ 1.500,00 | R$ 25.000,00 | R$ 72.424,29 | medio | R$ 5.000,00 (faixa R$ 2.500,00 a R$ 7.500,00) | R$ 52.424,29 | medio |
| grande (2 eletricistas+ajudante+fracao de engenheiro, contrato ~R$1,3 milhao/ano, tipo subestacao existente) | R$ 49.371,41 | R$ 48.415,70 | R$ 3.000,00 | R$ 65.000,00 | R$ 165.787,11 | medio | R$ 13.000,00 (faixa R$ 6.500,00 a R$ 19.500,00) | R$ 113.787,11 | medio |

*Classes: baixo < R$50 mil; medio R$50-200 mil; alto > R$200 mil. Usar seguro-garantia em vez de caucao mantem o investimento inicial mais baixo (o premio de 0,5-1,5% ao ano custa muito menos que imobilizar 5% do valor anual em caucao), especialmente em contratos grandes.*

## 6. Regras praticas de lance
- Desconto tipico observado em GO (casos incluidos apos revisao manual, descontos validos): mediana 7.3%; 1o quartil 6.7%; 3o quartil 9.7% (n=4 -- AMOSTRA MUITO PEQUENA, tratar como indicativo, nao como estatistica robusta).
- Nos vizinhos (MT+DF+MS, casos incluidos): mediana 6.9%; 1o quartil 5.7%; 3o quartil 17.7% (n=7).
- Nenhum desconto suspeito (< 0% ou > 90%) apareceu nos 11 casos incluidos -- todos os descontos calculados sao plausiveis.
- Risco de preco NAO e uniforme por tipo de contrato: em postos unicos de mao de obra dedicada de baixo valor mensal (ex.: 1 eletricista por ~R$6-7 mil/mes), o preco de referencia do PNCP ja fica ABAIXO do nosso custo direto modelado (CLT completo) mesmo com desconto zero -- ou seja, esses contratos so sao viaveis para quem opera como autonomo/MEI (menor carga de encargos sobre si mesmo) ou para quem dilui esse posto entre varios contratos.
- Ja em contratos com item mais robusto (posto mensal de equipe completa, pacotes de subestacao/gerador, ou catalogos por evento), o desconto maximo sem prejuizo (segundo o preco de lucro zero modelado) variou de ~23% (posto mensal de equipe, Caso 3) a ~50-68% (pacotes maiores e intervencoes unitarias, Casos 2 e 4) sobre o valor estimado do PNCP -- ha bastante folga para lances agressivos nesses formatos, DESDE que a equipe minima realmente caiba no valor do item.
- Regra pratica: antes de dar lance, calcular primeiro o custo direto mensal da equipe minima exigida pelo objeto (nao pelo item do PNCP) usando as premissas comuns; se o VALOR ESTIMADO do PNCP para o item de mao de obra dedicada already for menor que esse custo direto, e sinal de que o edital foi orcado com premissas mais baratas que as SEAC-GO/SEACONS (ex.: orgao usou piso salarial antigo, ou nao incluiu periculosidade) -- nesse caso avaliar se vale disputar, pois a margem so aparece se a empresa tiver estrutura de custo mais enxuta que a modelada.

## 7. Exigencias de habilitacao recorrentes
*Baseado em 8 PDFs de edital/termo de referencia baixados manualmente via API de arquivos do PNCP (2s entre requisicoes), ja que `W/textos` ainda estava vazio para esta area no momento da analise.*

**CREA + Anotacao de Responsabilidade Tecnica (ART)**
- Recorrencia: presente em 3 dos 6 editais lidos integralmente (UFJ/Jatai-GO, AGESUL/MS, Comando do Exercito/GO) e nas exigencias de habilitacao tecnica de forma geral
- Evidencia: UFJ (GO): 'profissional engenheiro eletricista, devidamente registrado no CREA-GO'; AGESUL (MS): 'Aos licitantes vinculados ao CREA recai a obrigacao de apresentar a Certidao de Acervo Operacional -- CAO' e exigencia de ART/documento equivalente do responsavel tecnico; Comando do Exercito (GO): 'o contratado deve ser capaz de apresentar uma ART (...) apos a prestacao do servico'.

**Atestado(s) de capacidade tecnica compativel (execucao anterior de servico semelhante)**
- Recorrencia: presente em 4 dos 6 editais lidos integralmente
- Evidencia: Nova Bandeirantes/MT: 'apresentacao de, no minimo, 01 (um) atestado de capacidade tecnica (...) que comprove a execucao de servicos de natureza compativel'; AGESUL/MS: 'atestados que comprovassem execucao de servico com caracteristicas semelhantes'; UFJ/GO e Comando do Exercito/GO: atestados podem ser apresentados em nome de matriz ou filial.

**Garantia contratual de 5% do valor do contrato (caucao, seguro-garantia ou fianca bancaria)**
- Recorrencia: presente em pelo menos 3 dos 6 editais lidos (os 2 contratos federais/DF e o da UFJ/GO), tipicamente ausente ou dispensada em contratos pequenos sem dedicacao exclusiva
- Evidencia: UFJ/GO e MPU/DF: 'caucao em dinheiro ou em titulos da divida publica, seguro-garantia, fianca bancaria ou titulo de capitalizacao, em valor correspondente a 5% (cinco por cento) do valor'; AGESUL/MS: garantia de execucao com seguro-garantia devendo cobrir 'Acoes Trabalhistas'.

**Dedicacao exclusiva de mao de obra (quando exigida, justificada pelo volume de demanda continua)**
- Recorrencia: presente em 1 dos 6 editais lidos (Nova Bandeirantes/MT) como excecao justificada; os demais contratos continuados leem explicitamente 'SEM dedicacao exclusiva de mao de obra'
- Evidencia: Nova Bandeirantes/MT: 'Justifica-se a exigencia de dedicacao exclusiva de mao de obra e carga horaria de 44 horas semanais devido ao volume constante de demandas de pequeno porte'; UFJ/GO e MDHC/DF: 'a serem executados sem regime de dedicacao exclusiva de mao de obra'.

**EPI/EPC e Normas Regulamentadoras do MTE (NRs)**
- Recorrencia: presente em 4 dos 6 editais lidos, geralmente de forma generica (lista de NRs aplicaveis, sem citar NR-10 pelo numero explicitamente no texto)
- Evidencia: AGESUL/MS lista 'NR-05, NR-06 -- Equipamentos de Protecao Individual, NR-07, NR-08...' (sem citar NR-10 nominalmente no trecho capturado); UFJ/GO e Nova Bandeirantes/MT exigem fornecimento e uso de EPI/EPC conforme normas de seguranca do trabalho, sem nomear NRs especificas.

**Vistoria tecnica previa (facultativa na maioria dos casos lidos)**
- Recorrencia: mencionada em 2 dos 6 editais lidos, sempre como facultativa, nao obrigatoria
- Evidencia: MPU/DF: 'Vistoria: Facultativa (item 4.8 do TR)'; Estado de Goias (SME, adequacoes pontuais): anexo especifico 'ATESTADO DE VISITA TECNICA' entre os documentos do processo.

## 8. Recomendacao
**Classe geral: SELETIVO**

O volume de contratos genuinamente de SERVICO de eletrica predial em GO e pequeno e concentrado (so 4 casos incluidos na amostra coletada ate agora, de 91 casos que bateram na area) -- o grosso do mercado GO nesta area e fornecimento_puro de material (72% dos 115 casos), que a empresa deve evitar por definicao (ela vende mao de obra, nao material). Dentro do recorte que sobra, os contratos continuados de manutencao (postos e catalogos por evento) mostraram margem folgada nos casos modelados, DESDE que a equipe minima do objeto caiba no valor do item -- mas postos unicos de mao de obra dedicada de baixo valor mensal (tipo Caso 1, MT) podem ser estruturalmente deficitarios para uma empresa com CLT completo, so fechando a conta para autonomos/MEI. Recomenda-se mirar SELETIVAMENTE contratos continuados com item de posto mensal de equipe (nao posto unico) ou catalogo de manutencao corretiva por evento, e manutencao de subestacao/gerador/nobreak JA EXISTENTE (dentro do escopo, boa margem observada) -- e evitar disputar postos unicos de eletricista isolado com valor mensal baixo sem antes calcular se o custo CLT completo cabe no valor do item.

### Por subarea
| Subarea | Classe | Justificativa |
|---|---|---|
| Manutencao eletrica predial continua | seletivo | 5 casos incluidos (1 GO + 4 vizinhos), a maioria com boa margem quando o item cobre uma equipe completa (nao 1 pessoa so); evitar postos unicos de baixo valor mensal (ver Caso 1). |
| Subestacao existente (manutencao) | atacar | 4 casos incluidos (1 GO + 3 vizinhos), com margem folgada nos 2 casos modelados (subestacao/gerador/nobreak/banco de capacitores JA EXISTENTES); e o nicho onde a exclusao automatica mais erra (por confundir manutencao com implantacao), sinal de que a concorrencia pode subestimar esses editais tambem -- boa oportunidade para quem sabe interpretar o objeto corretamente. |
| Adequacoes pontuais | seletivo | Apenas 2 casos incluidos (ambos GO), ambos com item unico e escopo multi-disciplinar (eletrica + civil/AC) -- avaliar caso a caso se a fracao eletrica do escopo justifica assumir o resto (pintura, cobertura, piso) ou se e melhor formar parceria/subcontratar essas partes. |
| SPDA/aterramento | evitar_por_ora | 0 casos incluidos isoladamente na amostra atual (aparece so como item dentro de reformas excluidas por obra_grande) -- sem dados suficientes para recomendar com confianca; monitorar quando a coleta trouxer mais casos. |
| Laudos/termografia | evitar_por_ora | 0 casos incluidos na amostra atual e nenhuma referencia de preco de camera termografica nos dados -- antes de mirar esse nicho, cotar equipamento e levantar mais editais especificos de laudo/termografia. |

## Limitacoes
- Amostra final muito pequena: apenas 11 casos incluidos (4 GO + 7 vizinhos) apos revisao manual, sobre 115 casos que bateram na area nos dados ja coletados (que ainda esta em andamento). Os indicadores de desconto/ticket/percentuais tem carater DIRECIONAL, nao estatistico -- qualquer novo caso coletado pode mudar os quartis de forma significativa.
- 83 dos 115 casos (72%) sao fornecimento_puro -- registros de precos para AQUISICAO de material eletrico (sem servico), o padrao dominante do mercado GO nesta area no PNCP. Isso reflete um viés real do mercado (municipios compram material a granel e usam mao de obra propria ou eventual), nao um erro de coleta.
- n_participantes: o PNCP nao publica esse numero; ficou null em todos os 11 casos incluidos, inclusive nos 8 PDFs de edital lidos integralmente nesta analise (nenhum trazia contagem explicita de participantes no corpo do texto).
- W/textos estava vazio para eletrica_predial no momento desta analise (coletor.py ainda baixando textos na fase 4) -- todas as evidencias de exigencias de habilitacao vieram de 8 arquivos baixados manualmente via API de arquivos do PNCP (2s entre requisicoes), nao do campo 'exigencias' de casos.jsonl (que ficou vazio para os 115 casos). Quando W/textos for populado pelo coletor, rodar novamente casos.py/indicadores.py deve melhorar a cobertura desse campo.
- 2 dos 8 arquivos baixados vinham compactados em formatos que nao pudemos abrir totalmente neste ambiente (.rar foi aberto com sucesso via unrar-free; .7z do caso Itaberai/GO nao pode ser extraido por falta de ferramenta 7z) -- para esses casos usamos apenas a Relacao de Itens (PDF simples, sempre acessivel) e o objeto/itens do proprio PNCP.
- 12 dos 21 casos que a heuristica automatica havia marcado como incluidos foram RECLASSIFICADOS para excluidos apos leitura do objeto e, em 2 casos, dos itens/resultados no compra bruto (ex.: '01065846000172_2026_72' parecia ser manutencao predial pelo objeto, mas os itens reais eram filmagem, hospedagem e crachas de um evento do IFSP -- falso positivo classico de ata generica de eventos). Isso reforça que o campo 'objeto' isolado pode enganar; sempre que possivel conferimos os itens do compra bruto antes de decidir.
- 2 casos que a heuristica automatica havia marcado como equipamento_alto (por mencionar 'gerador'/'subestacao' no objeto) foram RECLASSIFICADOS para incluidos, porque o contrato e de MANUTENCAO de subestacao/gerador JA EXISTENTE (dentro do escopo explicito da area), nao de implantacao nova -- a regra automatica nao distingue manutencao de implantacao quando a palavra-chave aparece.
- Casos de 'carona'/adesao a ata de registro de precos podem trazer valor_estimado_total inflado (o teto da ata inteira, nao a necessidade real do orgao aderente) -- tratamos isso como limitacao ao interpretar tickets de casos do tipo adesao.
- Modelo de custo direto para os 4 casos de margem usa premissas conservadoras e simplificadas (equipe minima assumida a partir do objeto, nao de uma planilha de composicao de custos do proprio edital, que NUNCA foi usada como fonte de custo). Em particular, o Caso 4 (subestacao do Bioparque do Pantanal) nao modela plantao/sobreaviso 24x7 que um ativo critico de energia normalmente exige -- tratar a margem calculada ali como limite superior.
- Nao ha referencia de preco de camera termografica em custos/custos/referencias.json; nenhum numero foi inventado para essa camera no investimento (ver nota especifica na secao de investimento). A subarea de laudos/termografia nao teve nenhum caso incluido na amostra (0 de 115), entao tambem nao ha exemplar real para essa subarea neste relatorio.
- SPDA/aterramento nao teve nenhum caso incluido isoladamente como subarea principal na amostra atual (aparece apenas como item dentro de reformas prediais maiores que foram excluidas por obra_grande) -- nao ha indicadores nem exemplar dedicados a essa subarea nesta rodada.
