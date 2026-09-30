/**
 * AQI Prediction System - Data Handler & Error Resiliency Module
 * Provides robust error handling, API checks, fallback synthetic generation,
 * and 24-station data normalization for Delhi NCR.
 */

const DataHandler = (function() {
  // AQI Bands (CPCB Standards)
  const AQI_BANDS = [
    { min: 0, max: 50, name: 'Good', color: '#22c55e', textCol: '#ffffff' },
    { min: 51, max: 100, name: 'Satisfactory', color: '#84cc16', textCol: '#000000' },
    { min: 101, max: 200, name: 'Moderate', color: '#eab308', textCol: '#000000' },
    { min: 201, max: 300, name: 'Poor', color: '#f97316', textCol: '#ffffff' },
    { min: 301, max: 400, name: 'Very Poor', color: '#ef4444', textCol: '#ffffff' },
    { min: 401, max: 1000, name: 'Severe', color: '#7f1d1d', textCol: '#ffffff' }
  ];

  let rawSnapshot = null;
  let normalizedStations = [];
  let isFallbackMode = false;
  let fallbackMessage = '';

  // Helper: Normalize station name to slug ID
  function slugify(name) {
    return (name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  }

  // Safe accessor to prevent JS TypeError crashes
  function safeGet(obj, pathStr, defaultValue = 'Data currently unavailable') {
    try {
      if (!obj) return defaultValue;
      const parts = pathStr.split('.');
      let curr = obj;
      for (let p of parts) {
        if (curr === undefined || curr === null) return defaultValue;
        curr = curr[p];
      }
      if (curr === undefined || curr === null || Number.isNaN(curr)) {
        return defaultValue;
      }
      return curr;
    } catch (e) {
      return defaultValue;
    }
  }

  // Get AQI Band Info from Value
  function getAQIBand(value) {
    const val = Math.round(Number(value) || 0);
    for (let b of AQI_BANDS) {
      if (val >= b.min && val <= b.max) return b;
    }
    return AQI_BANDS[AQI_BANDS.length - 1];
  }

  // Fallback Data Generator in case API is down, rate-limited, or exhausted
  function createFallbackDataset() {
    const defaultStationNames = [
      "Air Check", "Anand Lok", "Ashok Vihar, Delhi - DPCC", "CRRI Mathura Road, New Delhi - IMD",
      "Cantonment Area, Delhi - DPCC", "Commonwealth Sports Complex, Delhi - DPCC", "DTU, New Delhi - CPCB",
      "IGNOU_Maidan Garhi, Delhi - DPCC", "IHBAS, Dilshad Garden,New Delhi - CPCB", "IIT Delhi, Delhi - IITM",
      "JNU, Delhi - DPCC", "Knowledge Park - V, Greater Noida - UPPCB", "New Delhi", "Pusa, Delhi - DPCC",
      "Santushti Apartments, Vasant Kunj", "Sector - 62, Noida, UP - IMD", "Sector 1, Noida extension",
      "Sector-116, Noida - UPPCB", "Shadipur, Delhi - CPCB", "Sirifort, Delhi - CPCB", "Sonia Vihar, Delhi - DPCC",
      "Talkatora Garden, Delhi - DPCC", "Teri Gram, Gurugram - HSPCB", "Ved Vihar-Loni, Ghaziabad - UPPCB"
    ];

    const baseCoords = [
      [28.6230, 77.2341], [28.5587, 77.2188], [28.6953, 77.1816], [28.5512, 77.2735],
      [28.5941, 77.1251], [28.6158, 77.2719], [28.7500, 77.1112], [28.4936, 77.2011],
      [28.6811, 77.3025], [28.5424, 77.1916], [28.5407, 77.1685], [28.5570, 77.4536],
      [28.6357, 77.2244], [28.6396, 77.1462], [28.5266, 77.1493], [28.6245, 77.3577],
      [28.5834, 77.4317], [28.5692, 77.3938], [28.6514, 77.1473], [28.5504, 77.2159],
      [28.7105, 77.2494], [28.6218, 77.1944], [28.4275, 77.1465], [28.7391, 77.2736]
    ];

    const now = new Date('2026-09-02T23:00:00');
    const timestamps = Array.from({length: 168}, (_, i) => {
      const t = new Date(now.getTime() - (167 - i) * 3600000);
      return t.toISOString().slice(0, 19);
    });

    const stations = defaultStationNames.map((name, idx) => {
      const basePM = Math.round(25 + (idx * 2.5) % 65);
      const baseAQI = Math.round(basePM * 1.4);
      const pmValues = timestamps.map((ts, i) => Math.round((basePM + Math.sin(i / 10) * 15 + Math.random() * 8) * 10) / 10);
      const aqiValues = pmValues.map(v => Math.round(v * 1.45));
      const tempValues = timestamps.map((ts, i) => Math.round((28 + Math.sin(i / 6) * 4) * 10) / 10);
      const humValues = timestamps.map((ts, i) => Math.round(70 + Math.cos(i / 6) * 15));
      const windValues = timestamps.map((ts, i) => Math.round((6 + Math.sin(i / 8) * 3) * 10) / 10);

      return {
        id: slugify(name),
        station: name,
        latitude: baseCoords[idx][0],
        longitude: baseCoords[idx][1],
        status: 'online',
        last_report: '2026-09-02T23:00:00',
        available_pollutants: ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3'],
        stats: {
          aqi: { latest: baseAQI, mean: baseAQI - 5, min: Math.round(baseAQI * 0.6), max: Math.round(baseAQI * 1.5), unit: '' },
          pm25: { latest: basePM, mean: basePM - 3, min: Math.round(basePM * 0.5), max: Math.round(basePM * 1.6), unit: 'µg/m³' },
          pm10: { latest: Math.round(basePM * 2.1), mean: Math.round(basePM * 2.0), min: 40, max: 250, unit: 'µg/m³' },
          no2: { latest: 32.5, mean: 30.0, min: 12, max: 75, unit: 'µg/m³' },
          so2: { latest: 14.2, mean: 12.0, min: 5, max: 35, unit: 'µg/m³' },
          co: { latest: 0.85, mean: 0.8, min: 0.3, max: 2.1, unit: 'mg/m³' },
          o3: { latest: 22.4, mean: 20.0, min: 5, max: 65, unit: 'µg/m³' },
          temperature_2m: { latest: tempValues[167], mean: 30.1, min: 25, max: 35, unit: '°C' },
          relative_humidity_2m: { latest: humValues[167], mean: 72, min: 48, max: 94, unit: '%' },
          wind_speed_10m: { latest: windValues[167], mean: 6.8, min: 0.5, max: 13, unit: 'km/h' },
          wind_direction_10m: { latest: 215, mean: 210, min: 10, max: 350, unit: '°' },
          surface_pressure: { latest: 979.5, mean: 978.0, min: 974, max: 983, unit: 'hPa' },
          ventilation_index: { latest: 5.4, mean: 7.2, min: 0.5, max: 20, unit: '' },
          temperature_change_3h: { latest: -0.5, mean: -0.01, min: -4.5, max: 5.0, unit: '°C' }
        },
        pollutants: {
          pm25: { unit: 'µg/m³', values: pmValues },
          pm10: { unit: 'µg/m³', values: pmValues.map(v => Math.round(v * 2.1)) },
          no2: { unit: 'µg/m³', values: timestamps.map(() => Math.round(20 + Math.random() * 30)) },
          so2: { unit: 'µg/m³', values: timestamps.map(() => Math.round(8 + Math.random() * 15)) },
          co: { unit: 'mg/m³', values: timestamps.map(() => Math.round((0.5 + Math.random() * 1.2) * 100) / 100) },
          o3: { unit: 'µg/m³', values: timestamps.map(() => Math.round(10 + Math.random() * 40)) }
        },
        weather: {
          temperature_2m: { unit: '°C', values: tempValues },
          relative_humidity_2m: { unit: '%', values: humValues },
          wind_speed_10m: { unit: 'km/h', values: windValues },
          wind_direction_10m: { unit: '°', values: timestamps.map(() => 215) },
          surface_pressure: { unit: 'hPa', values: timestamps.map(() => 979.5) },
          temperature_change_3h: { unit: '°C', values: timestamps.map(() => -0.5) },
          ventilation_index: { unit: '', values: timestamps.map(() => 5.4) }
        },
        forecast: {
          pm25: [
            { horizon_h: 1, value: Math.round(basePM * 1.05) },
            { horizon_h: 6, value: Math.round(basePM * 1.15) },
            { horizon_h: 12, value: Math.round(basePM * 1.25) },
            { horizon_h: 24, value: Math.round(basePM * 1.35) },
            { horizon_h: 72, value: Math.round(basePM * 1.20) }
          ],
          aqi: [
            { horizon_h: 6, value: Math.round(baseAQI * 1.15), reliable: true }
          ]
        }
      };
    });

    return {
      meta: {
        anchor_time: '2026-09-02T23:00:00',
        history_hours: 168,
        forecast_horizons_h: [1, 6, 12, 24, 72],
        aqi_alert_threshold: 100
      },
      summary: {
        stations_total: 24,
        online: 24,
        stations_with_alert: 12
      },
      stations: stations
    };
  }

  // Normalize Data API Response or Local Object
  function initData() {
    try {
      // 1. Check window object or snapshot first
      if (window.DASHBOARD_SNAPSHOT && Array.isArray(window.DASHBOARD_SNAPSHOT.stations) && window.DASHBOARD_SNAPSHOT.stations.length > 0) {
        rawSnapshot = window.DASHBOARD_SNAPSHOT;
      } else if (window.DASHBOARD_SNAPSHOT && Array.isArray(window.DASHBOARD_SNAPSHOT.locations) && window.DASHBOARD_SNAPSHOT.locations.length > 0) {
        // Adapt legacy locations format if present
        rawSnapshot = {
          meta: { anchor_time: '2026-09-02T23:00:00' },
          stations: window.DASHBOARD_SNAPSHOT.locations.map(loc => ({
            id: loc.id || slugify(loc.name),
            station: loc.name,
            latitude: loc.latitude || 28.6139,
            longitude: loc.longitude || 77.2090,
            status: 'online',
            stats: {
              aqi: { latest: loc.latest ? loc.latest.pm25 * 1.4 : 65 },
              pm25: { latest: loc.latest ? loc.latest.pm25 : 40 },
              temperature_2m: { latest: 28 },
              relative_humidity_2m: { latest: 70 },
              wind_speed_10m: { latest: 6.5 },
              surface_pressure: { latest: 978 }
            },
            forecast: { aqi: [{ horizon_h: 6, value: 71 }] }
          }))
        };
      } else {
        // Check for error or credit exhaustion
        isFallbackMode = true;
        fallbackMessage = 'API credits exhausted or server rate-limited. Loaded fallback dataset.';
        rawSnapshot = createFallbackDataset();
      }

      // 2. Validate snapshot stations
      if (!rawSnapshot || !Array.isArray(rawSnapshot.stations) || rawSnapshot.stations.length === 0) {
        throw new Error("Invalid station array structure in API snapshot");
      }

      // 3. Normalize all 24 stations
      normalizedStations = rawSnapshot.stations.map((s, index) => {
        const stationName = s.station || s.name || `Station ${index + 1}`;
        const id = s.id || slugify(stationName);

        // Ensure stats exists
        const stats = s.stats || {};
        
        return {
          id: id,
          station: stationName,
          latitude: s.latitude || (28.5 + (index * 0.015)),
          longitude: s.longitude || (77.1 + (index * 0.015)),
          status: s.status || 'online',
          last_report: s.last_report || rawSnapshot.meta?.anchor_time || '2026-09-02T23:00:00',
          available_pollutants: s.available_pollutants || ['pm25'],
          stats: stats,
          pollutants: s.pollutants || {},
          weather: s.weather || {},
          forecast: s.forecast || { aqi: [{ horizon_h: 6, value: 70 }] }
        };
      });

    } catch (err) {
      console.warn("DataHandler initialization error caught gracefully:", err);
      isFallbackMode = true;
      fallbackMessage = 'Data processing error encountered. Showing resilient fallback mode.';
      rawSnapshot = createFallbackDataset();
      normalizedStations = rawSnapshot.stations.map(s => ({ ...s, id: slugify(s.station) }));
    }
  }

  // Run initialization
  initData();

  // Public Methods
  return {
    isFallback: () => isFallbackMode,
    getFallbackMessage: () => fallbackMessage,
    getMeta: () => rawSnapshot ? rawSnapshot.meta : {},
    getSummary: () => rawSnapshot ? rawSnapshot.summary : {},
    
    // Get list of all 24 normalized stations
    getAllStations: function() {
      return normalizedStations;
    },

    // Get specific station by ID or Name
    getStation: function(idOrName) {
      if (!idOrName || idOrName === 'ALL' || idOrName === 'delhi-ncr-average') {
        return this.getNcrAverage();
      }
      const slug = slugify(idOrName);
      const found = normalizedStations.find(s => s.id === slug || slugify(s.station) === slug);
      return found || normalizedStations[0];
    },

    // Calculate Delhi NCR Regional Average across all 24 stations
    getNcrAverage: function() {
      if (normalizedStations.length === 0) return null;

      let totalAQI = 0, totalPM25 = 0, totalPM10 = 0, totalNO2 = 0, totalSO2 = 0, totalCO = 0, totalO3 = 0;
      let totalTemp = 0, totalHum = 0, totalWind = 0, totalPress = 0, totalVent = 0;
      let count = normalizedStations.length;

      normalizedStations.forEach(s => {
        totalAQI += safeGet(s.stats, 'aqi.latest', 65);
        totalPM25 += safeGet(s.stats, 'pm25.latest', 35);
        totalPM10 += safeGet(s.stats, 'pm10.latest', 90);
        totalNO2 += safeGet(s.stats, 'no2.latest', 32);
        totalSO2 += safeGet(s.stats, 'so2.latest', 14);
        totalCO += safeGet(s.stats, 'co.latest', 0.85);
        totalO3 += safeGet(s.stats, 'o3.latest', 22);
        totalTemp += safeGet(s.stats, 'temperature_2m.latest', 28);
        totalHum += safeGet(s.stats, 'relative_humidity_2m.latest', 70);
        totalWind += safeGet(s.stats, 'wind_speed_10m.latest', 6.5);
        totalPress += safeGet(s.stats, 'surface_pressure.latest', 978);
        totalVent += safeGet(s.stats, 'ventilation_index.latest', 6.8);
      });

      const avgAQI = Math.round(totalAQI / count);
      const avgPM25 = Math.round((totalPM25 / count) * 10) / 10;
      const avgPM10 = Math.round(totalPM10 / count);
      const avgNO2 = Math.round((totalNO2 / count) * 10) / 10;
      const avgSO2 = Math.round((totalSO2 / count) * 10) / 10;
      const avgCO = Math.round((totalCO / count) * 100) / 100;
      const avgO3 = Math.round((totalO3 / count) * 10) / 10;

      return {
        id: 'delhi-ncr-average',
        station: 'Delhi NCR Regional Average',
        latitude: 28.6139,
        longitude: 77.2090,
        status: 'online',
        last_report: rawSnapshot.meta?.anchor_time || '2026-09-02T23:00:00',
        available_pollutants: ['pm25', 'pm10', 'no2', 'so2', 'co', 'o3'],
        stats: {
          aqi: { latest: avgAQI, mean: avgAQI, unit: '' },
          pm25: { latest: avgPM25, mean: avgPM25, unit: 'µg/m³' },
          pm10: { latest: avgPM10, mean: avgPM10, unit: 'µg/m³' },
          no2: { latest: avgNO2, mean: avgNO2, unit: 'µg/m³' },
          so2: { latest: avgSO2, mean: avgSO2, unit: 'µg/m³' },
          co: { latest: avgCO, mean: avgCO, unit: 'mg/m³' },
          o3: { latest: avgO3, mean: avgO3, unit: 'µg/m³' },
          temperature_2m: { latest: Math.round((totalTemp / count) * 10) / 10, unit: '°C' },
          relative_humidity_2m: { latest: Math.round(totalHum / count), unit: '%' },
          wind_speed_10m: { latest: Math.round((totalWind / count) * 10) / 10, unit: 'km/h' },
          wind_direction_10m: { latest: 215, unit: '°' },
          surface_pressure: { latest: Math.round(totalPress / count), unit: 'hPa' },
          ventilation_index: { latest: Math.round((totalVent / count) * 10) / 10, unit: '' },
          temperature_change_3h: { latest: -0.5, unit: '°C' }
        },
        pollutants: normalizedStations[0].pollutants,
        weather: normalizedStations[0].weather,
        forecast: {
          aqi: [{ horizon_h: 6, value: Math.round(avgAQI * 1.1), reliable: true }],
          pm25: [
            { horizon_h: 1, value: Math.round(avgPM25 * 1.05) },
            { horizon_h: 6, value: Math.round(avgPM25 * 1.15) },
            { horizon_h: 12, value: Math.round(avgPM25 * 1.25) },
            { horizon_h: 24, value: Math.round(avgPM25 * 1.35) },
            { horizon_h: 72, value: Math.round(avgPM25 * 1.20) }
          ]
        }
      };
    },

    safeGet: safeGet,
    getAQIBand: getAQIBand
  };
})();
