// ════════════════════════════════════════════════════════════════
// FUNCIONES DE FORMATO
// ════════════════════════════════════════════════════════════════

function formatearNumero(numero) {
  const num = parseInt(numero) || 0;
  return '$' + num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

// ════════════════════════════════════════════════════════════════
// INICIALIZACIÓN GENERAL
// ════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function() {
  // Formatear números KPI con separadores
  const elementosFormato = document.querySelectorAll('.kpi-formatted');
  elementosFormato.forEach(elemento => {
    const valor = elemento.dataset.value;
    if (valor) {
      elemento.textContent = formatearNumero(valor);
    }
  });
  // Abrir modal de proveedores si está en parámetro GET
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('modal') === 'proveedores') {
    const modalProveedores = new bootstrap.Modal(document.getElementById('modalProveedores'));
    modalProveedores.show();
  }

  // Búsqueda de proveedores
  const buscarProveedor = document.getElementById('buscarProveedor');
  const tablaProveedores = document.getElementById('tablaProveedores');
  const sinResultados = document.getElementById('sinResultados');

  if (buscarProveedor) {
    buscarProveedor.addEventListener('input', function() {
      const termino = this.value.toLowerCase();
      let visible = 0;
      const filas = document.querySelectorAll('.fila-proveedor');
      filas.forEach(fila => {
        const coincide = fila.dataset.nombre.includes(termino) ||
                        fila.dataset.contacto.includes(termino) ||
                        fila.dataset.telefono.includes(termino);
        fila.style.display = coincide ? '' : 'none';
        if (coincide) visible++;
      });
      sinResultados.style.display = visible === 0 && termino !== '' ? 'block' : 'none';
    });
  }

  // Mostrar/ocultar monto pagado según estado
  const estadoPago = document.getElementById('estadoPago');
  if (estadoPago) {
    estadoPago.addEventListener('change', function() {
      const montoPagadoDiv = document.getElementById('montoPagadoDiv');
      if (this.value === 'parcial') {
        montoPagadoDiv.style.display = 'block';
      } else {
        montoPagadoDiv.style.display = 'none';
      }
    });
  }

  // Preparar modal de pago
  const modalPago = document.getElementById('modalPago');
  if (modalPago) {
    modalPago.addEventListener('show.bs.modal', function(event) {
      const button = event.relatedTarget;
      if (button && button.dataset.compraId) {
        document.getElementById('compraId').value = button.dataset.compraId;
        // Actualizar action del formulario con el ID de compra
        const formPago = document.getElementById('formPago');
        if (formPago) {
          formPago.action = `/proveedores/compras/${button.dataset.compraId}/pago/`;
        }
      }
      // Limpiar y ocultar campos
      const formPago = document.getElementById('formPago');
      if (formPago) {
        formPago.reset();
      }
      document.getElementById('montoPagadoDiv').style.display = 'none';
    });
  }

  // Inicializar gráficas
  initializeCharts();
});

// ════════════════════════════════════════════════════════════════
// GRÁFICOS CON CHART.JS
// ════════════════════════════════════════════════════════════════

function initializeCharts() {
  const colores = {
    principal: '#4DA8DA',
    secundario: '#00C9A7',
    terciario: '#9B59B6',
    cuartario: '#f0d080',
    quinto: '#E05C7A'
  };

  const meseslabels = window.meseslabels || [];
  const mesesa = window.mesesa || [];
  const productosLabels = window.productosLabels || [];
  const productosData = window.productosData || [];
  const gastosLabels = window.gastosLabels || [];
  const gastosData = window.gastosData || [];
  const gastosPorcentajes = window.gastosPorcentajes || [];

  const coloresGraficos = [
    colores.principal,
    colores.secundario,
    colores.terciario,
    colores.cuartario,
    colores.quinto
  ];

  // Gráfico de línea: Compras por mes
  const ctxComprasMes = document.getElementById('chartComprasMes');
  if (ctxComprasMes && meseslabels.length > 0) {
    new Chart(ctxComprasMes, {
      type: 'line',
      data: {
        labels: meseslabels,
        datasets: [{
          label: 'Compras',
          data: mesesa,
          borderColor: colores.principal,
          backgroundColor: 'rgba(77, 168, 218, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: colores.principal,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(77, 168, 218, 0.1)',
              drawBorder: false
            },
            ticks: {
              color: '#FFFFFF',
              font: {
                size: 12,
                weight: 'bold'
              }
            }
          },
          x: {
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              color: '#FFFFFF',
              font: {
                size: 12,
                weight: 'bold'
              }
            }
          }
        }
      }
    });
  }

  // Gráfico de barras: Productos más comprados
  const ctxProductosTop = document.getElementById('chartProductosTop');
  if (ctxProductosTop && productosLabels.length > 0) {
    new Chart(ctxProductosTop, {
      type: 'bar',
      data: {
        labels: productosLabels,
        datasets: [{
          label: 'Cantidad',
          data: productosData,
          backgroundColor: coloresGraficos.slice(0, productosLabels.length),
          borderRadius: 6,
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: {
              color: 'rgba(77, 168, 218, 0.1)',
              drawBorder: false
            },
            ticks: {
              color: '#FFFFFF',
              font: {
                size: 12,
                weight: 'bold'
              }
            }
          },
          y: {
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              color: '#FFFFFF',
              font: {
                size: 13,
                weight: 'bold'
              },
              padding: 10
            }
          }
        }
      }
    });
  }

  // Gráfico de pastel: Gastos por proveedor
  const ctxGastosProveedor = document.getElementById('chartGastosProveedor');
  if (ctxGastosProveedor && gastosLabels.length > 0) {
    const gastosLabelsConPorcentaje = gastosLabels.map((label, idx) =>
      `${label} - ${gastosPorcentajes[idx]}%`
    );

    new Chart(ctxGastosProveedor, {
      type: 'doughnut',
      data: {
        labels: gastosLabelsConPorcentaje,
        datasets: [{
          data: gastosData,
          backgroundColor: coloresGraficos.slice(0, gastosLabels.length),
          borderColor: '#011936',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#FFFFFF',
              padding: 15,
              font: {
                size: 12,
                weight: 'bold'
              }
            }
          }
        }
      }
    });
  }
}
