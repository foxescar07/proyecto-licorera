const ctx = document.getElementById('tendenciaChart');

if (ctx) {
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'],
            datasets: [{
                label: 'Ventas',
                data: [15, 25, 12, 30, 45, 60, 35],
                borderColor: '#B7372A',
                backgroundColor: 'rgba(183,55,42,0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}