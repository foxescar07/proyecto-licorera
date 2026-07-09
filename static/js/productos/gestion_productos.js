/**
 * GESTION_PRODUCTOS.JS — Gestión de Productos
 * Estadísticas, filtrado, dropdowns, acordeón, tooltips
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
    const cantPres = row.querySelectorAll('td:nth-child(3) .tag-info').length;
    if (cantPres === 0) {
      sinPres++;
    } else {
      totalPres += cantPres;
      if (cantPres > maxPres) maxPres = cantPres;
      if (cantPres < minPres) minPres = cantPres;
    }
  });
  if (minPres === Infinity) minPres = 0;

  document.querySelectorAll('.categoria-item').forEach(item => {
    const nombre = item.querySelector('.acc-hdr').textContent.split('productos')[0].trim();
    const cant   = item.querySelectorAll('.producto-row').length;
    if (cant > 0) conteoCats[nombre] = cant;
  });

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

function toggleAcc(btn, bodyId) {
  const body   = document.getElementById(bodyId);
  const isOpen = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', String(!isOpen));
  body.style.display = isOpen ? 'none' : 'block';
}

function filtrarProductos(q) {
  const term = q.toLowerCase().trim();
  let alguno = false;
  document.querySelectorAll('.categoria-item').forEach(item => {
    let visibles = 0;
    item.querySelectorAll('.producto-row').forEach(row => {
      const match = !term || row.dataset.nombre.includes(term) || row.dataset.codigo.includes(term);
      row.style.display = match ? '' : 'none';
      if (match) visibles++;
    });
    item.style.display = visibles ? '' : 'none';
    if (term && visibles) {
      const btn    = item.querySelector('.acc-hdr');
      const bodyId = btn.getAttribute('aria-controls');
      btn.setAttribute('aria-expanded', 'true');
      document.getElementById(bodyId).style.display = 'block';
    }
    if (visibles) alguno = true;
  });
  document.getElementById('noResultados').classList.toggle('d-none', alguno || !term);
}

function confirmarToggle(url, nombre, accion) {
  if (confirm('¿Deseas ' + accion + ' "' + nombre + '"?')) {
    const form = document.getElementById('form-eliminar');
    form.action = url;
    form.submit();
  }
}

function confirmarEliminar(url, nombre) {
  if (confirm('¿Eliminar definitivamente «' + nombre + '»?')) {
    const form = document.getElementById('form-eliminar');
    form.action = url;
    form.submit();
  }
}
