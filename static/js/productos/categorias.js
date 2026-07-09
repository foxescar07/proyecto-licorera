/**
 * CATEGORIAS.JS — Gestión de Categorías
 * Dropdowns para seleccionar categoría padre, tooltips
 */

document.addEventListener('DOMContentLoaded', function() {
  // Dropdown crear categoría
  document.querySelectorAll('.cat-padre-item').forEach(function(item) {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      document.getElementById('crear-padre-label').textContent = this.textContent.trim();
      document.getElementById('crear-padre-hidden').value = this.dataset.value;
    });
  });

  // Dropdown editar categoría
  document.querySelectorAll('.edit-padre-item').forEach(function(item) {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      const target = this.dataset.target;
      document.getElementById('edit-padre-label-' + target).textContent = this.textContent.trim();
      document.getElementById('edit-padre-hidden-' + target).value = this.dataset.value;
    });
  });

  // Tooltips en botones Editar/Eliminar
  const tooltipTriggerList = document.querySelectorAll('.cat-card [title]');
  tooltipTriggerList.forEach(function (el) {
    new bootstrap.Tooltip(el, {
      placement: 'top',
      trigger: 'hover'
    });
  });
});
