/**
 * Pollutant Intelligence Application Logic (pollutants-app.js)
 * Clean Light Theme, Searchable 24-Location Dropdown, WHO Guideline Comparisons,
 * Disease Share Bars, and Resilient Data Error Handling.
 */

// Pollutant Knowledge Base Definition
const POLLUTANT_INFO = {
  pm25: {
    id: 'pm25', name: 'PM2.5', formula: 'PM₂.₅', fullName: 'Fine Particulate Matter',
    unit: 'µg/m³', whoLimit: 15, naaqs: 60,
    description: 'Microscopic particles ≤2.5 micrometers in diameter capable of penetrating deep into pulmonary alveoli and systemic blood circulation.',
    size: '2.5 µm — 30x smaller than a human hair',
    facts: [
      { icon: '🔬', text: 'Penetrates deep into pulmonary alveoli & arterial blood' },
      { icon: '👁️', text: 'Primary constituent of atmospheric winter smog' },
      { icon: '⏱️', text: 'Remains airborne for days during thermal inversion' },
      { icon: '🌾', text: 'Drifts hundreds of kilometers from stubble fire clusters' }
    ],
    sources: [
      { name: 'Vehicular Exhaust', pct: 35, color: '#ef4444' },
      { name: 'Biomass/Stubble Smoke', pct: 28, color: '#f97316' },
      { name: 'Road & Construction Dust', pct: 18, color: '#eab308' },
      { name: 'Industrial Stacks', pct: 12, color: '#94a3b8' },
      { name: 'Domestic & Trash Fires', pct: 7, color: '#cbd5e1' }
    ],
    healthImpact: [
      { disease: 'Chronic Obstructive Pulmonary Disease (COPD)', pct: 30, color: '#ef4444' },
      { disease: 'Lower Respiratory Infections', pct: 24, color: '#f97316' },
      { disease: 'Cerebrovascular Stroke Risk', pct: 23, color: '#eab308' },
      { disease: 'Ischemic Heart Disease (Heart Attack)', pct: 16, color: '#3b82f6' },
      { disease: 'Trachea & Lung Cancer', pct: 7, color: '#8b5cf6' }
    ],
    envEffects: [
      { icon: '🌫️', label: 'Haze & Visibility Loss', desc: 'Attenuates sunlight & reduces visibility' },
      { icon: '🌡️', label: 'Solar Radiative Forcing', desc: 'Alters atmospheric radiation & boundary layer' },
      { icon: '🌿', label: 'Crop Photosynthesis Damage', desc: 'Covers leaves and reduces agricultural yield' }
    ]
  },
  pm10: {
    id: 'pm10', name: 'PM10', formula: 'PM₁₀', fullName: 'Coarse Particulate Matter',
    unit: 'µg/m³', whoLimit: 45, naaqs: 100,
    description: 'Inhalable coarse dust particles ≤10 micrometers in diameter, commonly whipped up from unpaved roads and construction activities.',
    size: '10 µm — about 1/7th the width of a human hair',
    facts: [
      { icon: '👃', text: 'Deposits in upper nasal passages and trachea' },
      { icon: '💨', text: 'Resuspended heavily by strong surface winds' },
      { icon: '🤧', text: 'Primary trigger for acute nasal allergies & asthma' }
    ],
    sources: [
      { name: 'Construction & Demolition', pct: 40, color: '#94a3b8' },
      { name: 'Unpaved Road Dust', pct: 30, color: '#eab308' },
      { name: 'Vehicles', pct: 15, color: '#ef4444' },
      { name: 'Industry', pct: 10, color: '#f97316' },
      { name: 'Other', pct: 5, color: '#cbd5e1' }
    ],
    healthImpact: [
      { disease: 'Nasal & Upper Airway Irritation', pct: 38, color: '#eab308' },
      { disease: 'Asthma Exacerbation & Wheezing', pct: 32, color: '#f97316' },
      { disease: 'Chronic Bronchitis Flare-ups', pct: 18, color: '#ef4444' },
      { disease: 'Mucosal Eye & Throat Inflammation', pct: 12, color: '#3b82f6' }
    ],
    envEffects: [
      { icon: '🌫️', label: 'Coarse Haze Clouds', desc: 'Reduces regional optical clarity' },
      { icon: '🍃', label: 'Stomatal Blockage', desc: 'Impairs plant transpiration' }
    ]
  },
  no2: {
    id: 'no2', name: 'NO₂', formula: 'NO₂', fullName: 'Nitrogen Dioxide',
    unit: 'µg/m³', whoLimit: 25, naaqs: 80,
    description: 'Reddish-brown toxic gas emitted from high-temperature combustion in diesel vehicles, thermal power plants, and industrial boilers.',
    size: 'Molecular gas',
    facts: [
      { icon: '👃', text: 'Acrid, sharp pungent odor' },
      { icon: '🚗', text: 'Highly concentrated around heavy traffic arterial corridors' },
      { icon: '🌧️', text: 'Key precursor to acid precipitation and nitrate haze' }
    ],
    sources: [
      { name: 'Diesel Vehicle Exhaust', pct: 55, color: '#ef4444' },
      { name: 'Power Plants', pct: 25, color: '#eab308' },
      { name: 'Industrial Furnaces', pct: 12, color: '#f97316' },
      { name: 'Domestic Gas Burning', pct: 8, color: '#cbd5e1' }
    ],
    healthImpact: [
      { disease: 'Pediatric Asthma Attacks', pct: 42, color: '#ef4444' },
      { disease: 'Airway Hyper-reactivity', pct: 28, color: '#f97316' },
      { disease: 'Childhood Lung Capacity Deficit', pct: 20, color: '#eab308' },
      { disease: 'Respiratory Infection Vulnerability', pct: 10, color: '#3b82f6' }
    ],
    envEffects: [
      { icon: '🌧️', label: 'Acid Rain Precursor', desc: 'Damages soil & aquatic ecosystems' },
      { icon: '🌊', label: 'Nutrient Eutrophication', desc: 'Causes algal blooms in water bodies' }
    ]
  },
  so2: {
    id: 'so2', name: 'SO₂', formula: 'SO₂', fullName: 'Sulfur Dioxide',
    unit: 'µg/m³', whoLimit: 40, naaqs: 80,
    description: 'Pungent, suffocating gas produced from combustion of sulfur-rich fossil fuels in coal power plants and heavy fuel boilers.',
    size: 'Molecular gas',
    facts: [
      { icon: '🏭', text: 'Dominantly produced from industrial stack combustion' },
      { icon: '♨️', text: 'Smells strongly like a freshly struck match' },
      { icon: '🌧️', text: 'Forms sulfate aerosol particles in moist air' }
    ],
    sources: [
      { name: 'Coal Power Generation', pct: 62, color: '#475569' },
      { name: 'Industrial Boilers & Kilns', pct: 22, color: '#f97316' },
      { name: 'Heavy Diesel Fleet', pct: 10, color: '#ef4444' },
      { name: 'Refineries', pct: 6, color: '#cbd5e1' }
    ],
    healthImpact: [
      { disease: 'Acute Bronchoconstriction', pct: 45, color: '#ef4444' },
      { disease: 'Mucosal Eye & Throat Irritation', pct: 25, color: '#f97316' },
      { disease: 'Chronic Bronchitis Complications', pct: 20, color: '#eab308' },
      { disease: 'Cardiovascular Stress', pct: 10, color: '#3b82f6' }
    ],
    envEffects: [
      { icon: '🌧️', label: 'Acid Rain Formation', desc: 'Causes forest dieback & water acidification' },
      { icon: '🏛️', label: 'Stone Corrosion', desc: 'Erodes marble & limestone heritage monuments' }
    ]
  },
  co: {
    id: 'co', name: 'CO', formula: 'CO', fullName: 'Carbon Monoxide',
    unit: 'mg/m³', whoLimit: 4, naaqs: 4,
    description: 'Colorless, odorless toxic gas formed from incomplete combustion of carbon-based fuels. Inhibits oxygen delivery to bodily organs.',
    size: 'Molecular gas',
    facts: [
      { icon: '👻', text: 'Completely imperceptible to human senses' },
      { icon: '🩸', text: 'Binds to hemoglobin 200x stronger than oxygen' },
      { icon: '🚗', text: 'Highest near traffic intersections & idling engines' }
    ],
    sources: [
      { name: 'Vehicular Exhaust', pct: 68, color: '#ef4444' },
      { name: 'Biomass Burning', pct: 18, color: '#f97316' },
      { name: 'Industrial Waste Combustion', pct: 9, color: '#eab308' },
      { name: 'Other', pct: 5, color: '#cbd5e1' }
    ],
    healthImpact: [
      { disease: 'Arterial Oxygen Deprivation (Hypoxia)', pct: 40, color: '#ef4444' },
      { disease: 'Myocardial Ischemia & Chest Pain', pct: 30, color: '#f97316' },
      { disease: 'Central Nervous System Dizziness', pct: 20, color: '#eab308' },
      { disease: 'Impaired Visual & Cognitive Alertness', pct: 10, color: '#3b82f6' }
    ],
    envEffects: [
      { icon: '🌡️', label: 'Indirect Greenhouse Impact', desc: 'Elevates methane & tropospheric ozone' }
    ]
  },
  o3: {
    id: 'o3', name: 'Ozone', formula: 'O₃', fullName: 'Ground-Level Ozone',
    unit: 'µg/m³', whoLimit: 100, naaqs: 100,
    description: 'Secondary photochemical pollutant created when nitrogen oxides (NOx) and volatile organic compounds (VOCs) react under intense sunlight.',
    size: 'Molecular gas',
    facts: [
      { icon: '☀️', text: 'Requires intense solar radiation (peaks 1:00-4:00 PM)' },
      { icon: '🧪', text: 'Not emitted directly; formed via atmospheric photolysis' },
      { icon: '🔥', text: 'Major component of summer photochemical smog' }
    ],
    sources: [
      { name: 'Vehicular NOx Photolysis', pct: 48, color: '#ef4444' },
      { name: 'Industrial VOC Solvents', pct: 26, color: '#f97316' },
      { name: 'Power Plant Precursors', pct: 16, color: '#eab308' },
      { name: 'Refinery Fuel Vapors', pct: 10, color: '#cbd5e1' }
    ],
    healthImpact: [
      { disease: 'Airway Inflammatory Scarring', pct: 36, color: '#ef4444' },
      { disease: 'Reduced Lung Vital Capacity', pct: 30, color: '#f97316' },
      { disease: 'Severe Asthma Attacks', pct: 22, color: '#eab308' },
      { disease: 'Cardiopulmonary Mortality', pct: 12, color: '#3b82f6' }
    ],
    envEffects: [
      { icon: '🌾', label: 'Agricultural Crop Yield Reduction', desc: 'Damages wheat, rice & soybean foliage' },
      { icon: '🌳', label: 'Forest Foliage Bleaching', desc: 'Stunts tree canopy growth' }
    ]
  }
};

// Global App State
const state = {
  selectedStation: 'ALL',
  selectedPollutant: 'pm25',
  chartTrend: null
};

document.addEventListener('DOMContentLoaded', () => {
  try {
    checkFallbackBanner();
    initLocationDropdown();
    initPollutantSelector();
    updateDashboard(true);
  } catch (err) {
    console.error("Pollutants App initialization error caught gracefully:", err);
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

// Pollutant Selector Buttons (PM2.5, PM10, NO2, SO2, CO, O3)
function initPollutantSelector() {
  const container = document.getElementById('pollutant-selector');
  if (!container) return;

  container.innerHTML = '';
  Object.keys(POLLUTANT_INFO).forEach(key => {
    const pol = POLLUTANT_INFO[key];
    const btn = document.createElement('button');
    btn.className = `pol-pill ${key === state.selectedPollutant ? 'active' : ''}`;
    btn.dataset.pollutant = key;
    btn.textContent = pol.name;

    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.pol-pill').forEach(b => b.classList.remove('active'));
      e.currentTarget.classList.add('active');
      state.selectedPollutant = key;
      updateDashboard();
    });

    container.appendChild(btn);
  });
}

// Update Master Pollutant Dashboard
function updateDashboard() {
  try {
    const st = DataHandler.getStation(state.selectedStation);
    if (!st) return;

    const polKey = state.selectedPollutant;
    const info = POLLUTANT_INFO[polKey] || POLLUTANT_INFO.pm25;

    // Header values
    document.getElementById('pol-name').textContent = info.name;
    document.getElementById('pol-formula').textContent = info.formula;
    document.getElementById('pol-fullname').textContent = info.fullName;

    // Current concentration value
    let curVal = 0;
    if (st.stats && st.stats[polKey]) {
      curVal = DataHandler.safeGet(st.stats[polKey], 'latest', 30);
    } else {
      curVal = DataHandler.safeGet(st.stats, 'pm25.latest', 35);
    }

    if (typeof curVal === 'number') {
      curVal = Math.round(curVal * 10) / 10;
    }

    document.getElementById('pol-current-val').textContent = curVal;
    document.getElementById('pol-unit').textContent = info.unit;

    // AQI / Severity Badge
    const band = DataHandler.getAQIBand(polKey === 'pm25' ? curVal * 1.4 : curVal);
    const badge = document.getElementById('pol-severity-badge');
    document.getElementById('pol-severity-text').textContent = band.name;
    badge.style.backgroundColor = band.color;
    badge.style.color = band.textCol;

    // WHO Limit Comparison Ratio Card (Matching Reference Image 2)
    const limit = info.whoLimit;
    const ratio = (typeof curVal === 'number') ? (Math.round((curVal / limit) * 10) / 10) : 1.0;
    const whoBadge = document.getElementById('who-ratio-badge');
    const whoHeadline = document.getElementById('who-headline-text');
    const whoDetail = document.getElementById('who-detail-text');

    if (ratio > 1.0) {
      whoBadge.className = 'bg-red-500 text-white p-3 rounded-xl text-center min-w-[95px] flex-shrink-0';
      whoBadge.innerHTML = `<span class="text-base font-extrabold font-mono block leading-tight">${ratio}x</span><span class="text-[10px] font-bold uppercase tracking-wider block opacity-90">Above</span>`;
      whoHeadline.textContent = `${ratio}x Above WHO Guideline`;
      whoDetail.textContent = `Current concentration of ${curVal} ${info.unit} is ${ratio}x higher than the recommended WHO threshold of ${limit} ${info.unit}.`;
    } else {
      whoBadge.className = 'bg-emerald-500 text-white p-3 rounded-xl text-center min-w-[95px] flex-shrink-0';
      whoBadge.innerHTML = `<span class="text-base font-extrabold font-mono block leading-tight">Within</span><span class="text-[10px] font-bold uppercase tracking-wider block opacity-90">Limit</span>`;
      whoHeadline.textContent = `Within WHO Guideline Limit`;
      whoDetail.textContent = `Current level of ${curVal} ${info.unit} satisfies the WHO ambient safety recommendation of ${limit} ${info.unit}.`;
    }

    // Limit Bar Fill & Pointer
    const maxScale = info.naaqs * 2;
    const pct = (typeof curVal === 'number') ? Math.min(Math.max((curVal / maxScale) * 100, 2), 98) : 20;
    document.getElementById('pol-bar-fill').style.width = `${pct}%`;

    // Position WHO & NAAQS markers
    const whoPct = Math.min((info.whoLimit / maxScale) * 100, 90);
    const naaqsPct = Math.min((info.naaqs / maxScale) * 100, 95);
    document.getElementById('marker-who').style.left = `${whoPct}%`;
    document.getElementById('marker-naaqs').style.left = `${naaqsPct}%`;

    // Description & Facts
    document.getElementById('pol-description').textContent = info.description;
    const factsGrid = document.getElementById('pol-facts-grid');
    factsGrid.innerHTML = '';
    info.facts.forEach(f => {
      const d = document.createElement('div');
      d.className = 'bg-slate-50 border border-slate-200 p-2.5 rounded-lg flex items-center gap-2';
      d.innerHTML = `<span class="text-base">${f.icon}</span><span class="text-slate-700 font-medium">${f.text}</span>`;
      factsGrid.appendChild(d);
    });

    // Sources Stacked Bar & Legend
    const stackedBar = document.getElementById('sources-stacked-bar');
    const sourcesLegend = document.getElementById('sources-legend');
    stackedBar.innerHTML = '';
    sourcesLegend.innerHTML = '';

    info.sources.forEach(src => {
      const seg = document.createElement('div');
      seg.style.width = `${src.pct}%`;
      seg.style.backgroundColor = src.color;
      stackedBar.appendChild(seg);

      const leg = document.createElement('div');
      leg.className = 'flex items-center gap-2';
      leg.innerHTML = `
        <span class="w-3 h-3 rounded-full flex-shrink-0" style="background-color: ${src.color}"></span>
        <span class="text-slate-700 truncate">${src.name}</span>
        <span class="font-bold font-mono text-slate-900 ml-auto">${src.pct}%</span>
      `;
      sourcesLegend.appendChild(leg);
    });

    // Disease Mortality Impact Bars (Matching Reference Image 3)
    const diseaseContainer = document.getElementById('health-disease-bars');
    diseaseContainer.innerHTML = '';
    info.healthImpact.forEach(hi => {
      const dRow = document.createElement('div');
      dRow.className = 'space-y-1';
      dRow.innerHTML = `
        <div class="flex justify-between text-xs font-semibold text-slate-700">
          <span>${hi.disease}</span>
          <span class="font-mono font-bold text-slate-900">${hi.pct}%</span>
        </div>
        <div class="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
          <div class="h-full rounded-full" style="width: ${hi.pct}%; background-color: ${hi.color}"></div>
        </div>
      `;
      diseaseContainer.appendChild(dRow);
    });

    // Environmental Effects Grid
    const envGrid = document.getElementById('env-effects-grid');
    envGrid.innerHTML = '';
    info.envEffects.forEach(ee => {
      const item = document.createElement('div');
      item.className = 'bg-slate-50 border border-slate-200 p-2.5 rounded-lg flex items-center gap-3';
      item.innerHTML = `
        <span class="text-xl">${ee.icon}</span>
        <div>
          <h5 class="text-xs font-bold text-slate-800">${ee.label}</h5>
          <p class="text-[11px] text-slate-500">${ee.desc}</p>
        </div>
      `;
      envGrid.appendChild(item);
    });

    // All Pollutants Overview Cards
    renderComparisonCards(st);

    // Trend Chart
    renderTrendChart(st, polKey);

  } catch (err) {
    console.error("Error updating Pollutants Dashboard UI caught gracefully:", err);
  }
}

// Render Comparison Cards for All Pollutants
function renderComparisonCards(st) {
  const container = document.getElementById('comparison-cards');
  if (!container) return;

  container.innerHTML = '';
  const pollKeys = ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3'];

  pollKeys.forEach(k => {
    const info = POLLUTANT_INFO[k];
    const val = st.stats && st.stats[k] ? st.stats[k].latest : '--';
    const band = (typeof val === 'number') ? DataHandler.getAQIBand(k === 'pm25' ? val * 1.4 : val) : { name: '--', color: '#cbd5e1', textCol: '#334155' };

    const card = document.createElement('div');
    card.className = `bg-white border ${k === state.selectedPollutant ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-slate-200'} rounded-xl p-4 cursor-pointer transition-all hover:border-slate-300`;
    card.innerHTML = `
      <div class="flex justify-between items-center mb-2">
        <span class="font-bold text-sm text-slate-800 font-mono">${info.name}</span>
        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" style="background-color: ${band.color}; color: ${band.textCol};">${band.name}</span>
      </div>
      <div class="flex items-baseline gap-1">
        <span class="text-2xl font-extrabold font-mono text-slate-900">${val}</span>
        <span class="text-xs text-slate-500">${info.unit}</span>
      </div>
    `;

    card.addEventListener('click', () => {
      state.selectedPollutant = k;
      document.querySelectorAll('.pol-pill').forEach(b => {
        b.classList.toggle('active', b.dataset.pollutant === k);
      });
      updateDashboard();
    });

    container.appendChild(card);
  });
}

// Render 7-Day Pollutant Trend Line Chart
function renderTrendChart(st, polKey) {
  const ctx = document.getElementById('trendChart')?.getContext('2d');
  if (!ctx) return;

  const info = POLLUTANT_INFO[polKey] || POLLUTANT_INFO.pm25;
  let values = [];

  if (st.pollutants && st.pollutants[polKey] && Array.isArray(st.pollutants[polKey].values)) {
    values = st.pollutants[polKey].values;
  } else {
    values = Array(168).fill(st.stats[polKey]?.latest || 30);
  }

  // Sample points (every 3h)
  const sampledLabels = [];
  const sampledVals = [];
  for (let i = 0; i < values.length; i += 3) {
    sampledLabels.push(`T-${168 - i}h`);
    sampledVals.push(values[i]);
  }

  if (state.chartTrend) {
    state.chartTrend.destroy();
  }

  state.chartTrend = new Chart(ctx, {
    type: 'line',
    data: {
      labels: sampledLabels,
      datasets: [{
        label: `${info.name} (${info.unit})`,
        data: sampledVals,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
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
        legend: { display: false },
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
