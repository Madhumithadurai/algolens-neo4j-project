'use strict';
/* Small dependency-free SVG line chart. */
(function () {
  function niceTicks(min, max, count) {
    if (max === min) max = min + 1;
    const raw = (max - min) / count;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const r = raw / mag;
    const step = (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * mag;
    const out = [];
    for (let v = Math.floor(min / step) * step; out.length < 60; v += step) {
      out.push(+v.toFixed(10));
      if (v >= max - 1e-12) break;
    }
    return out;
  }

  /**
   * opts: { series: [{name, points:[{x,y}]}], xLabel, yLabel, unit }
   */
  App.lineChart = function (container, opts) {
    const series = (opts.series || []).filter((s) => s.points.length);
    if (!series.length) {
      container.innerHTML = '<p class="muted">Nothing to plot yet.</p>';
      return;
    }
    const W = 640, H = 320, m = { l: 66, r: 18, t: 14, b: 50 };
    const pts = series.flatMap((s) => s.points);
    const xs = [...new Set(pts.map((p) => p.x))].sort((a, b) => a - b);
    const xmin = xs[0], xmax = xs[xs.length - 1];
    const logX = xmin > 0 && xmax / xmin >= 50;
    const yTicks = niceTicks(0, Math.max(...pts.map((p) => p.y)) || 1, 5);
    const ymax = yTicks[yTicks.length - 1];
    const tx = (v) => (logX ? Math.log10(v) : v);
    const sx = (v) => (xmin === xmax ? m.l + (W - m.l - m.r) / 2
      : m.l + ((tx(v) - tx(xmin)) / (tx(xmax) - tx(xmin))) * (W - m.l - m.r));
    const sy = (v) => H - m.b - (v / ymax) * (H - m.t - m.b);

    let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${App.esc(opts.yLabel)} against ${App.esc(opts.xLabel)}">`;
    yTicks.forEach((t) => {
      const y = sy(t);
      s += `<line class="grid" x1="${m.l}" x2="${W - m.r}" y1="${y}" y2="${y}"/>`;
      s += `<text class="tick" x="${m.l - 8}" y="${y + 4}" text-anchor="end">${App.num(t)}</text>`;
    });
    let xTicks = xs;
    if (!logX && xs.length > 10) xTicks = niceTicks(xmin, xmax, 6).filter((t) => t >= xmin && t <= xmax);
    xTicks.forEach((t) => {
      const x = sx(t);
      s += `<line class="grid" x1="${x}" x2="${x}" y1="${m.t}" y2="${H - m.b}"/>`;
      s += `<text class="tick" x="${x}" y="${H - m.b + 17}" text-anchor="middle">${App.compact(t)}</text>`;
    });
    s += `<line class="axis" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`;
    s += `<line class="axis" x1="${m.l}" x2="${m.l}" y1="${m.t}" y2="${H - m.b}"/>`;
    s += `<text class="axis-label" x="${(m.l + W - m.r) / 2}" y="${H - 10}" text-anchor="middle">${App.esc(opts.xLabel)}${logX ? ' (log scale)' : ''}</text>`;
    s += `<text class="axis-label" transform="translate(16 ${(m.t + H - m.b) / 2}) rotate(-90)" text-anchor="middle">${App.esc(opts.yLabel)}</text>`;

    series.forEach((ser, i) => {
      const c = 's' + ((i % 5) + 1);
      const sorted = [...ser.points].sort((a, b) => a.x - b.x);
      s += `<polyline class="line ${c}" points="${sorted.map((p) => `${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ')}"/>`;
      sorted.forEach((p) => {
        s += `<circle class="dot ${c}" cx="${sx(p.x).toFixed(1)}" cy="${sy(p.y).toFixed(1)}" r="4.5"><title>${App.esc(ser.name)}: ${App.num(p.y)} ${App.esc(opts.unit || '')} at n = ${App.num(p.x)}</title></circle>`;
      });
    });
    s += '</svg>';
    const legend = series.map((ser, i) => `<span style="--c: var(--s${(i % 5) + 1})">${App.esc(ser.name)}</span>`).join('');
    container.innerHTML = s + `<div class="legend">${legend}</div>`;
  };
})();
