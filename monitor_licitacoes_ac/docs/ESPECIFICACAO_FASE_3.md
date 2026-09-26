# Fase 3 — monitor de oportunidades em engenharia e nova experiência web

Data: 26/09/2026. Versão: 1.1. Estado: requisitos implementados localmente; liberação pública pendente de configuração e validação do acesso Google.

Este pacote reúne as sugestões de engenharia mecânica, elétrica, atuação conjunta e iluminação pública, além das cinco diretrizes de layout solicitadas pelo usuário. Após a especificação, o usuário autorizou a implementação local e a delegação a agentes. O estado, evidências, arquivos e pendências estão em [relatório de implementação](IMPLEMENTACAO_FASE_3.md). Nenhuma consulta real ao PNCP foi iniciada durante a validação desta fase.

## 1. Documentos e leitura

1. Este documento: objetivo, diagnóstico, escopo, arquitetura e etapas.
2. [Catálogo de áreas e regras de busca](CATALOGO_AREAS_FASE_3.md): setores, serviços, palavras-chave e compatibilidade.
3. [Interface e experiência de uso](UX_INTERFACE_FASE_3.md): telas, navegação, hierarquia, espaçamento e mensagens.
4. [Aceitação e validação](ACEITACAO_FASE_3.md): critérios verificáveis, cenários, testes e liberação.
5. [Implementação e validação](IMPLEMENTACAO_FASE_3.md): entregas, agentes, evidências locais e pendências externas.

Este documento permanece como referência dos requisitos e critérios da fase; o relatório vinculado separa o que foi implementado e testado do que depende de validação manual ou configuração externa. A fase 2 continua sendo a referência histórica; esta fase amplia seu escopo para a web e novas especialidades.

## 2. Objetivo e escopo

Transformar o monitor existente em uma ferramenta de triagem de licitações de engenharia em Goiás, mantendo a busca de climatização e acrescentando oportunidades relacionadas aos profissionais mecânico e eletricista da empresa. A pessoa deverá entender o que está consultando, acompanhar a coleta, ler resumos e guardar filtros e resultados sem depender de navegar por vários portais.

O nome de apresentação proposto é **Monitor de licitações de engenharia — Goiás**. Manter o pacote `monitor_ac`, o diretório local, o domínio e os lançadores atuais para evitar uma migração operacional desnecessária.

Inclui:

- Catálogo técnico configurável com iluminação pública como área explícita.
- Separação de setor técnico, tipo de serviço, contexto do empreendimento e perfil profissional.
- Redesenho responsivo, menu por tarefas, ajuda em português e filtros avançados recolhidos.
- Consulta controlada, resultados progressivos, interrupção, contagem de chamadas e indicação de resultados incompletos.
- Buscas salvas com validação clara, versões de formato e preservação dos arquivos existentes.
- Resumos explicáveis, HTML/CSV/XLSX, histórico de consultas e recuperação após atualizar a página.
- Preparação do fluxo de conta para a autenticação externa já discutida; ativação condicionada à configuração real do provedor e da política de acesso.
- Compatibilidade com CLI, SQLite, cache ME/EPP e execução Windows existentes.

Fora do escopo da fase: outras UFs, aquisição de dados fora do PNCP, interpretação automática de PDFs, resumo por IA, participação automática em certames, comprovação automática de habilitação profissional, pagamentos e migração para uma plataforma de hospedagem diferente.

## 3. Base existente examinada

Diretório: `C:\dev\session\monitor_licitacoes_ac`. Fontes examinadas: README, YAML, especificação/validação anteriores, documentação do túnel, módulos de coleta, filtros, configuração, cliente, persistência e web, além da suíte atual.

| Recurso | Situação encontrada no código/documentação |
|---|---|
| PNCP | Paginação, intervalo, retries, tratamento de 429, limites de páginas e validação de respostas |
| Escopo | GO, município por IBGE, esferas, modalidades e janela de encerramento |
| Relevância | Filtro obrigatório de climatização, palavras do objeto e seis áreas simples |
| ME/EPP | Classificação conservadora por itens, cache e registro de alterações |
| Web | Servidor Python local, consulta em thread, polling, cartões e resumos |
| Menu | Âncoras para consulta, buscas salvas, resultados, relatórios e ajuda na mesma página longa |
| Salvamento | Filtros em JSON, recusa de nome vazio e conflito de nome/arquivo |
| Relatórios | HTML, CSV e XLSX; arquivos datados e aliases `ultimo.*` |
| Histórico | SQLite com licitações, mudanças e estrutura de execuções; CLI registra execuções |
| Acesso | Túnel documentado; tela exibe e-mail recebido no cabeçalho do Access e link de saída |
| Windows | `.venv`, `executar.bat`, `web.bat` e `subir_publico.bat` existentes |
| Testes | Baseline informado antes desta fase: 61 aprovados; validação após implementação: 102 aprovados |

Os documentos da fase 2 registram contagens e exemplos de CLI históricos. Use o relatório de implementação e o resultado mais recente da suíte para o estado atual; não trate números antigos como validação desta fase.

Não há evidência de que o provedor Google ou a política de acesso do Cloudflare estejam configurados. O usuário definiu que o app público deve aceitar qualquer conta Google. A preferência foi implementada no fluxo de preparação, mas a autenticação só pode ser anunciada como ativa após configurar o provedor, aplicar a política e fazer o smoke test no domínio.

## 4. Diagnóstico do baseline, riscos e melhorias necessárias

A tabela registra os problemas encontrados antes da implementação desta fase. Consulte o relatório de implementação para saber quais foram tratados e quais permanecem pendentes.

| ID | Constatação | Consequência | Requisito futuro |
|---|---|---|---|
| P01 | `coleta.py` aplica `FiltroPalavras(config['filtro'])` antes das áreas | Iluminação pública, SPDA e subestações seriam descartados sem termo de climatização | Selecionar regras por setor, sem uma condição global obrigatória de ar-condicionado |
| P02 | IDs de áreas são comparados literalmente com o objeto | `fornecimento` perde textos de aquisição; `pecas` e outros IDs não representam conjuntos de sinônimos | Resolver IDs em regras e evidências do catálogo |
| P03 | Tela combina filtros, salvamento, andamento, resultados e ajuda extensa | A ação principal concorre com muitas informações | Navegação por tarefas, filtros essenciais primeiro e detalhes sob demanda |
| P04 | Coleta agrega todas as páginas antes de classificar candidatos | Resultados demoram a aparecer; o usuário não vê candidatos durante a primeira etapa | Emitir progresso por página e candidatos parciais com atualização por identidade |
| P05 | Estado da consulta é global e reside em memória | Atualização/reinício perde contexto; diferentes visitantes compartilham resultados e filtros salvos | Identificar execuções, persistir metadados e definir propriedade por usuário antes do uso autenticado por terceiros |
| P06 | Não existe cancelamento pela interface nem prazo global de coleta | Usuário não controla uma consulta demorada | Cancelamento cooperativo, orçamento de chamadas e prazo de coleta visíveis |
| P07 | `_worker` pode anunciar conclusão mesmo com falhas e não usa o registro de execuções da CLI | Resultado incompleto pode parecer completo; histórico web fica insuficiente | Estados explícitos, registro da execução web e preservação da última consulta completa |
| P08 | `render` retorna sem limpar quando recebe lista vazia; carregamento inicial não retoma status | Risco de cartões antigos ou consulta em curso invisível após recarregar | Estado de apresentação derivado da execução, inclusive vazio, reconexão e retomada |
| P09 | Verificação de nome existente ocorre antes de substituição de arquivo | Salvamentos concorrentes podem disputar o mesmo nome | Criação exclusiva/trava e conflito retornado de forma atômica |
| P10 | Publicação troca cada `ultimo.*` separadamente | Interrupção pode misturar formatos de execuções diferentes | Manifesto por execução; atualizar ponteiro da última consulta completa após publicar todo o conjunto |
| P11 | Login externo não foi verificado, e cabeçalho é apenas exibido | Não há garantia documentada de autenticação nem isolamento | Validar identidade no modo público protegido e autorização em API, buscas e arquivos |
| P12 | Termos amplos como LED, rede, painel, bomba e manutenção são ambíguos | Muitos resultados sem relação com a empresa | Regras de contexto, sinônimos controlados e corpus de exemplos positivos/negativos |

## 5. Regras principais do produto

### Busca e classificação

- Goiás é o escopo explícito e fixo nesta fase. Esfera federal significa órgãos com unidade em GO, não uma pesquisa nacional.
- Os grupos de seleção têm controles locais de marcar/desmarcar todas e estado parcial. Nenhuma seleção inicia coleta.
- O modo inicial mantém climatização/refrigeração/PMOC e esferas estadual e municipal. Áreas elétricas são adicionadas por escolha explícita, inclusive pelo preset de iluminação pública.
- Perfil profissional ajuda a montar a seleção; não exige que o edital mencione “engenheiro” nem prova habilitação da empresa.
- A consulta percorre as modalidades escolhidas uma única vez. Selecionar dez áreas não cria dez varreduras iguais da API.
- Título/objeto refere-se ao campo `objetoCompra` disponível atualmente. Resumo e termos encontrados mostram de onde veio a classificação; não presumir conteúdo de anexos não lidos.

### Tempo, chamadas e estado

- Abrir, navegar, carregar/salvar busca e baixar um relatório existente não chama o PNCP.
- Proposta de limites iniciais da web: **120 s de coleta** e **60 tentativas HTTP** por execução, configuráveis no servidor. Cada tentativa de retry conta; cache e polling local não contam. São limites operacionais do produto, não uma declaração sobre a cota do PNCP.
- Manter intervalo padrão de 2 s na web, nunca inferior ao mínimo configurado. Opções técnicas ficam em “Avançado”. Não prometer conclusão em dois minutos.
- O prazo de coleta inclui esperas, backoff, páginas e itens. Conferir relógio monotônico e cancelamento antes de cada chamada/espera; limitar timeouts ao tempo restante. Esperas longas devem ser interrompíveis.
- Cancelamento/prazo vencido impede novas chamadas; uma chamada já em curso pode terminar depois. A tela deve dizer “Finalizando a requisição em andamento”. Persistir/exportar os resultados já obtidos, marcando a cobertura parcial. Tempo de finalização de arquivos é separado do tempo de coleta.
- Em 429, a proposta é interromper novas chamadas da execução, informar o limite e respeitar `Retry-After` antes de permitir nova coleta. Não criar retomada automática oculta.
- Sem total confiável, mostrar atividade, etapa e contagens, sem percentuais artificiais ou prazo restante inventado.
- Uma execução PNCP ativa por servidor na primeira entrega; disputa retorna 409 e não cria uma segunda thread. No modo privado, a mensagem de ocupação não revela dados de outro usuário.

### Dados, conta e histórico

- A consulta deve ter ID estável, filtros usados, versão do catálogo, início/fim, estado, contagens, falhas e arquivos próprios.
- Expor candidatos cedo; substituir o cartão da mesma identidade quando vier uma versão mais recente. Identificar candidatos ainda sem itens como “Benefício em análise”, sem inferir ME/EPP.
- Persistir resultados e cursor/versão de apresentação suficientes para recarregar a tela. Se o servidor reiniciar durante uma consulta, marcar interrupção; não retomar chamadas externas automaticamente.
- `ultimo.*` deve continuar apontando para a última execução completa, inclusive uma completa sem resultados. Consultas parciais ficam acessíveis pelo seu ID.
- No modo local sem autenticação, dados pertencem ao espaço local. Em modo público protegido, buscas, consultas e arquivos pertencem à identidade validada. Os arquivos antigos ficam no espaço legado até associação explícita ao proprietário; não atribuir tudo ao primeiro visitante.
- A ativação pública exige verificação real do IdP Google no Cloudflare, sessão, logout, validação de identidade e bloqueio de acesso indevido. A política solicitada permite qualquer conta Google; sua aplicação e validação no Cloudflare continuam pendentes.
- Não armazenar senha Google; não registrar tokens/cookies em logs. Não usar apenas um cabeçalho arbitrário para conceder acesso. Prever validação do JWT do Access (assinatura, emissor, audiência e validade) e isolamento da origem em loopback.

## 6. Arquitetura de referência

Continuar com Python, configuração YAML, SQLite e a API web existente. Separar HTML/CSS/JS hoje embutidos em `web.py`; não introduzir um framework de frontend ou novo serviço apenas para organizar a tela. A implementação foi integrada nos módulos existentes: consulte o relatório para a estrutura real; o diagrama abaixo é a arquitetura de referência que orientou o trabalho.

Compatibilidade de configuração: resolver o caminho de `catalogo_areas.yaml` em relação ao `config.yaml`, assim como os caminhos locais existentes. Preservar termos personalizados do filtro antigo em um perfil de compatibilidade de climatização, sem aplicá-los como barreira global às novas áreas. Ausência do catálogo numa configuração legada mantém o funcionamento anterior; catálogo explicitamente informado e inválido gera erro de configuração, sem fallback silencioso.

Na CLI, propor `--setores`, `--servicos` e `--contextos` como listas de IDs separados por vírgula, com validação pelo mesmo catálogo da web. Sem esses argumentos, manter o escopo legado. Continuar exigindo modalidade explícita (`--modalidades` ou `--todas-modalidades`); a inclusão de novas áreas não autoriza varredura automática de todas as modalidades.

```text
monitor_licitacoes_ac/
  config.yaml                    # limites operacionais e referência ao catálogo
  catalogo_areas.yaml             # novo: setores, serviços, sinônimos e presets
  monitor_ac/
    api_client.py                # transporte, limites, espera cancelável e progresso
    coleta.py                    # escopo, classificação progressiva e deduplicação
    filtros.py                   # mecanismos de correspondência e ME/EPP
    catalogo.py                  # novo: validação e resolução das regras técnicas
    consultas.py                 # novo: ciclo de vida e propriedade das execuções
    buscas.py                    # novo: arquivos de filtros, migração e conflitos
    autenticacao.py              # novo: modo local e identidade verificada do Access
    persistencia.py              # migrações compatíveis e histórico de execuções web
    relatorio.py                 # formatos e manifesto por consulta
    web.py                       # roteamento HTTP e validação das requisições
    templates/index.html         # novo: estrutura da interface
    static/app.css               # novo: estilos e componentes responsivos
    static/app.js                # novo: filtros, navegação e estados
    cli.py                       # mesmas regras de catálogo, parâmetros explícitos
  tests/                         # regressões existentes + casos novos por módulo
  docs/                          # estas especificações e futura evidência de validação
  executar.bat / web.bat / subir_publico.bat
```

Contratos propostos:

| Endpoint | Contrato futuro |
|---|---|
| `GET /api/options` | Manter opções existentes e acrescentar catálogo versionado, presets e limites públicos |
| `GET /api/session` | Modo de acesso, identidade autorizada e capacidades; sem tokens |
| `POST /api/start` | Validar filtros, criar execução e retornar 202 com `consulta_id`; preservar compatibilidade dos payloads atuais |
| `GET /api/status?consulta_id=...&since=...` | Estado, contagens e atualizações com revisão monotônica; sem ID, última consulta acessível |
| `POST /api/consultas/{id}/cancelar` | Solicitar cancelamento idempotente da execução autorizada |
| `GET /api/consultas` | Histórico paginado somente das execuções acessíveis |
| `GET /api/consultas/{id}` | Metadados, resultados paginados e manifesto de arquivos |
| `/api/searches` e `/api/searches/{id}` | Manter funções atuais, acrescentar versão e isolamento de proprietário |
| `/files/...` | Resolver apenas arquivos permitidos; verificar propriedade no modo autenticado |

`since` representa a revisão da apresentação, não apenas a quantidade de registros: uma compra já exibida pode ser atualizada. Respostas com revisão expirada instruem recarga integral. Validar IDs, tipos, tamanho do corpo e caminhos; retornar 400 para JSON inválido, 422 para filtros inválidos, 409 para disputa, 404 para recurso inexistente/inacessível e 401 para sessão ausente no modo protegido.

A separação de arquivos não pode permitir servir token do túnel, configuração, SQLite, logs ou arquivos arbitrários. Rotas estáticas usam uma raiz restrita e lista de extensões. Requisições de alteração no modo público usam defesa contra CSRF e validação de origem. HTML personalizado e respostas de conta não podem ser armazenados em cache compartilhado.

Persistência: acrescentar campos/tabelas versionadas para proprietário, filtros, versão do catálogo, snapshot de resultados, status e manifesto, sem apagar `licitacoes`, `mudancas_relevantes` ou `execucoes`. Cada thread abre sua própria conexão SQLite. Cache técnico de itens pode ser compartilhado internamente; a listagem de consultas e arquivos não é compartilhada por isso.

## 7. Etapas de implementação executadas

| Etapa | Entrega | Resultado |
|---|---|---|
| 1 | Catálogo, regras por área, iluminação pública e compatibilidade de filtros | Implementada; coberta por testes de catálogo/domínio |
| 2 | Consultas identificadas, progresso, limites, cancelamento e isolamento por identidade | Implementada no backend; testes offline aprovados |
| 3 | Interface por tarefas, catálogo, filtros, resultados progressivos e ajuda | Implementada; revisão visual local realizada |
| 4 | Acesso local e validação do JWT do Cloudflare Access | Implementada e coberta por testes; configuração externa pendente |
| 5 | Documentação, lançadores Windows e regressão da suíte | Documentação atualizada; 102 testes aprovados. Smoke test dos lançadores ainda pendente. |

As tarefas foram executadas por agentes Luna e integradas no projeto local. A disponibilização pública para qualquer conta Google ainda requer configurar o IdP e a política de acesso no Cloudflare e executar validação no domínio.

## 8. Decisões e pendências para a implementação

- Padrões propostos nesta especificação: GO fixo, climatização como seleção inicial, palavras-chave com correspondência de qualquer termo, perfis como presets e iluminação pública explicitamente selecionável.
- Revisar o catálogo com exemplos de editais da empresa; categorias representam interesses de busca, não certificação das atribuições dos engenheiros.
- Preferência de acesso público definida pelo usuário: qualquer conta Google. Falta configurar e testar essa política no Cloudflare.
- Medição de visitantes e distinção entre proprietário/outros pode ser uma fase posterior com identidade validada; métricas agregadas antigas não permitem essa separação retroativa com certeza.
- A configuração externa deve seguir a documentação oficial atual do Cloudflare. A implementação local não acessa nem guarda credenciais Google.
