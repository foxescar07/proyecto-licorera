// ════════════════════════════════════════════════════════════════
// DEVOLUCIONES.JS — Control de flujo y funcionalidad
// ════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function() {
  // Abrir modal si es Paso 1
  const urlParams = new URLSearchParams(window.location.search);
  const paso = document.querySelector('[data-paso]')?.dataset.paso;

  if (paso === '1') {
    const modal = new bootstrap.Modal(document.getElementById('modalSeleccionarVenta'), {
      backdrop: 'static',
      keyboard: false
    });
    modal.show();
  }

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
  };

  // ════════════════════════════════════════════════════════════════
  // PASO 6 — DRAG & DROP DE ARCHIVOS
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

  // Toggle del historial desplegable
  if (historialToggle) {
    historialToggle.addEventListener('click', function() {
      historialContent.classList.toggle('d-none');
      historialToggle.classList.toggle('active');
    });
  }

  // Búsqueda en tiempo real
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

      // Mostrar mensaje de sin resultados
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
