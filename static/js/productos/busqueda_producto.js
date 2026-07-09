/**
 * BUSQUEDA_PRODUCTO.JS — Búsqueda y Autocompletado de Productos
 * Dropdown con sugerencias, búsqueda detallada, visualización de stock
 */

let URL_BUSCAR = '';
let input, ulSugest, out, btn;
let bpTimer = null;

document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('bp-container');
  input      = document.getElementById('bp-input');
  ulSugest   = document.getElementById('bp-sugerencias');
  out        = document.getElementById('bp-resultado');
  btn        = document.getElementById('bp-btn');

  if (!input || !ulSugest || !container) return;

  URL_BUSCAR = container.getAttribute('data-buscar-url') || '';

  // Debounce input de búsqueda
  input.addEventListener('input', function () {
    clearTimeout(bpTimer);
    const valor = this.value.trim();

    if (valor.length < 2) {
      ocultarSugerencias();
      return;
    }
    bpTimer = setTimeout(() => bpAutocompletar(valor), 300);
  });

  // Permitir Enter para ir directo al detalle
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      ocultarSugerencias();
      bpBuscarDetalle(this.value.trim());
    }
  });

  // Click en sugerencia
  ulSugest.addEventListener('click', function (e) {
    const item = e.target.closest('.dropdown-item');
    if (!item || item.classList.contains('disabled')) return;
    e.preventDefault();

    const nombre = item.querySelector('span').textContent.trim();
    input.value  = nombre;
    ocultarSugerencias();
    bpBuscarDetalle(nombre);
  });

  // Cerrar dropdown al hacer click fuera
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.input-group')) {
      ocultarSugerencias();
    }
  });
});

// Pedir sugerencias y pintarlas como dropdown-item
async function bpAutocompletar(q) {
  try {
    const resp = await fetch(`${URL_BUSCAR}?q=${encodeURIComponent(q)}&modo=sugerencias`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await resp.json();
    pintarSugerencias(data.resultados || []);
  } catch {
    ocultarSugerencias();
  }
}

function pintarSugerencias(resultados) {
  if (!resultados.length) {
    ulSugest.innerHTML = `<li><span class="dropdown-item disabled text-muted">Sin coincidencias</span></li>`;
    ulSugest.classList.add('show');
    return;
  }

  ulSugest.innerHTML = resultados.map(r => `
    <li>
      <a class="dropdown-item d-flex justify-content-between align-items-center" href="#" data-pk="${r.pk}">
        <span>${r.nombre}</span>
        <small class="text-muted ms-2">${r.categoria} · ${r.codigo}</small>
      </a>
    </li>
  `).join('');

  ulSugest.classList.add('show');
}

function ocultarSugerencias() {
  ulSugest.classList.remove('show');
  ulSugest.innerHTML = '';
}

// Detalle completo del producto
window.bpBuscarDetalle = async function (q) {
  if (!q) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>';
  out.innerHTML = '';

  try {
    const resp = await fetch(`${URL_BUSCAR}?q=${encodeURIComponent(q)}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await resp.json();

    if (!data.encontrado) {
      out.innerHTML = `<div class="alert ${resp.status === 500 ? 'alert-danger' : 'alert-warning'} py-2 small">
        <i class="bi bi-search me-1"></i>${data.mensaje}</div>`;
      return;
    }

    const p          = data.producto;
    const esAgotado  = p.stock_total === 0;
    const esCritico  = p.stock_total > 0 && p.stock_total <= 10;
    const badgeClass = esAgotado ? 'bg-danger' : esCritico ? 'bg-warning text-dark' : 'bg-success';
    const badgeText  = esAgotado ? 'Sin stock'  : esCritico ? 'Stock crítico'        : 'Disponible';

    out.innerHTML = `
      <div class="card prod-card p-3">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <div>
            <div class="fw-bold">${p.nombre}</div>
            <div class="text-muted small">${p.categoria} · Cód: ${p.codigo}</div>
          </div>
          <div class="d-flex align-items-center gap-2">
            <span class="badge ${badgeClass}">${badgeText}</span>
            <button onclick="document.getElementById('bp-resultado').innerHTML='';document.getElementById('bp-input').value='';"
                    class="btn-close btn-close-white bp-close-btn"></button>
          </div>
        </div>
        <div class="d-flex gap-4 small mt-2">
          <div>
            <span class="text-muted">Stock total: </span>
            <strong class="${esAgotado ? 'text-danger' : esCritico ? 'text-warning' : 'text-success'}">${p.stock_total}</strong>
          </div>
        </div>
        ${p.presentaciones.length ? `
          <hr class="border-secondary my-2">
          <div class="small text-muted mb-1 fw-semibold">Presentaciones</div>
          ${p.presentaciones.map(pr => `
            <div class="d-flex justify-content-between py-1 border-bottom border-secondary small">
              <span>${pr.nombre} <span class="text-muted">(${pr.unidades} uds)</span></span>
              <span class="text-info">Stock: ${pr.stock_actual} — $${parseInt(pr.precio||0).toLocaleString('es-CO')}</span>
            </div>`).join('')}
        ` : ''}
      </div>`;

  } catch {
    out.innerHTML = `<div class="alert alert-danger py-2 small">
      <i class="bi bi-exclamation-octagon me-1"></i>Error de conexión.</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-search"></i>';
  }
};
