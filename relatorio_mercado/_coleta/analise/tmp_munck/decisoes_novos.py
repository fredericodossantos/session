# -*- coding: utf-8 -*-
import json

novos = {
 "00394452000103_2026_14034": (False, "fora_escopo", "Aquisição de materiais/insumos/alimentos/medicamentos veterinários para efetivo animal do Exército; falso positivo de indexação, sem relação com munck."),
 "01561372000150_2026_2": (True, None, "RECLASSIFICADO de fornecimento_puro: obra pequena (R$200 mil, abaixo do limiar de obra grande) de implantação de postes ornamentais com fornecimento de material E mão de obra (objeto expresso); mesmo padrão do caso GO Vila Propício, dentro do escopo explícito de 'implantação de postes'."),
 "01800242000122_2026_16": (True, None, "Locação pura de caminhão munck com motorista e cesto aéreo isolado, por hora (983h); núcleo do escopo."),
 "02396166000102_2025_1": (False, "obra_grande", "Obra de infraestrutura urbana (pavimentação asfáltica, calçadas, meio-fio, sinalização) com implantação de 34 postes de iluminação como item incidental; valor R$9,06 milhões > limiar de R$1,5 milhão -- confirma exclusão por obra_grande."),
 "03342938000188_2025_99": (False, "fornecimento_puro", "Aquisição e instalação de poliguindaste duplo articulado (guincho de basculamento para caçambas estacionárias tipo Brooks) em caminhão já existente da prefeitura; equipamento de guincho de caçamba (diferente do guindauto/munck de içamento), e é aquisição de bem, não locação de serviço."),
 "03354560000132_2025_58": (True, None, "RECLASSIFICADO de fornecimento_puro: obra pequena (R$197 mil) de implantação/ornamentação de postes com item explícito de 'MÃO DE OBRA' separado do material; abaixo do limiar de obra grande, dentro do escopo de 'implantação de postes'."),
 "03741683000126_2025_22": (True, None, "Já classificado corretamente pela heurística (item corretamente codificado como Serviço): implantação de postes ornamentais com luminárias LED, obra pequena (R$438 mil, abaixo do limiar)."),
 "03903176000141_2026_1": (True, None, "Locação pura de caminhão munck/guindauto de 15 toneladas, por hora (360h); núcleo do escopo, maior capacidade que a maioria dos casos de GO."),
 "03979663000198_2026_162": (False, "fornecimento_puro", "Aquisição definitiva de containers marítimos adaptados prontos para uso; içamento é apenas parte da logística de instalação do bem comprado, não um serviço de munck contratado à parte."),
 "15410665000140_2026_8": (False, "fora_escopo", "Implantação de rede de distribuição de energia elétrica em média tensão (13,8kV) com transformadores para conjunto habitacional -- é obra de engenharia elétrica de rede/subestação, não serviço de munck ou substituição pontual de postes de iluminação; reclassificado de incluído (heurística) para excluído."),
 "17058108000138_2026_75": (False, "fora_escopo", "Aquisição de blocos de concreto para muro de gabião e material de pavimentação; 'alça de içamento' é uma característica do produto (alça no próprio bloco), não um serviço de içamento com munck -- falso positivo."),
 "18008920000111_2026_38": (False, "fornecimento_puro", "Aquisição de poliguindaste simples e caçambas estacionárias (equipamento de guincho para caçambas de entulho, diferente do guindauto/munck de içamento); compra de bem, não locação de serviço."),
 "18188219000121_2026_331": (True, None, "Locação de caminhão munck de GRANDE porte (45 t/m, lança 20m, caminhão 3 eixos, PBT 23t), por hora (2 itens: ampla concorrência 450h + cota ME/EPP 150h); núcleo do escopo -- maior capacidade da amostra."),
 "18245167000188_2026_106": (False, "fornecimento_puro", "Aquisição de materiais/acessórios de içamento (cintas de amarração, manilhas, cintas de elevação) -- insumos de apoio, não locação de caminhão munck."),
 "18409227000150_2026_81": (False, "fornecimento_puro", "Aquisição de caminhão novo (chassi 8x4/6x4) equipado com prancha, guincho e guindaste hidráulico tipo Munck; compra de bem, não locação de serviço."),
 "18428847000137_2026_101": (False, "equipamento_alto", "Obra de construção/complementação de UBS (movimentação de terra, muro de arrimo, pavimentação, poço artesiano, CFTV, gerador a diesel); postes de iluminação externa são item incidental dentro de uma obra predial geral, não serviço de munck."),
 "25063983000136_2026_8": (False, "fora_escopo", "Obra de urbanização geral (pavimentação, calçadas, meios-fios, paisagismo, mobiliário urbano) com sistema de iluminação pública/postes como item incidental dentro de um contrato único de obra civil; reclassificado de incluído (heurística) para excluído -- foco não é munck nem poste isolado."),
 "25269069000146_2026_37": (True, None, "RECLASSIFICADO parcialmente de fornecimento_puro: RP de locação de frota mista (escavadeira+retroescavadeira+munck), mas o item 3 é especificamente 'LOCAÇÃO DE CAMINHÃO MUNCK' por hora, com vencedor e preço próprios (100h, R$290,00/h estimado -> R$288,00/h homologado) -- disputável isoladamente; itens mal codificados como material pelo órgão."),
 "37226644000102_2026_95": (False, "fornecimento_puro", "Aquisição de implementos agrícolas (calcareadeira, carreta basculante, guincho agrícola hidráulico para big bag); guincho agrícola é equipamento distinto do guindauto/munck -- fora do escopo."),
}

antigos = json.load(open('/tmp/decisoes_munck.json'))
todos = {**antigos, **novos}
assert len(todos) == 46, len(todos)
json.dump(todos, open('/tmp/claude-0/-home-user-session/d24dffd9-bbbf-5219-be82-f54211868e67/scratchpad/mercado/analise/tmp_munck/decisoes_completas.json','w'), ensure_ascii=False, indent=1)
print("OK, total decisoes:", len(todos))
