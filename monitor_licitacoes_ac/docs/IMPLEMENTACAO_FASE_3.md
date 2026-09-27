# Fase 3 — implementação e validação

Data: 26/09/2026. Estado: integrada localmente; publicação com login Google ainda não validada.

Este relatório complementa a [especificação](ESPECIFICACAO_FASE_3.md), o [catálogo](CATALOGO_AREAS_FASE_3.md), a [UX](UX_INTERFACE_FASE_3.md) e os [critérios de aceitação](ACEITACAO_FASE_3.md). O usuário escolheu permitir **qualquer conta Google**. Essa preferência está registrada, mas a configuração do IdP e da política no Cloudflare exige uma etapa externa separada.

## O que foi implementado

- Catálogo versionado de climatização, engenharia mecânica, engenharia elétrica e serviços integrados, incluindo iluminação pública com subáreas; seleção por setor, serviço e contexto; presets profissionais; compatibilidade de buscas antigas.
- Interface em português com filtros organizados, escopo fixo de Goiás, esferas, modalidades, pesquisa no catálogo, “marcar todas” nos grupos, ajuda, buscas salvas, histórico, cartões de resultados, resumos e downloads. Abrir a página não inicia uma consulta.
- Acompanhamento progressivo por página, limite configurável de tempo e tentativas, cancelamento cooperativo, estados de execução e recuperação após recarga/reinício.
- Persistência de consultas e isolamento por proprietário. Modo local mantém identidade local; modo Cloudflare aceita somente JWT validado pelo servidor, com assinatura, emissor, audiência e validade verificados. Um cabeçalho de e-mail isolado não concede acesso.
- Validações dos filtros, respostas de erro, gravação exclusiva de busca, proteção de origem/CSRF e restrição das rotas de arquivos.
- Lançador público configurado para exigir modo protegido, domínio/audiência do Cloudflare e servidor na origem local antes de abrir o túnel.

## Delegação

As tarefas foram distribuídas por módulos para evitar consultas externas e sobreposição:

| Agente Luna | Tarefa executada |
|---|---|
| `luna_catalogo` | Catálogo, filtros por setores/serviços, compatibilidade v1 e opções da CLI |
| `luna_consultas` | Ciclo de vida da consulta, progresso por página, orçamento, prazo, cancelamento e isolamento |
| `luna_interface` | HTML, CSS, JavaScript e instruções de uso da interface |
| `luna_api` | Revisão de API PNCP, tentativas, prazos, interrupção e eventos de página |
| `luna_dominio` | Revisão da classificação ME/EPP e dos filtros/evidências do objeto |
| `luna_operacao` | Revisão de configuração, persistência, relatórios, logs e lançadores Windows |

As três últimas tarefas também concluíram correções independentes; os detalhes e arquivos constam no relatório de cada módulo abaixo. A suíte final foi executada pelo coordenador após integrar todas as alterações.

## Arquivos modificados

Arquivos novos: `catalogo_areas.yaml`; `monitor_ac/acesso.py`, `monitor_ac/catalogo.py`, `monitor_ac/consultas.py` e `monitor_ac/web.py`; `templates/index.html`, `static/app.css` e `static/app.js`; `subir_publico.bat` e `web.bat`; cinco documentos desta fase em `docs/`; e os testes `tests/test_acesso.py`, `tests/test_api_limites_fase3.py`, `tests/test_catalogo_fase3.py` e `tests/test_consultas.py`.

Arquivos atualizados: `.gitignore`, `config.yaml`, `executar.bat`, `README.md`, `requirements.txt`; `monitor_ac/api_client.py`, `monitor_ac/cli.py`, `monitor_ac/coleta.py`, `monitor_ac/config.py`, `monitor_ac/filtros.py`, `monitor_ac/mapeamento.py`, `monitor_ac/persistencia.py` e `monitor_ac/relatorio.py`; `tests/test_api_resiliencia.py`, `tests/test_dominio.py`, `tests/test_operacao.py` e `tests/test_web.py`.

## Validação realizada

Comando executado no ambiente virtual do projeto em 26/09/2026:

```powershell
C:\dev\session\monitor_licitacoes_ac\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Resultado: **102 testes aprovados**. A suíte cobre catálogo e falsos positivos, buscas v1, identidade JWT simulada, isolamento de consultas, deadline/cancelamento/orçamento, resiliência da API, persistência, relatórios e rotas web. Mensagens de erro de API nos testes são cenários simulados e suas asserções passaram.

A interface local foi aberta com configuração e banco temporários e inspecionada em desktop. Catálogo, rótulos e resumo de seleção foram conferidos; a página não disparou consulta ao PNCP durante a abertura. A inspeção não equivale a teste de uso em celular, teclado, zoom de 200% ou carga com 1.000 resultados. Nenhuma busca real no PNCP foi iniciada nesta validação.

### Validação complementar (revisão pós-implementação)

Suíte após as correções da revisão: **119 testes aprovados**; saída completa em
[`resultado_testes_fase3.txt`](resultado_testes_fase3.txt). O arquivo
`resultado_testes.txt` continua sendo a evidência da fase 2 (56 testes).

O contrato do PNCP foi conferido com chamadas reais: `tamanhoPagina` aceita de 10 a 50
(5, 51 e 100 dão HTTP 400); sem resultados a API responde 204; datas vêm sem fuso
(horário de Brasília); `tipoBeneficio` dos itens é inteiro com `tipoBeneficioNome`; o
endpoint de itens devolve lista simples e aceita `tamanhoPagina=500`. Uma execução real
pela CLI e outra pela interface (seis modalidades, 69 s, dentro do limite de 120 s)
concluíram com CSV, HTML e XLSX válidos.

Correções desta revisão: links externos só em http/https (interface e servidor); modo
`local` restrito ao loopback e recusando tráfego de túnel; `api.repetir_429` e
`filtro.campos` removidos por não terem efeito; palavra-chave da interface aceita plural;
`GET /api/status?consulta_id=&since=` incremental; catálogo local dos 246 municípios de
GO (`municipios_go.json`); histórico paginado; Content-Security-Policy; publicação com
`ultimo.*` bloqueado (Excel aberto) vira aviso; lançadores verificam dependências e a
assinatura do `cloudflared.exe`.

Revisões delegadas: API interrompe em HTTP 429 sem retry oculto e respeita `Retry-After`; classificação limita palavras-chave ao objeto e mantém dados de ME/EPP ausentes como desconhecidos; persistência e relatórios têm rollback, e os lançadores validam os pré-requisitos do modo público. Uma regressão na fixture de migração foi corrigida para fechar as próprias conexões SQLite de teste antes da verificação de arquivos no Windows.

### Verificação final de conformidade com a fase 3 (esta revisão)

Suíte após esta verificação final: **123 testes aprovados** (119 anteriores + 4 novos),
saída completa regravada em [`resultado_testes_fase3.txt`](resultado_testes_fase3.txt).
Cada requisito de `ESPECIFICACAO_FASE_3.md`, `ACEITACAO_FASE_3.md` (AC01–AC34),
`UX_INTERFACE_FASE_3.md` e `CATALOGO_AREAS_FASE_3.md` foi conferido individualmente
contra o código; os itens abaixo estavam sem teste, parciais ou ausentes e foram
corrigidos nesta revisão:

- **AC11** (múltiplas áreas não multiplicam a varredura): não havia um teste que
  comparasse o número de requisições HTTP entre uma seleção com 1 setor e outra com 16
  setores. Adicionado `test_setores_multiplos_nao_multiplicam_requisicoes_por_modalidade`
  em `tests/test_dominio.py`, confirmando que a contagem de chamadas do transporte falso
  não muda com o número de setores selecionados.
- **AC07** (perfis Mecânica/Elétrica/Ambos/Multidisciplinar): não havia verificação de
  que "Ambos" é a união exata de Mecânica+Elétrica e que "Multidisciplinar" inclui também
  os contratos integrados, nem de que a avaliação de um objeto puramente elétrico não
  exige menção a "engenheiro". Adicionado
  `test_perfis_mecanica_eletrica_ambos_e_multidisciplinar_tem_a_uniao_esperada` em
  `tests/test_catalogo_fase3.py`.
- **AC33** (CSRF/defesa de origem): a suíte só exercitava o caminho de sucesso
  (`Origin` igual ao `Host`) no modo `cloudflare`; a rejeição de uma requisição de
  alteração sem `Origin` ou com `Origin` de outro site nunca tinha sido testada.
  Adicionado `test_origem_ausente_ou_divergente_e_rejeitada_no_modo_cloudflare` em
  `tests/test_web.py`.
- **AC20** (duas gravações concorrentes nunca sobrescrevem silenciosamente): a criação
  exclusiva de arquivo (`O_CREAT|O_EXCL`) já existia, mas nenhum teste disparava
  gravações realmente concorrentes contra o mesmo nome de busca. Adicionado
  `test_gravacao_concorrente_do_mesmo_nome_tem_um_sucesso_e_um_conflito` em
  `tests/test_web.py` (8 threads, mesmo nome; exatamente um `201` e sete `409`, arquivo
  final íntegro).
- **AC25** (todo conjunto de checkboxes tem "marcar todas" com escopo claro): a
  especificação (`UX_INTERFACE_FASE_3.md`, seção 4) pede um botão geral **"Marcar todas
  as áreas"** distinto dos botões por grupo ("Marcar N opções visíveis"); esse botão
  geral não existia. Adicionado em `templates/index.html` (`#selectAllSectors`) e
  `static/app.js` (`updateSectorGroupButtons`/`handleClick`), verificado por Playwright.

Verificação em navegador (Chromium via Playwright, `python -m monitor_ac.web --port
18790` local, sem tocar a API real do PNCP; 1.000 resultados sintéticos gravados
diretamente no SQLite via `Consultas.registrar/admitir/atualizar/finalizar` para o
teste de carga):

- Viewports 360×740 e 1280×800 (pedidos pela tarefa) e também 768×1024 e 1440×900
  (larguras do próprio AC26): sem rolagem horizontal, sem erros de console e sem
  violação de Content-Security-Policy em nenhuma das quatro telas.
- Reflow equivalente a zoom 200%/400% (WCAG 1.4.10, emulado por viewports de 640 e
  320 px de largura — a técnica de `document.documentElement.style.zoom` não reflui o
  viewport do Chromium do mesmo jeito que o zoom real do navegador): sem rolagem
  horizontal e com o CTA "Consultar licitações" continuando visível/alcançável.
  Confirma AC26.
  A `<body>` já declarava `min-width: 320px` e as media queries cobrem 700/920 px.
- Navegação por Tab a partir do topo da página: o primeiro parada é o link "Pular para
  o conteúdo" e os nove focos seguintes mantêm contorno de foco visível (nenhum com
  `outline: none`). Menu do celular abre com `aria-expanded="true"` e o item ativo do
  menu principal usa `aria-current="page"`. `Escape` fecha o diálogo "Salvar busca" sem
  disparar a gravação. Confirma trechos relevantes de AC24/AC25/AC27.
- Contraste medido na página renderizada (resolvendo o fundo efetivo, já que `<body>`
  não define `background-color` própria e herda o tom claro do `<html>`): texto
  principal ≈ 13,1:1 e botão primário ≈ 7,6:1 sobre seus fundos, acima do mínimo de
  4,5:1 do critério do projeto (AC27).
- Carga de 1.000 resultados sintéticos: os 1.000 cartões renderizaram em ~2,1 s: e a
  digitação no campo de palavras-chave continuou respondendo em ~60 ms com a lista
  grande na tela, sem erro de console (AC26/UX seção "Validação da interface").
- **Bug encontrado e corrigido nesta verificação**: "Ver resultados" no histórico
  (`openHistoryItem` sem `useFilters`) renderizava os 1.000 cartões dentro da seção
  "Consultar", mas nunca trocava a página ativa para `#consultar` — a seção continuava
  com `hidden`, deixando os cartões no DOM porém invisíveis (`offsetParent` nulo) e o
  `scrollIntoView` sem efeito. Corrigido em `static/app.js` chamando `routeToHash`
  antes do scroll, confirmado por Playwright (cartão visível, nav mostrando "Consultar"
  como página ativa). Não há teste automatizado de unidade para esse comportamento de
  navegação (o projeto não tem executor de testes de JS); a evidência é a verificação
  em navegador acima, reproduzível com o mesmo roteiro.
- Requisição automática de `/favicon.ico` gerava um erro 404 no console em toda
  abertura da página; corrigido com `<link rel="icon" href="data:,">` em
  `templates/index.html`.

Pendências **externas** que continuam fora do alcance desta sessão (não dá para
corrigir localmente):

1. AC29–AC31: configurar o Google como IdP e a política "qualquer conta Google" no
   Cloudflare Access, e então validar login, negação, expiração e logout no domínio
   público real.
2. AC32 (smoke test completo dos lançadores `.bat`): esta sessão roda em Linux, sem
   `cmd.exe`/PowerShell/`schtasks`; os lançadores foram revisados estaticamente
   (ASCII/CRLF, verificação de dependências e da assinatura Authenticode do
   `cloudflared.exe`) e cobertos por `tests/test_operacao.py::TestLancadoresBat`, mas a
   execução real em duplo clique no Windows não foi (nem pode ser) refeita aqui.
3. Roteiro de usabilidade com um usuário real que não conhece o sistema
   (`UX_INTERFACE_FASE_3.md`, seção 12).
4. Publicação pública real no domínio `licitacoes-ac.98fred.dev` e verificação do
   túnel `cloudflared` em produção (`docs/CLOUDFLARE_TUNNEL.md`).

### Verificação no Windows real (26/09/2026)

Feita na máquina de produção, sobre a `main` em `0bd13c7` (suíte: 123 testes OK).

- **AC32 atendido.** `executar.bat --help` chamado de fora da pasta usa a `.venv`;
  `executar.bat --opcao-invalida` devolve código 2; `web.bat --help` funciona; o
  `cloudflared.exe` tem assinatura `Valid` da Cloudflare (2026.9.3); o duplo clique em
  `subir_publico.bat` subiu o servidor em modo `cloudflare` (`/healthz` →
  `access_mode: cloudflare`) e reaproveitou o túnel.
- **Domínio público protegido.** Sem sessão, `/` e `/api/session` redirecionam (302)
  para o login do Cloudflare Access.
- **AC31 bloqueado no Cloudflare, não no app.** O teste do provedor Google no painel
  passa, mas o login pela aplicação `licitacoes-ac` termina em "Failed to fetch
  user/group information from the identity provider", antes de chegar à origem (a
  tentativa nem aparece no log de autenticação). Logins funcionavam às 14h19 e 14h37
  com o provedor Google anterior; a falha começou após a troca de provedor (15h35–15h46).
  Política (`Allow` → Everyone), app e cliente OAuth (Web, modo "Testando" com o e-mail
  do dono como usuário de teste) conferidos. Um provedor One-time PIN foi adicionado à
  conta, mas não está habilitado na aplicação.
- **Roteiro de usabilidade (UX seção 12) executado em modo local**: localizar iluminação
  pública → manutenção → Goiás municipal → pregão eletrônico → consultar (40 s,
  11 chamadas, 2 resultados) → abrir resumo → baixar Excel → salvar busca → Ajuda →
  carregar busca. Concluído sem chamadas acidentais; consultar sem modalidade mostra
  erro claro e não chama o PNCP. Sem rolagem horizontal a 360 px.

Problemas encontrados no roteiro, a corrigir:

1. **CTA longe no celular (AC24/AC26).** A 360 px o botão "Consultar licitações" fica
   a ~5.500 px do topo (página de ~7.000 px) e não é fixo; exige rolar cerca de 7 telas.
2. **Região `aria-live` grande demais (AC27).** O bloco inteiro de setores/subáreas está
   dentro de uma região viva; um leitor de tela anunciaria a lista toda a cada mudança.
3. **Rótulos de progresso incoerentes.** Durante a coleta, "Etapa" mostra `6` (código da
   modalidade); o botão fica em "Iniciando consulta..." por toda a execução; ao terminar,
   o título segue "Consulta em andamento" ao lado do selo "Concluída".
4. **Resumo com dados crus (AC28).** "Valor estimado" aparece como `2582659.7` e as datas
   como `2026-09-14T08:00:00`, enquanto o cartão já mostra `R$ 2.582.659,70` e `28/09/2026`.
5. **Subáreas espremidas.** O painel "Detalhar Iluminação pública" ocupa só a largura de
   um cartão, deixando o resto da linha vazio e alongando a lista.
6. **Confirmação fora de vista.** "Busca salva" aparece no topo da página, longe do botão
   usado no fim da tela, e continua visível ao trocar de seção.
7. **Possível falso positivo (AC05).** Com Iluminação pública + manutenção, entrou a
   manutenção de veículos e máquinas da frota de Caturaí, que só cita "Iluminação
   Pública" como secretaria atendida.
   **Corrigido** na branch `fix/falso-positivo-frota`: exclusão contextual `frota_veicular`
   no setor de iluminação pública (ver [catálogo, seção 3](CATALOGO_AREAS_FASE_3.md)).

## Pendências antes de oferecer acesso público

1. Configurar Google como IdP e aplicar no Cloudflare a política para qualquer conta Google, conforme a decisão do usuário.
2. Informar `CF_ACCESS_TEAM_DOMAIN` e `CF_ACCESS_AUD` (ou os valores equivalentes no `config.yaml`) e confirmar que o serviço de origem inicia em modo `cloudflare`.
3. Validar no domínio login permitido, bloqueio de sessão ausente/expirada, saída e isolamento com mais de uma conta. Só então anunciar autenticação pública ativa.
4. Completar revisão manual de acessibilidade e responsividade nas larguras e níveis de zoom dos critérios AC25–27.
5. Fazer smoke test dos lançadores Windows sem iniciar uma varredura PNCP. O ambiente de testes passou pela venv; a execução do túnel e a configuração externa não foram testadas. O `cloudflared.exe` local informa versão 2026.9.3; a opção de token por arquivo requer 2025.4.0 ou posterior, segundo os [parâmetros oficiais do túnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/).

Referências oficiais para a etapa Cloudflare: [configuração do Google como provedor de identidade](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/google/), [validação de JWT do Access](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/) e [parâmetros do cloudflared](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/).
