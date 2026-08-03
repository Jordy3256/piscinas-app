/* JVAQUA ERP v1.3.0 — mejoras progresivas de UX.
   No modifica datos ni reglas de negocio. */
(() => {
  'use strict';

  const sameOrigin = (url) => {
    try { return new URL(url, window.location.href).origin === window.location.origin; }
    catch (_) { return false; }
  };

  const fallbackForPath = (path) => {
    if (path.startsWith('/dashboard/finanzas/')) return '/dashboard/finanzas/flujo/';
    if (path.startsWith('/dashboard/clientes/') || path.startsWith('/dashboard/contratos/')) return '/dashboard/clientes/';
    if (path.startsWith('/dashboard/inventario/')) return '/dashboard/inventario/';
    if (path.startsWith('/dashboard/operativo/') || path.includes('/mantenimientos/')) return '/dashboard/operativo/';
    if (path.startsWith('/dashboard/notificaciones/')) return '/dashboard/inicio/';
    return '/dashboard/inicio/';
  };

  const titleCase = (value) => value
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

  function improveBackNavigation() {
    const oldButton = document.getElementById('jv-back-button');
    if (!oldButton) return;

    // Clonar elimina listeners heredados de versiones anteriores y evita doble navegación.
    const button = oldButton.cloneNode(true);
    oldButton.replaceWith(button);

    const crumb = document.getElementById('jv-breadcrumb');
    const current = window.location.href;
    const referrer = document.referrer;
    const validReferrer = referrer && sameOrigin(referrer) && referrer !== current;

    button.addEventListener('click', () => {
      if (validReferrer && window.history.length > 1) {
        window.history.back();
        return;
      }
      window.location.assign(fallbackForPath(window.location.pathname));
    });

    if (crumb) {
      const labels = window.location.pathname
        .split('/')
        .filter(Boolean)
        .filter((part) => !/^\d+$/.test(part))
        .map(titleCase);
      crumb.textContent = labels.join(' › ');
      crumb.setAttribute('title', crumb.textContent);
    }
  }

  function prepareResponsiveTables() {
    document.querySelectorAll('table').forEach((table) => {
      if (table.dataset.jvTableMode === 'scroll' || table.classList.contains('calendar')) return;
      if (table.dataset.jvMobile === 'off') return;

      const headers = Array.from(table.querySelectorAll('thead th')).map((th) => th.textContent.trim());
      if (!headers.length) return;

      table.classList.add('jv-mobile-table');
      table.querySelectorAll('tbody tr').forEach((row) => {
        const cells = Array.from(row.children).filter((cell) => cell.tagName === 'TD');
        if (cells.length === 1 && cells[0].hasAttribute('colspan')) row.classList.add('jv-empty-row');
        cells.forEach((cell, index) => {
          if (!cell.hasAttribute('data-jv-label')) {
            cell.setAttribute('data-jv-label', headers[index] || '');
          }
        });
      });
    });
  }

  function improveForms() {
    document.querySelectorAll('form').forEach((form) => {
      const actionRow = form.querySelector('.jv-form-actions');
      if (actionRow) actionRow.classList.add('jv-mobile-actions');

      form.addEventListener('submit', () => {
        const submit = form.querySelector('button[type="submit"], input[type="submit"]');
        if (!submit || submit.dataset.noBusy === 'true' || submit.classList.contains('jv-submit-busy')) return;
        window.setTimeout(() => {
          submit.classList.add('jv-submit-busy');
          submit.setAttribute('aria-busy', 'true');
          submit.setAttribute('aria-disabled', 'true');
        }, 80);
      });
    });
  }

  function preserveListContext() {
    const path = window.location.pathname;
    const key = `jv13:list:${path}`;

    if (window.location.search) sessionStorage.setItem(key, window.location.href);
    sessionStorage.setItem('jv13:last-page', window.location.href);

    // Guardar posición de desplazamiento para volver al mismo punto.
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(() => {
        sessionStorage.setItem(`jv13:scroll:${window.location.href}`, String(window.scrollY));
        ticking = false;
      });
    }, { passive: true });

    window.addEventListener('pageshow', (event) => {
      if (!event.persisted) return;
      const stored = Number(sessionStorage.getItem(`jv13:scroll:${window.location.href}`) || 0);
      if (stored > 0) window.scrollTo({ top: stored, behavior: 'auto' });
    });
  }

  function labelIconButtons() {
    document.querySelectorAll('a.btn, button.btn').forEach((control) => {
      if (control.getAttribute('aria-label') || control.textContent.trim()) return;
      const title = control.getAttribute('title');
      if (title) control.setAttribute('aria-label', title);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    improveBackNavigation();
    prepareResponsiveTables();
    improveForms();
    preserveListContext();
    labelIconButtons();
  });
})();
