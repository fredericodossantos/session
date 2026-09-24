# Monitor de licitações de ar-condicionado — Goiás

Busca no **PNCP** (Portal Nacional de Contratações Públicas) as contratações com
recebimento de propostas **em aberto** do Estado de Goiás e dos municípios goianos,
filtra as de ar-condicionado (manutenção, instalação, fornecimento, PMOC),
identifica as **exclusivas para ME/EPP** e gera um **CSV** e um **HTML** legível no celular.

## Instalação (Windows)

1. Instale o Python 3.11 ou mais novo (python.org). Na instalação, marque *Add python.exe to PATH*.
2. Abra o **Prompt de Comando** na pasta `monitor_licitacoes_ac` e rode:

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

No Linux/macOS: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

## Uso

```bat
executar.bat                                 :: prazo de propostas nos próximos 30 dias
executar.bat --dias 15                       :: janela de 15 dias
executar.bat --municipio 5208707             :: só Goiânia (código IBGE)
executar.bat --somente-me-epp                :: só com benefício ME/EPP
executar.bat --incluir-federal               :: inclui órgãos federais sediados em GO
executar.bat --modalidades 6,8               :: só pregão eletrônico e dispensa
executar.bat --salvar-bruto -v               :: salva as respostas da API p/ conferência
```

(Equivale a `.venv\Scripts\python -m monitor_ac ...`.)

Ao final o programa mostra no console quantas licitações a API retornou, quantas passaram
no filtro e quantas têm benefício ME/EPP, e onde estão os arquivos.

Códigos de saída: `0` ok · `1` concluiu com alguma falha de requisição (resultado pode estar
incompleto; ver log) · `2` nenhuma consulta funcionou ou erro inesperado (relatório anterior mantido).

### Arquivos gerados (pasta `saida/`)

| Arquivo | Conteúdo |
|---|---|
| `ultimo.html` | Relatório da execução mais recente (abra no celular/navegador) |
| `ultimo.csv` | Mesmos dados em CSV (`;`, UTF-8 com BOM, abre direto no Excel) |
| `licitacoes_ac_go_AAAAMMDD_HHMM.*` | Cópia datada de cada execução |
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
2. **Escopo**: esfera do órgão (`orgaoEntidade.esferaId`), UF/município (`unidadeOrgao`) e
   `dataEncerramentoProposta` entre agora e agora + `--dias`.
3. **Filtro** de palavras-chave em `objetoCompra`.
4. **ME/EPP**: para cada licitação filtrada consulta
   `GET https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens`
   e lê `tipoBeneficio` de cada item (1 = exclusiva ME/EPP, 2 = subcontratação, 3 = cota
   reservada, 4 = sem benefício, 5 = não se aplica):
   - todos os itens tipo 1 → **Exclusiva ME/EPP**
   - só alguns itens tipo 1 → **Parcial**
   - nenhum tipo 1 mas algum tipo 3 → **Cota reservada ME/EPP**
   - nenhum dos dois → **Ampla participação**
   - itens indisponíveis → **Não informado**

   A classificação fica guardada no SQLite e só é consultada de novo se `dataAtualizacao` mudar.
5. **Links**: edital no PNCP `https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}` e
   `linkSistemaOrigem` informado pelo órgão.

Respeito à API: 1 requisição por segundo (configurável), timeout de 15 s para conectar e 90 s
para ler, até 5 tentativas com espera exponencial (2, 4, 8, 16 s) em erro de rede, 429 e 5xx,
honrando `Retry-After`. Erros 4xx não são repetidos.

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
- Horários da API vêm sem fuso (horário de Brasília) e são exibidos como estão.
