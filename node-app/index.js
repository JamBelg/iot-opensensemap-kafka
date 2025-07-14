import express from 'express';
import pkg from 'pg';
const { Pool } = pkg;

const app = express();
const PORT = 3000;

const pool = new Pool({
  user: 'postgres',
  host: 'postgres',
  database: 'iot_db',
  password: 'postgres',
  port: 5432,
});

function formatDate(date) {
  const d = new Date(date);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${day}.${month}.${year} ${hours}:${minutes}`;
}

app.get('/', async (req, res) => {
  try {
    const valuesResult = await pool.query(`
      SELECT value, original_timestamp
      FROM sensor_values
      ORDER BY original_timestamp DESC
      LIMIT 100
    `);
    const eventsResult = await pool.query(`
      SELECT id, event_type, status
      FROM sensor_events
      ORDER BY id DESC
      LIMIT 100
    `);
    const countValues = await pool.query('SELECT COUNT(*) FROM sensor_values');
    const countEvents = await pool.query('SELECT COUNT(*) FROM sensor_events');

    const valueCount = countValues.rows[0].count;
    const eventCount = countEvents.rows[0].count;

    const valuesData = valuesResult.rows.map(row => ({
      value: row.value,
      date: formatDate(row.original_timestamp),
    }));

    const eventsData = eventsResult.rows;

    const chartLabels = valuesData.map(v => v.date).reverse();
    const chartValues = valuesData.map(v => v.value).reverse();

    res.send(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>IoT Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
          body {
            padding: 2rem;
            background-color: #f8f9fa;
          }
          h1, h2, h3 {
            text-align: center;
          }
          .center-table {
            margin: auto;
            width: 80%;
          }
          .chart-container {
            width: 100%;
            max-width: 800px;
            margin: 2rem auto;
          }
          th, td {
            width: 100px;
            text-align: center;
          }
          .pagination {
            display: flex;
            justify-content: center;
            margin: 1rem 0;
          }
          .pagination button {
            margin: 0 5px;
            padding: 0.3rem 0.8rem;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>📊 IoT Sensor Dashboard</h1>

          <h2>✅ Sensor Values Count: ${valueCount}</h2>
          <div class="chart-container">
            <canvas id="lineChart"></canvas>
          </div>

          <h3>Latest Sensor Values</h3>
          <table class="table table-striped table-bordered center-table">
            <thead class="table-dark">
              <tr><th>Date</th><th>Value</th></tr>
            </thead>
            <tbody id="values-body"></tbody>
          </table>
          <div class="pagination" id="pagination-controls"></div>

          <h2>📦 Sensor Events Count: ${eventCount}</h2>
          <h3>Latest Events</h3>
          <table class="table table-striped table-bordered center-table">
            <thead class="table-dark">
              <tr><th>ID</th><th>Type</th><th>Status</th></tr>
            </thead>
            <tbody>
              ${eventsData.map(row => `
                <tr>
                  <td>${row.id}</td>
                  <td>${row.event_type}</td>
                  <td>${row.status}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <script>
          const valuesData = ${JSON.stringify(valuesData)};
          const rowsPerPage = 10;
          let currentPage = 1;

          function renderTablePage(page) {
            const tableBody = document.getElementById('values-body');
            const start = (page - 1) * rowsPerPage;
            const end = start + rowsPerPage;
            const rows = valuesData.slice(start, end);
            tableBody.innerHTML = rows.map(row => \`
              <tr>
                <td>\${row.date}</td>
                <td>\${row.value}</td>
              </tr>
            \`).join('');
          }

          function renderPagination() {
            const totalPages = Math.ceil(valuesData.length / rowsPerPage);
            const controls = document.getElementById('pagination-controls');
            controls.innerHTML = '';
            for (let i = 1; i <= totalPages; i++) {
              const btn = document.createElement('button');
              btn.textContent = i;
              if (i === currentPage) btn.disabled = true;
              btn.onclick = () => {
                currentPage = i;
                renderTablePage(currentPage);
                renderPagination();
              };
              controls.appendChild(btn);
            }
          }

          renderTablePage(currentPage);
          renderPagination();

          const ctx = document.getElementById('lineChart').getContext('2d');
          new Chart(ctx, {
            type: 'line',
            data: {
              labels: ${JSON.stringify(chartLabels)},
              datasets: [{
                label: 'Sensor Value',
                data: ${JSON.stringify(chartValues)},
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                fill: false
              }]
            },
            options: {
              responsive: true,
              scales: {
                x: { title: { display: true, text: 'Date' }},
                y: { title: { display: true, text: 'Value' }}
              }
            }
          });
        </script>
      </body>
      </html>
    `);
  } catch (err) {
    console.error(err);
    res.status(500).send('Error querying database');
  }
});

app.listen(PORT, () => {
  console.log(`🌐 Server is running at http://localhost:${PORT}`);
});
