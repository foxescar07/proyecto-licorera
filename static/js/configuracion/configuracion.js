// ══════════════════════════════════════════
// URLs de Django (pasadas desde el template vía data-attributes)
// ══════════════════════════════════════════
const cfgData = document.getElementById('cfg-data');
const URL_ACTIVIDAD          = cfgData.dataset.urlActividad;
const URL_GUARDAR_EMPRESA    = cfgData.dataset.urlGuardarEmpresa;
const URL_GUARDAR_IMPUESTOS  = cfgData.dataset.urlGuardarImpuestos;
const URL_CREAR_BACKUP       = cfgData.dataset.urlCrearBackup;

// ══════════════════════════════════════════
// CSRF helper
// ══════════════════════════════════════════
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}
const CSRF_TOKEN = getCookie('csrftoken') ||
  document.querySelector('input[name=csrfmiddlewaretoken]')?.value;

// ══════════════════════════════════════════
// ESTADO VISUAL (tema/pagina de inicio/brillo/fuente/zoom/toggles)
// mismo objeto que ya lee/aplica base.html y aside.html: localStorage.cys_config
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
let logoEmpresaFile = null; // archivo seleccionado, pendiente de subir al guardar
let toastPrefTimeout = null;

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
// El tema ya NO se define aquí: se reutiliza window.aplicarTemaCYS,
// expuesto por base.js, para que los 5 temas nunca se desincronicen
// entre archivos (fuente única de verdad).
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
function aplicarTema(tema) {
  if (window.aplicarTemaCYS) {
    window.aplicarTemaCYS(tema);
  }
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
    mostrarToastPreferencia();
  });
  document.getElementById('knobFuente').addEventListener('cambio', e => {
    cfgActual.fuente = e.detail;
    aplicarFuente(e.detail);
    guardarCfg(cfgActual);
    mostrarToastPreferencia();
  });
  document.getElementById('knobZoom').addEventListener('cambio', e => {
    cfgActual.zoom = e.detail;
    aplicarZoom(e.detail);
    guardarCfg(cfgActual);
    mostrarToastPreferencia();
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

  // ── Autoguardado de toggles (barra lateral, alertas) ──
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
      mostrarToastPreferencia();
    });
  });

  // ── Modal de actividad de usuarios ──
  document.getElementById('modalActividad').addEventListener('show.bs.modal', function () {
    const tbody = document.getElementById('tablaActividad');
    tbody.innerHTML = '<tr><td colspan="3" class="text-center">Cargando...</td></tr>';

    fetch(URL_ACTIVIDAD)
      .then(res => res.json())
      .then(data => {
        document.getElementById('tituloActividad').textContent =
          data.es_admin ? 'Actividad de todos los usuarios' : 'Mi actividad';
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
});

// ══════════════════════════════════════════
// TEMA / PÁGINA DE INICIO — se aplican y guardan al instante
// ══════════════════════════════════════════
function seleccionarTema(tema, el) {
  document.querySelectorAll('#opcionesTema .cfg-opt').forEach(o => o.classList.remove('activo'));
  el.classList.add('activo');
  cfgActual.tema = tema;
  aplicarTema(tema);
  guardarCfg(cfgActual);
  mostrarToastPreferencia();
}
function seleccionarInicio(valor, el) {
  document.querySelectorAll('#opcionesInicio .cfg-opt').forEach(o => o.classList.remove('activo'));
  el.classList.add('activo');
  cfgActual.paginaInicio = valor;
  guardarCfg(cfgActual);
  document.cookie = `cys_pagina_inicio=${valor}; path=/; max-age=31536000; SameSite=Lax`;
  mostrarToastPreferencia();
}

// ══════════════════════════════════════════
// LOGO EMPRESA — preview local, se sube junto con "Guardar"
// ══════════════════════════════════════════
function previewLogoEmpresa(input) {
  if (!input.files || !input.files[0]) return;
  logoEmpresaFile = input.files[0];
  const reader = new FileReader();
  reader.onload = function (e) {
    document.getElementById('logoEmpresaPreview').innerHTML =
      `<img src="${e.target.result}" alt="Logo empresa">`;
  };
  reader.readAsDataURL(logoEmpresaFile);
}

// ══════════════════════════════════════════
// EMPRESA — POST real a configuracion:guardar_empresa (incluye logo si se cambió)
// ══════════════════════════════════════════
async function guardarInfoEmpresa() {
  const btn = document.getElementById('btnGuardarEmpresa');
  btn.disabled = true;

  const fd = new FormData();
  fd.append('nombre_empresa', document.getElementById('empresaNombre').value.trim());
  fd.append('nit',            document.getElementById('empresaNit').value.trim());
  fd.append('telefono',       document.getElementById('empresaTelefono').value.trim());
  fd.append('email',          document.getElementById('empresaEmail').value.trim());
  fd.append('direccion',      document.getElementById('empresaDireccion').value.trim());
  if (logoEmpresaFile) {
    fd.append('logo', logoEmpresaFile);
  }

  try {
    const resp = await fetch(URL_GUARDAR_EMPRESA, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF_TOKEN },
      body: fd,
    });
    const data = await resp.json();
    if (data.ok) {
      mostrarToast('Información de la empresa guardada');
      logoEmpresaFile = null;
    } else {
      mostrarToast(data.error || 'No se pudo guardar', 'error');
    }
  } catch (e) {
    mostrarToast('Error de conexión con el servidor', 'error');
  } finally {
    btn.disabled = false;
  }
}

// ══════════════════════════════════════════
// IMPUESTOS — POST real a configuracion:guardar_impuestos
// ══════════════════════════════════════════
async function guardarImpuestos() {
  const btn = document.getElementById('btnGuardarImpuestos');
  btn.disabled = true;

  const fd = new FormData();
  fd.append('iva_porcentaje', document.getElementById('ivaPorcentaje').value);
  fd.append('moneda', document.getElementById('monedaSelect').value);

  const unidadesRaw = document.getElementById('unidadesMedida').value;
  unidadesRaw.split(',').map(u => u.trim()).filter(Boolean).forEach(u => {
    fd.append('unidades[]', u);
  });

  try {
    const resp = await fetch(URL_GUARDAR_IMPUESTOS, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF_TOKEN },
      body: fd,
    });
    const data = await resp.json();
    if (data.ok) {
      mostrarToast('Impuestos guardados');
    } else {
      mostrarToast(data.error || 'No se pudo guardar', 'error');
    }
  } catch (e) {
    mostrarToast('Error de conexión con el servidor', 'error');
  } finally {
    btn.disabled = false;
  }
}

// ══════════════════════════════════════════
// BACKUP — POST real a configuracion:crear_backup
// ══════════════════════════════════════════
async function generarRespaldo() {
  const btn = document.getElementById('btnBackup');
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Generando...';

  try {
    const resp = await fetch(URL_CREAR_BACKUP, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF_TOKEN },
    });
    const data = await resp.json();

    if (data.ok) {
      document.getElementById('dbUltimoRespaldo').textContent = data.fecha;
      mostrarToast('Respaldo generado: ' + data.nombre);

      const lista = document.getElementById('listaBackups');
      const vacio = lista.querySelector('[data-backup-empty]');
      if (vacio) vacio.remove();

      const item = document.createElement('div');
      item.className = 'cfg-backup-item';
      item.innerHTML = `
        <div>
          <div class="cfg-backup-item__nombre">${data.nombre}</div>
          <div class="cfg-backup-item__meta">${data.fecha} · ${data.tamaño}</div>
        </div>
        <i class="bi bi-file-earmark-zip" style="color:var(--azul-claro);"></i>
      `;
      lista.prepend(item);
    } else {
      mostrarToast(data.error || 'No se pudo generar el respaldo', 'error');
    }
  } catch (e) {
    mostrarToast('Error de conexión con el servidor', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-cloud-arrow-down me-1"></i> Generar respaldo';
  }
}

// ══════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════
function mostrarToast(msg = 'Configuración guardada', tipo = 'ok') {
  const t = document.getElementById('cfg-toast');
  t.innerHTML = `<i class="bi bi-check-circle-fill me-2"></i>${msg}`;
  if (tipo === 'error') {
    t.style.background  = 'rgba(192,57,43,.15)';
    t.style.borderColor = 'rgba(192,57,43,.4)';
    t.style.color       = '#e87070';
  } else if (tipo === 'info') {
    t.style.background  = 'rgba(77,168,218,.15)';
    t.style.borderColor = 'rgba(77,168,218,.4)';
    t.style.color       = '#4DA8DA';
  } else {
    t.style.background  = 'rgba(39,174,96,.15)';
    t.style.borderColor = 'rgba(39,174,96,.4)';
    t.style.color       = '#2ecc71';
  }
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 2800);
}

// Toast corto y silencioso para autoguardado de preferencias (evita spam si se togglean varias seguidas)
function mostrarToastPreferencia() {
  clearTimeout(toastPrefTimeout);
  toastPrefTimeout = setTimeout(() => {
    mostrarToast('Preferencia guardada', 'info');
  }, 250);
}