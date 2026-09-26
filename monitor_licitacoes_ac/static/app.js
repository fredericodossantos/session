/*
 * API contract for backend integration (kept in one isolated client below):
 * GET  /api/options -> { modalidades:[{codigo,nome}], uf:{codigo,nome},
 *   municipios:[{codigo_ibge,nome}] (catálogo estático de GO, ~246 itens),
 *   catalog:{versao,setores:[{id,rotulo,grupo,subareas:[{id,rotulo}]}],
 *   servicos:[{id,rotulo}],contextos:[{id,rotulo}],perfis:[{id,rotulo,setores}],
 *   presets:[{id,rotulo,setores,servicos,perfil?}],
 *   palavras_chave:{modo:'frase_literal_qualquer'}} }. New catalog is optional
 * while backend integration is in progress; legacy area ids below remain valid.
 * GET  /api/session (optional) -> {session:{email,authenticated}} and optionally
 *   {last_run_id}. Do not infer a Google session from absent/untrusted headers.
 * POST /api/start -> {schema_version:2,catalogo_versao,perfil,setores,subareas,
 *   servicos,contextos,incluir_predial_generico,modalidades,uf:'GO',esferas,
 *   dias,municipio,palavras_chave,intervalo,me,bruto,areas}. Return 202 with
 *   {id|consulta_id}. `areas` preserves the current web.py v1 payload.
 * GET  /api/status?consulta_id=<id>&since=<revisao> (aceita `id` como sinônimo
 *   de `consulta_id`) -> sem `since`: {id,consulta_id,running,estado,status,
 *   results,candidatos,files,started_at,updated_at,revisao} (contrato cheio).
 *   Com `since`: mesma forma, mas sem `results`/`candidatos`; em vez disso
 *   {atualizacoes:[{revisao,tipo:'resultado'|'candidato'|'candidato_retirado',
 *   resultado?|candidato?|identidade?}]} com só o que mudou desde `since`. Se o
 *   servidor não puder aplicar a revisão pedida, cai para o contrato cheio (sem
 *   `atualizacoes`); o cliente detecta isso pela ausência do campo e refaz o
 *   estado local a partir de `results`/`candidatos`. Polling é serial e para em
 *   estado terminal. Rotas opcionais: POST /api/cancel {id}, GET
 *   /api/history?pagina=&por_pagina= -> {execucoes,pagina,por_pagina,total,
 *   tem_proxima}, GET /api/history/<id>. Searches retain the existing
 *   /api/searches CRUD contract. Report downloads remain same-origin
 *   /files/<name> links.
 */
(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const state = {
    options: null, catalog: null, legacyCatalog: false, runId: null,
    polling: false, pollTimer: null, runStartedAt: 0, savedSearches: [],
    expandedResults: new Set(), resultItems: new Map(), activePage: 'consultar', lastSnapshot: null,
    legacyCompatibility: null, lastRevisao: 0, municipioPorCodigo: new Map(),
    historyPage: 1, historyPerPage: 20, historyTotal: 0, historyHasNext: false,
  };

  const legacyAreas = [
    { id: 'instalacao', rotulo: 'Instalação' },
    { id: 'manutencao', rotulo: 'Manutenção' },
    { id: 'fornecimento', rotulo: 'Fornecimento / aquisição' },
    { id: 'pmoc', rotulo: 'PMOC' },
    { id: 'refrigeracao', rotulo: 'Refrigeração' },
    { id: 'pecas', rotulo: 'Peças e insumos' },
  ];
  const knownSpheres = [
    { id: 'E', name: 'Estadual', checked: true },
    { id: 'M', name: 'Municipal', checked: true },
    { id: 'F', name: 'Federal', checked: false },
    { id: 'D', name: 'Distrital', checked: false },
  ];
  const aliases = {
    '#consulta': '#consultar', '#resultadosTitulo': '#consultar', '#relatorios': '#historico',
    '#resultados': '#consultar',
  };

  // Monta a query string ignorando valores ausentes, para não mandar `since=undefined`
  // ou `since=0` sem necessidade (0 é uma revisão válida, então só omite null/undefined/'').
  function queryString(params) {
    const partes = Object.entries(params)
      .filter(([, valor]) => valor !== undefined && valor !== null && valor !== '')
      .map(([chave, valor]) => `${encodeURIComponent(chave)}=${encodeURIComponent(valor)}`);
    return partes.length ? `?${partes.join('&')}` : '';
  }

  const api = {
    async request(path, init = {}) {
      const response = await fetch(path, { credentials: 'same-origin', ...init,
        headers: { Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...(init.headers || {}) } });
      const type = response.headers.get('content-type') || '';
      let data = null;
      if (type.includes('application/json')) data = await response.json();
      else if (response.status !== 204) {
        const raw = await response.text();
        throw new Error(raw.includes('<html') || raw.includes('<!doctype')
          ? 'A sessão pode ter expirado. Entre novamente e tente de novo.'
          : `Resposta inesperada do servidor (${response.status}).`);
      }
      if (!response.ok) {
        const error = new Error(data?.error || data?.message || `Não foi possível concluir a ação (${response.status}).`);
        error.status = response.status;
        throw error;
      }
      return data || {};
    },
    options: () => api.request('/api/options'),
    // Optional, added by the root integration only after a real validated session exists.
    session: () => api.request('/api/session'),
    start: payload => api.request('/api/start', { method: 'POST', body: JSON.stringify(payload) }),
    status: (id, since) => api.request('/api/status' + queryString({ consulta_id: id, since })),
    cancel: id => api.request('/api/cancel', { method: 'POST', body: JSON.stringify({ id }) }),
    searches: () => api.request('/api/searches'),
    getSearch: file => api.request(`/api/searches/${encodeURIComponent(file)}`),
    saveSearch: payload => api.request('/api/searches', { method: 'POST', body: JSON.stringify(payload) }),
    deleteSearch: file => api.request(`/api/searches/${encodeURIComponent(file)}`, { method: 'DELETE' }),
    history: (pagina, porPagina) => api.request('/api/history' + queryString({ pagina, por_pagina: porPagina })),
    historyItem: id => api.request(`/api/history/${encodeURIComponent(id)}`),
  };

  function safeText(value, fallback = 'Não informado') {
    return value === null || value === undefined || String(value).trim() === '' ? fallback : String(value);
  }
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
  }
  // Os links de resultado vêm do PNCP (externo): recusa qualquer esquema que não seja
  // http/https (ex.: javascript:, data:) antes de montar o href.
  function safeHttpUrl(value) {
    if (!value) return '';
    try {
      const url = new URL(String(value));
      return ['http:', 'https:'].includes(url.protocol) && url.hostname ? url.href : '';
    } catch { return ''; }
  }
  function showGlobal(message, kind = 'info') {
    const box = $('#globalMessage'); box.textContent = message; box.className = `notice ${kind}`; box.hidden = false;
  }
  function hideGlobal() { $('#globalMessage').hidden = true; }
  function setInlineMessage(node, message, kind = '') {
    node.textContent = message; node.className = `notice-inline ${kind}`.trim();
  }
  function normalizedHash() { return location.hash || '#consultar'; }
  function routeToHash(hash) {
    const requested = aliases[hash] || hash;
    if (location.hash === requested) renderPage(requested);
    else location.hash = requested;
  }
  function renderPage(hash = normalizedHash()) {
    const legacyHash = aliases[hash] ? hash : null;
    if (legacyHash) { hash = aliases[legacyHash]; history.replaceState(null, '', hash); }
    const route = hash.replace(/^#/, '');
    const page = ['consultar', 'buscas', 'historico', 'ajuda'].includes(route) ? route : 'consultar';
    state.activePage = page;
    $$('[data-page-view]').forEach(section => { section.hidden = section.dataset.pageView !== page; });
    $$('.main-nav a[data-page]').forEach(link => {
      if (link.dataset.page === page) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    $('#mainNav').classList.remove('open'); $('#menuToggle').setAttribute('aria-expanded', 'false');
    if (page === 'buscas') loadSavedSearches();
    if (page === 'historico') loadHistory();
    if (page === 'consultar') window.setTimeout(() => $('#page-consultar h1').focus({ preventScroll: true }), 0);
    if (legacyHash === '#resultadosTitulo' || legacyHash === '#resultados') window.setTimeout(() => $('#resultsSection').scrollIntoView({ block: 'start' }), 20);
  }

  function catalogEntries() { return state.catalog?.setores || []; }
  function isSectorSelected(id) { return $(`input[name="sector"][value="${CSS.escape(id)}"]`)?.checked || false; }
  function selectedValues(name) { return $$(`input[name="${name}"]:checked`).map(input => input.value); }
  function setValues(name, values = []) {
    const set = new Set((values || []).map(String));
    $$(`input[name="${name}"]`).forEach(input => { input.checked = set.has(input.value); });
  }
  function labelFor(id, items, idKey = 'id', labelKey = 'rotulo') {
    return items.find(item => String(item[idKey]) === String(id))?.[labelKey] || id;
  }
  function catalogSearchText() { return $('#catalogSearch').value.trim().toLocaleLowerCase('pt-BR'); }
  function sectorMatchesFilter(sector, filter) {
    if (!filter) return true;
    return [sector.rotulo, sector.id, sector.grupo, ...(sector.subareas || []).flatMap(s => [s.rotulo, s.id])]
      .some(value => String(value || '').toLocaleLowerCase('pt-BR').includes(filter));
  }

  function renderSectors() {
    const host = $('#sectorGroups'); const filter = catalogSearchText();
    if (state.legacyCatalog) {
      host.innerHTML = `<div class="notice" role="note"><strong>Catálogo de setores fase 3 ainda não disponível.</strong> Você pode usar as áreas já existentes enquanto o servidor é atualizado.</div>
        <fieldset class="choice-fieldset"><legend>Áreas atuais <span class="optional">(opcional)</span></legend><div class="choice-grid">${legacyAreas.map(area => checkboxMarkup('legacy-area', area.id, area.rotulo)).join('')}</div></fieldset>`;
      return;
    }
    const all = catalogEntries();
    const visible = all.filter(sector => sectorMatchesFilter(sector, filter));
    const groups = new Map();
    const groupLabels = { mecanica: 'Engenharia mecânica', eletrica: 'Engenharia elétrica', integrados: 'Soluções integradas' };
    all.forEach(sector => {
      const key = sector.grupo || 'Áreas técnicas';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(sector);
    });
    const renderedGroups = [...groups.entries()].map(([group, sectors]) => {
      const groupLabel = groupLabels[group] || group;
      const groupKey = `group-${slug(groupLabel)}`;
      const hasVisible = sectors.some(sector => sectorMatchesFilter(sector, filter));
      return `<section class="catalog-group" aria-labelledby="${groupKey}" ${filter && !hasVisible ? 'hidden' : ''}><h3 id="${groupKey}">${escapeHtml(groupLabel)}</h3>
        <div class="group-tools"><span>Selecione os setores relevantes</span><button type="button" data-select-visible="${escapeHtml(groupLabel)}">Marcar ${sectors.length} opções visíveis</button></div>
        <div class="choice-grid">${sectors.map(sector => sectorMarkup(sector, filter)).join('')}</div></section>`;
    }).join('');
    host.innerHTML = filter && !visible.length
      ? '<div class="empty-state compact-empty"><p>Nenhuma área corresponde à pesquisa. Tente outro termo.</p></div>' + renderedGroups
      : renderedGroups;
    updateSectorGroupButtons();
  }
  function slug(value) { return String(value).toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
  function checkboxMarkup(name, id, label, attrs = '') {
    return `<label class="check-option"><input type="checkbox" name="${escapeHtml(name)}" value="${escapeHtml(id)}" ${attrs}><span>${escapeHtml(label)}</span></label>`;
  }
  function sectorMarkup(sector, filter) {
    const selected = isSectorSelected(sector.id) ? 'checked' : '';
    const subareas = sector.subareas || [];
    const matchingSubareas = subareas;
    const subareaSelected = new Set(selectedValues('subarea'));
    const subareaMarkup = subareas.length ? `<fieldset class="subareas" data-parent-sector="${escapeHtml(sector.id)}" ${selected ? '' : 'hidden'}><legend>Detalhar ${escapeHtml(sector.rotulo)} <span class="optional">(opcional)</span></legend>
      <div class="group-tools"><span>Sem subárea selecionada, todas as atividades deste setor</span><button type="button" data-toggle-subareas="${escapeHtml(sector.id)}">${selectedValues('subarea').length ? 'Marcar opções visíveis' : 'Marcar opções visíveis'}</button></div>
      <div class="choice-grid">${matchingSubareas.map(sub => `<div ${filter && ![sub.rotulo, sub.id].some(x => String(x).toLocaleLowerCase('pt-BR').includes(filter)) ? 'hidden' : ''}>${checkboxMarkup('subarea', sub.id, sub.rotulo, `data-sector="${escapeHtml(sector.id)}" ${subareaSelected.has(sub.id) ? 'checked' : ''}`)}</div>`).join('')}</div></fieldset>` : '';
    return `<div class="sector-option" ${filter && !sectorMatchesFilter(sector, filter) ? 'hidden' : ''}><label class="check-option"><input type="checkbox" name="sector" value="${escapeHtml(sector.id)}" ${selected}><span>${escapeHtml(sector.rotulo)}</span></label>${subareaMarkup}</div>`;
  }

  function renderList(host, name, entries, { defaultChecked = [], empty = 'Nenhuma opção disponível.' } = {}) {
    if (!entries?.length) { host.innerHTML = `<span class="muted">${escapeHtml(empty)}</span>`; return; }
    const set = new Set(defaultChecked.map(String));
    host.innerHTML = entries.map(entry => checkboxMarkup(name, entry.id ?? entry.codigo, entry.rotulo ?? entry.nome,
      set.has(String(entry.id ?? entry.codigo)) ? 'checked' : '')).join('');
  }
  function updateToggleButtons() {
    $$('[data-toggle-all]').forEach(button => {
      const name = button.dataset.toggleAll;
      const inputs = $$(`#${name === 'sphere' ? 'sphereChoices' : name === 'modality' ? 'modalityChoices' : name === 'service' ? 'serviceChoices' : 'contextChoices'} input[type="checkbox"]`);
      button.textContent = inputs.length && inputs.every(input => input.checked) ? 'Desmarcar todas' : 'Marcar todas';
      button.disabled = !inputs.length;
    });
  }
  function updateSectorGroupButtons() {
    $$('.catalog-group').forEach(group => {
      const visible = $$('input[name="sector"]', group).filter(input => !input.closest('.sector-option')?.hidden);
      const button = $('[data-select-visible]', group);
      if (!button) return;
      const allChecked = visible.length > 0 && visible.every(input => input.checked);
      button.textContent = allChecked ? 'Desmarcar setores visíveis' : `Marcar ${visible.length} setores visíveis`;
      button.disabled = visible.length === 0;
    });
    $$('[data-toggle-subareas]').forEach(button => {
      const host = button.closest('fieldset');
      const visible = $$('input[name="subarea"]', host).filter(input => !input.parentElement.closest('[hidden]'));
      const allChecked = visible.length > 0 && visible.every(input => input.checked);
      button.textContent = allChecked ? 'Desmarcar opções visíveis' : 'Marcar opções visíveis';
      button.disabled = visible.length === 0;
    });
  }
  function renderCatalog() {
    const options = state.options || {};
    state.catalog = options.catalog || options.catalogo || null;
    state.legacyCatalog = !state.catalog || !Array.isArray(state.catalog.setores) || !state.catalog.setores.length;
    if (state.catalog) {
      renderProfiles(); renderPresets(); renderSectors();
      renderList($('#serviceChoices'), 'service', state.catalog.servicos || [], { empty: 'Serviços não informados pelo catálogo.' });
      renderList($('#contextChoices'), 'context', state.catalog.contextos || [], { empty: 'Contextos não informados pelo catálogo.' });
    } else {
      $('#profile').innerHTML = '<option value="">Seleção personalizada</option><option value="legacy">Climatização e refrigeração (áreas atuais)</option>';
      $('#serviceChoices').innerHTML = '<span class="muted">Tipos de serviço aparecem quando o catálogo fase 3 estiver disponível.</span>';
      $('#contextChoices').innerHTML = '<span class="muted">Contextos aparecem quando o catálogo fase 3 estiver disponível.</span>';
      renderPresets(); renderSectors();
    }
    const modalities = options.modalidades || options.modalities || [];
    renderList($('#modalityChoices'), 'modality', modalities.map(m => ({ id: m.codigo ?? m.id, rotulo: m.nome ?? m.rotulo })), { empty: 'Modalidades não disponíveis. Verifique o servidor.' });
    renderList($('#sphereChoices'), 'sphere', knownSpheres.map(s => ({ id: s.id, rotulo: s.name })), { defaultChecked: ['E', 'M'] });
    updateToggleButtons();
    renderMunicipalities(options.municipios || options.municipalities || []);
    updateSummaries();
  }
  function renderProfiles() {
    const profiles = state.catalog?.perfis || [];
    $('#profile').innerHTML = '<option value="">Seleção personalizada</option>' + profiles.map(p => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.rotulo)}</option>`).join('');
  }
  function renderPresets() {
    const presets = state.catalog?.presets || [];
    const common = presets.filter(p => /climatiza|pmoc|ilumina|equipe/i.test(`${p.id} ${p.rotulo}`));
    const list = common.length ? common.slice(0, 4) : presets.slice(0, 4);
    $('#presetButtons').innerHTML = list.length
      ? list.map(p => `<button type="button" class="preset-chip" data-preset="${escapeHtml(p.id)}">${escapeHtml(p.rotulo)}</button>`).join('')
      : '<span class="muted">Atalhos aparecerão quando o catálogo estiver disponível.</span>';
  }
  // Rótulo usado tanto no datalist quanto para restaurar o texto exibido a partir do código.
  function municipalityLabel(nome, codigo) { return `${nome} (${codigo})`; }
  function renderMunicipalities(items) {
    state.municipioPorCodigo = new Map();
    items.forEach(item => {
      const code = String(item.codigo_ibge ?? item.codigo ?? item.id);
      state.municipioPorCodigo.set(code, item.nome ?? item.rotulo);
    });
    $('#municipalityOptions').innerHTML = [...state.municipioPorCodigo.entries()]
      .map(([code, nome]) => `<option value="${escapeHtml(municipalityLabel(nome, code))}"></option>`).join('');
    $('#municipalityHelp').textContent = items.length
      ? 'Digite o nome do município; a busca preenche o código IBGE usado na consulta.'
      : 'A lista de municípios ainda não está disponível. Use o código IBGE em Opções avançadas.';
  }
  // Sincroniza o campo oculto (código IBGE) a partir do texto digitado no campo de busca.
  // Só aceita o código quando o texto corresponde exatamente a uma opção do catálogo;
  // texto livre/incompleto não filtra silenciosamente por um município errado.
  function syncMunicipalityFromInput() {
    const raw = $('#municipalityName').value.trim();
    const casamento = [...state.municipioPorCodigo.entries()]
      .find(([code, nome]) => municipalityLabel(nome, code) === raw);
    $('#municipality').value = casamento ? casamento[0] : '';
    updateSummaries();
  }

  function applyPreset(id) {
    const preset = state.catalog?.presets?.find(item => item.id === id);
    if (!preset) return;
    setValues('sector', preset.setores || []);
    setValues('service', preset.servicos || []);
    setValues('subarea', []);
    if (preset.perfil) $('#profile').value = preset.perfil;
    else $('#profile').value = '';
    updateSectorDetails(); updateToggleButtons(); updateSectorGroupButtons(); updateSummaries();
    showGlobal(`Atalho “${preset.rotulo}” aplicado. Revise os filtros e inicie quando quiser.`);
  }
  function applyProfile(id) {
    if (!id) return;
    if (id === 'legacy' && state.legacyCatalog) {
      setValues('legacy-area', ['pmoc', 'refrigeracao']);
      updateToggleButtons(); updateSummaries(); return;
    }
    const profile = state.catalog?.perfis?.find(item => item.id === id);
    if (!profile) return;
    setValues('sector', profile.setores || []);
    updateSectorDetails(); updateSectorGroupButtons(); updateSummaries();
    showGlobal(`Perfil “${profile.rotulo}” aplicado. Você pode ajustar os setores selecionados.`);
  }
  function updateSectorDetails() {
    $$('.subareas[data-parent-sector]').forEach(fieldset => {
      fieldset.hidden = !isSectorSelected(fieldset.dataset.parentSector);
      if (fieldset.hidden) $$('input[name="subarea"]', fieldset).forEach(input => { input.checked = false; });
    });
  }

  function filters() {
    const selectedSector = selectedValues(state.legacyCatalog ? 'legacy-area' : 'sector');
    const subareas = {};
    $$('input[name="subarea"]:checked').forEach(input => {
      const sector = input.dataset.sector;
      (subareas[sector] ||= []).push(input.value);
    });
    const municipalitySelect = $('#municipality').value;
    const manualMunicipality = $('#municipalityCode').value.trim();
    const legacyMapping = {
      manutencao: 'manutencao', instalacao: 'instalacao', fornecimento: 'fornecimento',
      pmoc: 'pmoc', refrigeracao: 'refrigeracao', pecas: 'pecas',
    };
    const selectedModern = state.legacyCatalog ? [] : selectedSector;
    const v2 = {
      schema_version: 2,
      catalogo_versao: state.catalog?.versao || null,
      perfil: $('#profile').value || null,
      setores: selectedModern,
      subareas,
      servicos: selectedValues('service'),
      contextos: selectedValues('context'),
      incluir_predial_generico: $('#genericBuilding').checked,
    };
    const selectedServices = v2.servicos;
    const areas = state.legacyCatalog
      ? selectedSector
      : [...new Set([...selectedServices.filter(id => legacyMapping[id]), ...selectedModern.filter(id => legacyMapping[id])])];
    return {
      ...v2,
      modalidades: selectedValues('modality').map(Number),
      uf: 'GO', esferas: selectedValues('sphere'), dias: Number($('#days').value),
      municipio: municipalitySelect || manualMunicipality || null,
      palavras_chave: $('#keywords').value.split(',').map(text => text.trim()).filter(Boolean),
      intervalo: Number($('#interval').value), me: $('#meOnly').checked, bruto: false,
      areas,
      ...(state.legacyCompatibility ? { compatibilidade_v1: state.legacyCompatibility } : {}),
    };
  }
  function updateSummaries() {
    const f = filters();
    const sectors = state.legacyCatalog ? f.areas.map(id => labelFor(id, legacyAreas)) : f.setores.map(id => labelFor(id, catalogEntries()));
    const services = f.servicos.map(id => labelFor(id, state.catalog?.servicos || []));
    const modalities = f.modalidades.map(id => labelFor(id, state.options?.modalidades || [], 'codigo', 'nome'));
    const spheres = f.esferas.map(id => labelFor(id, knownSpheres, 'id', 'name'));
    const parts = [
      `${sectors.length} ${sectors.length === 1 ? 'setor' : 'setores'}`,
      `${services.length} ${services.length === 1 ? 'serviço' : 'serviços'}`,
      `${modalities.length} ${modalities.length === 1 ? 'modalidade' : 'modalidades'}`,
      f.municipio ? (state.municipioPorCodigo.get(String(f.municipio)) || `município ${f.municipio}`) : 'todo o estado',
      `${f.dias || 0} dias`,
    ];
    if (f.esferas.length) parts.push(spheres.join(' e '));
    if (f.me) parts.push('somente ME/EPP');
    if (f.incluir_predial_generico) parts.push('manutenção predial a confirmar');
    const activeAdvanced = Number(Boolean($('#municipalityCode').value.trim())) + Number(f.me) + Number(f.incluir_predial_generico);
    $('#searchSummary').textContent = parts.join(' · ');
    $('#selectedSectorsSummary').textContent = sectors.length ? `Selecionados: ${sectors.join(', ')}` : 'Nenhum setor selecionado.';
    $('#advancedCount').textContent = activeAdvanced ? `Avançado — ${activeAdvanced} filtro${activeAdvanced === 1 ? '' : 's'} ativo${activeAdvanced === 1 ? '' : 's'}` : 'Filtros adicionais e limites da consulta';
    renderActiveChips(f, sectors, services);
  }
  function renderActiveChips(f, sectors, services) {
    const chips = [];
    sectors.forEach(id => chips.push({ group: state.legacyCatalog ? 'legacy-area' : 'sector', id, label: labelFor(id, state.legacyCatalog ? legacyAreas : catalogEntries()) }));
    services.forEach(id => chips.push({ group: 'service', id, label: labelFor(id, state.catalog?.servicos || []) }));
    f.contextos.forEach(id => chips.push({ group: 'context', id, label: labelFor(id, state.catalog?.contextos || []) }));
    f.modalidades.forEach(id => chips.push({ group: 'modality', id: String(id), label: labelFor(id, state.options?.modalidades || [], 'codigo', 'nome') }));
    $('#activeChips').innerHTML = chips.slice(0, 12).map(chip => `<span class="filter-chip">${escapeHtml(chip.label)}<button type="button" aria-label="Remover ${escapeHtml(chip.label)}" data-remove-group="${escapeHtml(chip.group)}" data-remove-id="${escapeHtml(chip.id)}">×</button></span>`).join('');
  }

  function validate(f) {
    $('#modalitiesError').hidden = true;
    $('#sectorsError').hidden = true;
    ['sphereError', 'daysError', 'intervalError', 'ibgeError'].forEach(id => { const node = $(`#${id}`); node.textContent = ''; node.hidden = true; });
    $('#modalityChoices').removeAttribute('aria-invalid');
    const problems = [];
    if (!f.modalidades.length) {
      $('#modalitiesError').hidden = false; $('#modalityChoices').setAttribute('aria-invalid', 'true');
      problems.push({ node: $('input[name="modality"]') || $('#modalityChoices'), message: 'Escolha pelo menos uma modalidade.' });
    }
    if (!state.legacyCatalog && !f.setores.length) { $('#sectorsError').hidden = false; problems.push({ node: $('#showCatalog'), message: 'Escolha pelo menos um setor técnico.' }); }
    if (!f.esferas.length) { $('#sphereError').textContent = 'Escolha pelo menos uma esfera do órgão.'; $('#sphereError').hidden = false; problems.push({ node: $('input[name="sphere"]'), message: $('#sphereError').textContent }); }
    if (!Number.isInteger(f.dias) || f.dias < 1 || f.dias > 365) { $('#daysError').textContent = 'Informe um prazo entre 1 e 365 dias.'; $('#daysError').hidden = false; problems.push({ node: $('#days'), message: $('#daysError').textContent }); }
    if (!Number.isFinite(f.intervalo) || f.intervalo < 1) { $('#intervalError').textContent = 'Use um intervalo de pelo menos 1 segundo.'; $('#intervalError').hidden = false; problems.push({ node: $('#interval'), message: $('#intervalError').textContent }); }
    if (f.municipio && !/^\d{7}$/.test(String(f.municipio))) { $('#ibgeError').textContent = 'O código IBGE precisa ter 7 dígitos.'; $('#ibgeError').hidden = false; problems.push({ node: $('#municipalityCode'), message: $('#ibgeError').textContent }); }
    if (problems.length) {
      showGlobal(problems[0].message, 'error');
      problems[0].node.focus?.();
      return false;
    }
    return true;
  }
  function formPayload(f) {
    // V2 fields implement the catalog proposal; v1 fields keep current web.py functional.
    return { ...f, setores: f.setores, schema_version: 2 };
  }
  async function startSearch(event) {
    event.preventDefault(); hideGlobal();
    const payload = filters();
    if (!validate(payload)) return;
    $('#startButton').disabled = true; $('#startButton').textContent = 'Iniciando consulta…';
    try {
      const response = await api.start(formPayload(payload));
      state.runId = response.id || response.consulta_id || response.run_id || null;
      state.runStartedAt = Date.now(); state.polling = true;
      clearProgressView(); $('#progressPanel').hidden = false; $('#cancelButton').hidden = false;
      $('#progressMessage').textContent = 'Consulta iniciada. Buscando oportunidades…';
      $('#runState').textContent = 'Em andamento';
      $('#resultsList').innerHTML = ''; state.resultItems.clear(); state.expandedResults.clear();
      state.lastRevisao = 0;
      $('#resultDownloads').hidden = true;
      setRunningNotice(true);
      showGlobal(`Consulta iniciada${state.runId ? ` · ID ${state.runId}` : ''}.` , 'success');
      pollStatus();
    } catch (error) {
      $('#startButton').disabled = false; $('#startButton').textContent = 'Consultar licitações';
      showGlobal(error.message, 'error');
    }
  }
  function clearProgressView() {
    $('#progressPhase').textContent = 'Aguardando'; $('#elapsedTime').textContent = '—';
    $('#requestCount').textContent = '0'; $('#resultCount').textContent = '0'; $('#progressDetail').textContent = '';
  }
  function setRunningNotice(running) { $('#runningNotice').hidden = !running; }
  // Aplica a resposta de /api/status: com `atualizacoes`, é incremental (o servidor só mandou
  // o que mudou desde `lastRevisao`) e `renderResults` mescla nos cartões já existentes; sem
  // `atualizacoes`, é o contrato cheio (primeira carga, ou fallback do servidor) e o estado local
  // de resultados é reconstruído do zero para não deixar cartões obsoletos na tela.
  function applyStatusResponse(raw) {
    const incremental = Array.isArray(raw.atualizacoes);
    if (!incremental) state.resultItems.clear();
    if (typeof raw.revisao === 'number') state.lastRevisao = raw.revisao;
    const snapshot = incremental ? { ...raw, eventos: raw.atualizacoes } : raw;
    state.lastSnapshot = snapshot;
    renderSnapshot(snapshot);
    return snapshot;
  }
  async function pollStatus() {
    if (!state.polling) return;
    try {
      const raw = await api.status(state.runId, state.lastRevisao);
      const snapshot = applyStatusResponse(raw);
      const running = Boolean(raw.running ?? raw.consulta?.running ?? false);
      if (running) state.pollTimer = window.setTimeout(pollStatus, 1300);
      else finishRun(snapshot);
    } catch (error) {
      // Não sabemos se a próxima resposta poderá aplicar a revisão pedida; preferimos uma
      // recarga completa a arriscar um buraco na sequência de eventos.
      state.lastRevisao = 0;
      $('#progressMessage').textContent = 'Não foi possível atualizar o andamento. Tentando reconectar…';
      $('#lastUpdated').textContent = `Última atualização: ${new Date().toLocaleTimeString('pt-BR')}`;
      state.pollTimer = window.setTimeout(pollStatus, 3500);
    }
  }
  function getStatus(snapshot) { return snapshot.status || snapshot.consulta?.status || {}; }
  function renderSnapshot(snapshot) {
    const status = getStatus(snapshot);
    const results = snapshot.results || snapshot.resultados || snapshot.consulta?.results || [];
    $('#progressMessage').textContent = safeText(status.mensagem, status.fase || 'Consulta em andamento.');
    $('#progressPhase').textContent = safeText(status.etapa || status.modalidade || status.fase, 'Aguardando');
    $('#requestCount').textContent = safeText(status.requisicoes ?? status.chamadas, '0');
    $('#resultCount').textContent = safeText(status.registros ?? status.encontradas ?? status.resultados ?? (results.length || state.resultItems.size), '0');
    const detail = [];
    if (status.pagina) detail.push(`Página ${status.pagina}`);
    if (status.registros_lidos) detail.push(`${status.registros_lidos} registros lidos`);
    if (status.falhas) detail.push(`${status.falhas} falhas de requisição`);
    if (status.parcial || status.cancelada) detail.push(status.cancelada ? 'Consulta cancelada; resultados encontrados foram preservados.' : 'Resultado parcial.');
    $('#progressDetail').textContent = detail.join(' · ');
    if (state.runStartedAt) $('#elapsedTime').textContent = formatDuration(Date.now() - state.runStartedAt);
    $('#lastUpdated').textContent = `Atualizado às ${new Date().toLocaleTimeString('pt-BR')}`;
    renderResults(results, snapshot.files || snapshot.arquivos || {}, snapshot);
    renderDownloads(snapshot.files || snapshot.arquivos || {}, status);
  }
  function finishRun(snapshot) {
    state.polling = false; clearTimeout(state.pollTimer); setRunningNotice(false);
    const status = getStatus(snapshot); const phase = String(status.fase || '').toLowerCase();
    $('#cancelButton').hidden = true; $('#startButton').disabled = false; $('#startButton').textContent = 'Consultar licitações';
    // Usa o Map acumulado, não o payload da última resposta: em modo incremental ele
    // pode vir vazio (nada mudou na última revisão) mesmo com cartões já na tela.
    const hasResults = state.resultItems.size > 0;
    if (phase.includes('erro') || snapshot.error) {
      $('#runState').textContent = 'Falha'; $('#runState').classList.add('error');
      showGlobal(safeText(status.mensagem, 'A consulta não foi concluída.'), 'error');
    } else if (!hasResults) {
      $('#runState').textContent = 'Concluída';
      showGlobal(status.parcial ? 'A consulta terminou parcialmente. Confira as informações e os relatórios disponíveis.' : 'A consulta terminou sem resultados para estes critérios. Edite os filtros para tentar outra busca.', status.parcial ? 'error' : 'info');
    } else {
      $('#runState').textContent = status.parcial || status.cancelada ? 'Parcial' : 'Concluída';
      showGlobal(status.parcial || status.cancelada ? 'Consulta encerrada parcialmente. Os resultados encontrados foram preservados.' : `Consulta concluída com ${$('#resultCount').textContent} resultados.`, status.parcial || status.cancelada ? 'error' : 'success');
    }
    $('#startButton').textContent = 'Consultar novamente';
  }
  function formatDuration(ms) {
    const secs = Math.floor(ms / 1000); const min = Math.floor(secs / 60);
    return min ? `${min} min ${String(secs % 60).padStart(2, '0')} s` : `${secs} s`;
  }
  async function cancelRun() {
    if (!state.runId) {
      showGlobal('O servidor ainda não fornece um identificador de consulta para cancelar. A execução segue ativa.', 'error'); return;
    }
    $('#cancelButton').disabled = true; $('#cancelButton').textContent = 'Solicitando cancelamento…';
    $('#progressMessage').textContent = 'Finalizando a requisição em andamento. Os resultados encontrados serão preservados.';
    try {
      await api.cancel(state.runId);
      $('#runState').textContent = 'Cancelamento solicitado';
    } catch (error) {
      $('#cancelButton').disabled = false; $('#cancelButton').textContent = 'Cancelar consulta';
      showGlobal(error.message, 'error');
    }
  }

  function resultIdentity(item, index) {
    return String(item.id || item.identidade || item.controlePNCP || item.numero_controle_pncp || item.chave ||
      [item.cnpj, item.anoCompra || item.ano, item.sequencialCompra || item.sequencial].filter(Boolean).join('-') || index);
  }
  function resultTitle(item) { return item.objetoCompra || item.objeto || item.titulo || item.descricao || 'Objeto não informado'; }
  function resultDate(item) { return item.dataEncerramentoProposta || item.data_encerramento_proposta || item.data_encerramento || item.data_fim || item.prazo; }
  function formatDate(value) {
    if (!value) return 'Prazo não informado';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  }
  function resultSummaryRows(item) {
    const evidence = (item.evidencias || []).map(entry => [entry.tipo, entry.termo, entry.trecho].filter(Boolean).join(': ')).join(' · ');
    const fieldMap = [
      ['Objeto completo', item.objetoCompra || item.objeto], ['Órgão', item.orgao || item.nomeOrgao],
      ['Unidade', item.unidade || item.nomeUnidade], ['Município', item.municipio],
      ['Modalidade', item.modalidade], ['Número', item.numeroCompra || item.numero],
      ['Valor estimado', item.valorTotalEstimado ?? item.valor_estimado], ['Abertura de propostas', item.data_abertura],
      ['Encerramento de propostas', item.data_encerramento], ['Benefício ME/EPP', item.situacao_me_epp || item.beneficio],
      ['Origem da classificação dos itens', item.origem_itens], ['Termos de correspondência', item.termos],
      ['Evidências no objeto', evidence], ['Controle PNCP', item.numero_controle], ['Data da consulta', item.consultado_em],
    ];
    return fieldMap.filter(([, value]) => value !== undefined && value !== null && value !== '').map(([label, value]) => `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(Array.isArray(value) ? value.join(', ') : value)}</dd>`).join('');
  }
  function renderResults(items = [], files = {}, snapshot = {}) {
    const removed = new Set(snapshot.candidatos_retirados || snapshot.removidos || []);
    const incoming = [...items, ...(snapshot.candidatos || [])];
    const events = [...(snapshot.eventos || snapshot.events || [])];
    if (snapshot.evento) events.push(snapshot.evento);
    for (const event of events) {
      const name = String(event.evento || event.tipo_evento || event.tipo || '').toLocaleLowerCase('pt-BR');
      if (name === 'candidato_retirado' || name === 'retirado') { removed.add(event.identidade || event.id || event.chave); continue; }
      const candidate = event.candidato || event.resultado || event.dados;
      if (candidate && (name === 'candidato' || name === 'resultado' || !name)) incoming.push(candidate);
    }
    const normalized = [];
    for (const item of incoming) {
      const eventName = String(item.evento || item.tipo_evento || item.tipo || '').toLocaleLowerCase('pt-BR');
      const id = resultIdentity(item, normalized.length);
      if (eventName === 'candidato_retirado' || eventName === 'retirado' || item.candidato_retirado) { removed.add(id); continue; }
      if (eventName === 'resultado' || eventName === 'candidato' || !eventName) normalized.push(item);
    }
    for (const id of removed) state.resultItems.delete(String(typeof id === 'object' ? resultIdentity(id, '') : id));
    // Snapshots are authoritative: retain incremental cards already received if a page has not
    // repeated them, but remove explicit candidate_retirado events and preserve UI expansion.
    normalized.forEach((item, index) => state.resultItems.set(resultIdentity(item, index), item));
    for (const id of state.expandedResults) if (!state.resultItems.has(id)) state.expandedResults.delete(id);
    if (!state.resultItems.size) {
      const status = getStatus(state.lastSnapshot || {});
      const emptyText = status.fase && !status.fase.toLowerCase().includes('parado')
        ? 'Nenhuma oportunidade corresponde aos filtros desta consulta.'
        : 'Escolha áreas, local e modalidade. A página não consulta o PNCP até você iniciar uma busca.';
      $('#resultsList').innerHTML = `<div class="empty-state"><span class="empty-icon" aria-hidden="true">⌕</span><h3>${emptyText.startsWith('Nenhuma') ? 'Nenhum resultado encontrado' : 'Sua busca começa aqui'}</h3><p>${escapeHtml(emptyText)}</p></div>`;
      return;
    }
    const host = $('#resultsList');
    const empty = $('.empty-state', host); if (empty) empty.remove();
    const ordered = [...state.resultItems.entries()].sort(([, a], [, b]) => {
      const da = new Date(resultDate(a) || '2999-12-31').getTime();
      const db = new Date(resultDate(b) || '2999-12-31').getTime();
      return da - db;
    });
    const kept = new Set();
    ordered.forEach(([id, item], index) => {
      kept.add(id);
      let card = $(`[data-result-id="${CSS.escape(id)}"]`, host);
      const shouldOpen = state.expandedResults.has(id) || Boolean(card && !$('[data-summary]', card).hidden);
      const markup = renderResultCard(item, index, files, shouldOpen);
      if (!card) host.insertAdjacentHTML('beforeend', markup);
      else card.outerHTML = markup;
      const updatedCard = $(`[data-result-id="${CSS.escape(id)}"]`, host);
      if (updatedCard) host.append(updatedCard);
    });
    $$('[data-result-id]', host).forEach(card => { if (!kept.has(card.dataset.resultId)) card.remove(); });
  }
  function renderResultCard(item, index, files, summaryOpen = false) {
    const id = resultIdentity(item, index); summaryOpen ||= state.expandedResults.has(id);
    const org = item.orgao || item.nomeOrgao || item.razaoSocial || 'Órgão não informado';
    const municipality = [item.municipio || item.nomeMunicipio, item.uf || 'GO'].filter(Boolean).join(' · ');
    const value = item.valorTotalEstimado ?? item.valor_estimado;
    const tags = [];
    const sectors = item.setores_identificados || item.areas_identificadas || item.areas || [];
    (Array.isArray(sectors) ? sectors : [sectors]).filter(Boolean).forEach(x => tags.push(`<span class="tag">${escapeHtml(typeof x === 'string' ? x : x.rotulo || x.nome || x.id)}</span>`));
    const me = item.situacao_me_epp || item.beneficio_me_epp;
    if (item.beneficio_pendente) tags.push('<span class="tag warn">Benefício ME/EPP em análise</span>');
    else if (me) tags.push(`<span class="tag ${/exclusiva|parcial|cota/i.test(me) ? 'success' : ''}">${escapeHtml(me)}</span>`);
    if (item.nova) tags.push('<span class="tag success">Nova</span>');
    if (item.atualizada) tags.push('<span class="tag warn">Atualizada</span>');
    const explanation = item.explicacao || item.motivo_correspondencia || item.evidencia;
    const urlPncp = safeHttpUrl(item.url_pncp || item.link_pncp);
    const urlOrigem = safeHttpUrl(item.linkSistemaOrigem || item.link_origem);
    const links = [
      urlPncp ? `<a href="${escapeHtml(urlPncp)}" target="_blank" rel="noopener">Abrir no PNCP (nova aba)</a>` : '',
      urlOrigem ? `<a href="${escapeHtml(urlOrigem)}" target="_blank" rel="noopener">Abrir no portal de origem (nova aba)</a>` : '',
    ].filter(Boolean).join('');
    return `<article class="result-card" data-result-id="${escapeHtml(id)}"><div class="result-top"><h3 class="result-title">${escapeHtml(resultTitle(item))}</h3><span class="deadline">Até ${escapeHtml(formatDate(resultDate(item)))}</span></div>
      <div class="result-meta"><span>${escapeHtml(org)}</span>${municipality ? `<span>${escapeHtml(municipality)}</span>` : ''}<span>Valor estimado: ${escapeHtml(value === undefined ? 'Não informado' : formatCurrency(value))}</span></div>
      ${tags.length ? `<div class="result-tags">${tags.join('')}</div>` : ''}${explanation ? `<p class="result-explanation">${escapeHtml(explanation)}</p>` : ''}
      <div class="result-actions"><button type="button" data-toggle-summary="${escapeHtml(id)}" aria-expanded="${summaryOpen}">${summaryOpen ? 'Fechar resumo' : 'Ver resumo'}</button></div>
      <div class="result-summary" data-summary="${escapeHtml(id)}" ${summaryOpen ? '' : 'hidden'}><dl>${resultSummaryRows(item)}</dl>${links ? `<div class="result-links">${links}</div>` : ''}</div></article>`;
  }
  function formatCurrency(value) {
    const number = Number(value);
    if (!Number.isFinite(number) || number === 0) return value === 0 ? 'Não informado' : safeText(value);
    return number.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }
  function renderDownloads(files, status = {}) {
    const host = $('#resultDownloads');
    const labels = { xlsx: 'Excel (.xlsx)', html: 'HTML', csv: 'CSV' };
    const links = Object.entries(labels).filter(([key]) => files[key]).map(([key, label]) => `<a class="download-link" href="${escapeHtml(files[key])}" target="_blank" rel="noopener">Baixar ${label}</a>`);
    host.innerHTML = links.join(''); host.hidden = !links.length;
    if (links.length && (status.parcial || status.cancelada)) host.setAttribute('aria-label', 'Relatórios parciais da consulta');
    else host.setAttribute('aria-label', 'Baixar resultados');
  }

  function suggestedName(f = filters()) {
    const chosen = state.legacyCatalog ? f.areas : f.setores;
    const main = chosen.length ? labelFor(chosen[0], state.legacyCatalog ? legacyAreas : catalogEntries()) : 'Busca de engenharia';
    const service = f.servicos.length ? labelFor(f.servicos[0], state.catalog?.servicos || []) : '';
    return [main, service, 'GO'].filter(Boolean).join(' — ');
  }
  function openSaveDialog() {
    $('#saveDialogSummary').textContent = $('#searchSummary').textContent;
    $('#savedSearchName').value = suggestedName(); $('#saveSearchError').hidden = true;
    $('#saveDialog').showModal(); window.setTimeout(() => $('#savedSearchName').focus(), 0);
  }
  function closeDialog(dialog) { if (dialog.open) dialog.close(); }
  async function saveCurrentSearch() {
    const name = $('#savedSearchName').value.trim(); const errorNode = $('#saveSearchError');
    if (!name) { errorNode.textContent = 'Dê um nome para salvar esta busca.'; errorNode.hidden = false; $('#savedSearchName').setAttribute('aria-invalid', 'true'); $('#savedSearchName').focus(); return; }
    $('#savedSearchName').removeAttribute('aria-invalid'); errorNode.hidden = true;
    const button = $('#confirmSaveButton'); button.disabled = true; button.textContent = 'Salvando…';
    try {
      const result = await api.saveSearch({ nome: name, filtros: filters() });
      closeDialog($('#saveDialog')); showGlobal('Busca salva. Você pode encontrá-la em Buscas salvas.', 'success');
      await loadSavedSearches(result.arquivo);
    } catch (error) {
      errorNode.textContent = error.status === 409 ? 'Já existe uma busca com esse nome. Use outro nome.' : error.message;
      errorNode.hidden = false; $('#savedSearchName').focus();
    } finally { button.disabled = false; button.textContent = 'Salvar busca'; }
  }
  async function loadSavedSearches(selectFile = '') {
    const host = $('#savedSearchesList'); host.innerHTML = '<div class="loading-block">Carregando buscas salvas…</div>';
    try {
      const result = await api.searches(); state.savedSearches = result.buscas || [];
      if (!state.savedSearches.length) {
        host.innerHTML = '<div class="empty-state compact-empty"><h3>Nenhuma busca salva</h3><p>Na página Consultar, use “Salvar filtros” para guardar seus critérios.</p></div>'; return;
      }
      host.innerHTML = state.savedSearches.map(item => `<article class="saved-row"><div><h3>${escapeHtml(item.nome || 'Busca salva')}</h3><p>${escapeHtml(item.atualizado_em ? `Alterada em ${formatDate(item.atualizado_em)}` : 'Filtros guardados')}</p></div><div class="row-actions"><button type="button" class="button button-secondary" data-load-search="${escapeHtml(item.arquivo)}">Carregar filtros</button><button type="button" class="button button-quiet" data-delete-search="${escapeHtml(item.arquivo)}" data-search-name="${escapeHtml(item.nome || 'Busca salva')}">Excluir</button></div></article>`).join('');
      if (selectFile) setInlineMessage($('#savedSearchesMessage'), 'Busca salva com sucesso.', 'success');
    } catch (error) {
      host.innerHTML = '<div class="empty-state compact-empty"><h3>Não foi possível carregar as buscas</h3><p>Verifique a conexão e tente novamente.</p></div>';
      setInlineMessage($('#savedSearchesMessage'), error.message, 'error');
    }
  }
  async function loadOneSearch(file) {
    try {
      const result = await api.getSearch(file); applyFilters(result.filtros || {});
      routeToHash('#consultar'); showGlobal('Filtros carregados. Revise e inicie quando quiser.', 'success');
    } catch (error) { setInlineMessage($('#savedSearchesMessage'), error.message, 'error'); }
  }
  function applyFilters(f) {
    state.legacyCompatibility = null;
    setValues('modality', f.modalidades || []); setValues('sphere', f.esferas || ['E', 'M']);
    $('#profile').value = f.perfil || '';
    if (state.legacyCatalog) setValues('legacy-area', f.areas || []);
    else {
      let sectors = f.setores || []; let services = f.servicos || [];
      if (!f.schema_version && !sectors.length && Array.isArray(f.areas) && f.areas.length) {
        const ids = new Set(catalogEntries().map(item => item.id));
        const prior = f.areas.map(String);
        sectors = prior.filter(id => ids.has(id));
        services = [...new Set([...services, ...prior.filter(id => ['instalacao', 'manutencao', 'fornecimento', 'pecas'].includes(id))])];
        if (!sectors.length && ids.has('climatizacao')) sectors = ['climatizacao'];
        state.legacyCompatibility = { areas: prior, schema_version: 1 };
        showGlobal('Busca antiga: critérios preservados. Revise os filtros antes de iniciar.', 'info');
      }
      setValues('sector', sectors); setValues('service', services); setValues('context', f.contextos || []);
      setValues('subarea', Object.values(f.subareas || {}).flat());
    }
    if (f.dias !== undefined) $('#days').value = f.dias;
    const muni = String(f.municipio ?? f.municipio_ibge ?? '');
    const nomeMuni = muni ? state.municipioPorCodigo.get(muni) : '';
    if (nomeMuni) { $('#municipality').value = muni; $('#municipalityName').value = municipalityLabel(nomeMuni, muni); $('#municipalityCode').value = ''; }
    else { $('#municipality').value = ''; $('#municipalityName').value = ''; $('#municipalityCode').value = muni; }
    if (Array.isArray(f.palavras_chave)) $('#keywords').value = f.palavras_chave.join(', ');
    if (f.intervalo !== undefined) $('#interval').value = f.intervalo;
    $('#meOnly').checked = Boolean(f.me); $('#genericBuilding').checked = Boolean(f.incluir_predial_generico);
    updateSectorDetails(); updateToggleButtons(); updateSectorGroupButtons(); updateSummaries();
  }
  let deleteTarget = null;
  function confirmDelete(file, name) {
    deleteTarget = file; $('#confirmDialogMessage').textContent = `A busca “${name}” será removida. Esta ação não apaga relatórios.`;
    $('#confirmDialog').showModal();
  }
  async function deleteSavedSearch() {
    if (!deleteTarget) return;
    const button = $('#confirmDeleteButton'); button.disabled = true;
    try {
      await api.deleteSearch(deleteTarget); closeDialog($('#confirmDialog'));
      setInlineMessage($('#savedSearchesMessage'), 'Busca excluída.', 'success'); await loadSavedSearches();
    } catch (error) { setInlineMessage($('#savedSearchesMessage'), error.message, 'error'); }
    finally { button.disabled = false; deleteTarget = null; }
  }

  async function loadHistory(pagina = state.historyPage) {
    const host = $('#historyList');
    host.innerHTML = '<div class="loading-block">Carregando histórico…</div>';
    try {
      const result = await api.history(pagina, state.historyPerPage);
      const rows = result.execucoes || result.historico || result.items || [];
      state.historyPage = result.pagina || pagina;
      state.historyPerPage = result.por_pagina || state.historyPerPage;
      state.historyTotal = result.total ?? rows.length;
      state.historyHasNext = Boolean(result.tem_proxima);
      if (!rows.length) {
        host.innerHTML = state.historyPage > 1
          ? '<div class="empty-state compact-empty"><h3>Página sem execuções</h3><p>Volte para a página anterior.</p></div>'
          : '<div class="empty-state compact-empty"><h3>Nenhuma execução no histórico</h3><p>Quando o servidor registrar manifestos de execução, seus relatórios aparecerão aqui.</p></div>';
        renderHistoryPagination(); return;
      }
      host.innerHTML = rows.map(item => {
        const id = item.id || item.consulta_id || item.execucao_id;
        return `<article class="history-row"><div><h3>${escapeHtml(item.data_hora || item.iniciada_em || item.data || 'Execução anterior')}</h3><p>${escapeHtml(item.resumo_filtros || item.resumo || 'Critérios não informados')} · ${escapeHtml(item.resultados ?? item.quantidade ?? 0)} resultados · ${escapeHtml(item.estado || item.status || 'Concluída')}</p></div><div class="row-actions">${id ? `<button class="button button-secondary" type="button" data-open-history="${escapeHtml(id)}">Ver resultados</button><button class="button button-quiet" type="button" data-use-history="${escapeHtml(id)}">Usar filtros</button>` : ''}${item.files?.xlsx ? `<a class="button button-quiet" href="${escapeHtml(item.files.xlsx)}">Baixar Excel</a>` : ''}</div></article>`;
      }).join('');
      renderHistoryPagination();
    } catch (error) {
      host.innerHTML = '<div class="empty-state compact-empty"><h3>Histórico indisponível</h3><p>Esta versão do servidor ainda não fornece a lista de execuções. Os arquivos da última consulta continuam acessíveis quando ela termina.</p></div>';
      setInlineMessage($('#historyMessage'), error.status === 404 ? 'Histórico não fornecido pelo servidor.' : error.message, '');
      state.historyHasNext = false; renderHistoryPagination();
    }
  }
  // Controles "Anterior/Próxima" acessíveis: texto simples (sem depender de ícone), com
  // `disabled` nos extremos e a página atual anunciada para leitor de tela via aria-live.
  function renderHistoryPagination() {
    const host = $('#historyPagination'); if (!host) return;
    if (!state.historyTotal) { host.innerHTML = ''; return; }
    const totalPaginas = Math.max(1, Math.ceil(state.historyTotal / state.historyPerPage));
    host.innerHTML = `<button type="button" class="button button-quiet" id="historyPrev" ${state.historyPage <= 1 ? 'disabled' : ''}>Anterior</button>
      <span class="muted" aria-live="polite">Página ${state.historyPage} de ${totalPaginas} · ${state.historyTotal} execuç${state.historyTotal === 1 ? 'ão' : 'ões'}</span>
      <button type="button" class="button button-quiet" id="historyNext" ${state.historyHasNext ? '' : 'disabled'}>Próxima</button>`;
    $('#historyPrev')?.addEventListener('click', () => loadHistory(state.historyPage - 1));
    $('#historyNext')?.addEventListener('click', () => loadHistory(state.historyPage + 1));
  }
  async function openHistoryItem(id, useFilters = false) {
    try {
      const result = await api.historyItem(id);
      if (useFilters) { applyFilters(result.filtros || result.parametros || {}); routeToHash('#consultar'); showGlobal('Filtros históricos carregados. Inicie quando quiser.', 'success'); return; }
      const snapshot = result.snapshot || result;
      // Um snapshot histórico substitui o que está na tela; não misturar com cartões de uma
      // consulta em andamento (ou de outra execução vista antes).
      state.resultItems.clear(); state.expandedResults.clear();
      state.lastSnapshot = snapshot; renderSnapshot(snapshot); $('#progressPanel').hidden = false; $('#resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) { setInlineMessage($('#historyMessage'), error.status === 404 ? 'Este servidor ainda não oferece a visualização histórica dos resultados.' : error.message, 'error'); }
  }

  function clearFilters() {
    state.legacyCompatibility = null;
    $('#searchForm').reset(); $('#municipality').value = ''; $('#municipalityName').value = ''; $('#municipalityCode').value = '';
    $$('#sectorGroups input, #serviceChoices input, #contextChoices input, #modalityChoices input').forEach(input => { input.checked = false; });
    knownSpheres.forEach(sphere => { const input = $(`#sphereChoices input[value="${sphere.id}"]`); if (input) input.checked = sphere.checked; });
    $('#days').value = 30; $('#interval').value = 2; $('#catalogSearch').value = '';
    updateSectorDetails(); updateToggleButtons(); updateSectorGroupButtons(); updateSummaries(); hideGlobal();
  }
  function removeFilter(group, id) {
    const input = $$(`input[name="${CSS.escape(group)}"]`).find(item => item.value === id);
    if (input) { input.checked = false; if (group === 'sector') updateSectorDetails(); updateSummaries(); }
  }
  function handleClick(event) {
    const button = event.target.closest('button'); if (!button) return;
    if (button.dataset.preset) applyPreset(button.dataset.preset);
    if (button.dataset.selectVisible) {
      const groupName = button.dataset.selectVisible;
      const group = $$('.catalog-group').find(node => $('h3', node)?.textContent === groupName);
      if (group) {
        const inputs = $$('input[name="sector"]', group).filter(input => !input.closest('.sector-option')?.hidden);
        const uncheck = inputs.length > 0 && inputs.every(input => input.checked);
        inputs.forEach(input => { input.checked = !uncheck; });
      }
      updateSectorDetails(); updateSectorGroupButtons(); updateSummaries();
    }
    if (button.dataset.toggleAll) {
      const name = button.dataset.toggleAll;
      const hostId = { service: 'serviceChoices', context: 'contextChoices', modality: 'modalityChoices', sphere: 'sphereChoices' }[name];
      const inputs = $$(`#${hostId} input[type="checkbox"]`);
      const uncheck = inputs.length > 0 && inputs.every(input => input.checked);
      inputs.forEach(input => { input.checked = !uncheck; });
      updateToggleButtons(); updateSummaries();
    }
    if (button.dataset.toggleSubareas) {
      const set = new Set(selectedValues('subarea'));
      const sector = catalogEntries().find(item => item.id === button.dataset.toggleSubareas);
      const visible = (sector?.subareas || []).filter(item => $(`input[name="subarea"][value="${CSS.escape(item.id)}"]`)?.closest('label')?.offsetParent !== null);
      const allChecked = visible.length && visible.every(item => set.has(item.id));
      visible.forEach(item => { const input = $(`input[name="subarea"][value="${CSS.escape(item.id)}"]`); if (input) input.checked = !allChecked; });
      updateSectorGroupButtons(); updateSummaries();
    }
    if (button.dataset.removeGroup) removeFilter(button.dataset.removeGroup, button.dataset.removeId);
    if (button.dataset.toggleSummary) {
      const id = button.dataset.toggleSummary; const node = $(`[data-summary="${CSS.escape(id)}"]`);
      const open = node.hidden; node.hidden = !open; button.setAttribute('aria-expanded', String(open)); button.textContent = open ? 'Fechar resumo' : 'Ver resumo';
      if (open) state.expandedResults.add(id); else state.expandedResults.delete(id);
    }
    if (button.dataset.loadSearch) loadOneSearch(button.dataset.loadSearch);
    if (button.dataset.deleteSearch) confirmDelete(button.dataset.deleteSearch, button.dataset.searchName);
    if (button.dataset.openHistory) openHistoryItem(button.dataset.openHistory);
    if (button.dataset.useHistory) openHistoryItem(button.dataset.useHistory, true);
  }
  function bindEvents() {
    $('#menuToggle').addEventListener('click', () => {
      const nav = $('#mainNav'); const open = !nav.classList.contains('open'); nav.classList.toggle('open', open); $('#menuToggle').setAttribute('aria-expanded', String(open));
    });
    window.addEventListener('hashchange', () => renderPage());
    $('#searchForm').addEventListener('submit', startSearch);
    $('#cancelButton').addEventListener('click', cancelRun);
    $('#catalogSearch').addEventListener('input', renderSectors);
    $('#profile').addEventListener('change', event => applyProfile(event.target.value));
    $('#presetButtons').addEventListener('click', handleClick);
    $('#searchForm').addEventListener('click', handleClick);
    $('#resultsList').addEventListener('click', handleClick);
    $('#savedSearchesList').addEventListener('click', handleClick);
    $('#historyList').addEventListener('click', handleClick);
    $('#searchForm').addEventListener('change', event => {
      if (event.target.matches('input, select') && !['modality', 'sphere'].includes(event.target.name)) state.legacyCompatibility = null;
      if (event.target.name === 'sector') { $('#profile').value = ''; updateSectorDetails(); }
      updateToggleButtons(); updateSectorGroupButtons(); updateSummaries();
    });
    ['days', 'municipalityCode', 'keywords', 'interval', 'meOnly', 'genericBuilding'].forEach(id => {
      $(`#${id}`).addEventListener('input', updateSummaries); $(`#${id}`).addEventListener('change', updateSummaries);
    });
    $('#municipalityName').addEventListener('input', syncMunicipalityFromInput);
    $('#municipalityName').addEventListener('change', syncMunicipalityFromInput);
    $('#showCatalog').addEventListener('click', () => { $('#sectorGroups').scrollIntoView({ behavior: 'smooth', block: 'start' }); $('#catalogSearch').focus(); });
    $('#saveFiltersButton').addEventListener('click', openSaveDialog);
    $('#confirmSaveButton').addEventListener('click', saveCurrentSearch);
    $('#savedSearchName').addEventListener('input', () => { $('#saveSearchError').hidden = true; $('#savedSearchName').removeAttribute('aria-invalid'); });
    $('#confirmDeleteButton').addEventListener('click', deleteSavedSearch);
    $('#clearFiltersButton').addEventListener('click', clearFilters);
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') { $('#mainNav').classList.remove('open'); $('#menuToggle').setAttribute('aria-expanded', 'false'); }
    });
  }
  async function loadOptionalSession() {
    try {
      const result = await api.session(); const session = result.session;
      if (session?.authenticated && session.email) {
        $('#accountArea').hidden = false;
        $('#accountArea').innerHTML = `${escapeHtml(session.email)}${session.logout_url ? `<a href="${escapeHtml(session.logout_url)}">Sair</a>` : ''}`;
      }
      if (result.last_run_id) {
        state.runId = result.last_run_id;
        const snapshot = applyStatusResponse(await api.status(state.runId));
        if (snapshot.running) { state.polling = true; state.runStartedAt = Date.now(); $('#progressPanel').hidden = false; setRunningNotice(true); pollStatus(); }
      }
    } catch { /* Optional route: the screen remains usable when the backend omits sessions. */ }
  }
  async function boot() {
    bindEvents(); renderPage();
    try {
      state.options = await api.options(); renderCatalog();
    } catch (error) {
      state.options = { modalidades: [] }; state.legacyCatalog = true; renderCatalog();
      $('#sectorGroups').innerHTML = `<div class="notice error">${escapeHtml(error.message)} O catálogo não pôde ser carregado.</div>`;
      showGlobal('Não foi possível carregar as opções da busca. Verifique a conexão com o servidor.', 'error');
    }
    // Loading local UI data only. This never invokes /api/start or the PNCP.
    loadOptionalSession();
  }
  boot();
})();
