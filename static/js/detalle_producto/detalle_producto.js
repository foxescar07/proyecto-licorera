/**
 * GESTION_PRODUCTOS.JS — Gestión de Productos
 * Estadísticas, filtrado, dropdowns, tooltips
 */

function formatMiles(n) {
  var num = parseInt(String(n).replace(/\D/g, ''), 10);
  if (isNaN(num)) return n;
  return num.toLocaleString('es-CO');
}

document.addEventListener('DOMContentLoaded', function () {
  // Cálculo de estadísticas iniciales
  const rows  = document.querySelectorAll('.producto-row');
  const total = rows.length;
  let sinPres = 0;
  let totalPres = 0;
  let maxPres = 0;
  let minPres = total > 0 ? Infinity : 0;
  const conteoCats = {};

  rows.forEach(row => {
    const cantPres = row.querySelectorAll('.gp-badge-pres').length;
    if (cantPres === 0) {
      sinPres++;
    } else {
      totalPres += cantPres;
      if (cantPres > maxPres) maxPres = cantPres;
      if (cantPres < minPres) minPres = cantPres;
    }

    const cat = row.dataset.categoria || 'Sin categoría';
    conteoCats[cat] = (conteoCats[cat] || 0) + 1;
  });
  if (minPres === Infinity) minPres = 0;

  const catWrap = document.getElementById('grafico-categorias');
  Object.entries(conteoCats).forEach(([cat, n]) => {
    const pct = total > 0 ? Math.round((n / total) * 100) : 0;
    catWrap.innerHTML += `
      <div>
        <div class="cat-stat-row">
          <span class="cat-stat-name">${cat}</span>
          <span>${n} (${pct}%)</span>
        </div>
        <div class="bar-track cat-stat-track">
          <div class="bar-fill cat-stat-fill" style="width:${pct}%;"></div>
        </div>
      </div>`;
  });

  // Promedio de presentaciones por producto
  const conPres = total - sinPres;
  const promedio = conPres > 0 ? (totalPres / conPres) : 0;
  document.getElementById('txt-prom-pres').textContent = promedio.toFixed(1);
  document.getElementById('stat-pres-min').textContent = minPres;
  document.getElementById('stat-pres-max').textContent = maxPres;
  const pctBarra = maxPres > 0 ? Math.round((promedio / maxPres) * 100) : 0;
  document.getElementById('bar-prom-pres').style.width = pctBarra + '%';

  document.getElementById('stat-sin-pres').textContent = sinPres;
  if (total > 0)
    document.getElementById('bar-sin-pres').style.width = Math.round((sinPres / total) * 100) + '%';

  // Formato de precios con puntos de miles
  document.querySelectorAll('.precio-fmt').forEach(function (el) {
    var texto = el.textContent.trim();
    var num = texto.replace('$', '').replace(/\./g, '').trim();
    if (num && !isNaN(num) && parseInt(num) > 0) {
      el.textContent = '$' + formatMiles(num);
    }
  });

  // Dropdowns de categoría en modales editar
  document.querySelectorAll('.edit-prod-cat-item').forEach(function(item) {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      const target = this.dataset.target;

      document.getElementById('editProd-cat-label-' + target).textContent = this.textContent.trim();
      document.getElementById('editProd-cat-hidden-' + target).value = this.dataset.value;

      this.closest('ul').querySelectorAll('.edit-prod-cat-item').forEach(el => el.classList.remove('active'));
      this.classList.add('active');
    });
  });

  // Tooltips de Bootstrap
  const tooltipTriggerList = document.querySelectorAll('.prod-table [title]');
  tooltipTriggerList.forEach(function (el) {
    new bootstrap.Tooltip(el, {
      placement: 'top',
      trigger: 'hover'
    });
  });

  // Cierre de dropdowns en acciones
  document.querySelectorAll('.prod-dropdown-menu .dropdown-item').forEach(function (item) {
    item.addEventListener('click', function () {
      const menu = item.closest('.dropdown-menu');
      const toggleBtn = menu ? menu.previousElementSibling : null;
      if (toggleBtn) {
        const dd = bootstrap.Dropdown.getOrCreateInstance(toggleBtn);
        dd.hide();
      }
    });
  });

  document.addEventListener('click', function (e) {
    document.querySelectorAll('.dropdown-menu.show').forEach(function (menu) {
      const dropdownWrap = menu.closest('.dropdown');
      if (dropdownWrap && !dropdownWrap.contains(e.target)) {
        const toggleBtn = menu.previousElementSibling;
        if (toggleBtn) {
          bootstrap.Dropdown.getOrCreateInstance(toggleBtn).hide();
        }
      }
    });
  }, true);
});

function filtrarProductos(q) {
  const term = q.toLowerCase().trim();
  let visibles = 0;

  document.querySelectorAll('.producto-row').forEach(row => {
    const match = !term || row.dataset.nombre.includes(term) || row.dataset.codigo.includes(term);
    row.style.display = match ? '' : 'none';
    if (match) visibles++;
  });

  document.getElementById('noResultados').classList.toggle('d-none', visibles > 0 || !term);
}

function mostrarModalConfirmacion(mensaje, onAceptar, opciones) {
  opciones = opciones || {};
  const modalEl   = document.getElementById('modalConfirmarAccion');
  const mensajeEl = document.getElementById('confirmar-mensaje');
  const tituloEl  = document.getElementById('confirmar-titulo');
  const btnAceptar = document.getElementById('confirmar-btn-aceptar');

  mensajeEl.textContent = mensaje;
  tituloEl.innerHTML = '<i class="bi bi-question-circle me-2 text-info"></i>' + (opciones.titulo || 'Confirmar acción');

  btnAceptar.className = 'btn ' + (opciones.claseBoton || 'prod-btn-primary');
  btnAceptar.textContent = opciones.textoBoton || 'Aceptar';

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

  const nuevoBtn = btnAceptar.cloneNode(true);
  btnAceptar.parentNode.replaceChild(nuevoBtn, btnAceptar);
  nuevoBtn.addEventListener('click', function () {
    modal.hide();
    onAceptar();
  });

  modal.show();
}

function confirmarToggle(url, nombre, accion) {
  mostrarModalConfirmacion(
    '¿Deseas ' + accion + ' "' + nombre + '"?',
    function () {
      const form = document.getElementById('form-eliminar');
      form.action = url;
      form.submit();
    }
  );
}

function confirmarEliminar(url, nombre) {
  mostrarModalConfirmacion(
    '¿Eliminar definitivamente «' + nombre + '»?',
    function () {
      const form = document.getElementById('form-eliminar');
      form.action = url;
      form.submit();
    },
    { titulo: 'Eliminar', claseBoton: 'btn-danger', textoBoton: 'Eliminar' }
  );
}
// ── Toggle: colapsar/expandir la lista de productos ──
window.toggleListaProductos = function() {
  const lista = document.getElementById('listaProductos');
  const icon = document.getElementById('gpToggleIcon');
  if (!lista || !icon) return;
  const colapsada = lista.classList.toggle('gp-lista-colapsada');
  icon.classList.toggle('gp-toggle-icon-rotado', colapsada);
};
window.addEventListener('load', function () {
  document.querySelectorAll('[title]').forEach(function (el) {
    new bootstrap.Tooltip(el, {
      placement: 'top',
      trigger: 'hover'
    });
  });
});
// ── ÍCONO DE CATEGORÍA POR PRODUCTO ──
(function () {
  const REGLAS = [
    { match: /cerveza/,          clase: 'gp-cat-cerveza', icono: 'bi-cup-straw' },
    { match: /gaseosa|soda/,     clase: 'gp-cat-gaseosa', icono: 'bi-cup-fill' },
    { match: /whisky|whiskey/,   clase: 'gp-cat-whisky',  icono: 'bi-cup-hot-fill' },
    { match: /vino/,             clase: 'gp-cat-vino',    icono: 'bi-flower1' },
    { match: /licor|ron|aguardiente/, clase: 'gp-cat-licor', icono: 'bi-droplet-fill' },
  ];
  const DEFAULT = { clase: '', icono: 'bi-box-seam' };

  document.querySelectorAll('.producto-row').forEach(function (row) {
    const cat = row.dataset.categoria || '';
    const box = row.querySelector('[data-cat-icon]');
    if (!box) return;

    const regla = REGLAS.find(function (r) { return r.match.test(cat); }) || DEFAULT;
    if (regla.clase) box.classList.add(regla.clase);
    box.innerHTML = '<i class="bi ' + regla.icono + '"></i>';
  });
})();
$(document).ready(function () {
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
      { orderable: false, targets: [0] }
    ],
    language: {
      emptyTable: "No hay productos registrados."
    },
    dom: 'rt'
  });
});

// ── REGISTRAR CÓDIGOS ──
(function () {
  let filaActiva   = null;
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