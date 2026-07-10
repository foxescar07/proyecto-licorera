// ── Toggle ver/ocultar contraseña ──
function toggleEye(inputId, btn) {
  const field = document.getElementById(inputId);
  const icon  = btn.querySelector('i');
  if (!field || !icon) return;
  const isPassword = field.type === 'password';
  field.type = isPassword ? 'text' : 'password';
  icon.classList.toggle('bi-eye',       !isPassword);
  icon.classList.toggle('bi-eye-slash',  isPassword);
}

document.getElementById('btnToggleNueva')?.addEventListener('click', function () {
  toggleEye('nuevaClave', this);
});
document.getElementById('btnToggleConfirmar')?.addEventListener('click', function () {
  toggleEye('confirmarClave', this);
});

// ── Validación de formulario ──
const form = document.getElementById('formReset');
if (form) {
  form.addEventListener('submit', function(e) {
    const clave        = document.getElementById('nuevaClave').value;
    const confirmar    = document.getElementById('confirmarClave').value;
    const errClave     = document.getElementById('errClave');
    const errConfirmar = document.getElementById('errConfirmar');
    let ok = true;
    errClave.style.display = 'none';
    errConfirmar.style.display = 'none';

    if (clave.length < 6) {
      errClave.textContent = 'Mínimo 6 caracteres.';
      errClave.style.display = 'block'; ok = false;
    } else if ((clave.match(/\d/g) || []).length < 2) {
      errClave.textContent = 'Debe contener al menos 2 números.';
      errClave.style.display = 'block'; ok = false;
    } else if (!/[A-Z]/.test(clave)) {
      errClave.textContent = 'Debe contener al menos 1 mayúscula.';
      errClave.style.display = 'block'; ok = false;
    }
    if (clave !== confirmar) {
      errConfirmar.textContent = 'Las contraseñas no coinciden.';
      errConfirmar.style.display = 'block'; ok = false;
    }
    if (!ok) e.preventDefault();
  });
}
