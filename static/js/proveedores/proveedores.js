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
    responsive: true,
    columnDefs: [
      { responsivePriority: 1, targets: 0 },  // #
      { responsivePriority: 2, targets: 1 },  // Empresa
      { responsivePriority: 3, targets: 2 },  // NIT
      { responsivePriority: 4, targets: 8 },  // Acciones
      { responsivePriority: 5, targets: 3 },  // Contacto
      { responsivePriority: 6, targets: 4 },  // Tipo
      { responsivePriority: 7, targets: 5 },  // Estado
      { responsivePriority: 8, targets: 6 },  // Responsable
      { responsivePriority: 9, targets: 7 }   // Fecha Registro
    ],
    language: {
      info: "Mostrando _START_ a _END_ de _TOTAL_ proveedores",
      infoEmpty: "Mostrando 0 a 0 de 0 proveedores",
      emptyTable: "No hay proveedores registrados.",
      zeroRecords: "Sin resultados para tu búsqueda.",
      paginate: { first:'«', previous:'‹', next:'›', last:'»' }
    },
    dom: 'rt<"d-flex justify-content-center align-items-center mt-3"ip>',
    drawCallback: function() {
      // Callback para acciones después de dibujar la tabla
    }
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
    function(settings, data, dataIndex, rowData, counter) {
      if (settings.sTableId !== 'tablaProveedores') return true;
      if (filtroEstadoActual === 'todos') return true;
      var node = settings.aoData[dataIndex].nTr;
      var estado = $(node).attr('data-estado');
      return estado === filtroEstadoActual;
    }
  );

  // Filtro por tipo de proveedor (Distribuidor, Fabricante, Importador)
  $.fn.dataTable.ext.search.push(
    function(settings, data, dataIndex, rowData, counter) {
      if (settings.sTableId !== 'tablaProveedores') return true;
      if (filtroTipoActual === 'todos') return true;
      var node = settings.aoData[dataIndex].nTr;
      var tipo = $(node).attr('data-tipo');
      return tipo === filtroTipoActual;
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
});
