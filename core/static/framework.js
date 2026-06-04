/* Miskamo Framework — shared UI utilities */
var _T = {};

function T(k) { return _T[k] || k; }

function id(s) { return document.getElementById(s); }

function q(s) { return document.querySelector(s); }

function qa(s) { return document.querySelectorAll(s); }

function toast(msg, type) {
  type = type || 'info';
  var bg = type === 'ok' ? '#4caf50' : type === 'err' ? '#f44336' : '#ff9800';
  var c = document.getElementById('toast-container');
  if (!c) {
    c = document.createElement('div'); c.id = 'toast-container';
    c.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem';
    document.body.appendChild(c);
  }
  var t = document.createElement('div');
  t.style.cssText = 'background:' + bg + ';color:#fff;padding:.7rem 1.2rem;border-radius:8px;font-size:.9rem;box-shadow:0 4px 14px rgba(0,0,0,.3);opacity:0;transition:opacity .3s';
  t.textContent = msg;
  c.appendChild(t);
  requestAnimationFrame(function(){ t.style.opacity = '1'; });
  var sec = window._toastSec || 6;
  setTimeout(function(){ t.style.opacity = '0'; setTimeout(function(){ t.remove(); }, 400); }, sec * 1000);
}

/* TabManager — minimal contract for module tabs */
var TabManager = {
  current: null,
  init: function(tabId) {
    if (this.current && this.current !== tabId) {
      var prev = document.querySelector('.tab-content.active');
      if (prev) { prev.classList.remove('active'); }
    }
    this.current = tabId;
    var el = id('tab-' + tabId);
    if (el) { el.classList.add('active'); }
  }
};

/* Standard tab switch */
function switchTab(tabId) {
  /* hide all tab-content */
  qa('.tab-content').forEach(function(el) { el.classList.remove('active'); });
  /* show target */
  var el = id('tab-' + tabId);
  if (el) { el.classList.add('active'); }
  /* update nav active */
  qa('.nav-tab').forEach(function(n) { n.classList.remove('active'); });
  var nav = q('.nav-tab[data-tab="' + tabId + '"]');
  if (nav) { nav.classList.add('active'); }
  TabManager.current = tabId;
  localStorage.setItem('last_tab', tabId);
}
