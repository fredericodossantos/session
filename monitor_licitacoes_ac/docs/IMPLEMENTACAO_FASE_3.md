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

Revisões delegadas: API interrompe em HTTP 429 sem retry oculto e respeita `Retry-After`; classificação limita palavras-chave ao objeto e mantém dados de ME/EPP ausentes como desconhecidos; persistência e relatórios têm rollback, e os lançadores validam os pré-requisitos do modo público. Uma regressão na fixture de migração foi corrigida para fechar as próprias conexões SQLite de teste antes da verificação de arquivos no Windows.

## Pendências antes de oferecer acesso público

1. Configurar Google como IdP e aplicar no Cloudflare a política para qualquer conta Google, conforme a decisão do usuário.
2. Informar `CF_ACCESS_TEAM_DOMAIN` e `CF_ACCESS_AUD` (ou os valores equivalentes no `config.yaml`) e confirmar que o serviço de origem inicia em modo `cloudflare`.
3. Validar no domínio login permitido, bloqueio de sessão ausente/expirada, saída e isolamento com mais de uma conta. Só então anunciar autenticação pública ativa.
4. Completar revisão manual de acessibilidade e responsividade nas larguras e níveis de zoom dos critérios AC25–27.
5. Fazer smoke test dos lançadores Windows sem iniciar uma varredura PNCP. O ambiente de testes passou pela venv; a execução do túnel e a configuração externa não foram testadas. O `cloudflared.exe` local informa versão 2026.9.3; a opção de token por arquivo requer 2025.4.0 ou posterior, segundo os [parâmetros oficiais do túnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/).

Referências oficiais para a etapa Cloudflare: [configuração do Google como provedor de identidade](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/google/), [validação de JWT do Access](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/) e [parâmetros do cloudflared](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/).
