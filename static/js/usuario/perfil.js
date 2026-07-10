(function () {
  const EDITAR_URL = window.EDITAR_URL || '';
  const FOTO_URL   = window.FOTO_URL || '';

  const csrf = () => document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] ?? '';

  /* ── TOAST BOOTSTRAP ── */
  const toastEl   = document.getElementById('fotoToast');
  const toastBody = document.getElementById('fotoToastBody');
  const bsToast   = new bootstrap.Toast(toastEl, { delay: 3200 });
  const showToast = (txt, tipo) => {
    toastBody.textContent = txt;
    toastEl.className = `toast align-items-center border-0 text-bg-${tipo === 'ok' ? 'success' : 'danger'}`;
    bsToast.show();
  };

  /* ── HELPERS ── */
  const $         = id => document.getElementById(id);
  const showErr   = (spanId, divId, txt) => { $(spanId).textContent = txt; $(divId).style.display = 'flex'; };
  const hideErr   = id => $(id).style.display = 'none';
  const showAlert = (id, txt, tipo) => {
    const el = $(id);
    el.className   = `cys-modal-alert mb-3 cys-modal-alert--${tipo === 'ok' ? 'ok' : 'err'}`;
    el.textContent = txt; el.style.display = 'block';
  };
  const postAjax  = (url, fd, onOk, onErr) => {
    fd.append('csrfmiddlewaretoken', csrf());
    fetch(url, { method:'POST', body:fd, headers:{'X-Requested-With':'XMLHttpRequest'} })
      .then(r => r.json())
      .then(d => d.ok ? onOk(d) : onErr(d.error || 'Error desconocido.'))
      .catch(() => onErr('Error de conexión.'));
  };
  const modalChain = (hideEl, showEl) => {
    const m = bootstrap.Modal.getInstance(hideEl) || new bootstrap.Modal(hideEl);
    m.hide();
    hideEl.addEventListener('hidden.bs.modal', () => new bootstrap.Modal(showEl).show(), { once: true });
  };

  /* ── ACTUALIZAR TODOS LOS AVATARES ── */
  function sincronizarAvatares(src) {
    $('modalAvatarPreview').innerHTML = `<img src="${src}" style="width:100%;height:100%;object-fit:cover;display:block;" alt="">`;
    const btn = $('avatarBtn');
    btn.classList.add('cys-perfil-avatar--foto');
    btn.innerHTML = `<img id="fotoPreview" src="${src}" alt="Foto"
      style="width:100%;height:100%;object-fit:cover;border-radius:50%;display:block;">
      <div class="cys-perfil-avatar__overlay"><i class="bi bi-camera-fill"></i></div>`;
    const editarAvatar = $('modalEditarAvatar');
    if (editarAvatar) editarAvatar.innerHTML = `<img src="${src}"
      style="width:100%;height:100%;object-fit:cover;border-radius:50%;display:block;" alt="">`;
    const sbAvatar = document.querySelector('.cys-sb-avatar');
    if (sbAvatar) {
      sbAvatar.innerHTML = `<img src="${src}"
        style="width:100%;height:100%;object-fit:cover;border-radius:50%;display:block;" alt="">`;
      sbAvatar.style.padding = '0';
      sbAvatar.style.overflow = 'hidden';
    }
  }

  function restaurarAvatares() {
    $('modalAvatarPreview').innerHTML = `<i class="bi bi-person-fill" style="font-size:3rem;color:var(--azul-claro);"></i>`;
    const btn = $('avatarBtn');
    btn.classList.remove('cys-perfil-avatar--foto');
    btn.innerHTML = `<i class="bi bi-person-fill cys-perfil-avatar__icon"></i>`;
    const editarAvatar = $('modalEditarAvatar');
    if (editarAvatar) editarAvatar.innerHTML = `<i class="bi bi-person-fill cys-modal-avatar__icon"></i>`;
    const sbAvatar = document.querySelector('.cys-sb-avatar');
    if (sbAvatar) {
      sbAvatar.innerHTML = `<i class="bi bi-person-fill cys-sb-avatar__icon"></i>`;
      sbAvatar.style.padding = '';
      sbAvatar.style.overflow = '';
    }
  }

  /* ── OJO CONTRASEÑA ── */
  document.addEventListener('click', e => {
    const btn = e.target.closest('[data-toggle-target]');
    if (!btn) return;
    const field = $(btn.dataset.toggleTarget), icon = btn.querySelector('i');
    if (!field || !icon) return;
    const isPwd = field.type === 'password';
    field.type = isPwd ? 'text' : 'password';
    icon.classList.toggle('bi-eye',      !isPwd);
    icon.classList.toggle('bi-eye-slash', isPwd);
  });

  /* ── FOTO PERFIL ── */
  const inputFoto      = $('inputFoto');
  const btnModalSubir  = $('btnModalSubirFoto');
  const btnModalQuitar = $('btnModalQuitarFoto');

  btnModalSubir.addEventListener('click', () => inputFoto.click());

  inputFoto.addEventListener('change', function () {
    if (!this.files.length) return;
    const file = this.files[0];
    const reader = new FileReader();
    reader.onload = e => {
      sincronizarAvatares(e.target.result);
      btnModalSubir.disabled = true;
      btnModalSubir.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Subiendo…';
      const fd = new FormData(); fd.append('foto', file);
      postAjax(FOTO_URL, fd,
        () => {
          btnModalSubir.disabled = false;
          btnModalSubir.innerHTML = '<i class="bi bi-upload me-2"></i> Subir nueva foto';
          btnModalQuitar.disabled = false;
          showAlert('msgModalFoto', '✅ Foto actualizada.', 'ok');
          showToast('✅ Foto actualizada.', 'ok');
        },
        err => {
          btnModalSubir.disabled = false;
          btnModalSubir.innerHTML = '<i class="bi bi-upload me-2"></i> Subir nueva foto';
          showAlert('msgModalFoto', err, 'err');
        }
      );
    };
    reader.readAsDataURL(file);
    this.value = '';
  });

  btnModalQuitar.addEventListener('click', function () {
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Eliminando…';
    const fd = new FormData(); fd.append('quitar', '1');
    postAjax(FOTO_URL, fd,
      () => {
        this.innerHTML = '<i class="bi bi-trash3 me-1"></i> Quitar foto actual';
        this.disabled  = true;
        restaurarAvatares();
        showAlert('msgModalFoto', '✅ Foto eliminada.', 'ok');
        showToast('✅ Foto eliminada.', 'ok');
      },
      err => {
        this.disabled = false;
        this.innerHTML = '<i class="bi bi-trash3 me-1"></i> Quitar foto actual';
        showAlert('msgModalFoto', err, 'err');
      }
    );
  });

  $('modalFoto').addEventListener('show.bs.modal', () => {
    $('msgModalFoto').style.display = 'none';
  });

  /* ── EDITAR INFO ── */
  $('btnGuardarInfo')?.addEventListener('click', function () {
    const nombre = $('epNombre').value.trim(), apellidos = $('epApellidos').value.trim(),
          email  = $('epEmail').value.trim(),  telefono  = $('epTelefono').value.trim();
    if (!nombre || !apellidos || !email) { showAlert('msgEditarInfo', 'Nombre, apellidos y correo son obligatorios.', 'err'); return; }
    this.disabled = true; this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando…';
    const fd = new FormData();
    fd.append('accion','info'); fd.append('nombre',nombre); fd.append('apellidos',apellidos);
    fd.append('email',email); fd.append('telefono',telefono);
    postAjax(EDITAR_URL, fd,
      () => { showAlert('msgEditarInfo','✅ Perfil actualizado.','ok'); setTimeout(() => location.reload(), 1400); },
      err => { this.disabled=false; this.innerHTML='<i class="bi bi-check-lg"></i> Guardar Cambios'; showAlert('msgEditarInfo',err,'err'); }
    );
  });

  /* ── CAMBIAR USUARIO ── */
  const elUsuP1 = $('modalUsuarioPaso1'), elUsuP2 = $('modalUsuarioPaso2');
  $('btnAbrirCambioUsuario')?.addEventListener('click', () => { $('usuP1Clave').value=''; hideErr('errUsuP1'); new bootstrap.Modal(elUsuP1).show(); });
  elUsuP1?.addEventListener('hidden.bs.modal', () => { $('usuP1Clave').value=''; hideErr('errUsuP1'); });
  $('btnUsuP1Siguiente')?.addEventListener('click', function () {
    const clave = $('usuP1Clave').value;
    if (!clave) { showErr('errUsuP1Txt','errUsuP1','Ingresa tu contraseña actual.'); return; }
    hideErr('errUsuP1'); this.disabled=true; this.innerHTML='<span class="spinner-border spinner-border-sm"></span>';
    const fd = new FormData(); fd.append('accion','verificar_clave'); fd.append('clave_actual',clave);
    postAjax(EDITAR_URL, fd,
      () => { this.disabled=false; this.innerHTML='Siguiente <i class="bi bi-arrow-right ms-1"></i>'; $('usuP2Nuevo').value=''; hideErr('errUsuP2'); modalChain(elUsuP1,elUsuP2); },
      err => { this.disabled=false; this.innerHTML='Siguiente <i class="bi bi-arrow-right ms-1"></i>'; showErr('errUsuP1Txt','errUsuP1',err); }
    );
  });
  $('btnUsuP2Volver')?.addEventListener('click', () => modalChain(elUsuP2, elUsuP1));
  $('btnUsuP2Guardar')?.addEventListener('click', function () {
    const nuevo = $('usuP2Nuevo').value.trim();
    if (!nuevo) { showErr('errUsuP2Txt','errUsuP2','Escribe el nuevo nombre de usuario.'); return; }
    if (!/^[a-zA-Z0-9_]{3,30}$/.test(nuevo)) { showErr('errUsuP2Txt','errUsuP2','Solo letras, números y _ (3–30 caracteres).'); return; }
    hideErr('errUsuP2'); this.disabled=true; this.innerHTML='<span class="spinner-border spinner-border-sm"></span>';
    const fd = new FormData(); fd.append('accion','cambiar_usuario'); fd.append('usuario',nuevo);
    postAjax(EDITAR_URL, fd, () => location.reload(),
      err => { this.disabled=false; this.innerHTML='<i class="bi bi-check-lg me-1"></i> Confirmar'; showErr('errUsuP2Txt','errUsuP2',err); }
    );
  });

  /* ── CAMBIAR CLAVE ── */
  const elClvP1 = $('modalClavePaso1'), elClvP2 = $('modalClavePaso2');
  $('btnAbrirCambioClave')?.addEventListener('click', () => { $('clvP1Actual').value=''; hideErr('errClvP1'); new bootstrap.Modal(elClvP1).show(); });
  elClvP1?.addEventListener('hidden.bs.modal', () => { $('clvP1Actual').value=''; hideErr('errClvP1'); });
  $('btnClvP1Siguiente')?.addEventListener('click', function () {
    const clave = $('clvP1Actual').value;
    if (!clave) { showErr('errClvP1Txt','errClvP1','Ingresa tu contraseña actual.'); return; }
    hideErr('errClvP1'); this.disabled=true; this.innerHTML='<span class="spinner-border spinner-border-sm"></span>';
    const fd = new FormData(); fd.append('accion','verificar_clave'); fd.append('clave_actual',clave);
    postAjax(EDITAR_URL, fd,
      () => { this.disabled=false; this.innerHTML='Siguiente <i class="bi bi-arrow-right ms-1"></i>'; $('clvP2Nueva').value=''; $('clvP2Confirmar').value=''; hideErr('errClvP2'); modalChain(elClvP1,elClvP2); },
      err => { this.disabled=false; this.innerHTML='Siguiente <i class="bi bi-arrow-right ms-1"></i>'; showErr('errClvP1Txt','errClvP1',err); }
    );
  });
  $('btnClvP2Volver')?.addEventListener('click', () => modalChain(elClvP2, elClvP1));
  $('btnClvP2Guardar')?.addEventListener('click', function () {
    const nueva=$('clvP2Nueva').value, confirmar=$('clvP2Confirmar').value;
    if (!nueva)              { showErr('errClvP2Txt','errClvP2','Escribe la nueva contraseña.'); return; }
    if (nueva.length < 6)    { showErr('errClvP2Txt','errClvP2','Mínimo 6 caracteres.'); return; }
    if (nueva !== confirmar) { showErr('errClvP2Txt','errClvP2','Las contraseñas no coinciden.'); return; }
    hideErr('errClvP2'); this.disabled=true; this.innerHTML='<span class="spinner-border spinner-border-sm"></span>';
    const fd = new FormData(); fd.append('accion','cambiar_clave'); fd.append('clave_nueva',nueva);
    postAjax(EDITAR_URL, fd, () => location.reload(),
      err => { this.disabled=false; this.innerHTML='<i class="bi bi-check-lg me-1"></i> Guardar'; showErr('errClvP2Txt','errClvP2',err); }
    );
  });

})();
