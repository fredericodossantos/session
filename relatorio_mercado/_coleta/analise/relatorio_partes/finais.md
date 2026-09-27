## Oportunidades para os caminhões munck

- **Locação de caminhão com operador, paga por hora.** É o uso mais frequente na amostra de Goiás.
  - A hora vencedora em GO ficou entre R$ 180 e R$ 406, com mediana de R$ 295.
  - A referência da GOINFRA é R$ 213,33/h (tabela T334, fev/2026).
  - O piso seguro com caminhão próprio é de uns **R$ 220/h** quando o diesel é da empresa e de uns **R$ 90/h** quando o diesel é do órgão.
- **Caminhão com cesto aéreo para iluminação pública, por hora.** Várias prefeituras de GO contratam só o caminhão com cesto e o operador. Nos editais lidos, cerca de 3 em 6 aceitam munck ou guindauto com cesto acoplado. Ter um cesto adaptado a um dos munck abre esse mercado. O preço da adaptação não é publicado e precisa ser cotado com fornecedores.
- **Apoio a contratos da própria empresa.** Içamento de condensadoras, troca de luminárias em altura e implantação de poucos postes. Na amostra quase não há licitações só disso. O ganho vem de não precisar alugar caminhão nos contratos de climatização e elétrica.
- **Break-even:** os dois caminhões precisam faturar juntos cerca de **136 horas por mês** para cobrir o custo fixo (operador, seguro e depreciação).

## Riscos e exigências que costumam barrar empresas do nosso porte

- **Atestados com quantidade mínima.** Na iluminação pública aparecem, por exemplo, 1.452 pontos atendidos. Em climatização e PMOC pedem responsável técnico com CREA e ART/CAT. Sem acervo técnico registrado no nome dos engenheiros, a empresa fica fora.
- **Preço vencedor abaixo do custo com carteira assinada.** Postos únicos de eletricista com valor mensal baixo, e locações de munck abaixo de ~R$ 220/h com diesel por conta da empresa, só fecham para MEI ou autônomo. O mesmo vale para descontos acima de ~46% em contratos de climatização item a item.
- **Cláusula de combustível.** No munck e no cesto aéreo, quem paga o diesel muda o custo da hora em mais de 50%. Leia essa cláusula antes de dar o lance.
- **Ata de registro de preços sem garantia de volume.** É o formato mais comum na amostra. A ata não obriga o órgão a contratar tudo o que registrou, então a receita fica incerta mesmo com a ata vencida.
- **Dedicação exclusiva de mão de obra.** É frequente na manutenção predial. Traz conta vinculada, repactuação e risco trabalhista, e costuma exigir sair do Simples Nacional.
- **Garantia contratual de até 5%** (Lei 14.133, art. 98). O seguro-garantia custa de ~0,5% a 1,5% ao ano e evita imobilizar caixa.
- **Prazo de pagamento.** A Lei 14.133 não fixa prazo em dias; ele vem do contrato. O modelo de investimento supõe o primeiro recebimento perto do dia 60.

## Limitações dos dados

- **Número de participantes.** O PNCP não publica esse dado. Ele só apareceu em 1 dos 535 casos analisados, lido no texto do edital. A mediana de participantes não pôde ser calculada.
- **Amostras pequenas fora de climatização.** Em GO, sobraram após a triagem:
  - refrigeração: 5 casos;
  - iluminação pública: 3;
  - elétrica predial: 6;
  - munck: 12;
  - manutenção predial: 2.

  Esses números são direcionais, não estatísticos.
- **A busca do PNCP é textual e traz muito ruído.** Dos 335 casos detalhados em GO, 240 foram excluídos na triagem. Por motivo:
  - fornecimento puro de material: 129;
  - fora do escopo: 41;
  - menção de passagem: 35;
  - equipamento caro: 30;
  - obra grande: 5.
- **Nenhum caso de SPDA ou termografia em GO** apareceu com resultado no período, nem com busca dirigida a esses termos.
- **Órgãos cadastram serviço como "material" no PNCP.** Por isso a triagem foi revista caso a caso por analistas.
- **Desconto.** O desconto usa o preço unitário do primeiro colocado, ponderado pelo valor estimado de cada item. Compras com mais de 40 itens com resultado (20 na coleta suplementar) tiveram só os primeiros itens considerados.
- **Estados vizinhos** têm cobertura parcial: até 3 páginas de busca por termo e até 8 casos por área e estado.
- **Custos de referência.** Parte dos custos são estimativas marcadas como tal:
  - piso de técnico de refrigeração de 2026;
  - custo por km de veículo leve;
  - manutenção e depreciação do munck;
  - adaptação de cesto aéreo.

  A tabela completa, com fonte e confiabilidade, está na aba `custos_referencia` da planilha.
- **Janela de 15 páginas.** Termos muito genéricos, como "manutenção ar condicionado", bateram no teto de 15 páginas de busca antes de cobrir os 24 meses inteiros.

## Método e fontes

- **Licitações:** API pública do PNCP (busca, detalhe da compra, itens, resultados e arquivos), acessada em 27/09/2026.
  - Período: editais encerrados de 27/09/2024 a 27/09/2026.
  - Modalidades: pregão e concorrência, eletrônicos ou presenciais.
  - Volume: cerca de 12 mil requisições, a no máximo 1 por segundo.
- **Custos:**
  - CCT da construção civil de GO (SINDUSCON-GO/SINTRACOM 2025/2027);
  - CCT e CDPS SEAC/SEACONS-GO;
  - CCT SETCEG 2026/2028 (motoristas);
  - Lei 4.950-A/66 (piso de engenheiro);
  - encargos sociais do SINAPI (8ª ed., fev/2026, Goiás);
  - Acórdão TCU 2622/2013 (BDI);
  - tabela GOINFRA T334 (fev/2026);
  - SICRO/DNIT (jan/2026);
  - ANP (preço médio de combustível em GO, semana de 20 a 26/09/2026);
  - lojas online para materiais;
  - Código Tributário de Goiânia (ISS de 5%).

  As URLs estão na planilha.
- **Margem.** Custo direto mais BDI pela fórmula do TCU, com os valores médios de cada tipo de obra e tributos de 8,65% (PIS/COFINS 3,65% + ISS 5%). O preço vencedor foi classificado como:
  - **folgado:** igual ou acima do preço com BDI;
  - **apertado:** entre o preço de lucro zero e o preço com BDI;
  - **prejuízo provável:** abaixo do preço de lucro zero.

  A planilha de custos do próprio edital nunca foi usada como custo.
