/**
 * REPORTES.JS — Reportes y Análisis
 * DataTable, filtrado, paginación, gráficas en tarjetas
 */
console.log('[reportes.js] archivo cargado y ejecutándose');

/* ── DataTable Historial de Ventas ── */
$(document).ready(function() {
    var table = $('#reportes-table').DataTable({
        paging: true,
        searching: true,
        info: true,
        lengthChange: false,
        pageLength: 10,
        ordering: true,
        responsive: true,
        language: {
            info: "Mostrando _START_ a _END_ de _TOTAL_ ventas",
            infoEmpty: "Mostrando 0 a 0 de 0 ventas",
            paginate: { first:'«', previous:'‹', next:'›', last:'»' }
        },
        dom: 'rt<"cys-hv-table-footer"ip>'
    });

    $('#buscar-historial').on('keyup', function() {
        table.search(this.value).draw();
    });

    function syncExportLinks() {
        const fi = $('#filtro-fecha-inicio').val() || '';
        const ff = $('#filtro-fecha-fin').val()    || '';
        const p  = `&fecha_inicio=${fi}&fecha_fin=${ff}`;
        $('#btn-export-excel').attr('href', `?export=excel&tipo=ventas${p}`);
        $('#btn-export-pdf').attr('href',   `?export=pdf&tipo=ventas${p}`);
        $('#btn-export-print').attr('href', `?export=pdf&tipo=ventas&print=true${p}`);
    }

    $('#filtro-fecha-inicio, #filtro-fecha-fin').on('change', function() {
        syncExportLinks();
        aplicarFiltro();
    });

    syncExportLinks();
});

function aplicarFiltro() {
    const fi = document.getElementById('filtro-fecha-inicio').value;
    const ff = document.getElementById('filtro-fecha-fin').value;
    let url  = window.location.pathname + '?';
    if (fi) url += 'fecha_inicio=' + fi + '&';
    if (ff) url += 'fecha_fin='    + ff;
    window.location.href = url;
}

/* ── Búsqueda inventario ── */
function filtrarTablaInv(q) {
    q = q.toLowerCase();
    document.querySelectorAll('#tabla-modal-stock .inv-row').forEach(function(row) {
        const txt = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        row.style.display = txt.includes(q) ? '' : 'none';
    });
}

/* ── Búsqueda proveedores ── */
function filtrarTablaProv(q) {
    q = q.toLowerCase();
    document.querySelectorAll('#tabla-modal-proveedores .prov-row').forEach(function(row) {
        const nombre  = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const empresa = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        row.style.display = (nombre.includes(q) || empresa.includes(q)) ? '' : 'none';
    });
}

/* ── Paginación simple proveedores ── */
var provPagActual = 1;
function pagProv(dir) {
    var rows = document.querySelectorAll('#tabla-modal-proveedores .prov-row');
    var perPage = 5;
    var total   = Math.ceil(rows.length / perPage);
    provPagActual = Math.max(1, Math.min(provPagActual + dir, total));
    rows.forEach(function(r, i) {
        var page = Math.floor(i / perPage) + 1;
        r.style.display = page === provPagActual ? '' : 'none';
    });
    document.getElementById('prov-pag-indicator').textContent = provPagActual;
}

/* ── Análisis de ventas — sidebar nav ── */
function avSetTab(tab) {
    ['resumen','fecha','top'].forEach(function(t) {
        var panel = document.getElementById('avPanel-'  + t);
        var btn   = document.getElementById('avNav-'    + t);
        if (!panel || !btn) return;
        if (t === tab) {
            panel.classList.remove('cys-av-panel--hidden');
            btn.classList.add('active');
        } else {
            panel.classList.add('cys-av-panel--hidden');
            btn.classList.remove('active');
        }
    });
}

/* ── Búsqueda: Análisis de Ventas → panel "Por fecha" ── */
function filtrarTablaAVFecha(q) {
    q = q.toLowerCase().trim();
    const filas = document.querySelectorAll('#tabla-modal-av-ventas .av-fecha-row');
    let visibles = 0;
    filas.forEach(function(row) {
        const cliente  = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const producto = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        const coincide = cliente.includes(q) || producto.includes(q);
        row.style.display = coincide ? '' : 'none';
        if (coincide) visibles++;
    });
    const noResults = document.getElementById('av-fecha-no-results');
    if (noResults) {
        noResults.classList.toggle('d-none', !(filas.length > 0 && visibles === 0));
    }
}

/* ── Búsqueda: Análisis de Ventas → panel "Top productos" ── */
function filtrarTablaAVTop(q) {
    q = q.toLowerCase().trim();
    const filas = document.querySelectorAll('#tabla-modal-av-top .av-top-row');
    let visibles = 0;
    filas.forEach(function(row) {
        const producto = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const coincide = producto.includes(q);
        row.style.display = coincide ? '' : 'none';
        if (coincide) visibles++;
    });
    const noResults = document.getElementById('av-top-no-results');
    if (noResults) {
        noResults.classList.toggle('d-none', !(filas.length > 0 && visibles === 0));
    }
}

/* ── Búsqueda devoluciones ── */
function filtrarTablaDevoluciones(q) {
    q = q.toLowerCase();
    document.querySelectorAll('#tabla-modal-devoluciones .dev-row').forEach(function(row) {
        const cliente  = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const producto = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        row.style.display = (cliente.includes(q) || producto.includes(q)) ? '' : 'none';
    });
}

/* ── Búsqueda: Resumen Diario → tab "Entradas" ── */
function filtrarTablaRDEntradas(q) {
    q = q.toLowerCase().trim();
    const filas = document.querySelectorAll('#tabla-modal-rd-entradas .rd-entrada-row');
    let visibles = 0;
    filas.forEach(function(row) {
        const producto = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const coincide = producto.includes(q);
        row.style.display = coincide ? '' : 'none';
        if (coincide) visibles++;
    });
    const noResults = document.getElementById('rd-entradas-no-results');
    if (noResults) {
        noResults.classList.toggle('d-none', !(filas.length > 0 && visibles === 0));
    }
}

/* ── Búsqueda: Resumen Diario → tab "Salidas" ── */
function filtrarTablaRDSalidas(q) {
    q = q.toLowerCase().trim();
    const filas = document.querySelectorAll('#tabla-modal-rd-salidas .rd-salida-row');
    let visibles = 0;
    filas.forEach(function(row) {
        const producto = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const coincide = producto.includes(q);
        row.style.display = coincide ? '' : 'none';
        if (coincide) visibles++;
    });
    const noResults = document.getElementById('rd-salidas-no-results');
    if (noResults) {
        noResults.classList.toggle('d-none', !(filas.length > 0 && visibles === 0));
    }
}

/* ── Búsqueda: Resumen Diario → tab "Ventas" ── */
function filtrarTablaRDVentas(q) {
    q = q.toLowerCase().trim();
    const filas = document.querySelectorAll('#tabla-modal-rd-ventas .rd-venta-row');
    let visibles = 0;
    filas.forEach(function(row) {
        const cliente  = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        const producto = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        const coincide = cliente.includes(q) || producto.includes(q);
        row.style.display = coincide ? '' : 'none';
        if (coincide) visibles++;
    });
    const noResults = document.getElementById('rd-ventas-no-results');
    if (noResults) {
        noResults.classList.toggle('d-none', !(filas.length > 0 && visibles === 0));
    }
}

/* ════════════════════════════════════════════════════════════
   MINI GRÁFICAS EN LAS TARJETAS DE REPORTE
   ════════════════════════════════════════════════════════════ */

const CYS_CHART_PALETTE = ['#A78BFA', '#3ECF8E'];

function toggleCardChart(btn) {
    const card   = btn.closest('.cys-card');
    const wrap   = card.querySelector('.cys-report-card__chart-wrap');
    const layout = card.querySelector('.cys-report-card-layout');
    if (!wrap || !layout) return;

    const mostrandoGrafica = card.classList.toggle('cys-card--chart-mode');
    btn.classList.toggle('is-active');

    if (mostrandoGrafica) {
        layout.classList.add('d-none');
        wrap.classList.remove('d-none');

        if (!wrap.dataset.rendered) {
            renderReportCardChart(wrap, card);
            wrap.dataset.rendered = '1';
        }
    } else {
        layout.classList.remove('d-none');
        wrap.classList.add('d-none');
    }
}

function renderReportCardChart(wrap, card) {
    const statItems = card.querySelectorAll('.cys-report-card__stat-item');

    const labels = [];
    const data = [];
    const colors = [];

    let colorIndex = 0;
    statItems.forEach(function (item) {
        const numEl = item.querySelector('.cys-report-card__stat-num');
        const labelEl = item.querySelector('.cys-report-card__stat-label');
        if (!numEl || !labelEl) return;

        const rawText = numEl.textContent.trim();
        if (!/\d/.test(rawText)) return;

        const valorNumerico = parseFloat(rawText.replace(/[^0-9.\-]/g, '')) || 0;
        const color = CYS_CHART_PALETTE[colorIndex % CYS_CHART_PALETTE.length];
        colorIndex++;

        labels.push(labelEl.textContent.trim());
        data.push(valorNumerico);
        colors.push(color);
    });

    if (data.length === 0) {
        wrap.innerHTML = '<div class="cys-empty-box cys-empty-box--mini">Sin datos suficientes para graficar.</div>';
        return;
    }

    const canvas = wrap.querySelector('canvas');
    if (!canvas) return;

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderRadius: 6,
                maxBarThickness: 42
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 500 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#02224a',
                    borderColor: 'rgba(167,139,250,.35)',
                    borderWidth: 1,
                    titleColor: '#fff',
                    bodyColor: '#EAF3FA'
                }
            },
            scales: {
                x: {
                    ticks: { color: '#8FA3B1', font: { size: 10 } },
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: '#8FA3B1', font: { size: 10 }, precision: 0 },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                }
            }
        }
    });
}

/* ════════════════════════════════════════════════════════════
   INICIALIZACIÓN
   La apertura de los modales de las tarjetas YA NO se maneja
   aquí: cada tarjeta tiene data-bs-toggle="modal" y
   data-bs-target="#modalX" en el HTML, así que Bootstrap las
   abre directamente (delegado sobre document, no depende de
   cuándo cargue este script).
   Aquí solo queda: la paginación inicial de proveedores y el
   botón de gráfica de cada tarjeta (que debe frenar la
   propagación del clic para no abrir el modal al mismo tiempo).
   ════════════════════════════════════════════════════════════ */
function initReportesUI() {
    pagProv(0);

    const botonesGrafica = document.querySelectorAll('.cys-report-card__chart-toggle');
    console.log('[reportes.js] botones de gráfica encontrados:', botonesGrafica.length);

    botonesGrafica.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            console.log('[reportes.js] clic en botón de gráfica detectado');
            e.preventDefault();
            e.stopPropagation();
            toggleCardChart(this);
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReportesUI);
} else {
    initReportesUI();
}