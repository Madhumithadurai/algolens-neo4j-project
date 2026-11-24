'use strict';
/* Step player: first / previous / play / next / last over a list of frames. */
App.StepPlayer = class {
  constructor(root, captionEl, onRender) {
    this.root = root;
    this.captionEl = captionEl;
    this.onRender = onRender;
    this.frames = [];
    this.i = 0;
    this.timer = null;
    root.innerHTML = `
      <div class="player">
        <button type="button" class="btn" data-act="first" title="First step" aria-label="First step">⏮</button>
        <button type="button" class="btn" data-act="prev" title="Previous step" aria-label="Previous step">‹</button>
        <button type="button" class="btn" data-act="play" title="Play" aria-label="Play">▶</button>
        <button type="button" class="btn" data-act="stepNext" title="Next step" aria-label="Next step">›</button>
        <button type="button" class="btn" data-act="last" title="Last step" aria-label="Last step">⏭</button>
        <span class="count">no steps</span>
        <select aria-label="Playback speed" title="Playback speed">
          <option value="1200">Slow</option>
          <option value="600" selected>Normal</option>
          <option value="220">Fast</option>
          <option value="40">Very fast</option>
        </select>
      </div>`;
    this.countEl = root.querySelector('.count');
    this.speedEl = root.querySelector('select');
    this.playBtn = root.querySelector('[data-act="play"]');
    root.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-act]');
      if (b && !b.disabled) this[b.dataset.act]();
    });
    this.speedEl.addEventListener('change', () => {
      if (this.timer) { this.pause(); this.play(); }
    });
    this.update();
  }

  load(frames, startAtEnd) {
    this.pause();
    this.frames = frames || [];
    this.i = startAtEnd ? Math.max(0, this.frames.length - 1) : 0;
    this.show();
  }

  clear() {
    this.pause();
    this.frames = [];
    this.i = 0;
    if (this.captionEl) this.captionEl.innerHTML = '';
    this.update();
  }

  show() {
    const f = this.frames[this.i];
    if (f) {
      this.onRender(f, this.i, this.frames.length);
      if (this.captionEl) this.captionEl.innerHTML = f.caption || '';
    }
    this.update();
  }

  update() {
    const n = this.frames.length;
    this.countEl.textContent = n ? `step ${this.i + 1} of ${n}` : 'no steps';
    this.root.querySelectorAll('button').forEach((b) => { b.disabled = n < 2; });
    this.playBtn.textContent = this.timer ? '⏸' : '▶';
    this.playBtn.title = this.timer ? 'Pause' : 'Play';
  }

  first() { this.pause(); this.i = 0; this.show(); }
  last() { this.pause(); this.i = Math.max(0, this.frames.length - 1); this.show(); }
  prev() { this.pause(); if (this.i > 0) { this.i--; this.show(); } }
  stepNext() { this.pause(); this.next(); }

  next() {
    if (this.i < this.frames.length - 1) { this.i++; this.show(); return true; }
    return false;
  }

  play() {
    if (this.timer) { this.pause(); return; }
    if (this.frames.length < 2) return;
    if (this.i >= this.frames.length - 1) { this.i = 0; this.show(); }
    this.timer = setInterval(() => { if (!this.next()) this.pause(); }, Number(this.speedEl.value));
    this.update();
  }

  pause() {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    this.update();
  }
};
