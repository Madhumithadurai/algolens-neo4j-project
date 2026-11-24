'use strict';
/* Benchmark tab: run several algorithms over several input sizes and chart them. */
(function () {
  const $ = (id) => document.getElementById(id);
  const ALGOS = {
    search: [['binary', 'Binary search'], ['avl', 'AVL tree search']],
    graph: [['dijkstra', 'Dijkstra'], ['bellman-ford', 'Bellman-Ford'], ['floyd-warshall', 'Floyd-Warshall']],
  };
  const SIZES = { search: '100, 1000, 5000, 10000, 50000', graph: '10, 25, 50, 100, 150' };
  let last = null;

  function init() {
    $('bCategory').addEventListener('change', updateCategory);
    $('bRun').addEventListener('click', () => App.withBusy($('bRun'), 'Running… please wait', run));
    $('bExport').addEventListener('click', exportCsv);
    updateCategory();
  }

  function updateCategory() {
    const cat = $('bCategory').value;
    $('bAlgos').innerHTML = ALGOS[cat]
      .map(([id, name]) => `<label class="check"><input type="checkbox" value="${id}" checked> ${name}</label>`).join('');
    $('bSizes').value = SIZES[cat];
    $('bSizesLabel').textContent = cat === 'search' ? 'Input sizes (number of keys)' : 'Input sizes (number of vertices)';
    document.querySelectorAll('.only-search').forEach((el) => { el.hidden = cat !== 'search'; });
    document.querySelectorAll('.only-graph').forEach((el) => { el.hidden = cat !== 'graph'; });
  }

  async function run() {
    const cat = $('bCategory').value;
    const algorithms = [...$('bAlgos').querySelectorAll('input:checked')].map((i) => i.value);
    if (!algorithms.length) throw new Error('Select at least one algorithm.');
    const sizes = App.parseNumbers($('bSizes').value).map(Math.round);
    const body = {
      category: cat, algorithms, sizes, save: $('bSave').checked,
      repeats: Number($('bRepeats').value), seed: Number($('bSeed').value),
    };
    if (cat === 'search') body.queries = Number($('bQueries').value);
    else { body.density = Number($('bDensity').value); body.weights = $('bWeights').value; }
    const box = $('bSummary');
    box.className = 'summary empty';
    box.textContent = 'Running on the server. Larger sizes take longer…';
    const started = performance.now();
    const data = await App.api.post('/api/benchmark', body);
    data.wallSeconds = (performance.now() - started) / 1000;
    last = data;
    render(data);
    $('bExport').disabled = false;
  }

  function verificationTag(v) {
    if (v === 'match') return '<span class="tag ok">match</span>';
    if (v === 'reference') return '<span class="tag ref">reference</span>';
    if (v === 'mismatch') return '<span class="tag bad">mismatch</span>';
    return '';
  }

  /** Growth summary: how much time grew compared with input size, per algorithm. */
  function observations(data) {
    const isSearch = data.category === 'search';
    const out = [];
    data.parameters.algorithms.forEach((a) => {
      const rows = data.results.filter((r) => r.algorithm === a && r.status === 'ok');
      if (rows.length < 2) return;
      const lo = rows[0], hi = rows[rows.length - 1];
      const tGrow = hi.executionTimeMs / lo.executionTimeMs;
      const x = (v) => (v >= 100 ? Math.round(v).toLocaleString('en-US') : v.toFixed(1));
      const nGrow = hi.inputSize / lo.inputSize;
      let ref = '';
      if (isSearch) ref = `log₂ n grew ×${x(Math.log2(hi.inputSize) / Math.log2(Math.max(lo.inputSize, 2)))}`;
      else if (a === 'floyd-warshall') ref = `V³ grew ×${x(nGrow ** 3)}`;
      else ref = `V grew ×${x(nGrow)}, E grew ×${x(hi.edges / lo.edges)}`;
      out.push(`<li>${App.ALGO_NAMES[a]}: from ${App.num(lo.inputSize)} to ${App.num(hi.inputSize)}, time grew ×${x(tGrow)} (${ref}).</li>`);
    });
    return out.length ? `<ul class="observations">${out.join('')}</ul>` : '';
  }

  function render(data) {
    const isSearch = data.category === 'search';
    const ok = data.results.filter((r) => r.status === 'ok');
    const skipped = data.results.length - ok.length;
    const box = $('bSummary');
    box.className = 'summary';
    box.innerHTML = `<div class="verdict ok">Benchmark finished in ${App.num(data.wallSeconds)} s</div>
      <div class="metrics">
        ${App.metric('Measurements', ok.length)}
        ${App.metric('Skipped', skipped)}
        ${App.metric('Repeats', data.parameters.repeats)}
        ${App.metric('Seed', data.parameters.seed)}
        ${isSearch ? App.metric('Searches per run', App.num(data.parameters.queries)) : App.metric('Density', data.parameters.density)}
        ${App.metric('Recorded in Neo4j', data.savedCount)}
      </div>
      ${observations(data)}
      ${data.recordNote ? `<ul class="notes"><li>${App.esc(data.recordNote)}</li></ul>` : ''}`;

    // charts
    const series = (field, scale) => data.parameters.algorithms.map((a) => ({
      name: App.ALGO_NAMES[a],
      points: data.results.filter((r) => r.algorithm === a && r.status === 'ok')
        .map((r) => ({ x: r.inputSize, y: r[field] * scale })),
    }));
    const xLabel = isSearch ? 'Number of keys (n)' : 'Number of vertices (V)';
    if (isSearch) {
      $('bTimeTitle').textContent = 'Time for one search (µs, median)';
      App.lineChart($('bChartTime'), { series: series('executionTimeMs', 1000), xLabel, yLabel: 'µs per search', unit: 'µs' });
    } else {
      $('bTimeTitle').textContent = 'Time for one run (ms, median)';
      App.lineChart($('bChartTime'), { series: series('executionTimeMs', 1), xLabel, yLabel: 'milliseconds', unit: 'ms' });
    }
    $('bMemTitle').textContent = isSearch ? 'Peak extra memory (KB, includes AVL tree)' : 'Peak memory during one run (KB)';
    App.lineChart($('bChartMem'), { series: series('memoryKb', 1), xLabel, yLabel: 'KB', unit: 'KB' });

    // table
    let h = '<table class="data"><thead><tr>';
    if (isSearch) {
      h += '<th>Algorithm</th><th>Keys</th><th>µs per search</th><th>Batch median (ms)</th><th>± stdev</th><th>Tree build (ms)</th><th>Peak memory (KB)</th><th>Check</th>';
    } else {
      h += '<th>Algorithm</th><th>V</th><th>E</th><th>Density</th><th>Median (ms)</th><th>Mean ± stdev</th><th>Min – max</th><th>Peak memory (KB)</th><th>Check</th>';
    }
    h += '</tr></thead><tbody>';
    data.results.forEach((r) => {
      if (r.status !== 'ok') {
        const cols = isSearch ? 6 : 7;
        h += `<tr><td>${App.ALGO_NAMES[r.algorithm]}</td><td>${App.num(r.inputSize)}</td><td class="text" colspan="${cols}"><span class="tag skip">skipped</span> ${App.esc(r.note || '')}</td></tr>`;
        return;
      }
      if (isSearch) {
        h += `<tr><td>${App.ALGO_NAMES[r.algorithm]}</td><td>${App.num(r.inputSize)}</td><td>${App.num(r.perQueryUs)}</td>
          <td>${App.num(r.totalMedianMs)}</td><td>${App.num(r.totalStdevMs)}</td><td>${r.buildTimeMs === null ? '—' : App.num(r.buildTimeMs)}</td>
          <td>${App.num(r.memoryKb)}</td><td>${verificationTag(r.verification)}</td></tr>`;
      } else {
        h += `<tr><td>${App.ALGO_NAMES[r.algorithm]}</td><td>${App.num(r.inputSize)}</td><td>${App.num(r.edges)}</td><td>${App.num(r.graphDensity)}</td>
          <td>${App.num(r.executionTimeMs)}</td><td>${App.num(r.meanMs)} ± ${App.num(r.stdevMs)}</td><td>${App.num(r.minMs)} – ${App.num(r.maxMs)}</td>
          <td>${App.num(r.memoryKb)}</td><td>${verificationTag(r.verification)}</td></tr>`;
      }
    });
    $('bTable').innerHTML = h + '</tbody></table>';

    const e = data.environment;
    $('bEnv').innerHTML = `Environment: ${App.esc(e.implementation)} ${App.esc(e.pythonVersion)} on ${App.esc(e.platform)}, ${App.esc(e.processor)}, ${e.cpuCount} logical CPUs. Algorithm time excludes input generation and any database access.`;
  }

  function exportCsv() {
    if (!last) return;
    const header = ['algorithm', 'status', 'input_size', 'edges', 'density', 'time_per_run_ms', 'mean_ms', 'stdev_ms',
      'min_ms', 'max_ms', 'build_ms', 'memory_kb', 'queries', 'verification', 'note'];
    const rows = last.results.map((r) => [r.algorithm, r.status, r.inputSize, r.edges, r.graphDensity, r.executionTimeMs,
      r.meanMs ?? r.totalMeanMs, r.stdevMs ?? r.totalStdevMs, r.minMs ?? r.totalMinMs, r.maxMs ?? r.totalMaxMs,
      r.buildTimeMs, r.memoryKb, r.queries, r.verification, r.note]);
    App.downloadCSV(`benchmark_${last.category}_${Date.now()}.csv`, header, rows);
  }

  App.bench = { init };
})();
