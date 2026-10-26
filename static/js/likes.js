// Like / unlike without reloading. If anything fails, the form falls back to a normal POST.
(function () {
  'use strict';

  document.querySelectorAll('form[data-like-form]').forEach(function (form) {
    const button = form.querySelector('button');
    const icon = form.querySelector('[data-like-icon]');
    const count = form.querySelector('[data-like-count]');

    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      if (button.classList.contains('is-busy')) return;
      button.classList.add('is-busy');

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form), // includes csrfmiddlewaretoken
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
        });
        if (response.redirected) {
          // Session expired: the backend sent us to the login page.
          window.location.href = response.url;
          return;
        }
        if (!response.ok) throw new Error('Unexpected response');

        const data = await response.json();
        button.classList.toggle('is-liked', data.liked);
        button.setAttribute('aria-pressed', String(data.liked));
        icon.textContent = data.liked ? '♥' : '♡';
        count.textContent = data.count;
      } catch (error) {
        form.submit();
      } finally {
        button.classList.remove('is-busy');
      }
    });
  });
})();
