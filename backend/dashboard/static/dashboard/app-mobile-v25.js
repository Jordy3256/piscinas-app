/* JVAQUA ERP v1.4.0 — mejoras Mobile First no destructivas. */
(() => {
  'use strict';

  function markActionRows() {
    document.querySelectorAll('.card-footer .d-flex, form .d-flex.gap-2').forEach((row) => {
      if (row.querySelector('button[type="submit"], input[type="submit"], a.btn')) row.classList.add('jv25-actions');
    });
  }

  function normalizeMobileForms() {
    document.querySelectorAll('input, select, textarea').forEach((field) => {
      if (!field.getAttribute('autocomplete') && field.type === 'tel') field.setAttribute('autocomplete', 'tel');
      if (field.type === 'number') field.setAttribute('inputmode', 'decimal');
    });
  }

  function keepFocusedFieldVisible() {
    if (!window.matchMedia('(max-width: 767.98px)').matches) return;
    document.addEventListener('focusin', (event) => {
      const field = event.target.closest('input, select, textarea');
      if (!field) return;
      window.setTimeout(() => field.scrollIntoView({ block: 'center', behavior: 'smooth' }), 220);
    });
  }

  function improveExternalActions() {
    document.querySelectorAll('a[href^="https://wa.me/"], a[href*="maps.google"], a[href*="google.com/maps"]').forEach((link) => {
      link.setAttribute('rel', 'noopener noreferrer');
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    markActionRows();
    normalizeMobileForms();
    keepFocusedFieldVisible();
    improveExternalActions();
  });
})();
