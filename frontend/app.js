/**
 * Dashboard App Logic (app.js)
 * Clean Light Theme, Resilient Error Handling, 24-Location Dropdown, Leaflet Light Map.
 */

// Global State
const state = {
  selectedStation: 'ALL', // 'ALL' or station slug ID
  selectedHorizon: 6, // 1, 6, 12, 24, 72
  mapTimeOffset: 0, // 0, 6, 12, 24, 48, 72
  activeMapLayer: 'aqi',
  map: null,
  mapMarkers: [],
  mapOverlays: { fires: null, inversion: null },
  chartForecast: null
};

document.addEventListener('DOMContentLoaded', () => {
  try {
    checkFallbackBanner();
    initLocationDropdown();
    initHorizonButtons();
    initMap();
    updateDashboard();
  } catch (err) {
    console.error("Dashboard initialization error caught gracefully:", err);
  }
});

// Display Fallback Banner if Data API rate limited / credit exhausted
function checkFallbackBanner() {
  if (DataHandler.isFallback()) {
    const banner = document.getElementById('fallback-banner');
    if (banner) {
      banner.classList.remove('hidden');
      document.getElementById('fallback-banner-text').textContent = DataHandler.getFallbackMessage() || 'Live API rate-limited or credits exhausted. Displaying resilient cached baseline data.';
    }
  }
}

// Initialize Searchable Location Dropdown for 24 Stations
function initLocationDropdown() {
  renderSearchableLocationDropdown('station-selector-container', (selectedId) => {
    state.selectedStation = selectedId;
    updateDashboard();
  });
}

// Horizon Pills (+1h, +6h, +12h, +24h, +72h)
function initHorizonButtons() {
  document.querySelectorAll('.horizon-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.horizon-btn').forEach(b => b.classList.remove('active'));
      e.currentTarget.classList.add('active');
      state.selectedHorizon = parseInt(e.currentTarget.dataset.horizon);
      updateForecastCard();
    });
  });

  // Map layer buttons
  document.querySelectorAll('.layer-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.layer-btn').forEach(b => b.classList.remove('active'));
      e.currentTarget.classList.add('active');
      state.activeMapLayer = e.currentTarget.dataset.layer;
      updateMapLayers();
    });
  });

  // Map timeline ticks
  document.querySelectorAll('.time-tick').forEach(tick => {
    tick.addEventListener('click', (e) => {
      document.querySelectorAll('.time-tick').forEach(t => t.classList.remove('active'));
      e.currentTarget.classList.add('active');
      state.mapTimeOffset = parseInt(e.currentTarget.dataset.time);
      updateMapMarkers();
    });
  });
}

// Master Dashboard UI Update
function updateDashboard() {
  try {
    const st = DataHandler.getStation(state.selectedStation);
    if (!st) return;

    // 1. Current AQI Hero Card
    const currentAQI = Math.round(DataHandler.safeGet(st.stats, 'aqi.latest', 65));
    const band = DataHandler.getAQIBand(currentAQI);

    document.getElementById('card-current-aqi-val').textContent = currentAQI;
    const catBadge = document.getElementById('card-aqi-category');
    catBadge.textContent = band.name;
    catBadge.style.backgroundColor = band.color;
    catBadge.style.color = band.textCol;

    document.getElementById('card-aqi-location').textContent = `at ${st.station}`;
    document.getElementById('card-dominant-pollutant').textContent = `Dominant: PM2.5`;

    // AQI pointer position (0-400 scale)
    const pointerPct = Math.min(Math.max((currentAQI / 400) * 100, 4), 96);
    document.getElementById('aqi-spectrum-pointer').style.left = `${pointerPct}%`;

    // 2. Forecast Card
    updateForecastCard();

    // 3. Weather Now Card
    const temp = DataHandler.safeGet(st.stats, 'temperature_2m.latest', 28);
    const hum = DataHandler.safeGet(st.stats, 'relative_humidity_2m.latest', 70);
    const wind = DataHandler.safeGet(st.stats, 'wind_speed_10m.latest', 6.5);
    const press = DataHandler.safeGet(st.stats, 'surface_pressure.latest', 978);
    const vent = DataHandler.safeGet(st.stats, 'ventilation_index.latest', 5.4);

    document.getElementById('card-temp-val').textContent = temp;
    document.getElementById('card-humidity-val').textContent = typeof hum === 'number' ? `${hum}%` : hum;
    document.getElementById('card-wind-val').textContent = typeof wind === 'number' ? `${wind} km/h` : wind;
    document.getElementById('card-pressure-val').textContent = typeof press === 'number' ? `${press} hPa` : press;
    document.getElementById('card-ventilation-val').textContent = vent;

    // 4. Update Forecast Chart
    renderForecastChart(st);

    // 5. Update Map Markers
    updateMapMarkers();

  } catch (err) {
    console.error("Error updating dashboard UI caught gracefully:", err);
  }
}

// Update Forecast Card (+1h, +6h, +12h, +24h, +72h)
function updateForecastCard() {
  try {
    const st = DataHandler.getStation(state.selectedStation);
    if (!st) return;

    const currentAQI = Math.round(DataHandler.safeGet(st.stats, 'aqi.latest', 65));
    const h = state.selectedHorizon;

    let predictedAQI = currentAQI;
    if (st.forecast && Array.isArray(st.forecast.aqi)) {
      const fc = st.forecast.aqi.find(item => item.horizon_h === h);
      if (fc) predictedAQI = Math.round(fc.value);
      else {
        const pmFc = st.forecast.pm25?.find(item => item.horizon_h === h);
        if (pmFc) predictedAQI = Math.round(pmFc.value * 1.4);
      }
    }

    document.getElementById('selected-horizon-badge').textContent = `+${h}h Outlook`;
    document.getElementById('card-forecast-aqi-val').textContent = predictedAQI;
    document.getElementById('forecast-horizon-text').textContent = `in ${h} hour${h > 1 ? 's' : ''}`;

    const diff = Math.round((predictedAQI - currentAQI) * 10) / 10;
    const deltaBadge = document.getElementById('card-forecast-delta');
    if (diff >= 0) {
      deltaBadge.className = 'bg-red-50 text-red-700 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1';
      deltaBadge.innerHTML = `<i class="fa-solid fa-arrow-trend-up"></i> <span>${diff} higher</span>`;
    } else {
      deltaBadge.className = 'bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1';
      deltaBadge.innerHTML = `<i class="fa-solid fa-arrow-trend-down"></i> <span>${Math.abs(diff)} lower</span>`;
    }

    const alertLine = document.getElementById('card-forecast-alert-line');
    const alertText = document.getElementById('card-forecast-alert-text');
    if (predictedAQI > 100) {
      alertLine.className = 'text-xs text-red-600 flex items-center gap-1.5 pt-3 border-t border-slate-100 font-semibold';
      alertText.textContent = `🚨 Forecast Exceeds Alert Threshold (100 AQI)`;
    } else {
      alertLine.className = 'text-xs text-emerald-600 flex items-center gap-1.5 pt-3 border-t border-slate-100 font-semibold';
      alertText.textContent = `✓ Within AQI Alert Threshold (100 AQI)`;
    }
  } catch (err) {
    console.error("Forecast card update error caught gracefully:", err);
  }
}

// Render 72h Forecast Line Chart
function renderForecastChart(st) {
  const ctx = document.getElementById('aqi-forecast-chart')?.getContext('2d');
  if (!ctx) return;

  document.getElementById('forecast-chart-station').textContent = `Station: ${st.station}`;

  const currentAQI = DataHandler.safeGet(st.stats, 'aqi.latest', 65);
  const currentPM25 = DataHandler.safeGet(st.stats, 'pm25.latest', 35);

  const aqiPoints = [currentAQI];
  const pm25Points = [currentPM25];

  [1, 6, 12, 24, 72].forEach(h => {
    const fAqi = st.forecast?.aqi?.find(f => f.horizon_h === h);
    const fPm = st.forecast?.pm25?.find(f => f.horizon_h === h);

    const pmVal = fPm ? fPm.value : (currentPM25 * (1 + (h / 200)));
    const aqiVal = fAqi ? fAqi.value : (pmVal * 1.4);

    aqiPoints.push(Math.round(aqiVal));
    pm25Points.push(Math.round(pmVal * 10) / 10);
  });

  const labels = ['NOW (0h)', '+1h', '+6h', '+12h', '+24h', '+72h'];

  if (state.chartForecast) {
    state.chartForecast.destroy();
  }

  state.chartForecast = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'AQI Forecast',
          data: aqiPoints,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          fill: true,
          tension: 0.35,
          borderWidth: 3,
          pointRadius: 5,
          pointBackgroundColor: '#2563eb'
        },
        {
          label: 'PM2.5 (µg/m³)',
          data: pm25Points,
          borderColor: '#059669',
          backgroundColor: 'transparent',
          tension: 0.35,
          borderWidth: 2,
          borderDash: [4, 4],
          pointRadius: 4,
          pointBackgroundColor: '#059669'
        }
      ]
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
        x: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b' } },
        y: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b' } }
      }
    }
  });
}

// Leaflet Map Initialization (Light Voyager Tiles)
function initMap() {
  const mapElem = document.getElementById('delhi-aqi-map');
  if (!mapElem) return;

  state.map = L.map('delhi-aqi-map', {
    center: [28.6139, 77.2090],
    zoom: 10,
    zoomControl: false
  });

  L.control.zoom({ position: 'topright' }).addTo(state.map);

  // Clean CartoDB Voyager Light Map Tiles
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 18
  }).addTo(state.map);

  updateMapMarkers();
}

function updateMapMarkers() {
  if (!state.map) return;

  state.mapMarkers.forEach(m => state.map.removeLayer(m));
  state.mapMarkers = [];

  const stations = DataHandler.getAllStations();
  const timeOffset = state.mapTimeOffset;

  stations.forEach(st => {
    let aqiVal = DataHandler.safeGet(st.stats, 'aqi.latest', 65);

    if (timeOffset > 0 && st.forecast && Array.isArray(st.forecast.aqi)) {
      const fObj = st.forecast.aqi.find(f => f.horizon_h === timeOffset);
      if (fObj) aqiVal = fObj.value;
    }

    const band = DataHandler.getAQIBand(aqiVal);

    const markerIcon = L.divIcon({
      className: 'custom-station-pin-wrapper',
      html: `<div class="custom-station-pin" style="background-color: ${band.color}; color: ${band.textCol}; width: 32px; height: 32px; font-weight: 800; font-size: 11px;">${Math.round(aqiVal)}</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const marker = L.marker([st.latitude, st.longitude], { icon: markerIcon }).addTo(state.map);

    const popupHtml = `
      <div style="color: #0f172a; font-family: Inter, sans-serif; padding: 2px;">
        <strong style="font-size: 13px; display: block; margin-bottom: 3px;">${st.station}</strong>
        <div style="display: flex; gap: 6px; align-items: center; margin-bottom: 4px;">
          <span style="font-size: 18px; font-weight: 800; font-family: JetBrains Mono;">${Math.round(aqiVal)}</span>
          <span style="background: ${band.color}; color: ${band.textCol}; padding: 1px 6px; border-radius: 10px; font-size: 10px; font-weight: 700;">${band.name}</span>
        </div>
        <div style="font-size: 11px; color: #64748b;">
          PM2.5: ${DataHandler.safeGet(st.stats, 'pm25.latest', '--')} µg/m³<br>
          Temp: ${DataHandler.safeGet(st.stats, 'temperature_2m.latest', '--')} °C | Wind: ${DataHandler.safeGet(st.stats, 'wind_speed_10m.latest', '--')} km/h
        </div>
      </div>
    `;

    marker.bindPopup(popupHtml);
    marker.on('click', () => {
      state.selectedStation = st.id;
      const label = document.getElementById('selected-location-label');
      if (label) label.textContent = st.station;
      updateDashboard();
    });

    state.mapMarkers.push(marker);
  });

  updateMapLayers();
}

function updateMapLayers() {
  if (!state.map) return;

  if (state.mapOverlays.fires) state.map.removeLayer(state.mapOverlays.fires);
  if (state.mapOverlays.inversion) state.map.removeLayer(state.mapOverlays.inversion);

  if (state.activeMapLayer === 'fires') {
    const fireGroup = L.layerGroup();
    const fireSpots = [
      [29.85, 76.20], [30.12, 75.80], [29.90, 76.50], [29.65, 76.10], [30.25, 75.95],
      [29.75, 76.40], [30.05, 76.15], [29.50, 76.30], [29.95, 75.70], [30.30, 76.45]
    ];

    fireSpots.forEach(coord => {
      const fireMarker = L.circleMarker(coord, {
        radius: 7,
        color: '#ef4444',
        fillColor: '#f97316',
        fillOpacity: 0.85
      }).bindPopup('<b>🔥 Active Stubble Fire Hotspot</b><br>Plume Drift Vector toward Delhi NCR');
      fireGroup.addLayer(fireMarker);
    });

    fireGroup.addTo(state.map);
    state.mapOverlays.fires = fireGroup;
  }

  if (state.activeMapLayer === 'inversion') {
    const invPoly = L.polygon([
      [28.85, 76.90], [28.85, 77.45], [28.35, 77.45], [28.35, 76.90]
    ], {
      color: '#8b5cf6',
      fillColor: '#8b5cf6',
      fillOpacity: 0.15,
      weight: 2,
      dashArray: '4, 4'
    }).bindPopup('<b>🌫️ Inversion Trap Zone</b><br>Low PBL Ceiling (< 300m) with high pollutant retention');

    invPoly.addTo(state.map);
    state.mapOverlays.inversion = invPoly;
  }
}
