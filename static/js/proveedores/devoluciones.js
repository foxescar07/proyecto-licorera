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
});
