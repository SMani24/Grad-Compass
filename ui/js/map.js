let map;
let geojsonLayer;
let activeCountryLayer = null;
let activeCountryCodes = new Set();
let currentBaseZoom = 3.0;
let universityMarkers = [];
let isMapInteractive = false;

function extractCountryProps(feature) {
  return resolveCountryFeature(feature);
}

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
    activeCountryCodes = new Set((codes || []).map(c => c.toUpperCase()));

    const rawGeoData = await window.pywebview.api.get_geojson_data();
    if (!rawGeoData) return;

    const filteredFeatures = rawGeoData.features.filter(f => {
      const p = f.properties || {};
      const name = (p.ADMIN || p.name || "").toLowerCase();
      const code = (p.ISO_A3 || p.iso_a3 || f.id || "").toUpperCase();
      return code !== "ATA" && name !== "antarctica";
    });

    geojsonLayer = L.geoJSON({ ...rawGeoData, features: filteredFeatures }, {
      style: getCountryStyle,
      onEachFeature: (feature, layer) => {
        layer.on({
          mouseover: e => {
            if (!isMapInteractive) return;
            highlightCountry(e.target);
          },
          mouseout: e => {
            if (!isMapInteractive) return;
            resetCountryHighlight(e.target);
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
  const { code } = extractCountryProps(feature);
  const hasItems = activeCountryCodes.has(code);

  return {
    className: hasItems ? "country-polygon has-items" : "country-polygon",
    fillColor: hasItems ? "#bae6fd" : "#ffffff",
    fillOpacity: 1,
    weight: hasItems ? 1.4 : 0.75,
    color: hasItems ? "#0284c7" : "#cbd5e1"
  };
}

function highlightCountry(layer) {
  if (layer !== activeCountryLayer) {
    layer.setStyle({
      fillColor: "#38bdf8",
      color: "#0369a1",
      weight: 1.8
    });
  }
}

function resetCountryHighlight(layer) {
  if (layer !== activeCountryLayer) {
    geojsonLayer.resetStyle(layer);
  }
}

function selectCountry(feature, layer, recordHistory = true) {
  if (activeCountryLayer && geojsonLayer) {
    geojsonLayer.resetStyle(activeCountryLayer);
  }

  activeCountryLayer = layer;

  layer.setStyle({
    fillColor: "#7dd3fc",
    fillOpacity: 0.95,
    weight: 2.5,
    color: "#0284c7"
  });

  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    layer.bringToFront();
  }

  map.fitBounds(layer.getBounds(), {
    paddingTopLeft: [460, 40],
    paddingBottomRight: [40, 40],
    duration: 1.2
  });

  const { name, code, flag } = extractCountryProps(feature);
  window.onCountrySelected(name, code, flag, recordHistory);
}

function resetToWorldView() {
  clearUniversityMarkers();
  if (activeCountryLayer && geojsonLayer) {
    geojsonLayer.resetStyle(activeCountryLayer);
  }
  activeCountryLayer = null;
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
      let pinHtml = "";
      if (u.image_url) {
        pinHtml = `<div class="uni-photo-pin" style="background-image: url('${u.image_url}');" title="${u.name}"></div>`;
      } else {
        pinHtml = `<div class="uni-photo-pin" title="${u.name}"><span class="uni-pin-fallback-icon">🏛️</span></div>`;
      }

      const pinIcon = L.divIcon({
        className: "custom-uni-photo-marker",
        html: pinHtml,
        iconSize: [40, 46],
        iconAnchor: [20, 46],
        popupAnchor: [0, -44]
      });

      const marker = L.marker([u.latitude, u.longitude], { icon: pinIcon }).addTo(map);
      marker.bindTooltip(`<b>${u.name}</b>${u.city ? '<br>' + u.city : ''}`, { 
        direction: "top", 
        offset: [0, -42],
        opacity: 0.95
      });

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
  if (!countryCode) return;
  const upper = countryCode.toUpperCase();
  activeCountryCodes.add(upper);

  if (geojsonLayer) {
    geojsonLayer.eachLayer(layer => {
      const { code } = extractCountryProps(layer.feature);
      if (code === upper) {
        if (layer === activeCountryLayer) {
          layer.setStyle({
            fillColor: "#7dd3fc",
            fillOpacity: 0.95,
            weight: 2.5,
            color: "#0284c7"
          });
        } else {
          layer.setStyle(getCountryStyle(layer.feature));
        }
      }
    });
  }
}

window.setInitialZoom = function(zoom) {
  currentBaseZoom = zoom;
};