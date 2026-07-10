(function () {

  const $    = id => document.getElementById(id);
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';

  function apiFetch(url, fd) {
    return fetch(url, {
      method: 'POST', body: fd,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    }).then(r => r.json());
  }

  function mkFd(extra) {
    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', csrf());
    Object.entries(extra || {}).forEach(([k, v]) => fd.append(k, v));
    return fd;
  }

  /* ══════════════════════════════════════════════
     BÚSQUEDA
  ══════════════════════════════════════════════ */
  $('inputBuscarUsuario')?.addEventListener('input', function () {
    const q    = this.value.trim().toLowerCase();
    const cols = document.querySelectorAll('#contenedor-tarjetas > div[id^="col-"]');
    let vis    = 0;
    cols.forEach(col => {
      const show = !q || ['nombre','usuario','rol'].some(k => (col.dataset[k]||'').includes(q));
      col.style.display   = show ? '' : 'none';
      col.dataset.visible = show ? '1' : '0';
      if (show) vis++;
    });
    const sr = $('sin-resultados');
    if (sr) sr.style.setProperty('display', vis === 0 ? 'block' : 'none', 'important');
    reajustarLayout();
  });

  /* ══════════════════════════════════════════════
     STATS
  ══════════════════════════════════════════════ */
  function calcularStats() {
    let activos = 0, inactivos = 0, admin = 0, cajero = 0, empleado = 0;
    document.querySelectorAll('[id^="fila-"]').forEach(card => {
      const pk = card.id.slice(5);
      const eb = $('estado-badge-' + pk);
      const rb = $('rol-badge-'    + pk);
      if (!eb || !rb) return;
      eb.classList.contains('usuario-estado--activo') ? activos++ : inactivos++;
      const r = rb.textContent.trim().toLowerCase();
      r.includes('admin') ? admin++ : r.includes('caj') ? cajero++ : empleado++;
    });
    const total = activos + inactivos;
    $('cnt-activos').textContent   = activos;
    $('cnt-inactivos').textContent = inactivos;
    $('cnt-admin').textContent     = admin;
    $('cnt-cajero').textContent    = cajero;
    $('cnt-empleado').textContent  = empleado;
    const pct = total > 0 ? Math.round(activos / total * 100) : 0;
    $('pct-activos').textContent = pct + '%';
    $('bar-activos').style.width = pct + '%';
  }

  /* ══════════════════════════════════════════════
     LAYOUT
  ══════════════════════════════════════════════ */
  function contarVisibles() {
    return document.querySelectorAll(
      '#contenedor-tarjetas > div[id^="col-"][data-visible="1"]'
    ).length;
  }

  function sincronizarAlturaRecientes() {
    const layout = $('layout-principal');
    if (!layout.classList.contains('cards-view-3-4')) return;
    const main   = $('ul-main-ref');
    const widget = document.querySelector('#wrapperRecientes .widget-recientes');
    const scroll = document.querySelector('#wrapperRecientes .ul-recientes-scroll');
    if (!main || !widget || !scroll) return;
    const mainBottom    = main.getBoundingClientRect().bottom;
    const wrapperTop    = $('wrapperRecientes').getBoundingClientRect().top;
    const titleEl       = widget.querySelector('.ul-widget__title');
    const titleH        = titleEl ? titleEl.offsetHeight + 12 : 32;
    const paddingWidget = 22;
    const disponible    = mainBottom - wrapperTop - titleH - paddingWidget * 2;
    scroll.style.maxHeight = Math.max(disponible, 120) + 'px';
  }

  function reajustarLayout() {
    const total  = contarVisibles();
    const layout = $('layout-principal');
    const cS     = $('collapseStats');
    const cR     = $('collapseRecientes');

    layout.classList.remove('cards-view-1-2','cards-view-3-4','cards-view-5-6','cards-view-dense');

    const casos = [
      [2,        'cards-view-1-2',   false, false],
      [4,        'cards-view-3-4',   true,  true ],
      [6,        'cards-view-5-6',   true,  true ],
      [Infinity, 'cards-view-dense', true,  true ],
    ];
    const [, cls, showS, showR] = casos.find(([n]) => total <= n);
    layout.classList.add(cls);
    cS?.classList[showS ? 'add' : 'remove']('show');
    cR?.classList[showR ? 'add' : 'remove']('show');
    requestAnimationFrame(() => requestAnimationFrame(sincronizarAlturaRecientes));
  }

  /* ── INIT ── */
  calcularStats();
  reajustarLayout();
  window.addEventListener('resize', () => requestAnimationFrame(sincronizarAlturaRecientes));

  /* ══════════════════════════════════════════════
     MODAL CREAR USUARIO
  ══════════════════════════════════════════════ */
  const modalCrearEl  = $('modalCrearUsuario');
  const btnAbrirCrear = $('btnAbrirModalCrear');

  /* Toggle ojo de contraseña */
  window.cuToggleOjo = function(inputId, iconId) {
    const inp  = $(inputId);
    const icon = $(iconId);
    if (!inp || !icon) return;
    const esPassword = inp.type === 'password';
    inp.type = esPassword ? 'text' : 'password';
    icon.className = esPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
  };

  /* Validador en tiempo real: coincidencia de contraseñas */
  function cuValidarMatch() {
    const c1    = $('cuClave')?.value         || '';
    const c2    = $('cuClaveConfirm')?.value  || '';
    const hint  = $('cuClaveMatch');
    const inp2  = $('cuClaveConfirm');
    if (!hint || !c2) { hint && (hint.style.display = 'none'); return; }
    const ok = c1 === c2;
    hint.style.display = 'flex';
    hint.className     = 'cu-match-hint ' + (ok ? 'cu-match-ok' : 'cu-match-err');
    hint.innerHTML     = ok
      ? '<i class="bi bi-check-circle-fill"></i> Las contraseñas coinciden'
      : '<i class="bi bi-x-circle-fill"></i> Las contraseñas no coinciden';
    inp2.classList.toggle('eu-input--invalid', !ok);
  }

  /* Limpiar campos del modal crear */
  function cuLimpiar() {
    ['cuNombre','cuApellidos','cuIdentificacion','cuEmail','cuClave','cuClaveConfirm'].forEach(id => {
      const el = $(id);
      if (el) { el.value = ''; el.classList.remove('eu-input--invalid'); }
    });
    const ti = $('cuTipoId');    if (ti) ti.value = 'CC';
    const cb = $('cuAceptaTC'); if (cb) cb.checked = false;
    const tw = $('cuTcWrap');   if (tw) tw.classList.remove('cu-tc-wrap--invalid');
    const mh = $('cuClaveMatch'); if (mh) mh.style.display = 'none';
    const msg = $('cuMsg');
    if (msg) { msg.style.display = 'none'; msg.className = 'eu-msg'; }
    // resetear iconos ojo
    ['cuEyeIconClave','cuEyeIconConfirm'].forEach(id => {
      const ic = $(id); if (ic) ic.className = 'bi bi-eye';
    });
    ['cuClave','cuClaveConfirm'].forEach(id => {
      const inp = $(id); if (inp) inp.type = 'password';
    });
  }

  if (btnAbrirCrear && modalCrearEl) {
    btnAbrirCrear.addEventListener('click', () => {
      cuLimpiar();
      new bootstrap.Modal(modalCrearEl).show();
    });

    /* Listeners dinámicos — se registran una sola vez tras primer show */
    modalCrearEl.addEventListener('shown.bs.modal', function onShown() {
      modalCrearEl.removeEventListener('shown.bs.modal', onShown);

      $('cuClaveConfirm')?.addEventListener('input', cuValidarMatch);
      $('cuClave')?.addEventListener('input', cuValidarMatch);

      /* Botón ver T&C */
      $('cuBtnVerTC')?.addEventListener('click', () => {
        const tcModal = new bootstrap.Modal($('modalTC'));
        tcModal.show();
      });

      /* Al aceptar desde el modal T&C → marcar checkbox */
      $('tcBtnAceptar')?.addEventListener('click', () => {
        const cb = $('cuAceptaTC');
        if (cb) {
          cb.checked = true;
          $('cuTcWrap')?.classList.remove('cu-tc-wrap--invalid');
        }
      });
    });
  }

  /* Guardar nuevo usuario */
  window.guardarNuevoUsuario = function() {
    const nombre    = $('cuNombre')?.value.trim()        || '';
    const apellidos = $('cuApellidos')?.value.trim()     || '';
    const tipoId    = $('cuTipoId')?.value               || 'CC';
    const idNum     = $('cuIdentificacion')?.value.trim()|| '';
    const email     = $('cuEmail')?.value.trim()         || '';
    const clave     = $('cuClave')?.value                || '';
    const confirm   = $('cuClaveConfirm')?.value         || '';
    const acepta    = $('cuAceptaTC')?.checked           || false;

    /* Validación cliente */
    let errores = false;

    function marcar(id, mal) {
      $(id)?.classList.toggle('eu-input--invalid', mal);
    }

    marcar('cuNombre',        !nombre);
    marcar('cuApellidos',     !apellidos);
    marcar('cuIdentificacion',!idNum);
    marcar('cuClave',         !clave);
    marcar('cuClaveConfirm',  !confirm || clave !== confirm);
    if (!nombre || !apellidos || !idNum || !clave) errores = true;
    if (!confirm || clave !== confirm) errores = true;

    if (!acepta) {
      $('cuTcWrap')?.classList.add('cu-tc-wrap--invalid');
      errores = true;
    } else {
      $('cuTcWrap')?.classList.remove('cu-tc-wrap--invalid');
    }

    if (errores) {
      cuMostrarMsg(
        clave !== confirm
          ? 'Las contraseñas no coinciden.'
          : !acepta
            ? 'Debes aceptar los Términos y Condiciones.'
            : 'Completa todos los campos obligatorios.',
        'err'
      );
      return;
    }

    const btn = $('cuBtnGuardar');
    btn.disabled    = true;
    btn.textContent = 'Creando…';

    apiFetch('/usuarios/crear-admin/', mkFd({
      nombre, apellidos, tipo_id: tipoId,
      identificacion: idNum, email, clave,
    })).then(d => {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-person-plus me-1"></i> Crear Usuario';
      if (d.ok) {
        cuMostrarMsg('✅ ' + (d.mensaje || 'Usuario creado correctamente.'), 'ok');
        setTimeout(() => {
          bootstrap.Modal.getInstance($('modalCrearUsuario'))?.hide();
          cuLimpiar();
          if (d.pk) agregarTarjetaAlDOM(d);
        }, 1100);
      } else {
        cuMostrarMsg(d.error || 'Error al crear el usuario.', 'err');
      }
    }).catch(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-person-plus me-1"></i> Crear Usuario';
      cuMostrarMsg('Error de conexión.', 'err');
    });
  };

  function cuMostrarMsg(texto, tipo) {
    const el = $('cuMsg');
    if (!el) return;
    el.textContent   = texto;
    el.style.display = 'block';
    el.className     = 'eu-msg ' + (tipo === 'ok' ? 'eu-msg-ok' : 'eu-msg-error');
  }

  /* ══════════════════════════════════════════════
     AGREGAR TARJETA AL DOM
  ══════════════════════════════════════════════ */
  function agregarTarjetaAlDOM(d) {
    const contenedor = $('contenedor-tarjetas');
    if (!contenedor) return;
    const hoy   = new Date();
    const fecha = hoy.toLocaleDateString('es-CO', { day:'2-digit', month:'2-digit', year:'numeric' });

    const colDiv = document.createElement('div');
    colDiv.className = 'col-12 col-md-6';
    colDiv.id = 'col-' + d.pk;
    colDiv.dataset.nombre   = (d.nombre_completo || '').toLowerCase();
    colDiv.dataset.usuario  = (d.usuario || '').toLowerCase();
    colDiv.dataset.rol      = 'empleado';
    colDiv.dataset.visible  = '1';

    colDiv.innerHTML = `
      <div id="fila-${d.pk}" class="usuario-card h-100"
           style="opacity:0;transform:scale(.95);transition:opacity .35s,transform .35s;">
        <div class="d-flex align-items-center justify-content-between mb-3">
          <div class="d-flex align-items-center gap-2">
            <div class="usuario-avatar">${(d.nombre_completo||'?')[0].toUpperCase()}</div>
            <div>
              <div class="usuario-nombre">${d.nombre_completo}</div>
              <div class="usuario-user">@${d.usuario}</div>
            </div>
          </div>
          <div class="usuario-rol-control" id="rol-control-${d.pk}">
            <span id="rol-badge-${d.pk}"
                  class="badge usuario-rol usuario-rol--empleado usuario-rol--clickable"
                  onclick="abrirSelectorRol(${d.pk}, 'empleado')"
                  title="Cambiar rol">
              Empleado <i class="bi bi-pencil-fill usuario-rol__edit-icon"></i>
            </span>
            <div id="rol-selector-${d.pk}" class="usuario-rol-selector hidden-display">
              <select id="rol-select-${d.pk}" class="usuario-rol-select">
                <option value="cajero">Cajero</option>
                <option value="empleado" selected>Empleado</option>
              </select>
              <button class="usuario-rol-btn usuario-rol-btn--ok"
                      onclick="guardarRol(${d.pk})" title="Guardar rol">
                <i class="bi bi-check-lg"></i>
              </button>
              <button class="usuario-rol-btn usuario-rol-btn--cancel"
                      onclick="cancelarRol(${d.pk})" title="Cancelar">
                <i class="bi bi-x-lg"></i>
              </button>
            </div>
          </div>
        </div>
        <hr class="usuario-divider">
        <div class="row g-2 mb-3 usuario-datos">
          <div class="col-6">
            <div class="usuario-label">Identificación</div>
            <div class="usuario-value">${d.identificacion}</div>
            <div class="usuario-sub">${d.tipo_id_display || ''}</div>
          </div>
          <div class="col-6">
            <div class="usuario-label">Correo</div>
            <div class="usuario-email">${d.email || '—'}</div>
          </div>
          <div class="col-6">
            <div class="usuario-label">Miembro desde</div>
            <div class="usuario-muted">${fecha}</div>
          </div>
          <div class="col-6">
            <div class="usuario-label">Estado</div>
            <span id="estado-badge-${d.pk}" class="usuario-estado usuario-estado--activo">
              <span class="usuario-dot"></span> Activo
            </span>
          </div>
        </div>
        <div class="d-flex gap-2">
          <button onclick="abrirEditar(${d.pk})"
                  class="btn btn-sm flex-fill usuario-btn usuario-btn-editar">
            <i class="bi bi-pencil me-1"></i> Editar
          </button>
          <div id="wrap-toggle-${d.pk}" class="flex-fill d-flex flex-column gap-1">
            <button id="btn-toggle-${d.pk}"
                    onclick="toggleActivo(${d.pk}, true)"
                    class="btn btn-sm w-100 usuario-btn usuario-btn-desactivar">
              <i class="bi bi-person-dash me-1"></i> Desactivar
            </button>
            <button id="btn-eliminar-${d.pk}"
                    onclick="eliminarUsuario(${d.pk})"
                    class="btn btn-sm w-100 usuario-btn usuario-btn-eliminar hidden-display">
              <i class="bi bi-trash3 me-1"></i> Eliminar
            </button>
          </div>
        </div>
      </div>`;

    contenedor.appendChild(colDiv);
    requestAnimationFrame(() => {
      const card = colDiv.querySelector('.usuario-card');
      card.style.opacity   = '1';
      card.style.transform = 'scale(1)';
    });

    const recientesScroll = $('recientes-scroll');
    if (recientesScroll) {
      const item = document.createElement('div');
      item.className = 'ul-activity-item';
      item.id = 'reciente-' + d.pk;
      item.innerHTML = `
        <div class="ul-activity-avatar">${(d.nombre_completo||'?')[0].toUpperCase()}</div>
        <div class="ul-activity-body">
          <div class="ul-activity-name">${d.nombre_completo}</div>
          <div class="ul-activity-meta">Empleado</div>
        </div>
        <div class="ul-activity-time">${fecha}</div>`;
      recientesScroll.insertBefore(item, recientesScroll.firstChild);
    }

    const totalEl = $('total-usuarios-num');
    if (totalEl) totalEl.textContent = parseInt(totalEl.textContent || '0') + 1;

    calcularStats();
    reajustarLayout();
  }

  /* ══════════════════════════════════════════════
     MODAL EDITAR USUARIO
  ══════════════════════════════════════════════ */
  window.euMostrarMsg = (texto, tipo) => {
    const el = $('euMsg');
    el.textContent   = texto;
    el.style.display = 'block';
    el.className     = 'eu-msg ' + (tipo === 'ok' ? 'eu-msg-ok' : 'eu-msg-error');
  };

  window.abrirEditar = pk =>
    fetch(`/usuarios/editar/${pk}/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(r => r.json())
    .then(d => {
      if (!d.ok) return;
      ['Pk','Nombre','Apellidos','Email','Rol'].forEach(f =>
        $('eu' + f).value = d[f.toLowerCase()] ?? ''
      );
      $('euClaveNueva').value = '';
      $('euNombreHeader').textContent = '@' + d.usuario;
      $('euMsg').style.display = 'none';
      new bootstrap.Modal($('modalEditarUsuario')).show();
    });

  window.guardarEditar = () => {
    const pk  = $('euPk').value;
    const btn = $('euBtnGuardar');
    btn.disabled = true;
    btn.textContent = 'Guardando…';
    apiFetch(`/usuarios/editar/${pk}/`, mkFd({
      nombre:      $('euNombre').value.trim(),
      apellidos:   $('euApellidos').value.trim(),
      email:       $('euEmail').value.trim(),
      rol:         $('euRol').value,
      clave_nueva: $('euClaveNueva').value,
    })).then(d => {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Guardar Cambios';
      d.ok ? (euMostrarMsg('✅ ' + d.mensaje, 'ok'), setTimeout(() => location.reload(), 1200))
           : euMostrarMsg(d.error, 'err');
    }).catch(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Guardar Cambios';
      euMostrarMsg('Error de conexión.', 'err');
    });
  };

  /* ══════════════════════════════════════════════
     SELECTOR DE ROL INLINE
  ══════════════════════════════════════════════ */
  const ROL_LABELS = { cajero: 'Cajero', empleado: 'Empleado' };
  const ROL_CLASES = {
    cajero:   'usuario-rol--cajero',
    empleado: 'usuario-rol--empleado',
  };

  window.abrirSelectorRol = (pk, rolActual) => {
    document.querySelectorAll('.usuario-rol-selector').forEach(s => {
      if (s.id !== 'rol-selector-' + pk) s.style.display = 'none';
    });
    document.querySelectorAll('.usuario-rol--clickable').forEach(b => {
      if (b.id !== 'rol-badge-' + pk) b.style.display = '';
    });
    $('rol-badge-'    + pk).style.display = 'none';
    $('rol-selector-' + pk).style.display = 'flex';
    $('rol-select-'   + pk).value = rolActual;
    $('rol-select-'   + pk).focus();
  };

  window.cancelarRol = pk => {
    $('rol-selector-' + pk).style.display = 'none';
    $('rol-badge-'    + pk).style.display = '';
  };

  window.guardarRol = pk => {
    const nuevoRol = $('rol-select-' + pk).value;
    const btnOk    = document.querySelector(`#rol-selector-${pk} .usuario-rol-btn--ok`);
    btnOk.disabled = true;
    btnOk.innerHTML = '<span class="spinner-border spinner-border-sm" style="width:.75rem;height:.75rem;border-width:2px;"></span>';

    fetch(`/usuarios/editar/${pk}/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(r => r.json())
    .then(d => {
      if (!d.ok) throw new Error('No se pudieron obtener datos del usuario.');
      return apiFetch(`/usuarios/editar/${pk}/`, mkFd({
        nombre:      d.nombre,
        apellidos:   d.apellidos,
        email:       d.email,
        rol:         nuevoRol,
        clave_nueva: '',
      }));
    })
    .then(d => {
      btnOk.disabled = false;
      btnOk.innerHTML = '<i class="bi bi-check-lg"></i>';
      if (!d.ok) {
        const badge = $('rol-badge-' + pk);
        const prev  = badge.innerHTML;
        badge.style.display = '';
        $('rol-selector-' + pk).style.display = 'none';
        badge.innerHTML = `⚠ ${d.error || 'Error'}`;
        setTimeout(() => { badge.innerHTML = prev; }, 2500);
        return;
      }
      const badge = $('rol-badge-' + pk);
      badge.className = `badge usuario-rol ${ROL_CLASES[nuevoRol]} usuario-rol--clickable`;
      badge.innerHTML = `${ROL_LABELS[nuevoRol]} <i class="bi bi-pencil-fill usuario-rol__edit-icon"></i>`;
      badge.onclick   = () => abrirSelectorRol(pk, nuevoRol);
      $('rol-selector-' + pk).style.display = 'none';
      badge.style.display = '';
      const col = $('col-' + pk);
      if (col) col.dataset.rol = ROL_LABELS[nuevoRol].toLowerCase();
      calcularStats();
    })
    .catch(() => {
      btnOk.disabled = false;
      btnOk.innerHTML = '<i class="bi bi-check-lg"></i>';
      cancelarRol(pk);
    });
  };

  /* ══════════════════════════════════════════════
     TOGGLE ACTIVO
  ══════════════════════════════════════════════ */
  window.toggleActivo = (pk, activo) =>
    apiFetch(`/usuarios/toggle/${pk}/`, mkFd()).then(d => {
      if (!d.ok) return;
      const badge = $('estado-badge-' + pk);
      const btnT  = $('btn-toggle-'   + pk);
      const btnE  = $('btn-eliminar-' + pk);
      if (d.activo) {
        badge.className = 'usuario-estado usuario-estado--activo';
        badge.innerHTML = '<span class="usuario-dot"></span> Activo';
        btnT.className  = btnT.className.replace('usuario-btn-activar','usuario-btn-desactivar');
        btnT.innerHTML  = '<i class="bi bi-person-dash me-1"></i> Desactivar';
        btnT.onclick    = () => toggleActivo(pk, true);
        btnE.style.display = 'none';
      } else {
        badge.className = 'usuario-estado usuario-estado--inactivo';
        badge.innerHTML = '<span class="usuario-dot"></span> Inactivo';
        btnT.className  = btnT.className.replace('usuario-btn-desactivar','usuario-btn-activar');
        btnT.innerHTML  = '<i class="bi bi-person-check me-1"></i> Activar';
        btnT.onclick    = () => toggleActivo(pk, false);
        btnE.style.display = 'block';
      }
      calcularStats();
    });

  /* ══════════════════════════════════════════════
     ELIMINAR USUARIO
  ══════════════════════════════════════════════ */
  window.eliminarUsuario = pk => {
    if (!confirm('¿Eliminar este usuario? Esta acción no se puede deshacer.')) return;
    apiFetch(`/usuarios/eliminar/${pk}/`, mkFd()).then(d => {
      if (!d.ok) return;
      const card = $('fila-' + pk);
      if (card) {
        card.classList.add('usuario-card--removing');
        setTimeout(() => {
          $('col-' + pk)?.remove();
          $('reciente-' + pk)?.remove();
          const totalEl = $('total-usuarios-num');
          if (totalEl) totalEl.textContent = Math.max(0, parseInt(totalEl.textContent) - 1);
          calcularStats();
          reajustarLayout();
        }, 380);
      }
    });
  };

})();
