'use strict';
/* Experiment history tab: every recorded run, read back from Neo4j. */
(function () {
  const $ = (id) => document.getElementById(id);
  let rows = [];

  function init() {
    $('eRefresh').addEventListener('click', () => App.withBusy($('eRefresh'), 'Loading…', load));
    $('eFilter').addEventListener('change', () => load().catch((e) => App.toast(e.message, 'error')));
    $('eExport').addEventListener('click', exportCsv);
  }

  async function load() {
    const algo = $('eFilter').value;
    const data = await App.api.get('/api/experiments' + (algo ? `?algorithm=${encodeURIComponent(algo)}` : ''));
    if (!data.available) {
      rows = [];
      $('eStatus').textContent = '';
      $('eTable').innerHTML = '<div class="summary empty">Neo4j is not connected. Start the database and check the password in backend/.env, then refresh.</div>';
      $('eExport').disabled = true;
      return;
    }
    rows = data.experiments;
    $('eStatus').textContent = `${rows.length} run(s), newest first`;
    $('eExport').disabled = !rows.length;
    if (!rows.length) {
      $('eTable').innerHTML = '<div class="summary empty">No runs recorded yet. Run an algorithm or a benchmark with “Record in Neo4j” switched on.</div>';
      return;
    }
    const body = rows.map((e) => `<tr>
      <td>${App.esc(formatDate(e.createdAt))}</td>
      <td class="text">${App.ALGO_NAMES[e.algorithm] || App.esc(e.algorithm)}</td>
      <td class="text">${App.esc(e.mode || '')}</td>
      <td>${App.num(e.inputSize)}</td>
      <td>${e.edgeCount === undefined ? '—' : App.num(e.edgeCount)}</td>
      <td>${e.graphDensity === undefined ? '—' : App.num(e.graphDensity)}</td>
      <td>${App.num(e.executionTimeMs)}</td>
      <td>${App.num(e.memoryKb)}</td>
      <td>${e.dbLoadMs === undefined ? '—' : App.num(e.dbLoadMs)}</td>
      <td class="text">${App.esc(e.datasetName || '—')}</td>
      <td class="text">${App.esc(e.verification || (e.negativeCycle ? 'negative cycle' : ''))}</td>
    </tr>`).join('');
    $('eTable').innerHTML = `<table class="data"><thead><tr><th>Recorded</th><th>Algorithm</th><th>Mode</th><th>n / V</th><th>E</th>
      <th>Density</th><th>Time per run (ms)</th><th>Memory (KB)</th><th>Neo4j load (ms)</th><th>Dataset</th><th>Note</th></tr></thead>
      <tbody>${body}</tbody></table>`;
  }

  function formatDate(s) {
    if (!s) return '';
    const d = new Date(s.replace(/\[.*\]$/, ''));
    return Number.isNaN(d.getTime()) ? s : d.toLocaleString();
  }

  function exportCsv() {
    const header = ['created_at', 'algorithm', 'mode', 'input_size', 'edges', 'density', 'time_ms', 'memory_kb',
      'db_load_ms', 'build_ms', 'repeats', 'dataset', 'python', 'experiment_id'];
    App.downloadCSV('experiments.csv', header, rows.map((e) => [e.createdAt, e.algorithm, e.mode, e.inputSize, e.edgeCount,
      e.graphDensity, e.executionTimeMs, e.memoryKb, e.dbLoadMs, e.buildTimeMs, e.repeats, e.datasetName, e.pythonVersion, e.experimentId]));
  }

  App.experiments = { init, load };
})();
