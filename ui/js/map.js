let map;
let geojsonLayer;
let activeCountryLayer = null;
let activeCountryCodes = new Set();
let currentBaseZoom = 3.0;
let universityMarkers = [];
let isMapInteractive = false;

window.setMapInteractive = function(val) {
  isMapInteractive = val;
};

function initMap(initialZoom) {
  currentBaseZoom = initialZoom || 3.0;

  map = L.map("map", {
    center: [32.0, 15.0],
    zoom: currentBaseZoom,
    minZoom: 2.6,
    maxZoom: 14,
    zoomControl: false,
    attributionControl: false,
    maxBounds: [[-58, -180], [85, 180]],
    maxBoundsViscosity: 1.0
  });

  window.map = map;
  L.control.zoom({ position: "bottomright" }).addTo(map);

  if (window.pywebview && window.pywebview.api) {
    loadMapData();
  } else {
    window.addEventListener("pywebviewready", loadMapData);
  }
}

async function loadMapData() {
  try {
    const codes = await window.pywebview.api.get_active_countries();
    activeCountryCodes = new Set(codes || []);

    const rawGeoData = await window.pywebview.api.get_geojson_data();
    if (!rawGeoData) return;

    const filteredFeatures = rawGeoData.features.filter(f => {
      const code = f.properties.ISO_A3 || f.properties.iso_a3;
      const name = (f.properties.ADMIN || f.properties.name || "").toLowerCase();
      return code !== "ATA" && name !== "antarctica";
    });

    geojsonLayer = L.geoJSON({ ...rawGeoData, features: filteredFeatures }, {
      style: getCountryStyle,
      onEachFeature: (feature, layer) => {
        layer.on({
          mouseover: e => {
            if (!isMapInteractive) return;
            highlightCountry(e.target, feature);
          },
          mouseout: e => {
            if (!isMapInteractive) return;
            resetCountryHighlight(e.target, feature);
          },
          click: e => {
            if (!isMapInteractive) return;
            selectCountry(feature, e.target);
          }
        });
      }
    }).addTo(map);

    map.invalidateSize();
  } catch (err) {
    console.error("Map initialization error:", err);
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
    layer.setStyle({ fillColor: "#38bdf8", color: "#0369a1", weight: 1.8 });
  }
}

function resetCountryHighlight(layer, feature) {
  if (layer !== activeCountryLayer) {
    geojsonLayer.resetStyle(layer);
  }
}

function selectCountry(feature, layer, recordHistory = true) {
  activeCountryLayer = layer;

  map.fitBounds(layer.getBounds(), {
    paddingTopLeft: [460, 40],
    paddingBottomRight: [40, 40],
    duration: 1.2
  });

  const countryName = feature.properties.ADMIN || feature.properties.name;
  const countryCode = feature.properties.ISO_A3 || feature.properties.iso_a3;

  window.onCountrySelected(countryName, countryCode, recordHistory);
}

function resetToWorldView() {
  clearUniversityMarkers();
  activeCountryLayer = null;
  if (geojsonLayer) {
    geojsonLayer.eachLayer(l => geojsonLayer.resetStyle(l));
  }
  map.flyTo([32.0, 15.0], currentBaseZoom, { duration: 1.0 });
}

function clearUniversityMarkers() {
  universityMarkers.forEach(m => map.removeLayer(m));
  universityMarkers = [];
}

function renderUniversityPins(universities) {
  clearUniversityMarkers();

  universities.forEach(u => {
    if (u.latitude && u.longitude) {
      const pinIcon = L.divIcon({
        className: "custom-uni-pin",
        html: `<div class="uni-pin-glow" title="${u.name}"></div>`,
        iconSize: [16, 16]
      });

      const marker = L.marker([u.latitude, u.longitude], { icon: pinIcon }).addTo(map);
      marker.on("click", () => {
        if (!isMapInteractive) return;
        window.onUniversitySelected(u);
      });
      universityMarkers.push(marker);
    }
  });
}

function focusUniversityPin(lat, lng) {
  if (lat && lng) {
    map.flyTo([lat, lng], 8, { duration: 1.2, paddingBottomRight: [100, 0] });
  }
}

function markCountryActive(countryCode) {
  activeCountryCodes.add(countryCode);
  if (geojsonLayer) geojsonLayer.setStyle(getCountryStyle);
}

window.setInitialZoom = function(zoom) {
  currentBaseZoom = zoom;
};