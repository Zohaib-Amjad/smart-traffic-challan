// Keep the Chart.js instance so polling can replace it without duplicates.
let violationsChart = null;

function renderViolationsChart(data) {
  // Map grouped API rows to the labels and counts required by Chart.js.
  const ctx = document.getElementById('violationsPieChart');
  if (!ctx) return;

  const labels = data.map(item => item.violation_name.split('(')[0].trim());
  const counts = data.map(item => item.count);

  if (violationsChart) {
    violationsChart.destroy();
  }

  violationsChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        backgroundColor: [
          '#DC2626', // Red (Danger / Violation)
          '#F59E0B', // Amber / Yellow (Traffic Accent)
          '#2563EB', // Blue (Secondary)
          '#64748B', // Gray (Muted)
          '#16A34A'  // Green (Success)
        ],
        borderWidth: 2,
        borderColor: '#FFFFFF',
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            boxWidth: 10,
            padding: 8,
            color: '#1E293B',
            font: { size: 10, family: 'Plus Jakarta Sans', weight: '600' }
          }
        }
      },
      cutout: '68%'
    }
  });
}
