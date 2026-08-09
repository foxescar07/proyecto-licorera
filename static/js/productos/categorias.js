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
document.querySelectorAll('.cat-btn-confirmar-borrado').forEach(function (btn) {
  btn.addEventListener('click', function () {
    // 1. Encontramos el <form> al que pertenece este botón
    const form = btn.closest('form');
    const nombre = form.dataset.nombre;

    // 2. Escribimos el mensaje dinámico en el modal
    document.getElementById('confirmar-mensaje').textContent =
      '¿Eliminar definitivamente «' + nombre + '»?';

    // 3. Preparamos el modal para mostrarse
    const modalEl = document.getElementById('modalConfirmarAccion');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    const btnAceptar = document.getElementById('confirmar-btn-aceptar');

    // 4. Truco importante: clonamos el botón "Eliminar" para borrar
    //    cualquier evento de clic que le hubiéramos puesto antes
    const nuevoBtn = btnAceptar.cloneNode(true);
    btnAceptar.parentNode.replaceChild(nuevoBtn, btnAceptar);

    // 5. Le decimos qué hacer SOLO si el usuario confirma
    nuevoBtn.addEventListener('click', function () {
      modal.hide();
      form.submit();
    });

    // 6. Mostramos el modal
    modal.show();
  });
});