(function () {
    const cfg = JSON.parse(localStorage.getItem('cys_config') || '{}');
    const root = document.documentElement;
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
    const tema     = temas[cfg.tema]          || temas.oscuro;
    const densidad = densidades[cfg.densidad] || densidades.normal;
    Object.entries({...tema,...densidad}).forEach(([k,v]) => root.style.setProperty(k,v));
})();