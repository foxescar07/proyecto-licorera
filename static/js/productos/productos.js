/**
 * PRODUCTOS.JS — Gestión de Productos
 * DataTable, filtrado por categoría, creación, presentaciones
 */

let ultimaCatPk = null;
let dtInstance = null;
let GESTION_URL, CREAR_URL, PRES_URL, CSRF_TOKEN, NEXT_PATH, todoProductos;

document.addEventListener('DOMContentLoaded', function () {
  // Leer variables desde data-attributes
  const configEl = document.getElementById('productos-config');
  if (!configEl) return;

  GESTION_URL = configEl.getAttribute('data-gestion-url') || '';
  CREAR_URL = configEl.getAttribute('data-crear-url') || '';
  PRES_URL = configEl.getAttribute('data-pres-url') || '';
  CSRF_TOKEN = configEl.getAttribute('data-csrf-token') || '';
  NEXT_PATH = configEl.getAttribute('data-next-path') || '';

  try {
    todoProductos = JSON.parse(configEl.getAttribute('data-productos') || '[]');
  } catch (e) {
    console.error('Error parsing productos data:', e);
    todoProductos = [];
  }

  // Inicializar DataTable
  dtInstance = $('#tablaProductosCat').DataTable({
    paging: false,
    searching: false,
    info: false,
    ordering: true,
    responsive: true,
    language: {
      zeroRecords: "Sin resultados.",
      emptyTable: "No hay productos en esta categoría."
    }
  });

  inicializarGraficos();
  inicializarDropdownCategorias();
});

function filasHtmlDe(filtrados) {
  return filtrados.map((p, i) => {
    const pres = p.presentaciones.length
      ? p.presentaciones.map(pr =>
          `<span class="badge prod-pres-badge me-1">
            ${pr.nombre} · ${pr.unidades} uds · $${parseInt(pr.precio || 0).toLocaleString('es-CO')}
          </span>`).join('')
      : `<span class="prod-label prod-label-sm">Sin definir</span>`;

    return `<tr>
      <td class="px-4 prod-label text-center">${i + 1}</td>
      <td class="fw-semibold prod-cell-nombre">${p.nombre}</td>
      <td class="prod-cell-codigo text-center">${p.codigo || '—'}</td>
      <td>${pres}</td>
    </tr>`;
  }).join('');
}

function filtrarCategoria(btn) {
  const pk     = btn.dataset.catPk;
  const nombre = btn.dataset.catNombre;
  const empty  = document.getElementById('cat-empty-state');
  const tabla  = document.getElementById('cat-tabla-wrap');

  if (ultimaCatPk === pk) {
    ultimaCatPk = null;
    btn.classList.remove('active');
    document.getElementById('cat-titulo').textContent = 'Productos por categoría';
    empty.classList.add('cat-panel-visible');
    empty.classList.remove('cat-panel-oculto');
    tabla.classList.add('cat-panel-oculto');
    tabla.classList.remove('cat-panel-visible');
    return;
  }

  ultimaCatPk = pk;
  document.querySelectorAll('.prod-cat-chip').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const filtrados = pk === 'todos'
    ? todoProductos
    : todoProductos.filter(p => String(p.categoria_pk) === String(pk) || String(p.categoria_padre_pk) === String(pk));

  document.getElementById('cat-titulo').textContent =
    nombre + ' — ' + filtrados.length + ' producto' + (filtrados.length !== 1 ? 's' : '');

  empty.classList.add('cat-panel-oculto');
  empty.classList.remove('cat-panel-visible');
  tabla.classList.add('cat-panel-visible');
  tabla.classList.remove('cat-panel-oculto');

  dtInstance.clear();
  if (filtrados.length) {
    dtInstance.rows.add($(filasHtmlDe(filtrados)));
  }
  dtInstance.draw();
}

// Modal de productos por categoría
document.addEventListener('DOMContentLoaded', function() {
  const modalEl = document.getElementById('modalProductosCategoria');
  if (modalEl) {
    modalEl.addEventListener('show.bs.modal', function(e) {
      const btn = e.relatedTarget;
      if (!btn) return;
      const pk     = btn.dataset.catPk;
      const nombre = btn.dataset.catNombre;
      document.getElementById('titulo-categoria').textContent = nombre;

      const filtrados = todoProductos.filter(p => String(p.categoria_pk) === String(pk));
      const tbody     = document.getElementById('cuerpo-categoria');

      if (!filtrados.length) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-muted">
          <i class="bi bi-box-seam d-block mb-2 fs-3"></i>No hay productos en esta categoría.</td></tr>`;
        return;
      }

      tbody.innerHTML = filtrados.map((p, i) => {
        const pres = p.presentaciones.length
          ? p.presentaciones.map(pr =>
              `<span class="badge prod-badge-pres me-1">
                ${pr.nombre} (${pr.unidades} uds) — Stock: ${pr.stock_actual} — $${parseInt(pr.precio||0).toLocaleString('es-CO')}
              </span>`).join('')
          : `<span class="text-muted small">Sin definir</span>`;

        return `<tr ${p.stock_critico ? 'class="table-danger"' : ''}>
          <td class="text-muted small">${i+1}</td>
          <td class="fw-semibold small">${p.nombre}</td>
          <td><span class="fw-bold ${p.stock_critico ? 'text-danger' : 'text-info'}">${p.stock_total} uds</span></td>
          <td>${pres}</td>
          <td>
            <button class="btn btn-sm prod-btn-info" title="Ver detalle"
                    onclick="abrirDetalle(${p.pk},'${p.nombre}','${p.codigo}','${p.categoria_nombre}',${p.stock_total},'${p.descripcion}')">
              <i class="bi bi-eye"></i>
            </button>
          </td>
        </tr>`;
      }).join('');
    });
  }
});

function abrirDetalle(pk, nombre, codigo, categoria, stock_total, descripcion) {
  document.getElementById('det-nombre').textContent      = nombre;
  document.getElementById('det-codigo').textContent      = codigo;
  document.getElementById('det-categoria').textContent   = categoria;
  document.getElementById('det-cantidad').textContent    = stock_total + ' uds';
  document.getElementById('det-descripcion').textContent = descripcion || 'Sin descripción';

  const p  = todoProductos.find(x => x.pk == pk);
  const el = document.getElementById('det-presentaciones');
  el.innerHTML = p && p.presentaciones.length
    ? p.presentaciones.map(pr => `
        <div class="d-flex justify-content-between py-1 border-bottom border-secondary small">
          <span>${pr.nombre} <span class="text-muted">(${pr.unidades} uds) — Stock: ${pr.stock_actual}</span></span>
          <span class="text-info fw-semibold">$${parseInt(pr.precio||0).toLocaleString('es-CO')}</span>
        </div>`).join('')
    : '<span class="text-muted small">Sin presentaciones.</span>';

  bootstrap.Modal.getOrCreateInstance(document.getElementById('modalDetalleProducto')).show();
}

// Crear producto
function mostrarFeedback(tipo, msg) {
  const fb = document.getElementById('crear-feedback');
  fb.innerHTML = `<div class="alert ${tipo === 'ok' ? 'alert-success' : 'alert-danger'} py-2 small">${msg}</div>`;
  fb.style.display = 'block';
}

async function enviarCrearProducto() {
  const nombre    = document.getElementById('crear-nombre').value.trim();
  const categoria = document.getElementById('crear-categoria').value;
  if (!nombre)    { mostrarFeedback('error', 'El nombre es obligatorio.'); return; }
  if (!categoria) { mostrarFeedback('error', 'Selecciona una categoría.'); return; }

  const btn = document.getElementById('btn-crear-solo');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Guardando…';

  try {
    const resp = await fetch(CREAR_URL, {
      method: 'POST',
      body: new FormData(document.getElementById('form-nuevo-producto-modal')),
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await resp.json();
    if (resp.ok && data.ok) {
      mostrarFeedback('ok', `✓ Producto <strong>${data.nombre}</strong> creado.`);
      setTimeout(() => {
        bootstrap.Modal.getInstance(document.getElementById('modalCrearProducto')).hide();
        location.reload();
      }, 1200);
    } else {
      mostrarFeedback('error', data.errores ? Object.values(data.errores).flat().join(' ') : (data.error || 'Error al crear.'));
    }
  } catch { mostrarFeedback('error', 'Error de conexión.'); }
  finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Guardar Producto';
  }
}

async function crearProductoYPresentaciones() {
  const nombre    = document.getElementById('crear-nombre').value.trim();
  const categoria = document.getElementById('crear-categoria').value;
  if (!nombre)    { mostrarFeedback('error', 'El nombre es obligatorio.'); return; }
  if (!categoria) { mostrarFeedback('error', 'Selecciona una categoría.'); return; }

  const btn = document.getElementById('btn-guardar-presentaciones');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Guardando…';

  try {
    const resp = await fetch(CREAR_URL, {
      method: 'POST',
      body: new FormData(document.getElementById('form-nuevo-producto-modal')),
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await resp.json();
    if (resp.ok && data.ok) {
      bootstrap.Modal.getInstance(document.getElementById('modalCrearProducto')).hide();
      setTimeout(() => abrirModalPresentaciones(data.pk, data.nombre), 400);
    } else {
      mostrarFeedback('error', data.errores ? Object.values(data.errores).flat().join(' ') : (data.error || 'Error.'));
    }
  } catch { mostrarFeedback('error', 'Error de conexión.'); }
  finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-layers me-1"></i> Definir Presentaciones';
  }
}

// Presentaciones
function abrirModalPresentaciones(pk, nombre) {
  document.getElementById('pres-nombre-producto').textContent = nombre;
  document.getElementById('pres-nombre-unidad').value         = 'Unidad';
  document.getElementById('pres-unidades-unidad').value       = '1';
  document.getElementById('pres-precio-unidad').value         = '';
  document.getElementById('form-presentaciones-modal').action =
    PRES_URL.replace('/0/', '/' + pk + '/') + '?next=' + NEXT_PATH;
  document.getElementById('contenedor-presentaciones-modal').innerHTML = '';
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modalPresentacionesProducto')).show();
}

function cerrarModalPresentaciones() {
  bootstrap.Modal.getInstance(document.getElementById('modalPresentacionesProducto')).hide();
  location.reload();
}

function agregarPresentacionModal() {
  const cont = document.getElementById('contenedor-presentaciones-modal');
  const div  = document.createElement('div');
  div.className = 'row g-2 align-items-end mb-2 p-2 rounded border prod-pres-row';
  div.innerHTML = `
    <div class="col-md-3">
      <label class="form-label prod-label">Presentación</label>
      <input type="text" name="nombre[]" class="form-control prod-input" placeholder="Ej: Six-pack" required>
    </div>
    <div class="col-md-2">
      <label class="form-label prod-label">Unidades</label>
      <input type="number" name="unidades_base[]" class="form-control prod-input" min="1" required>
    </div>
    <div class="col-md-3">
      <label class="form-label prod-label">Precio (COP)</label>
      <input type="number" name="precio[]" class="form-control prod-input" min="0" required>
    </div>
    <div class="col-md-1 text-center">
      <button type="button" class="btn btn-sm btn-danger" onclick="this.closest('.prod-pres-row').remove()">
        <i class="bi bi-trash"></i>
      </button>
    </div>`;
  cont.appendChild(div);
}

// Gráficos (donut + últimos)
function inicializarGraficos() {
  const COLS = ['#4DA8DA','#CF9C48','#f312bb','#9b59b6','#e74c3c','#1abc9c','#e67e22'];

  // Donut
  const cats = {};
  todoProductos.forEach(p => { cats[p.categoria_nombre] = (cats[p.categoria_nombre]||0)+1; });
  const total = todoProductos.length || 1;
  const entradas = Object.entries(cats).sort((a,b)=>b[1]-a[1]);
  const R=53, C=65, W=20, CIRC=2*Math.PI*R;
  let off=0;
  const svg = document.getElementById('donut-svg');
  if (svg) {
    entradas.forEach(([n,v],i)=>{
      const dash=v/total*CIRC;
      const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
      c.setAttribute('cx',C);c.setAttribute('cy',C);c.setAttribute('r',R);
      c.classList.add('donut-segment', 'donut-color-' + (i % 7));
      c.setAttribute('stroke-dasharray',`${dash} ${CIRC-dash}`);
      c.setAttribute('stroke-dashoffset',-off*CIRC);
      c.setAttribute('transform',`rotate(-90 ${C} ${C})`);
      svg.appendChild(c);
      off+=v/total;
    });
  }

  // Leyenda
  const ley=document.getElementById('donut-leyenda');
  if (ley) {
    entradas.slice(0,5).forEach(([n,v],i)=>{
      ley.innerHTML += `<div class="donut-leyenda-row">
        <span class="donut-leyenda-dot donut-color-${i % 7}"></span>
        <span class="donut-leyenda-label">${n}</span>
        <span class="donut-leyenda-pct">${Math.round(v/total*100)}%</span>
      </div>`;
    });
  }

  // Últimos productos
  const ul=document.getElementById('lista-ultimos2');
  if (ul) {
    [...todoProductos].slice(-3).reverse().forEach(p=>{
      ul.innerHTML += `<li class="ultimos-item">
        <div>
          <div class="ultimos-nombre">${p.nombre}</div>
          <div class="ultimos-categoria">${p.categoria_nombre}</div>
        </div>
        <span class="ultimos-badge">${p.presentaciones.length} pres.</span>
      </li>`;
    });
  }
}

// Dropdown de categorías en modal crear
function inicializarDropdownCategorias() {
  document.querySelectorAll('.crear-cat-item').forEach(function(item) {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      document.getElementById('crear-categoria-label').textContent = this.textContent.trim();
      document.getElementById('crear-categoria').value = this.dataset.value;
    });
  });
}
window.addEventListener('load', function () {
  document.querySelectorAll('[title]').forEach(function (el) {
    new bootstrap.Tooltip(el, {
      placement: 'top',
      trigger: 'hover'
    });
  });
});