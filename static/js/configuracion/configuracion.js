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
// ══════════════════════════════════════════
// CSRF helper
// ══════════════════════════════════════════
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}
const CSRF_TOKEN = getCookie('csrftoken') || document.querySelector('input[name=csrfmiddlewaretoken]')?.value;

// ══════════════════════════════════════════
// ESTADO VISUAL
// ══════════════════════════════════════════
const CFG_DEFAULT = {
  tema: 'oscuro', paginaInicio: 'tablero', brillo: 100, fuente: 14, zoom: 100,
  sidebarAuto: false, resumenSidebar: true,
  alertaStock: true, widgetRotacion: true, silencioso: false,
};

function cargarCfg() {
  let cfg = { ...CFG_DEFAULT };
  try {
    const g = JSON.parse(localStorage.getItem('cys_config') || '{}');
    cfg = { ...cfg, ...g };
  } catch (e) {}
  return cfg;
}
function guardarCfg(cfg) {
  localStorage.setItem('cys_config', JSON.stringify(cfg));
}

let cfgActual = cargarCfg();
let perillaBrillo, perillaFuente, perillaZoom;
let logoEmpresaFile = null;

// ══════════════════════════════════════════
// PERILLAS (DIAL)
// ══════════════════════════════════════════
function crearPerilla(container) {
  const min    = parseFloat(container.dataset.min);
  const max    = parseFloat(container.dataset.max);
  const step   = parseFloat(container.dataset.step) || 1;
  const unidad = container.dataset.unit || '';

  container.innerHTML = `
    <div class="cfg-knob__dial">
      <svg class="cfg-knob__ring" viewBox="0 0 100 100">
        <path class="cfg-knob__track" pathLength="100" d="M20,80 A38,38 0 1 1 80,80"></path>
        <path class="cfg-knob__progress" pathLength="100" d="M20,80 A38,38 0 1 1 80,80"></path>
      </svg>
      <div class="cfg-knob__handle"><span class="cfg-knob__dot"></span></div>
      <div class="cfg-knob__center">
        <span class="cfg-knob__value">0</span><span class="cfg-knob__unit">${unidad}</span>
      </div>
    </div>
    <div class="cfg-knob__minmax"><span>${min}${unidad}</span><span>${max}${unidad}</span></div>
  `;

  const dial     = container.querySelector('.cfg-knob__dial');
  const progress = container.querySelector('.cfg-knob__progress');
  const handle   = container.querySelector('.cfg-knob__handle');
  const valorEl  = container.querySelector('.cfg-knob__value');

  const MIN_ANGLE = -135;
  const MAX_ANGLE = 135;

  function pintar(val) {
    val = Math.max(min, Math.min(max, val));
    const pct = (val - min) / (max - min);
    const angulo = MIN_ANGLE + pct * (MAX_ANGLE - MIN_ANGLE);
    progress.style.strokeDasharray = `${pct * 100} 100`;
    handle.style.transform = `rotate(${angulo}deg)`;
    valorEl.textContent = val;
    container.dataset.value = val;
  }

  function anguloDesdeEvento(e) {
    const rect = dial.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const x = e.touches ? e.touches[0].clientX : e.clientX;
    const y = e.touches ? e.touches[0].clientY : e.clientY;
    let deg = Math.atan2(x - cx, -(y - cy)) * 180 / Math.PI;
    if (deg > MAX_ANGLE + 45 || deg < MIN_ANGLE - 45) {
      deg = deg > 0 ? MAX_ANGLE : MIN_ANGLE;
    }
    return Math.max(MIN_ANGLE, Math.min(MAX_ANGLE, deg));
  }

  let arrastrando = false;

  function mover(e) {
    if (!arrastrando) return;
    e.preventDefault();
    const angulo = anguloDesdeEvento(e);
    const pct = (angulo - MIN_ANGLE) / (MAX_ANGLE - MIN_ANGLE);
    let val = min + pct * (max - min);
    val = Math.round(val / step) * step;
    pintar(val);
    container.dispatchEvent(new CustomEvent('cambio', { detail: val }));
  }

  dial.addEventListener('pointerdown', (e) => {
    arrastrando = true;
    dial.setPointerCapture(e.pointerId);
    mover(e);
  });
  dial.addEventListener('pointermove', mover);
  dial.addEventListener('pointerup', () => arrastrando = false);
  dial.addEventListener('pointercancel', () => arrastrando = false);

  return { pintar };
}

// ══════════════════════════════════════════
// APLICAR EN VIVO
// ══════════════════════════════════════════
function aplicarBrillo(val) {
  document.documentElement.style.filter = val === 100 ? '' : `brightness(${val}%)`;
}
function aplicarFuente(val) {
  document.documentElement.style.fontSize = val + 'px';
}
function aplicarZoom(val) {
  document.body.style.zoom = val === 100 ? '' : (val / 100);
}

const TEMAS = {
  oscuro: {'--fondo':'#011936','--fondo-card':'#0a2240','--fondo-card2':'#0d2a4d','--texto':'#e2e8f0','--texto-muted':'#7a9bbf','--azul-claro':'#4DA8DA','--azul-borde':'rgba(77,168,218,.2)','--azul-oscuro':'#05244a','--verde':'#2ecc71','--rojo':'#c0392b','--blanco':'#e8edf2','--gris-claro':'#8899aa'},
  claro: {'--fondo':'#f0f4f8','--fondo-card':'#ffffff','--fondo-card2':'#e8eef5','--texto':'#1a2a3a','--texto-muted':'#4a6a8a','--azul-claro':'#B22A1A','--azul-borde':'rgba(178,42,26,.18)','--azul-oscuro':'#ddeaf5','--verde':'#1a8a4a','--rojo':'#B22A1A','--blanco':'#1a2a3a','--gris-claro':'#3a5a7a'},
  'alto-contraste': {'--fondo':'#000000','--fondo-card':'#0a0a0a','--fondo-card2':'#111111','--texto':'#ffffff','--texto-muted':'#cccccc','--azul-claro':'#00cfff','--azul-borde':'rgba(0,207,255,.4)','--azul-oscuro':'#001a22','--verde':'#00ff88','--rojo':'#ff4444','--blanco':'#ffffff','--gris-claro':'#aaaaaa'},
  basecys: {'--fondo':'#241008','--fondo-card':'#34160D','--fondo-card2':'#421B10','--texto':'#F2DFB8','--texto-muted':'#C9A876','--azul-claro':'#D9A441','--azul-borde':'rgba(217,164,65,.25)','--azul-oscuro':'#1A0A06','--verde':'#8AB86F','--rojo':'#B0392E','--blanco':'#F2DFB8','--gris-claro':'#B89868'},
  sepia: {'--fondo':'#1a0f05','--fondo-card':'#2c1f0e','--fondo-card2':'#3d2b14','--texto':'#f5e6c8','--texto-muted':'#a08060','--azul-claro':'#d4a060','--azul-borde':'rgba(212,160,96,.25)','--azul-oscuro':'#150c04','--verde':'#7ab870','--rojo':'#c05030','--blanco':'#f5e6c8','--gris-claro':'#907060'},
};

function aplicarTema(tema) {
  const vars = TEMAS[tema] || TEMAS.oscuro;
  Object.entries(vars).forEach(([k, v]) => document.documentElement.style.setProperty(k, v));
}

// ══════════════════════════════════════════
// INIT
// ══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', function () {
  perillaBrillo = crearPerilla(document.getElementById('knobBrillo'));
  perillaFuente = crearPerilla(document.getElementById('knobFuente'));
  perillaZoom   = crearPerilla(document.getElementById('knobZoom'));

  document.getElementById('knobBrillo').addEventListener('cambio', e => {
    cfgActual.brillo = e.detail;
    aplicarBrillo(e.detail);
    guardarCfg(cfgActual);
  });
  document.getElementById('knobFuente').addEventListener('cambio', e => {
    cfgActual.fuente = e.detail;
    aplicarFuente(e.detail);
    guardarCfg(cfgActual);
  });
  document.getElementById('knobZoom').addEventListener('cambio', e => {
    cfgActual.zoom = e.detail;
    aplicarZoom(e.detail);
    guardarCfg(cfgActual);
  });

  document.querySelectorAll('#opcionesTema .cfg-opt').forEach(el =>
    el.classList.toggle('activo', el.dataset.tema === cfgActual.tema));
  document.querySelectorAll('#opcionesInicio .cfg-opt').forEach(el =>
    el.classList.toggle('activo', el.dataset.inicio === cfgActual.paginaInicio));

  document.getElementById('toggleSidebarAuto').checked    = cfgActual.sidebarAuto;
  document.getElementById('toggleResumenSidebar').checked = cfgActual.resumenSidebar;
  document.getElementById('toggleAlertaStock').checked    = cfgActual.alertaStock;
  document.getElementById('toggleWidgetRotacion').checked = cfgActual.widgetRotacion;
  document.getElementById('toggleSilencioso').checked     = cfgActual.silencioso;

  perillaBrillo.pintar(cfgActual.brillo);
  perillaFuente.pintar(cfgActual.fuente);
  perillaZoom.pintar(cfgActual.zoom);

  const togglesMap = {
    toggleSidebarAuto:    'sidebarAuto',
    toggleResumenSidebar: 'resumenSidebar',
    toggleAlertaStock:    'alertaStock',
    toggleWidgetRotacion: 'widgetRotacion',
    toggleSilencioso:     'silencioso',
  };
  Object.entries(togglesMap).forEach(([id, key]) => {
    document.getElementById(id).addEventListener('change', function () {
      cfgActual[key] = this.checked;
      guardarCfg(cfgActual);
      window.dispatchEvent(new CustomEvent('cys-config-changed', { detail: cfgActual }));
    });
  });
});

// ══════════════════════════════════════════
// TEMA / PÁGINA DE INICIO
// ══════════════════════════════════════════
function seleccionarTema(tema, el) {
  document.querySelectorAll('#opcionesTema .cfg-opt').forEach(o => o.classList.remove('activo'));
  el.classList.add('activo');
  cfgActual.tema = tema;
  aplicarTema(tema);
  guardarCfg(cfgActual);
}

function seleccionarInicio(valor, el) {
  document.querySelectorAll('#opcionesTema .cfg-opt').forEach(o => o.classList.remove('activo'));
  el.classList.add('activo');
  cfgActual.paginaInicio = valor;
  guardarCfg(cfgActual);
  document.cookie = `cys_pagina_inicio=${valor}; path=/; max-age=31536000; SameSite=Lax`;
}

// ══════════════════════════════════════════
// ACTIVIDAD DE USUARIOS (Carga dinámica)
// ══════════════════════════════════════════
document.getElementById('modalActividad').addEventListener('show.bs.modal', function () {
  const tbody = document.getElementById('tablaActividad');
  tbody.innerHTML = '<tr><td colspan="3" class="text-center">Cargando...</td></tr>';

  // Obtenemos la URL guardada en el atributo data del body o el modal
  const urlActividad = document.getElementById('modalActividad').dataset.url;

  fetch(urlActividad)
    .then(res => res.json())
    .then(data => {
      document.getElementById('tituloActividad').textContent = data.es_admin ? 'Actividad de todos los usuarios' : 'Mi actividad';
      document.getElementById('colUsuario').style.display = data.es_admin ? '' : 'none';

      tbody.innerHTML = '';
      if (data.registros.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">Sin registros</td></tr>';
        return;
      }
      data.registros.forEach(r => {
        const fila = document.createElement('tr');
        fila.innerHTML = `
          ${data.es_admin ? `<td>${r.usuario}</td>` : ''}
          <td>${r.fecha_hora}</td>
          <td>${r.ip}</td>
        `;
        tbody.appendChild(fila);
      });
    })
    .catch(() => {
      tbody.innerHTML = '<tr><td colspan="3" class="text-center">Error al cargar la actividad</td></tr>';
    });
});

// ══════════════════════════════════════════
// LOGO EMPRESA
// ══════════════════════════════════════════
function previewLogoEmpresa(input) {
  if (!input.files || !input.files[0]) return;
  logoEmpresaFile = input.files[0];
  const reader = new FileReader();
  reader.onload = function (e) {
    document.getElementById('logoEmpresaPreview').innerHTML = `<img src="${e.target.result}" alt="Logo empresa">`;
  };
  reader.readAsDataURL(logoEmpresaFile);
}

// ══════════════════════════════════════════
// ACCIONES ASÍNCRONAS (POST a Django)
// ══════════════════════════════════════════
async function guardarInfoEmpresa() {
  const btn = document.getElementById('btnGuardarEmpresa');
  const urlEmpresa = btn.dataset.url;
  btn.disabled = true;
  
  const fd = new FormData();
  fd.append('nombre_empresa', document.getElementById('empresaNombre').value.trim());
  fd.append('nit',            document.getElementById('empresaNit').value.trim());
  fd.append('telefono',       document.getElementById('empresaTelefono').value.trim());
  fd.append('email',          document.getElementById('empresaEmail').value.trim());
  fd.append('direccion',      document.getElementById('empresaDireccion').value.trim());
  if (logoEmpresaFile) fd.append('logo', logoEmpresaFile);

  try {
    const resp = await fetch(urlEmpresa, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF_TOKEN },
      body: fd,
    });
    const data = await resp.json();
    if (data.ok) {
      mostrarToast('Información de la empresa guardada');
      logoEmpresaFile = null;
    }
  } catch (e) {} finally { btn.disabled = false; }
}

async function guardarImpuestos() {
  const btn = document.getElementById('btnGuardarImpuestos');
  const urlImpuestos = btn.dataset.url;
  btn.disabled = true;
  
  const fd = new FormData();
  fd.append('iva_porcentaje', document.getElementById('ivaPorcentaje').value);
  fd.append('moneda', document.getElementById('monedaSelect').value);
  document.getElementById('unidadesMedida').value.split(',').map(u => u.trim()).filter(Boolean).forEach(u => {
    fd.append('unidades[]', u);
  });

  try {
    const resp = await fetch(urlImpuestos, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF_TOKEN },
      body: fd,
    });
    const data = await resp.json();
    if (data.ok) mostrarToast('Impuestos guardados');
  } catch (e) {} finally { btn.disabled = false; }
}

async function generarRespaldo() {
  const btn = document.getElementById('btnBackup');
  const urlBackup = btn.dataset.url;
  btn.disabled = true;
  
  try {
    const resp = await fetch(urlBackup, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF_TOKEN },
    });
    const data = await resp.json();
    if (data.ok) {
      document.getElementById('dbUltimoRespaldo').textContent = data.fecha;
      const lista = document.getElementById('listaBackups');
      const vacio = lista.querySelector('[data-backup-empty]');
      if (vacio) vacio.remove();
      const item = document.createElement('div');
      item.className = 'cfg-backup-item';
      item.innerHTML = `<div><div class="cfg-backup-item__nombre">${data.nombre}</div><div class="cfg-backup-item__meta">${data.fecha} · ${data.tamaño}</div></div><i class="bi bi-file-earmark-zip cfg-icon-blue"></i>`;
      lista.prepend(item);
    }
  } catch (e) {} finally { btn.disabled = false; }
}

function mostrarToast(msg = 'Configuración guardada') {
  const t = document.getElementById('cfg-toast');
  t.innerHTML = `<i class="bi bi-check-circle-fill me-2"></i>${msg}`;
}
})();