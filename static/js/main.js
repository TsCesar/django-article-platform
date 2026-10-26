// ArticleHub - small progressive enhancements. Every feature also works without JS.
(function () {
  'use strict';

  // Mobile navigation toggle
  const toggle = document.querySelector('[data-nav-toggle]');
  const menu = document.getElementById('nav-menu');
  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      const open = menu.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
  }

  // Flash messages: manual close + auto-dismiss after a few seconds
  function dismiss(message) {
    message.classList.add('is-hiding');
    setTimeout(function () { message.remove(); }, 300);
  }
  document.querySelectorAll('[data-message]').forEach(function (message) {
    const close = message.querySelector('[data-message-close]');
    if (close) close.addEventListener('click', function () { dismiss(message); });
    if (!message.classList.contains('message-error')) {
      setTimeout(function () { dismiss(message); }, 6000);
    }
  });

  // Confirmation before destructive or important POST actions
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  // Filter selects submit their form on change
  document.querySelectorAll('select[data-autosubmit]').forEach(function (select) {
    select.addEventListener('change', function () { select.form.submit(); });
  });
})();
