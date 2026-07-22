/* Interacciones pequeñas para el flujo de devoluciones. El proceso y las
   validaciones de negocio se mantienen en el servidor. */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('formDevoluciones');
  if (!form) return;

  const productChecks = [...form.querySelectorAll('.dev-product-check')];
  productChecks.forEach((check) => {
    const quantity = form.querySelector(`[name="cantidad_devolucion_${check.value}"]`);
    if (!quantity) return;

    quantity.disabled = !check.checked;
    check.addEventListener('change', () => {
      quantity.disabled = !check.checked;
      if (check.checked && Number(quantity.value) < 1) quantity.value = 1;
    });
  });

  form.addEventListener('submit', (event) => {
    const nextAction = event.submitter?.value !== 'atras';
    if (!nextAction) return;

    if (productChecks.length && !productChecks.some((check) => check.checked)) {
      event.preventDefault();
      window.alert('Selecciona al menos un producto para continuar.');
    }
  });

  const historyToggle = document.getElementById('devHistoryToggle');
  const historyBody = document.getElementById('devHistoryBody');
  let historyTableStarted = false;

  const startHistoryTable = () => {
    if (historyTableStarted || !window.jQuery || !jQuery.fn.DataTable) return;
    const table = jQuery('#tablaDevoluciones');
    if (!table.length) return;

    table.DataTable({
      responsive: true,
      pageLength: 5,
      lengthMenu: [[5, 10, 25, -1], [5, 10, 25, 'Todos']],
      order: [[5, 'desc']],
      columnDefs: [{ targets: [6], orderable: false, searchable: false }],
      language: {
        search: 'Buscar:',
        lengthMenu: 'Mostrar _MENU_',
        info: 'Mostrando _START_ a _END_ de _TOTAL_ devoluciones',
        infoEmpty: 'No hay devoluciones registradas',
        zeroRecords: 'No encontramos coincidencias',
        paginate: { first: 'Primera', last: 'Última', next: 'Siguiente', previous: 'Anterior' }
      }
    });
    historyTableStarted = true;
  };

  if (historyToggle && historyBody) {
    historyToggle.addEventListener('click', () => {
      const isOpen = !historyBody.classList.contains('d-none');
      historyBody.classList.toggle('d-none', isOpen);
      historyToggle.setAttribute('aria-expanded', String(!isOpen));
      if (!isOpen) startHistoryTable();
    });
  }
});
