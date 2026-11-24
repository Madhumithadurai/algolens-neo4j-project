'use strict';
/* Searching tab: binary search and AVL tree search. */
(function () {
  const $ = (id) => document.getElementById(id);
  let player;
  let loaded = null;   // {id, text} of the key list loaded from Neo4j

  const HINTS = {
    binary: 'Keys are sorted before searching if needed (sorting is not timed). Each step halves the interval.',
    avl: 'Keys are inserted in the order given. Use the step buttons to watch rotations, then the search path.',
  };

  function init() {
    player = new App.StepPlayer($('sPlayer'), $('sCaption'), renderFrame);
    $('sKeys').value = '42, 7, 19, 88, 3, 56, 23, 71, 15, 64, 30, 95, 11, 37, 50';
    $('sTarget').value = '56';
    $('sAlgo').addEventListener('change', updateHint);
    $('sGenerate').addEventListener('click', () => App.withBusy($('sGenerate'), 'Generating…', generate));
    $('sLoadDs').addEventListener('click', () => App.withBusy($('sLoadDs'), 'Loading…', loadDataset));
    $('sSaveDs').addEventListener('click', () => App.withBusy($('sSaveDs'), 'Saving…', saveDataset));
    $('sRun').addEventListener('click', () => App.withBusy($('sRun'), 'Running…', run));
    updateHint();
  }

  function updateHint() { $('sAlgoHint').textContent = HINTS[$('sAlgo').value]; }

  function setDatasets(list) {
    App.fillDatasetSelect($('sDataset'), list, 'No saved key lists', (d) => `${App.num(d.nodeCount || 0)} keys`);
  }

  function shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  async function generate() {
    const size = Number($('sGenSize').value);
    const data = await App.api.post('/api/generate/array', { size });
    let values = data.values;
    if ($('sAlgo').value === 'avl') values = shuffle(values.slice());
    $('sKeys').value = values.join(', ');
    $('sTarget').value = values[Math.floor(Math.random() * values.length)];
    loaded = null;
  }

  async function loadDataset() {
    const id = $('sDataset').value;
    if (!id) throw new Error('Choose a saved key list first.');
    const ds = await App.api.get('/api/datasets/' + encodeURIComponent(id));
    if (ds.type !== 'array') throw new Error('That dataset is a graph.');
    const text = ds.values.join(', ');
    $('sKeys').value = text;
    $('sTarget').value = ds.values[Math.floor(ds.values.length / 2)];
    loaded = { id, text };
    App.toast(`Loaded "${ds.name}" from Neo4j in ${App.num(ds.dbLoadMs)} ms.`);
  }

  async function saveDataset() {
    const values = App.parseNumbers($('sKeys').value);
    const name = window.prompt('Name for this key list:', `Keys (${values.length})`);
    if (!name) return;
    const res = await App.api.post('/api/datasets', {
      type: 'array', name, values, description: `Saved from AlgoLens on ${new Date().toLocaleString()}`,
    });
    loaded = { id: res.datasetId, text: $('sKeys').value };
    App.toast(`Saved "${name}" to Neo4j.`);
    await App.refreshDatasets();
    $('sDataset').value = res.datasetId;
  }

  async function run() {
    const algo = $('sAlgo').value;
    const text = $('sKeys').value;
    const keys = App.parseNumbers(text);
    if ($('sTarget').value === '') throw new Error('Enter the key to find.');
    const body = { target: Number($('sTarget').value), save: $('sSave').checked };
    if (loaded && loaded.text === text) body.datasetId = loaded.id;   // backend loads and times it
    else body.array = keys;
    const data = await App.api.post(`/api/search/${algo}`, body);
    renderResult(data);
    player.load(algo === 'binary' ? binaryFrames(data) : avlFrames(data), true);
  }

  // ---------------------------------------------------------------- results
  function renderResult(data) {
    const r = data.result, m = data.metrics, t = data.input.target;
    const isAvl = data.algorithm === 'avl';
    let verdict;
    if (r.found) verdict = isAvl ? `Found ${App.num(t)} in the AVL tree` : `Found ${App.num(t)} at index ${r.index}`;
    else verdict = `${App.num(t)} is not among the keys`;

    let html = `<div class="verdict ${r.found ? 'ok' : 'miss'}">${verdict}</div><div class="metrics">`;
    html += App.metric('Keys', App.num(isAvl ? r.size : data.input.size));
    html += App.metric('Comparisons', r.comparisons);
    html += App.metric('Time per search', App.num(m.timePerSearchUs), 'µs');
    if (isAvl) {
      html += App.metric('Tree build', App.num(m.buildTimeMs), 'ms');
      html += App.metric('Tree height', r.height);
      html += App.metric('Rotations', r.rotations);
    }
    html += App.metric('Peak memory', App.num(m.peakMemoryKb), 'KB');
    if (m.dbLoadMs !== null && m.dbLoadMs !== undefined) html += App.metric('Neo4j load', App.num(m.dbLoadMs), 'ms');
    html += '</div><ul class="notes">';
    html += `<li>Time is the median of ${m.repeats} runs of ${App.num(m.innerLoop)} searches (± ${App.num(m.stdevPerSearchUs)} µs).</li>`;
    if (isAvl) html += '<li>Peak memory includes building the tree.</li>';
    if (data.input.wasSorted === false) html += '<li>The keys were not sorted, so they were sorted first. Sorting is not part of the timing.</li>';
    if (isAvl && r.duplicatesIgnored) html += `<li>${r.duplicatesIgnored} duplicate key(s) were ignored.</li>`;
    html += `<li>${data.experimentId ? 'Recorded in Neo4j.' : App.esc(data.recordNote || '')}</li>`;
    html += '</ul>';
    const box = $('sResult');
    box.className = 'summary';
    box.innerHTML = html;
  }

  // ---------------------------------------------------------------- frames
  function binaryFrames(data) {
    const arr = data.result.sortedArray;
    const n = data.input.size;
    const t = App.num(data.input.target);
    const frames = [{ kind: 'array', arr, low: 0, high: n - 1, mid: null, n,
      caption: `Look for <b>${t}</b> among ${App.num(n)} sorted keys. The search interval is [0, ${n - 1}].` }];
    data.result.steps.forEach((s, i) => {
      let cap;
      const head = `Step ${i + 1}: interval [${s.low}, ${s.high}]`;
      if (s.action === 'found') cap = `${head}, middle index ${s.mid} holds ${App.num(s.value)}. That is the key, <b>found at index ${s.mid}</b>.`;
      else if (s.action === 'go-right') cap = `${head}, middle index ${s.mid} holds ${App.num(s.value)} &lt; ${t}. Keep the right half.`;
      else if (s.action === 'go-left') cap = `${head}, middle index ${s.mid} holds ${App.num(s.value)} &gt; ${t}. Keep the left half.`;
      else cap = `The interval is empty (low ${s.low} &gt; high ${s.high}), so <b>${t} is not present</b>.`;
      frames.push({ kind: 'array', arr, n, low: s.low, high: s.high, mid: s.mid,
        found: s.action === 'found', caption: cap });
    });
    return frames;
  }

  function avlFrames(data) {
    const r = data.result;
    const t = App.num(data.input.target);
    const frames = [];
    r.insertSteps.forEach((s) => {
      const rot = s.rotations.length
        ? s.rotations.map((x) => `${x.kind} rotation at ${App.num(x.pivot)}`).join(', ')
        : 'the tree stays balanced, no rotation';
      frames.push({
        kind: 'tree', tree: s.tree || null, inserted: s.key, pivots: s.rotations.map((x) => x.pivot),
        emptyMsg: 'Snapshots after each insertion are kept for up to 128 keys.',
        caption: s.duplicate ? `Insert ${App.num(s.key)}: already in the tree, ignored.`
          : `Insert <b>${App.num(s.key)}</b>: ${rot}.`,
      });
    });
    if (r.stepsTruncated) frames.push({ kind: 'tree', tree: r.tree, caption: 'The insertion log was shortened for this large input.' });
    const drawMsg = `The tree has ${App.num(r.size)} keys, too many to draw. The search path is described above.`;
    frames.push({ kind: 'tree', tree: r.tree, path: [], emptyMsg: drawMsg,
      caption: `Tree built: ${App.num(r.size)} keys, height ${r.height}, ${r.rotations} rotation(s). Now search for <b>${t}</b>.` });
    r.path.forEach((p, i) => {
      const keys = r.path.slice(0, i + 1).map((x) => x.key);
      let cap;
      if (p.action === 'found') cap = `Compare with ${App.num(p.key)}: equal, <b>found after ${i + 1} comparison(s)</b>.`;
      else {
        const dir = p.action === 'go-left' ? 'left' : 'right';
        const rel = p.action === 'go-left' ? '&lt;' : '&gt;';
        cap = `Compare with ${App.num(p.key)}: ${t} ${rel} ${App.num(p.key)}, go ${dir}.`;
        if (i === r.path.length - 1) cap += ` That subtree is empty, so <b>${t} is not in the tree</b>.`;
      }
      frames.push({ kind: 'tree', tree: r.tree, path: keys, current: p.key, found: p.action === 'found',
        emptyMsg: drawMsg, caption: cap });
    });
    return frames;
  }

  // ---------------------------------------------------------------- drawing
  function renderFrame(f) {
    const box = $('sViz');
    if (f.kind === 'array') drawArray(box, f);
    else drawTree(box, f);
  }

  function drawArray(box, f) {
    if (!f.arr) {
      box.innerHTML = `<p class="muted">${App.num(f.n)} keys are too many to draw (limit 256). Follow the steps in the caption.</p>`;
      return;
    }
    const cells = f.arr.map((v, i) => {
      const cls = ['cell'];
      if (i < f.low || i > f.high) cls.push('out');
      if (i === f.mid) cls.push(f.found ? 'found' : 'mid');
      if (i === f.low && f.low <= f.high) cls.push('lo');
      if (i === f.high && f.low <= f.high) cls.push('hi');
      return `<div class="${cls.join(' ')}"><span class="v">${App.num(v)}</span><span class="i">${i}</span></div>`;
    }).join('');
    box.innerHTML = `<div class="cells-wrap"><div class="cells">${cells}</div></div>`;
  }

  function drawTree(box, f) {
    const tree = f.tree;
    if (!tree) {
      box.innerHTML = `<p class="muted">${f.emptyMsg || 'Nothing to draw.'}</p>`;
      return;
    }
    const pos = new Map();
    const list = [];
    let idx = 0, maxDepth = 0;
    (function walk(n, d, parent) {
      if (!n) return;
      walk(n.left, d + 1, n);
      pos.set(n, { x: idx++, d });
      maxDepth = Math.max(maxDepth, d);
      list.push([n, parent]);
      walk(n.right, d + 1, n);
    })(tree, 0, null);

    const dx = 46, dy = 64, r = 17, pad = 24;
    const X = (n) => pad + r + pos.get(n).x * dx;
    const Y = (n) => pad + r + pos.get(n).d * dy;
    const W = pad * 2 + r * 2 + (idx - 1) * dx;
    const H = pad * 2 + r * 2 + maxDepth * dy;
    const pathSet = new Set(f.path || []);
    const pivots = new Set(f.pivots || []);

    let s = `<svg class="tree" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="AVL tree">`;
    list.forEach(([n, p]) => {
      if (!p) return;
      const onPath = pathSet.has(n.key) && pathSet.has(p.key);
      s += `<line class="tedge${onPath ? ' path' : ''}" x1="${X(p)}" y1="${Y(p)}" x2="${X(n)}" y2="${Y(n)}"/>`;
    });
    list.forEach(([n]) => {
      const cls = ['tnode'];
      if (pathSet.has(n.key)) cls.push('path');
      if (n.key === f.current) cls.push(f.found ? 'found' : 'current');
      if (n.key === f.inserted) cls.push('inserted');
      if (pivots.has(n.key)) cls.push('pivot');
      const label = App.num(n.key);
      const size = label.length > 5 ? 9 : label.length > 3 ? 10.5 : 12;
      s += `<g class="${cls.join(' ')}"><circle cx="${X(n)}" cy="${Y(n)}" r="${r}"/>`;
      s += `<text class="key" x="${X(n)}" y="${Y(n) + 4}" text-anchor="middle" style="font-size:${size}px">${label}</text>`;
      s += `<text class="bf" x="${X(n) + r + 2}" y="${Y(n) - r + 4}">${n.balance > 0 ? '+' : ''}${n.balance}</text></g>`;
    });
    s += '</svg>';
    box.innerHTML = s + '<p class="hint" style="margin-top:.5rem">Green ring: key just inserted. Dashed ring: node that was out of balance and rotated. Small numbers: balance factor (left height − right height).</p>';
  }

  App.search = { init, setDatasets };
})();
