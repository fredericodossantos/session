"""Interface web local e controlada para consultas ao monitor."""
from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import logging
import os
import re
import threading
import tempfile
import unicodedata
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .api_client import ClientePNCP
from .acesso import AcessoNegado, AutenticadorCloudflare, ConfiguracaoAcessoInvalida, Identidade
from .coleta import Parametros, executar
from .consultas import ConsultaOcupada, ConsultaError, Consultas, ESTADOS_ATIVOS
from .catalogo import carregar_catalogo, migrar_filtros_v1
from .config import carregar
from .filtros import SITUACOES_ME_EPP
from .persistencia import Historico
from .relatorio import _url_web, publicar

log = logging.getLogger(__name__)
MODALIDADES = {
    4: "Concorrência eletrônica",
    5: "Concorrência presencial",
    6: "Pregão eletrônico",
    7: "Pregão presencial",
    8: "Dispensa eletrônica",
    9: "Inexigibilidade",
    12: "Credenciamento",
}
AREAS_ATUACAO = {
    "instalacao": "Instalação",
    "manutencao": "Manutenção",
    "fornecimento": "Fornecimento / aquisição",
    "pmoc": "PMOC",
    "refrigeracao": "Refrigeração",
    "pecas": "Peças e insumos",
}


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return value


def _buscas_dir(state: "Estado", owner_id: str = "local") -> Path:
    return _diretorio_usuario(state, "buscas", owner_id)


def _diretorio_usuario(state: "Estado", secao: str, owner_id: str = "local") -> Path:
    raiz = Path(state.config["saida"]["pasta"])
    if state.modo_acesso == "cloudflare":
        pasta_id = hashlib.sha256(owner_id.encode("utf-8")).hexdigest()
        diretorio = raiz / "usuarios" / pasta_id / secao
    elif secao == "buscas":
        diretorio = raiz / "buscas"
    else:
        diretorio = raiz / secao
    diretorio.mkdir(parents=True, exist_ok=True)
    return diretorio


def _slug_busca(nome: str) -> str:
    base = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9_-]+", "-", base).strip("-_").lower()
    return (base or "busca")[:80] + ".json"


def _preparar_compatibilidade_v1(payload: dict[str, Any]) -> None:
    compatibilidade = payload.get("compatibilidade_v1")
    if not compatibilidade:
        return
    if not isinstance(compatibilidade, dict):
        raise ValueError("Os filtros antigos estão malformados.")
    original = compatibilidade.get("filtro_original")
    if not isinstance(original, dict):
        original = {"schema_version": 1,
                    "areas": compatibilidade.get("areas", payload.get("areas", [])),
                    "palavras_chave": payload.get("palavras_chave", [])}
    payload["compatibilidade_v1"] = migrar_filtros_v1(original)["compatibilidade_v1"]


def _arquivo_busca(state: "Estado", nome_arquivo: str, owner_id: str = "local") -> Path:
    nome = Path(unquote(nome_arquivo)).name
    if nome != nome_arquivo or not re.fullmatch(r"[A-Za-z0-9_-]+\.json", nome):
        raise ValueError("Nome de busca inválido.")
    return _buscas_dir(state, owner_id) / nome


class Estado:
    def __init__(self, config_path: Path, modo_acesso: str = "local"):
        self.config_path = config_path
        self.config = carregar(config_path)
        self.modo_acesso = modo_acesso
        if modo_acesso not in {"local", "cloudflare"}:
            raise ConfiguracaoAcessoInvalida("O modo de acesso deve ser local ou cloudflare.")
        self.autenticador = None
        if modo_acesso == "cloudflare":
            acesso = self.config.get("acesso", {})
            equipe = os.environ.get("CF_ACCESS_TEAM_DOMAIN", acesso.get("team_domain", ""))
            audiencia = os.environ.get("CF_ACCESS_AUD", acesso.get("audience", ""))
            self.autenticador = AutenticadorCloudflare(equipe, audiencia)
        caminho_catalogo = self.config.get("catalogo_areas")
        if caminho_catalogo:
            caminho_catalogo = Path(caminho_catalogo)
            if not caminho_catalogo.is_absolute():
                caminho_catalogo = config_path.resolve().parent / caminho_catalogo
            self.catalogo = carregar_catalogo(caminho_catalogo)
        else:
            self.catalogo = carregar_catalogo()
        consulta_cfg = self.config.get("consulta_web", {})
        self.consultas = Consultas(
            self.config["saida"]["banco"],
            timeout_s=consulta_cfg.get("timeout_segundos", 120),
            max_tentativas=consulta_cfg.get("max_tentativas", 60),
        )
        self.lock = threading.RLock()
        self.running = False
        self.status: dict[str, Any] = {"fase": "parado", "mensagem": "Escolha as modalidades para começar."}
        self.results: list[dict[str, Any]] = []
        self.files: dict[str, str] = {}

    def identidade(self, headers: Any) -> Identidade:
        if self.modo_acesso == "cloudflare":
            return self.autenticador.autenticar(headers)
        return Identidade(email="", subject="local", claims={})

    def consulta_mais_recente(self, owner_id: str) -> dict[str, Any] | None:
        historico = self.consultas.historico(limite=1, owner_id=owner_id)
        return historico[0] if historico else None

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {"running": self.running, "status": _json_value(self.status),
                    "results": _json_value(self.results), "files": self.files.copy()}


def _page(user_email: str = "") -> str:
    usuario = html.escape(user_email.strip()) if user_email.strip() else "Acesso local"
    logout = '<a href="/cdn-cgi/access/logout">Sair</a>' if user_email.strip() else ''
    return r'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Monitor de licitações — Goiás</title>
<style>
:root{font:15px system-ui,sans-serif;color:#17202a;background:#f3f5f7}*{box-sizing:border-box}body{margin:0}
header{background:#123b5d;color:#fff;padding:18px 22px}header a{color:#fff;margin-left:14px;font-weight:700}.topbar{display:flex;justify-content:space-between;gap:18px;align-items:center;flex-wrap:wrap}.usuario{font-size:.9rem;opacity:.95}.menu{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.menu a{background:#205579;border-radius:6px;padding:7px 11px;margin:0;font-size:.9rem}.menu a:hover{background:#2d6b95}main{max-width:1100px;margin:auto;padding:18px}
.painel,.card{background:#fff;border:1px solid #d9e0e7;border-radius:10px;padding:16px;margin-bottom:14px;box-shadow:0 2px 5px #0000000b}
h1{margin:0;font-size:1.25rem}h2{font-size:1rem;margin:0 0 12px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
label{display:block;font-weight:600;margin-bottom:5px}input,select{width:100%;padding:9px;border:1px solid #bcc8d3;border-radius:6px;font:inherit}
.checks{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:7px}.checks label{font-weight:400;background:#f7f9fb;padding:8px;border-radius:6px}
.checks input{width:auto;margin-right:7px}.acoes{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:14px}
.grupo-acoes{margin-top:8px}.grupo-acoes button{padding:6px 10px;background:#e7eef5;color:#174d70;font-size:.85rem}
button{border:0;border-radius:6px;padding:10px 16px;background:#0b6eaa;color:#fff;font-weight:700;cursor:pointer}button:disabled{opacity:.5;cursor:wait}
#mensagem{color:#425466}.barra{height:8px;background:#dde5ec;border-radius:9px;overflow:hidden}.barra i{display:block;width:35%;height:100%;background:#0b87c9;animation:pulse 1.2s infinite alternate}@keyframes pulse{to{width:85%}}
.muted{color:#5f6c78;font-size:.9rem}.obj{font-weight:650}.meta{display:flex;gap:10px;flex-wrap:wrap;color:#526273;font-size:.9rem}.links a{margin-right:14px;color:#075ca8;font-weight:650}
.resumo-local{margin-top:10px;border-top:1px solid #e4e9ee;padding-top:9px}.resumo-local dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;font-size:.9rem}.resumo-local dt{color:#5f6c78}.resumo-local dd{margin:0}.resumo-local summary{cursor:pointer;color:#075ca8;font-weight:700}
.badge{display:inline-block;padding:3px 8px;border-radius:20px;background:#e5eff8;margin-right:6px;font-size:.8rem}.vazio{text-align:center;color:#687684;padding:22px}
.busca-status{color:#425466;min-height:1.3em}.busca-status.erro{color:#b42318;font-weight:700}.busca-status.ok{color:#176b3a;font-weight:700}.busca-acoes button{background:#226b8f}
</style></head><body>
<header><div class="topbar"><div><h1>Monitor de licitações de climatização — Goiás</h1><div>Escolha o que consultar. Nada é enviado à API até você clicar em “Iniciar consulta”.</div></div><div class="usuario">''' + usuario + ' ' + logout + r'''</div></div><nav class="menu" aria-label="Menu principal"><a href="#consulta">Consulta</a><a href="#buscas">Buscas salvas</a><a href="#resultadosTitulo">Resultados</a><a href="#relatorios">Relatórios</a><a href="#ajuda">Ajuda</a></nav></header>
<main>
<section class="painel" id="consulta"><h2>1. Escolha o tipo de licitação</h2><div id="modalidades" class="checks">Carregando opções...</div><div class="acoes grupo-acoes"><button type="button" data-grupo="input[name=modalidade]" onclick="alternarGrupo(this.dataset.grupo,this)">Marcar todas</button></div>
<div class="grid" style="margin-top:12px"><div><label for="uf">Estado (UF)</label><select id="uf" disabled><option>Carregando...</option></select><div class="muted">Escopo atual do monitor.</div></div><div><label for="dias">Prazo nos próximos dias</label><input id="dias" type="number" min="1" value="30"></div>
<div><label for="municipio">Município (código IBGE, opcional)</label><input id="municipio" inputmode="numeric" placeholder="ex.: 5208707"></div>
<div><label for="palavras">Palavras-chave do título/objeto</label><input id="palavras" placeholder="ex.: hospital, manutenção, split"></div>
<div><label for="intervalo">Intervalo entre requisições (segundos)</label><input id="intervalo" type="number" min="1" step="0.5" value="2"></div></div>
<div style="margin-top:12px"><label>Área de atuação</label><div class="checks">''' + ''.join(f'''<label><input class="area" type="checkbox" value="{codigo}"> {nome}</label>''' for codigo, nome in AREAS_ATUACAO.items()) + r'''</div><div class="acoes grupo-acoes"><button type="button" data-grupo=".area" onclick="alternarGrupo(this.dataset.grupo,this)">Marcar todas</button></div><div class="muted">Opcional. A seleção é aplicada ao título/objeto da licitação.</div></div>
<div><label>Órgão / esfera</label><div class="checks"><label><input class="esfera" type="checkbox" value="E" checked> Estadual</label><label><input class="esfera" type="checkbox" value="M" checked> Municipal</label><label><input class="esfera" type="checkbox" value="F"> Federal</label><label><input class="esfera" type="checkbox" value="D"> Distrital</label></div><div class="acoes grupo-acoes"><button type="button" data-grupo=".esfera" onclick="alternarGrupo(this.dataset.grupo,this)">Marcar todas</button></div></div>
<div class="acoes"><label><input id="me" type="checkbox"> somente benefícios ME/EPP</label><label><input id="bruto" type="checkbox"> salvar respostas brutas</label></div>
<div class="acoes"><button id="iniciar" onclick="iniciar()">Iniciar consulta</button><span id="mensagem">Nenhuma consulta em andamento.</span></div></section>
<section class="painel" id="buscas"><h2>2. Buscas salvas</h2><div class="grid"><div><label for="nomeBusca">Nome da busca</label><input id="nomeBusca" required maxlength="120" placeholder="ex.: Manutenção em Goiânia"></div><div><label for="buscasSalvas">Busca existente</label><select id="buscasSalvas"><option value="">Nenhuma busca salva</option></select></div></div><div class="acoes busca-acoes"><button type="button" onclick="salvarBusca()">Salvar busca atual</button><button type="button" onclick="carregarBusca()">Carregar busca</button><button type="button" onclick="excluirBusca()">Excluir busca</button><span id="buscaStatus" class="busca-status" role="status" aria-live="polite"></span></div><div class="muted">A busca guarda somente os filtros. Os resultados continuam disponíveis em HTML, CSV e Excel após cada consulta.</div></section>
<section class="painel"><h2>3. Andamento</h2><div id="andamento" class="muted">Selecione pelo menos uma modalidade.</div><div class="barra" id="barra" hidden><i></i></div></section>
<section id="resultadosTitulo"><h2>4. Resultados encontrados</h2><div id="resultados"><div class="vazio">Os resultados aparecerão aqui conforme forem classificados.</div></div></section>
<section id="relatorios" class="painel"><h2>5. Relatórios da última consulta</h2><div id="relatorioLinks" class="links muted">Os links para HTML, CSV e Excel aparecerão aqui quando uma consulta for concluída.</div></section>
<section id="ajuda" class="painel"><h2>6. Ajuda — como usar</h2>
<ol>
<li>Em <b>Tipo de licitação</b>, marque uma ou mais modalidades que deseja acompanhar. Pregão eletrônico costuma ser o ponto de partida para serviços e fornecimentos.</li>
<li>Confirme o <b>Estado (UF)</b>. Este monitor está configurado para <b>Goiás (GO)</b>. Se quiser restringir a uma cidade, informe o código IBGE no campo Município.</li>
<li>Marque a <b>área de atuação</b> que combina com sua empresa, como instalação, manutenção, refrigeração ou PMOC. Se deixar todas desmarcadas, o monitor usa apenas os termos gerais de climatização.</li>
<li>Escolha a <b>esfera do órgão</b> (estadual, municipal, federal ou distrital). Para trabalhar em Goiás, normalmente use Estadual e Municipal.</li>
<li>Use <b>Palavras-chave</b> para procurar termos que apareçam no título ou objeto. Separe vários termos por vírgula, por exemplo: <i>hospital, manutenção, split</i>.</li>
<li>Defina o prazo em dias e, se necessário, marque <b>somente benefícios ME/EPP</b>. O intervalo entre requisições deve permanecer em pelo menos 1 segundo para respeitar a API pública.</li>
<li>Clique em <b>Iniciar consulta</b>. O andamento, a quantidade de requisições e as falhas aparecem em tempo real; os cartões são atualizados conforme os resultados chegam.</li>
<li>Na seção <b>Buscas salvas</b>, informe um nome para guardar os filtros atuais. Depois você pode carregar ou excluir essa busca sem preencher tudo novamente.</li>
<li>Abra <b>Ver resumo completo</b> em cada cartão para consultar órgão, município, objeto, valor, datas, benefício e itens. Ao final, use os links HTML, CSV e Excel exibidos na mensagem de conclusão para salvar ou compartilhar o resultado.</li>
</ol>
<p class="muted">A consulta pode levar alguns minutos, porque o PNCP é paginado e o monitor respeita um intervalo entre requisições. Se o resultado vier vazio, reduza o número de filtros ou aumente o prazo.</p>
</section>
</main>
<script>
let timer=null;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function carregarOpcoes(){fetch('/api/options').then(r=>r.json()).then(x=>{document.getElementById('modalidades').innerHTML=x.modalidades.map(m=>`<label><input type="checkbox" name="modalidade" value="${m.codigo}"> ${esc(m.nome)} <span class="muted">(${m.codigo})</span></label>`).join('');document.getElementById('uf').innerHTML=`<option>${esc(x.uf.nome)} (${esc(x.uf.codigo)})</option>`;atualizarGrupos();});}
function atualizarGrupos(){document.querySelectorAll('.grupo-acoes button[data-grupo]').forEach(b=>{let itens=[...document.querySelectorAll(b.dataset.grupo)];b.textContent=itens.length>0&&itens.every(x=>x.checked)?'Desmarcar todas':'Marcar todas';});}
function alternarGrupo(seletor,botao){let itens=[...document.querySelectorAll(seletor)];let todas=itens.length>0&&itens.every(x=>x.checked);itens.forEach(x=>x.checked=!todas);atualizarGrupos();}
function parametrosTela(){return {modalidades:selecionadas(),esferas:[...document.querySelectorAll('.esfera:checked')].map(x=>x.value),areas:[...document.querySelectorAll('.area:checked')].map(x=>x.value),dias:Number(document.getElementById('dias').value),municipio:document.getElementById('municipio').value.trim()||null,palavras_chave:document.getElementById('palavras').value.split(',').map(x=>x.trim()).filter(Boolean),intervalo:Number(document.getElementById('intervalo').value),me:document.getElementById('me').checked,bruto:document.getElementById('bruto').checked};}
function aplicarParametros(p){p=p||{};document.querySelectorAll('input[name=modalidade]').forEach(x=>x.checked=(p.modalidades||[]).map(Number).includes(Number(x.value)));document.querySelectorAll('.esfera').forEach(x=>x.checked=(p.esferas||[]).includes(x.value));document.querySelectorAll('.area').forEach(x=>x.checked=(p.areas||[]).includes(x.value));if(p.dias!==undefined)document.getElementById('dias').value=p.dias;if(p.municipio!==undefined)document.getElementById('municipio').value=p.municipio||'';if(Array.isArray(p.palavras_chave))document.getElementById('palavras').value=p.palavras_chave.join(', ');if(p.intervalo!==undefined)document.getElementById('intervalo').value=p.intervalo;if(p.me!==undefined)document.getElementById('me').checked=Boolean(p.me);if(p.bruto!==undefined)document.getElementById('bruto').checked=Boolean(p.bruto);atualizarGrupos();}
function statusBusca(mensagem,erro=false){let e=document.getElementById('buscaStatus');e.textContent=mensagem;e.className='busca-status '+(erro?'erro':'ok');}
function carregarBuscas(selecionar=''){fetch('/api/searches').then(r=>r.json()).then(x=>{let s=document.getElementById('buscasSalvas');s.innerHTML='<option value="">Selecione uma busca salva</option>'+(x.buscas||[]).map(b=>`<option value="${esc(b.arquivo)}">${esc(b.nome)}</option>`).join('');if(selecionar)s.value=selecionar;}).catch(()=>{});}
function salvarBusca(){let nome=document.getElementById('nomeBusca').value.trim();if(!nome){statusBusca('Informe um nome antes de salvar a busca.',true);document.getElementById('nomeBusca').focus();return;}fetch('/api/searches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome,filtros:parametrosTela()})}).then(async r=>({ok:r.ok,data:await r.json()})).then(x=>{if(!x.ok){statusBusca(x.data.error||'Não foi possível salvar a busca.',true);return;}statusBusca('Busca salva com sucesso.');carregarBuscas(x.data.arquivo);}).catch(()=>{statusBusca('Não foi possível salvar a busca. Verifique o servidor.',true);});}
function carregarBusca(){let arquivo=document.getElementById('buscasSalvas').value;if(!arquivo){statusBusca('Selecione uma busca salva para carregar.',true);return;}fetch('/api/searches/'+encodeURIComponent(arquivo)).then(async r=>({ok:r.ok,data:await r.json()})).then(x=>{if(!x.ok){statusBusca(x.data.error||'Não foi possível carregar a busca.',true);return;}document.getElementById('nomeBusca').value=x.data.nome||'';aplicarParametros(x.data.filtros);statusBusca('Filtros carregados. Clique em Iniciar consulta quando quiser.');}).catch(()=>{statusBusca('Não foi possível carregar a busca.',true);});}
function excluirBusca(){let arquivo=document.getElementById('buscasSalvas').value;if(!arquivo){statusBusca('Selecione uma busca salva para excluir.',true);return;}fetch('/api/searches/'+encodeURIComponent(arquivo),{method:'DELETE'}).then(async r=>({ok:r.ok,data:await r.json()})).then(x=>{if(!x.ok){statusBusca(x.data.error||'Não foi possível excluir a busca.',true);return;}statusBusca('Busca excluída.');document.getElementById('nomeBusca').value='';carregarBuscas();}).catch(()=>{statusBusca('Não foi possível excluir a busca.',true);});}
function selecionadas(){return [...document.querySelectorAll('input[name=modalidade]:checked')].map(x=>Number(x.value));}
function iniciar(){let p=parametrosTela();if(!p.modalidades.length){alert('Marque pelo menos uma modalidade antes de iniciar.');return;}if(!p.esferas.length){alert('Marque pelo menos uma esfera de órgão.');return;}document.getElementById('iniciar').disabled=true;fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}).then(r=>r.json()).then(x=>{if(x.error){alert(x.error);document.getElementById('iniciar').disabled=false;return;}document.getElementById('resultados').innerHTML='';poll();});}
function poll(){fetch('/api/status').then(r=>r.json()).then(x=>{let s=x.status||{};document.getElementById('mensagem').textContent=s.mensagem||s.fase||'';document.getElementById('andamento').textContent=`${s.fase||''} · modalidade ${s.modalidade||''} · registros ${s.registros??s.encontradas??0} · requisições ${s.requisicoes??0} · falhas ${s.falhas??0}`;document.getElementById('barra').hidden=!x.running;render(x.results||[]);if(x.files&&x.files.html){let links=' <a href="'+esc(x.files.html)+'" target="_blank">HTML</a> · <a href="'+esc(x.files.csv||'')+'" target="_blank">CSV</a> · <a href="'+esc(x.files.xlsx||'')+'" target="_blank">Excel</a>';document.getElementById('mensagem').innerHTML+=' · '+links;document.getElementById('relatorioLinks').innerHTML='<b>Arquivos gerados:</b> '+links;}if(x.running){timer=setTimeout(poll,1000)}else{document.getElementById('iniciar').disabled=false;}}).catch(()=>{timer=setTimeout(poll,2000)});}
function webLink(v,label){let s=String(v||'');return /^https?:\/\//i.test(s)?`<a href="${esc(s)}" target="_blank" rel="noopener">${label}</a>`:'';}
function moeda(v){if(v===null||v===undefined||v==='')return 'não informado';let n=Number(v);return Number.isFinite(n)?n.toLocaleString('pt-BR',{style:'currency',currency:'BRL'}):esc(v);}
function resumo(r){let termos=Array.isArray(r.termos)?r.termos.join(', '):'';return `<details class="resumo-local"><summary>Ver resumo completo</summary><dl><dt>Órgão</dt><dd>${esc(r.orgao)}</dd><dt>Unidade</dt><dd>${esc(r.unidade)}</dd><dt>Município / UF</dt><dd>${esc(r.municipio)} / ${esc(r.uf)}</dd><dt>Esfera</dt><dd>${esc(r.esfera)}</dd><dt>Modalidade</dt><dd>${esc(r.modalidade)} ${esc(r.numero_compra||'')}</dd><dt>Objeto/título</dt><dd>${esc(r.objeto)}</dd><dt>Valor estimado</dt><dd>${moeda(r.valor_estimado)}</dd><dt>Propostas</dt><dd>${esc(r.data_abertura||'')} até ${esc(r.data_encerramento||'')}</dd><dt>Benefício</dt><dd>${esc(r.situacao_me_epp||'Não informado')}</dd><dt>Itens</dt><dd>${esc(JSON.stringify(r.contagem_itens||{}))}</dd><dt>Termos</dt><dd>${esc(termos||'nenhum')}</dd><dt>Controle PNCP</dt><dd>${esc(r.numero_controle)}</dd></dl></details>`;}
function render(rs){if(!rs.length){return}document.getElementById('resultados').innerHTML=rs.map(r=>`<article class="card"><div><span class="badge">${esc(r.situacao_me_epp||'Não informado')}</span><b>${esc(r.data_encerramento||'')}</b></div><div class="obj">${esc(r.objeto)}</div><div>${esc(r.orgao)} · ${esc(r.municipio)}</div><div class="meta">${esc(r.modalidade)} · ${esc(r.numero_compra)} · origem dos itens: ${esc(r.origem_itens)}</div>${resumo(r)}<div class="links">${webLink(r.link_pncp,'Abrir referência no PNCP')}${r.link_origem?webLink(r.link_origem,esc(r.sistema_origem||'Sistema de origem')):''}</div></article>`).join('');}
carregarOpcoes();carregarBuscas();
</script></body></html>'''


def _sanear_links(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Defesa em profundidade: os links vêm do PNCP (externo); anula qualquer
    valor que não passe em `_url_web` antes de expor o registro à interface."""
    campos = ("url_pncp", "link_pncp", "linkSistemaOrigem", "link_origem")
    saneados = []
    for registro in registros:
        if not isinstance(registro, dict):
            saneados.append(registro)
            continue
        novo = dict(registro)
        for campo in campos:
            if campo in novo and _url_web(novo[campo]) is None:
                novo[campo] = ""
        saneados.append(novo)
    return saneados


def _apresentar_consulta(snapshot: dict[str, Any]) -> dict[str, Any]:
    status = snapshot.get("status") or {}
    if not status:
        estado = snapshot.get("estado", "")
        nomes = {"aguardando": "Na fila", "executando": "Em andamento", "concluida": "Concluída",
                 "parcial": "Resultado parcial", "cancelada": "Cancelada", "tempo_limite": "Limite atingido",
                 "falha": "Falha", "interrompida": "Interrompida"}
        status = {"fase": estado, "mensagem": nomes.get(estado, "Consulta"),
                  "requisicoes": snapshot.get("tentativas", 0), **(snapshot.get("progresso") or {})}
    estado = snapshot.get("estado", "")
    if estado not in ESTADOS_ATIVOS:
        nomes = {"concluida": ("concluído", "Consulta concluída."),
                 "parcial": ("parcial", "Consulta concluída parcialmente; confira os resultados disponíveis."),
                 "cancelada": ("cancelada", "Consulta cancelada; os resultados encontrados foram preservados."),
                 "tempo_limite": ("tempo_limite", "Limite da consulta atingido; os resultados encontrados foram preservados."),
                 "falha": ("erro", status.get("mensagem", "A consulta falhou.")),
                 "interrompida": ("interrompida", "O servidor reiniciou antes do término; a execução não foi retomada.")}
        fase, mensagem = nomes.get(estado, (estado, status.get("mensagem", "Consulta encerrada.")))
        status = dict(status)
        status.update(fase=fase, mensagem=mensagem,
                      parcial=estado in {"parcial", "cancelada", "tempo_limite", "interrompida"},
                      cancelada=estado == "cancelada")
    files = snapshot.get("arquivos") or snapshot.get("files") or {}
    return {
        "id": snapshot.get("consulta_id"), "consulta_id": snapshot.get("consulta_id"),
        "running": estado in ESTADOS_ATIVOS, "estado": estado, "status": status,
        "results": _sanear_links(snapshot.get("resultados", [])),
        "candidatos": _sanear_links(snapshot.get("candidatos", [])),
        "files": files, "filtros": snapshot.get("filtros", {}),
        "started_at": snapshot.get("inicio_execucao") or snapshot.get("inicio"),
        "updated_at": snapshot.get("fim") or snapshot.get("inicio"),
        "revisao": snapshot.get("revisao", 0),
    }


def _worker(state: Estado, consulta_id: str, owner_id: str, payload: dict[str, Any]) -> None:
    historico = cliente = None
    resultado = None
    candidatos: dict[str, dict[str, Any]] = {}
    resultados: dict[str, dict[str, Any]] = {}
    consulta = state.consultas

    def publicar_estado(*, status: dict[str, Any] | None = None,
                        evento: dict[str, Any] | None = None) -> None:
        consulta.atualizar(consulta_id, status=status or {},
                           resultados=list(resultados.values()), candidatos=list(candidatos.values()),
                           evento=evento, requisicoes=cliente.requisicoes if cliente else 0,
                           falhas=cliente.falhas if cliente else [])

    try:
        config = carregar(state.config_path)
        config["api"]["intervalo_entre_requisicoes"] = max(1.0, float(payload.get("intervalo", 2)))
        v2 = payload.get("schema_version") == 2 or "setores" in payload
        params = Parametros(dias=int(payload.get("dias", 30)),
                            municipio_ibge=payload.get("municipio") or None,
                            somente_me_epp=bool(payload.get("me")),
                            incluir_federal=False,
                            modalidades=[int(x) for x in payload["modalidades"]],
                            salvar_bruto=bool(payload.get("bruto")),
                            esferas=[str(x).upper() for x in payload.get("esferas", ["E", "M"])],
                            palavras_chave=[str(x).strip() for x in payload.get("palavras_chave", []) if str(x).strip()],
                            setores=[str(x) for x in payload.get("setores", [])] if v2 else None,
                            servicos=[str(x) for x in payload.get("servicos", [])],
                            subareas=payload.get("subareas", {}) if isinstance(payload.get("subareas", {}), dict) else {},
                            contextos=[str(x) for x in payload.get("contextos", [])],
                            incluir_predial_generico=bool(payload.get("incluir_predial_generico")),
                            perfil=payload.get("perfil"),
                            compatibilidade_v1=payload.get("compatibilidade_v1"),
                            catalogo=state.catalogo if v2 else None)
        params.areas_atuacao = [str(x).strip() for x in payload.get("areas", []) if str(x).strip()]
        historico = Historico(config["saida"]["banco"])
        cliente = ClientePNCP(config["api"])

        def progresso(fase: str, dados: dict[str, Any]) -> None:
            atualizado = _json_value(dados)
            status = {"fase": fase, "mensagem": "Coletando licitações no PNCP.",
                      "requisicoes": cliente.requisicoes, "falhas": len(cliente.falhas)}
            evento = None
            identidade = str(dados.get("identidade") or dados.get("numero_controle") or "")
            if fase == "pagina":
                status.update({campo: atualizado[campo] for campo in
                               ("modalidade", "pagina", "registros_pagina", "registros_modalidade",
                                "encontradas", "requisicoes", "falhas", "total_registros", "total_paginas")
                               if campo in atualizado})
                status["mensagem"] = f"Página {dados.get('pagina', '?')} recebida do PNCP."
            elif fase == "modalidade":
                status.update(atualizado)
                status["fase"] = "consultando modalidade"
                status["mensagem"] = f"Modalidade {dados.get('modalidade')} consultada."
            elif fase == "candidato":
                registro = dict(dados.get("registros", {}))
                registro.update({"id": identidade, "identidade": identidade, "beneficio_pendente": True})
                candidatos[identidade] = registro
                evento = {"tipo": "candidato", "candidato": registro}
                status.update({"fase": "classificando resultados", "mensagem": "Benefício ME/EPP em análise.",
                               "registros": len(candidatos) + len(resultados)})
            elif fase == "candidato_retirado":
                candidatos.pop(identidade, None)
                evento = {"tipo": "candidato_retirado", "identidade": identidade,
                          "revisao": dados.get("revisao"), "motivo": dados.get("motivo")}
                status.update({"fase": "atualizando resultados", "mensagem": "Uma versão mais recente do edital alterou a correspondência."})
            elif fase == "resultado":
                registro = dict(atualizado)
                registro.update({"id": identidade, "identidade": identidade, "beneficio_pendente": False})
                candidatos.pop(identidade, None)
                if not params.somente_me_epp or registro.get("situacao_me_epp") in SITUACOES_ME_EPP:
                    resultados[identidade] = registro
                else:
                    resultados.pop(identidade, None)
                evento = {"tipo": "resultado", "resultado": registro}
                status.update({"fase": "classificando resultados", "mensagem": "Classificação dos itens atualizada.",
                               "registros": len(resultados) + len(candidatos)})
            elif fase == "fim":
                status.update(atualizado)
                status.update({"fase": "finalizando", "mensagem": "Preparando relatórios da consulta."})
            publicar_estado(status=status, evento=evento)

        publicar_estado(status={"fase": "iniciando", "mensagem": "Preparando consulta ao PNCP.", "requisicoes": 0})
        controles = {
            "deadline_monotonic": consulta.deadline(consulta_id),
            "cancelar": lambda: consulta.deve_interromper(consulta_id),
            "max_tentativas": consulta.max_tentativas,
            "ao_iniciar_tentativa": lambda: consulta.registrar_tentativa(consulta_id),
        }
        resultado = executar(config, params, cliente, historico, progresso=progresso, controles=controles)
        resumo = {"encontradas": resultado.encontradas, "filtradas": resultado.filtradas,
                  "me_epp": resultado.me_epp, "exclusivas": resultado.exclusivas,
                  "novas": resultado.novas, "falhas": resultado.falhas,
                  "parametros": "consulta iniciada pela interface web"}
        diretorio = _diretorio_usuario(state, f"consultas/{consulta_id}", owner_id)
        arquivos = publicar(resultado.registros, diretorio, resumo)
        urls = {tipo: f"/files/{consulta_id}/{arquivo.name}" for tipo, arquivo in arquivos.items()}
        snapshot = consulta.snapshot(consulta_id, owner_id=owner_id)["consulta"]
        status = dict(snapshot.get("status") or {})
        estado_final = "parcial" if resultado.falhas or resultado.modalidades_com_falha else "concluida"
        status.update({"fase": "concluído" if estado_final == "concluida" else "parcial",
                       "mensagem": "Consulta concluída." if estado_final == "concluida" else "Consulta concluída com falhas; os resultados disponíveis foram preservados.",
                       "requisicoes": cliente.requisicoes, "falhas": resultado.falhas,
                       "encontradas": resultado.encontradas, "registros": len(resultados) + len(candidatos),
                       "parcial": estado_final == "parcial"})
        consulta.atualizar(consulta_id, status=status, arquivos=urls,
                           resultados=list(resultados.values()), candidatos=list(candidatos.values()),
                           requisicoes=cliente.requisicoes, falhas=cliente.falhas)
        consulta.finalizar(consulta_id, estado_final, falhas=cliente.falhas)
    except Exception as exc:
        log.exception("Falha na consulta web %s", consulta_id)
        try:
            snapshot = consulta.snapshot(consulta_id, owner_id=owner_id)["consulta"]
            status = dict(snapshot.get("status") or {})
            status.update({"fase": "erro", "mensagem": str(exc), "parcial": bool(resultados or candidatos),
                           "requisicoes": cliente.requisicoes if cliente else 0,
                           "falhas": len(cliente.falhas) if cliente else 0})
            consulta.atualizar(consulta_id, status=status, resultados=list(resultados.values()),
                               candidatos=list(candidatos.values()), requisicoes=status["requisicoes"])
            consulta.finalizar(consulta_id, "falha", falhas=cliente.falhas if cliente else [str(exc)])
        except (KeyError, ConsultaError):
            log.exception("Não foi possível persistir a falha da consulta %s", consulta_id)
    finally:
        if cliente:
            cliente.close()
        if historico:
            historico.fechar()


def _host_e_loopback(host: str) -> bool:
    """Aceita apenas endereços que não saem da própria máquina (127.0.0.0/8, ::1 ou
    'localhost'), usado para recusar `--modo-acesso local --host 0.0.0.0` de saída."""
    if host.strip().casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def _handler_class(state: Estado):
    class Handler(BaseHTTPRequestHandler):
        MAX_BODY = 1_048_576
        STATIC = {"/static/app.css": ("app.css", "text/css; charset=utf-8"),
                  "/static/app.js": ("app.js", "text/javascript; charset=utf-8")}

        def log_message(self, fmt: str, *args: Any) -> None:
            log.info("%s - %s", self.address_string(), fmt % args)

        def _send(self, code: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cache-Control", "private, no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, dado: Any) -> None:
            self._send(code, json.dumps(_json_value(dado), ensure_ascii=False).encode("utf-8"))

        def _identidade(self) -> Identidade | None:
            try:
                return state.identidade(self.headers)
            except AcessoNegado as exc:
                self._json(401, {"error": str(exc)})
                return None

        _CABECALHOS_TUNEL = ("Cf-Connecting-Ip", "Cf-Ray", "Cf-Access-Jwt-Assertion", "Cf-Visitor")

        def _acesso_local_bloqueado(self) -> str | None:
            """Em modo local não há autenticação: recusa tráfego que chegue por um túnel
            público (ex.: Cloudflare Tunnel encaminhado por engano para 127.0.0.1),
            identificado por cabeçalhos típicos do Cloudflare ou por um Host que não seja
            o próprio loopback (o que também bloqueia DNS rebinding)."""
            if state.modo_acesso != "local":
                return None
            for nome in self._CABECALHOS_TUNEL:
                if self.headers.get(nome) is not None:
                    return ("Este servidor está em modo local e recusa tráfego encaminhado por um túnel "
                            "público. Para expor a interface na rede, use --modo-acesso cloudflare.")
            host = (self.headers.get("Host") or "").strip()
            host_sem_porta = (host.split("]")[0] + "]") if host.startswith("[") else host.split(":")[0]
            if not _host_e_loopback(host_sem_porta):
                return ("Este servidor está em modo local e só aceita requisições para localhost/127.0.0.1. "
                        "Para expor a interface na rede, use --modo-acesso cloudflare.")
            return None

        def _body(self) -> dict[str, Any]:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Envie os dados no formato JSON.")
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError as exc:
                raise ValueError("Tamanho da requisição inválido.") from exc
            if length < 0 or length > self.MAX_BODY:
                raise ValueError("A requisição está vazia ou excede o limite de 1 MB.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("O corpo da requisição deve ser um objeto JSON.")
            return payload

        def _origem_valida(self) -> bool:
            if state.modo_acesso != "cloudflare":
                return True
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "").casefold()
            if not origin or not host:
                return False
            try:
                parsed = urlparse(origin)
                return parsed.scheme in {"https", "http"} and parsed.netloc.casefold() == host
            except ValueError:
                return False

        def _consulta_publica(self, snapshot: dict[str, Any]) -> dict[str, Any]:
            return _apresentar_consulta(snapshot)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            # Probe mínima usada pelo lançador para não encaminhar um servidor local
            # sem autenticação por engano ao túnel público.
            if path == "/healthz":
                self._json(200, {"ok": True, "access_mode": state.modo_acesso})
                return
            bloqueio = self._acesso_local_bloqueado()
            if bloqueio:
                self._json(403, {"error": bloqueio}); return
            identidade = self._identidade()
            if identidade is None:
                return
            owner_id = identidade.subject
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/":
                arquivo = Path(__file__).resolve().parent.parent / "templates" / "index.html"
                self._send(200, arquivo.read_bytes(), "text/html; charset=utf-8")
            elif path in self.STATIC:
                nome, tipo = self.STATIC[path]
                arquivo = Path(__file__).resolve().parent.parent / "static" / nome
                self._send(200, arquivo.read_bytes(), tipo)
            elif path == "/api/session":
                ultimo = state.consulta_mais_recente(owner_id)
                sessao = {"authenticated": state.modo_acesso == "cloudflare",
                          "email": identidade.email if state.modo_acesso == "cloudflare" else "",
                          "logout_url": "/cdn-cgi/access/logout" if state.modo_acesso == "cloudflare" else None,
                          "mode": state.modo_acesso}
                self._json(200, {"session": sessao,
                                 "last_run_id": (ultimo or {}).get("consulta_id")})
            elif path == "/api/options":
                body = {"modalidades": [{"codigo": x, "nome": MODALIDADES.get(x, f"Modalidade {x}")}
                                           for x in state.config["api"]["modalidades"]],
                        "uf": {"codigo": "GO", "nome": "Goiás"},
                        "municipios": [], "catalog": state.catalogo.publico(),
                        "limites": {"timeout_segundos": state.consultas.timeout_s,
                                    "max_tentativas": state.consultas.max_tentativas}}
                self._json(200, body)
            elif path == "/api/status":
                consulta_id = parse_qs(parsed.query).get("id", [None])[0]
                try:
                    snap = state.consultas.snapshot(consulta_id, owner_id=owner_id)["consulta"] if consulta_id else state.consulta_mais_recente(owner_id)
                except KeyError:
                    self._json(404, {"error": "Consulta não encontrada."}); return
                self._json(200, self._consulta_publica(snap) if snap else {
                    "id": None, "running": False,
                    "status": {"fase": "parado", "mensagem": "Escolha os filtros para começar."},
                    "results": [], "candidatos": [], "files": {}})
            elif path == "/api/history":
                rows = state.consultas.historico(limite=100, owner_id=owner_id)
                items = []
                for snap in rows:
                    exibido = self._consulta_publica(snap)
                    filtros = snap.get("filtros") or {}
                    termos = [str(x) for x in filtros.get("setores", []) + filtros.get("servicos", [])]
                    resumo = ", ".join(termos[:4]) or ", ".join(filtros.get("areas", [])[:4]) or "Consulta personalizada"
                    exibido.update({"data_hora": snap.get("inicio_execucao") or snap.get("inicio"),
                                    "resumo_filtros": resumo, "resultados": len(snap.get("resultados", []))})
                    items.append(exibido)
                self._json(200, {"execucoes": items})
            elif path.startswith("/api/history/"):
                consulta_id = path.removeprefix("/api/history/")
                if "/" in consulta_id or not re.fullmatch(r"[0-9a-fA-F-]{36}", consulta_id):
                    self._json(400, {"error": "Identificador de consulta inválido."}); return
                try:
                    snap = state.consultas.snapshot(consulta_id, owner_id=owner_id)["consulta"]
                except KeyError:
                    self._json(404, {"error": "Consulta não encontrada."}); return
                self._json(200, {"snapshot": self._consulta_publica(snap), "filtros": snap.get("filtros", {})})
            elif path == "/api/searches":
                diretorio = _buscas_dir(state, owner_id)
                buscas = []
                for arquivo in sorted(diretorio.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                    try:
                        dado = json.loads(arquivo.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    buscas.append({"arquivo": arquivo.name, "nome": dado.get("nome", arquivo.stem),
                                   "atualizado_em": dado.get("atualizado_em", "")})
                self._json(200, {"buscas": buscas})
            elif path.startswith("/api/searches/"):
                try:
                    arquivo = _arquivo_busca(state, path.removeprefix("/api/searches/"), owner_id)
                    if not arquivo.is_file():
                        self._json(404, {"error": "Busca não encontrada."}); return
                    self._send(200, arquivo.read_bytes())
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
            elif path.startswith("/files/"):
                partes = path.removeprefix("/files/").split("/")
                if len(partes) == 2 and re.fullmatch(r"[0-9a-fA-F-]{36}", partes[0]):
                    consulta_id, nome = partes
                    try:
                        snap = state.consultas.snapshot(consulta_id, owner_id=owner_id)["consulta"]
                    except KeyError:
                        self._send(404, "Arquivo não encontrado".encode("utf-8"), "text/plain; charset=utf-8"); return
                    url = f"/files/{consulta_id}/{nome}"
                    if url not in (snap.get("arquivos") or {}).values() or Path(nome).name != nome:
                        self._send(404, "Arquivo não encontrado".encode("utf-8"), "text/plain; charset=utf-8"); return
                    file_path = _diretorio_usuario(state, f"consultas/{consulta_id}", owner_id) / nome
                elif state.modo_acesso == "local" and len(partes) == 1:
                    nome = Path(partes[0]).name
                    if nome not in {"ultimo.html", "ultimo.csv", "ultimo.xlsx"} and not nome.startswith("licitacoes_ac_go_"):
                        self._send(404, "Arquivo não encontrado".encode("utf-8"), "text/plain; charset=utf-8"); return
                    file_path = Path(state.config["saida"]["pasta"]) / nome
                else:
                    self._send(404, "Arquivo não encontrado".encode("utf-8"), "text/plain; charset=utf-8"); return
                if not file_path.is_file() or file_path.suffix.lower() not in {".html", ".csv", ".xlsx"}:
                    self._send(404, "Arquivo não encontrado".encode("utf-8"), "text/plain; charset=utf-8"); return
                content_type = {".html": "text/html; charset=utf-8", ".csv": "text/csv; charset=utf-8",
                                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}[file_path.suffix.lower()]
                self._send(200, file_path.read_bytes(), content_type)
            else:
                self._send(404, "Não encontrado".encode("utf-8"), "text/plain; charset=utf-8")

        def do_POST(self) -> None:
            bloqueio = self._acesso_local_bloqueado()
            if bloqueio:
                self._json(403, {"error": bloqueio}); return
            identidade = self._identidade()
            if identidade is None:
                return
            if not self._origem_valida():
                self._json(403, {"error": "Origem da requisição não autorizada."}); return
            path = urlparse(self.path).path
            if path == "/api/searches":
                try:
                    payload = self._body()
                    nome = str(payload.get("nome", "")).strip()
                    filtros = payload.get("filtros")
                    if not nome or len(nome) > 120:
                        raise ValueError("Informe um nome entre 1 e 120 caracteres.")
                    if not isinstance(filtros, dict):
                        raise ValueError("Os filtros da busca são inválidos.")
                    arquivo = _buscas_dir(state, identidade.subject) / _slug_busca(nome)
                    documento = {"schema_version": 2, "nome": nome,
                                 "atualizado_em": datetime.now().isoformat(timespec="seconds"), "filtros": filtros}
                    dados = json.dumps(documento, ensure_ascii=False, indent=2).encode("utf-8")
                    try:
                        fd = os.open(arquivo, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    except FileExistsError:
                        self._json(409, {"error": "Já existe uma busca com esse nome. Escolha outro nome ou exclua a busca existente."}); return
                    try:
                        with os.fdopen(fd, "wb") as destino:
                            destino.write(dados)
                            destino.flush()
                            os.fsync(destino.fileno())
                    except OSError:
                        arquivo.unlink(missing_ok=True)
                        raise
                    self._json(201, {"ok": True, "arquivo": arquivo.name}); return
                except (ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
                    self._json(400, {"error": str(exc)}); return
            if path == "/api/cancel":
                try:
                    payload = self._body()
                    consulta_id = payload.get("id")
                    if not isinstance(consulta_id, str):
                        raise ValueError("Informe o identificador da consulta.")
                    atual = state.consultas.request_cancel(consulta_id, owner_id=identidade.subject)
                    self._json(200, {"ok": True, "consulta": atual})
                except KeyError:
                    self._json(404, {"error": "Consulta não encontrada."})
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
                return
            if path != "/api/start":
                self._send(404, "Não encontrado".encode("utf-8"), "text/plain; charset=utf-8"); return
            try:
                payload = self._body()
                _preparar_compatibilidade_v1(payload)
                modalidades = payload.get("modalidades")
                permitidas = set(state.config["api"]["modalidades"])
                if not isinstance(modalidades, list) or not modalidades:
                    raise ValueError("Escolha pelo menos uma modalidade.")
                if any(isinstance(x, bool) or not isinstance(x, int) or x not in permitidas for x in modalidades):
                    raise ValueError("Uma ou mais modalidades não são válidas.")
                if len(set(modalidades)) != len(modalidades):
                    raise ValueError("Remova modalidades repetidas.")
                schema_version = payload.get("schema_version")
                if isinstance(schema_version, bool) or schema_version not in (None, 1, 2):
                    raise ValueError("A versão dos filtros não é suportada. Recarregue a página.")
                if payload.get("uf", "GO") != "GO":
                    raise ValueError("O monitor atende somente licitações de Goiás (GO).")
                esferas = payload.get("esferas")
                if not isinstance(esferas, list) or not esferas or any(x not in {"E", "M", "F", "D"} for x in esferas):
                    raise ValueError("Escolha pelo menos uma esfera válida: estadual, municipal, federal ou distrital.")
                dias_brutos = payload.get("dias", 0)
                intervalo_bruto = payload.get("intervalo", 0)
                if isinstance(dias_brutos, bool) or isinstance(intervalo_bruto, bool):
                    raise ValueError("Prazo e intervalo precisam ser números válidos.")
                dias = int(dias_brutos)
                if float(dias_brutos) != dias:
                    raise ValueError("O prazo deve ser um número inteiro de dias.")
                intervalo = float(intervalo_bruto)
                if not 1 <= dias <= 365:
                    raise ValueError("O prazo deve estar entre 1 e 365 dias.")
                if not 1 <= intervalo <= 60:
                    raise ValueError("Use um intervalo entre 1 e 60 segundos.")
                termos = payload.get("palavras_chave", [])
                if not isinstance(termos, list) or len(termos) > 30 or any(not isinstance(x, str) or len(x) > 120 for x in termos):
                    raise ValueError("Use até 30 palavras ou frases, com no máximo 120 caracteres cada.")
                v2 = payload.get("schema_version") == 2 or "setores" in payload
                if v2:
                    for dim in ("setores", "servicos", "contextos"):
                        state.catalogo.validar_ids(dim, payload.get(dim, []))
                    if not payload.get("setores"):
                        raise ValueError("Escolha pelo menos um setor técnico.")
                    subareas = payload.get("subareas", {})
                    if not isinstance(subareas, dict):
                        raise ValueError("As subáreas selecionadas são inválidas.")
                    for setor, ids in subareas.items():
                        permitido = {item["id"] for item in state.catalogo.setor(setor).get("subareas", [])}
                        if not isinstance(ids, list) or any(x not in permitido for x in ids):
                            raise ValueError(f"Subárea inválida para o setor {setor}.")
                    perfil = payload.get("perfil")
                    if perfil is not None:
                        state.catalogo.validar_ids("perfis", [perfil], permitir_vazio=False)
                    versao = payload.get("catalogo_versao")
                    if versao != state.catalogo.versao:
                        raise ValueError("O catálogo de áreas foi atualizado. Recarregue a página antes de consultar.")
                filtros = dict(payload)
            except (ValueError, TypeError, KeyError) as exc:
                self._json(400, {"error": str(exc)}); return
            try:
                consulta_id = state.consultas.registrar(filtros, catalogo_versao=payload.get("catalogo_versao"),
                                                        owner_id=identidade.subject)
                state.consultas.admitir(consulta_id)
            except ConsultaOcupada:
                self._json(409, {"error": "Já existe uma consulta em andamento. Aguarde ou tente novamente."}); return
            except (ConsultaError, OSError) as exc:
                self._json(500, {"error": f"Não foi possível iniciar a consulta: {exc}"}); return
            threading.Thread(target=_worker, args=(state, consulta_id, identidade.subject, payload), daemon=True).start()
            self._json(202, {"ok": True, "id": consulta_id, "consulta_id": consulta_id})

        def do_DELETE(self) -> None:
            bloqueio = self._acesso_local_bloqueado()
            if bloqueio:
                self._json(403, {"error": bloqueio}); return
            identidade = self._identidade()
            if identidade is None:
                return
            if not self._origem_valida():
                self._json(403, {"error": "Origem da requisição não autorizada."}); return
            path = urlparse(self.path).path
            if not path.startswith("/api/searches/"):
                self._send(404, "Não encontrado".encode("utf-8"), "text/plain; charset=utf-8"); return
            try:
                arquivo = _arquivo_busca(state, path.removeprefix("/api/searches/"), identidade.subject)
                if not arquivo.is_file():
                    self._json(404, {"error": "Busca não encontrada."}); return
                arquivo.unlink()
                self._json(200, {"ok": True})
            except ValueError as exc:
                self._json(400, {"error": str(exc)})

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interface web local do monitor de licitações")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="abrir o navegador automaticamente")
    parser.add_argument("--modo-acesso", choices=("local", "cloudflare"),
                        default=os.environ.get("MONITOR_AC_MODO_ACESSO", "local"),
                        help="autenticação local ou validação de sessão Cloudflare Access")
    args = parser.parse_args(argv)
    if args.modo_acesso == "local" and not _host_e_loopback(args.host):
        parser.error("--modo-acesso local só pode ser vinculado a um endereço de loopback "
                     "(127.0.0.1, ::1 ou localhost). Para expor o servidor na rede, "
                     "use --modo-acesso cloudflare.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        state = Estado(Path(args.config), modo_acesso=args.modo_acesso)
    except (OSError, ValueError) as exc:
        parser.error(f"Configuração indisponível: {exc}")
    server = ThreadingHTTPServer((args.host, args.port), _handler_class(state))
    address = f"http://{args.host}:{args.port}"
    print(f"Interface web disponível em {address}")
    if args.open:
        threading.Timer(0.4, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
