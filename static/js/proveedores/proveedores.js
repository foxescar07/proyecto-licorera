// Inicializar gráficas
function initializeCharts() {
  const colores = {
    principal: '#4DA8DA',
    secundario: '#00C9A7',
    terciario: '#CF9C48',
    cuartario: '#9B59B6',
    quinto: '#22D3EE'
  };

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

$(document).ready(function() {
  // Inicializar gráficas
  initializeCharts();

  if ($.fn.DataTable.isDataTable('#tablaProveedores')) {
    $('#tablaProveedores').DataTable().destroy();
  }

  var table = $('#tablaProveedores').DataTable({
    paging: true,
    searching: true,
    info: true,
    lengthChange: false,
    pageLength: 10,
    ordering: true,
    columnDefs: [
      { orderable: false, targets: 8, searchable: false }
    ],
    language: {
      info: "Mostrando _START_ a _END_ de _TOTAL_ proveedores",
      infoEmpty: "Mostrando 0 a 0 de 0 proveedores",
      emptyTable: "No hay proveedores registrados.",
      zeroRecords: "Sin resultados para tu búsqueda.",
      paginate: { first:'«', previous:'‹', next:'›', last:'»' }
    },
    dom: 'rt<"d-flex justify-content-center align-items-center mt-3"ip>'
  });

  // Conectar input personalizado de búsqueda
  $('#buscar-proveedores').on('input', function() {
    table.search(this.value).draw();
  });

  // Variables para filtros
  var filtroEstadoActual = 'todos';
  var filtroTipoActual = 'todos';

  // Filtro por estado (Activo, Inactivo, Sancionado)
  $.fn.dataTable.ext.search.push(
    function(settings, data, dataIndex) {
      if (settings.sTableId !== 'tablaProveedores') return true;
      if (filtroEstadoActual === 'todos') return true;
      try {
        var node = table.row(dataIndex).node();
        if (node) {
          var estado = $(node).attr('data-estado');
          return estado === filtroEstadoActual;
        }
      } catch(e) {}
      return true;
    }
  );

  // Filtro por tipo de proveedor (Distribuidor, Fabricante, Importador)
  $.fn.dataTable.ext.search.push(
    function(settings, data, dataIndex) {
      if (settings.sTableId !== 'tablaProveedores') return true;
      if (filtroTipoActual === 'todos') return true;
      try {
        var node = table.row(dataIndex).node();
        if (node) {
          var tipo = $(node).attr('data-tipo');
          return tipo === filtroTipoActual;
        }
      } catch(e) {}
      return true;
    }
  );

  // Manejador para filtro de estado
  document.querySelectorAll('.filtro-estado-item').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      document.getElementById('filtroEstado-label').textContent = this.textContent.trim();
      filtroEstadoActual = this.dataset.estado;
      table.draw();
    });
  });

  // Manejador para filtro de tipo
  document.querySelectorAll('.filtro-tipo-item').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      document.getElementById('filtroTipo-label').textContent = this.textContent.trim();
      filtroTipoActual = this.dataset.tipo;
      table.draw();
    });
  });

  // Sincronizar export (si se usan filtros)
  function syncExportProv() {
    var q = $('#buscar-proveedores').val() || '';
    var p = q ? ('&q=' + encodeURIComponent(q)) : '';
    if (typeof $('#btn-export-excel-prov') !== 'undefined') {
      $('#btn-export-excel-prov').attr('href', '?export=excel&tipo=proveedores' + p);
      $('#btn-export-pdf-prov').attr('href',   '?export=pdf&tipo=proveedores' + p);
    }
  }
  $('#buscar-proveedores').on('keyup change', syncExportProv);
  syncExportProv();

  // Aplicar ancho dinámico a las barras desde data-width
  document.querySelectorAll('.bar-visual').forEach(bar => {
    const width = bar.getAttribute('data-width');
    if (width) {
      bar.style.width = width + '%';
    }
  });

  // ============================================
  // VALIDACIÓN DE NUEVO PROVEEDOR
  // ============================================
  const formNuevoProveedor = document.getElementById('formNuevoProveedor');
  const modalNuevoProveedor = document.getElementById('modalNuevoProveedor');

  if (formNuevoProveedor && modalNuevoProveedor) {
    // Prevenir cierre del modal si hay errores usando evento hide.bs.modal
    modalNuevoProveedor.addEventListener('hide.bs.modal', function(e) {
      const hasErrors = document.querySelectorAll('#formNuevoProveedor .invalid-feedback.d-block').length > 0;
      if (hasErrors) {
        e.preventDefault();
      }
    });

    // Prevenir cierre del modal al hacer clic en botones con data-bs-dismiss (fase de captura)
    document.addEventListener('click', function(e) {
      if (e.target.closest('#modalNuevoProveedor [data-bs-dismiss="modal"]')) {
        const hasErrors = document.querySelectorAll('#formNuevoProveedor .invalid-feedback.d-block').length > 0;
        if (hasErrors) {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }
      }
    }, true);

    // Manejar el envío del formulario
    formNuevoProveedor.addEventListener('submit', function(e) {
      e.preventDefault();

      // Limpiar errores previos
      document.querySelectorAll('#formNuevoProveedor .invalid-feedback').forEach(el => {
        el.innerHTML = '';
        el.classList.remove('d-block');
      });
      document.querySelectorAll('#formNuevoProveedor .prod-input').forEach(el => {
        el.classList.remove('is-invalid');
      });

      // Enviar formulario via AJAX
      const formData = new FormData(this);
      fetch(this.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // Mostrar toast de éxito
          showToast('Proveedor registrado exitosamente', 'success');

          // Cerrar modal y recargar tabla después de 2 segundos
          const modal = bootstrap.Modal.getInstance(modalNuevoProveedor);
          modal.hide();
          setTimeout(() => location.reload(), 1500);
        } else {
          // Mostrar errores debajo de cada campo
          if (data.errors) {
            for (const [field, messages] of Object.entries(data.errors)) {
              const errorDiv = document.getElementById(`error-${field}`);
              const input = document.getElementById(`id_${field}`);
              if (errorDiv && input) {
                const errorMsg = Array.isArray(messages) ? messages[0] : messages;
                errorDiv.innerHTML = `<small class="text-danger fw-bold"><i class="bi bi-exclamation-circle me-1"></i>${errorMsg}</small>`;
                errorDiv.classList.add('d-block');
                input.classList.add('is-invalid');
              }
            }
          }
        }
      })
      .catch(error => console.error('Error:', error));
    });
  }

  // Función para mostrar notificaciones estilo Bootstrap Alert
  function showToast(message, type = 'success') {
    const mainContent = document.querySelector('main') || document.body;

    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const icon = type === 'success' ? 'bi-check-circle' : 'bi-exclamation-circle';

    const alertHTML = `
      <div class="alert ${alertClass} alert-dismissible fade show d-flex align-items-center" role="alert" style="margin: 0; border-radius: 0; position: sticky; top: 0; z-index: 1050;">
        <i class="bi ${icon} me-2"></i>
        <div>${message}</div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>
      </div>
    `;

    mainContent.insertAdjacentHTML('afterbegin', alertHTML);
  }

  // ============================================
  // MANEJO DE ACCIONES CON MODALES
  // ============================================

  // Desactivar proveedor - Llenar modal y manejar envío
  document.querySelectorAll('.btn-desactivar').forEach(btn => {
    btn.addEventListener('click', function() {
      const providerId = this.dataset.providerId;
      const providerName = this.dataset.providerName;

      // Llenar datos del modal
      document.getElementById('proveedorDesactivarNombre').textContent = providerName;

      // Abrir modal
      const modalElement = document.getElementById('modalDesactivarGeneral');
      const modal = new bootstrap.Modal(modalElement);
      modal.show();

      // Manejar submit del formulario
      const form = document.getElementById('formDesactivarProveedor');
      form.onsubmit = function(e) {
        e.preventDefault();

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        fetch(`/proveedores/modal/desactivar/${providerId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              modal.hide();
              showToast(data.message, 'success');
              setTimeout(() => location.reload(), 1500);
            } else {
              showToast(data.error || 'Error al desactivar', 'error');
            }
          })
          .catch(error => {
            console.error('Error:', error);
            showToast('Error en la solicitud', 'error');
          });
      };
    });
  });

  // Reactivar proveedor
  document.querySelectorAll('.btn-reactivar').forEach(btn => {
    btn.addEventListener('click', function() {
      const providerId = this.dataset.providerId;
      const providerName = this.dataset.providerName;

      if (confirm(`¿Deseas reactivar a ${providerName}?`)) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        fetch(`/proveedores/modal/reactivar/${providerId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              showToast(data.message, 'success');
              setTimeout(() => location.reload(), 1500);
            } else {
              showToast(data.error || 'Error al reactivar', 'error');
            }
          })
          .catch(error => console.error('Error:', error));
      }
    });
  });

  // Sancionar proveedor - Llenar modal y manejar envío
  document.querySelectorAll('.btn-sancionar').forEach(btn => {
    btn.addEventListener('click', function() {
      const providerId = this.dataset.providerId;
      const providerName = this.dataset.providerName;

      // Llenar datos del modal
      document.getElementById('proveedorSancionarNombre').textContent = providerName;

      // Limpiar textarea
      document.getElementById('motivoSancion').value = '';

      // Abrir modal
      const modalElement = document.getElementById('modalSancionarGeneral');
      const modal = new bootstrap.Modal(modalElement);
      modal.show();

      // Manejar submit del formulario
      const form = document.getElementById('formSancionar');
      form.onsubmit = function(e) {
        e.preventDefault();

        const observacion = document.getElementById('motivoSancion').value;

        if (!observacion.trim()) {
          showToast('Debes indicar el motivo de la sanción', 'error');
          return;
        }

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const formData = new FormData();
        formData.append('observacion', observacion);
        formData.append('csrfmiddlewaretoken', csrfToken);

        fetch(`/proveedores/modal/sancionar/${providerId}/`, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              modal.hide();
              showToast(data.message, 'success');
              setTimeout(() => location.reload(), 1500);
            } else {
              showToast(data.error || 'Error al sancionar', 'error');
            }
          })
          .catch(error => {
            console.error('Error:', error);
            showToast('Error en la solicitud', 'error');
          });
      };
    });
  });

  // Levantar sanción
  document.querySelectorAll('.btn-levantar-sancion').forEach(btn => {
    btn.addEventListener('click', function() {
      const providerId = this.dataset.providerId;
      const providerName = this.dataset.providerName;

      if (confirm(`¿Deseas levantar la sanción a ${providerName}?`)) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        fetch(`/proveedores/modal/levantar-sancion/${providerId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              showToast(data.message, 'success');
              setTimeout(() => location.reload(), 1500);
            } else {
              showToast(data.error || 'Error al levantar sanción', 'error');
            }
          })
          .catch(error => console.error('Error:', error));
      }
    });
  });
});
