(function () {
  const URL_STOCK_STATUS = document.querySelector('.cys-header').dataset.urlStockStatus;

  const INTERVALO = 8000;
  let historialNotif = JSON.parse(localStorage.getItem('cys_notif_historial') || '[]');
  let vistosPrevios = new Set(JSON.parse(localStorage.getItem('cys_notif_vistos') || '[]'));

  window.notifTab = function (tab) {
    const esAlertas = tab === 'alertas';
    document.getElementById('panel-alertas').classList.toggle('d-none', !esAlertas);
    document.getElementById('panel-historial').classList.toggle('d-none', esAlertas);
    document.getElementById('tab-alertas').style.color = esAlertas ? '#4DA8DA' : 'rgba(226,232,240,.4)';
    document.getElementById('tab-alertas').style.borderBottomColor = esAlertas ? '#4DA8DA' : 'transparent';
    document.getElementById('tab-historial').style.color = esAlertas ? 'rgba(226,232,240,.4)' : '#4DA8DA';
    document.getElementById('tab-historial').style.borderBottomColor = esAlertas ? 'transparent' : '#4DA8DA';
  };

  function guardar() {
    localStorage.setItem('cys_notif_historial', JSON.stringify(historialNotif.slice(0, 50)));
    localStorage.setItem('cys_notif_vistos', JSON.stringify([...vistosPrevios]));
  }

  function itemHTML(nombre, cantidad, nivel, fecha) {
    const c = nivel === 'critico' ? '#9b5de5' : '#4DA8DA';
    const label = nivel === 'critico' ? 'crítico' : 'bajo';
    return `<div class="px-3 py-2" style="border-top:1px solid rgba(255,255,255,.05);">
      <div class="d-flex align-items-start gap-2">
        <span style="width:8px; height:8px; border-radius:50%; background:${c}; flex-shrink:0; margin-top:5px;"></span>
        <div style="font-size:12px; line-height:1.4; color:#e2e8f0;">
          ${nombre}<br>
          <small style="color:rgba(226,232,240,.4);">${cantidad} uds — ${label}${fecha ? ' · ' + fecha : ''}</small>
        </div>
      </div>
    </div>`;
  }

  function renderAlertas(criticos, bajos) {
    const panel = document.getElementById('panel-alertas');
    const todos = [
      ...(criticos || []).map(p => ({ ...p, nivel: 'critico' })),
      ...(bajos || []).map(p => ({ ...p, nivel: 'bajo' })),
    ];
    panel.innerHTML = todos.length
      ? todos.map(p => itemHTML(p.nombre, p.total_stock ?? p.cantidad, p.nivel)).join('')
      : `<div class="text-center py-3" style="font-size:12px; color:rgba(226,232,240,.4);">
           <i class="bi bi-check-circle" style="color:#2ecc71;"></i> Sin alertas — todo en orden
         </div>`;
  }

  function renderHistorial() {
    const panel = document.getElementById('panel-historial');
    panel.innerHTML = historialNotif.length
      ? historialNotif.map(n => itemHTML(n.nombre, n.cantidad, n.nivel, n.fecha)).join('')
      : `<div class="text-center py-3" style="font-size:12px; color:rgba(226,232,240,.4);">Sin notificaciones aún</div>`;
  }

  function actualizarBadgeYBounce(total, hayNuevos) {
    const badge = document.getElementById('notif-badge');
    const icono = document.getElementById('notif-bell-icon');
    if (total > 0) {
      badge.textContent = total > 99 ? '99+' : total;
      badge.classList.remove('d-none');
      icono.classList.add('notif-bell-active');
    } else {
      badge.classList.add('d-none');
      icono.classList.remove('notif-bell-active');
    }
  }

  function actualizar() {
    fetch(URL_STOCK_STATUS + "?_=" + Date.now(), {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' }
    })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => {
        const criticos = data.criticos || [];
        const bajos = data.bajos || [];
        renderAlertas(criticos, bajos);

        let hayNuevos = false;
        [...criticos.map(p => ({ ...p, nivel: 'critico' })), ...bajos.map(p => ({ ...p, nivel: 'bajo' }))]
          .forEach(p => {
            const key = p.nombre + '|' + p.nivel;
            if (!vistosPrevios.has(key)) {
              historialNotif.unshift({
                nombre: p.nombre, nivel: p.nivel, cantidad: p.total_stock ?? p.cantidad,
                fecha: new Date().toLocaleString('es-CO', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })
              });
              vistosPrevios.add(key);
              hayNuevos = true;
            }
          });
        if (hayNuevos) { guardar(); renderHistorial(); }

        actualizarBadgeYBounce(data.total_alertas ?? (criticos.length + bajos.length), hayNuevos);
      })
      .catch(() => {});
  }

  renderHistorial();
  actualizar();
  setInterval(actualizar, INTERVALO);
})();