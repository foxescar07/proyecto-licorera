/**
 * GESTION_STOCK.JS — Gestión de Stock & Productos
 * DataTable con búsqueda, filtros y formateo de moneda
 */

function formatMiles(n) {
  var num = parseInt(String(n).replace(/\D/g, ''), 10);
  if (isNaN(num)) return n;
  return num.toLocaleString('es-CO');
}

// ── TOOLTIPS: inicialización simple ──
function inicializarTooltipsLotes() {
  document.querySelectorAll('#tablaLotes [title]').forEach(function (el) {
    var existente = bootstrap.Tooltip.getInstance(el);
    if (existente) existente.dispose();

    new bootstrap.Tooltip(el, {
      placement: 'top',
      trigger: 'hover',
      container: 'body'
    });
  });
}

$(document).ready(function() {
  if ($.fn.DataTable.isDataTable('#tablaLotes')) {
    $('#tablaLotes').DataTable().destroy();
  }

  var table = $('#tablaLotes').DataTable({
    paging: true,
    searching: true,
    info: true,
    lengthChange: false,
    pageLength: 10,
    ordering: true,
    responsive: true,
    columnDefs: [
    { responsivePriority: 1, targets: 0 },  // Producto / Presentación — siempre visible
    { responsivePriority: 2, targets: 2 },  // Stock
    { responsivePriority: 3, targets: 4 },  // Estado
    { responsivePriority: 4, targets: 7 },  // Acciones
    { responsivePriority: 5, targets: 3 },  // Vencimiento
    { responsivePriority: 6, targets: 1 },  // Nº Lote
    { responsivePriority: 7, targets: 5 },  // Costo unit.
    { responsivePriority: 8, targets: 6 }   // Valor total
  ],
    language: {
      info: "Mostrando _START_ a _END_ de _TOTAL_ lotes",
      infoEmpty: "Mostrando 0 a 0 de 0 lotes",
      emptyTable: "No hay lotes con stock activo.",
      zeroRecords: "Sin resultados para tu búsqueda.",
      paginate: { first: '«', previous: '‹', next: '›', last: '»' }
    },
    dom: 'rt<"d-flex justify-content-center align-items-center mt-3"ip>',
    drawCallback: function() {
      $('#tablaLotes tbody tr').each(function() {
        [5, 6].forEach(function(idx) {
          var $td = $(this).find('td').eq(idx);
          var $span = $td.find('span');
          if ($span.length) {
            var texto = $span.text().trim();
            var num = texto.replace('$', '').replace(/\./g, '').trim();
            if (num && !isNaN(num) && parseInt(num) > 0) {
              $span.text('$' + formatMiles(num));
            }
          }
        }.bind(this));
      });
      inicializarTooltipsLotes();
    }
  });

  inicializarTooltipsLotes();

  $('#buscarLote').on('input', function() {
    table.search(this.value).draw();
  });

  var filtroEstadoActual = 'todos';

  $.fn.dataTable.ext.search.push(
    function(settings, data, dataIndex, rowData, counter) {
      if (settings.sTableId !== 'tablaLotes') return true;
      if (filtroEstadoActual === 'todos') return true;
      var node = settings.aoData[dataIndex].nTr;
      var estado = $(node).attr('data-estado');
      return estado === filtroEstadoActual;
    }
  );

  document.querySelectorAll('.filtro-estado-item').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      document.getElementById('filtroEstado-label').textContent = this.textContent.trim();
      filtroEstadoActual = this.dataset.estado;
      table.draw();
    });
  });

  const params = new URLSearchParams(window.location.search);
  const termino = params.get('buscar');
  if (termino) {
    $('#buscarLote').val(termino);
    table.search(termino).draw();

    setTimeout(() => {
      const row = table.row({search: 'applied'}).node();
      if (row) {
        $(row).css({transition: 'background-color 0.3s ease', backgroundColor: 'rgba(77,168,218,0.18)'});
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 100);
  }
});
