// ════════════════════════════════════════════════════════════════
// INICIALIZACIÓN GENERAL
// ════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function() {
  // Abrir modal de proveedores si está en parámetro GET
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('modal') === 'proveedores') {
    const modalProveedores = new bootstrap.Modal(document.getElementById('modalProveedores'));
    modalProveedores.show();
  }

  // Búsqueda de productos
  const buscarProducto = document.getElementById('buscarProducto');
  if (buscarProducto) {
    buscarProducto.addEventListener('input', function(e) {
      const busqueda = e.target.value.toLowerCase();
      document.querySelectorAll('#gridProductos > div').forEach(item => {
        const nombre = item.dataset.nombre;
        const categoria = item.dataset.categoria;
        const coincide = nombre.includes(busqueda) || categoria.includes(busqueda);
        item.style.display = coincide ? '' : 'none';
      });
    });
  }

  // Selección de producto
  document.querySelectorAll('.producto-radio').forEach(radio => {
    radio.addEventListener('change', function() {
      document.getElementById('productoSeleccionado').value = this.value;
    });
  });

  // Búsqueda y selección de proveedores
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

  // Función para seleccionar proveedor sin cerrar el modal
  window.seleccionarProveedor = function(proveedorId, proveedorNombre) {
    // Actualizar input hidden
    const inputProveedor = document.getElementById('proveedorSeleccionado');
    if (inputProveedor) {
      inputProveedor.value = proveedorId;
    }

    // Actualizar botón selector
    const btnSelector = document.querySelector('.btn-selector');
    if (btnSelector) {
      btnSelector.innerHTML = `
        <span class="d-flex align-items-center gap-2">
          <i class="bi bi-truck"></i>
          ${proveedorNombre}
        </span>
        <i class="bi bi-chevron-down"></i>
      `;
    }
  };

  // ====== GRÁFICOS CON CHART.JS ======
  initializeCharts();
});

// ════════════════════════════════════════════════════════════════
// GRÁFICOS
// ════════════════════════════════════════════════════════════════

function initializeCharts() {
  // Colores para los gráficos
  const colores = {
    principal: '#4DA8DA',
    secundario: '#00C9A7',
    terciario: '#9B59B6',
    cuartario: '#f0d080',
    quinto: '#E05C7A'
  };

  // Datos dinámicos del servidor
  const meseslabels = window.meseslabels || [];
  const mesesa = window.mesesa || [];
  const productosLabels = window.productosLabels || [];
  const productosData = window.productosData || [];
  const gastosLabels = window.gastosLabels || [];
  const gastosData = window.gastosData || [];
  const gastosPorcentajes = window.gastosPorcentajes || [];

  // Generar colores dinámicos para los gráficos
  const coloresGraficos = [
    colores.principal,
    colores.secundario,
    colores.terciario,
    colores.cuartario,
    colores.quinto
  ];

  // 1. Gráfico de línea: Compras por mes
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

  // 2. Gráfico de barras: Productos más comprados
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

  // 3. Gráfico de pastel: Gastos por proveedor
  const ctxGastosProveedor = document.getElementById('chartGastosProveedor');
  if (ctxGastosProveedor && gastosLabels.length > 0) {
    // Crear labels con porcentajes
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

// ════════════════════════════════════════════════════════════════
// SELECCIÓN DE MÉTODO DE PAGO (TARJETAS COMPACTAS)
// ════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.metodo-pago-card-compact').forEach(card => {
    card.addEventListener('click', function() {
      // Quitar selección anterior
      document.querySelectorAll('.metodo-pago-card-compact').forEach(c => c.classList.remove('active'));

      // Activar tarjeta seleccionada
      this.classList.add('active');

      // Guardar valor en input oculto
      document.getElementById('metodoPago').value = this.dataset.value;
    });
  });

  // Mostrar/ocultar monto pagado según estado
  document.getElementById('estadoPago')?.addEventListener('change', function() {
    const montoPagadoDiv = document.getElementById('montoPagadoDiv');
    if (this.value === 'parcial') {
      montoPagadoDiv.style.display = 'block';
    } else {
      montoPagadoDiv.style.display = 'none';
    }
  });

  // Enviar formulario de pago
  document.getElementById('formPago')?.addEventListener('submit', function(e) {
    e.preventDefault();

    // Validar que se seleccionó método de pago
    if (!document.getElementById('metodoPago').value) {
      alert('Por favor selecciona un método de pago');
      return;
    }

    const compraId = document.getElementById('compraId').value;
    const formData = new FormData(this);

    fetch(`/proveedores/compras/${compraId}/pago/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
      body: formData
    })
    .then(r => r.json())
    .then(d => {
      if (d.status === 'ok') {
        alert('✓ Pago registrado correctamente');
        bootstrap.Modal.getInstance(document.getElementById('modalPago')).hide();
        location.reload();
      } else {
        alert('Error: ' + d.message);
      }
    })
    .catch(err => {
      console.error('Error:', err);
      alert('Error al guardar el pago');
    });
  });

  // Formulario de cambio de estado
  const formEstadoCompra = document.getElementById('formEstadoCompra');
  if (formEstadoCompra) {
    formEstadoCompra.addEventListener('submit', function(e) {
      e.preventDefault();
      const compraId = document.getElementById('compraEstadoId').value;
      const formDataEstado = new FormData(this);
      fetch(`/proveedores/compras/${compraId}/cambiar-estado/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
        body: formDataEstado
      })
      .then(r => r.json())
      .then(d => {
        if (d.status === 'ok') {
          alert('✓ Estado actualizado correctamente');
          bootstrap.Modal.getInstance(document.getElementById('modalEstadoCompra')).hide();
          location.reload();
        } else {
          alert('Error: ' + d.message);
        }
      })
      .catch(err => {
        console.error('Error:', err);
        alert('Error al actualizar el estado');
      });
    });
  }
});

// ════════════════════════════════════════════════════════════════
// FUNCIONES DE MODALES
// ════════════════════════════════════════════════════════════════

function abrirModalPago(compraId) {
  // Limpiar formulario
  document.getElementById('formPago').reset();
  document.querySelectorAll('.metodo-pago-card-compact').forEach(c => c.classList.remove('active'));
  document.getElementById('montoPagadoDiv').style.display = 'none';

  // Establecer ID de compra
  document.getElementById('compraId').value = compraId;
}

function abrirModalEstado(compraId, estadoActual) {
  const modal = new bootstrap.Modal(document.getElementById('modalEstadoCompra'));
  document.getElementById('compraEstadoId').value = compraId;
  const selectEstado = document.getElementById('nuevoEstado');
  if (selectEstado) {
    selectEstado.value = estadoActual || 'pendiente';
  }
  modal.show();
}

function cambiarEstado(compraId, nuevoEstado) {
  // Esta función puede ser llamada directamente desde onclick en el HTML
  // Para máxima compatibilidad con el markup actual
  const formData = new FormData();
  formData.append('estado', nuevoEstado);
  formData.append('compra_id', compraId);

  fetch(`/proveedores/compras/${compraId}/cambiar-estado/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
    body: formData
  })
  .then(r => r.json())
  .then(d => {
    if (d.status === 'ok') {
      alert('✓ Estado actualizado correctamente');
      location.reload();
    } else {
      alert('Error: ' + d.message);
    }
  })
  .catch(err => {
    console.error('Error:', err);
    alert('Error al actualizar el estado');
  });
}
