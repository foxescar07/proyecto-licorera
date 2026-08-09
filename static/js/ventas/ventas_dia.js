/**
 * VENTAS_DIA.JS — Panel de Ventas del Día
 * Funcionalidades: búsqueda, ordenamiento, barras de progreso dinámicas
 */

document.addEventListener('DOMContentLoaded', function () {
  // Aplicar ancho dinámico a barras de progreso
  document.querySelectorAll('.cys-rank-fill-dynamic[data-porcentaje]').forEach(function(bar) {
    const porcentaje = bar.getAttribute('data-porcentaje');
    bar.style.width = porcentaje + '%';
  });

  const buscador = document.getElementById('buscadorHistorialDia');
  const orden = document.getElementById('ordenHistorialDia');
  const tbody = document.getElementById('tablaHistorialDiaBody');
  const sinResultados = document.getElementById('sinResultadosDia');

  if (!tbody) return;

  function filasActuales() {
    return Array.from(tbody.querySelectorAll('tr[data-row]'));
  }

  function filtrar() {
    const texto = (buscador.value || '').toLowerCase().trim();
    let visibles = 0;
    filasActuales().forEach(function (fila) {
      const coincide = fila.dataset.buscar.indexOf(texto) !== -1;
      fila.style.display = coincide ? '' : 'none';
      if (coincide) visibles++;
    });
    if (sinResultados) {
      sinResultados.style.display = visibles === 0 ? 'block' : 'none';
    }
  }

  function ordenar() {
    const criterio = orden.value;
    const filas = filasActuales();

    filas.sort(function (a, b) {
      switch (criterio) {
        case 'reciente':
          return new Date(b.dataset.fecha) - new Date(a.dataset.fecha);
        case 'antiguo':
          return new Date(a.dataset.fecha) - new Date(b.dataset.fecha);
        case 'mayor_total':
          return parseFloat(b.dataset.total) - parseFloat(a.dataset.total);
        case 'menor_total':
          return parseFloat(a.dataset.total) - parseFloat(b.dataset.total);
        default:
          return 0;
      }
    });

    filas.forEach(function (fila) {
      tbody.appendChild(fila);
    });
  }

  if (buscador) buscador.addEventListener('input', filtrar);
  if (orden) orden.addEventListener('change', ordenar);
});
