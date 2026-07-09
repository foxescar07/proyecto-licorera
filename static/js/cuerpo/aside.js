(function () {

  // ══════════════════════════════════════════
  // PREFERENCIAS DE BARRA LATERAL (definidas en Configuración)
  // Lee el mismo localStorage.cys_config que usa configuracion.html
  // ══════════════════════════════════════════
  let cysSidebarCfg = {};
  try { cysSidebarCfg = JSON.parse(localStorage.getItem('cys_config') || '{}'); } catch (e) {}

  // 1) Mostrar/ocultar sección Resumen (con transición suave, sin recargar)
  const resumenWrap = document.getElementById('cys-sb-resumen-wrap');
  function actualizarResumenWrap(visible) {
    if (!resumenWrap) return;
    resumenWrap.classList.toggle('cys-sb-resumen-oculto', visible === false);
  }
  actualizarResumenWrap(cysSidebarCfg.resumenSidebar);

  // Escucha el cambio en vivo desde la página de Configuración (misma pestaña)
  window.addEventListener('cys-config-changed', function (e) {
    actualizarResumenWrap(e.detail && e.detail.resumenSidebar);
  });

  window.toggleSubmenu = function (e, btn, id) {
    e.stopPropagation();
    const sub = document.getElementById(id);
    sub.classList.toggle('abierto');
    btn.classList.toggle('abierto');
  };

  const normalizePath = p => p.replace(/\/+$/, '') || '/';
  const currentPath = normalizePath(window.location.pathname);
  const links = document.querySelectorAll('.cys-sb-link, .cys-sb-sublink, .cys-sb-user-drop-link');

  let bestMatch = null, maxLength = -1;
  links.forEach(link => {
    const href = link.getAttribute('href');
    if (href && href !== '#') {
      const normalizedHref = normalizePath(href);
      const isExact  = currentPath === normalizedHref;
      const isPrefix = currentPath.startsWith(normalizedHref + '/') ||
                       (currentPath.startsWith(normalizedHref) && normalizedHref !== '/');
      if ((isExact || isPrefix) && normalizedHref.length > maxLength) {
        maxLength = normalizedHref.length; bestMatch = link;
      }
    }
  });

  if (bestMatch) {
    bestMatch.classList.add('active');
    if (bestMatch.classList.contains('cys-sb-sublink')) {
      const parentSubmenu = bestMatch.closest('.cys-sb-submenu');
      if (parentSubmenu) {
        parentSubmenu.classList.add('abierto');
        const parentBtn = parentSubmenu.previousElementSibling;
        if (parentBtn?.classList.contains('cys-sb-link--parent')) {
          parentBtn.classList.add('abierto', 'active');
        }
      }
    }
  }

  if (currentPath.startsWith('/ventas')) {
    document.getElementById('submenuVentas')?.classList.add('abierto');
  }
  if (currentPath.startsWith('/proveedores') || currentPath.startsWith('/compra')) {
    document.getElementById('submenuProveedores')?.classList.add('abierto');

    // Auto-expandir submenu de Compras si estamos en órdenes
    if (currentPath.includes('/ordenes')) {
      const submenuCompras = document.getElementById('submenuCompras');
      if (submenuCompras) {
        submenuCompras.style.display = 'block';
        const chevron = submenuCompras.previousElementSibling.querySelector('.bi-chevron-right');
        if (chevron) chevron.style.transform = 'rotate(90deg)';
      }
    }
  }

  const sidebar = document.getElementById('sidebarRight');
  if (!sidebar) return;
  sidebar.addEventListener('show.bs.offcanvas', () => document.body.classList.add('sidebar-open'));
  sidebar.addEventListener('hide.bs.offcanvas', () => document.body.classList.remove('sidebar-open'));
  if (sidebar.classList.contains('show')) document.body.classList.add('sidebar-open');

})();