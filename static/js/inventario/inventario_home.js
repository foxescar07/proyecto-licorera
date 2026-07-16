/**
 * INVENTARIO_HOME.JS — Dashboard Principal de Inventario
 * Funcionalidades: DataTables, escaneo QR, análisis de rotación, dropdown modales
 */

// ── DATATABLE MOVIMIENTOS ──
$(document).ready(function () {
  // Tabla movimientos
  if ($.fn.DataTable.isDataTable('#tablaMovimientos')) {
    $('#tablaMovimientos').DataTable().destroy();
  }
  $('#tablaMovimientos').DataTable({
    paging: false,
    searching: false,
    info: false,
    ordering: true,
    responsive: true,
    columnDefs: [
      { orderable: false, targets: [8] }  // Acciones no ordenable
    ],
    language: {
      emptyTable: "No hay movimientos para este día."
    },
    dom: 'rt'
  });

  // Tabla registrar códigos
  if ($.fn.DataTable.isDataTable('#tabla-codigos')) {
    $('#tabla-codigos').DataTable().destroy();
  }
  $('#tabla-codigos').DataTable({
    paging: false,
    searching: false,
    info: false,
    ordering: true,
    responsive: true,
    columnDefs: [
      { orderable: false, targets: [0] }  // # no ordenable
    ],
    language: {
      emptyTable: "No hay productos registrados."
    },
    dom: 'rt'
  });

  // Tabla catálogo lista
  if ($.fn.DataTable.isDataTable('#cat-list table')) {
    $('#cat-list table').DataTable().destroy();
  }
  var tablaCatalogo = $('#cat-list table').DataTable({
    paging: false,
    searching: false,
    info: false,
    ordering: true,
    responsive: true,
    columnDefs: [
      { orderable: false, targets: [0] }  // # no ordenable
    ],
    dom: 'rt'
  });
});
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

// ── FORMATO DE PRECIOS (puntos de miles, es-CO) ──
function formatMiles(n) {
  var num = parseInt(String(n).replace(/\D/g, ''), 10);
  if (isNaN(num)) return n;
  return num.toLocaleString('es-CO');
}

document.querySelectorAll('.precio-fmt').forEach(function (el) {
  var texto = el.textContent.trim();
  var num = texto.replace('$', '').replace(/\./g, '').trim();
  if (num && !isNaN(num) && parseInt(num) > 0) {
    el.textContent = '$' + formatMiles(num);
  }
});

// ── EDITAR MOVIMIENTO ──
document.getElementById('modalEditarMovimiento').addEventListener('show.bs.modal', function (e) {
  const btn = e.relatedTarget;
  if (!btn) return;
  document.getElementById('em-producto-nombre').textContent = btn.dataset.nombre;

  const tipoVal = btn.dataset.tipo;
  document.getElementById('em-tipo').value = tipoVal;
  document.getElementById('em-tipo-label').textContent =
    tipoVal === 'salida' ? 'Salida' : 'Entrada';

  document.getElementById('em-cantidad').value = btn.dataset.cantidad;
  document.getElementById('em-motivo').value   = btn.dataset.motivo;
  document.getElementById('form-editar-movimiento').action =
    '/inventario/movimiento/' + btn.dataset.pk + '/editar/';
});

// ── DROPDOWN TIPO (editar movimiento) ──
document.querySelectorAll('.em-tipo-item').forEach(function(item) {
  item.addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('em-tipo-label').textContent = this.textContent.trim();
    document.getElementById('em-tipo').value = this.dataset.value;
  });
});

// ── REGISTRAR CÓDIGOS ──
(function () {
  let filaActiva   = null;
  let zxingReader  = null;
  const modal      = document.getElementById('modalRegistrarCodigos');
  const scanInput  = document.getElementById('scan-input');
  const scanBtn    = document.getElementById('scan-guardar');
  const scanNombre = document.getElementById('scan-producto-nombre');
  const camBtn     = document.getElementById('scan-camara-btn');
  const camPanel   = document.getElementById('scan-camara-panel');
  const camVideo   = document.getElementById('scan-video');
  const camEstado  = document.getElementById('scan-camara-estado');

  function resetUI() {
    filaActiva = null;
    document.querySelectorAll('.scan-row').forEach(f => f.classList.remove('scan-row--active'));
    scanNombre.textContent = '— Haz clic en una fila para seleccionar —';
    scanInput.value        = '';
    scanInput.disabled     = true;
    scanBtn.disabled       = true;
    scanBtn.style.opacity  = '0.45';
    camBtn.disabled        = true;
    detenerCamara();
  }

  let html5Scanner = null;

  async function iniciarCamara() {
    camPanel.classList.remove('d-none');
    camEstado.textContent = 'Iniciando cámara…';

    if (typeof Html5Qrcode === 'undefined') {
      camEstado.textContent = 'Error: la librería no cargó. Revisa tu conexión.';
      return;
    }

    camVideo.style.display = 'none';
    let contenedor = document.getElementById('scan-video-html5');
    if (!contenedor) {
      contenedor = document.createElement('div');
      contenedor.id = 'scan-video-html5';
      camVideo.parentNode.insertBefore(contenedor, camVideo);
    }
    contenedor.style.width      = '340px';
    contenedor.style.maxWidth   = '100%';
    contenedor.style.height     = '220px';
    contenedor.style.margin     = '0 auto';
    contenedor.style.overflow   = 'hidden';
    contenedor.style.borderRadius = '12px';

    html5Scanner = new Html5Qrcode('scan-video-html5');

    try {
      await html5Scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 250, height: 150 } },
        (codigoDetectado) => {
          scanInput.value = codigoDetectado;
          camEstado.textContent = 'Código detectado: ' + codigoDetectado;
          detenerCamara();
        },
        () => {}
      );
      camEstado.textContent = 'Apunta la cámara al código de barras…';
    } catch (err) {
      console.error('Error al iniciar cámara:', err);
      camEstado.textContent = 'No se pudo acceder a la cámara: ' + (err.message || err);
    }
  }

  function detenerCamara() {
    if (html5Scanner) {
      html5Scanner.stop().then(() => html5Scanner.clear()).catch(() => {});
      html5Scanner = null;
    }
    camPanel.classList.add('d-none');
  }

  function guardarCodigo(fila, codigo) {
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const fd   = new FormData();
    fd.append('codigo', codigo);
    fd.append('csrfmiddlewaretoken', csrf);
    fetch(fila.dataset.url, { method: 'POST', body: fd })
      .then(r => {
        if (r.ok || r.redirected) {
          fila.dataset.codigo = codigo;
          fila.querySelector('.codigo-display').textContent = codigo || '—';
          fila.querySelector('td:nth-child(4)').innerHTML = codigo
            ? '<span class="badge inv-badge-entrada"><i class="bi bi-check-circle me-1"></i>Registrado</span>'
            : '<span class="badge inv-badge-salida-tbl"><i class="bi bi-x-circle me-1"></i>Sin código</span>';
          fila.classList.add('scan-row--saved');
          setTimeout(() => { fila.classList.remove('scan-row--saved'); resetUI(); }, 1200);
        }
      })
      .catch(() => alert('Error al guardar. Intenta de nuevo.'));
  }

  document.getElementById('tabla-codigos').addEventListener('click', function (e) {
    const fila = e.target.closest('.scan-row');
    if (!fila) return;
    document.querySelectorAll('.scan-row').forEach(f => f.classList.remove('scan-row--active'));
    filaActiva = fila;
    fila.classList.add('scan-row--active');
    scanNombre.textContent = fila.dataset.nombre;
    scanInput.value        = fila.dataset.codigo;
    scanInput.disabled     = false;
    scanBtn.disabled       = false;
    scanBtn.style.opacity  = '1';
    camBtn.disabled        = false;
    scanInput.focus();
  });

  camBtn.addEventListener('click', () => {
    html5Scanner ? detenerCamara() : iniciarCamara();
  });

  scanBtn.addEventListener('click', () => {
    if (filaActiva) guardarCodigo(filaActiva, scanInput.value.trim());
  });

  scanInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && filaActiva) {
      e.preventDefault();
      guardarCodigo(filaActiva, scanInput.value.trim());
    }
  });

  modal.addEventListener('hidden.bs.modal', resetUI);
})();

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

// ── CATÁLOGO ──
(function () {
  const buscar  = document.getElementById('cat-buscar');
  let catFiltro = '';
  const grid    = document.getElementById('cat-grid');
  const list    = document.getElementById('cat-list');
  const empty   = document.getElementById('cat-empty');
  const btnGrid = document.getElementById('cat-btn-grid');
  const btnList = document.getElementById('cat-btn-list');

  function filtrar() {
    const q   = buscar.value.toLowerCase().trim();
    const cat = catFiltro;
    let vis   = 0;
    document.querySelectorAll('.cat-item').forEach(el => {
      const ok = (!q || el.dataset.nombre.includes(q))
              && (!cat || el.dataset.cat === cat);
      el.style.display = ok ? '' : 'none';
      if (ok) vis++;
    });
    empty.classList.toggle('d-none', vis > 0);
  }

  buscar.addEventListener('input', filtrar);

  // FIX: antes el selector era '[data-cat]', que también capturaba las
  // tarjetas de producto (.cat-item) porque ELLAS TAMBIÉN tienen data-cat.
  // Eso hacía que al hacer clic en una tarjeta se sobreescribiera el label
  // del dropdown de categorías con el texto completo de la tarjeta.
  // Ahora apuntamos solo a los items del dropdown (.cat-cat-item).
  document.querySelectorAll('.cat-cat-item').forEach(function(a) {
    a.addEventListener('click', function(e) {
      e.preventDefault();
      document.getElementById('cat-cat-label').textContent = this.textContent.trim();
      catFiltro = this.dataset.cat;
      filtrar();
    });
  });

  btnGrid.addEventListener('click', () => {
    grid.classList.remove('d-none');
    list.classList.add('d-none');
    btnGrid.classList.replace('inv-btn-outline', 'inv-btn-primary');
    btnList.classList.replace('inv-btn-primary', 'inv-btn-outline');
  });

  btnList.addEventListener('click', () => {
    list.classList.remove('d-none');
    grid.classList.add('d-none');
    btnList.classList.replace('inv-btn-outline', 'inv-btn-primary');
    btnGrid.classList.replace('inv-btn-primary', 'inv-btn-outline');
  });
})();

// ── ANALÍTICA / ROTACIÓN ──
const ROTACION_URL = document.getElementById('rotacion-config')?.getAttribute('data-url') || '';

(function () {
  const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                 'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

  function fmtCOP(v) {
    if (v >= 1000000) return '$' + (v/1000000).toFixed(1).replace('.0','') + 'M';
    if (v >= 1000)    return '$' + Math.round(v/1000) + 'k';
    return '$' + v.toLocaleString('es-CO');
  }

  function calcRotacion(uds) {
    if (uds >= 100) return '<span class="text-success fw-bold">Alta</span> — reposición cada 3 días';
    if (uds >= 30)  return '<span class="text-warning fw-bold">Media</span> — reposición cada semana';
    if (uds > 0)    return '<span class="text-danger fw-bold">Baja</span> — poca salida';
    return '<span class="text-danger fw-bold">Sin movimiento</span>';
  }

  function itemFila(nombre, cantidad, sinMov) {
    const color = sinMov ? '#e74c3c' : (cantidad >= 50 ? '#27ae60' : '#f39c12');
    return `<div class="d-flex justify-content-between py-1 border-bottom border-secondary small">
      <span>${nombre}</span>
      <span class="fw-bold" style="color:${color};">${cantidad} uds</span>
    </div>`;
  }

  if (ROTACION_URL) {
    fetch(ROTACION_URL)
      .then(r => r.json())
      .then(data => {
        document.getElementById('seccion-analitica').style.display = 'block';
        if (data.estrella_nombre) {
          const ahora = new Date();
          document.getElementById('estrella-mes-label').textContent = MESES[ahora.getMonth()] + ' ' + ahora.getFullYear();
          document.getElementById('estrella-nombre').textContent       = data.estrella_nombre;
          document.getElementById('estrella-categoria').textContent    = 'Categoría: ' + (data.estrella_categoria || '—');
          document.getElementById('estrella-vendido').textContent      = data.estrella_vendido;
          document.getElementById('estrella-ingresos').textContent     = data.estrella_ingresos > 0 ? fmtCOP(data.estrella_ingresos) : '—';
          document.getElementById('estrella-presentacion').textContent = data.estrella_presentacion || '—';
          document.getElementById('estrella-rotacion').innerHTML       = calcRotacion(data.estrella_vendido || 0);
          const critico = data.estrella_stock_critico;
          document.getElementById('estrella-stock').innerHTML =
          `<span class="${critico ? 'text-danger' : 'text-success'}">${data.estrella_stock}</span>` +
          `<span class="estrella-valor-label">uds${critico ? ' ⚠' : ''}</span>`;
          document.getElementById('bloque-estrella').style.display = 'block';
        }
        const rotacion      = data.rotacion || [];
        const sinMovimiento = data.sin_movimiento || [];
        const todos         = [...rotacion, ...sinMovimiento];
        if (todos.length) {
          document.getElementById('rotacion-loading').style.display = 'none';
          const canvas = document.getElementById('chartRotacion');
          canvas.style.display = 'block';
          canvas.parentElement.style.height = Math.max(300, todos.length * 40) + 'px';
          new Chart(canvas, {
            type: 'bar',
            data: {
              labels: todos.map(p => p.nombre),
              datasets: [{ label: 'Unidades vendidas', data: todos.map(p => p.cantidad),
                backgroundColor: todos.map((_, i) => i < rotacion.length ? '#4DA8DA' : '#e74c3c'),
                borderRadius: 5, borderSkipped: false }]
            },
            options: {
              indexAxis: 'y', responsive: true, maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                x: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.07)' }, ticks: { color: '#8899aa' } },
                y: { grid: { display: false }, ticks: { color: '#c8d6e5', autoSkip: false } }
              }
            }
          });
          const alta = rotacion.filter(p => p.cantidad >= 50);
          const baja = rotacion.filter(p => p.cantidad > 0 && p.cantidad < 50);
          document.getElementById('lista-alta-rotacion').innerHTML = alta.length
            ? alta.map(p => itemFila(p.nombre, p.cantidad, false)).join('')
            : '<p class="text-muted small text-center py-2">Sin productos de alta rotación.</p>';
          document.getElementById('lista-baja-rotacion').innerHTML = [...baja, ...sinMovimiento].length
            ? [...baja.map(p => itemFila(p.nombre, p.cantidad, false)), ...sinMovimiento.map(p => itemFila(p.nombre, 0, true))].join('')
            : '<p class="text-muted small text-center py-2">Todos tienen movimiento.</p>';
          document.getElementById('tablas-rotacion').style.display = 'flex';
        } else {
          document.getElementById('rotacion-loading').innerHTML = '<p class="text-muted small text-center py-3">No hay datos de ventas en los últimos 30 días.</p>';
        }
      })
      .catch(() => {
        document.getElementById('seccion-analitica').style.display = 'block';
        document.getElementById('rotacion-loading').innerHTML = '<p class="text-muted small">Error al cargar datos.</p>';
      });
  }
})();

// ── DROPDOWN CONTEO PRODUCTO ──
document.querySelectorAll('.conteo-prod-item').forEach(function(item) {
  item.addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('conteo-prod-label').textContent = this.textContent.trim();
    document.getElementById('conteo-prod-hidden').value = this.dataset.value;
  });
});

window.addEventListener('load', function () {
  document.querySelectorAll('.container-fluid [title]').forEach(function (el) {
    new bootstrap.Tooltip(el, {
      placement: 'top',
      trigger: 'hover'
    });
  });
});