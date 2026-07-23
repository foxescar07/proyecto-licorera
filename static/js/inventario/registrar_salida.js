/**
 * REGISTRAR_SALIDA.JS — Registro de Salidas de Inventario
 * Gráfico de motivos, dropdown sincronizados, validación de stock
 */

// Gráfico de motivos de salida
function inicializarGraficoMotivos() {
  const canvas = document.getElementById('chartMotivos');
  if (!canvas) return;

  const configElement = document.getElementById('salida-config');
  let chartData = [0, 0, 0, 0];

  if (configElement) {
    const data = configElement.getAttribute('data-chart-motivos');
    if (data) {
      try {
        chartData = JSON.parse(data);
      } catch (e) {
        console.error('Error al parsear datos del gráfico:', e);
      }
    }
  }

  new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ['Venta','Merma','Daño','Vencido'],
      datasets: [{
        data: chartData,
        backgroundColor: ['#4DA8DA','#1c6ef3','#CF9C48','#9b59b6'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      cutout: '74%'
    }
  });
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  inicializarGraficoMotivos();
  inicializarDropdowns();
  inicializarValidacion();
});

/**
 * Inicializar todos los dropdowns sincronizados
 */
function inicializarDropdowns() {
  const sel             = document.getElementById('select-presentacion');
  const selectLoteForm  = document.getElementById('select-lote-form');
  const selectMotivo    = document.getElementById('select-motivo');
  const badgeWrap       = document.getElementById('stock-badge-wrap');
  const badgeVal        = document.getElementById('stock-badge-val');
  const inputQty        = document.getElementById('input-cantidad');
  const alertaExceso    = document.getElementById('alerta-exceso');

  if (!sel) return;

  // Dropdown Presentación: sincroniza texto del botón + select oculto + stock
  document.querySelectorAll('.presentacion-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      sel.value = item.dataset.value;
      document.getElementById('presentacion-label').textContent = item.textContent.trim();
      document.getElementById('presentacion-btn').classList.remove('sal-campo-error');
      sel.dispatchEvent(new Event('change'));
    });
  });

  // Dropdown Lote: sincroniza texto del botón + select oculto
  document.querySelectorAll('.lote-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      selectLoteForm.value = item.dataset.value;
      document.getElementById('lote-label').textContent = item.textContent.trim();
    });
  });

  // Dropdown Motivo: sincroniza texto del botón + select oculto
  document.querySelectorAll('.motivo-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      selectMotivo.value = item.dataset.value;
      document.getElementById('motivo-label').textContent = item.textContent.trim();
    });
  });

  // Al cambiar la presentación: muestra stock y filtra lotes del select oculto
  sel.addEventListener('change', function () {
    const configElement = document.getElementById('salida-config');
    let lotesData = {};

    if (configElement) {
      const data = configElement.getAttribute('data-lotes');
      if (data) {
        try {
          lotesData = JSON.parse(data);
        } catch (e) {
          console.error('Error al parsear datos de lotes:', e);
        }
      }
    }

    const d = lotesData[this.value];
    Array.from(selectLoteForm.options).forEach(opt => {
      if (!opt.value) { opt.selected = true; return; }
      opt.style.display = opt.dataset.presentacion === this.value ? '' : 'none';
    });
    if (!d) { badgeWrap.classList.add('d-none'); return; }
    badgeVal.textContent = d.stock;
    badgeWrap.classList.remove('d-none');
  });

  if (inputQty) {
    inputQty.addEventListener('input', function () {
      const configElement = document.getElementById('salida-config');
      let lotesData = {};

      if (configElement) {
        const data = configElement.getAttribute('data-lotes');
        if (data) {
          try {
            lotesData = JSON.parse(data);
          } catch (e) {
            console.error('Error al parsear datos de lotes:', e);
          }
        }
      }

      const d = lotesData[sel.value];
      alertaExceso.classList.toggle('d-none', !(d && +this.value > d.stock));
    });
  }
}

/**
 * Validación del formulario antes de enviar
 */
function inicializarValidacion() {
  const sel = document.getElementById('select-presentacion');
  const formSalida = document.getElementById('form-salida');

  if (!formSalida || !sel) return;

  formSalida.addEventListener('submit', function (e) {
    if (!sel.value) {
      e.preventDefault();
      const btn = document.getElementById('presentacion-btn');
      btn.classList.add('sal-campo-error');
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
}
