$(document).ready(function() {
  var table = $('#tablaProveedores').DataTable({
    paging: true,
    searching: true,
    info: true,
    lengthChange: false,
    pageLength: 10,
    ordering: false,
    responsive: true,
    language: {
      info: "Mostrando _START_ a _END_ de _TOTAL_ proveedores",
      infoEmpty: "Mostrando 0 a 0 de 0 proveedores",
      paginate: { first:'«', previous:'‹', next:'›', last:'»' }
    },
    dom: 'rt<"cys-hv-table-footer"ip>'
  });

  // Conectar input personalizado
  $('#buscar-proveedores').on('keyup', function() {
    table.search(this.value).draw();
  });

  // Sincronizar export (si se usan filtros de fecha u otros parámetros)
  function syncExportProv() {
    // ejemplo: añadir query de búsqueda actual si se requiere
    var q = $('#buscar-proveedores').val() || '';
    var p = q ? ('&q=' + encodeURIComponent(q)) : '';
    $('#btn-export-excel-prov').attr('href', '?export=excel&tipo=proveedores' + p);
    $('#btn-export-pdf-prov').attr('href',   '?export=pdf&tipo=proveedores' + p);
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
