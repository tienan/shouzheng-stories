(() => {
  'use strict';
  const root = document.documentElement;
  const PREFS = 'sz.preferences';
  const POSITION = 'sz.reading';
  let preferences = {};
  const read = key => {
    try { return JSON.parse(localStorage.getItem(key) || 'null'); }
    catch { return null; }
  };
  const write = (key, value) => { try { localStorage.setItem(key, JSON.stringify(value)); } catch {} };
  const stored = read(PREFS);
  if (stored && typeof stored === 'object') preferences = stored;
  let fontSize = Number(preferences.fontSize);
  if (!Number.isFinite(fontSize) || fontSize < 16 || fontSize > 28) fontSize = 20;
  let width = preferences.width === 860 ? 860 : 720;
  const feedback = document.querySelector('#reader-feedback');
  const announce = text => { if (feedback) feedback.textContent = text; };
  function theme(value) {
    root.dataset.theme = ['light', 'dark', 'sepia'].includes(value) ? value : 'light';
    preferences.theme = root.dataset.theme;
    document.querySelectorAll('.theme-toggle').forEach(button => {
      const dark = root.dataset.theme === 'dark';
      button.setAttribute('aria-label', dark ? '切换日间模式' : '切换夜间模式');
      button.setAttribute('title', dark ? '切换日间模式' : '切换夜间模式');
      const label = button.querySelector('.theme-label');
      if (label) label.textContent = dark ? '日读' : '夜读';
    });
    document.querySelectorAll('[data-paper]').forEach(button => button.setAttribute('aria-pressed', String(root.dataset.theme === 'sepia')));
    write(PREFS, preferences);
  }
  theme(preferences.theme || 'light');
  document.querySelectorAll('.theme-toggle').forEach(button => button.addEventListener('click', () => theme(root.dataset.theme === 'dark' ? 'light' : 'dark')));
  document.querySelectorAll('[data-paper]').forEach(button => button.addEventListener('click', () => {
    theme(root.dataset.theme === 'sepia' ? 'light' : 'sepia');
    announce(root.dataset.theme === 'sepia' ? '已切换暖纸模式' : '已切换日间模式');
  }));
  function applyFont() {
    root.style.setProperty('--reader-size', fontSize + 'px');
    preferences.fontSize = fontSize;
    document.querySelectorAll('[data-font="smaller"]').forEach(button => button.disabled = fontSize <= 16);
    document.querySelectorAll('[data-font="larger"]').forEach(button => button.disabled = fontSize >= 28);
    write(PREFS, preferences);
  }
  applyFont();
  document.querySelectorAll('[data-font]').forEach(button => button.addEventListener('click', () => {
    fontSize = Math.max(16, Math.min(28, fontSize + (button.dataset.font === 'larger' ? 2 : -2)));
    applyFont();
    announce('正文字号 ' + fontSize + ' 像素');
  }));
  function applyWidth() {
    root.style.setProperty('--reader-width', width + 'px');
    preferences.width = width;
    document.querySelectorAll('[data-width]').forEach(button => {
      button.textContent = width === 860 ? '窄版' : '宽版';
      button.setAttribute('aria-pressed', String(width === 860));
    });
    write(PREFS, preferences);
  }
  applyWidth();
  document.querySelectorAll('[data-width]').forEach(button => button.addEventListener('click', () => {
    width = width === 720 ? 860 : 720;
    applyWidth();
    announce(width === 860 ? '已切换宽版阅读' : '已切换窄版阅读');
  }));
  const savedPosition = read(POSITION);
  const continueLink = document.querySelector('#continue-reading');
  const siteRoot = new URL(document.body.dataset.siteRoot || './', location.href);
  if (continueLink && savedPosition && typeof savedPosition.path === 'string') {
    const destination = new URL(savedPosition.path, location.origin);
    if (destination.origin === location.origin && destination.pathname.startsWith(siteRoot.pathname + 'meiji/')) {
      continueLink.href = destination.pathname + '#resume';
      continueLink.textContent = '继续阅读：' + (savedPosition.title || '明治未明') + ' →';
      continueLink.hidden = false;
    }
  }
  const article = document.querySelector('article[data-reader-title]');
  const progress = document.querySelector('.reading-progress');
  const backTop = document.querySelector('.back-top');
  if (!article) return;
  const clamp = x => Math.max(0, Math.min(1, x));
  function articleRange() {
    const top = article.getBoundingClientRect().top + scrollY;
    return { top, length: Math.max(1, article.offsetHeight - innerHeight * 0.7) };
  }
  if (location.hash === '#resume' && savedPosition && savedPosition.path === location.pathname && Number.isFinite(savedPosition.ratio)) {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const range = articleRange();
      window.scrollTo({ top: range.top + range.length * clamp(savedPosition.ratio), behavior: 'instant' });
    }));
  }
  let scheduled = false;
  let lastWrite = 0;
  function update() {
    scheduled = false;
    const range = articleRange();
    const ratio = clamp((scrollY - range.top) / range.length);
    if (progress) progress.style.width = ratio * 100 + '%';
    if (backTop) backTop.hidden = scrollY < 500;
    if (Date.now() - lastWrite > 500) {
      write(POSITION, { path: location.pathname, ratio, title: article.dataset.readerTitle });
      lastWrite = Date.now();
    }
  }
  function schedule() {
    if (!scheduled) { scheduled = true; requestAnimationFrame(update); }
  }
  addEventListener('scroll', schedule, { passive: true });
  addEventListener('resize', schedule, { passive: true });
  addEventListener('pagehide', () => {
    const range = articleRange();
    write(POSITION, { path: location.pathname, ratio: clamp((scrollY - range.top) / range.length), title: article.dataset.readerTitle });
  });
  if (backTop) backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }));
  update();
})();
