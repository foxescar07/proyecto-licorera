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

  // ══════════════════════════════════════════
  // MODO MINI (icons-only) + TOOLTIPS
  // ══════════════════════════════════════════
  const KEY_MINI = 'cys_sidebar_mini';
  const ANCHO_FULL = '290px';
  const ANCHO_MINI = '84px';

  const btnMini = document.getElementById('btnMiniSidebar');
  const iconMini = btnMini ? btnMini.querySelector('i') : null;

  // Tooltips de TODO lo que tenga data-bs-toggle="tooltip" dentro del aside
  // (módulos, Ventas/Inventario, avatar, botón de cerrar y botón modo mini).
  // Quedan siempre activos, sin importar si el aside está expandido o compacto.
  let sidebarTooltips = [];
  if (window.bootstrap) {
    sidebarTooltips = Array.from(sidebar.querySelectorAll('[data-bs-toggle="tooltip"]'))
      .map(el => new bootstrap.Tooltip(el, {
        trigger: 'hover',
        placement: el.getAttribute('data-bs-placement') || 'right',
        container: 'body' // evita que el overflow del sidebar los recorte
      }));
  }

  // Ajusta la variable CSS que usa base.css para el espacio que le deja
  // al header/subnav/main, según el ancho real del sidebar en este momento.
  function actualizarOffsetLayout(activo) {
    document.documentElement.style.setProperty('--sidebar-offset', activo ? ANCHO_MINI : ANCHO_FULL);
  }

  function aplicarModoMini(activo) {
    sidebar.classList.toggle('cys-sb-mini', activo);

    // Forzamos el ancho directo por JS (gana sobre cualquier otra regla CSS,
    // incluida la de #sidebarRight { width: 290px !important } en base.css).
    if (activo) {
      sidebar.style.setProperty('width', ANCHO_MINI, 'important');
    } else {
      sidebar.style.removeProperty('width');
    }

    actualizarOffsetLayout(activo);

    if (iconMini) {
      iconMini.classList.toggle('bi-chevron-double-left', !activo);
      iconMini.classList.toggle('bi-chevron-double-right', activo);
    }
  }

  let miniActivo = cysSidebarCfg.sidebarMini || localStorage.getItem(KEY_MINI) === '1';
  aplicarModoMini(miniActivo);

  // Si el sidebar ya estaba abierto al cargar la página (sidebarAuto),
  // aseguramos que el layout tenga el offset correcto desde el inicio.
  if (sidebar.classList.contains('show')) actualizarOffsetLayout(miniActivo);

  if (btnMini) {
    btnMini.addEventListener('click', () => {
      miniActivo = !miniActivo;
      localStorage.setItem(KEY_MINI, miniActivo ? '1' : '0');
      aplicarModoMini(miniActivo);
    });
  }

})();