/**
 * GESTION_LOTES.JS — Gestión de Lotes de Inventario
 * Funcionalidades: gráfico de stock, dropdown de presentación, validación
 */

document.addEventListener('DOMContentLoaded', function () {
  // Inicializar gráfico de proveedores
  inicializarGraficoProveedores();

  // Inicializar dropdown de presentación
  inicializarDropdownPresentacion();

  // Inicializar validación de formulario
  inicializarValidacionFormulario();
});

/**
 * Crea el gráfico de barras de stock por producto
 */
function inicializarGraficoProveedores() {
  const canvas = document.getElementById('chartProveedores');
  if (!canvas) return;

  // Los datos vienen del servidor (Django) mediante atributos data-
  const configElement = document.getElementById('lotes-config');
  let labels = [];
  let data = [];

  if (configElement) {
    const labelsData = configElement.getAttribute('data-labels');
    const chartData = configElement.getAttribute('data-data');

    if (labelsData && chartData) {
      try {
        labels = JSON.parse(labelsData);
        data = JSON.parse(chartData);
      } catch (e) {
        console.error('Error al parsear datos del gráfico:', e);
      }
    }
  }

  new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Unidades en stock',
        data: data,
        backgroundColor: [
          'rgba(62, 181, 229, 0.85)',
          'rgb(190, 87, 231)',
          'rgb(10, 74, 169)',
          'rgba(108, 92, 231, 0.85)',
          'rgba(155, 254, 218, 0.85)'
        ],
        borderColor: ['#4195c9', '#d059ff', '#014ab0', '#6c5ce7', '#9bfebc'],
        borderWidth: 1,
        borderRadius: 5
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.06)' },
          ticks: { color: '#dce8f2', font: { size: 10 } }
        },
        y: {
          grid: { display: false },
          ticks: { color: '#dce8f2', font: { size: 11, weight: '600' } }
        }
      }
    }
  });
}

/**
 * Sincroniza el dropdown visual con el select oculto
 */
function inicializarDropdownPresentacion() {
  const selLote = document.getElementById('select-presentacion-lote');
  if (!selLote) return;

  document.querySelectorAll('.presentacion-lote-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      selLote.value = item.dataset.value;
      document.getElementById('presentacion-lote-label').textContent = item.textContent.trim();
    });
  });
}

/**
 * Validación del formulario antes de enviar
 */
function inicializarValidacionFormulario() {
  const formLote = document.getElementById('form-lote');
  const selLote = document.getElementById('select-presentacion-lote');

  if (!formLote || !selLote) return;

  formLote.addEventListener('submit', e => {
    if (!selLote.value) {
      e.preventDefault();
      const btn = document.getElementById('presentacion-lote-btn');
      btn.style.borderColor = '#e74c3c';
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
}
document.querySelectorAll('.lote-spin-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.target);
    if (!input) return;
    const step = parseFloat(input.step) || 1;
    const min = input.min !== '' ? parseFloat(input.min) : -Infinity;
    let valor = parseFloat(input.value) || 0;
    valor = btn.classList.contains('lote-spin-up') ? valor + step : valor - step;
    if (valor < min) valor = min;
    input.value = valor;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
});