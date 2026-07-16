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