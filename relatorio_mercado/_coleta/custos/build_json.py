import json

DATA_ACESSO = "2026-09-27"
registros = []

def add(categoria, item, valor, unidade, fonte_url, trecho, obs, conf):
    registros.append({
        "categoria": categoria,
        "item": item,
        "valor": valor,
        "unidade": unidade,
        "fonte_url": fonte_url,
        "data_acesso": DATA_ACESSO,
        "trecho_ou_pagina": trecho,
        "observacao": obs,
        "confiabilidade": conf,
    })

# =========================================================================
# 1. MÃO DE OBRA
# =========================================================================

add("Mão de obra - referência geral", "Salário mínimo nacional 2026", 1621.00, "R$/mês",
    "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/decreto/d12797.htm",
    "Decreto nº 12.797/2025, vigência a partir de 01/01/2026, reajuste de 6,79% sobre R$1.518,00 (2025). "
    "Acesso direto ao planalto.gov.br bloqueado nesta sessão (proxy de rede); conteúdo confirmado de forma "
    "cruzada por 4 fontes secundárias independentes (Serasa Experian, Buk, Barbieri Advogados, Sintespem-SD) "
    "que citam o mesmo decreto e valor.",
    "Base para todos os cálculos de piso/insalubridade/periculosidade abaixo.",
    "alta")

# --- Construção civil GO (SINDUSCON-GO / SINTRACOM Goiânia) ---
fonte_cct_cc = "https://www.sintracomgoiania.com.br/images/convencoes_arquivos/construcao-civil/CCT_2025_2027_Divulgacao_Conjunta_Sinduscon_e_Sintracom_Goias_assinado.pdf"

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)", "Ajudante/Servente - piso mensal",
    1548.80, "R$/mês", fonte_cct_cc,
    "pág. 2, Cláusula Quarta - Dos Pisos Salariais, quadro de funções, vigência a partir de 01/05/2025",
    "CCT 2025/2027 (Termo Aditivo Salarial), vigência 01/05/2025 a 30/04/2027. Reajuste de 7,32% sobre o "
    "praticado em 30/04/2025. Jornada 44h/semana (padrão CLT/CCT construção civil).", "alta")

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)", "Ajudante/Servente - valor hora",
    7.04, "R$/hora", fonte_cct_cc, "pág. 2, mesma tabela", "Mesma fonte do item acima.", "alta")

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)", "Meio-Oficial (eletricista/pedreiro/carpinteiro qualificado) - piso mensal",
    1720.40, "R$/mês", fonte_cct_cc, "pág. 2, quadro de pisos salariais",
    "Categoria 'Meio-Oficial' é a referência de eletricista de obra qualificado nesta CCT.", "alta")

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)", "Meio-Oficial - valor hora",
    7.82, "R$/hora", fonte_cct_cc, "pág. 2, quadro de pisos salariais", "Mesma fonte.", "alta")

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)", "Encarregado - piso mensal",
    3542.00, "R$/mês", fonte_cct_cc, "pág. 3, quadro de pisos salariais", "", "alta")

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)", "Mestre de Obras - piso mensal",
    5060.00, "R$/mês", fonte_cct_cc, "pág. 3, quadro de pisos salariais",
    "Piso novo, criado nesta CCT 2025/2027.", "alta")

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)",
    "Técnico de refrigeração/AC predial ('Profissional em Manutenção Industrial e Predial, Ar Condicionado') - piso mínimo aplicável",
    1548.80, "R$/mês", fonte_cct_cc,
    "pág. 1, Cláusula Quinta (lista nominal da função) c/c pág. 2 §2º ('piso salarial para trabalhadores sem "
    "piso definido será igual ao salário base do ajudante/servente')",
    "A CCT NÃO define piso próprio para esta função: ela só recebe o reajuste de 7,32% sobre o salário já "
    "praticado, e o piso mínimo legal aplicável é o do ajudante/servente. Na prática de mercado a remuneração "
    "efetiva costuma ficar acima deste piso mínimo (ver estimativa de mercado na aba de premissas).", "alta")

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)",
    "Operador de grua/mini-grua (proxy p/ operador de munck/guindauto) e Supervisor de segurança (proxy p/ técnico de segurança) - piso mínimo aplicável",
    1548.80, "R$/mês", fonte_cct_cc,
    "pág. 1, Cláusula Quinta (lista nominal das funções) c/c pág. 2 §2º",
    "Mesma regra do item anterior: sem piso próprio definido nesta CCT; piso mínimo = ajudante/servente.",
    "alta")

add("Mão de obra - Construção civil (SINDUSCON-GO/SINTRACOM)", "Vale-refeição / auxílio-alimentação (manutenção predial/facilities)",
    22.54, "R$/dia trabalhado", fonte_cct_cc,
    "pág. 8-9, Cláusula Décima Primeira - Alimentação, §3º",
    "Válido a partir de 01/05/2025. O fornecimento de VALE REFEIÇÃO (em pecúnia/cartão) está restrito aos "
    "empregados de escritório e aos que desenvolvem atividades de manutenção predial/facilities - "
    "aplica-se diretamente ao cenário de equipes de manutenção.", "alta")

add("Mão de obra - Construção civil / Lei Federal", "Salário mínimo profissional Engenheiro - jornada 6h (Lei 4.950-A/66, art. 5º)",
    9726.00, "R$/mês", "https://www.seesp.org.br/site/juridico/legislacao/lei-4-950-a-1966-piso-salarial",
    "Art. 5º da Lei 4.950-A/1966: piso-base de 6 (seis) vezes o maior salário mínimo nacional para jornada de 6h/dia.",
    "Valor calculado por nós: 6 × R$1.621,00 (salário mínimo 2026) = R$9.726,00. A lei fixa o piso em múltiplos "
    "de salário mínimo; o valor em R$ é cálculo próprio a partir do decreto 12.797/2025.", "alta")

add("Mão de obra - Construção civil / Lei Federal", "Salário mínimo profissional Engenheiro - jornada 8h (Lei 4.950-A/66, arts. 5º e 6º)",
    13778.50, "R$/mês", "https://www.seesp.org.br/site/juridico/legislacao/lei-4-950-a-1966-piso-salarial",
    "Art. 6º: horas excedentes das 6 diárias acrescidas de 25%. Matematicamente equivale a 8,5 salários mínimos "
    "para jornada de 8h/dia (6 SM base + 2h extras a 125% = +2,5 SM).",
    "Valor calculado por nós: 8,5 × R$1.621,00 = R$13.778,50. Confere com a regra de mercado consagrada "
    "'8,5 salários mínimos para 8h', mas obtida por dedução direta do texto legal (não copiada de terceiros).",
    "alta")

# --- SEAC/SEACONS Goiás (limpeza, conservação, manutenção predial terceirizada) ---
fonte_cdps_2025 = "https://goias.gov.br/seinfra/wp-content/uploads/sites/6/2025/09/ANEXO-3.pdf"
fonte_cct_seac_2025 = "https://www.corengo.org.br/wp-content/uploads/2025/04/11-Apendice-G-CCT-2025.2026-SEAC.GO-GO000026.25.pdf"
fonte_cct_seac_2026 = "https://febrac.org.br/wp-content/uploads/2026/01/GO001031.2025C-CCT-2026-2027-LIMPEZA-AMBIENTAL-ESTADO-DE-GOIAS-REGISTRADA.pdf"

add("Mão de obra - SEAC-GO/SEACONS (terceirização/manutenção predial)", "Eletricista - piso mensal (01/01/2025)",
    3229.78, "R$/mês", fonte_cdps_2025,
    "pág. 3, ANEXO à CDPS nº /2025, item 25 'Eletricista'",
    "CDPS (Certidão de Demonstração de Pisos Salariais) vinculada à CCT SEAC-GO x SEACONS 2025/2026 "
    "(registro GO000026/2025). Reajuste de 6,77% já aplicado sobre piso 01/01/2024 (R$3.024,99).", "alta")

add("Mão de obra - SEAC-GO/SEACONS (terceirização/manutenção predial)", "Auxiliar de Manutenção Predial - piso mensal (01/01/2025)",
    3229.78, "R$/mês", fonte_cdps_2025, "pág. 3, item 11", "Mesmo valor da função Eletricista nesta CDPS.", "alta")

add("Mão de obra - SEAC-GO/SEACONS (terceirização/manutenção predial)", "Ajudante/Amarrador - piso mensal (01/01/2025)",
    1601.55, "R$/mês", fonte_cdps_2025, "pág. 3, item 1", "Piso-base da categoria (funções sem qualificação).", "alta")

add("Mão de obra - SEAC-GO/SEACONS (terceirização/manutenção predial)", "Vigia - piso mensal (01/01/2025)",
    1768.08, "R$/mês", fonte_cdps_2025, "pág. 4, item 59", "", "alta")

add("Mão de obra - SEAC-GO/SEACONS (terceirização/manutenção predial)", "Motorista de carros leves - piso mensal (01/01/2025)",
    2028.63, "R$/mês", fonte_cdps_2025, "pág. 4, item 42",
    "Piso classificado como 'SUB JUDICE' - há decisão judicial (processo nº 0010802-64.2024.5.18.0010, TRT-18) "
    "que impede as empresas de utilizar este piso específico enquanto a disputa não é resolvida (ver "
    "cct_seac_corengo.pdf, pág. 3 e 6 desta pasta). Usar com cautela contratual.", "média")

add("Mão de obra - SEAC-GO/SEACONS (terceirização/manutenção predial)",
    "Técnico em Refrigeração (CBO 9112-05) - piso mensal estimado 2026",
    3450.55, "R$/mês", fonte_cct_seac_2026,
    "pág. 2, Cláusula Terceira, §2º e §3º: 'As funções Técnico em Refrigeração (CBO 9112-05)... passarão a "
    "ter piso salarial definidos a partir da vigência desta CCT [01/01/2026]'",
    "ESTIMATIVA. A CCT 2026/2027 determina a criação de piso próprio para esta função a partir de 2026, mas "
    "a CDPS específica de 2026 (documento que traria o valor numérico definitivo) não foi localizada nesta "
    "sessão nem em busca web dedicada. Premissa adotada: aplicar o reajuste geral de 6,8340% (cláusula 3ª "
    "§3º) sobre o piso de Eletricista/Encanador 2025 (R$3.229,78, mesma faixa salarial das funções técnicas "
    "de manutenção nesta CCT) => 3.229,78 × 1,06834 = R$3.450,55. Recomenda-se confirmar com o SEAC-GO ou "
    "SEACONS a CDPS 2026 antes de fechar orçamento.", "baixa")

add("Mão de obra - SEAC-GO/SEACONS", "Insalubridade grau médio (20% sobre salário mínimo nacional) - valor 2026",
    324.20, "R$/mês", "https://goias.gov.br/seinfra/wp-content/uploads/sites/6/2025/09/ANEXO-3.pdf",
    "pág. 1-2 do CDPS: regra 'insalubridade em grau médio corresponde a 20% sobre o Salário Mínimo Nacional "
    "vigente' (exemplo docto: R$303,60 = 20% de R$1.518,00, SM 2025)",
    "Valor 2026 recalculado por nós: 20% × R$1.621,00 = R$324,20. A regra percentual (20%) é da fonte "
    "primária; a base 2026 é do Decreto 12.797/2025.", "alta")

add("Mão de obra - SEAC-GO/SEACONS", "Insalubridade grau máximo (40% sobre salário mínimo nacional) - valor 2026",
    648.40, "R$/mês", "https://goias.gov.br/seinfra/wp-content/uploads/sites/6/2025/09/ANEXO-3.pdf",
    "pág. 2 do CDPS: regra '40% sobre o Salário Mínimo Nacional vigente'",
    "Valor 2026 recalculado por nós: 40% × R$1.621,00 = R$648,40.", "alta")

# --- SIMELGO / SINDMETAL (metalúrgicos, eletricista industrial) ---
add("Mão de obra - SIMELGO/SINDMETAL Goiás (metalúrgicos/eletricista industrial)",
    "Piso salarial geral da categoria (1 salário mínimo + 20%) - valor 2026",
    1945.20, "R$/mês",
    "https://sindmetalgo.com.br/wp-content/uploads/2024/04/Mediador_-_Extrato_Convencao_Coletiva_SIMELGO_ULTIMA_assinado_assinado.pdf",
    "Cláusula Terceira - Do Piso Salarial: 'Piso Salarial para os trabalhadores da categoria, no valor "
    "equivalente a 01 salário mínimo legal, acrescido de 20%'",
    "Texto-fonte é da CCT SIMELGO x SINDMETAL vigência 2024/2025 (a regra do piso é estável e citada também "
    "no aditivo 2025/2026, conforme simelgo.com.br/noticias, mas o PDF do aditivo 2025/2026 com o texto "
    "integral não pôde ser baixado nesta sessão - domínio bloqueado pela rede). Valor 2026 recalculado: "
    "1,20 × R$1.621,00 = R$1.945,20. Esta é a categoria patronal correta para eletricista/mecânico industrial "
    "de manutenção (fora do regime SEAC/SINDUSCON).", "média")

# =========================================================================
# 2. ENCARGOS SOCIAIS (SINAPI)
# =========================================================================

fonte_encargos = "https://buscadorsinapi.com.br/encargos-sociais"

add("Encargos sociais SINAPI", "Encargos sociais Horista - Goiás - DESONERADO (vigência 2026, 8ª edição)",
    93.22, "% sobre salário", fonte_encargos,
    "Tabela 'Vigência ano-calendário 2026 · publicado pela Caixa em 13/07/2026 · Livro SINAPI - Cálculos e "
    "Parâmetros, 8ª Edição', linha Goiás/GO",
    "Fonte terceirizada (agregador), não a planilha oficial da CAIXA (bloqueada por proxy de rede nesta "
    "sessão). Recomenda-se conferir no Caderno Técnico oficial da CAIXA antes de uso definitivo em orçamento.",
    "média")

add("Encargos sociais SINAPI", "Encargos sociais Horista - Goiás - ONERADO (vigência 2026, 8ª edição)",
    107.72, "% sobre salário", fonte_encargos,
    "mesma tabela, coluna 'Horista Onerado', linha Goiás/GO", "Mesma ressalva do item acima.", "média")

add("Encargos sociais SINAPI", "Encargos sociais Horista - Goiás - DESONERADO (vigência 2025, 7ª edição)",
    87.82, "% sobre salário", fonte_encargos,
    "Tabela 'Vigência ano-calendário 2025 · publicado pela Caixa em 18/02/2026 · 7ª Edição', linha Goiás/GO",
    "Série anterior, útil para comparação/transição. Mesma ressalva de confiabilidade.", "média")

add("Encargos sociais SINAPI", "Encargos sociais Horista - Goiás - ONERADO (vigência 2025, 7ª edição)",
    108.78, "% sobre salário", fonte_encargos,
    "mesma tabela, coluna 'Horista Onerado', linha Goiás/GO", "Mesma ressalva.", "média")

add("Encargos sociais SINAPI", "Encargos sociais Mensalista - Goiás",
    None, "% sobre salário", fonte_encargos,
    "não encontrado nesta fonte (site traz apenas tabela Horista Desonerado/Onerado por UF)",
    "NÃO ENCONTRADO nesta sessão. ESTIMATIVA proposta: para mão de obra de manutenção contratada por "
    "empreitada/posto (encarregados, técnicos mensalistas), usar como proxy o mesmo percentual Horista "
    "Onerado/Desonerado de GO acima, com ressalva expressa de que a tabela de Mensalista tende a ser "
    "de 5 a 10 p.p. menor que a de Horista na metodologia SINAPI (por não incluir corte de ponto/reincidência "
    "de repouso semanal remunerado da mesma forma). Confirmar com o Caderno Técnico da CAIXA "
    "'Encargos Sociais' antes de aplicar em orçamento definitivo.", "baixa")

# =========================================================================
# 3. BDI TCU 2622/2013
# =========================================================================

fonte_bdi = "https://buscadorsinapi.com.br/bdi-referencia"
obs_bdi = ("Fonte terceirizada (agregador SINAPI), não o inteiro teor do Acórdão 2622/2013-TCU-Plenário. "
           "Tentativas de acesso direto a cópias do acórdão hospedadas em domínios de prefeituras/universidades "
           "(editais.uff.br, tamarana.pr.gov.br) e ao portal do TCU foram bloqueadas pelo proxy de rede ou por "
           "proteção anti-bot nesta sessão. Os valores batem com os números amplamente publicados/consagrados "
           "do Acórdão 2622/2013 (item 9.2.1) na literatura de engenharia de custos - recomenda-se conferência "
           "cruzada antes de uso formal em processo licitatório.")

add("BDI - Acórdão TCU 2622/2013", "Faixa BDI - Construção de Edifícios - 1º quartil",
    20.34, "%", fonte_bdi, "Tabela 'Faixas de BDI por Tipo de Obra', linha Edifícios", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013", "Faixa BDI - Construção de Edifícios - médio",
    22.12, "%", fonte_bdi, "mesma tabela, coluna médio", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013", "Faixa BDI - Construção de Edifícios - 3º quartil",
    25.00, "%", fonte_bdi, "mesma tabela, coluna 3º quartil", obs_bdi, "média")

add("BDI - Acórdão TCU 2622/2013", "Faixa BDI - Construção e Manutenção de Estações e Redes de Distribuição de Energia Elétrica - 1º quartil",
    24.00, "%", fonte_bdi, "mesma tabela, linha 'Construção e Manutenção de Estações e Redes de Distribuição de Energia Elétrica'", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013", "Faixa BDI - Construção e Manutenção de Estações e Redes de Distribuição de Energia Elétrica - médio",
    25.84, "%", fonte_bdi, "mesma tabela, coluna médio", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013", "Faixa BDI - Construção e Manutenção de Estações e Redes de Distribuição de Energia Elétrica - 3º quartil",
    27.86, "%", fonte_bdi, "mesma tabela, coluna 3º quartil", obs_bdi, "média")

add("BDI - Acórdão TCU 2622/2013 - Composição (base Edificações)", "AC - Administração Central (1ºQ / médio / 3ºQ)",
    "3,00% / 4,00% / 5,50%", "%", fonte_bdi, "Tabela de componentes do BDI", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013 - Composição (base Edificações)", "S - Seguro e Garantia (1ºQ / médio / 3ºQ)",
    "0,80% / 0,80% / 1,00%", "%", fonte_bdi, "Tabela de componentes do BDI", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013 - Composição (base Edificações)", "R - Risco (1ºQ / médio / 3ºQ)",
    "0,97% / 1,27% / 1,27%", "%", fonte_bdi, "Tabela de componentes do BDI", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013 - Composição (base Edificações)", "G - Garantia Adicional (1ºQ / médio / 3ºQ)",
    "0,00% / 0,00% / 0,50%", "%", fonte_bdi, "Tabela de componentes do BDI - não tabelado formalmente pelo Acórdão, prática de editais", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013 - Composição (base Edificações)", "DF - Despesas Financeiras (1ºQ / médio / 3ºQ)",
    "0,59% / 1,23% / 1,39%", "%", fonte_bdi, "Tabela de componentes do BDI", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013 - Composição (base Edificações)", "L - Lucro (1ºQ / médio / 3ºQ)",
    "6,16% / 7,40% / 8,96%", "%", fonte_bdi, "Tabela de componentes do BDI", obs_bdi, "média")
add("BDI - Acórdão TCU 2622/2013 - Composição (base Edificações)", "T - Tributos PIS+COFINS+ISS (1ºQ / médio / 3ºQ)",
    "5,65% / 6,65% / 8,65%", "%", fonte_bdi, "Tabela de componentes do BDI: PIS 0,65% + COFINS 3,00% + ISS 2% a 5% conforme município", obs_bdi, "média")

# =========================================================================
# 4. TRIBUTOS (ISS Goiânia / Simples Nacional)
# =========================================================================

add("Tributos", "ISS Goiânia - alíquota geral para serviços prestados por empresas (inclui manutenção/instalação, itens 7.05 e 14.06 da lista de serviços)",
    5.0, "%", "https://www.goiania.go.gov.br/download/financas/novoctm.pdf",
    "pág. 37-38 (numeração do PDF), Art. 71, IV do Código Tributário Municipal de Goiânia (regulamentado pela "
    "Lei Complementar nº 344/2021): 'Demais atividades exercidas na forma de empresas... 5% (cinco por cento)'",
    "Confirmado por leitura direta do PDF oficial da Prefeitura de Goiânia. Os itens 7.05 (reparação/conservação "
    "de edifícios) e 14.06 (instalação/montagem de aparelhos/máquinas/equipamentos) da lista de serviços "
    "municipal não têm alíquota diferenciada prevista (as reduções de 2% e 3,5% do art. 71 são específicas "
    "para transporte coletivo urbano e serviços de saúde, respectivamente).", "alta")

add("Tributos", "Simples Nacional - enquadramento de serviços de manutenção/instalação elétrica e de refrigeração em imóveis prontos (fora de obra de engenharia)",
    "Anexo III (alíquota efetiva 6% a 33% conforme RBT12 e fator 'r')", "-",
    "https://www.marciobalduchi.com.br/diversos-servicos-de-instalacao-e-manutencao-tributados-no-anexo-iii-do-simples-nacional/",
    "Artigo: 'diversos serviços de instalação e manutenção (elétrica, ar condicionado, ventilação, refrigeração, "
    "prevenção contra incêndio) são tributados no Anexo III da LC 123/2006'",
    "NÃO acessamos diretamente a Resolução CGSN/LC 123 nesta sessão (fonte é artigo jurídico especializado, "
    "consistente com o texto legal amplamente conhecido). Ponto de atenção: se a manutenção for prestada "
    "como parte de contrato de OBRA de engenharia (ex.: reforma predial completa), a tributação migra para "
    "o Anexo IV; se houver cessão de mão de obra, a empresa fica sujeita a exclusão do Simples Nacional.",
    "média")

# =========================================================================
# 5. MATERIAIS - CLIMATIZAÇÃO
# =========================================================================

add("Materiais - Climatização", "Gás refrigerante R410A - botija 11,35kg (loja 1: Multifrio Shop)",
    961.28, "R$/botija", "https://www.multifrioshop.com/fluidos-refrigerantes/gas-r410a-botija-11-35kg-r410-410a-refrigerante",
    "campo 'price' da página do produto (preço tabela); preço à vista/Pix indicado na página: R$865,15",
    "Confirmado por leitura direta da página.", "alta")
add("Materiais - Climatização", "Gás refrigerante R410A - botija 11,35kg (loja 2: Frigelar, referência de busca)",
    890.00, "R$/botija", "https://www.frigelar.com.br/gas-refrigerante-r410a-eos-cilindro-de-1134kg/p/kit5357",
    "não fetchado diretamente (timeout/erro HTTP2 na sessão); valor obtido via resultado de busca datado desta sessão ('R$ 890,00 no PIX, 7% desconto')",
    "Confiabilidade menor por não termos aberto a página diretamente.", "média")
add("Materiais - Climatização", "Gás refrigerante R410A - botija 11,35/11,3kg (loja 3: RL Refrigeração, referência de busca)",
    None, "R$/botija", "https://www.rlrefrigeracao.com.br/produto/botija-gas-r410a-113kg.html",
    "página retornou HTTP 403 (bloqueio anti-bot) nesta sessão; não foi possível confirmar preço",
    "não encontrado (bloqueio de acesso)", "baixa")
add("Materiais - Climatização", "Gás refrigerante R410A - botija ~11,35kg - MEDIANA das fontes acessadas",
    925.64, "R$/botija", "ver 2 itens acima (Multifrio R$961,28 tabela / R$865,15 Pix; Frigelar ~R$890 Pix)",
    "mediana simples entre R$961,28 e R$890,00", "Mediana de apenas 2 pontos por limitação de acesso a mais lojas nesta sessão.", "média")

add("Materiais - Climatização", "Gás refrigerante R22 - botija 13,6kg (loja 1: Multifrio Shop)",
    1095.72, "R$/botija", "https://www.multifrioshop.com/fluidos-refrigerantes/gas-r22-refrigerante-original-botija-13-6kg-generico",
    "campo 'price' da página (preço tabela); preço à vista/Pix: R$986,15", "Confirmado por leitura direta.", "alta")
add("Materiais - Climatização", "Gás refrigerante R22 - botija 13,6kg (loja 2: Refricenter)",
    866.62, "R$/botija", "https://www.refricenter.com.br/linha-da-gases/fluido-refrigerante-ou-gas-eos-r22-cilindro-13-62-kg",
    "campo 'price' da página", "Confirmado por leitura direta.", "alta")
add("Materiais - Climatização", "Gás refrigerante R22 - botija 13,6kg (loja 3: RL Refrigeração, referência de busca)",
    1013.58, "R$/botija", "https://www.rlrefrigeracao.com.br/produto/gas-r22-cilindro-botija-136kg.html",
    "valor obtido via resultado de busca ('R$1.013,58, ou R$962,90 via Pix'); página retornou 403 ao fetch direto",
    "confiabilidade menor por não termos aberto a página diretamente.", "média")
add("Materiais - Climatização", "Gás refrigerante R22 - botija 13,6kg - MEDIANA das 3 fontes",
    1013.58, "R$/botija", "ver 3 itens acima", "mediana de R$866,62 / R$1.013,58 / R$1.095,72", "", "alta")

add("Materiais - Climatização", "Tubo de cobre 1/4\" - preço por metro (loja: Eletro ABC)",
    14.80, "R$/metro", "https://www.eletroarbc.com.br/produtos/tubo-de-cobre-1-4-para-ar-condicionado-preco-de-1-metro/",
    "preço 'R$14,80' repetido nas variações do produto na página", "Confirmado por leitura direta.", "alta")
add("Materiais - Climatização", "Tubo de cobre 3/8\" - preço por metro",
    None, "R$/metro", "-", "não encontrado com confirmação direta nesta sessão (páginas de hiperfrio.com.br e centraleletrorefrigeracao.com.br retornaram HTTP 403)",
    "ESTIMATIVA: tubos de cobre para refrigeração seguem aproximadamente a proporção de peso/massa linear "
    "entre bitolas; o 3/8\" costuma custar de 1,6 a 2,0x o preço do 1/4\" no varejo especializado. Aplicando "
    "essa razão sobre o valor confirmado de R$14,80/m (1/4\"): estimativa de R$24 a R$30/metro. Confirmar "
    "com fornecedor local antes de orçar.", "baixa")

add("Materiais - Climatização", "Capacitor de partida/permanente para ar-condicionado/compressor (faixa de mercado)",
    "22 a 45 (variação conforme µF e voltagem)", "R$/unidade",
    "https://www.tudoar.com.br/quanto-custa-um-capacitor-de-ar-condicionado ; https://www.friopecas.com.br/pecas-e-servicos/pecas-ar-condicionado/capacitores",
    "tudoar.com.br: 'em 2025, os preços variam de R$22 a R$42'; friopecas.com.br: preços de catálogo entre "
    "R$11,04 e R$39,57 (capacitores diversos, campo 'price' de vários SKUs na página)",
    "Faixa ampla por variar muito com capacitância (µF) e tensão (250V/370V/440V). Não foi possível isolar "
    "um único SKU 'padrão de mercado' (ex.: 35+5µF 440V) com preço único confiável nesta sessão.", "média")

add("Materiais - Climatização", "Termostato para geladeira/freezer (faixa de mercado, loja: Casa Eletropeças)",
    "38,98 a 86,98 (conforme marca/modelo)", "R$/unidade", "https://www.casaeletropecas.com.br/pecas-geladeira/termostato",
    "preços R$38,98 / R$54,98 / R$70,98 / R$86,98 encontrados na listagem de produtos da página",
    "Confirmado por leitura direta; valor típico de entrada ~R$39-55.", "alta")

add("Materiais - Climatização", "Compressor hermético pequeno (ref. 1/4+HP, R134a, para geladeira/freezer doméstico)",
    393.25, "R$/unidade", "https://www.eletrofrigor.com.br/produto/compressor-1-4-hp-r134a-220v-1f-reciproco-hermetico-embraco-emr80hlr-6975",
    "valor obtido via resultado de busca ('Embraco EMR80HLR 1/4+HP a R$393,25 à vista/Pix, 3% desconto'); "
    "página retornou 404 ao fetch direto nesta sessão (produto pode ter mudado de URL)",
    "Confiabilidade menor por não termos confirmado com fetch direto da página do produto.", "média")

add("Materiais - Climatização", "Gás refrigerante R134a - botija 13,6/13kg (loja: Geofrio)",
    947.35, "R$/botija", "https://geofrio.com.br/produtos/gas-refrigerante-r134-ar-condicionado-automotivo-botija-13kg/",
    "campo 'price' da página (preço tabela); preço promocional na página: R$899,98",
    "Confirmado por leitura direta. Nota: este produto específico é rotulado para uso automotivo, mas o gás "
    "R134a é o mesmo utilizado em refrigeração comercial/doméstica de pequeno porte.", "alta")
add("Materiais - Climatização", "Gás refrigerante R134a - botija 13,6kg (loja 2: DSfrio, referência de busca)",
    980.00, "R$/botija", "https://www.dsfrio.com.br/gas-refrigerante-r134a-botija-cilindro-de-136kg",
    "valor obtido via resultado de busca ('R$980,00 com desconto, de R$1.080,00; R$931,00 via Pix')",
    "confiabilidade menor por não termos aberto a página diretamente (bloqueio 403 ao fetch).", "média")

add("Materiais - Climatização", "Gás refrigerante R404A - botija 10,9kg (loja: Eletrofrigor, referência de busca)",
    725.55, "R$/botija", "https://www.eletrofrigor.com.br/produto/gas-fluido-refrigerante-r404a-botija-10-9kg-friven-1712",
    "valor obtido via resultado de busca ('Friven R404A 10,9kg R$725,55 com 3% desconto Pix'); página "
    "retornou HTTP 404 ao fetch direto nesta sessão",
    "confiabilidade menor por não termos confirmado com fetch direto.", "média")
add("Materiais - Climatização", "Gás refrigerante R404A - botija 10,9kg (loja 2: Loja Mincarone/Genetron, referência de busca)",
    949.50, "R$/botija", "https://www.lojamincarone.com.br/MLB-3206717017-botija-de-gas-fluido-refrigerante-r404a-genetron-10896kg-_JM",
    "valor obtido via resultado de busca; página não pôde ser fetchada nesta sessão (erro de certificado SSL)",
    "confiabilidade menor.", "média")

add("Materiais - Climatização", "Kit de limpeza bactericida/limpa-serpentina para ar-condicionado (1L)",
    19.90, "R$/unidade", "https://www.refritron.com.br/material-de-instalacao-e-manutencao/produtos-de-limpeza-e-higienizacao",
    "valor obtido via resultado de busca ('Refritron: bactericida higienizador 1L a partir de R$19,90')",
    "Referência de entrada de linha; kits mais completos (com espuma + bactericida + pastilha) tendem a "
    "custar mais (não quantificado nesta sessão). Página não fetchada diretamente.", "baixa")

add("Materiais - Climatização", "Isolamento térmico tubular (tubo/calha para tubulação de cobre)",
    None, "R$/metro", "-", "não encontrado nesta sessão", "ESTIMATIVA sem fonte de mercado consultada: faixa "
    "usual de mercado para isolamento elastomérico 1/4\"-3/8\" fica entre R$3 e R$8/metro. Recomenda-se "
    "cotação direta antes de orçar.", "baixa")

add("Materiais - Climatização", "Suporte/base para unidade condensadora (split)",
    None, "R$/unidade", "-", "não encontrado nesta sessão",
    "ESTIMATIVA sem fonte de mercado consultada: suportes de parede em L para condensadoras pequenas/médias "
    "costumam variar entre R$60 e R$150 conforme capacidade de carga. Recomenda-se cotação direta.", "baixa")

add("Materiais - Climatização", "Filtro (ar-condicionado/refrigeração)",
    None, "R$/unidade", "-", "não encontrado com item específico nesta sessão",
    "ESTIMATIVA sem fonte de mercado consultada: filtros secadores de linha de líquido para pequenos sistemas "
    "costumam variar entre R$15 e R$60 conforme diâmetro/capacidade. Recomenda-se cotação direta.", "baixa")

# =========================================================================
# 6. MATERIAIS - ILUMINAÇÃO PÚBLICA
# =========================================================================

add("Materiais - Iluminação pública", "Reator para vapor de sódio 70W, externo, galvanizado (fabricante: Demape)",
    70.80, "R$/unidade", "https://demape.com.br/produto/reator-vapor-de-sodio-70w-externo-galvanizado/",
    "preço exibido na página do produto", "Confirmado por leitura direta (fabricante nacional).", "alta")
add("Materiais - Iluminação pública", "Reator para vapor de sódio 150W, externo, galvanizado (fabricante: Demape)",
    91.91, "R$/unidade", "https://demape.com.br/produto/reator-vapor-de-sodio-150w-externo-galvanizado-ence/",
    "preço exibido na página do produto", "Confirmado por leitura direta.", "alta")
add("Materiais - Iluminação pública", "Reator para vapor de sódio 70W (loja 2: VLP Comercial, referência de busca)",
    36.80, "R$/unidade", "https://www.vlpcomercial.com.br/iluminacao/reatores/eletromagnetico/para-lampada-sodio.html",
    "valor obtido via resultado de busca", "confiabilidade menor por não termos aberto a página diretamente.", "baixa")

add("Materiais - Iluminação pública", "Lâmpada vapor de sódio 70W/150W tubular ou ovóide E27/E40 (faixa de mercado)",
    "24 a 59 (conforme potência)", "R$/unidade",
    "https://www.ourolux.com.br/produtos/iluminac-o/lampadas-de-descarga/vapor-de-sodio.html",
    "resultado de busca: 'preços a partir de aproximadamente R$24,00 a R$58,88 para diferentes wattagens "
    "(70W, 150W, 250W, 400W, 600W, 1000W)'", "Página não fetchada diretamente; faixa ampla e não específica só para 70/150W.", "baixa")

add("Materiais - Iluminação pública", "Relé fotoelétrico/fotocélula para iluminação pública (faixa de mercado)",
    "17,55 a 188,48 (grande variação conforme modelo/marca)", "R$/unidade",
    "https://lista.mercadolivre.com.br/rele-fotocelula-para-iluminacao-publica",
    "resultado de busca consolidando ofertas de Mercado Livre (marcas Qualitronix, Exatron, MarGirius, "
    "Techna, Proeletronic)", "Faixa muito ampla; recomenda-se cotação de um modelo específico (ex.: "
    "relé bivolt padrão NEMA) antes de orçar. Página de busca não fetchada diretamente (proteção anti-bot).", "baixa")

add("Materiais - Iluminação pública", "Luminária LED pública 60W-100W (faixa de mercado, referência)",
    "acima de R$100 até acima de R$250, conforme potência/marca", "R$/unidade",
    "https://www.sustentaled.com.br/ ; https://lista.mercadolivre.com.br/luminaria-publica-led-60w",
    "resultado de busca: 'faixa de preços que variam de até R$100 até acima de R$250' (Mercado Livre, 60W)",
    "Apenas referência ampla, conforme solicitado no escopo ('só como referência'); páginas de produto do "
    "Sustenta LED retornaram HTTP 403 ao fetch direto nesta sessão.", "baixa")

add("Materiais - Iluminação pública", "Braço para luminária pública, 1m, 2 polegadas, reto (fabricante/loja: Irmãos Soares)",
    84.90, "R$/unidade", "https://www.irmaossoares.com.br/braco-para-luminaria-publica-1m-2-polegadas-reto-eletrometa/p",
    "campo 'price' da página do produto", "Confirmado por leitura direta.", "alta")

add("Materiais - Iluminação pública", "Cabo e conectores para rede de iluminação pública",
    None, "R$/metro ou R$/unidade", "-", "não encontrado item específico nesta sessão (tempo de pesquisa esgotado)",
    "Ver itens de 'Elétrica predial' abaixo (cabo 2,5mm² e cabo de cobre nu) como proxy de custo de cabo "
    "para redes de baixa tensão; conectores de derivação (tipo cunha/perfurante) tipicamente custam entre "
    "R$3 e R$12/unidade no varejo elétrico (ESTIMATIVA sem fonte cotada nesta sessão).", "baixa")

# =========================================================================
# 7. MATERIAIS - ELÉTRICA PREDIAL
# =========================================================================

add("Materiais - Elétrica predial", "Disjuntor DIN unipolar 25A/32A curva C (faixa de mercado, referência de busca)",
    "7,76 a 9,19", "R$/unidade",
    "https://www.disfer.com.br/disjuntores ; https://www.pjneblina.com.br/produto/disjuntor-mini-din-unipolar-25a-curva-c-3ka-230400v-sdd61c25-steck/5026776",
    "resultado de busca: 'Disfer: disjuntor unipolar DIN 32A Elitek R$7,76 (R$7,37 Pix), 25A também R$7,76'; "
    "'PJ Neblina: disjuntor mini DIN unipolar 25A R$9,19'",
    "Não conseguimos confirmar com fetch direto (página do Santil não expôs preço no HTML estático; possível "
    "carregamento via JS). Faixa de disjuntor unipolar simples de linha residencial/comercial leve.", "média")

add("Materiais - Elétrica predial", "Cabo flexível 2,5mm² 750V - rolo de 100 metros (loja: Casa do Eletricista SC)",
    236.88, "R$/rolo de 100m", "https://www.casadoeletricistasc.com.br/cabo-flexivel-750v-2-5mm2-antichama-preto-corfio-rolo-100m/p/kit611",
    "campo 'price' da página (preço tabela); variações de preço à vista/parcelado na mesma página: R$229,77 / R$234,51",
    "Confirmado por leitura direta.", "alta")
add("Materiais - Elétrica predial", "Cabo flexível 2,5mm² 750V - rolo de 100 metros (loja 2: ACS Materiais Elétricos, referência de busca)",
    234.90, "R$/rolo de 100m", "https://www.acsmateriaiseletricos.com.br/produtos/cabo-flexivel-25mm-750v-antichama-azul-100-metros/",
    "valor obtido via resultado de busca", "página não fetchada diretamente nesta sessão.", "média")
add("Materiais - Elétrica predial", "Cabo flexível 2,5mm² - rolo de 100m - MEDIANA de 2 fontes",
    235.89, "R$/rolo de 100m", "ver 2 itens acima", "mediana simples de R$236,88 e R$234,90", "", "média")

add("Materiais - Elétrica predial", "Tomada elétrica 2P+T 10A/20A (padrão NBR 14136)",
    None, "R$/unidade", "-", "não encontrado com confirmação direta nesta sessão (tempo de pesquisa esgotado)",
    "ESTIMATIVA sem fonte cotada: tomadas de embutir padrão novo (módulo + placa) costumam variar entre "
    "R$8 e R$25 conforme linha (popular a intermediária). Recomenda-se cotação direta.", "baixa")

add("Materiais - Elétrica predial / SPDA", "Cabo de cobre nu 35mm² (7 fios) - preço por metro (loja: Cetti Materiais Elétricos)",
    36.76, "R$/metro", "https://cetti.com.br/p/cabo-de-cobre-nu-35-mm2-com-7-fios-solidos-para-aterramento-eletrico-1-metro/",
    "campo 'price' da página do produto", "Confirmado por leitura direta. Preço fortemente atrelado à cotação do cobre (LME), variável.", "alta")
add("Materiais - Elétrica predial / SPDA", "Cabo de cobre nu 50mm² - preço por metro",
    None, "R$/metro", "https://www.lojacentraleletrica.com.br/produto/cabo-de-cobre-nu-50mm-para-aterramento",
    "não encontrado (página não fetchada com sucesso nesta sessão)",
    "ESTIMATIVA: proporcionalmente ao peso de cobre (50/35 = 1,43x), a partir do valor confirmado de "
    "R$36,76/m para 35mm² => estimativa de R$45 a R$55/metro para 50mm². Confirmar com fornecedor.", "baixa")

add("Materiais - Elétrica predial / SPDA", "Haste de aterramento tipo Copperweld 5/8\" x 2,40m (loja: Wermar)",
    36.11, "R$/unidade", "https://www.wermar.com.br/materiais-eletricos/haste-copperweld-para-aterramento-com-conector-2-40m",
    "um dos preços 'R$36,11' encontrados na página (outra variação/kit na mesma página: R$42,48)",
    "Confirmado por leitura direta, mas página lista mais de um SKU/variação (com/sem conector); valor "
    "reportado é o menor encontrado no HTML da página.", "média")

# =========================================================================
# 8. VEÍCULOS
# =========================================================================

add("Veículos", "Locação de caminhão munck/guindauto com operador - valor hora (referência nacional, mínimo 3h)",
    250.00, "R$/hora", "https://www.munk.com.br/locacao-de-caminhao-munck/locacao-de-caminhao-munck-com-operador/valor-de-locacao-de-caminhao-munck-por-hora-osasco",
    "resultado de busca: 'para serviços cobrados por hora, valor médio de R$250,00/hora, com mínimo de 3 horas de contratação'",
    "Fonte é de locadora de São Paulo (Osasco), não específica de GO/DF. GOINFRA (Goiás), DNIT/SICRO e "
    "AGETOP têm tabelas oficiais de custo horário de equipamento, mas os domínios goinfra.go.gov.br e "
    "sicro.dnit.gov.br ficaram bloqueados pelo proxy de rede nesta sessão (todas as tentativas de acesso "
    "retornaram falha de túnel). Página de origem não fetchada diretamente (blog sem números na versão "
    "estática do HTML).", "baixa")

add("Veículos", "Locação de caminhão munck de grande porte com operador - valor diária (referência nacional)",
    "3.500 a 7.000", "R$/dia", "https://www.csmmuncksp.com.br/blog/categorias/artigos/quanto-custa-a-locacao-de-um-munck-entenda-os-fatores-que-influenciam-o-preco",
    "resultado de busca: 'preços para aluguel de muncks de grande porte normalmente ficam entre R$3.500 e "
    "R$7.000 por dia'", "Mesma ressalva do item acima (fonte SP, não GO/DF específica).", "baixa")

add("Veículos", "SINAPI - Guindauto hidráulico 6.500kg/momento 5,8tm (caminhão toco 9.700kg, 160cv) - custo do insumo ÓLEO DIESEL na composição (não é o custo horário total do equipamento)",
    147.19, "R$/hora", "https://orcamentor.com/composicao/91633/",
    "composição SINAPI 91633 (base 07/2026, não desonerado): 'GUINDAUTO HIDRÁULICO... MATERIAIS NA "
    "OPERAÇÃO' = consumo de óleo diesel 22,37 L/h × R$6,58/L = R$147,19/h",
    "ATENÇÃO: este é APENAS o componente de combustível ('materiais na operação') da composição SINAPI, "
    "não o Custo Horário Produtivo (CHP) total do equipamento (que também soma depreciação, juros, seguros "
    "e manutenção). O CHP total completo não foi localizado nesta sessão dentro do prazo disponível - "
    "recomenda-se consultar a composição completa (código pai que referencia 91633) no SINAPI/GOINFRA "
    "diretamente.", "média")

add("Veículos", "Custo por quilômetro rodado - veículo leve (utilitário/pickup) - faixa de mercado 2026",
    "0,80 a 1,50", "R$/km", "https://valorfinal.com.br/calculadora-custo-por-km",
    "resultado de busca: 'na prática, o mercado pratica valores entre R$0,80 e R$1,50 por km em 2026 "
    "(combustível + manutenção + depreciação parcial)'",
    "ESTIMATIVA/faixa de referência, não uma tabela oficial. Página não fetchada diretamente (calculadora "
    "interativa, sem tabela estática de valores no HTML). Premissas típicas citadas pela fonte: consumo "
    "urbano médio Inmetro/Conpet, 15.000km/ano, seguro ~3,5% do valor FIPE, depreciação conforme Tabela "
    "FIPE.", "baixa")

# =========================================================================
# 9. COMBUSTÍVEIS (ANP)
# =========================================================================

fonte_anp = "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/arquivos-lpc/2026/revendas_lpc_2026-09-20_2026-09-26.xlsx"

add("Combustíveis - ANP (dado primário oficial)", "Gasolina comum - preço médio de revenda em Goiás",
    6.672, "R$/litro", fonte_anp,
    "Planilha oficial ANP 'Levantamento de Preços de Combustíveis', semana 20/09/2026 a 26/09/2026, filtro "
    "ESTADO='GOIAS', PRODUTO='GASOLINA COMUM'; média de 179 postos pesquisados (mediana: R$6,77/L; mín "
    "R$5,99; máx R$6,99)",
    "Cálculo próprio a partir dos dados brutos por posto revendedor da planilha oficial da ANP (não é um "
    "valor já publicado pronto, e sim calculado por nós a partir do arquivo primário).", "alta")

add("Combustíveis - ANP (dado primário oficial)", "Diesel S500 (comum) - preço médio de revenda em Goiás",
    6.664, "R$/litro", fonte_anp,
    "mesma planilha, filtro PRODUTO='DIESEL S500'; n=105 postos (mediana: R$6,59/L; mín R$5,99; máx R$7,95)",
    "Cálculo próprio a partir dos dados brutos da planilha oficial ANP.", "alta")

add("Combustíveis - ANP (dado primário oficial)", "Diesel S10 - preço médio de revenda em Goiás",
    7.232, "R$/litro", fonte_anp,
    "mesma planilha, filtro PRODUTO='DIESEL S10'; n=139 postos (mediana: R$7,19/L; mín R$6,39; máx R$7,99)",
    "Cálculo próprio a partir dos dados brutos da planilha oficial ANP.", "alta")

add("Combustíveis - ANP (dado primário oficial)", "Etanol hidratado - preço médio de revenda em Goiás",
    4.309, "R$/litro", fonte_anp,
    "mesma planilha, filtro PRODUTO='ETANOL'; n=175 postos (mediana: R$4,47/L)",
    "Cálculo próprio a partir dos dados brutos da planilha oficial ANP.", "alta")

add("Combustíveis - ANP (dado primário oficial)", "GLP (botijão 13kg) - preço médio de revenda em Goiás",
    113.72, "R$/botijão 13kg", fonte_anp,
    "mesma planilha, filtro PRODUTO='GLP'; n=153 postos/revendas (mediana: R$115,00)",
    "Cálculo próprio a partir dos dados brutos da planilha oficial ANP.", "alta")

add("Combustíveis - ANP (agregador, cross-check)", "Gasolina comum - preço médio de revenda em Goiás (cross-check)",
    6.499, "R$/litro", "https://www.combustiveis-anp.com.br/estado/go",
    "'considerando estas cidades, a gasolina comum vai de R$5,860/L (Jataí) a R$6,840/L (Trindade)... com "
    "média de R$6,499/L' (Setembro/2026, 17 cidades)",
    "Fonte secundária (agregador) baseada nos mesmos dados semanais da ANP, mas com amostra/metodologia "
    "de agregação diferente da nossa (média por cidade, não por posto); usada apenas como conferência "
    "cruzada do valor primário calculado acima (R$6,672/L).", "média")

# =========================================================================
# 10. GARANTIA CONTRATUAL E PRAZO DE PAGAMENTO
# =========================================================================

add("Garantia contratual", "Seguro-garantia - prêmio anual típico (percentual sobre o valor garantido)",
    "0,40% a 2,00% ao ano (uso comum: 0,5% a 1,5% a.a.)", "% ao ano sobre valor garantido",
    "https://effecti.com.br/seguro-garantia-licitacoes-publicas/",
    "resultado de busca: 'o preço do seguro garantia licitação é de cerca de 0,5% a 1,5% do valor da "
    "garantia ao ano... outra fonte menciona 0,40% a 2,00% ao ano, variando conforme o perfil da empresa'",
    "Página não fetchada diretamente nesta sessão (artigo comercial de corretora/insurtech); valores "
    "consistentes com o que é reportado por múltiplas seguradoras/corretoras do mercado brasileiro de "
    "seguro-garantia. Faixa exigida de garantia sobre o valor do contrato: até 5% (padrão, art. 96 da Lei "
    "14.133/2021), podendo chegar a 10% em contratos de maior complexidade/risco.", "média")

add("Garantia contratual / Lei 14.133/2021", "Percentual-padrão de garantia contratual exigível",
    "até 5% do valor do contrato (podendo chegar a 10% em obras/serviços de maior complexidade e risco, "
    "conforme art. 99, e a até 30% em contratos de grande vulto com cláusula de retomada, art. 102)",
    "%", "https://effecti.com.br/seguro-garantia-licitacoes-publicas/",
    "resultado de busca, citando a Lei nº 14.133/2021, art. 96 e seguintes",
    "Não acessamos o texto integral da Lei 14.133/2021 diretamente nesta sessão (planalto.gov.br bloqueado "
    "pelo proxy); percentuais reportados são consistentes com o conhecimento consolidado sobre a Lei "
    "14.133/2021 (arts. 96-102).", "média")

add("Prazo de pagamento", "Prazo de pagamento na Lei 14.133/2021 (liquidação + pagamento)",
    "não há teto único nacional fixado por lei; prática comum reportada: até 15 dias úteis para liquidação "
    "da despesa (a contar do recebimento da nota fiscal/instrumento de cobrança) + até 10 dias úteis para "
    "pagamento (a contar da liquidação) - total prático de referência de ~25 dias úteis",
    "dias úteis", "https://metalicitacoes.com.br/nova-lei-de-licitacoes-14133/",
    "resultado de busca: 'a Lei 14.133/2021 não fixou um teto único de dias para toda a Administração "
    "Pública; prevalecem as regras locais, e a cláusula contratual continua sendo a referência', citando "
    "os prazos usuais de 15 dias úteis (liquidação) e 10 dias úteis (pagamento) mencionados por fontes "
    "jurídicas especializadas",
    "NÃO conseguimos confirmar o texto literal do art. 141 da Lei 14.133/2021 nesta sessão (planalto.gov.br "
    "bloqueado pelo proxy de rede, e o portal licitacoesecontratos.tcu.gov.br retornou apenas uma página "
    "de desafio anti-bot/JS sem conteúdo). O ponto mais importante e confirmado por múltiplas fontes é que "
    "A LEI NÃO FIXA UM PRAZO MÁXIMO ÚNICO NACIONAL - o edital/contrato de cada órgão é que define o prazo "
    "concreto. Prática municipal usual observada no mercado: 30 dias corridos após liquidação/atesto da "
    "nota fiscal.", "baixa")

# Write JSON
out = {
    "meta": {
        "titulo": "Referências de custo de mercado - estudo de margem em licitações de manutenção, Goiás, 2026",
        "data_acesso_padrao": DATA_ACESSO,
        "gerado_em": "2026-09-27",
        "observacao_geral": (
            "Levantamento realizado com acesso à internet via curl/WebSearch a partir de um ambiente com "
            "proxy de egress restritivo (allowlist de domínios). Diversos domínios oficiais de primeira "
            "escolha (planalto.gov.br, sinduscongoias.com.br, seacons.com.br, editais.uff.br, "
            "goinfra.go.gov.br, sicro.dnit.gov.br, simelgo.com.br, mediador.trabalho.gov.br, "
            "licitacoesecontratos.tcu.gov.br) ficaram bloqueados pelo proxy de rede desta sessão ou por "
            "proteção anti-bot (Cloudflare/PerimeterX) e não puderam ser lidos diretamente; nesses casos "
            "foram usadas fontes alternativas (espelhos, sindicatos parceiros, agregadores especializados, "
            "resultados de busca) e isso está sinalizado em cada registro, com confiabilidade reduzida "
            "(média/baixa) quando aplicável. Nenhum valor foi inventado: onde não foi possível confirmar um "
            "número, o campo 'valor' é null e o campo 'observacao' registra 'não encontrado' com a proposta "
            "de estimativa e a premissa usada, OU o item foi deixado como estimativa marcada explicitamente."
        ),
    },
    "registros": registros,
}

with open("/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado/custos/custos/referencias.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("Total de registros:", len(registros))
