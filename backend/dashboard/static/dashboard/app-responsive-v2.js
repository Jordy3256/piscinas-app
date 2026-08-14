/* Mejoras progresivas de interfaz; no altera datos ni lógica del negocio. */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('table').forEach((table) => {
    if (table.closest('.table-responsive, .jv-table-scroll')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'jv-table-scroll';
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  });

  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', () => {
      const submit = form.querySelector('button[type="submit"], input[type="submit"]');
      if (!submit || submit.dataset.noBusy === 'true') return;
      window.setTimeout(() => {
        submit.classList.add('jv-submit-busy');
        submit.setAttribute('aria-busy', 'true');
      }, 60);
    });
  });
});
