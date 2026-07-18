// ════════════════════════════════════════════════════════════════
// DEVOLUCIONES.JS — Control de flujo y funcionalidad
// ════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function() {
  // ════════════════════════════════════════════════════════════════
  // ACTUALIZAR PRODUCTOS CUANDO CAMBIA LA VENTA
  // ════════════════════════════════════════════════════════════════

  const ventaRadios = document.querySelectorAll('input[name="venta_id"]');

  ventaRadios.forEach(radio => {
    radio.addEventListener('change', function() {
      if (this.checked) {
        cargarProductosDeLaVenta(this.value);
      }
    });
  });

  window.cargarProductosDeLaVenta = function(ventaId) {
    fetch(`/ventas/devoluciones/detalle/${ventaId}/`)
      .then(response => {
        if (!response.ok) throw new Error('Error al cargar detalles de la venta');
        return response.json();
      })
      .then(data => {
        actualizarTablaProductos(data);
      })
      .catch(error => {
        console.error('Error:', error);
        alert('Error al cargar los productos. Por favor intenta de nuevo.');
      });
  };

  window.actualizarTablaProductos = function(ventaData) {
    const tablasContenedor = document.getElementById('tablasContenedor');

    if (!tablasContenedor) {
      console.error('No se encontró el contenedor de tablas');
      return;
    }

    if (!ventaData.detalles || ventaData.detalles.length === 0) {
      tablasContenedor.innerHTML = '<div class="text-center py-4 px-2"><i class="bi bi-inbox text-muted"></i><p class="text-muted fs-small">No hay productos en esta venta.</p></div>';
      return;
    }

    let html = `
      <div class="table-responsive mb-3">
        <table class="table-clean">
          <thead>
            <tr class="table-head-row">
              <th class="table-head-cell">✓</th>
              <th class="table-head-cell table-head-cell-left">Producto</th>
              <th class="table-head-cell">Original</th>
              <th class="table-head-cell">Devuelto</th>
              <th class="table-head-cell">Pendiente</th>
              <th class="table-head-cell">A Devolver</th>
              <th class="table-head-cell table-head-cell-right">Precio</th>
              <th class="table-head-cell table-head-cell-right">Subtotal</th>
            </tr>
          </thead>
          <tbody>
    `;

    ventaData.detalles.forEach(detalle => {
      html += `
        <tr class="table-body-row">
          <td class="table-body-cell table-body-cell-center">
            <input type="checkbox"
                   name="producto_id"
                   value="${detalle.detalle_id}"
                   class="form-check-input producto-checkbox"
                   onchange="updateSubtotal(this)">
          </td>
          <td class="table-body-cell">
            <div class="product-name-cell">${detalle.producto}</div>
            ${detalle.presentacion ? `<div class="product-subtext">${detalle.presentacion}</div>` : ''}
          </td>
          <td class="table-body-cell table-body-cell-center table-body-cell-fw">${detalle.cantidad}</td>
          <td class="table-body-cell table-body-cell-center table-body-cell-fw">0</td>
          <td class="table-body-cell table-body-cell-center table-body-cell-fw-bold">${detalle.cantidad}</td>
          <td class="table-body-cell table-body-cell-center">
            <input type="number"
                   name="cantidad_devolucion_${detalle.detalle_id}"
                   min="0"
                   max="${detalle.cantidad}"
                   value="0"
                   class="form-control cantidad-input table-cell-input"
                   onchange="updateCheckboxAndSubtotal(this, ${detalle.detalle_id})">
          </td>
          <td class="table-body-cell table-body-cell-right table-body-cell-fw">$${Math.round(detalle.precio).toLocaleString('es-CO')}</td>
          <td class="table-body-cell table-body-cell-right table-body-cell-fw-bold table-body-cell-cyan" data-subtotal="${detalle.detalle_id}">$0</td>
        </tr>
      `;
    });

    html += `
          </tbody>
        </table>
      </div>
      <div class="card-info-box mb-3">
        <div class="grid-3col">
          <div>
            <div class="text-muted text-xs uppercase fw-bold mb-05">Productos seleccionados</div>
            <div class="text-cyan fw-bold" id="productosCount">0</div>
          </div>
          <div>
            <div class="text-muted text-xs uppercase fw-bold mb-05">Cantidad total</div>
            <div class="text-cyan fw-bold" id="cantidadTotal">0</div>
          </div>
          <div>
            <div class="text-muted text-xs uppercase fw-bold mb-05">Monto a devolver</div>
            <div class="text-cyan fw-bold" id="montoTotal">$0</div>
          </div>
        </div>
      </div>
    `;

    tablasContenedor.innerHTML = html;
  };

  // ════════════════════════════════════════════════════════════════
  // FUNCIONES PARA PASO 2 — ACTUALIZAR CHECKBOX Y SUBTOTALES
  // ════════════════════════════════════════════════════════════════

  window.updateCheckboxAndSubtotal = function(input, detalleId) {
    const cantidad = parseInt(input.value) || 0;
    const checkbox = document.querySelector(`input[type="checkbox"][value="${detalleId}"]`);

    if (cantidad > 0) {
      checkbox.checked = true;
    } else {
      checkbox.checked = false;
    }

    updateSubtotal(checkbox);
  };

  window.updateSubtotal = function(checkbox) {
    const detalleId = checkbox.value;
    const cantidadInput = document.querySelector(`input[name="cantidad_devolucion_${detalleId}"]`);
    const row = checkbox.closest('tr');
    const precioUnitario = parseFloat(row.cells[6].textContent.replace('$', '').replace(',', ''));

    if (checkbox.checked) {
      cantidadInput.disabled = false;
      if (cantidadInput.value === '0') {
        cantidadInput.value = cantidadInput.max;
      }
    } else {
      cantidadInput.disabled = true;
      cantidadInput.value = 0;
    }

    const cantidad = parseInt(cantidadInput.value) || 0;
    const subtotal = cantidad * precioUnitario;
    row.querySelector(`[data-subtotal]`).textContent = `$${subtotal.toLocaleString('es-CO', {maximumFractionDigits: 0})}`;

    calculateTotals();
  };

  window.calculateTotals = function() {
    let productosCount = 0;
    let cantidadTotal = 0;
    let montoTotal = 0;

    document.querySelectorAll('.cantidad-input:not([disabled])').forEach(input => {
      const cantidad = parseInt(input.value) || 0;
      if (cantidad > 0) {
        productosCount++;
        cantidadTotal += cantidad;
        const precioUnitario = parseFloat(input.closest('tr').cells[6].textContent.replace('$', '').replace(',', ''));
        montoTotal += cantidad * precioUnitario;
      }
    });

    document.getElementById('productosCount').textContent = productosCount;
    document.getElementById('cantidadTotal').textContent = cantidadTotal;
    document.getElementById('montoTotal').textContent = `$${montoTotal.toLocaleString('es-CO', {maximumFractionDigits: 0})}`;
    document.getElementById('resumenMonto').textContent = `$${montoTotal.toLocaleString('es-CO', {maximumFractionDigits: 0})}`;
  };

  // ════════════════════════════════════════════════════════════════
  // PASO 3 — MOSTRAR/OCULTAR DETALLES DE REEMBOLSO
  // ════════════════════════════════════════════════════════════════

  const reembolsoRadios = document.querySelectorAll('input[name="tipo_reembolso"]');

  reembolsoRadios.forEach(radio => {
    radio.addEventListener('change', function() {
      const cambioDiv = document.getElementById('detalles-cambio');
      const reembolsoDiv = document.getElementById('detalles-reembolso');

      if (cambioDiv) cambioDiv.classList.add('d-none');
      if (reembolsoDiv) reembolsoDiv.classList.add('d-none');

      if (this.value === 'cambio' && cambioDiv) {
        cambioDiv.classList.remove('d-none');
      } else if (this.value === 'reembolso' && reembolsoDiv) {
        reembolsoDiv.classList.remove('d-none');
      }

      updateResumenReembolso();
    });
  });

  window.updateResumenReembolso = function() {
    const tipoSeleccionado = document.querySelector('input[name="tipo_reembolso"]:checked');
    const resumenTipo = document.getElementById('resumenTipo');
    const resumenPlazo = document.getElementById('resumenPlazo');

    if (!tipoSeleccionado) {
      if (resumenTipo) resumenTipo.textContent = 'No seleccionado';
      if (resumenPlazo) resumenPlazo.textContent = '—';
      return;
    }

    const tiposTexto = {
      'cambio': 'Cambio de producto',
      'nota_credito': 'Nota crédito',
      'reembolso': 'Reembolso'
    };

    const plazos = {
      'cambio': 'Inmediato',
      'nota_credito': 'Instantáneo',
      'reembolso': '3-7 días hábiles'
    };

    if (resumenTipo) resumenTipo.textContent = tiposTexto[tipoSeleccionado.value] || tipoSeleccionado.value;
    if (resumenPlazo) resumenPlazo.textContent = plazos[tipoSeleccionado.value] || '—';
  };

  // ════════════════════════════════════════════════════════════════
  // PASO 5 — DRAG & DROP DE ARCHIVOS
  // ════════════════════════════════════════════════════════════════

  const dropZone = document.getElementById('dropZone');
  if (dropZone) {
    const fileInput = document.getElementById('evidencia');
    const previewContainer = document.getElementById('previewContainer');
    const fileList = document.getElementById('fileList');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.style.background = 'rgba(77,168,218,0.1)';
      dropZone.style.borderColor = 'rgba(77,168,218,0.8)';
    });

    dropZone.addEventListener('dragleave', () => {
      dropZone.style.background = 'rgba(77,168,218,0.05)';
      dropZone.style.borderColor = 'rgba(77,168,218,0.5)';
    });

    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      fileInput.files = e.dataTransfer.files;
      updatePreview();
    });

    fileInput.addEventListener('change', updatePreview);

    function updatePreview() {
      fileList.innerHTML = '';
      if (fileInput.files.length > 0) {
        previewContainer.style.display = 'block';
        Array.from(fileInput.files).forEach((file, index) => {
          const fileItem = document.createElement('div');
          fileItem.className = 'file-preview-item';

          const icon = file.type.includes('image') ? 'image' : 'file-pdf';
          const size = (file.size / 1024 / 1024).toFixed(2);

          fileItem.innerHTML = `
            <i class="bi bi-${icon}"></i>
            <div>${file.name}</div>
            <div>${size} MB</div>
            <button type="button" class="btn-remove-file" onclick="this.closest('div').remove(); if(document.querySelectorAll('#fileList > div').length === 0) document.getElementById('previewContainer').style.display='none';">
              <i class="bi bi-x"></i>
            </button>
          `;
          fileList.appendChild(fileItem);
        });
      } else {
        previewContainer.style.display = 'none';
      }
    }
  }

  // ════════════════════════════════════════════════════════════════
  // HISTORIAL DESPLEGABLE — BUSCADOR Y DETALLES
  // ════════════════════════════════════════════════════════════════

  const historialToggle = document.getElementById('historialToggle');
  const historialContent = document.getElementById('historialContent');
  const searchInput = document.getElementById('searchHistorial');
  const sinResultados = document.getElementById('sinResultados');
  const listaDevolucionesHistorial = document.getElementById('listaDevolucionesHistorial');

  if (historialToggle) {
    historialToggle.addEventListener('click', function() {
      historialContent.classList.toggle('d-none');
      historialToggle.classList.toggle('active');
      const chevron = historialToggle.querySelector('.chevron-toggle');
      if (chevron) {
        chevron.style.transform = historialContent.classList.contains('d-none') ? 'rotate(0deg)' : 'rotate(180deg)';
      }
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', function(e) {
      const searchTerm = e.target.value.toLowerCase();
      const cards = document.querySelectorAll('.devolucion-card');
      let visibleCount = 0;

      cards.forEach(card => {
        const cliente = card.dataset.cliente.toLowerCase();
        const numero = card.dataset.numero.toLowerCase();
        const fecha = card.dataset.fecha.toLowerCase();

        const matches = cliente.includes(searchTerm) ||
                       numero.includes(searchTerm) ||
                       fecha.includes(searchTerm);

        if (matches || searchTerm === '') {
          card.style.display = '';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      if (visibleCount === 0 && searchTerm !== '') {
        sinResultados.classList.remove('d-none');
      } else {
        sinResultados.classList.add('d-none');
      }
    });
  }
});

// ════════════════════════════════════════════════════════════════
// MODAL COMPROBANTE — FUNCIONES GLOBALES
// ════════════════════════════════════════════════════════════════

// Toggle detalles de devolución y abrir modal
window.toggleDetalleDevolucion = function(element) {
  const card = element.closest('.devolucion-card');
  const detalle = card.querySelector('.devolucion-detalle');

  // Si no está expandido, lo expandimos y abrimos el modal
  if (detalle.classList.contains('d-none')) {
    detalle.classList.remove('d-none');
    card.classList.add('expanded');
    abrirModalComprobante(card);
  } else {
    // Si ya está expandido, solo lo colapsamos
    detalle.classList.add('d-none');
    card.classList.remove('expanded');
  }
};

// Abrir modal con datos de la devolución
function abrirModalComprobante(card) {
  // Obtener datos del card
  const devolucionId = card.getAttribute('data-id');
  const numero = card.querySelector('.devolucion-numero').textContent.trim();
  const cliente = card.querySelector('.devolucion-cliente').textContent.trim();
  const fecha = card.querySelector('.devolucion-fecha').textContent.trim();
  const monto = card.querySelector('.devolucion-monto').textContent.trim();

  // Obtener detalles expandidos
  const detalleDiv = card.querySelector('.devolucion-detalle');
  let motivo = '—';
  let tipoReembolso = '—';
  let observaciones = 'Sin observaciones';

  if (detalleDiv) {
    // Extraer motivo (primer bloque de información)
    const estadoDiv = detalleDiv.querySelector('.grid-2col');
    if (estadoDiv) {
      const divs = estadoDiv.querySelectorAll('div');
      if (divs.length > 0) {
        const motivoBlocks = divs[0].querySelectorAll('div');
        if (motivoBlocks.length > 1) {
          motivo = motivoBlocks[1].textContent.trim() || '—';
        }
      }
      // Extraer tipo de reembolso
      if (divs.length > 1) {
        const tipoBlocks = divs[1].querySelectorAll('div');
        if (tipoBlocks.length > 1) {
          tipoReembolso = tipoBlocks[1].textContent.trim() || '—';
        }
      }
    }

    // Extraer observaciones
    const textContent = detalleDiv.textContent;
    if (textContent) {
      const obsMatch = textContent.match(/Observaciones(.+?)(?:Ver comprobante|$)/s);
      if (obsMatch) {
        observaciones = obsMatch[1].trim() || 'Sin observaciones';
      }
    }
  }

  // Llenar el modal
  document.getElementById('modalId').textContent = devolucionId || '—';
  document.getElementById('modalNumero').textContent = numero;
  document.getElementById('modalCliente').textContent = cliente;
  document.getElementById('modalFecha').textContent = fecha;
  document.getElementById('modalMonto').textContent = monto;
  document.getElementById('modalMotivo').textContent = motivo;
  document.getElementById('modalTipoReembolso').textContent = tipoReembolso;
  document.getElementById('modalObservaciones').textContent = observaciones;

  // Actualizar botón del comprobante completo
  const linkBtn = document.getElementById('modalLinkComprobante');

  // Obtener ID del link de comprobante
  const comprobanteLink = card.querySelector('a[data-devolucion-id]');
  const devId = comprobanteLink ? comprobanteLink.getAttribute('data-devolucion-id') : devolucionId;

  // Remover onclick anterior si existe
  linkBtn.onclick = null;

  if (devId) {
    // Usar la URL correcta de Django
    const comprobanteUrl = `/ventas/devoluciones/comprobante/${devId}/`;

    linkBtn.onclick = function(e) {
      e.preventDefault();
      e.stopPropagation();
      window.location.href = comprobanteUrl;
      return false;
    };

    console.log('URL del comprobante:', comprobanteUrl);
  }

  // Abrir modal con Bootstrap
  try {
    const modalElement = document.getElementById('modalComprobante');
    const modal = new bootstrap.Modal(modalElement, {
      backdrop: true,
      keyboard: true
    });
    modal.show();
  } catch (e) {
    console.error('Error al abrir modal:', e);
  }
}
