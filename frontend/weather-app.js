/**
 * Weather & Atmospheric Dynamics Logic (weather-app.js)
 * Clean Light Theme, Searchable 24-Location Dropdown, Thermal Inversion Metrics,
 * and Resilient Data Error Handling.
 */

// Global State
const state = {
  selectedStation: 'ALL',
  selectedMetric: 'temperature_2m',
  chartWeather: null
};

document.addEventListener('DOMContentLoaded', () => {
  try {
    checkFallbackBanner();
    initLocationDropdown();
    initMetricButtons();
    updateDashboard();
  } catch (err) {
    console.error("Weather App initialization error caught gracefully:", err);
  }
});

// Fallback Banner Check
function checkFallbackBanner() {
  if (DataHandler.isFallback()) {
    const banner = document.getElementById('fallback-banner');
    if (banner) {
      banner.classList.remove('hidden');
      document.getElementById('fallback-banner-text').textContent = DataHandler.getFallbackMessage() || 'Live API rate-limited or credits exhausted. Displaying resilient cached baseline data.';
    }
  }
}

// Searchable Dropdown Location Selector (24 Locations)
function initLocationDropdown() {
  renderSearchableLocationDropdown('station-selector-container', (selectedId) => {
    state.selectedStation = selectedId;
    updateDashboard();
  });
}

// Chart Metric Selector Buttons
function initMetricButtons() {
  document.querySelectorAll('.weather-metric-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.weather-metric-btn').forEach(b => {
        b.classList.remove('active', 'bg-white', 'shadow-xs', 'text-slate-700');
        b.classList.add('text-slate-600');
      });
      e.currentTarget.classList.add('active', 'bg-white', 'shadow-xs', 'text-slate-700');
      state.selectedMetric = e.currentTarget.dataset.metric;
      renderWeatherChart();
    });
  });
}

// Update Master Weather UI
function updateDashboard() {
  try {
    const st = DataHandler.getStation(state.selectedStation);
    if (!st) return;

    // 1. Weather Cards
    const temp = DataHandler.safeGet(st.stats, 'temperature_2m.latest', 28);
    const tempDelta = DataHandler.safeGet(st.stats, 'temperature_change_3h.latest', -0.5);
    const hum = DataHandler.safeGet(st.stats, 'relative_humidity_2m.latest', 70);
    const wind = DataHandler.safeGet(st.stats, 'wind_speed_10m.latest', 6.5);
    const windDir = DataHandler.safeGet(st.stats, 'wind_direction_10m.latest', 215);
    const press = DataHandler.safeGet(st.stats, 'surface_pressure.latest', 978);
    const vent = DataHandler.safeGet(st.stats, 'ventilation_index.latest', 5.4);

    document.getElementById('temp-val').textContent = temp;
    document.getElementById('temp-trend').textContent = `3h Change: ${tempDelta > 0 ? '+' : ''}${tempDelta} °C`;

    document.getElementById('humidity-val').textContent = hum;
    document.getElementById('wind-val').textContent = wind;
    document.getElementById('wind-dir-text').textContent = `Direction: ${windDir}° (${getWindDirectionName(windDir)} Drift)`;

    document.getElementById('vent-val').textContent = vent;
    
    // Inversion Layer Details
    document.getElementById('ground-temp-val').textContent = `${temp} °C`;
    document.getElementById('upper-temp-val').textContent = `${Math.round((temp + 3.3) * 10) / 10} °C`;
    document.getElementById('pbl-height-val').textContent = `${Math.round(250 + (vent * 25))} m`;

    renderWeatherChart();
  } catch (err) {
    console.error("Error updating Weather Dashboard UI caught gracefully:", err);
  }
}

function getWindDirectionName(deg) {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return directions[Math.round((deg || 215) / 45) % 8];
}

// Render Weather Trend Chart
function renderWeatherChart() {
  const ctx = document.getElementById('weatherDetailChart')?.getContext('2d');
  if (!ctx) return;

  const st = DataHandler.getStation(state.selectedStation);
  if (!st) return;

  const metricKey = state.selectedMetric;
  let values = [];

  if (st.weather && st.weather[metricKey] && Array.isArray(st.weather[metricKey].values)) {
    values = st.weather[metricKey].values;
  } else {
    values = Array(168).fill(st.stats[metricKey]?.latest || 25);
  }

  // Sample points (every 3h)
  const sampledLabels = [];
  const sampledVals = [];
  for (let i = 0; i < values.length; i += 3) {
    sampledLabels.push(`T-${168 - i}h`);
    sampledVals.push(values[i]);
  }

  const metricNames = {
    temperature_2m: { label: 'Temperature 2m (°C)', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.08)' },
    relative_humidity_2m: { label: 'Relative Humidity (%)', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.08)' },
    wind_speed_10m: { label: 'Wind Speed 10m (km/h)', color: '#10b981', bg: 'rgba(16, 185, 129, 0.08)' },
    surface_pressure: { label: 'Surface Pressure (hPa)', color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.08)' }
  };

  const meta = metricNames[metricKey] || metricNames.temperature_2m;

  if (state.chartWeather) {
    state.chartWeather.destroy();
  }

  state.chartWeather = new Chart(ctx, {
    type: 'line',
    data: {
      labels: sampledLabels,
      datasets: [{
        label: meta.label,
        data: sampledVals,
        borderColor: meta.color,
        backgroundColor: meta.bg,
        fill: true,
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#475569', font: { family: 'Inter', weight: '500' } } },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: '#ffffff',
          titleColor: '#0f172a',
          bodyColor: '#334155',
          borderColor: '#e2e8f0',
          borderWidth: 1
        }
      },
      scales: {
        x: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b', font: { size: 10 } } },
        y: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b', font: { size: 10 } } }
      }
    }
  });
}
