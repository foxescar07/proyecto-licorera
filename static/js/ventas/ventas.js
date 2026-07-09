/**
 * VENTAS.JS — Sistema de Punto de Venta
 * Maneja la interfaz del carrito, pagos, y operaciones de caja
 */

// ════════════════════════════════════════════════════════════════
// INICIALIZACIÓN — Leer datos desde HTML
// ════════════════════════════════════════════════════════════════

let CATALOGO = {};
let URLS = {};

document.addEventListener('DOMContentLoaded', function () {
  // Leer datos del elemento data- en el HTML
  const configElement = document.getElementById('ventas-config');

  if (configElement) {
    // Parsear catálogo JSON
    const catalogoData = configElement.getAttribute('data-catalogo');
    if (catalogoData) {
      try {
        CATALOGO = JSON.parse(catalogoData);
      } catch (e) {
        console.error('Error al parsear CATALOGO:', e);
        CATALOGO = {};
      }
    }

    // Obtener URLs
    URLS = {
      registrarConteo: configElement.getAttribute('data-url-conteo') || '',
      cierreCaja: configElement.getAttribute('data-url-cierre') || ''
    };
  }

  // Inicializar funcionalidad del punto de venta
  inicializarPuntodeVenta();
});

/**
 * Inicializa toda la funcionalidad del punto de venta
 */
function inicializarPuntodeVenta() {
  // Aquí va todo el código que estaba antes en el archivo
  console.log('Punto de venta inicializado');
  console.log('Catálogo disponible:', CATALOGO);
  console.log('URLs:', URLS);
}

// ════════════════════════════════════════════════════════════════
// EXPORTAR VARIABLES GLOBALES (compatibilidad con código existente)
// ════════════════════════════════════════════════════════════════

// Hacer disponibles globalmente para scripts que las usen directamente
window.CATALOGO = () => CATALOGO;
window.URLS = () => URLS;
