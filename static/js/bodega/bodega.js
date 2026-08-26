/**
 * BODEGA.JS — Módulo de Bodega y Conteo
 * Funcionalidades: Agenda (Tabs/Acordeón), Conteo y UI global
 */

// Limpiar backdrop huérfano SOLO si no hay modal abriendo
window.addEventListener('load', function() {
  setTimeout(function() {
    if (!document.querySelector('.modal.show')) {
      document.querySelectorAll('.modal-backdrop').forEach(function(b) { b.remove(); });
      document.body.classList.remove('modal-open');
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';
    }
  }, 300);
});

// Tooltips globales
window.addEventListener('load', function () {
  document.querySelectorAll('.container-fluid [title]').forEach(function (el) {
    new bootstrap.Tooltip(el, {
      placement: 'top',
      trigger: 'hover'
    });
  });
});

// ── ACORDEÓN "Inventarios Programados": recuerda si estaba abierto ──
(function () {
  const collapseEl = document.getElementById('agendaBody');
  if (!collapseEl) return;
  const KEY = 'cys_agenda_abierta';

  if (sessionStorage.getItem(KEY) === '1') {
    collapseEl.classList.add('show');
  }

  collapseEl.addEventListener('shown.bs.collapse', () => sessionStorage.setItem(KEY, '1'));
  collapseEl.addEventListener('hidden.bs.collapse', () => sessionStorage.setItem(KEY, '0'));
})();

// ── TABS AGENDAS: recuerda el último tab visto (Activos / Historial) ──
(function () {
  const TAB_KEY = 'cys_agenda_tab';

  function filtrarAgendas(tab) {
    document.querySelectorAll('.agenda-item').forEach(item => {
      item.style.display = (item.dataset.categoria === tab) ? '' : 'none';
    });
  }

  document.querySelectorAll('.agenda-tab-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.agenda-tab-btn').forEach(b => {
        b.classList.remove('agenda-tab-activo');
        b.classList.add('agenda-tab-inactivo');
      });
      this.classList.remove('agenda-tab-inactivo');
      this.classList.add('agenda-tab-activo');
      sessionStorage.setItem(TAB_KEY, this.dataset.tab);
      filtrarAgendas(this.dataset.tab);
    });
  });

  // Al cargar la página: restaurar el último tab visto (por defecto "activos")
  const tabGuardado = sessionStorage.getItem(TAB_KEY) || 'activos';
  document.querySelectorAll('.agenda-tab-btn').forEach(b => {
    const esGuardado = b.dataset.tab === tabGuardado;
    b.classList.toggle('agenda-tab-activo', esGuardado);
    b.classList.toggle('agenda-tab-inactivo', !esGuardado);
  });
  filtrarAgendas(tabGuardado);
})();

// ── DROPDOWN CONTEO PRODUCTO ──
document.querySelectorAll('.conteo-prod-item').forEach(function(item) {
  item.addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('conteo-prod-label').textContent = this.textContent.trim();
    document.getElementById('conteo-prod-hidden').value = this.dataset.value;
  });
});