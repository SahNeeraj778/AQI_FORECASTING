

import React, { useEffect, useMemo, useState } from 'https://esm.sh/react@18.3.1';
import { createRoot } from 'https://esm.sh/react-dom@18.3.1/client';

const h = React.createElement;
const pollutantInfo = {
  aqi: { label: 'AQI', icon: '◌', source: 'A summary index', human: 'Use the colour band as an at-a-glance guide for outdoor activity.', environment: 'It combines the effect of the monitored pollutants.', scale: 500, unit: '' },
  pm25: { label: 'PM2.5', icon: '··', source: 'Fine particles from traffic, construction, combustion and dust.', human: 'Small enough to reach deep into the lungs and enter the bloodstream.', environment: 'Creates haze and settles on soil, water and vegetation.', scale: 120, unit: 'µg/m³' },
  pm10: { label: 'PM10', icon: '⠿', source: 'Coarse dust from roads, construction, industry and pollen.', human: 'Can irritate the eyes, nose, throat and airways.', environment: 'Reduces visibility and deposits dust on plants and surfaces.', scale: 180, unit: 'µg/m³' },
  no2: { label: 'NO₂', icon: 'N', source: 'A gas produced mainly by vehicle engines and fuel burning.', human: 'Irritates airways and can make asthma symptoms worse.', environment: 'Helps form ground-level ozone and particle pollution.', scale: 100, unit: 'µg/m³' },
  so2: { label: 'SO₂', icon: 'S', source: 'A gas released when sulphur-containing fuels are burned.', human: 'Can trigger breathing difficulty, especially for people with asthma.', environment: 'Contributes to acid rain and particle formation.', scale: 80, unit: 'µg/m³' },
  co: { label: 'CO', icon: 'C', source: 'A colourless gas from incomplete combustion, often vehicle exhaust.', human: 'Reduces the amount of oxygen that blood can carry.', environment: 'Supports ground-level ozone formation.', scale: 4, unit: 'mg/m³' },
  o3: { label: 'O₃', icon: 'O', source: 'A secondary pollutant formed when sunlight reacts with other emissions.', human: 'Can cause coughing, throat irritation and reduced lung function.', environment: 'Damages leaves and lowers crop yields.', scale: 100, unit: 'µg/m³' }
};
const weather = [
  ['temperature_2m', 'Temperature', '°C', '☀'], ['relative_humidity_2m', 'Humidity', '%', '◒'],
  ['wind_speed_10m', 'Wind', 'km/h', '⌁'], ['surface_pressure', 'Pressure', 'hPa', '◍'], ['precipitation', 'Rain', 'mm', '☂']
];
const fmt = (value, digits = 0) => value == null ? '—' : Number(value).toFixed(digits);
const niceStation = (name) => name.replace(/,?\s*(Delhi|New Delhi|India|DPCC|CPCB|HSPCB|UPPCB|IITM|IMD).*/gi, '').replace(/[-_]/g, ' ').trim() || name;
function band(aqi) {
  if (aqi <= 50) return { name: 'Good', color: '#57c77d', action: 'Enjoy normal outdoor activity.' };
  if (aqi <= 100) return { name: 'Satisfactory', color: '#e9c85d', action: 'Most people can continue normal activity.' };
  if (aqi <= 200) return { name: 'Moderate', color: '#f39b45', action: 'Sensitive groups should reduce prolonged outdoor exertion.' };
  if (aqi <= 300) return { name: 'Poor', color: '#ec6b59', action: 'Limit long or intense outdoor activity.' };
  if (aqi <= 400) return { name: 'Very Poor', color: '#cf5575', action: 'Avoid outdoor exertion; keep windows closed if possible.' };
  return { name: 'Severe', color: '#8e4e77', action: 'Stay indoors and avoid outdoor activity.' };
}
function shortTime(value) { return new Intl.DateTimeFormat('en-IN', { hour: 'numeric', hour12: true }).format(new Date(value)); }
function LineChart({ values, timestamps, color, unit, forecast }) {
  const points = values.slice(-30); const times = timestamps.slice(-30); const max = Math.max(...points, forecast || 0) * 1.15 || 1; const min = Math.min(...points) * .8;
  const coords = points.map((v, i) => `${(i / Math.max(points.length - 1, 1)) * 100},${92 - ((v - min) / Math.max(max - min, 1)) * 76}`).join(' ');
  return h('div', { className: 'chart-wrap' },
    h('div', { className: 'chart-key' }, h('span', { className: 'line-key', style: { background: color } }), 'Observed', h('span', { className: 'dash-key' }), 'Forecast'),
    h('svg', { viewBox: '0 0 100 100', preserveAspectRatio: 'none', className: 'trend-chart', role: 'img', 'aria-label': `Recent ${unit} trend` },
      [25, 50, 75].map(y => h('line', { key: y, x1: 0, x2: 100, y1: y, y2: y, className: 'gridline' })),
      h('polyline', { points: coords, fill: 'none', stroke: color, strokeWidth: '1.5', vectorEffect: 'non-scaling-stroke' }),
      forecast != null && h('line', { x1: 97, x2: 100, y1: coords.split(' ').at(-1).split(',')[1], y2: 92 - ((forecast - min) / Math.max(max - min, 1)) * 76, stroke: '#f3b96b', strokeWidth: '1.5', strokeDasharray: '4 3', vectorEffect: 'non-scaling-stroke' })
    ),
    h('div', { className: 'chart-times' }, h('span', null, shortTime(times[0])), h('span', null, 'Now'))
  );
}
function buildAtmosphereScenario(stats) {
  const pm25 = stats.pm25.latest, wind = stats.wind_speed_10m.latest, humidity = stats.relative_humidity_2m.latest;
  const pbl = Math.max(180, Math.round(1120 - humidity * 5 - pm25 * 5 + wind * 23));
  const inversion = Math.min(96, Math.max(14, Math.round(82 - wind * 3 + humidity / 6 + pm25 / 8)));
  const dispersion = Math.min(95, Math.max(8, Math.round(wind * 7 + pbl / 22)));
  return { pbl, inversion, dispersion, plume: Math.round(24 + pm25 / 3 + wind * 2), windTo: (stats.wind_direction_10m.latest + 180) % 360 };
}
function AppHeader({ page, setPage, stationIndex, setStationIndex, stations, station }) {
  return h('header', { className: 'topbar atmosphere-topbar' },
    h('a', { className: 'brand', href: '#' }, h('span', { className: 'brand-dot' }), 'aeroflow'),
    h('nav', { className: 'page-tabs', 'aria-label': 'Dashboard views' },
      h('button', { className: page === 'forecast' ? 'active' : '', onClick: () => setPage('forecast') }, 'Forecast'),
      h('button', { className: page === 'atmosphere' ? 'active' : '', onClick: () => setPage('atmosphere') }, 'Atmosphere')
    ),
    h('label', { className: 'header-location' }, h('span', null, 'Select location'), h('select', { value: stationIndex, onChange: e => setStationIndex(Number(e.target.value)) }, stations.map((s, i) => h('option', { value: i, key: s.station }, niceStation(s.station)))))
  );
}
function AtmospherePage({ station }) {
  const stats = station.stats, scene = buildAtmosphereScenario(stats), status = band(stats.aqi.latest);
  const warnings = [
    [scene.inversion > 65, scene.inversion > 65 ? 'Strong inversion may trap pollution near the surface.' : 'Inversion strength is currently moderate.'],
    [scene.dispersion < 45, scene.dispersion < 45 ? 'Poor dispersion conditions could raise particulate levels.' : 'Dispersion conditions support dilution.'],
    [false, 'Regional plume influence is possible under the current wind field.'],
    [false, 'Recheck as observations update.']
  ];
  return h('section', { className: 'atmosphere-page' }),
    h('div', { className: 'atmo-hero' }, h('p', { className: 'eyebrow' }, 'Atmospheric diagnostic workspace'), h('h1', null, 'Why the forecast is', h('br'), 'changing'), h('p', null, 'The coupled scenario explains how local meteorology changes transport and how particulate pollution can reinforce poor mixing.')),
    h('section', { className: 'inversion-banner' }, h('div', { className: 'inversion-glyph' }, '⇅'), h('div', null, h('p', { className: 'eyebrow' }, 'Atmospheric inversion'), h('h2', null, scene.inversion > 65 ? 'Strong trapping conditions' : 'Mixing conditions are present'), h('span', null, `${scene.inversion}/100 inversion strength · ${scene.pbl}m estimated mixing height`)), h('strong', null, scene.inversion > 65 ? 'PM2.5 accumulation expected' : 'Ventilation supports dispersion')),
    h('section', { className: 'atmo-grid' },
      h('article', { className: 'panel plume-panel' }, h('p', { className: 'eyebrow' }, 'Regional plume tracker'), h('h2', null, 'Stubble-burning influence'), h('div', { className: 'plume-scene' }, h('b', null, '♨'), h('i', null, '→  →  →'), h('span', null, 'Delhi NCR')), h('div', { className: 'plume-stats' }, h('div', null, h('small', null, 'WIND DIRECTION'), h('b', null, `${fmt(stats.wind_direction_10m.latest)}°`)), h('div', null, h('small', null, 'PLUME INFLUENCE'), h('b', null, `${scene.plume}%`)), h('div', null, h('small', null, 'EST. ARRIVAL'), h('b', null, '18–30 h'))), h('p', { className: 'scene-note' }, '✦ Fire source and estimated arrival are synthetic because the snapshot does not contain satellite fire detections.')),
      h('article', { className: 'panel loop-panel' }, h('p', { className: 'eyebrow' }, 'Two-way feedback'), h('h2', null, 'Coupled loop'), h('div', { className: 'coupled-loop' }, [['PM2.5', `${fmt(stats.pm25.latest, 1)} µg/m³`, 'pink'], ['PBL height', `${scene.pbl} m`, 'blue'], ['Pollution trapping', `${scene.inversion}/100`, 'orange'], ['AQI response', `${fmt(stats.aqi.latest)} ${status.name}`, 'purple']].map((item, index) => h(React.Fragment, { key: item[0] }, h('div', { className: `loop-node ${item[2]}` }, h('b', null, item[0]), h('small', null, item[1])), index < 3 && h('i', null, '↓'))))
    ),
    h('section', { className: 'atmo-grid atmo-bottom' },
      h('article', { className: 'warning-panel' }, h('div', null, h('p', { className: 'eyebrow' }, 'Early warnings'), h('h2', null, 'Actionable signals for the', h('br'), 'next 72 hours')), h('ul', null, warnings.map(([high, text]) => h('li', { key: text, className: high ? 'high' : '' }, high ? '↟ ' : '⌁ ', text)))),
      h('article', { className: 'health-panel' }, h('div', { className: 'health-icon' }, '♥'), h('div', null, h('p', { className: 'eyebrow' }, 'Health advisory'), h('h2', null, `${status.name} AQI`), h('p', null, status.action)))
    )
  );
}
function App() {
  const [snapshot, setSnapshot] = useState(null); const [stationIndex, setStationIndex] = useState(0); const [metric, setMetric] = useState('aqi'); const [page, setPage] = useState('forecast');
  useEffect(() => { fetch('./dashboard_snapshot.json').then(r => r.json()).then(setSnapshot).catch(() => setSnapshot({ error: true })); }, []);
  const station = snapshot?.stations?.[stationIndex];
  const available = useMemo(() => station ? ['aqi', ...Object.keys(station.pollutants).filter(k => k !== 'aqi')] : [], [station]);
  useEffect(() => { if (available.length && !available.includes(metric)) setMetric('aqi'); }, [available, metric]);
  if (!snapshot) return h('main', { className: 'loading' }, h('div', { className: 'pulse' }), h('p', null, 'Reading air quality signals…'));
  if (snapshot.error) return h('main', { className: 'loading' }, h('h1', null, 'Unable to load the dashboard data'), h('p', null, 'Run the site from a local server so it can read dashboard_snapshot.json.'));
  const stat = station.stats[metric]; const info = pollutantInfo[metric]; const latest = stat?.latest; const forecast = station.forecast?.[metric] || [];
  const sixHour = forecast.find(f => f.horizon_h === 6) || forecast[0]; const aqi = station.stats.aqi.latest; const aqiForecast = station.forecast?.aqi?.[0]?.value; const status = band(aqi); const history = metric === 'aqi' ? station.pollutants.aqi : station.pollutants[metric];
  const contribution = Math.min(100, (latest / info.scale) * 100); const rising = sixHour && sixHour.value > latest;
  if (page === 'atmosphere') return h('main', { className: 'shell' }, h(AppHeader, { page, setPage, stationIndex, setStationIndex, stations: snapshot.stations, station }), h(AtmospherePage, { station }), h('footer', null, h('span', { className: 'brand-dot' }), ' Aeroflow · observed snapshot + labelled synthetic coupled-model scenario signals'));
  return h('main', { className: 'shell' },
    h(AppHeader, { page, setPage, stationIndex, setStationIndex, stations: snapshot.stations, station }),
    h('section', { className: 'hero' }, h('div', null, h('p', { className: 'eyebrow' }, 'AQI prediction system'), h('h1', null, 'Know the air. Plan ahead.'), h('p', { className: 'subhead' }, 'Live station data, weather signals, and model forecasts for Delhi NCR.')),
      h('div', { className: 'location-summary' }, h('time', null, new Date(station.last_report).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })), h('span', null, 'Viewing ', niceStation(station.station)))),
    h('section', { className: 'overview-grid' },
      h('article', { className: 'aqi-card', style: { '--status': status.color } }, h('div', { className: 'card-label' }, h('span', { className: 'live-dot' }), ' CURRENT AQI'), h('div', { className: 'aqi-row' }, h('strong', null, fmt(aqi)), h('div', null, h('span', { className: 'pill', style: { background: status.color } }, status.name), h('p', null, 'at ', niceStation(station.station)))), h('div', { className: 'scale' }, [0, 50, 100, 200, 300, 400, 500].map((n, i) => h('span', { key: n, className: i === 6 ? 'last' : '', style: { width: `${i === 6 ? 0 : 20}%` } })), h('i', { style: { left: `${Math.min(aqi / 5, 100)}%` } })), h('div', { className: 'scale-numbers' }, h('span', null, 'Good'), h('span', null, 'Satisfactory'), h('span', null, 'Moderate'), h('span', null, 'Poor'), h('span', null, 'Severe'))),
      h('article', { className: 'forecast-card' }, h('div', { className: 'card-label' }, '◔  MODEL FORECAST'), h('h2', null, aqiForecast ? fmt(aqiForecast) : '—', h('small', null, ' AQI in 6 hours')), h('p', { className: rising ? 'rise' : 'fall' }, rising ? '↗ ' : '↘ ', sixHour ? `${fmt(Math.abs(sixHour.value - latest), 1)} ${info.unit} ${rising ? 'higher' : 'lower'} ${metric === 'aqi' ? '' : info.label}` : 'Forecast unavailable'), h('div', { className: 'forecast-note' }, aqiForecast > 100 ? '⚠ Above the alert threshold of 100 AQI' : '✓ Within the AQI alert threshold')),
      h('article', { className: 'weather-card' }, h('div', { className: 'card-label' }, '☁  WEATHER NOW'), h('div', { className: 'weather-now' }, h('span', null, '☀'), h('strong', null, `${fmt(station.stats.temperature_2m.latest)}°`), h('p', null, 'Partly cloudy')), h('div', { className: 'weather-mini' }, weather.slice(1, 4).map(([key, label, unit, icon]) => h('span', { key }, h('b', null, icon, ' ', fmt(station.stats[key].latest, key === 'wind_speed_10m' ? 1 : 0)), h('small', null, unit, ' ', label)))))),
    h('section', { className: 'weather-section weather-before-pollution' }, h('div', { className: 'section-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'Conditions around the station'), h('h2', null, 'Weather signals')), h('p', null, 'Weather can disperse, trap, or transform pollution.')), h('div', { className: 'weather-grid' }, weather.map(([key, label, unit, icon]) => { const s = station.stats[key]; return h('article', { className: 'weather-tile', key }, h('span', null, icon), h('p', null, label), h('strong', null, fmt(s.latest, key === 'wind_speed_10m' ? 1 : 0), h('small', null, unit)), h('em', null, `Range ${fmt(s.min)}–${fmt(s.max)}`)); }))),
    h('section', { className: 'panel selector-panel' }, h('div', { className: 'section-heading' }, h('div', null, h('p', { className: 'eyebrow' }, 'Explore pollution'), h('h2', null, 'Select one signal')), h('p', null, 'Choose a pollutant to reveal its current level, outlook, sources and effects.')),
      h('nav', { className: 'metric-tabs', 'aria-label': 'Pollutant selection' }, available.map(key => h('button', { key, className: metric === key ? 'active' : '', onClick: () => setMetric(key) }, h('b', null, pollutantInfo[key].icon), pollutantInfo[key].label)))),
    h('section', { className: 'detail-grid' },
      h('article', { className: 'panel metric-detail' }, h('div', { className: 'metric-title' }, h('span', { className: 'metric-icon' }, info.icon), h('div', null, h('p', { className: 'eyebrow' }, 'CURRENT LEVEL'), h('h2', null, info.label))), h('div', { className: 'value-block' }, h('strong', null, fmt(latest, latest < 10 ? 2 : 1)), h('span', null, info.unit)), h('div', { className: 'comparison' }, h('span', null, 'Relative level'), h('div', { className: 'meter' }, h('i', { style: { width: `${contribution}%`, background: status.color } })), h('b', null, `${fmt(contribution)}% of dashboard reference`)), h(LineChart, { values: history.values, timestamps: station.timestamps, color: status.color, unit: info.label, forecast: sixHour?.value })),
      h('article', { className: 'panel impact-detail' }, h('p', { className: 'eyebrow' }, 'AT A GLANCE'), h('h2', null, `What ${info.label} means`), h('div', { className: 'impact-list' }, h('div', null, h('span', { className: 'impact-icon source' }, '↗'), h('section', null, h('b', null, 'Where it comes from'), h('p', null, info.source))), h('div', null, h('span', { className: 'impact-icon human' }, '♥'), h('section', null, h('b', null, 'People'), h('p', null, info.human))), h('div', null, h('span', { className: 'impact-icon nature' }, '⌁'), h('section', null, h('b', null, 'Environment'), h('p', null, info.environment))))),
    h('footer', null, h('span', { className: 'brand-dot' }), ' Breathe Forecast · Data snapshot supplied by the prediction pipeline')
  ));
}
createRoot(document.getElementById('root')).render(h(App));
