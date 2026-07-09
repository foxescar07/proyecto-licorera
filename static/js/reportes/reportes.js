/**
 * REPORTES.JS — Reportes y Análisis
 * DataTable, filtrado, paginación, gráficas en tarjetas
 */

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
document.addEventListener('DOMContentLoaded', function() { pagProv(0); });

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

/* ════════════════════════════════════════════════════════════
   TARJETAS DE REPORTE: abrir modal SOLO si no se tocó el botón
   de gráfica ni el área de la gráfica.
   ════════════════════════════════════════════════════════════ */
document.querySelectorAll('.cys-card--interactive[data-modal-target]').forEach(function (card) {
    card.addEventListener('click', function (e) {
        if (e.target.closest('.cys-report-card__chart-toggle') ||
            e.target.closest('.cys-report-card__chart-wrap')) {
            return;
        }
        const sel = card.getAttribute('data-modal-target');
        const modalEl = document.querySelector(sel);
        if (modalEl && window.bootstrap) {
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
        }
    });
});

/* Botón de gráfica: maneja su propio clic/touch */
document.querySelectorAll('.cys-report-card__chart-toggle').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
        e.stopPropagation();
        e.preventDefault();
        toggleCardChart(this);
    });
});

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
