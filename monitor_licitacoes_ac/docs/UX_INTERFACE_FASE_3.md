# Fase 3 — interface, navegação e experiência de uso

Data: 26/09/2026. Versão: 1.1. Requisitos implementados na interface local em `templates/index.html`, `static/app.css` e `static/app.js`. Este documento continua como roteiro de UX; veja o [relatório de implementação](IMPLEMENTACAO_FASE_3.md) para limites da validação visual e publicação.

## 1. Resultado esperado

A pessoa abre o monitor, reconhece seu contexto em Goiás, escolhe o serviço que oferece e inicia a consulta. Enquanto espera, vê atividade e oportunidades surgindo. Ao terminar, consegue ler cada resumo, guardar os filtros, baixar os resultados e voltar à consulta depois.

A primeira tela deve responder: **o que consultar, onde consultar e qual é a próxima ação**. Informações técnicas, ajuda longa e gerenciamento de arquivos saem da área principal de decisão.

## 2. As cinco diretrizes solicitadas

| Diretriz do usuário | Decisão de interface | Como conferir |
|---|---|---|
| Hierarquia visual | Título da página, resumo do escopo e botão de consulta acima dos detalhes; cartões com objeto e prazo em primeiro plano | O usuário identifica a ação e o contexto sem percorrer a ajuda |
| Redução de carga cognitiva | Filtros essenciais visíveis; detalhes técnicos recolhidos; catálogo por grupos com pesquisa local | Tela inicial sem logs, JSON, códigos internos ou listas de ajuda extensas |
| Espaço de respiro | Escala de espaçamento consistente, separação entre grupos, alinhamento de rótulos e limites de largura | Verificação visual em desktop, celular e zoom |
| Destaque nos CTAs | “Consultar licitações” como única ação de maior destaque na montagem da busca | Salvar, limpar e gerenciar não competem visualmente com o início |
| Navegação sem fricção | Menu por tarefas, item atual indicado, preservação de filtros e retorno previsível | Navegar não dispara nova coleta nem apaga o preenchimento |

## 3. Navegação

Menu principal proposto: **Consultar · Buscas salvas · Histórico e relatórios · Ajuda**. Resultados pertencem à consulta e ficam no mesmo fluxo; evitar dois destinos diferentes com os mesmos cartões. A conta fica no extremo oposto do cabeçalho, com nome/e-mail e saída somente quando houver sessão validada.

No desktop, menu horizontal. No celular, botão “Menu” com estado expandido acessível; os mesmos rótulos, sem depender de ícones isolados. O item ativo usa texto, fundo e `aria-current`.

As rotas podem ser seções controladas por hash (`#consultar`, `#buscas`, `#historico`, `#ajuda`), mantendo o servidor existente. Somente a seção ativa fica no fluxo de foco. Atalhos antigos como `#consulta`, `#resultadosTitulo` e `#relatorios` devem encaminhar à seção correspondente, preservando links conhecidos.

Voltar/avançar no navegador restaura o destino. Sair de “Consultar” não cancela a execução; o cabeçalho conserva um indicador discreto “Consulta em andamento — acompanhar”. Ao voltar, recuperar o mesmo ID e os filtros daquele trabalho, sem nova chamada ao PNCP.

## 4. Estrutura da tela de consulta

Esboço funcional, sem compromisso com um framework:

```text
Monitor de licitações de engenharia                    Conta
Consultar | Buscas salvas | Histórico e relatórios | Ajuda

Encontre oportunidades para sua empresa
Goiás · Estadual e municipal · Próximos 30 dias

Atalhos: [Climatização] [PMOC] [Iluminação pública] [Áreas da equipe]

O que sua empresa quer atender?
[Perfil opcional: Mecânica / Elétrica / Ambos / Multidisciplinar]
[Setores selecionados e botão Escolher áreas]
[Tipos de serviço: Instalação, Manutenção, ...]
[Palavras do título/objeto, opcionais]

Onde e em quais modalidades?
[Goiás (GO)] [Todo o estado / município] [Prazo]
[Esferas] [Modalidades]

▸ Opções avançadas
Resumo: 3 setores · 2 serviços · 2 modalidades · todo o estado
[CONSULTAR LICITAÇÕES]    Salvar filtros    Limpar filtros

Andamento (aparece depois de iniciar)
Etapa · Tempo decorrido · Requisições · Quantidade encontrada
[Cancelar consulta]

Resultados (aparecem progressivamente)
[Objeto do edital]                 [Prazo]
Órgão · Município · Área identificada
Valor · Benefício ME/EPP · Por que apareceu
[Ver resumo]
```

### Filtros essenciais

- Escopo Goiás em destaque, sem um seletor de estado desabilitado que pareça quebrado. Texto “Goiás (GO) — cobertura atual”. Não oferecer outras UFs fictícias.
- Município por nome com seleção que resolve para IBGE, usando catálogo local de municípios de GO. Manter entrada de código em “Avançado” para compatibilidade. Se a seleção por nome não estiver disponível, mostrar campo IBGE com ajuda clara, sem afirmar que um texto livre filtrou a cidade.
- Prazo inicial de 30 dias, com rótulo “Propostas com encerramento nos próximos … dias”.
- Modalidades compactas com descrição acessível; pregão eletrônico sugerido como atalho, sem iniciar consulta. Nenhuma modalidade marcada implica erro de validação antes de chamar o servidor de coleta.
- Área elétrica e iluminação pública acessíveis no primeiro nível de escolha. Agrupar o catálogo em Mecânica, Elétrica e Integrados, com busca textual que apenas filtra opções localmente.
- Tipos de serviço disponíveis conforme o catálogo, sem exigir códigos ou digitação de sinônimos.
- Campo “Palavras do título/objeto (opcional)” com exemplo e instrução: “Separe por vírgula. Basta uma delas aparecer”.
- Chips de filtros ativos podem ser removidos individualmente. Presets deixam evidente o que marcaram.

### Opções avançadas

Guardar aqui: benefícios ME/EPP, contexto do empreendimento, subáreas detalhadas, intervalo entre chamadas, visualização dos limites de coleta, salvamento bruto e código IBGE manual. “Salvar respostas brutas” é administrativo e não aparece para visitantes comuns em modo autenticado.

Seleções feitas em Avançado aparecem no resumo mesmo quando o painel está fechado. Mostrar a indicação “Avançado — 2 filtros ativos” para evitar filtros escondidos que expliquem um resultado vazio.

### Marcar todas

Cada conjunto de checkboxes oferece “Marcar todas”/“Desmarcar todas” e contador. Seleção parcial usa estado misto. Grupos internos, como subáreas de iluminação pública, não mudam seleções de outros grupos.

Se houver pesquisa dentro do catálogo, o comando será “Marcar N opções visíveis”, para não selecionar silenciosamente itens ocultos. O botão geral “Marcar todas as áreas” fica disponível com esse nome explícito. “Desmarcar todas” deixa o grupo vazio; o comportamento de grupo vazio é explicado: setores/modalidades/esferas são obrigatórios, serviços/contextos/subáreas são opcionais.

## 5. Hierarquia, estilo e espaçamento

Especificação inicial de tokens, ajustável na revisão visual:

| Elemento | Diretriz |
|---|---|
| Fonte | Família de sistema; corpo 16 px; entrelinha 1,5; campos no mínimo 16 px no celular |
| Títulos | Página 28–32 px desktop / 24 px celular; seção 20–22 px; cartão 18 px |
| Texto secundário | 14 px ou mais; usado para contexto, não para requisitos ou erros importantes |
| Largura | Conteúdo até 1200 px; textos de ajuda até aproximadamente 75 caracteres por linha |
| Escala | 4, 8, 12, 16, 24, 32 e 48 px; usar tokens CSS |
| Espaçamento | 24–32 px entre seções; 16–24 px dentro de cartões; 8 px entre rótulo/campo |
| Margens | 24–32 px desktop; 16 px celular |
| Formulário | Até duas colunas no desktop, uma no celular; evitar grades com muitos campos apertados |
| Superfícies | Fundo claro `#F4F7FA`, painéis brancos, bordas leves `#D9E2EC`, sombra discreta |
| Texto e ação | Texto `#172B4D`; ação primária `#075985` com texto branco; foco `#1D4ED8` |
| Estados | Sucesso, atenção e erro com cor + ícone/legenda, nunca somente cor |
| Alvos | Área acionável de pelo menos 44 × 44 px para controles de toque |

Medir contraste das combinações efetivamente usadas: alvo de 4,5:1 para texto normal e 3:1 para componentes/foco e texto grande. Valores são critérios do projeto, a validar na versão renderizada.

O CTA principal usa fundo sólido; salvar/carregar/download usam estilo secundário; “Excluir” usa tratamento destrutivo discreto apenas no contexto de gerenciamento. Não usar três botões azuis idênticos para ações de pesos diferentes.

Uma barra de ação fixa só deve aparecer em telas pequenas quando o CTA original sair da área visível. Ela não pode cobrir cartões, mensagens, teclado, rodapé ou foco. Sem barras piscando e sem animação que simule porcentagem de conclusão.

## 6. Consulta, progresso e respostas ao usuário

| Estado | Conteúdo e ação esperados |
|---|---|
| Pronto | Resumo dos critérios; CTA “Consultar licitações” |
| Validação falhou | Mensagem ao lado do campo e resumo de erros; foco no primeiro problema; sem chamadas PNCP |
| Iniciando | Confirmação imediata, ID da consulta e botão impedindo clique duplicado |
| Coletando páginas | Modalidade, página, registros lidos, candidatos encontrados, chamadas e tempo decorrido |
| Classificando itens | Cartões já visíveis; benefício “Em análise” até haver evidência; contagens atualizadas |
| Cancelamento solicitado | “Finalizando a requisição em andamento. Os resultados encontrados serão preservados.” |
| Concluída | Total de resultados, data/hora, filtros aplicados e downloads |
| Concluída sem resultados | Explicar que nenhum resultado correspondeu; oferecer editar filtros ou ampliar prazo; nunca iniciar outra consulta automaticamente |
| Parcial/limite/cancelada | Aviso persistente, motivo, cobertura e downloads identificados como parciais |
| Falha de conexão com o app | “Não foi possível atualizar o andamento”; manter resultados já vistos e tentar reconexão com intervalo limitado |
| Sessão expirada | Ação “Entrar novamente”, com restauração do destino; não interpretar HTML de login como JSON da API |

Não tratar 429 como “nenhum resultado”. Falha total não substitui o relatório completo anterior. Carregamento da página consulta somente o estado local da última execução acessível; não chama o PNCP.

O polling deve evitar ciclos paralelos, respeitar o estado final e mostrar a última atualização. Em erro de rede prolongado, deixar explícita a falta de atualização. Não duplicar consultas ao reconectar.

## 7. Resultados e resumo

Ordem inicial: encerramento mais próximo, com ordenação estável por identidade em empate. Quando chega uma atualização, modificar o cartão existente. Paginar ou renderizar em lotes; não reconstruir milhares de cartões a cada segundo nem fechar o resumo que o usuário está lendo.

No cartão, mostrar apenas:

1. Objeto/título legível e prazo de proposta.
2. Órgão, município/UF e valor estimado (ou “Não informado”).
3. Setores identificados, situação ME/EPP e indicação nova/atualizada quando disponível.
4. Uma explicação curta da correspondência e botão “Ver resumo”.

O resumo expande no próprio cartão, com objeto completo, órgão/unidade, modalidade e número, local, datas, valor, origem, classificação dos itens, termos/evidências e referência PNCP. Códigos internos e origem do cache ficam em “Detalhes técnicos”, não no texto principal.

Links externos são secundários e indicam “Abrir no PNCP”/“Abrir no portal de origem”, com abertura em nova aba identificada. Não prometer que o portal dispensa autenticação. O resumo é dos dados coletados, com campos ausentes declarados; não afirmar que houve leitura integral do edital.

Formato de data em português e indicação de horário de Brasília. Valor zero que represente informação ausente/sigilosa precisa de rótulo adequado quando a fonte permitir identificar isso, sem inventar valor.

Após concluir, o CTA de destaque passa a “Baixar resultados”. Oferecer **Excel (.xlsx)** para organizar/analisar, **HTML** para leitura e compartilhamento e **CSV** para integração, todos da mesma consulta. Mostrar quantidade, filtros, geração e condição completa/parcial nos arquivos.

## 8. Buscas salvas

“Salvar filtros” abre um formulário curto com nome obrigatório, resumo do que será salvo e botão “Salvar busca”. A própria tela sugere um nome editável, como “Iluminação pública — GO — manutenção”. É possível manter o campo vazio, mas a tentativa de salvar deve apresentar o motivo claramente.

Requisitos:

- Nome vazio: “Dê um nome para salvar esta busca”; foco no campo e `aria-invalid`.
- Nome em conflito, inclusive diferença só de acento/caixa ou colisão do nome de arquivo: “Já existe uma busca com esse nome. Use outro nome.” Não sobrescrever automaticamente.
- Durante salvamento: estado “Salvando…” e prevenção de cliques repetidos.
- Sucesso: “Busca salva”, seleção atualizada e ação “Ver buscas salvas”.
- Falha de rede/servidor: mensagem persistente, manter dados digitados e permitir nova tentativa.
- Carregar: restaurar campos, abrir Consultar e mostrar “Filtros carregados. Revise e inicie quando quiser”.
- Excluir: confirmação com o nome exato da busca, antes de remover o arquivo.
- Listagem com nome, setores principais e data da alteração, sem nomes técnicos de arquivos como rótulo principal.
- Filtros importados/legados inválidos: apresentar campos incompatíveis sem perder o arquivo nem disparar consulta.

Salvar filtros não salva uma nova cópia dos resultados. A interface explica essa diferença em uma frase próxima à ação, sem exigir leitura da ajuda inteira.

## 9. Histórico e relatórios

Uma linha/cartão por execução: data/hora, critérios resumidos, quantidade de resultados, duração, estado e ações “Ver resultados”, “Usar filtros” e “Baixar”. Dar acesso a todas as oportunidades daquela execução, inclusive além da primeira página.

“Usar filtros” prepara uma nova busca, sem coleta imediata. “Ver resultados” abre o snapshot salvo sem chamar o PNCP. Falha parcial ou cancelamento aparece na listagem e dentro do relatório. Não dar a entender que resultados antigos ainda têm proposta aberta: mostrar data da consulta e prazo atual do registro.

Persistir manifestos para que arquivos permaneçam encontráveis após reiniciar o servidor. A lista deve ter paginação e estados vazio/erro. Arquivos antigos sem manifesto podem aparecer em uma área “Relatórios anteriores” com data inferida do nome identificada como tal, sem inventar filtros ou estado de conclusão.

## 10. Entrada, conta e ajuda

O fluxo externo proposto é: endereço público → tela de entrada do provedor validado → app → menu e identidade. Uma tela de apresentação própria pode explicar o produto e oferecer “Entrar com Google” somente depois de existir integração funcional com Google. Não desenhar botão que apenas simule autenticação.

A tela inicial de conta precisa cobrir: acesso permitido, conta sem autorização, sessão expirada e saída. Mensagens em português no que o app controla. Não prometer tradução de toda a interface do provedor. No acesso local permitido, mostrar “Modo local”; numa página pública sem autenticação, não apresentar o rótulo enganoso “Acesso local”.

Ajuda em página própria, organizada por tarefas: primeira busca, áreas/perfis, iluminação pública, palavras-chave, ME/EPP, acompanhamento/cancelamento, salvar/carregar, baixar formatos e solução de problemas. Pequenos links de ajuda ao lado de campos abrem a seção correspondente. Explicar claramente por que dois minutos não garantem uma consulta completa.

## 11. Acessibilidade e comportamento responsivo

- Usar elementos semânticos, `fieldset`/`legend`, rótulos ligados aos campos e ordem de tabulação natural.
- Foco visível em todos os controles; retorno de foco ao fechar menus e diálogos; `Escape` fecha um diálogo sem executar ação.
- Mensagens de validação associadas ao campo; estado global em região viva sem anunciar a lista inteira a cada polling.
- Não depender de hover, cor ou ícones para indicar ação/estado.
- Respeitar preferência de movimento reduzido; evitar animação infinita quando a consulta estiver parada.
- Interface utilizável com teclado, zoom de 200%, largura de 360 px e sem rolagem horizontal geral.
- Testar no mínimo 360, 768 e 1440 px, incluindo textos longos, vários filtros e resultados vazios/parciais.
- Alteração de filtros após iniciar não modifica uma execução em curso. Mostrar “Filtros desta consulta” separadamente dos novos critérios em edição.

## 12. Revisão de usabilidade proposta

Roteiro curto com um usuário que não conhece o sistema: localizar iluminação pública, selecionar manutenção, consultar Goiás em esfera municipal, entender o andamento, abrir um resumo e baixar Excel. Depois salvar a busca, navegar à ajuda e carregá-la novamente.

Alvo: concluir o roteiro sem orientação externa e sem iniciar chamadas acidentais. Registrar dúvidas, cliques errados e mensagens não compreendidas; corrigir a interface antes da liberação. Reavaliar a proposta se a quantidade de campos visíveis continuar exigindo rolagem extensa antes do CTA.
