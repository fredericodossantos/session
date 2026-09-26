# Monitor de licitações de engenharia — Goiás

Busca no **PNCP** (Portal Nacional de Contratações Públicas) as contratações com
recebimento de propostas **em aberto** do Estado de Goiás e dos municípios goianos,
filtra oportunidades de engenharia mecânica, elétrica e climatização,
identifica as **exclusivas para ME/EPP** e gera relatórios **HTML**, **CSV** e **Excel**.

## Instalação (Windows)

1. Instale o Python 3.11 ou mais novo (python.org). Na instalação, marque *Add python.exe to PATH*.
2. Abra o **Prompt de Comando** na pasta `monitor_licitacoes_ac` e rode:

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

No Linux/macOS: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

`executar.bat` e `web.bat` usam `.venv\Scripts\python.exe` quando ele existe. Sem a venv,
eles tentam o Python do sistema (`py -3`) só depois de conferir se as dependências
(`requests`, `yaml`, `openpyxl`) estão instaladas; se não estiverem, ou se `py` não existir,
mostram um erro claro (sem acentos, para não embolar em consoles cp850/cp437) com os dois
comandos acima e saem sem tentar rodar o programa. `web.bat` também pausa nesse caso, para dar
tempo de ler a mensagem antes do console fechar (foi aberto com duplo clique).

## Uso

### Interface web local (recomendada)

Para abrir a tela de consulta sem iniciar nenhuma requisição automaticamente:

```bat
web.bat
```

O navegador abrirá `http://127.0.0.1:8765`. A página usa a navegação **Consultar**,
**Buscas salvas**, **Histórico e relatórios** e **Ajuda**. Na consulta, escolha setores,
tipos de serviço opcionais, Goiás (GO), prazo de propostas, esfera e pelo menos uma
modalidade. Use os atalhos de perfil ou de busca e revise o resumo dos filtros antes de
clicar em **Consultar licitações**. Abrir ou navegar pela interface não consulta o PNCP.

O catálogo da fase 3 organiza os setores em grupos e inclui iluminação pública com
subáreas, além de perfis de engenharia mecânica, elétrica, atuação conjunta e empresa
multidisciplinar. A pesquisa do catálogo filtra opções localmente. Nenhuma seleção inicia
uma consulta até o botão principal ser acionado.

As palavras do título/objeto são separadas por vírgula e qualquer uma pode corresponder.
Por exemplo: `hospital, manutenção, iluminação pública`. Elas refinam os resultados
coletados; portanto, escolher menos modalidades continua sendo a forma principal de
reduzir chamadas à API.

Os setores definem o assunto da oportunidade; serviços como instalação, manutenção,
fornecimento e projeto são refinamentos opcionais. Contextos como hospitais, escolas,
indústria e data centers também podem refinar a busca. Iluminação pública é um setor
próprio e não depende de termos de climatização. As buscas legadas preservam os filtros
`areas` existentes quando são carregadas.

O intervalo padrão da tela é de 2 segundos entre requisições. Durante uma execução, a
tela apresenta etapa, tempo, chamadas e cartões atualizados pela identidade do item.
**Cancelar consulta** solicita a interrupção preservando o que já foi encontrado. O limite
padrão é de 120 segundos e 60 tentativas HTTP por consulta; chamadas já em andamento podem
terminar antes de a tela mostrar o encerramento. A interface não inicia coletas simultâneas.

**Consultar licitações** é a única ação da tela que inicia uma consulta ao PNCP. Para
reduzir chamadas, selecione somente as modalidades necessárias. O servidor é local e
fica disponível apenas em `127.0.0.1` por padrão. No modo `cloudflare` (opcional, com
login), a identidade só aparece depois que o servidor valida o JWT do Cloudflare Access;
um cabeçalho de e-mail isolado não autentica.

Use **Salvar filtros** para informar um nome e guardar somente os critérios. Na tela
**Buscas salvas**, você pode carregar ou excluir a busca; um nome vazio ou repetido é
recusado sem sobrescrever uma busca existente. O histórico e os snapshots de consulta
permanecem disponíveis depois de atualizar a página. Cada execução tem arquivos próprios
para baixar em Excel (`.xlsx`), HTML e CSV.

O município pode ser escolhido pelo nome (catálogo local dos 246 municípios de Goiás em
`municipios_go.json`); o código IBGE manual continua em **Avançado**. O histórico é
paginado. Durante a consulta, a tela pede ao servidor só as novidades desde a última
revisão (`GET /api/status?consulta_id=...&since=...`), sem recarregar a lista inteira.

O modo local não tem login: ele só aceita conexões em `127.0.0.1`/`localhost` e recusa
requisições encaminhadas por túnel. Para acesso pela internet, use `subir_publico.bat`
(modo `publico`: sem login, exposto pelo Cloudflare Tunnel).

### Acesso público pelo Cloudflare

`subir_publico.bat` inicia o servidor em `--modo-acesso publico` (sem login; decisão
explícita do dono do projeto) e só depois inicia o túnel; antes de subir o
`tools\cloudflared.exe`, confere a assinatura Authenticode do executável (detalhes em
[docs/CLOUDFLARE_TUNNEL.md](docs/CLOUDFLARE_TUNNEL.md)) e recusa continuar se ela não for
confirmada como da Cloudflare. O lançador recusa um servidor na porta 8765 que não
confirme o modo `publico`. O endereço deste projeto é
`https://licitacoes-ac.98fred.dev/`; o computador precisa permanecer ligado e o token do
túnel fica em `cloudflare-tunnel.token`, ignorado pelo Git.

Se um dia o projeto quiser exigir login antes de liberar o domínio, o modo
`--modo-acesso cloudflare` continua disponível: ele valida o JWT do Cloudflare Access,
exigindo `acesso.team_domain` e `acesso.audience` em `config.yaml` (ou as variáveis
`CF_ACCESS_TEAM_DOMAIN` e `CF_ACCESS_AUD`) e um provedor/política configurados no painel
do Cloudflare Access.

```bat
executar.bat --modalidades 6 --dias 30       :: pregão eletrônico, próximos 30 dias
executar.bat --modalidades 6 --dias 15       :: janela de 15 dias
executar.bat --municipio 5208707             :: só Goiânia (código IBGE)
executar.bat --somente-me-epp                :: só com benefício ME/EPP
executar.bat --incluir-federal               :: inclui órgãos federais sediados em GO
executar.bat --modalidades 6,8               :: só pregão eletrônico e dispensa
executar.bat --todas-modalidades --dias 30   :: autoriza explicitamente todas as modalidades
executar.bat --salvar-bruto -v               :: salva as respostas da API p/ conferência
```

(Equivale a `.venv\Scripts\python -m monitor_ac ...`.)

Ao final o programa mostra no console quantas licitações a API retornou, quantas passaram
no filtro e quantas têm benefício ME/EPP, e onde estão os arquivos.

Códigos de saída: `0` ok · `1` concluiu com alguma falha de requisição ou aviso na publicação
(resultado pode estar incompleto; ver log) · `2` nenhuma consulta funcionou ou erro inesperado
(relatório anterior mantido).

Se `ultimo.xlsx` (ou `.html`/`.csv`) estiver aberto no Excel/outro programa no momento da
execução, a atualização desses atalhos pode falhar (arquivo bloqueado no Windows). Isso não
é tratado como falha total: os relatórios datados desta execução (`licitacoes_ac_go_*.*`)
já foram publicados normalmente, e `ultimo.*` é revertido ao estado anterior (nenhum atalho
fica misturando execuções diferentes). O programa termina com código `1` e um aviso no
console/log dizendo qual arquivo está bloqueado e onde estão os relatórios desta execução;
feche o programa que está com o arquivo aberto e rode novamente para atualizar `ultimo.*`.

### Arquivos gerados (pasta `saida/`)

| Arquivo | Conteúdo |
|---|---|
| `ultimo.html` | Relatório da execução mais recente (abra no celular/navegador) |
| `ultimo.csv` | Mesmos dados em CSV (`;`, UTF-8 com BOM, abre direto no Excel) |
| `ultimo.xlsx` | Planilha Excel formatada, com filtros e cabeçalho congelado |
| `licitacoes_ac_go_*.html` / `*.csv` | Cópias datadas com identificador único por execução |
| `historico.db` | Histórico SQLite (licitações já vistas + registro das execuções) |
| `bruto_*.json` | Respostas brutas da API (só com `--salvar-bruto`) |

Log: `logs/monitor.log` (rotativo, 5 × 2 MB) com cada execução e cada falha de requisição.

O relatório vem ordenado pela **data-limite de propostas** (mais próxima primeiro). Os cartões
**Exclusiva ME/EPP** ficam em verde com ★; cota reservada em âmbar; parcial em azul. Licitações
vistas pela primeira vez recebem a marca **NOVA**; as que mudaram no PNCP desde a execução
anterior, **atualizada**.

## Configuração (`config.yaml`)

- `filtro.termos_inclusao`: basta um para a licitação entrar (ar condicionado, climatização,
  split, refrigeração, PMOC...).
- `filtro.termos_condicionais`: só contam junto de um termo de inclusão
  (ex.: "manutenção preventiva e corretiva").
- `filtro.termos_exclusao`: descartam a licitação (ex.: automotivo, frota).
- A comparação ignora maiúsculas/minúsculas, acentos e hífens, casa no início da palavra e aceita
  plural simples ("climatizador" casa "climatizadores"; "split" **não** casa "splitter").
- `api.modalidades`, `api.intervalo_entre_requisicoes`, `api.tentativas`, timeouts etc.
- `esferas`: `E` estadual, `M` municipal (padrão); acrescente `F` para federais.
- `sistemas_origem`: trechos de domínio → nome do sistema (SISLOG, BLL, Licitanet, BNC...).

## Como funciona

1. **Consulta** `GET https://pncp.gov.br/api/consulta/v1/contratacoes/proposta` com
   `uf=GO`, `dataFinal` (hoje + `--dias`, formato `AAAAMMDD`), `codigoModalidadeContratacao`
   (uma chamada por modalidade), `pagina` e `tamanhoPagina=50`, percorrendo todas as páginas
   (`totalPaginas`/`paginasRestantes`). HTTP 204 = sem resultados.
2. **Escopo**: exige esfera permitida do órgão (`orgaoEntidade.esferaId`), UF de Goiás
   (`unidadeOrgao`) e `dataEncerramentoProposta` válida entre agora e agora + `--dias`.
   Com `--municipio`, exige também código IBGE correspondente. Dados ausentes nesses
   campos não comprovam elegibilidade e ficam fora do relatório.
3. **Filtro** de palavras-chave em `objetoCompra`.
4. **ME/EPP**: para cada licitação filtrada consulta
   `GET https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens`
   e lê `tipoBeneficio` de cada item (1 = exclusiva ME/EPP, 2 = subcontratação, 3 = cota
   reservada, 4 = sem benefício, 5 = não se aplica):
   - algum item sem benefício conhecido → **Não informado** (classificação conservadora)
   - todos os itens tipo 1 → **Exclusiva ME/EPP**
   - só alguns itens tipo 1 → **Parcial**
   - nenhum tipo 1 mas algum tipo 3 → **Cota reservada ME/EPP**
   - sem tipos 1/3, mas algum tipo 2 → **Subcontratação ME/EPP**
   - apenas tipos 4/5 → **Ampla participação**
   - itens indisponíveis → **Não informado**

   `--somente-me-epp` inclui exclusiva, parcial, cota e subcontratação. A tabela de
   códigos segue o [manual oficial do PNCP](https://pncp.gov.br/manual/pt-br/2.5/tabelas_de_dominio/tipo_de_beneficio.html).
   A classificação completa fica guardada no SQLite e é reutilizada quando a data de
   atualização está presente e não mudou. Cache incompleto ou de versão antiga é reconsultado.
   Todos os candidatos são registrados antes do filtro de apresentação ME/EPP.
5. **Links**: edital no PNCP `https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}` e
   `linkSistemaOrigem` informado pelo órgão.

Respeito à API: 1 requisição por segundo (configurável), timeout de 15 s para conectar e 90 s
para ler, até 5 tentativas com espera exponencial (2, 4, 8, 16 s) em erro de rede, 429 e 5xx,
considerando `Retry-After` em segundos ou data HTTP. Erros 4xx não são repetidos,
exceto respostas transitórias previstas pelo cliente (408, 425 e 429).
Em `429`, a modalidade é sempre interrompida imediatamente para não consumir mais chamadas
e o `Retry-After` informado é respeitado antes de qualquer nova coleta; não há opção para
reativar um retry automático oculto (AC17).
Páginas repetidas, formatos inválidos e limites de paginação atingidos são falhas,
com resultado explicitamente incompleto; `api.max_paginas` e `api.max_paginas_itens`
limitam a coleta (padrão: 1.000 páginas cada).
Se `Retry-After` exigir mais de 300 segundos, a consulta é interrompida com falha
registrada, sem repetir antes do prazo solicitado pelo servidor.

## Agendamento no Windows (Agendador de Tarefas)

**Pela interface**: Agendador de Tarefas → *Criar Tarefa Básica…* → nome "Licitações AC GO" →
*Diariamente*, 07:00 → *Iniciar um programa*:

- Programa/script: `C:\caminho\monitor_licitacoes_ac\executar.bat`
- Adicionar argumentos (opcional): `--dias 30`
- Iniciar em: `C:\caminho\monitor_licitacoes_ac`

Nas propriedades, marque *Executar estando o usuário conectado ou não* se quiser que rode com a
sessão bloqueada.

**Pela linha de comando** (Prompt de Comando):

```bat
schtasks /Create /TN "Licitacoes AC GO" /SC DAILY /ST 07:00 ^
  /TR "\"C:\caminho\monitor_licitacoes_ac\executar.bat\" --dias 30"
```

Para rodar duas vezes por dia, crie uma segunda tarefa (ex.: 13:00). Para testar na hora:
`schtasks /Run /TN "Licitacoes AC GO"`.

## Testes

```bat
.venv\Scripts\python -m unittest discover -s tests -t . -v
```

Os testes rodam sem internet, com respostas fictícias no formato da API (paginação, 204,
retry/backoff, filtro, classificação ME/EPP, histórico "novo", ordenação e relatórios).

## Primeira execução: conferência recomendada

Rode `executar.bat --salvar-bruto -v` e abra 3 resultados do `ultimo.html`:
compare órgão, município, objeto, valor, datas e a situação ME/EPP com a página do edital
no PNCP (aba *Itens* → coluna *Benefício*). O `bruto_*.json` mostra exatamente o que a API devolveu.

## Limitações conhecidas

- **Só o que está no PNCP.** Municípios que ainda publicam apenas em diário oficial ou portal
  próprio não aparecem. Dispensas eletrônicas nem sempre têm período de propostas no PNCP.
- **Link do sistema de origem é opcional** para o órgão: às vezes vem vazio ou aponta para a
  página inicial da plataforma, não para o processo.
- **`valorTotalEstimado` pode vir 0** quando o orçamento é sigiloso.
- **Benefício ME/EPP depende do cadastro dos itens pelo órgão**; há órgãos que marcam
  "Não se aplica" em tudo mesmo quando o edital é exclusivo. Na dúvida, confira o edital.
- **Cota reservada** normalmente aparece como item duplicado (ex.: 75% ampla + 25% cota).
- **`dataFinal`** é o único filtro de data aceito pelo endpoint `/proposta`; a janela
  `--dias` é reaplicada localmente sobre `dataEncerramentoProposta` para garantir o resultado.
- **Parâmetro de modalidade**: a versão 1.0 do Manual da API de Consultas o marca como
  obrigatório; o programa consulta uma modalidade por vez (6, 7, 8, 4, 5, 12 por padrão).
- **Instabilidade**: a API do PNCP tem quedas e lentidão frequentes; falhas ficam no log e
  o relatório avisa quando o resultado pode estar incompleto.
- Horários sem fuso são tratados como Brasília. Horários com offset são convertidos
  para UTC−03:00; a conversão é destinada às propostas atuais, não a séries históricas
  do período em que havia horário de verão.

## Continuidade local — fase 2

A [especificação técnica](docs/ESPECIFICACAO_FASE_2.md) registra escopo, riscos,
arquitetura, critérios de aceitação e implementação. O [registro de validação](docs/VALIDACAO_FASE_2.md)
lista agentes, arquivos, testes e pendências.

O ambiente existente está em `C:\dev\session\monitor_licitacoes_ac\.venv`.
Não é necessário recriá-lo:

```powershell
Set-Location C:\dev\session\monitor_licitacoes_ac
.\web.bat
# Alternativa de linha de comando, com modalidade escolhida explicitamente:
.\executar.bat --modalidades 6 --dias 30
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

O histórico anterior é preservado e atualizado de forma compatível. Alterações relevantes
de uma compra são registradas no banco. A classificação é uma indicação do cadastro dos
itens; conferir o edital continua necessário, inclusive para subcontratação, que não
significa participação exclusiva no certame.
No arquivo bruto, `origem_itens` distingue consulta, cache e indisponibilidade;
itens vindos do cache não são apresentados como uma nova resposta da API.

O HTML aceita links HTTP(S). O CSV e o XLSX neutralizam textos que poderiam ser
interpretados como fórmulas no Excel. A publicação prepara os três relatórios antes
de atualizar `ultimo.*`; a substituição de cada `ultimo.*` ainda é individual, não como
um conjunto atômico, mas se uma delas falhar (arquivo aberto no Excel, por exemplo) o
conjunto é revertido ao estado anterior — nunca fica com formatos de execuções diferentes
misturados. Nesse caso (arquivo bloqueado) a execução termina como sucesso com aviso, não
como erro; veja "Códigos de saída" acima. Outras falhas de I/O (disco cheio etc.) continuam
interrompendo a publicação com erro.
