document.addEventListener('DOMContentLoaded', function () {
    // ── SIDEBAR ──
    const sidebarEl = document.getElementById('sidebarRight');
    if (sidebarEl) {
        const bsSidebar = new bootstrap.Offcanvas(sidebarEl, {
            scroll: true,
            backdrop: false
        });
        const menuBtn = document.getElementById('menuBtn');

        // Abrir automáticamente según preferencia de Configuración (cys_config.sidebarAuto)
        let cysCfg = {};
        try { cysCfg = JSON.parse(localStorage.getItem('cys_config') || '{}'); } catch (e) {}
        if (cysCfg.sidebarAuto === true) {
            sidebarEl.classList.add('show');
            document.body.classList.add('sidebar-open');
            sidebarEl.style.visibility = 'visible';
        }

        menuBtn?.addEventListener('click', () => bsSidebar.toggle());

        // En cada evento limpiar lo que Bootstrap intenta poner
        function limpiarBootstrap() {
            document.body.style.removeProperty('padding-right');
            document.body.style.removeProperty('overflow');
        }

        sidebarEl.addEventListener('show.bs.offcanvas', () => {
            document.body.classList.add('sidebar-open');
            limpiarBootstrap();
        });
        sidebarEl.addEventListener('shown.bs.offcanvas', limpiarBootstrap);
        sidebarEl.addEventListener('hide.bs.offcanvas', limpiarBootstrap);
        sidebarEl.addEventListener('hidden.bs.offcanvas', () => {
            document.body.classList.remove('sidebar-open');
            limpiarBootstrap();
        });
    }

    // ── ABRIR SUBMENÚ SEGÚN RUTA ──
    const path = window.location.pathname;
    function abrir(sid, bid) {
        document.getElementById(sid)?.classList.add('abierto');
        document.getElementById(bid)?.classList.add('abierto');
    }
    if (path.startsWith('/ventas/')) abrir('submenuVentas', 'btnVentas');
    if (path.startsWith('/proveedores/') ||
        path.startsWith('/compra/')) abrir('submenuProveedores', 'btnProveedores');
    if (path.startsWith('/productos/')) abrir('submenuProductos', 'btnProductos');
    if (path.startsWith('/inventario/')) abrir('submenuInventario', 'btnInventario');
});