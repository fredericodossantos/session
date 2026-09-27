# Como continuar o estudo de mercado (prompt para o próximo agente)

Este arquivo existe para que uma nova sessão retome o trabalho se a anterior acabar no
meio. Leia tudo antes de agir. Responda sempre em português, de forma direta.

## Preferências do usuário (obrigatórias)

- O usuário autorizou criar arquivos, pastas, commits, pushes e tarefas persistentes sem
  perguntar. **Não interrompa** com perguntas; decida pelo mais sensato e registre a
  decisão. Chame o usuário só em caso extremo ou quando algo for impossível (ex.: rede
  bloqueada). Se precisar perguntar, use opções clicáveis (AskUserQuestion) e continue
  trabalhando no que não depende da resposta.
- Delegue a subagentes mais baratos sempre que possível: Haiku para consultas e tarefas
  mecânicas; Sonnet para código, revisão e análise. Resolva você mesmo só o que depende de
  contexto que só você tem. Confira os números que os subagentes entregarem.
- Branch de trabalho: `claude/cool-rubin-rw63g1` (repositório `fredericodossantos/session`).
- O ambiente de nuvem precisa de **Acesso à rede = Completo** (PNCP, sites de CCT, SINAPI,
  TCU, lojas). Se algo der 403 no proxy, peça ao usuário para conferir essa configuração.

## Pedido original (resumo fiel)

Produzir um **relatório de mercado** para uma empresa de engenharia de Goiás que disputa
licitações, indicando em quais áreas concentrar esforços: licitações **sem investimento
alto**, **com volume** e **com margem boa no lance vencedor**.

**Empresa:** eng. mecânico, eng. eletricista, técnicos/eletricistas e mecânicos de
refrigeração; ferramental de manutenção; **2 caminhões com munck** e veículos leves. Atua em
ar-condicionado/climatização, PMOC, refrigeração, instalações elétricas e iluminação
pública. Sede em GO; pode disputar DF, MT, MS, TO e MG. Quer contratos cujo custo seja
principalmente mão de obra, deslocamento e materiais de reposição baratos, pagos por
medição (de preferência mensal).

**Excluir (e contar quantos por motivo):**
1. fornecimento e instalação de grupos geradores, subestações novas, chillers, VRF ou
   centrais completas, usinas solares, ou qualquer implantação com equipamentos acima de
   ~40% do valor;
2. obras de implantação acima de ~R$ 1,5 mi (salvo como referência);
3. fornecimento puro de bens sem serviço relevante;
4. objeto que só cita o termo de passagem (ônibus com ar, evento com gerador etc.).

**Áreas** (catálogo `monitor_licitacoes_ac/catalogo_areas.yaml`):
- **Climatização:** manutenção preventiva e corretiva, PMOC, higienização, recarga de gás,
  instalação/remanejamento com equipamento do órgão, contratos por unidade ou BTU.
- **Refrigeração:** câmaras frias, refrigeradores e bebedouros.
- **Iluminação pública:** manutenção, ronda, pequenas extensões, poda. Aponte em cada caso
  se o edital exige **cesto aéreo** ou aceita **munck/guindauto com cesto**.
- **Elétrica predial:** manutenção, quadros, SPDA/aterramento, subestação existente,
  termografia e laudos.
- **Munck:** locação com operador, içamento, postes.
- **Manutenção predial integrada** com núcleo em elétrica e climatização.

**Método:**
- **Fonte principal:** PNCP (a cerca de 1 requisição por segundo; em HTTP 429, parar e esperar).
- **Período:** últimos 24 meses (desde 2024-09-27). Goiás primeiro, depois uma amostra dos
  estados vizinhos.
- **Amostra por área:** 15 a 40 licitações encerradas com resultado.
- **Registro por caso:**
  - órgão, município/UF, data, modalidade e objeto;
  - contrato continuado ou pontual, e a vigência;
  - valores estimado e homologado, e o desconto (1 − homologado/estimado);
  - nº de participantes (se existir);
  - se foi exclusiva ME/EPP, e se houve deserta ou fracassada;
  - exigência de veículos (cesto aéreo, munck, frota mínima).
- **Investimento inicial:** materiais, mobilização, garantia até 5% e folha do 1º mês,
  mais o prazo de pagamento. Classificar em baixo (até R$ 50 mil), médio (R$ 50–200 mil) ou
  alto (acima de R$ 200 mil).
- **Margem**, em 3 a 5 casos típicos por área, com custo de mercado:
  - mão de obra pelos pisos da CCT de GO mais encargos;
  - materiais a preço de loja;
  - deslocamento e munck;
  - BDI do TCU (Acórdão 2622/2013);
  - **nunca** a planilha do próprio edital.

  Classificar o preço vencedor em "folgado" (≥ preço com BDI), "apertado" (entre lucro
  zero e preço com BDI) ou "prejuízo provável" (abaixo de lucro zero), explicando as
  premissas.
- **Indicadores por área:**
  - volume por ano em GO e valor total;
  - ticket mediano;
  - mediana de participantes;
  - desconto (mediana e quartis);
  - % de desertas/fracassadas;
  - % de exclusivas ME/EPP;
  - investimento típico;
  - margem;
  - exigências de habilitação recorrentes.

**Entregáveis:**
1. **Relatório (HTML ou Markdown, em português):**
   - resumo executivo de 1 página com o ranking atacar / seletivo / evitar e 1–2 linhas de
     justificativa por área;
   - uma seção por área, com indicadores e 3 a 5 casos com link do PNCP;
   - regras de lance por área;
   - oportunidades para os munck;
   - riscos de habilitação;
   - limitações dos dados.
2. **Planilha .xlsx:** uma aba de dados brutos (um caso por linha, com link) e uma aba de
   indicadores por área **calculados por fórmula**.

**Regras:**
- Não invente números; diga quando a amostra for pequena.
- Cite a fonte (URL + data de acesso) de todo preço e todo caso.
- Sem login, sem formulários, sem executáveis.
- Sem CPF ou dados pessoais: razão social de empresa pode aparecer; se o fornecedor for
  pessoa física, não grave nome nem documento.

## Estado em 2026-09-27 (quando este arquivo foi escrito)

**1. Coleta PNCP**, por um subagente Sonnet:
- O script está em `relatorio_mercado/_coleta/coletor.py`, com checkpoint em
  `_coleta/checkpoint.json` e log em `_coleta/coletor.log`. Ele retoma sozinho e pula o
  que já existe.
- As fases:
  1. índice de buscas em GO (`go_hits*.jsonl`) e nos vizinhos (`viz_hits*.jsonl`);
  2. seleção de candidatos (pregão/concorrência com resultado) em `selecao.jsonl`;
  3. detalhe + itens + resultados + arquivos em `compras/{cnpj}_{ano}_{seq}.json`;
  4. texto dos TR/editais em `textos/*.txt`.
- **Para retomar:** copie `relatorio_mercado/_coleta/` para uma pasta de trabalho fora do
  repositório (o script usa a própria pasta como diretório de dados), rode
  `python3 -u coletor.py` em background e acompanhe o log. Confira `stats.json` e o fim do
  log para saber em que fase parou.
- **Endpoints que funcionam:**
  - busca: `https://pncp.gov.br/api/search/?q=...&tipos_documento=edital&status=encerradas&ufs=GO&ordenacao=-data&tam_pagina=100&pagina=N`;
  - detalhe: `https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}`
    (o caminho `/api/pncp/v1/.../compras/{ano}/{seq}` dá 301);
  - itens: `https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens?pagina=1&tamanhoPagina=500`;
  - resultados: `.../itens/{n}/resultados`;
  - arquivos: `.../arquivos`.
- A API às vezes responde "Empty reply" ou ProxyError: é só tentar de novo com espera.
- **O PNCP não publica o número de participantes**; registre essa limitação, ou extraia
  das atas/resultados em PDF quando houver.

**2. Referências de custo**, por um subagente Sonnet: pastas `relatorio_mercado/_coleta/custos/`
(PDFs e textos de CCT, BDI etc.). A saída esperada é `custos/referencias.json` e
`custos/referencias.md`, com valor, fonte, data de acesso e confiabilidade. Se esses dois
arquivos não existirem, refaça esta etapa.

**3. Cópia automática:** a cada 20 min, um script de snapshot (autorizado pelo usuário)
copiava a pasta de trabalho para `relatorio_mercado/_coleta/` e fazia commit e push. Ele
morre junto com o container; se precisar, recrie a mesma rotina.

**4. Pipeline de análise pronto:** `relatorio_mercado/_coleta/analise/`
(`casos.py` → `casos.jsonl`; `indicadores.py` → `indicadores.json/.md`; `planilha.py` →
`planilha.xlsx`, com indicadores por fórmula já conferidos no LibreOffice). Veja o
`analise/README.md`. Rode os três scripts de novo quando a coleta terminar. O LibreOffice
(`apt-get install -y libreoffice-calc`) serve para recalcular e conferir as fórmulas.

## Próximos passos

1. Terminar a coleta e as referências de custo (itens 1 e 2 acima).
2. **Análise por área**, com um subagente Sonnet por área em paralelo, lendo `compras/` e
   `textos/`:
   - classificar relevância e exclusões, com contagem por motivo;
   - separar contrato continuado de pontual;
   - calcular o desconto por caso (valor homologado ÷ estimado, somando itens com resultado);
   - marcar deserta ou fracassada, ME/EPP, exigências de veículo e de habilitação;
   - montar o investimento inicial e a margem em 3 a 5 casos típicos, com
     `custos/referencias.json`;
   - saída: um JSON e um MD por área.
3. **Consolidar** (você mesmo):
   - conferir a consistência;
   - montar a planilha `relatorio_mercado/estudo_mercado.xlsx` (aba de dados brutos e aba
     de indicadores com fórmulas; use openpyxl e confira as fórmulas com LibreOffice, se
     houver);
   - montar o relatório `relatorio_mercado/relatorio_mercado.html`;
   - publicar o HTML como Artifact (carregue antes o skill `artifact-design`);
   - enviar a planilha ao usuário (SendUserFile);
   - fazer commit e push, desligar a cópia automática e avisar o usuário com um resumo
     curto.
