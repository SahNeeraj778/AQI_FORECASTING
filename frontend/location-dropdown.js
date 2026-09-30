/**
 * Searchable Location Selector Component (Supports 24+ Locations)
 * Replaces cumbersome horizontal tabs with a clean, searchable dropdown menu.
 */

function renderSearchableLocationDropdown(containerId, onSelectCallback) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const stations = DataHandler.getAllStations();
  const currentStation = DataHandler.getStation(state ? state.selectedStation : 'ALL');

  container.className = 'location-dropdown-wrapper';
  container.innerHTML = `
    <button id="location-dropdown-btn" type="button" class="location-btn">
      <div class="loc-info">
        <i class="fa-solid fa-location-dot loc-icon"></i>
        <span id="selected-location-label" class="truncate">${currentStation ? currentStation.station : 'Delhi NCR Average'}</span>
      </div>
      <i class="fa-solid fa-chevron-down text-xs text-slate-400"></i>
    </button>
    
    <div id="location-dropdown-menu" class="location-menu">
      <div class="search-input-wrapper">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input type="text" id="location-search-input" class="location-search-input" placeholder="Search 24 locations...">
      </div>
      <div class="location-options-list" id="location-options-list">
        <!-- Station Options Injected Here -->
      </div>
    </div>
  `;

  const btn = document.getElementById('location-dropdown-btn');
  const menu = document.getElementById('location-dropdown-menu');
  const searchInput = document.getElementById('location-search-input');
  const optionsList = document.getElementById('location-options-list');

  // Toggle Dropdown Menu
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    menu.classList.toggle('open');
    if (menu.classList.contains('open')) {
      searchInput.focus();
    }
  });

  // Close when clicking outside
  document.addEventListener('click', (e) => {
    if (!container.contains(e.target)) {
      menu.classList.remove('open');
    }
  });

  // Filter stations based on search query
  function populateOptions(filterText = '') {
    optionsList.innerHTML = '';
    
    // Add Regional Average option first
    const avgOption = { id: 'ALL', station: 'Delhi NCR Regional Average (24 Stations)' };
    const allOptions = [avgOption, ...stations];

    const filtered = allOptions.filter(s => 
      s.station.toLowerCase().includes(filterText.toLowerCase())
    );

    if (filtered.length === 0) {
      optionsList.innerHTML = '<div class="p-3 text-xs text-slate-400 text-center">No locations found</div>';
      return;
    }

    filtered.forEach(st => {
      const isAvg = st.id === 'ALL';
      const aqiVal = isAvg 
        ? DataHandler.getNcrAverage()?.stats?.aqi?.latest 
        : (st.stats?.aqi?.latest || 65);
      
      const band = DataHandler.getAQIBand(aqiVal);
      const isSelected = state ? (state.selectedStation === st.id || (isAvg && state.selectedStation === 'ALL')) : false;

      const item = document.createElement('div');
      item.className = `location-option-item ${isSelected ? 'selected' : ''}`;
      item.innerHTML = `
        <span class="truncate">${st.station}</span>
        <span class="loc-badge" style="background-color: ${band.color}; color: ${band.textCol};">${Math.round(aqiVal)} ${band.name}</span>
      `;

      item.addEventListener('click', () => {
        document.getElementById('selected-location-label').textContent = st.station;
        menu.classList.remove('open');
        if (state) state.selectedStation = st.id;
        if (typeof onSelectCallback === 'function') {
          onSelectCallback(st.id);
        }
      });

      optionsList.appendChild(item);
    });
  }

  // Live Search Filter
  searchInput.addEventListener('input', (e) => {
    populateOptions(e.target.value);
  });

  // Initial population
  populateOptions();
}
