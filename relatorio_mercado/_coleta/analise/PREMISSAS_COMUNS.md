# Premissas comuns de custo (valem para TODAS as áreas)

Fonte de cada número: `custos/custos/referencias.json`. Cite fonte_url e data de acesso
(2026-09-27) no texto. Onde a linha abaixo diz "estimativa", deixe isso explícito no texto.

## Mão de obra (valores mensais de 2026)

| Função | Piso usado | Base |
|---|---|---|
| Técnico em refrigeração / mecânico de refrigeração | R$ 3.450,55 | **estimativa**: piso SEAC-GO 2025 do eletricista (R$ 3.229,78) × 1,06834 (reajuste de 2026 da CCT SEAC/SEACONS) |
| Eletricista | R$ 3.450,55 | mesma base |
| Ajudante | R$ 1.711,00 | SEAC 2025 R$ 1.601,55 × 1,06834 (**estimativa**) |
| Motorista/operador de caminhão munck | R$ 1.870,00 | CCT SETCEG 2026/2028; o operador de munck não tem piso próprio em GO (**limitação**) |
| Engenheiro responsável técnico | R$ 13.778,50 para 8 h | Lei 4.950-A/66; use a fração de tempo compatível com o contrato (ex.: 10% a 20%) |

- **Periculosidade:** +30% sobre o salário-base do eletricista (NR-10) em elétrica e iluminação pública.
- **Encargos sociais:** SINAPI GO mensalista sem desoneração, **69,28%** (vigência 01/2026). Mostre a sensibilidade com o horista (107,72%) em uma linha.
- **Vale-alimentação:** R$ 22,54/dia × 22 = R$ 495,88/mês por empregado (CCT da construção civil de GO).
- **EPI, uniforme e ferramentas de desgaste:** R$ 150/mês por empregado (**estimativa**).

## Veículos

- **Veículo leve:** R$ 1,20/km (**estimativa**: gasolina a R$ 6,672/L da ANP-GO ÷ 10 km/L = R$ 0,67, mais R$ 0,53 de manutenção, pneus, depreciação e seguro).
- **Caminhão munck:** R$ 213,33/h (GOINFRA T334, fev/2026, código 072080, mínimo de 4 h/dia; já inclui o operador). É o custo de referência de mercado. Para caminhão próprio, o custo real fica abaixo desse valor: registre como premissa conservadora.
- **Caminhão guindauto com cesto aéreo:** R$ 330,89/h (SICRO E9690 GO, confiabilidade média).

### Adendo: caminhão munck PRÓPRIO (vale para todas as áreas)

A empresa já tem os 2 munck. Nas margens, use o custo do caminhão próprio calculado na
análise de munck (`areas/munck.json`, campo premissas_custo). Esse custo inclui operador,
diesel, manutenção, pneus, seguro e depreciação de um munck usado. Os valores de GOINFRA e
SICRO ficam como referência de mercado ou de locação.

| Combustível por conta de | Custo direto | Preço de lucro zero | Preço com BDI |
|---|---|---|---|
| Contratada | R$ 186,77/h | R$ 219,55/h | R$ 235,82/h |
| Órgão | R$ 71,30/h | — | R$ 90,02/h |

Se o edital exigir cesto aéreo, a adaptação de cesto no munck não tem preço publicado.
Informe isso como investimento a cotar; o caminhão novo com cesto de fábrica custou
R$ 747.667 em Jataí, e serve só como teto.

## BDI (fórmula do TCU, Acórdão 2622/2013)

BDI = [(1 + AC + S + R + G)(1 + DF)(1 + L) / (1 − T)] − 1

- **Climatização, refrigeração, elétrica predial e manutenção predial:** composição de "Construção de Edifícios", valores médios: AC 4,00%; S+G 0,80%; R 1,27%; DF 1,23%; L 7,40%.
- **Iluminação pública e redes:** composição de "Redes de Distribuição de Energia", valores médios: AC 5,92%; S+G 0,51%; R 1,48%; DF 1,07%; L 8,31%.
- **Tributos:** T = 8,65% (PIS/COFINS cumulativos 3,65% + ISS 5%, alíquota de Goiânia). Se o município for outro, mantenha 5% como teto conservador.
- **Preço com BDI** = custo direto × (1 + BDI).
- **Preço de lucro zero** = custo direto × (1 + BDI calculado com L = 0).
- **Classificação do preço vencedor:**
  - "folgado": ≥ preço com BDI;
  - "apertado": entre o preço de lucro zero e o preço com BDI;
  - "prejuízo provável": abaixo do preço de lucro zero.
- **Simples Nacional** (anexo III/IV): pode baixar os tributos, mas não é modelado. Cite como observação.

## Investimento inicial

Some:
1. folha e custos de 2 meses (pagamento em até ~30 dias após a medição mensal, então o 1º recebimento cai perto do dia 60);
2. estoque inicial de materiais de reposição;
3. mobilização (uniformes, EPI e ferramentas faltantes);
4. garantia de 5% do valor anual. Em caução, o valor é imobilizado; em seguro-garantia, o custo é o prêmio de ~0,5% a 1,5% ao ano. Mostre as duas formas.

Classificação: baixo até R$ 50 mil; médio de R$ 50 mil a R$ 200 mil; alto acima de R$ 200 mil.

## Produtividade

Declare a premissa e a justificativa. Exemplo: manutenção preventiva mensal de um split de até 24 mil BTU leva de 0,75 h a 1 h de um técnico com ajudante, mais deslocamento. Use hipóteses conservadoras e mostre a sensibilidade de ±25% em uma linha.
