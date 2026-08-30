(function () {
  "use strict";

  const danger = [
    "atrasado","atrasada","vencido","vencida","crítico","critico","crítica","critica",
    "cancelado","cancelada","anulado","anulada","rechazado","rechazada","error",
    "sin stock","mora","déficit","deficit"
  ];
  const success = [
    "completado","completada","realizado","realizada","pagado","pagada","cobrado","cobrada",
    "activo","activa","al día","al dia","aprobado","aprobada","disponible","correcto","correcta",
    "finalizado","finalizada"
  ];
  const warning = [
    "pendiente","por vencer","próximo","proximo","próxima","proxima","sin asignar",
    "atención","atencion","bajo","baja","parcial"
  ];
  const info = [
    "programado","programada","hoy","información","informacion","nuevo","nueva",
    "en proceso","proyectado","proyectada"
  ];

  function norm(value) {
    return (value || "").replace(/\s+/g, " ").trim().toLowerCase();
  }
  function matches(text, words) {
    return words.some(word => text === word || text.startsWith(word + " ") || text.endsWith(" " + word));
  }
  function semanticClass(text) {
    if (matches(text, danger)) return "jvs-state-danger";
    if (matches(text, success)) return "jvs-state-success";
    if (matches(text, warning)) return "jvs-state-warning";
    if (matches(text, info)) return "jvs-state-info";
    return "";
  }

  function paintStates(root) {
    const selector = [
      ".badge",".status",".estado",".pill",".chip",
      "[class*='status']","[class*='estado']","[class*='badge']",
      "[class*='pill']","[class*='chip']"
    ].join(",");

    root.querySelectorAll(selector).forEach(el => {
      if (el.closest("script,style")) return;
      const text = norm(el.textContent);
      if (!text || text.length > 70) return;
      const cls = semanticClass(text);
      if (!cls) return;
      el.classList.remove("jvs-state-danger","jvs-state-success","jvs-state-warning","jvs-state-info");
      el.classList.add("jvs-state", cls);
    });
  }

  function paintExplicitNumbers(root) {
    root.querySelectorAll("[data-jv-value]").forEach(el => {
      const raw = String(el.getAttribute("data-jv-value") || "").replace(",", ".");
      const value = Number(raw);
      if (!Number.isFinite(value)) return;
      el.classList.remove("jvs-value-positive","jvs-value-negative","jvs-value-neutral");
      el.classList.add(value > 0 ? "jvs-value-positive" : value < 0 ? "jvs-value-negative" : "jvs-value-neutral");
    });
  }

  function apply(root) {
    paintStates(root || document);
    paintExplicitNumbers(root || document);
  }

  document.addEventListener("DOMContentLoaded", () => {
    apply(document);
    const observer = new MutationObserver(mutations => {
      mutations.forEach(m => {
        m.addedNodes.forEach(node => {
          if (node.nodeType === 1) apply(node);
        });
      });
    });
    observer.observe(document.body, {childList:true, subtree:true});
  });
})();
