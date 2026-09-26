# Validação da fase 2

## Ambiente e baseline
- Trabalho executado diretamente em `C:\dev\session\monitor_licitacoes_ac`.
- Ambiente virtual existente: `.venv\Scripts\python.exe`, Python 3.12.10.
- `python -m pip check`: nenhuma dependência incompatível.
- Baseline: 15 testes aprovados antes das alterações. O arquivo `tests/test_monitor.py` permanece byte a byte igual à cópia inicial (SHA-256 conferido).
- A pasta do projeto ainda aparece como não rastreada no Git do diretório pai. Nenhum commit foi criado.

## Especificação e delegação
A especificação `ESPECIFICACAO_FASE_2.md` foi criada após leitura de todos os módulos, README, YAML e testes, antes da delegação.

| Agente | Modelo | Responsabilidade |
|---|---|---|
| `/root/luna_api` | GPT-6 Luna | HTTP, retries, paginação, validação de respostas e testes de API |
| `/root/luna_dominio` | GPT-6 Luna | classificação ME/EPP, escopo, datas, deduplicação, cache, histórico e testes de domínio |
| `/root/luna_operacao` | GPT-6 Luna | configuração, CLI, relatórios, batch Windows e testes operacionais |
| Coordenação | agente principal | especificação, revisão de interfaces/correções, testes integrados, documentação e validação final |

Os agentes implementaram no mesmo projeto local, com arquivos separados por responsabilidade. A revisão solicitou e integrou correções para página curta de itens, metadados inconsistentes, fuso sem tzdata, comparação de datas serializadas, migração de cache, identidade derivada, fechamento de recursos Windows e cabeçalho CSV.

## Arquivos modificados
- `monitor_ac/api_client.py`
- `monitor_ac/cli.py`
- `monitor_ac/coleta.py`
- `monitor_ac/config.py`
- `monitor_ac/filtros.py`
- `monitor_ac/mapeamento.py`
- `monitor_ac/persistencia.py`
- `monitor_ac/relatorio.py`
- `config.yaml`
- `executar.bat`
- `README.md`

## Arquivos criados
- `docs/ESPECIFICACAO_FASE_2.md`
- `docs/VALIDACAO_FASE_2.md`
- `docs/resultado_testes.txt` — saída da execução final
- `tests/test_api_resiliencia.py`
- `tests/test_dominio.py`
- `tests/test_operacao.py`
- `tests/test_integracao_fase2.py`

## Testes e evidências
Resultado final: **56 testes executados, 56 aprovados, código de saída 0**, em 0,456 s.
São 15 originais + 16 de API + 13 de domínio + 8 operacionais + 4 de integração.
Mensagens de erro presentes na saída são falhas simuladas deliberadamente pelos testes.

Comando da suíte completa, executado no diretório do projeto:

```powershell
C:\dev\session\monitor_licitacoes_ac\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

A saída final consta em `resultado_testes.txt`. A suíte usa respostas HTTP fictícias, SQLite e arquivos temporários; não depende de rede. Cobre os 15 testes originais, paginação inválida/repetida, retries, classificação conservadora, subcontratação, cache, migração, deduplicação, histórico, configuração, proteção HTML/CSV e falha de publicação. Os fluxos integrados exercitam coleta, persistência e relatórios reais com transporte HTTP falso.

Smoke tests do `executar.bat` executados a partir de `C:\dev\session`:
- `--version`: versão 1.0.0, código 0.
- `--help`: ajuda exibida, código 0.
- `--dias 0`: argumento rejeitado, código 2 propagado pelo batch.

## Limitações e pendências
- A interface web local foi acrescentada em `monitor_ac/web.py` e `web.bat`. Ela não
  consulta ao abrir; exige seleção explícita de modalidade e esfera, aceita palavras-chave
  do título/objeto, mostra resultados durante a execução e expõe HTML/CSV ao final. O
  smoke test HTTP confirmou `GET /` e `/api/options` com status 200. A suíte atual tem
  59 testes aprovados.
- A execução CLI sem `--modalidades` agora termina antes de qualquer chamada, com código 2.
  Todas as modalidades só podem ser liberadas explicitamente com `--todas-modalidades`.
- `api.repetir_429` passou a `false` por padrão: limite da API encerra a modalidade sem
  retries automáticos. Isso evita transformar um limite em novas chamadas; o usuário pode
  iniciar nova consulta manualmente depois.
- Não foi feita coleta completa contra a API real nesta fase; falta conferência manual de uma amostra de editais e de seus itens no PNCP. Os testes não certificam disponibilidade do serviço externo.
- A classificação reflete os itens publicados, sem interpretar o edital. Informação desconhecida produz classificação conservadora. O domínio de benefícios foi conferido no [manual oficial](https://pncp.gov.br/manual/pt-br/2.5/tabelas_de_dominio/tipo_de_beneficio.html).
- O cache depende da atualização informada pelo órgão; não há política adicional de expiração por idade. Sem identificação canônica da compra, o hash do conteúdo evita colisões por truncamento, mas mudanças de conteúdo podem representar uma nova identidade.
- A publicação é atômica por arquivo, não pelo par HTML/CSV. Interrupção entre substituições pode deixar versões diferentes. Execuções simultâneas não são coordenadas por trava global.
- Datas atuais usam UTC−03:00; não há suporte histórico ao horário de verão. A máquina deve estar configurada com o horário local de Brasília para a janela calculada por `datetime.now()`.
- O Agendador de Tarefas não foi configurado nem alterado.
- A cópia de segurança pré-alteração está em `C:\dev\session\monitor_licitacoes_ac_baseline`. Ela inclui uma cópia redundante da venv: a revisão automática de aprovação bloqueou a remoção dessa pasta redundante e ela foi mantida. O ambiente original continua sendo o utilizado.

## Execução local
```powershell
Set-Location C:\dev\session\monitor_licitacoes_ac
.\executar.bat --dias 30
# Somente contratações com benefício ME/EPP:
.\executar.bat --dias 30 --somente-me-epp
```

Relatórios: `saida\ultimo.html` e `saida\ultimo.csv`; banco: `saida\historico.db`; log: `logs\monitor.log`. Nenhuma dependência nova foi instalada.
