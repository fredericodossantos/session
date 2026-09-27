# Fase 3 — catálogo de áreas e regras de busca

Data: 26/09/2026. Versão: 1.1. Regras implementadas em `catalogo_areas.yaml`, vinculadas à [especificação principal](ESPECIFICACAO_FASE_3.md). Estado e evidências no [relatório de implementação](IMPLEMENTACAO_FASE_3.md).

## 1. Dimensões da seleção

A expressão atual “Área de atuação” mistura o equipamento com a tarefa realizada. Separar em quatro dimensões:

| Dimensão | Exemplos | Efeito |
|---|---|---|
| Setor técnico | Climatização, SPDA, iluminação pública | Define o assunto que torna o edital relevante |
| Tipo de serviço | Projeto, instalação, manutenção, fornecimento | Refina a atividade dentro do setor |
| Contexto (opcional) | Hospital, escola, indústria, data center | Refina o local/aplicação sem servir sozinho como prova de relevância técnica |
| Perfil profissional | Mecânica, Elétrica, Ambos, Multidisciplinar | Atalho para selecionar áreas relacionadas; não é uma exigência literal do objeto |

Uma licitação pode corresponder a vários setores e serviços, mantendo um único cartão. Guardar a evidência de cada correspondência para explicar o resultado.

## 2. Catálogo de setores

Os termos abaixo são o conjunto inicial a transformar em regras versionadas. Acentos, caixa, hífens e plurais previstos devem ser normalizados. Termos com “+” exigem as duas partes no mesmo objeto; alternativas separadas por ponto e vírgula indicam caminhos possíveis de correspondência. Não adotar busca por substring irrestrita.

### Engenharia mecânica e climatização

| ID estável | Rótulo na interface | Termos e contexto inicial |
|---|---|---|
| `climatizacao` | Climatização e ar-condicionado | ar-condicionado; condicionador de ar; climatização; climatizador; split; HVAC; VRF; VRV; fan coil; fancoil |
| `pmoc` | PMOC | PMOC; plano de manutenção operação e controle; plano de manutenção + climatização |
| `refrigeracao` | Refrigeração comercial e industrial | refrigeração comercial; refrigeração industrial; refrigeração; sistema frigorífico; unidade condensadora; resfriamento industrial |
| `ventilacao_exaustao` | Ventilação e exaustão | ventilação mecânica; sistema de exaustão; exaustor industrial; renovação de ar; exaustão + cozinha industrial |
| `agua_gelada` | Chillers, bombas e centrais de água gelada | chiller; central de água gelada; água gelada + bomba; torre de resfriamento; circuito de água gelada |
| `camaras_frias` | Câmaras frias e sistemas frigoríficos | câmara fria; câmara frigorífica; túnel de congelamento; instalação frigorífica |
| `conforto_termico` | Conforto térmico e eficiência da climatização | conforto térmico; eficiência energética + climatização/ar-condicionado/HVAC |

Bombas de saneamento isoladas e equipamentos de ventilação clínica não entram automaticamente nos setores acima. Refrigeração permanece compatível com o interesse já existente; descartar contexto exclusivamente automotivo conforme regras locais do setor.

### Engenharia elétrica

| ID estável | Rótulo na interface | Termos e contexto inicial |
|---|---|---|
| `instalacoes_eletricas` | Instalações elétricas prediais e industriais | instalação elétrica; instalações elétricas; infraestrutura elétrica; rede elétrica predial; rede elétrica industrial |
| `paineis_comandos` | Quadros, painéis e comandos elétricos | quadro elétrico; quadro de distribuição; painel elétrico; comando elétrico; centro de controle de motores |
| `subestacoes` | Subestações e redes de média tensão | subestação; média tensão; cabine primária; rede de distribuição de energia |
| `energia_emergencia` | Geradores, nobreaks e baterias | grupo gerador; gerador de energia; gerador elétrico; nobreak; no-break; UPS + alimentação ininterrupta; banco de baterias + energia/nobreak |
| `spda_aterramento` | SPDA e aterramento | SPDA; sistema de proteção contra descargas atmosféricas; para-raios; aterramento elétrico; malha de aterramento |
| `automacao_predial` | Automação predial e BMS | automação predial; sistema de gestão predial; BMS + edifício/climatização/predial |
| `solar_fotovoltaica` | Energia solar fotovoltaica | fotovoltaico; fotovoltaica; energia solar + geração elétrica; usina solar; inversor + fotovoltaico |
| `eficiencia_eletrica` | Eficiência energética elétrica | eficiência energética + instalação elétrica/iluminação/energia elétrica; correção de fator de potência; qualidade de energia elétrica |
| `iluminacao_publica` | Iluminação pública | iluminação pública; parque de iluminação; parque luminotécnico; rede de iluminação pública; luminárias + vias públicas/logradouros; telegestão + iluminação |

Projeto, manutenção e laudo elétrico aparecem como tipos de serviço combinados com esses setores. Um título explícito como “Laudo das instalações elétricas” deve corresponder sem mencionar climatização.

### Atuação conjunta e contratos integrados

| ID estável | Rótulo na interface | Regra inicial de contexto |
|---|---|---|
| `climatizacao_infra_eletrica` | Climatização com infraestrutura elétrica | Evidência de climatização + instalação/infraestrutura elétrica |
| `automacao_hvac` | Automação e controle de climatização | HVAC/climatização/ar-condicionado + automação/controle/BMS |
| `retrofit_predial` | Retrofit e modernização de prédios públicos | retrofit/requalificação/modernização + edifício/prédio + climatização/instalação elétrica/iluminação |
| `manutencao_integrada` | Manutenção predial integrada | manutenção predial/integrada + elétrica/climatização; manutenção predial genérica só mediante opção explícita abaixo |
| `ambientes_criticos` | Data centers e ambientes críticos | data center/datacenter/CPD/sala-cofre/ambiente crítico + refrigeração/climatização/energia/nobreak/gerador |

Opção avançada **“Incluir manutenção predial com escopo técnico a confirmar”**, desmarcada por padrão: permite títulos genéricos como “Manutenção predial integrada” mesmo sem detalhe elétrico/mecânico. Exibir a etiqueta “Escopo a confirmar no edital”. Essa exceção exige seleção de `manutencao_integrada` e não libera obras civis genéricas em outros setores.

Projetos de hospitais, escolas e órgãos públicos entram pelos setores técnicos e pelo contexto correspondente. Fiscalização/acompanhamento de obras, elaboração de memoriais e especificações são serviços aplicados ao setor selecionado; não servem sozinhos para captar qualquer obra.

## 3. Iluminação pública em detalhe

Área de primeiro nível dentro de Engenharia elétrica, com título visível e selecionável, sem ficar escondida em “Outros”. Subáreas propostas:

| ID de subárea | Opção | Regra complementar ao contexto de iluminação pública |
|---|---|---|
| `ip_manutencao` | Manutenção de iluminação pública | manutenção; conservação; reparo; atendimento corretivo |
| `ip_expansao` | Implantação e expansão de redes | implantação; instalação; ampliação; expansão; extensão de rede |
| `ip_led` | Modernização para LED | LED + modernização/substituição/luminária/iluminação |
| `ip_telegestao` | Telegestão e automação | telegestão; gestão remota; automação; controle remoto |
| `ip_eficiencia` | Eficiência energética | eficiência energética; eficientização; redução de consumo |
| `ip_componentes` | Postes, braços e luminárias | poste; braço; luminária; relé fotoelétrico, sempre no contexto do setor |
| `ip_projetos` | Projetos e fiscalização | projeto; fiscalização; supervisão; acompanhamento técnico |
| `ip_cadastro_gestao` | Cadastro e gestão do parque | cadastro; inventário; georreferenciamento; gestão + parque de iluminação/luminotécnico |

Selecionar o setor e nenhuma subárea significa todas as suas atividades. Selecionar subáreas restringe esse setor à união delas. Se outros setores estiverem selecionados, a restrição de iluminação pública não se aplica a eles.

Não incluir só porque aparece `LED`, `IP`, `poste` ou `rede`. Exemplos a rejeitar sem contexto adicional: painel de LED para eventos, lâmpada automotiva, rede de computadores, poste de cerca e endereço IP. “Eficiência energética” precisa de contexto de iluminação para corresponder a este setor específico.

**Iluminação Pública como unidade atendida.** “Iluminação Pública” também é nome de secretaria, departamento ou diretoria. Quando o núcleo do objeto é frota, veículos ou máquinas (termos da exclusão contextual `frota_veicular`: veículo, veicular, frota, automotivo/a, autopeças, caminhão, pneu, combustível, gasolina, óleo diesel, lubrificante, máquinas pesadas, maquinário pesado, linha amarela, oficina mecânica, funilaria), a menção só vale se o objeto trouxer evidência técnica explícita do parque: “manutenção de/da iluminação pública”, “conservação/expansão/ampliação/modernização da iluminação pública”, “implantação/instalação de iluminação pública”, “serviços/sistema/rede/pontos de iluminação pública”, “parque de iluminação”, “parque luminotécnico”, luminária, relé fotoelétrico, poste ou telegestão. Sem essa evidência, o setor é descartado.

Decisão sobre veículos a serviço do parque: caminhão cesto, guindauto ou equipe com veículo **para executar** a manutenção/expansão da iluminação pública entra (a exceção casa “manutenção da iluminação pública”, “poste”, “luminária” etc.), porque é serviço típico das empresas do setor. A **compra, o conserto ou os insumos do próprio veículo** (“manutenção do caminhão cesto utilizado pela Iluminação Pública”, pneus, combustível) não entram. Lâmpada isolada não é exceção, para não reabrir “lâmpada automotiva”. Os demais setores elétricos/mecânicos não recebem esta regra: seus termos (instalação elétrica, grupo gerador, subestação…) não são nomes de unidade administrativa; climatização e refrigeração mantêm suas exclusões automotivas fixas.

## 4. Tipos de serviço

Cada serviço é opcional e exige correspondência em algum setor selecionado. Nenhum serviço escolhido significa todas as atividades daquele setor.

| ID | Rótulo | Sinônimos iniciais |
|---|---|---|
| `projetos` | Projetos e dimensionamento | projeto; dimensionamento; cálculo de carga; estudo técnico |
| `instalacao` | Instalação e implantação | instalação; implantação; montagem |
| `comissionamento` | Comissionamento | comissionamento; testes de aceitação; partida assistida |
| `manutencao` | Manutenção preventiva e corretiva | manutenção; conservação; reparo; conserto; assistência técnica |
| `fornecimento` | Fornecimento e aquisição | fornecimento; aquisição; compra |
| `locacao` | Locação de equipamentos | locação; aluguel |
| `pecas` | Peças e insumos | peça; componente; insumo; material de reposição |
| `laudos_inspecoes` | Laudos, inspeções e perícias | laudo; inspeção; perícia; vistoria; diagnóstico técnico |
| `fiscalizacao` | Fiscalização e acompanhamento | fiscalização; supervisão; acompanhamento de obra; acompanhamento técnico |
| `memoriais` | Memoriais e especificações técnicas | memorial descritivo; memorial de cálculo; especificação técnica |
| `modernizacao` | Modernização e retrofit | modernização; retrofit; requalificação; substituição |
| `gestao` | Gestão e cadastro técnico | gestão; cadastro; inventário; georreferenciamento |

“PMOC” continua sendo setor/atividade específica, não um sinônimo de qualquer manutenção. Um edital com a sigla PMOC pode corresponder ao serviço `manutencao` pela regra explícita desse serviço, mesmo sem a palavra expandida.

## 5. Perfis e contextos

Presets de perfil:

- **Engenharia mecânica**: sugere os setores mecânicos. O usuário pode retirar ou acrescentar setores.
- **Engenharia elétrica**: sugere os setores elétricos, incluindo iluminação pública.
- **Ambos**: união das sugestões mecânicas e elétricas; não exige duas menções no objeto.
- **Empresa multidisciplinar**: união acima mais os contratos integrados. Escopo predial genérico permanece uma opção separada e desmarcada.

Aplicar um preset altera a seleção visível e seu resumo, sem iniciar consulta. Selecionar um perfil não esconde seleções ativas. Se houver edição manual posterior, mostrar “Seleção personalizada”.

Presets rápidos orientados ao negócio: “Climatização: instalação e manutenção”, “PMOC”, “Iluminação pública” e “Ver áreas da equipe”. O primeiro privilegia climatização, refrigeração, câmaras frias, água gelada e PMOC com instalação/manutenção, permitindo ajustes. A seleção inicial de compatibilidade deve preservar os setores já contemplados pelo YAML de climatização, sem ativar toda a elétrica.

Contextos opcionais: hospitais/saúde, escolas/educação, indústria, prédios administrativos/órgãos públicos e data centers/ambientes críticos. A ausência de contexto não restringe; vários contextos usam OU. Não exigir palavra “público” em todo objeto: a fonte já é a contratação pública, mas o tipo de instalação precisa de evidência quando usado como filtro.

O perfil serve à descoberta de oportunidades. A interface não deve dizer que um profissional está legalmente habilitado para todos os itens sugeridos; a compatibilidade efetiva da empresa com cada edital será conferida fora da classificação automática.

## 6. Regra de combinação e evidências

```text
aceito = escopo GO + esfera + município (se informado) + prazo
         E qualquer setor selecionado com sua regra satisfeita
         E qualquer serviço selecionado (se houver)
         E qualquer contexto selecionado (se houver)
         E qualquer palavra/frase adicional (se houver)
```

`qualquer` significa OU dentro do mesmo grupo; entre grupos usa-se E. Subáreas valem apenas para seu setor. Modalidades determinam a coleta; ME/EPP é um filtro posterior aos itens. Perfil não acrescenta mais uma condição depois de definir os setores.

Regras por setor devem permitir: `qualquer_termo`, `todos_os_grupos` (OU em cada grupo, E entre grupos), `exclusoes` e `excecoes_de_contexto`, com IDs estáveis e versão. No YAML, `exclusoes` descarta o setor sempre que um termo aparece; `exclusoes_contextuais` (lista de `{id, termos, exceto}`) descarta o setor quando algum `termos` aparece **e** nenhum `exceto` aparece — é a forma das exceções de contexto. O catálogo recusa exclusão contextual sem `id`, `termos` ou `exceto`. A configuração deve recusar IDs repetidos, regras sem evidência e referências a setores inexistentes. O catálogo não aceita código executável nem regex arbitrária fornecida pela interface.

Evidência mínima por resultado: setor, serviço/subárea quando encontrado, termo ou frase normalizada, trecho do objeto original e versão do catálogo. Não inventar percentuais de aderência. Exibir “Corresponde a iluminação pública: ‘modernização da iluminação pública’”.

Exclusões automotivas do YAML atual devem ser preservadas para o comportamento legado e refinadas por setor: não aplicar globalmente `frota` a um edital misto que tenha um trecho explícito de iluminação pública. Um resultado misto pode entrar por uma regra válida independente e mostrar a evidência. Testar exclusão de climatização exclusivamente veicular e inclusão de objetos mistos com contexto técnico comprovável.

Palavras-chave digitadas continuam sendo frases literais normalizadas do título/objeto, separadas por vírgula. Termo de equipamento genérico não expande o setor automaticamente. IDs internos nunca são usados como os únicos termos de busca.

## 7. Parâmetros e migração

Exemplo de filtros v2 (contrato proposto):

```json
{
  "schema_version": 2,
  "catalogo_versao": "1",
  "perfil": "eletrica",
  "setores": ["iluminacao_publica", "instalacoes_eletricas"],
  "subareas": {"iluminacao_publica": ["ip_manutencao", "ip_led"]},
  "servicos": ["manutencao", "modernizacao"],
  "contextos": [],
  "incluir_predial_generico": false,
  "modalidades": [6, 8],
  "uf": "GO",
  "esferas": ["E", "M"],
  "dias": 30,
  "municipio": null,
  "palavras_chave": [],
  "intervalo": 2,
  "me": false,
  "bruto": false
}
```

Reutilizar os nomes de parâmetros já existentes quando possível. `perfil` registra o preset escolhido; os IDs selecionados são a fonte efetiva da consulta. A versão usada deve ir para o histórico, mesmo que o catálogo seja atualizado depois.

Buscas antigas sem `schema_version` são v1 e mantêm o escopo de climatização. `areas` vazio corresponde a esse escopo sem refinamento de serviço. `instalacao`, `manutencao`, `fornecimento` e `pecas` tornam-se serviços; `pmoc` e `refrigeracao` tornam-se refinamentos de setor.

Para v1 com áreas mistas, preservar o OU original das seleções. Por exemplo, `["manutencao", "pmoc"]` significa manutenção no escopo de climatização **OU** PMOC, e não apenas PMOC com a palavra manutenção. O adaptador deve preservar essa expressão em `compatibilidade_v1` quando não couber na combinação simples v2. Ao carregar, mostrar “Busca antiga: critérios preservados” e oferecer conversão explícita para v2 com resumo antes de salvar. Não modificar o arquivo antigo apenas por abri-lo.

IDs desconhecidos ou retirados não podem ampliar silenciosamente a busca: manter o arquivo, informar as opções incompatíveis e pedir ajuste na tela. Se houver equivalência documentada entre versões do catálogo, aplicá-la com aviso. Importação/exportação de filtros, se exposta, deve validar o mesmo esquema e nunca executar uma consulta ao importar.

## 8. Casos essenciais do corpus

| Objeto fictício | Seleção | Resultado esperado |
|---|---|---|
| Modernização da iluminação pública com luminárias LED | Iluminação pública | Inclui, mesmo sem ar-condicionado |
| Telegestão do parque de iluminação pública | Iluminação pública / telegestão | Inclui |
| Aquisição de painel de LED para eventos | Iluminação pública | Exclui |
| Instalação de postes para cercamento | Iluminação pública | Exclui |
| Manutenção de subestação de média tensão | Subestações + manutenção | Inclui |
| Elaboração de laudo de SPDA e aterramento elétrico | SPDA + laudos | Inclui |
| Fornecimento de gerador de energia para escola | Energia de emergência + fornecimento | Inclui |
| Gerador de relatórios para sistema de informática | Energia de emergência | Exclui |
| Aquisição de aparelhos de ar-condicionado | Climatização + fornecimento | Inclui por aquisição |
| Aquisição de splitter HDMI | Climatização | Exclui |
| Contratação de PMOC | PMOC + manutenção | Inclui pela regra explícita PMOC |
| Instalação de câmara fria para alimentos | Câmaras frias + instalação | Inclui |
| Aquisição de bomba para poço artesiano | Água gelada | Exclui |
| Automação do sistema HVAC e infraestrutura elétrica | Automação HVAC / integrado | Inclui uma vez, com várias evidências |
| Reforma de prédio sem objeto técnico detalhado | Contratos integrados padrão | Exclui |
| Manutenção predial integrada | Integrado + opção de escopo a confirmar | Inclui com aviso; exclui com opção desmarcada |
| Manutenção de ar-condicionado automotivo da frota | Climatização padrão | Exclui |
| Manutenção de iluminação pública e veículos da frota | Iluminação pública | Inclui pelo contexto explícito de iluminação, com objeto completo visível |
| Manutenção de veículos, máquinas e sistemas hidráulicos da frota para atendimento das demandas da Iluminação Pública | Iluminação pública + manutenção | Exclui: IP só como unidade atendida |
| Aquisição de pneus / combustível para a Secretaria de Iluminação Pública | Iluminação pública | Exclui |
| Manutenção do caminhão cesto utilizado pela Iluminação Pública | Iluminação pública | Exclui (conserto do veículo) |
| Locação de caminhão cesto com operador para manutenção da iluminação pública | Iluminação pública | Inclui (veículo a serviço do parque) |
| Fornecimento de materiais elétricos destinados à manutenção da iluminação pública | Iluminação pública + manutenção | Inclui |

Acrescentar variantes com acentos, caixa, singular/plural e hífens. Cada setor e cada subárea de iluminação pública deve ter ao menos um caso positivo e um caso limítrofe/negativo antes da implementação ser considerada concluída.
