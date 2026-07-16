(function () {
    const cfg = JSON.parse(localStorage.getItem('cys_config') || '{}');
    const root = document.documentElement;

    // ── FUENTE ÚNICA DE VERDAD DE TEMAS ──
    // Cualquier script de página (ej. configuracion.js) debe reutilizar
    // window.CYS_TEMAS / window.aplicarTemaCYS en vez de definir su propia
    // copia, para que los 5 temas nunca se desincronicen entre archivos.
    const temas = {
        oscuro: {
            '--fondo':'#011936','--fondo-card':'#0a2240','--fondo-card2':'#0d2a4d',
            '--texto':'#e2e8f0','--texto-muted':'#7a9bbf','--azul-claro':'#4DA8DA',
            '--azul-borde':'rgba(77,168,218,.2)','--azul-oscuro':'#05244a',
            '--verde':'#2ecc71','--rojo':'#c0392b','--blanco':'#e8edf2','--gris-claro':'#8899aa',
        },
        claro: {
            '--fondo':'#f0f4f8','--fondo-card':'#ffffff','--fondo-card2':'#e8eef5',
            '--texto':'#1a2a3a','--texto-muted':'#4a6a8a','--azul-claro':'#B22A1A',
            '--azul-borde':'rgba(178,42,26,.18)','--azul-oscuro':'#ddeaf5',
            '--verde':'#1a8a4a','--rojo':'#B22A1A','--blanco':'#1a2a3a','--gris-claro':'#3a5a7a',
        },
        'alto-contraste': {
            '--fondo':'#000000','--fondo-card':'#0a0a0a','--fondo-card2':'#111111',
            '--texto':'#ffffff','--texto-muted':'#cccccc','--azul-claro':'#00cfff',
            '--azul-borde':'rgba(0,207,255,.4)','--azul-oscuro':'#001a22',
            '--verde':'#00ff88','--rojo':'#ff4444','--blanco':'#ffffff','--gris-claro':'#aaaaaa',
        },
        basecys: {
            '--fondo':'#241008','--fondo-card':'#34160D','--fondo-card2':'#421B10',
            '--texto':'#F2DFB8','--texto-muted':'#C9A876','--azul-claro':'#D9A441',
            '--azul-borde':'rgba(217,164,65,.25)','--azul-oscuro':'#1A0A06',
            '--verde':'#8AB86F','--rojo':'#B0392E','--blanco':'#F2DFB8','--gris-claro':'#B89868',
        },
        sepia: {
            '--fondo':'#1a0f05','--fondo-card':'#2c1f0e','--fondo-card2':'#3d2b14',
            '--texto':'#f5e6c8','--texto-muted':'#a08060','--azul-claro':'#d4a060',
            '--azul-borde':'rgba(212,160,96,.25)','--azul-oscuro':'#150c04',
            '--verde':'#7ab870','--rojo':'#c05030','--blanco':'#f5e6c8','--gris-claro':'#907060',
        },
    };

    const densidades = {
        compacto: {'--card-padding':'.75rem','--gap-base':'.4rem','--font-base':'.8rem'},
        normal:   {'--card-padding':'1.25rem','--gap-base':'.75rem','--font-base':'.875rem'},
        relajado: {'--card-padding':'1.75rem','--gap-base':'1.1rem','--font-base':'.95rem'},
    };

    function aplicarTema(nombreTema) {
        const vars = temas[nombreTema] || temas.oscuro;
        Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
    }

    function aplicarDensidad(nombreDensidad) {
        const vars = densidades[nombreDensidad] || densidades.normal;
        Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
    }

    // Aplica de inmediato (antes del primer paint) según lo guardado en localStorage
    aplicarTema(cfg.tema);
    aplicarDensidad(cfg.densidad);

    // Expone todo para que otras páginas/scripts (ej. configuracion.js) lo reutilicen
    window.CYS_TEMAS = temas;
    window.CYS_DENSIDADES = densidades;
    window.aplicarTemaCYS = aplicarTema;
    window.aplicarDensidadCYS = aplicarDensidad;
})();
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[title]').forEach(function (el) {
    new bootstrap.Tooltip(el, {
      placement: 'top',
      trigger: 'hover',
      container: 'body'
    });
  });
});

/* ============================================================
   WIDGET DE ACCESIBILIDAD — agregado al final de base.js
   Se guarda todo en localStorage bajo la clave 'cys_a11y' y se
   reaplica solo en cada carga de página, en cualquier plantilla
   que extienda base.html (por eso funciona igual en Reportes,
   Ventas, Inventario, etc. sin repetir nada).

   El "Modo de color" (Predeterminado / Oscuro / Claro) reutiliza
   window.aplicarTemaCYS() definida arriba en este mismo archivo,
   así nunca queda desincronizado con el sistema de temas.
   ============================================================ */
(function () {

    const A11Y_STORAGE_KEY = 'cys_a11y';
    const a11yRoot = document.documentElement;

    const a11yDefaults = {
        fontSize: 100,       // porcentaje
        modo: 'predeterminado',
        contraste: false,
        espaciado: false,
        enlaces: false,
        fuente: false,
    };

    function cargarConfigA11y() {
        try {
            return { ...a11yDefaults, ...JSON.parse(localStorage.getItem(A11Y_STORAGE_KEY) || '{}') };
        } catch (e) {
            return { ...a11yDefaults };
        }
    }

    function guardarConfigA11y(cfg) {
        localStorage.setItem(A11Y_STORAGE_KEY, JSON.stringify(cfg));
    }

    let configA11y = cargarConfigA11y();

    function aplicarTodoA11y(cfg) {
        // Tamaño de texto
        a11yRoot.style.fontSize = cfg.fontSize + '%';

        // Modo de color -> delega en aplicarTemaCYS (definida arriba en este archivo)
        if (typeof window.aplicarTemaCYS === 'function' && cfg.modo !== 'predeterminado') {
            window.aplicarTemaCYS(cfg.modo === 'oscuro' ? 'oscuro' : 'claro');
        } else if (typeof window.aplicarTemaCYS === 'function' && cfg.modo === 'predeterminado') {
            window.aplicarTemaCYS('oscuro'); // tema base del proyecto
        }

        // Alto contraste
        a11yRoot.classList.toggle('cys-a11y-contraste', cfg.contraste);
        // Espaciado de texto
        a11yRoot.classList.toggle('cys-a11y-espaciado', cfg.espaciado);
        // Resaltar enlaces
        a11yRoot.classList.toggle('cys-a11y-enlaces', cfg.enlaces);
        // Fuente legible
        a11yRoot.classList.toggle('cys-a11y-fuente', cfg.fuente);
    }

    // Aplica de inmediato al cargar la página (antes de esperar el DOM completo)
    aplicarTodoA11y(configA11y);

    document.addEventListener('DOMContentLoaded', function () {

        const toggleBtn   = document.getElementById('cysA11yToggle');
        const panel       = document.getElementById('cysA11yPanel');
        const closeBtn    = document.getElementById('cysA11yClose');

        const fontMinus   = document.getElementById('cysA11yFontMinus');
        const fontPlus    = document.getElementById('cysA11yFontPlus');
        const fontVal     = document.getElementById('cysA11yFontVal');

        const modoBtns    = document.querySelectorAll('.cys-a11y-colormode__btn');

        const chkContraste = document.getElementById('cysA11yContraste');
        const chkEspaciado = document.getElementById('cysA11yEspaciado');
        const chkEnlaces   = document.getElementById('cysA11yEnlaces');
        const chkFuente    = document.getElementById('cysA11yFuente');

        const resetBtn    = document.getElementById('cysA11yReset');

        if (!toggleBtn || !panel) return; // por si algún template no tiene el panel, no rompe la página

        // ---- Refleja el estado guardado en los controles del panel ----
        function sincronizarUIA11y() {
            fontVal.textContent = configA11y.fontSize + '%';

            modoBtns.forEach(btn => {
                btn.classList.toggle('cys-a11y-colormode__btn--active', btn.dataset.modo === configA11y.modo);
            });

            chkContraste.checked = configA11y.contraste;
            chkEspaciado.checked = configA11y.espaciado;
            chkEnlaces.checked   = configA11y.enlaces;
            chkFuente.checked    = configA11y.fuente;
        }
        sincronizarUIA11y();

        // ---- Abrir / cerrar panel ----
        function abrirPanelA11y() {
            panel.classList.add('cys-a11y-panel--open');
            toggleBtn.setAttribute('aria-expanded', 'true');
        }
        function cerrarPanelA11y() {
            panel.classList.remove('cys-a11y-panel--open');
            toggleBtn.setAttribute('aria-expanded', 'false');
        }

        toggleBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            panel.classList.contains('cys-a11y-panel--open') ? cerrarPanelA11y() : abrirPanelA11y();
        });
        closeBtn.addEventListener('click', cerrarPanelA11y);

        // Cierra si haces click fuera del panel
        document.addEventListener('click', function (e) {
            if (!panel.contains(e.target) && e.target !== toggleBtn) {
                cerrarPanelA11y();
            }
        });

        // ---- Tamaño de texto ----
        fontMinus.addEventListener('click', function () {
            configA11y.fontSize = Math.max(70, configA11y.fontSize - 10);
            aplicarTodoA11y(configA11y);
            guardarConfigA11y(configA11y);
            sincronizarUIA11y();
        });
        fontPlus.addEventListener('click', function () {
            configA11y.fontSize = Math.min(150, configA11y.fontSize + 10);
            aplicarTodoA11y(configA11y);
            guardarConfigA11y(configA11y);
            sincronizarUIA11y();
        });

        // ---- Modo de color ----
        modoBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                configA11y.modo = btn.dataset.modo;
                aplicarTodoA11y(configA11y);
                guardarConfigA11y(configA11y);
                sincronizarUIA11y();
            });
        });

        // ---- Switches ----
        chkContraste.addEventListener('change', function () {
            configA11y.contraste = chkContraste.checked;
            aplicarTodoA11y(configA11y);
            guardarConfigA11y(configA11y);
        });
        chkEspaciado.addEventListener('change', function () {
            configA11y.espaciado = chkEspaciado.checked;
            aplicarTodoA11y(configA11y);
            guardarConfigA11y(configA11y);
        });
        chkEnlaces.addEventListener('change', function () {
            configA11y.enlaces = chkEnlaces.checked;
            aplicarTodoA11y(configA11y);
            guardarConfigA11y(configA11y);
        });
        chkFuente.addEventListener('change', function () {
            configA11y.fuente = chkFuente.checked;
            aplicarTodoA11y(configA11y);
            guardarConfigA11y(configA11y);
        });

        // ---- Restablecer ----
        resetBtn.addEventListener('click', function () {
            configA11y = { ...a11yDefaults };
            aplicarTodoA11y(configA11y);
            guardarConfigA11y(configA11y);
            sincronizarUIA11y();
        });
    });

})();