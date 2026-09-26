# Fase 3 — critérios de aceitação e estratégia de validação

Data: 26/09/2026. Versão: 1.1. Critérios da implementação local; consulte o [relatório de implementação](IMPLEMENTACAO_FASE_3.md) para evidências e pendências.

Validação automatizada final: `C:\dev\session\monitor_licitacoes_ac\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v` — **102 testes aprovados** em 26/09/2026; após a revisão pós-implementação, **119 testes aprovados** (saída em [`resultado_testes_fase3.txt`](resultado_testes_fase3.txt)). Os critérios que dependem de provedor externo, implantação pública, vários tamanhos de tela ou inspeção manual continuam identificados no relatório como pendentes de validação.

Referências: [especificação principal](ESPECIFICACAO_FASE_3.md), [catálogo](CATALOGO_AREAS_FASE_3.md) e [interface](UX_INTERFACE_FASE_3.md).

## 1. Critérios de aceitação

| ID | Critério verificável | Evidência exigida |
|---|---|---|
| AC01 | Climatização continua selecionável e permanece o escopo inicial; outras áreas só entram quando escolhidas | Regressões do escopo antigo e teste dos defaults |
| AC02 | Iluminação pública é uma opção visível em Engenharia elétrica, com as oito subáreas especificadas | Catálogo validado e demonstração na interface |
| AC03 | Editais elétricos selecionados entram sem menção a ar-condicionado, e texto elétrico não entra numa seleção exclusiva de climatização | Testes de coleta com transporte falso e exemplos positivos/negativos |
| AC04 | Cada setor, serviço e subárea usa regras/sinônimos e não apenas seu ID | Corpus com aquisição/fornecimento, VRF/HVAC, PMOC, SPDA e telegestão |
| AC05 | LED de eventos, splitter HDMI, poste de cerca, gerador de relatórios e bomba de poço não entram nos setores indevidos | Casos negativos automatizados |
| AC06 | OU dentro dos grupos e E entre grupos funciona; subárea restringe apenas seu próprio setor | Testes com seleção de vários setores e serviços |
| AC07 | Perfis Mecânica, Elétrica, Ambos e Multidisciplinar preenchem seleção explícita, sem exigir a profissão no objeto | Testes de preset e revisão de rótulos |
| AC08 | GO, município, prazo e esferas são validados; dados insuficientes não comprovam elegibilidade | Testes atuais preservados e validação de entrada |
| AC09 | ME/EPP mantém classificação conservadora, cache e distinção entre desconhecido e ampla participação | Suíte existente e casos novos no fluxo progressivo |
| AC10 | Abrir app, usar menu, aplicar preset, salvar/carregar filtros, ler histórico e baixar arquivo existente faz zero chamadas PNCP | Contador do cliente falso nos testes de interface/integração |
| AC11 | Múltiplas áreas não multiplicam a varredura: mesma modalidade/página é coletada uma vez por execução, salvo retries previstos | Registro de chamadas do transporte falso |
| AC12 | Início devolve ID; cliques duplos/concorrentes não criam duas consultas; recarregar retoma a mesma execução | Testes HTTP, concorrência e fluxo no navegador |
| AC13 | Progresso aparece por página e candidatos são exibidos antes de toda a coleta terminar | Transporte controlado por eventos, com segunda página bloqueada até verificar primeiro resultado |
| AC14 | Uma compra presente em mais de uma página/modalidade tem um cartão; uma versão mais nova atualiza esse cartão e invalida benefício obsoleto quando necessário | Teste de deduplicação, atualização e revisão incremental |
| AC15 | Durante itens pendentes, interface mostra “Benefício em análise”; com filtro ME/EPP, não apresenta desconhecido como elegível | Testes de estados intermediários e final |
| AC16 | Limites de tempo/tentativas e cancelamento impedem chamadas subsequentes e preservam resultados parciais | Relógio falso, controle de espera, cancelamento e contagem exata de tentativas |
| AC17 | 429 interrompe novas chamadas da execução e não dispara retry oculto; ausência de resultados e falha são estados distintos | Teste 429 com/sem Retry-After e revisão de mensagens |
| AC18 | Falha total, parcial, cancelamento e término por limite têm status próprios, registrados e exportados | Teste integrado HTTP → coleta → SQLite → relatórios |
| AC19 | A lista vazia limpa cartões da execução anterior; falha de conexão mantém apenas dados identificados da consulta atual | Teste de sequência entre duas execuções e reconexão |
| AC20 | Campo de busca vazia, nome duplicado e erro de gravação dão feedback claro; duas gravações concorrentes nunca sobrescrevem silenciosamente | Testes HTTP de 400/422/409 e erro operacional, mais inspeção do foco na UI |
| AC21 | Buscas v1 continuam abrindo, com semântica OU preservada nas áreas mistas; IDs incompatíveis geram aviso, não ampliação silenciosa | Fixtures v1, arquivo original intacto e round-trip v2 |
| AC22 | Relatórios HTML, CSV e XLSX pertencem ao mesmo ID; última completa não é substituída por parcial/falha | Teste com falha injetada em cada estágio de publicação |
| AC23 | Histórico/arquivos são recuperáveis após reiniciar; execução interrompida não reinicia o PNCP sozinha | Reabrir persistência e testar inicialização |
| AC24 | “Consultar licitações” é o CTA dominante; navegação e opções avançadas reduzem a tela inicial | Revisão visual e roteiro de usabilidade da especificação UX |
| AC25 | Todos os conjuntos de checkboxes oferecem seleção em lote com escopo claro e estado parcial | Teclado e interação com pesquisa interna e subgrupos |
| AC26 | Menu, busca, resumo, salvamento e downloads funcionam a 360/768/1440 px e com zoom 200% | Capturas e lista curta de resultados da revisão visual |
| AC27 | Rótulos, foco, erros e anúncios de progresso são acessíveis; contraste e alvos atendem aos critérios do projeto | Inspeção semântica, teclado e medição de contraste |
| AC28 | Resumos exibem evidências reais do objeto e ausência de dados, sem inventar leitura de PDF ou habilitação da empresa | Testes de campos ausentes e revisão de conteúdo |
| AC29 | Modo público protegido só considera identidade validada; sem sessão não há acesso a API, buscas nem downloads | Testes de autenticação e autorização negativos e positivos |
| AC30 | Duas contas não podem listar/ler/alterar consultas, filtros e arquivos uma da outra, inclusive por ID/URL direto | Matriz de autorização em todas as rotas |
| AC31 | Login Google, acesso negado, expiração e logout foram verificados antes de anunciar autenticação ativa | Smoke test do provedor realmente configurado, após decisão sobre acesso |
| AC32 | Execução Windows continua usando a venv existente, funciona fora da pasta e propaga erros da CLI | Smoke tests dos lançadores sem coleta externa automática |
| AC33 | Nenhum segredo, banco ou arquivo arbitrário é servido; entradas e conteúdo externo são tratados com segurança | Path traversal, XSS, fórmulas em planilha, limite de corpo e CSRF |
| AC34 | Ajuda e README explicam perfis, setores, iluminação pública, salvamento, formatos e limite de coleta | Revisão dos exemplos contra comportamento implementado |

AC29–31 são obrigatórios para liberação pública com contas. A revisão local do layout e do catálogo pode ocorrer antes, identificada como modo local. Exibir um e-mail no cabeçalho ou passar um teste com header falso não comprova login.

## 2. Estratégia de testes

### Base de regressão

Preservar os testes existentes em `test_monitor.py`, `test_api_resiliencia.py`, `test_dominio.py`, `test_operacao.py`, `test_integracao_fase2.py` e `test_web.py`. A última execução registrada na conversa foi de 61 testes aprovados; não foi repetida durante a elaboração destas specs.

Antes de implementar, executar a suíte para obter uma nova base datada. No final, rodar toda a suíte, não apenas os arquivos alterados:

```powershell
Set-Location C:\dev\session\monitor_licitacoes_ac
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Não validar comportamento de produção apenas por contagem de testes. Registrar comando, data, quantidade, resultado e evidências específicas dos requisitos. Mensagens de falhas simuladas não são falhas da suíte se as asserções correspondentes passarem.

### Testes de unidade propostos

- `test_catalogo.py`: esquema, IDs únicos, referências válidas, catálogo completo, sinônimos e regras de contexto.
- `test_filtros_setores.py`: combinação de grupos, negativos ambíguos, exclusões por setor e evidências com texto original escapado.
- `test_buscas.py`: migração v1/v2, semântica das áreas mistas, validação, conflito de slug, falha de disco e concorrência.
- `test_consultas.py`: estados, ID, relógio, tentativas, deadline, cancelamento, revisões de resultado e retomada de estado.
- `test_autenticacao.py`: modo local, JWT válido/expirado/inválido, emissor/audiência incorretos, indisponibilidade de chaves sem liberação indevida e propriedade.

Relógio e espera devem ser injetáveis; testar timeout/backoff/cancelamento sem esperar dois minutos reais. Dados fictícios devem incluir uma compra antiga e uma versão mais recente para verificar que o progresso não conserva conteúdo ultrapassado.

### Testes integrados offline

Usar servidor HTTP em porta efêmera, transporte PNCP falso, SQLite e diretórios temporários. Exercitar os componentes reais da coleta, persistência, relatórios e roteamento.

Fluxos mínimos:

1. Climatização legada → execução completa → três formatos → registro de histórico.
2. Iluminação pública sem climatização → resultado correto → filtros salvos e restaurados.
3. Mecânica + elétrica com duplicata → um cartão por identidade → evidências múltiplas.
4. Página lenta → candidato exibido antes da conclusão → benefício atualizado posteriormente.
5. Resultado completo vazio após execução com itens → tela/relatórios vazios legítimos, sem resíduo.
6. 429, 5xx, JSON inválido ou itens indisponíveis → status parcial/falha coerente, sem falso sucesso.
7. Cancelamento em coleta e em backoff → nenhuma chamada subsequente → arquivos parciais válidos.
8. Estouro de orçamento de tempo/tentativas → interrupção identificada → última completa preservada.
9. Reinício do processo → histórico recuperado → execução pendente marcada interrompida, sem nova coleta.
10. Salvamentos simultâneos de mesmo nome → um sucesso e um conflito, sem perda do arquivo vencedor.
11. Duas contas → leitura/escrita/download autorizados apenas para o respectivo proprietário.
12. Falha ao gerar o segundo/terceiro formato → manifesto completo anterior continua utilizável.

Testar também compatibilidade dos payloads HTTP atuais, CLI sem `--modalidades`, dados sem UF/prazo, subcontratação ME/EPP e links HTTP(S). Evitar mudar uma expectativa antiga apenas para acomodar regressão involuntária.

### Validação da interface

Usar fixtures e servidor de teste para não gastar a API na revisão de layout. Navegar, aplicar presets, usar “Marcar todas”, abrir detalhes, salvar filtros e simular vazio/erro/sucesso/cancelamento/reconexão. Avaliar via teclado e em celular/desktop.

Verificar que formulários não utilizam alertas genéricos como único feedback; ações preservam o preenchimento após falha. Mudanças no catálogo e navegação não perdem seleções ativas. O resumo aberto não se fecha a cada atualização do progresso.

Meta operacional local proposta: retorno de início/status em até 1 s no ambiente de teste sem carga concorrente; progresso visível em até 2 ciclos de polling após um evento interno. Não aplicar essa meta ao tempo de resposta externo do PNCP. Com 1.000 resultados fictícios, paginar/renderizar em lotes e manter digitação e navegação responsivas; registrar o ambiente e o tamanho de cada lote usado.

### Validação externa controlada

Somente na fase de implementação/liberação, depois da validação offline: conferir documentação oficial atual do PNCP e do provedor de autenticação. Uma consulta pequena com modalidade explícita e limite de chamadas pode comparar uma amostra com os dados publicados. Registrar o gasto de chamadas; não executar varredura completa para verificar estilos ou navegação.

A validação externa deve distinguir disponibilidade do serviço de correção do app. Não concluir “nenhuma oportunidade existe” a partir de coleta incompleta ou fora do prazo. A revisão das atribuições profissionais e exigências do edital não é substituída por testes de palavras-chave.

## 3. Ordem de implementação e marcos de revisão

| Marco | Entrega revisável | Condição de saída |
|---|---|---|
| M1 — domínio | Catálogo versionado e corpus | AC01–09; iluminação pública independente de climatização |
| M2 — execução | IDs, progresso, limites, cancelamento e snapshots | AC10–19; estados reproduzíveis com transporte falso |
| M3 — experiência | Menu, filtros, resultados, salvamento e ajuda | AC20–21 e AC24–28; revisão visual aprovada |
| M4 — persistência | Histórico e conjuntos de relatórios | AC22–23; reinício e falhas de publicação testados |
| M5 — acesso | Autenticação real e isolamento | AC29–31 e proteções relevantes de AC33 |
| M6 — liberação | Integração, regressão, Windows e documentação | AC32–34 e suíte completa aprovada |

Os marcos foram executados localmente com tarefas independentes delegadas a agentes Luna. O marco de acesso público não está liberado até a configuração do Google no Cloudflare e o smoke test.

## 4. Migração e recuperação

Antes de implementar migrações, produzir backup consistente do SQLite e cópia das buscas/manifestos para uma pasta de recuperação, com a coleta parada. Não copiar um banco em escrita sem mecanismo de backup consistente. Conferir caminhos absolutos e nunca remover o histórico original como preparação.

Aplicar migração versionada e idempotente em transação; testar a partir do esquema existente. Arquivos JSON v1 continuam legíveis sem gravação automática. Introduzir o catálogo por configuração com padrão compatível; uma configuração inválida deve interromper a inicialização com mensagem clara.

Publicar arquivos da execução em diretório próprio e gravar manifesto somente quando o conjunto estiver pronto. O ponteiro da última consulta completa é atualizado por último. O rollback deve restaurar código/configuração compatíveis com o banco ou usar a cópia consistente; não tentar abrir um esquema incompatível e ignorar erros.

Antes de tornar a interface pública para várias contas, verificar isolamento de todos os arquivos legados, alias `ultimo.*`, endpoints de status e listagens. A existência do túnel não dispensa essas validações.

## 5. Rastreabilidade dos pedidos

| Pedido/sugestão | Onde foi incorporado |
|---|---|
| Engenheiro mecânico e eletricista | Catálogo, perfis e AC03/07 |
| Projetos, manutenção, PMOC, refrigeração, ventilação, chillers e câmaras frias | Setores mecânicos + serviços + corpus |
| Instalações, painéis, média tensão, geradores, SPDA, BMS, solar e eficiência | Setores elétricos + serviços + corpus |
| Contratos integrados, retrofit, hospitais/escolas e ambientes críticos | Setores conjuntos + contextos opcionais |
| Iluminação pública e todas as subáreas sugeridas | Seção própria no catálogo; AC02/05 |
| Hierarquia visual | Tokens, prioridade de cartão/CTA, AC24 |
| Redução de carga cognitiva | Menu por tarefas, filtros essenciais/avançados, AC24/34 |
| Espaço de respiro | Escala de espaçamento, larguras e layouts, AC26 |
| CTAs claros | Consulta como ação principal e feedback por estado, AC12/20/24 |
| Navegação previsível | Estado preservado, histórico e retorno à consulta, AC12/23/25 |
| Marcar todas por conjunto | Regras por grupo e seleção parcial, AC25 |
| Resultados progressivos, controle de requisições e dúvida sobre 2 minutos | Limites propostos, contagens, cancelamento e AC10–19 |
| Resumo dos editais, salvar buscas e exportar | UX de cartão, JSON de filtros, HTML/CSV/XLSX e AC20–23/28 |
| Login e menu | Fluxo previsto, verificação real do Google e pendência de quem pode acessar; AC29–31 |
| Somente specs, sem delegar ainda | Quatro documentos, sem alteração funcional, designação de agentes ou ativação externa |

## 6. Estado de aceitação após implementação local

- O código e a configuração local foram alterados e integrados; a política do Cloudflare permaneceu sem alterações.
- A suíte completa passou. Testes da autenticação usam chaves e tokens falsos; isso valida o verificador do app, não comprova que o Google esteja ativo no domínio.
- A página local foi inspecionada visualmente em desktop; essa inspeção não substitui teclado, 360/768 px e zoom de 200% previstos em AC25–27.
- Nenhuma consulta real ao PNCP foi iniciada para validar a interface; os testes usam transporte falso.
- A preferência de acesso está definida como qualquer conta Google. Configurar o IdP/política e verificar login, negação, expiração e saída ainda são necessários para AC31 e liberação pública.
