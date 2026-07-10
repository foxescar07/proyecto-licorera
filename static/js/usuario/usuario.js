// ── Sacudir tarjeta si hay errores ──
function sacudir() {
  const t = document.getElementById('tarjeta');
  if (t) { t.classList.remove('shake'); void t.offsetWidth; t.classList.add('shake'); }
}

// ── Toggle password login ──
const btnToggleLogin = document.getElementById('btnToggleLogin');
if (btnToggleLogin) {
  btnToggleLogin.addEventListener('click', function () {
    const field = document.getElementById('loginPass');
    const icon  = this.querySelector('i');
    if (field && icon) {
      const isPass = field.type === 'password';
      field.type = isPass ? 'text' : 'password';
      icon.classList.toggle('bi-eye',      !isPass);
      icon.classList.toggle('bi-eye-slash', isPass);
    }
  });
}

// ── Hint dinámico campo usuario ──
const loginUser = document.getElementById('loginUser');
if (loginUser) {
  loginUser.addEventListener('input', function () {
    const val  = this.value.trim();
    const hint = document.getElementById('loginHint');
    if (!hint) return;
    if (!val) { hint.style.display = 'none'; hint.innerHTML = ''; return; }
    const soloNumeros = /^\d+$/.test(val);
    if (soloNumeros) {
      hint.className = 'cys-login-hint cys-login-hint--doc';
      hint.innerHTML = `<i class="bi bi-card-text"></i>
        <span>Estás ingresando tu <strong>número de documento</strong>.</span>`;
    } else {
      hint.className = 'cys-login-hint cys-login-hint--user';
      hint.innerHTML = `<i class="bi bi-person-badge"></i>
        <span>Estás ingresando tu <strong>nombre de usuario personalizado</strong>.</span>`;
    }
    hint.style.display = 'flex';
  });
}

// ── Solo números en OTP ──
const inputOtp = document.getElementById('inputOtp');
if (inputOtp) {
  inputOtp.addEventListener('input', function () {
    this.value = this.value.replace(/\D/g, '').slice(0, 6);
  });
}

// ── Cuenta regresiva 10 min (persistente con sessionStorage) ──
const spanTimer  = document.getElementById('cuentaRegresiva');
const badgeTimer = document.getElementById('badgeTimer');
const btnVerif   = document.getElementById('btnVerificar');

if (spanTimer) {
  const STORAGE_KEY = 'cys_otp_expira';
  const DURACION    = 10 * 60 * 1000; // 10 min en ms

  // Si no hay timestamp guardado o ya expiró más de 10 min, crear uno nuevo
  let expiraEn = parseInt(sessionStorage.getItem(STORAGE_KEY) || '0');
  if (!expiraEn || Date.now() > expiraEn + 1000) {
    expiraEn = Date.now() + DURACION;
    sessionStorage.setItem(STORAGE_KEY, expiraEn);
  }

  function mostrarExpirado() {
    spanTimer.textContent   = '00:00';
    spanTimer.style.color   = '#e87070';
    if (badgeTimer) {
      badgeTimer.innerHTML  = '<i class="bi bi-x-circle me-1"></i> Código expirado';
      badgeTimer.style.color       = '#e87070';
      badgeTimer.style.background  = 'rgba(192,57,43,.1)';
      badgeTimer.style.borderColor = 'rgba(192,57,43,.35)';
    }
    if (btnVerif) {
      btnVerif.disabled    = true;
      btnVerif.style.opacity    = '.45';
      btnVerif.style.cursor     = 'not-allowed';
      btnVerif.innerHTML   = '<i class="bi bi-x-circle me-1"></i> Código expirado';
    }
    // Mostrar enlace de reenvío
    const reenviar = document.getElementById('enlaceReenviar');
    if (reenviar) reenviar.style.display = 'inline-flex';
    sessionStorage.removeItem(STORAGE_KEY);
  }

  function actualizarTimer() {
    const restante = expiraEn - Date.now();
    if (restante <= 0) {
      clearInterval(intervalo);
      mostrarExpirado();
      return;
    }
    const m = String(Math.floor(restante / 60000)).padStart(2, '0');
    const s = String(Math.floor((restante % 60000) / 1000)).padStart(2, '0');
    spanTimer.textContent = `${m}:${s}`;
    if (restante <= 60000) spanTimer.style.color = '#e87070';
  }

  actualizarTimer();
  const intervalo = setInterval(actualizarTimer, 1000);
}

// ── Limpiar timer al reenviar ──
const enlaceReenviar = document.getElementById('enlaceReenviar');
if (enlaceReenviar) {
  enlaceReenviar.addEventListener('click', () => {
    sessionStorage.removeItem('cys_otp_expira');
  });
}
