'use strict';
/* Shortest-path tab: Dijkstra, Bellman-Ford, Floyd-Warshall. */
(function () {
  const $ = (id) => document.getElementById(id);
  const MAX_DRAW = 80;
  let player;
  let coords = {};       // vertex -> {x, y} when a dataset provides a layout
  let loaded = null;     // {id, text, directed} of the graph loaded from Neo4j
  let current = null;    // last run: {algo, graph, data, fwUpdates}

  const SAMPLE = 'A B 4\nA C 2\nB C 1\nB D 5\nC D 8\nC E 10\nD E 2\nD F 6\nE F 2\nF G 3\nE G 7';
  const SAMPLE_COORDS = { A: [10, 50], B: [30, 20], C: [30, 80], D: [55, 30], E: [55, 75], F: [80, 50], G: [95, 85] };

  const HINTS = {
    dijkstra: 'Single source. Needs non-negative weights. Always expands the closest unvisited vertex.',
    'bellman-ford': 'Single source. Allows negative weights, relaxes every edge up to V−1 times and reports negative cycles.',
    'floyd-warshall': 'All pairs. Builds the full distance matrix in O(V³). Source and target only choose the path to highlight.',
  };

  function init() {
    player = new App.StepPlayer($('gPlayer'), $('gCaption'), renderFrame);
    $('gEdges').value = SAMPLE;
    $('gDirected').checked = false;
    Object.entries(SAMPLE_COORDS).forEach(([k, [x, y]]) => { coords[k] = { x, y }; });
    let t;
    $('gEdges').addEventListener('input', () => { clearTimeout(t); t = setTimeout(syncGraph, 250); });
    $('gDirected').addEventListener('change', syncGraph);
    $('gSource').addEventListener('change', () => { if (!current) drawPreview(); });
    $('gAlgo').addEventListener('change', () => { $('gAlgoHint').textContent = HINTS[$('gAlgo').value]; });
    $('gGenerate').addEventListener('click', () => App.withBusy($('gGenerate'), 'Generating…', generate));
    $('gLoadDs').addEventListener('click', () => App.withBusy($('gLoadDs'), 'Loading…', loadDataset));
    $('gSaveDs').addEventListener('click', () => App.withBusy($('gSaveDs'), 'Saving…', saveDataset));
    $('gRun').addEventListener('click', () => App.withBusy($('gRun'), 'Running…', run));
    $('gAlgoHint').textContent = HINTS[$('gAlgo').value];
    syncGraph();
    $('gTarget').value = 'G';
  }

  function setDatasets(list) {
    App.fillDatasetSelect($('gDataset'), list, 'No saved graphs',
      (d) => `${d.nodeCount} vertices, ${d.edgeCount} edges`);
  }

  // ---------------------------------------------------------------- parsing
  function parseGraphText(text) {
    const nodes = [], seen = new Set(), edges = [];
    const add = (n) => { if (!seen.has(n)) { seen.add(n); nodes.push(n); } };
    text.split('\n').forEach((raw, i) => {
      const line = raw.replace(/#.*/, '').trim();
      if (!line) return;
      const parts = line.split(/[\s,]+/).filter(Boolean);
      if (parts.length === 1) { add(parts[0]); return; }
      if (parts.length !== 3) throw new Error(`Line ${i + 1}: write "from to weight", for example "A B 4".`);
      const w = Number(parts[2]);
      if (!Number.isFinite(w)) throw new Error(`Line ${i + 1}: "${parts[2]}" is not a number.`);
      add(parts[0]); add(parts[1]);
      edges.push({ source: parts[0], target: parts[1], weight: w });
    });
    return { nodes, edges };
  }

  function graphToText(nodes, edges) {
    const used = new Set();
    const lines = edges.map((e) => { used.add(e.source); used.add(e.target); return `${e.source} ${e.target} ${e.weight}`; });
    nodes.filter((n) => !used.has(n)).forEach((n) => lines.push(n));
    return lines.join('\n');
  }

  function fillVertexSelect(sel, nodes, allowNone) {
    const keep = sel.value;
    sel.innerHTML = (allowNone ? '<option value="">None</option>' : '') +
      nodes.map((n) => `<option value="${App.esc(n)}">${App.esc(n)}</option>`).join('');
    if (nodes.includes(keep)) sel.value = keep;
  }

  /** Re-read the edge list, refresh the vertex menus and redraw the plain graph. */
  function syncGraph() {
    const msg = $('gParseMsg');
    try {
      const g = parseGraphText($('gEdges').value);
      msg.textContent = `${g.nodes.length} vertices, ${g.edges.length} edges`;
      msg.className = 'hint';
      fillVertexSelect($('gSource'), g.nodes, false);
      fillVertexSelect($('gTarget'), g.nodes, true);
    } catch (e) {
      msg.textContent = e.message;
      msg.className = 'hint error';
    }
    current = null;
    player.clear();
    drawPreview();
  }

  function drawPreview() {
    let g;
    try { g = parseGraphText($('gEdges').value); } catch (e) { return; }
    const graph = { ...g, directed: $('gDirected').checked };
    drawGraph($('gSvg'), graph, null, $('gSource').value);
    $('gTable').innerHTML = '';
  }

  // ---------------------------------------------------------------- actions
  async function generate() {
    const neg = $('gNeg').checked, cyc = $('gNegCycle').checked;
    const body = {
      vertices: Number($('gV').value), density: Number($('gDensity').value),
      minWeight: Number($('gMinW').value), maxWeight: Number($('gMaxW').value),
      negative: neg, negativeCycle: cyc, directed: $('gDirected').checked || neg || cyc,
    };
    const g = await App.api.post('/api/generate/graph', body);
    $('gDirected').checked = g.directed;
    coords = {};
    loaded = null;
    $('gEdges').value = graphToText(g.nodes, g.edges);
    syncGraph();
    if ((neg || cyc) && $('gAlgo').value === 'dijkstra') {
      $('gAlgo').value = 'bellman-ford';
      $('gAlgoHint').textContent = HINTS['bellman-ford'];
    }
    if (g.plantedCycle) App.toast(`Planted negative cycle: ${g.plantedCycle.join(' → ')} → ${g.plantedCycle[0]}`);
  }

  async function loadDataset() {
    const id = $('gDataset').value;
    if (!id) throw new Error('Choose a saved graph first.');
    const ds = await App.api.get('/api/datasets/' + encodeURIComponent(id));
    if (ds.type !== 'graph') throw new Error('That dataset is a key list.');
    coords = {};
    ds.nodes.forEach((n) => { if (n.x !== null && n.y !== null) coords[n.id] = { x: n.x, y: n.y }; });
    const text = graphToText(ds.nodes.map((n) => n.id), ds.edges);
    $('gEdges').value = text;
    $('gDirected').checked = ds.directed;
    loaded = { id, text, directed: ds.directed };
    syncGraph();
    if (ds.edges.some((e) => e.weight < 0) && $('gAlgo').value === 'dijkstra') {
      $('gAlgo').value = 'bellman-ford';
      $('gAlgoHint').textContent = HINTS['bellman-ford'];
    }
    App.toast(`Loaded "${ds.name}" from Neo4j in ${App.num(ds.dbLoadMs)} ms.`);
  }

  async function saveDataset() {
    const g = parseGraphText($('gEdges').value);
    const name = window.prompt('Name for this graph:', `Graph (${g.nodes.length} vertices)`);
    if (!name) return;
    const directed = $('gDirected').checked;
    const res = await App.api.post('/api/datasets', {
      type: 'graph', name, nodes: g.nodes, edges: g.edges, directed, coordinates: coords,
      description: `Saved from AlgoLens on ${new Date().toLocaleString()}`,
    });
    loaded = { id: res.datasetId, text: $('gEdges').value, directed };
    App.toast(`Saved "${name}" to Neo4j.`);
    await App.refreshDatasets();
    $('gDataset').value = res.datasetId;
  }

  async function run() {
    const algo = $('gAlgo').value;
    const text = $('gEdges').value;
    const directed = $('gDirected').checked;
    const g = parseGraphText(text);
    if (!g.nodes.length) throw new Error('Enter at least one edge.');
    const body = {
      source: $('gSource').value, target: $('gTarget').value || null, directed,
      save: $('gSave').checked, repeats: Number($('gRepeats').value) || 5,
    };
    if (loaded && loaded.text === text && loaded.directed === directed) body.datasetId = loaded.id;
    else { body.nodes = g.nodes; body.edges = g.edges; }
    const data = await App.api.post('/api/graph/' + algo, body);
    current = { algo, graph: { ...g, directed }, data };
    renderResult();
    player.load(algo === 'floyd-warshall' ? fwFrames() : singleSourceFrames(), true);
  }

  // ---------------------------------------------------------------- results
  function renderResult() {
    const { algo, data } = current;
    const r = data.result, m = data.metrics, inp = data.input;
    let html = '';
    if (r.negativeCycle) {
      const cyc = r.cycle && r.cycle.length ? r.cycle : r.negativeCycleNodes;
      html += `<div class="verdict bad">Negative cycle found${cyc && cyc.length ? ': ' + cyc.map(App.esc).join(' → ') + (r.cycle ? ' → ' + App.esc(cyc[0]) : '') : ''}</div>`;
    } else {
      html += `<div class="verdict ok">${App.ALGO_NAMES[algo]} finished from ${App.esc(inp.source)}</div>`;
    }
    html += '<div class="metrics">';
    html += App.metric('Vertices', App.num(inp.vertices)) + App.metric('Edges', App.num(inp.edges));
    html += App.metric('Density', App.num(inp.density));
    html += App.metric('Median time', App.num(m.medianMs), 'ms');
    html += App.metric('Mean ± stdev', `${App.num(m.meanMs)} ± ${App.num(m.stdevMs)}`, 'ms');
    html += App.metric('Peak memory', App.num(m.peakMemoryKb), 'KB');
    if (algo === 'dijkstra') html += App.metric('Relaxations', r.relaxations);
    if (algo === 'bellman-ford') html += App.metric('Passes', r.iterations) + App.metric('Relaxations', r.relaxations);
    if (algo === 'floyd-warshall') html += App.metric('Matrix updates', App.num(r.updates));
    if (m.dbLoadMs !== null && m.dbLoadMs !== undefined) html += App.metric('Neo4j load', App.num(m.dbLoadMs), 'ms');
    html += '</div>';

    if (inp.target) {
      if (data.path && data.path.length) {
        html += `<div class="pathline">Path ${App.esc(inp.source)} → ${App.esc(inp.target)}: <b>${data.path.map(App.esc).join(' → ')}</b>, total ${App.dist(data.pathCost)}</div>`;
      } else {
        html += `<div class="pathline">No usable path from ${App.esc(inp.source)} to ${App.esc(inp.target)}.</div>`;
      }
    }
    if (r.negativeCycle) {
      html += '<div class="alert">Shortest distances are undefined for vertices reachable from a negative cycle, because going round the cycle again always lowers the cost. The distances shown are the values when the algorithm stopped.</div>';
    }
    (data.warnings || []).forEach((w) => { html += `<div class="alert">${App.esc(w)}</div>`; });
    html += '<ul class="notes">';
    html += `<li>Time is the median of ${m.repeats} runs without step recording.</li>`;
    if (r.stepsTruncated) html += '<li>The step log was shortened for this large graph. The final result is complete.</li>';
    if (algo === 'floyd-warshall' && !r.initialMatrix) html += '<li>Step playback for Floyd-Warshall is available up to 60 vertices.</li>';
    html += `<li>${data.experimentId ? 'Recorded in Neo4j.' : App.esc(data.recordNote || '')}</li>`;
    html += '</ul>';
    if (algo === 'floyd-warshall') html += '<button class="btn quiet" id="gMatrixCsv">Download distance matrix (CSV)</button>';

    const box = $('gResult');
    box.className = 'summary';
    box.innerHTML = html;
    const btn = $('gMatrixCsv');
    if (btn) btn.addEventListener('click', () => {
      App.downloadCSV('floyd_warshall_matrix.csv', ['from \\ to', ...r.nodes],
        r.matrix.map((row, i) => [r.nodes[i], ...row.map((v) => (v === null ? 'inf' : v))]));
    });
  }

  // ---------------------------------------------------------------- frames
  function singleSourceFrames() {
    const { algo, graph, data } = current;
    const r = data.result;
    const src = r.source;
    const dist = {}, prev = {};
    graph.nodes.forEach((n) => { dist[n] = null; prev[n] = null; });
    dist[src] = 0;
    const visited = new Set();
    const frames = [{ dist: { ...dist }, prev: { ...prev }, visited: new Set(), changed: src,
      caption: `Start: distance to ${App.esc(src)} is 0, every other vertex is ∞.` }];

    r.steps.forEach((s) => {
      const f = { edge: null, current: null, changed: null, edgeKind: s.type };
      if (s.type === 'visit') {
        visited.add(s.node);
        f.current = s.node;
        f.caption = `Take the closest unvisited vertex: <b>${App.esc(s.node)}</b> at distance ${App.dist(s.dist)}. Its distance is now final.`;
      } else if (s.type === 'relax') {
        dist[s.to] = s.newDist;
        prev[s.to] = s.from;
        f.edge = [s.from, s.to];
        f.current = s.from;
        f.changed = s.to;
        f.caption = `${s.iteration ? `Pass ${s.iteration}: ` : ''}edge ${App.esc(s.from)}→${App.esc(s.to)} (weight ${App.num(s.weight)}) improves ${App.esc(s.to)} from ${App.dist(s.oldDist)} to <b>${App.dist(s.newDist)}</b>.`;
      } else if (s.type === 'skip') {
        f.edge = [s.from, s.to];
        f.current = s.from;
        f.caption = `Edge ${App.esc(s.from)}→${App.esc(s.to)} would give ${App.dist(s.candidate)}, not better than ${App.dist(s.current)}. No change.`;
      } else if (s.type === 'iteration') {
        f.caption = `Pass ${s.iteration} of at most ${s.maxIterations}: try to relax every edge.`;
      } else if (s.type === 'converged') {
        f.caption = `Nothing changed in pass ${s.iteration}, so the distances are final and Bellman-Ford stops early.`;
      } else if (s.type === 'negative-cycle') {
        f.edge = [s.from, s.to];
        f.cycle = s.cycle;
        f.caption = `Extra check: edge ${App.esc(s.from)}→${App.esc(s.to)} can still be improved after V−1 passes. That means a <b>negative cycle</b>: ${s.cycle.map(App.esc).join(' → ')} → ${App.esc(s.cycle[0])}.`;
      }
      f.dist = { ...dist };
      f.prev = { ...prev };
      f.visited = new Set(visited);
      frames.push(f);
    });

    if (r.stepsTruncated) frames.push({ dist: { ...dist }, prev: { ...prev }, visited: new Set(visited),
      caption: `The step log stops after ${r.steps.length} steps. The next step shows the final result.` });

    const finalVisited = new Set(algo === 'dijkstra' ? r.visitOrder
      : graph.nodes.filter((n) => r.distances[n] !== null));
    let cap;
    if (r.negativeCycle) cap = `Finished: negative cycle ${r.cycle.map(App.esc).join(' → ')} → ${App.esc(r.cycle[0])} (red).`;
    else {
      cap = `Finished. Green edges form the shortest-path tree from ${App.esc(src)}.`;
      if (data.path && data.path.length > 1) cap += ` The path to ${App.esc(data.input.target)} is pink, cost <b>${App.dist(data.pathCost)}</b>.`;
    }
    frames.push({ final: true, dist: r.distances, prev: r.previous, visited: finalVisited,
      path: r.negativeCycle ? null : data.path, cycle: r.negativeCycle ? r.cycle : null, caption: cap });
    return frames;
  }

  function fwFrames() {
    const r = current.data.result;
    current.fwUpdates = r.steps.filter((s) => s.type === 'update');
    const finalCap = r.negativeCycle
      ? `Finished. Negative diagonal entries (red) reveal a negative cycle through ${r.negativeCycleNodes.map(App.esc).join(', ')}.`
      : `Finished: every entry is a shortest distance.${current.data.path && current.data.path.length > 1 ? ` Path to ${App.esc(current.data.input.target)} highlighted.` : ''}`;
    const final = { fw: true, final: true, matrix: r.matrix, path: r.negativeCycle ? null : current.data.path, caption: finalCap };
    if (!r.initialMatrix) return [final];

    const frames = [{ fw: true, upto: 0, k: null,
      caption: 'Start: 0 on the diagonal, the edge weight where an edge exists, ∞ elsewhere.' }];
    let applied = 0;
    r.steps.forEach((s) => {
      if (s.type === 'k') {
        frames.push({ fw: true, upto: applied, k: s.k,
          caption: `Round k = <b>${App.esc(s.k)}</b>: allow paths that pass through ${App.esc(s.k)}. Shaded row and column are used.` });
      } else {
        applied++;
        frames.push({ fw: true, upto: applied, k: s.k, cell: [s.iIndex, s.jIndex], i: s.i, j: s.j,
          caption: `dist(${App.esc(s.i)}, ${App.esc(s.j)}) improves via ${App.esc(s.k)}: ${App.dist(s.old)} → <b>${App.dist(s.new)}</b>.` });
      }
    });
    if (r.stepsTruncated) frames.push({ fw: true, upto: applied, caption: 'The step log was shortened. The next step shows the final matrix.' });
    frames.push(final);
    return frames;
  }

  function matrixAt(frame) {
    if (frame.matrix) return frame.matrix;
    const r = current.data.result;
    const M = r.initialMatrix.map((row) => row.slice());
    for (let t = 0; t < frame.upto; t++) {
      const u = current.fwUpdates[t];
      M[u.iIndex][u.jIndex] = u.new;
    }
    return M;
  }

  // ---------------------------------------------------------------- drawing
  function renderFrame(frame) {
    const src = current.data.input.source;
    if (frame.fw) {
      const hl = { current: frame.k, changedSet: new Set([frame.i, frame.j].filter(Boolean)), path: frame.path };
      drawGraph($('gSvg'), current.graph, hl, src);
      $('gTable').innerHTML = matrixTable(frame);
    } else {
      drawGraph($('gSvg'), current.graph, frame, src);
      $('gTable').innerHTML = distanceTable(frame);
    }
  }

  function layout(nodes) {
    const W = 640, H = 430, pad = 44;
    const pos = {};
    if (nodes.length && nodes.every((n) => coords[n])) {
      const xs = nodes.map((n) => coords[n].x), ys = nodes.map((n) => coords[n].y);
      const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys);
      nodes.forEach((n) => {
        pos[n] = {
          x: pad + ((coords[n].x - minx) / ((maxx - minx) || 1)) * (W - 2 * pad),
          y: pad + ((coords[n].y - miny) / ((maxy - miny) || 1)) * (H - 2 * pad),
        };
      });
    } else {
      const R = Math.min(W, H) / 2 - pad;
      nodes.forEach((n, i) => {
        const a = -Math.PI / 2 + (2 * Math.PI * i) / nodes.length;
        pos[n] = nodes.length === 1 ? { x: W / 2, y: H / 2 } : { x: W / 2 + R * Math.cos(a), y: H / 2 + R * Math.sin(a) };
      });
    }
    return { pos, W, H };
  }

  function drawGraph(box, graph, f, source) {
    const n = graph.nodes.length;
    if (!n) { box.innerHTML = '<p class="muted">The graph is empty.</p>'; return; }
    if (n > MAX_DRAW) {
      box.innerHTML = `<p class="muted">${n} vertices are too many to draw clearly (limit ${MAX_DRAW}). The table shows the results.</p>`;
      return;
    }
    f = f || {};
    const { pos, W, H } = layout(graph.nodes);
    const r = n > 30 ? 11 : 16;
    const K = (a, b) => a + '\u0001' + b;
    const ek = (a, b) => (graph.directed || a < b ? K(a, b) : K(b, a));
    const edgeSet = new Set(graph.edges.map((e) => K(e.source, e.target)));
    const tree = new Set(), path = new Set(), cyc = new Set();
    if (f.prev && !(f.cycle && f.cycle.length)) Object.entries(f.prev).forEach(([v, u]) => { if (u !== null && u !== undefined) tree.add(ek(u, v)); });
    if (f.path && f.path.length > 1) for (let i = 0; i + 1 < f.path.length; i++) path.add(ek(f.path[i], f.path[i + 1]));
    if (f.cycle && f.cycle.length) f.cycle.forEach((c, i) => cyc.add(ek(c, f.cycle[(i + 1) % f.cycle.length])));
    const active = f.edge ? ek(f.edge[0], f.edge[1]) : null;
    const pathNodes = new Set(f.path || []);
    const cycNodes = new Set(f.cycle || []);

    let s = `<svg class="graph" viewBox="0 0 ${W} ${H}" role="img" aria-label="Weighted graph"><defs>`;
    ['base', 'active', 'skip', 'path', 'cycle', 'tree'].forEach((t) => {
      s += `<marker id="arr-${t}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow arrow-${t}"/></marker>`;
    });
    s += '</defs>';

    graph.edges.forEach((e) => {
      const a = pos[e.source], b = pos[e.target];
      const key = ek(e.source, e.target);
      let cls = 'base';
      if (key === active) cls = f.edgeKind === 'skip' ? 'skip' : 'active';
      else if (cyc.has(key)) cls = 'cycle';
      else if (path.has(key)) cls = 'path';
      else if (tree.has(key)) cls = 'tree';
      const marker = graph.directed ? ` marker-end="url(#arr-${cls})"` : '';
      const wcls = `wlabel${['active', 'path', 'cycle'].includes(cls) ? ' w-' + cls : ''}`;
      if (e.source === e.target) {
        const y = a.y - r;
        s += `<path class="edge e-${cls}" d="M${a.x - 6},${y} C${a.x - 28},${y - 38} ${a.x + 28},${y - 38} ${a.x + 6},${y}"${marker}/>`;
        s += `<text class="${wcls}" x="${a.x}" y="${y - 32}" text-anchor="middle">${App.num(e.weight)}</text>`;
        return;
      }
      const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
      const ux = dx / len, uy = dy / len, nx = -uy, ny = ux;
      const bidir = graph.directed && edgeSet.has(K(e.target, e.source));
      const shift = bidir ? 5 : 0, bend = bidir ? 30 : 0, tip = graph.directed ? r + 2 : r;
      const p1 = { x: a.x + ux * r + nx * shift, y: a.y + uy * r + ny * shift };
      const p2 = { x: b.x - ux * tip + nx * shift, y: b.y - uy * tip + ny * shift };
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      const d = bidir
        ? `M${p1.x.toFixed(1)},${p1.y.toFixed(1)} Q${(mx + nx * bend).toFixed(1)},${(my + ny * bend).toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`
        : `M${p1.x.toFixed(1)},${p1.y.toFixed(1)} L${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
      const lo = bidir ? bend / 2 + 6 : 9;
      s += `<path class="edge e-${cls}" d="${d}"${marker}/>`;
      s += `<text class="${wcls}" x="${(mx + nx * lo).toFixed(1)}" y="${(my + ny * lo + 4).toFixed(1)}" text-anchor="middle">${App.num(e.weight)}</text>`;
    });

    graph.nodes.forEach((name) => {
      const p = pos[name];
      const cls = ['gnode'];
      if (f.visited && f.visited.has(name)) cls.push('visited');
      if (pathNodes.has(name)) cls.push('onpath');
      if (cycNodes.has(name)) cls.push('cycle');
      if (name === f.changed || (f.changedSet && f.changedSet.has(name))) cls.push('changed');
      if (name === f.current) cls.push('current');
      if (name === source) cls.push('source');
      const label = App.esc(name);
      const fs = name.length > 3 ? (r > 12 ? 10 : 8) : (r > 12 ? 13 : 10);
      s += `<g class="${cls.join(' ')}"><circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${r}"/>`;
      s += `<text class="nlabel" x="${p.x.toFixed(1)}" y="${(p.y + fs / 3).toFixed(1)}" text-anchor="middle" style="font-size:${fs}px">${label}</text>`;
      if (f.dist) s += `<text class="dlabel" x="${p.x.toFixed(1)}" y="${(p.y + r + 13).toFixed(1)}" text-anchor="middle">${App.dist(f.dist[name])}</text>`;
      s += '</g>';
    });
    s += '</svg>';
    box.innerHTML = s;
  }

  function distanceTable(f) {
    const rows = current.graph.nodes.map((n) => {
      const cls = [n === f.changed ? 'changed' : '', f.visited && f.visited.has(n) ? 'done' : ''].join(' ').trim();
      const prev = f.prev && f.prev[n] !== null && f.prev[n] !== undefined ? App.esc(f.prev[n]) : '—';
      return `<tr class="${cls}"><td>${App.esc(n)}</td><td>${App.dist(f.dist[n])}</td><td>${prev}</td></tr>`;
    }).join('');
    return `<table class="data"><thead><tr><th>Vertex</th><th>Distance</th><th>Previous</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function matrixTable(f) {
    const r = current.data.result;
    const order = r.nodes;
    if (order.length > 60) return `<p class="muted">The ${order.length}×${order.length} matrix is too large to show. Download it as CSV.</p>`;
    const M = matrixAt(f);
    const k = f.k !== null && f.k !== undefined ? order.indexOf(f.k) : -1;
    let h = '<table class="data matrix"><thead><tr><th></th>' + order.map((n) => `<th>${App.esc(n)}</th>`).join('') + '</tr></thead><tbody>';
    M.forEach((row, i) => {
      h += `<tr><th>${App.esc(order[i])}</th>`;
      row.forEach((v, j) => {
        const cls = [];
        if (i === k || j === k) cls.push('kline');
        if (f.cell && f.cell[0] === i && f.cell[1] === j) cls.push('changed');
        if (i === j && v !== null && v < 0) cls.push('neg');
        h += `<td class="${cls.join(' ')}">${App.dist(v)}</td>`;
      });
      h += '</tr>';
    });
    return h + '</tbody></table>';
  }

  App.graph = { init, setDatasets };
})();
