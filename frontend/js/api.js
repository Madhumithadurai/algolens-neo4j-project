'use strict';
/* Shared helpers: API calls, number formatting, small UI utilities. */
window.App = window.App || {};

App.api = {
  async request(method, url, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(url, opts);
    } catch (e) {
      throw new Error('The backend is not reachable. Start it with "python app.py" in the backend folder.');
    }
    let data = null;
    try { data = await res.json(); } catch (e) { /* non-JSON response */ }
    if (!res.ok) throw new Error((data && data.error) || `Request failed with status ${res.status}.`);
    return data;
  },
  get(url) { return this.request('GET', url); },
  post(url, body) { return this.request('POST', url, body); },
};

App.ALGO_NAMES = {
  binary: 'Binary search', avl: 'AVL tree search', dijkstra: 'Dijkstra',
  'bellman-ford': 'Bellman-Ford', 'floyd-warshall': 'Floyd-Warshall',
};

App.esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** General number formatting: integers with separators, other values to ~4 significant digits. */
App.num = function (v) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  if (Number.isInteger(v)) return v.toLocaleString('en-US');
  const a = Math.abs(v);
  if (a >= 1000) return v.toLocaleString('en-US', { maximumFractionDigits: 1 });
  if (a >= 1) return v.toFixed(3).replace(/\.?0+$/, '');
  if (a === 0) return '0';
  return Number(v.toPrecision(3)).toString();
};

/** Distances: null from the backend means infinity. */
App.dist = (v) => (v === null || v === undefined ? '∞' : App.num(v));

App.compact = function (n) {
  if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(n % 1e3 ? 1 : 0) + 'k';
  return App.num(n);
};

App.metric = (label, value, unit) =>
  `<div class="metric"><span class="metric-label">${label}</span><span class="metric-value">${value}${unit ? `<small>${unit}</small>` : ''}</span></div>`;

App.parseNumbers = function (text) {
  const parts = String(text).split(/[\s,;]+/).filter(Boolean);
  if (!parts.length) throw new Error('Enter at least one number.');
  return parts.map((p) => {
    const n = Number(p);
    if (!Number.isFinite(n)) throw new Error(`"${p}" is not a number.`);
    return n;
  });
};

App.toast = function (msg, kind) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (kind ? ' ' + kind : '');
  clearTimeout(App._toastTimer);
  App._toastTimer = setTimeout(() => { t.className = 'toast'; }, kind === 'error' ? 6000 : 3800);
};

/** Disable a button while an async task runs; errors become a toast. */
App.withBusy = async function (btn, label, fn) {
  const old = btn.textContent;
  btn.disabled = true;
  btn.textContent = label;
  try {
    return await fn();
  } catch (e) {
    App.toast(e.message, 'error');
    return undefined;
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
};

App.downloadCSV = function (filename, header, rows) {
  const cell = (v) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const csv = [header, ...rows].map((r) => r.map(cell).join(',')).join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

App.fillDatasetSelect = function (select, datasets, emptyLabel, describe) {
  const keep = select.value;
  if (!datasets.length) {
    select.innerHTML = `<option value="">${emptyLabel}</option>`;
    return;
  }
  select.innerHTML = '<option value="">Choose…</option>' + datasets
    .map((d) => `<option value="${App.esc(d.datasetId)}">${App.esc(d.name)} (${describe(d)})</option>`).join('');
  if (datasets.some((d) => d.datasetId === keep)) select.value = keep;
};
