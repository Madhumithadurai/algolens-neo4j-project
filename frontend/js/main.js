'use strict';
/* Start-up: tabs, Neo4j status, dataset menus. */
(function () {
  const $ = (id) => document.getElementById(id);
  let lastNeo = null;

  App.refreshDatasets = async function () {
    try {
      const d = await App.api.get('/api/datasets');
      App.search.setDatasets(d.datasets.filter((x) => x.type === 'array'));
      App.graph.setDatasets(d.datasets.filter((x) => x.type !== 'array'));
    } catch (e) { /* status pill already shows the problem */ }
  };

  function setStatus(kind, text, detail) {
    const el = $('dbStatus');
    el.className = 'status status-' + kind;
    el.textContent = text;
    el.title = detail || '';
  }

  async function checkHealth() {
    try {
      const h = await App.api.get('/api/health');
      if (h.neo4j) setStatus('up', 'Neo4j connected', h.neo4jUri);
      else setStatus('down', 'Neo4j offline, runs not recorded', h.neo4jError || '');
      if (h.neo4j !== lastNeo) {
        lastNeo = h.neo4j;
        App.refreshDatasets();
      }
    } catch (e) {
      setStatus('error', 'Backend not reachable', e.message);
      lastNeo = null;
    }
  }

  function showTab(name) {
    document.querySelectorAll('.tab').forEach((t) => {
      const on = t.dataset.tab === name;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', String(on));
    });
    document.querySelectorAll('.panel').forEach((p) => { p.hidden = p.id !== 'tab-' + name; });
    if (name === 'experiments') App.experiments.load().catch((e) => App.toast(e.message, 'error'));
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (location.protocol === 'file:') $('fileBanner').hidden = false;
    document.querySelectorAll('.tab').forEach((t) => t.addEventListener('click', () => showTab(t.dataset.tab)));
    App.search.init();
    App.graph.init();
    App.bench.init();
    App.experiments.init();
    checkHealth();
    setInterval(checkHealth, 15000);
  });
})();
