// ══════════════════════════════════════════════
// CONFIGURACIÓN — JS
// ══════════════════════════════════════════════
(function () {

  // ────────────────────────────────────────────
  // NAVEGACIÓN ENTRE SECCIONES (scroll + resaltado)
  // ────────────────────────────────────────────
  const navLinks = document.querySelectorAll('.cys-cfg-secnav__link');
  const sections = document.querySelectorAll('.cys-cfg-section');

  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const target = document.getElementById(link.dataset.section);
      target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  if ('IntersectionObserver' in window && sections.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        navLinks.forEach(l => l.classList.remove('is-active'));
        const activeLink = document.querySelector(
          `.cys-cfg-secnav__link[data-section="${entry.target.id}"]`
        );
        activeLink?.classList.add('is-active');
      });
    }, { rootMargin: '-20% 0px -70% 0px', threshold: 0 });

    sections.forEach(section => observer.observe(section));
  }

  // ────────────────────────────────────────────
  // TEMA DE COLOR
  // ────────────────────────────────────────────
  const THEME_KEY = 'cys-theme';
  const swatches = document.querySelectorAll('.cys-theme-swatch');

  function aplicarTema(nombre) {
    document.documentElement.setAttribute('data-theme', nombre);
    swatches.forEach(s => s.classList.toggle('is-active', s.dataset.theme === nombre));
    localStorage.setItem(THEME_KEY, nombre);
    // TODO: persistir el tema elegido en el backend (fetch/POST)
    // para que se mantenga igual aunque el usuario entre desde otro dispositivo
  }

  swatches.forEach(swatch => {
    swatch.addEventListener('click', () => aplicarTema(swatch.dataset.theme));
  });

  // Aplicar el tema guardado (o el azul por defecto) al cargar
  aplicarTema(localStorage.getItem(THEME_KEY) || 'azul');

  // ────────────────────────────────────────────
  // LOGO DE LA EMPRESA — dropzone
  // ────────────────────────────────────────────
  const dropzone = document.getElementById('logoDropzone');
  const logoInput = document.getElementById('logoInput');
  const emptyState = document.getElementById('logoEmptyState');
  const preview = document.getElementById('logoPreview');
  const previewImg = document.getElementById('logoPreviewImg');
  const removeBtn = document.getElementById('logoRemoveBtn');
  const errorEl = document.getElementById('logoError');

  const MAX_SIZE = 2 * 1024 * 1024; // 2MB
  const TIPOS_VALIDOS = ['image/png', 'image/jpeg'];

  function mostrarError(msg) {
    errorEl.textContent = msg;
    errorEl.hidden = false;
  }

  function limpiarError() {
    errorEl.hidden = true;
    errorEl.textContent = '';
  }

  function mostrarLogo(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      emptyState.hidden = true;
      preview.hidden = false;
    };
    reader.readAsDataURL(file);
    // TODO: subir el archivo al backend (fetch/POST con FormData)
  }

  function manejarArchivo(file) {
    limpiarError();
    if (!file) return;

    if (!TIPOS_VALIDOS.includes(file.type)) {
      mostrarError('Solo se aceptan archivos PNG o JPG.');
      return;
    }
    if (file.size > MAX_SIZE) {
      mostrarError('El archivo supera el tamaño máximo de 2MB.');
      return;
    }
    mostrarLogo(file);
  }

  dropzone?.addEventListener('click', () => logoInput.click());

  logoInput?.addEventListener('change', () => {
    manejarArchivo(logoInput.files[0]);
  });

  ['dragenter', 'dragover'].forEach(evento => {
    dropzone?.addEventListener(evento, (e) => {
      e.preventDefault();
      dropzone.classList.add('is-dragover');
    });
  });

  ['dragleave', 'drop'].forEach(evento => {
    dropzone?.addEventListener(evento, (e) => {
      e.preventDefault();
      dropzone.classList.remove('is-dragover');
    });
  });

  dropzone?.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files[0];
    manejarArchivo(file);
  });

  removeBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    logoInput.value = '';
    previewImg.src = '';
    preview.hidden = true;
    emptyState.hidden = false;
    limpiarError();
    // TODO: eliminar el logo en el backend (fetch/DELETE)
  });

  // ────────────────────────────────────────────
  // UNIDADES DE MEDIDA — agregar / quitar tags
  // ────────────────────────────────────────────
  const tagsWrap = document.getElementById('unidadesTags');
  const nuevaUnidadInput = document.getElementById('nuevaUnidadInput');
  const addUnidadBtn = document.getElementById('addUnidadBtn');

  function crearTag(nombre) {
    const tag = document.createElement('span');
    tag.className = 'cys-tag';
    tag.textContent = nombre + ' ';

    const btnRemove = document.createElement('button');
    btnRemove.type = 'button';
    btnRemove.className = 'cys-tag__remove';
    btnRemove.setAttribute('aria-label', 'Quitar');
    btnRemove.innerHTML = '<i class="bi bi-x"></i>';

    tag.appendChild(btnRemove);
    return tag;
  }

  function agregarUnidad() {
    const nombre = nuevaUnidadInput.value.trim();
    if (!nombre) return;

    const existentes = Array.from(tagsWrap.querySelectorAll('.cys-tag'))
      .map(t => t.firstChild.textContent.trim().toLowerCase());

    if (existentes.includes(nombre.toLowerCase())) {
      nuevaUnidadInput.value = '';
      nuevaUnidadInput.focus();
      return;
    }

    tagsWrap.appendChild(crearTag(nombre));
    nuevaUnidadInput.value = '';
    nuevaUnidadInput.focus();
    // TODO: persistir la nueva unidad en el backend (fetch/POST)
  }

  addUnidadBtn?.addEventListener('click', agregarUnidad);

  nuevaUnidadInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      agregarUnidad();
    }
  });

  tagsWrap?.addEventListener('click', (e) => {
    const btn = e.target.closest('.cys-tag__remove');
    if (!btn) return;
    btn.closest('.cys-tag')?.remove();
    // TODO: eliminar la unidad en el backend (fetch/DELETE)
  });

  // ────────────────────────────────────────────
  // BASE DE DATOS — placeholders
  // ────────────────────────────────────────────
  document.querySelector('.cys-cfg-backup-create')?.addEventListener('click', () => {
    // TODO: conectar con el endpoint real de generación de respaldo
    console.log('Generar nueva copia de seguridad — pendiente de backend');
  });

  document.querySelectorAll('.cys-cfg-history__action').forEach(btn => {
    btn.addEventListener('click', () => {
      // TODO: conectar con el endpoint real de descarga
      console.log('Descargar copia — pendiente de backend');
    });
  });

})();