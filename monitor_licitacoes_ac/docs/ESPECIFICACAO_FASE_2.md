# Especificação técnica — fase 2

## 1. Objetivo e escopo
Fortalecer o monitor local existente de licitações de climatização de Goiás, preservando CLI, configuração YAML, SQLite e relatórios HTML/CSV. Base verificada: 15 testes offline aprovados em Python do ambiente `.venv`. Diretório real: `C:\dev\session\monitor_licitacoes_ac`. Não inclui aplicação web, implantação remota, agendamento automático nem interpretação jurídica do edital.

## 2. Funcionalidades existentes
Consulta por modalidade e paginação; retries e backoff; filtros normalizados com inclusão, exclusão e termos condicionais; escopo por UF, esfera, município e prazo; classificação por itens ME/EPP; cache por atualização; histórico SQLite; HTML responsivo e CSV com BOM; logs rotativos; CLI e execução Windows.

## 3. Problemas, riscos e lacunas observados
- API: formatos inesperados podem causar exceções genéricas; páginas repetidas podem prolongar indefinidamente a coleta; Retry-After só aceita segundos.
- Benefícios: código desconhecido e combinação de itens conhecidos/desconhecidos podem resultar em ampla participação indevida; subcontratação não tem classificação própria.
- Identidade: fallback truncado na coleta e chave vazia no SQLite permitem colisões; primeira versão duplicada prevalece mesmo quando há versão mais recente.
- Escopo: UF, esfera e prazo ausentes passam como se comprovadamente elegíveis; datas com offset perdem o fuso sem conversão.
- Cache/histórico: ausência de data pode manter cache indefinido; filtro somente ME/EPP impede registrar demais candidatos; estado atualizado considera apenas data.
- Operação: configuração e modalidades pouco validadas; falhas de publicação ficam fora do tratamento central; recursos podem ficar abertos.
- Relatórios: URLs não restringem esquema; textos podem virar fórmulas no Excel; nomes datados colidem no mesmo minuto; publicação pode deixar arquivo parcialmente escrito.
- Cobertura: os 15 testes cobrem fluxo feliz e falhas básicas, mas não esses casos de regressão.

## 4. Melhorias necessárias
Validar respostas e limitar paginação, registrar falhas como ErroAPI e respeitar Retry-After em data HTTP. Classificar informação desconhecida conservadoramente, explicitar subcontratação e preservar regras atuais de exclusividade/cota/parcial. Usar identidade canônica ou hash completo; escolher duplicata mais atual; restringir escopo a dados comprováveis. Converter offsets para horário de Brasília. Invalidar cache incompleto/sem atualização; registrar candidatos antes do filtro de apresentação. Validar configuração/CLI antes da rede e garantir encerramento de recursos. Proteger HTML/CSV e preparar arquivos antes da substituição de cada último relatório.

## 5. Arquitetura e arquivos
Manter `cli -> config, api_client, coleta, persistencia, relatorio`; coleta usa filtros e mapeamento. Não adicionar dependências de produção.
- Agente Luna API: `monitor_ac/api_client.py`, `tests/test_api_resiliencia.py`.
- Agente Luna domínio: `monitor_ac/filtros.py`, `mapeamento.py`, `coleta.py`, `persistencia.py`, `tests/test_dominio.py`.
- Agente Luna operação: `monitor_ac/config.py`, `cli.py`, `relatorio.py`, `executar.bat`, `tests/test_operacao.py`.
- Coordenação: documentação, config.yaml se necessário, revisão cruzada, testes e integração.
Não editar arquivos de outro responsável sem combinar. Preservar testes existentes e bancos existentes; mudanças de esquema devem ser compatíveis e não destrutivas.

## 6. Critérios de aceitação
1. Os 15 testes originais continuam aprovados, acrescidos de regressões para as correções.
2. Resposta malformada/repetida termina em falha registrada, sem falso sucesso ou loop infinito; 204 permanece vazio válido.
3. Benefício desconhecido nunca prova ampla participação nem exclusividade; subcontratação aparece como benefício explícito.
4. Compras distintas sem número não colidem; duplicatas são únicas; cache inválido é reconsultado; histórico conserva primeira aparição.
5. Prazo e localização ausentes não comprovam escopo; datas equivalentes com offsets produzem horário consistente.
6. Erros operacionais retornam código 2; execução parcial retorna 1; sucesso retorna 0; falha total de consulta conserva relatório anterior.
7. HTML não gera links executáveis fora de HTTP(S); CSV neutraliza fórmulas; arquivos datados não colidem; falha de geração conserva últimos relatórios.
8. Batch funciona a partir de outro diretório, usa a venv local e propaga saída; README descreve regras e limitações reais.

## 7. Estratégia de testes
Unittest offline com sessões HTTP falsas, relógios/esperas controlados quando necessário, SQLite e saídas temporárias. Cobrir paginação, retry, HTTP 4xx/429/5xx, dados inválidos, classificação mista, cache, deduplicação, escopo, configuração, publicação e códigos de saída. Executar suíte inteira usando `.venv\Scripts\python.exe -m unittest discover -s tests -t . -v`; validar versão, dependências e batch com --help/--version de outro diretório. Consulta documental oficial pode apoiar contrato PNCP; teste offline não certifica disponibilidade nem conteúdo da API real.

## 8. Etapas de implementação
1. Inspeção e baseline (concluídos: 15/15).
2. Registrar esta especificação antes da delegação.
3. Executar os três pacotes independentes com agentes GPT-6 Luna no diretório compartilhado.
4. Revisar mudanças, resolver interfaces e complementar regressões encontradas.
5. Atualizar README e registrar resultados/pendências em `docs/VALIDACAO_FASE_2.md`.
6. Executar suíte completa e smoke tests Windows; entregar instruções locais.
