let map;
let geojsonLayer;
let activeCountryLayer = null;
let activeCountryCodes = new Set();

function initMap() {
  map = L.map("map", {
    center: [25.0, 10.0],
    zoom: 2.4,
    minZoom: 2,
    maxZoom: 9,
    zoomControl: false,
    attributionControl: false
  });

  // Expose to window so app.js can call invalidateSize()
  window.map = map;

  L.control.zoom({ position: "bottomright" }).addTo(map);

  // Initialize data once pywebview is bridged
  if (window.pywebview && window.pywebview.api) {
    loadMapData();
  } else {
    window.addEventListener("pywebviewready", loadMapData);
  }
}

async function loadMapData() {
  try {
    // 1. Get populated countries from SQLite
    const codes = await window.pywebview.api.get_active_countries();
    activeCountryCodes = new Set(codes || []);

    // 2. Get vector boundaries directly from Python backend
    const geoData = await window.pywebview.api.get_geojson_data();
    if (!geoData) {
      console.error("GeoJSON data returned empty from Python backend.");
      return;
    }

    geojsonLayer = L.geoJSON(geoData, {
      style: getCountryStyle,
      onEachFeature: (feature, layer) => {
        layer.on({
          mouseover: e => highlightCountry(e.target, feature),
          mouseout: e => resetCountryHighlight(e.target, feature),
          click: e => selectCountry(feature, e.target)
        });
      }
    }).addTo(map);

    map.invalidateSize();
  } catch (err) {
    console.error("Failed to load map data:", err);
  }
}

function getCountryStyle(feature) {
  const code = feature.properties.ISO_A3 || feature.properties.iso_a3;
  const hasItems = activeCountryCodes.has(code);

  return {
    className: hasItems ? "country-polygon has-items" : "country-polygon",
    fillColor: hasItems ? "#bae6fd" : "#ffffff",
    fillOpacity: 1,
    weight: hasItems ? 1.4 : 0.75,
    color: hasItems ? "#0284c7" : "#cbd5e1"
  };
}

function highlightCountry(layer, feature) {
  if (layer !== activeCountryLayer) {
    layer.setStyle({
      fillColor: "#38bdf8",
      color: "#0369a1",
      weight: 1.8
    });
  }
}

function resetCountryHighlight(layer, feature) {
  if (layer !== activeCountryLayer) {
    geojsonLayer.resetStyle(layer);
  }
}

function selectCountry(feature, layer) {
  activeCountryLayer = layer;

  map.fitBounds(layer.getBounds(), {
    paddingTopLeft: [440, 40],
    paddingBottomRight: [40, 40],
    duration: 1.2
  });

  const countryName = feature.properties.ADMIN || feature.properties.name;
  const countryCode = feature.properties.ISO_A3 || feature.properties.iso_a3;

  window.onCountrySelected(countryName, countryCode);
}

function resetToWorldView() {
  activeCountryLayer = null;
  if (geojsonLayer) {
    geojsonLayer.eachLayer(l => geojsonLayer.resetStyle(l));
  }
  map.flyTo([25.0, 10.0], 2.4, { duration: 1.0 });
}

document.addEventListener("DOMContentLoaded", initMap);