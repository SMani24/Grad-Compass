"use strict";

function hasCoordinates(university) {
  return typeof university.latitude === "number" && typeof university.longitude === "number"
    && Number.isFinite(university.latitude) && Number.isFinite(university.longitude)
    && Math.abs(university.latitude) <= 90 && Math.abs(university.longitude) <= 180;
}

function filterUniversities(universities, filters) {
  const query = (filters.search || "").trim().toLowerCase();
  return universities.filter(university => (!filters.country || university.country_code === filters.country)
    && (!filters.status || university.status === filters.status)
    && (!query || [university.name, university.city, university.country_code].some(value => String(value || "").toLowerCase().includes(query))));
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

function dominantLandmassBounds(feature) {
  const geometry = feature?.geometry;
  const polygons = geometry?.type === "Polygon" ? [geometry.coordinates]
    : geometry?.type === "MultiPolygon" ? geometry.coordinates : [];
  let largest = null;
  let largestArea = -1;
  for (const polygon of polygons) {
    const ring = polygon[0];
    if (!ring || ring.length < 4) continue;
    const points = [];
    for (const coordinate of ring) {
      let [longitude, latitude] = coordinate;
      if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) break;
      const previous = points.at(-1)?.[0];
      // Keep a dateline-crossing ring together rather than spanning the globe.
      if (previous !== undefined) {
        while (longitude - previous > 180) longitude -= 360;
        while (longitude - previous < -180) longitude += 360;
      }
      points.push([longitude, latitude]);
    }
    if (points.length !== ring.length) continue;
    let area = 0;
    for (let index = 0; index < points.length; index++) {
      const current = points[index];
      const next = points[(index + 1) % points.length];
      area += current[0] * next[1] - next[0] * current[1];
    }
    const south = Math.min(...points.map(point => point[1]));
    const north = Math.max(...points.map(point => point[1]));
    // Approximate geographic area so a polar island does not dominate by projection.
    area = Math.abs(area) * Math.cos((south + north) * Math.PI / 360);
    if (area > largestArea) {
      largestArea = area;
      largest = [[south, Math.min(...points.map(point => point[0]))],
        [north, Math.max(...points.map(point => point[0]))]];
    }
  }
  return largest;
}

if (typeof module !== "undefined") module.exports = { hasCoordinates, filterUniversities, safeExternalUrl, dominantLandmassBounds };

if (typeof document !== "undefined") {
  const get = id => document.getElementById(id);
  const state = { universities: [], filtered: [], selected: null, view: "map", geometry: null, map: null, polygons: null, markers: null, mapError: false, detailSequence: 0 };
  const elements = { search: get("search"), country: get("country"), status: get("status"), results: get("results"), inspector: get("inspector") };
  let navigationIndex = 0;
  let navigationEnd = 0;
  let editingSearch = false;

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function countryName(code) { return typeof BY_CODE !== "undefined" ? BY_CODE[code]?.name || code : code; }
  function countryFlag(code) { return typeof BY_CODE !== "undefined" ? BY_CODE[code]?.flag || "🌐" : "🌐"; }
  function stage(status) { return node("span", "stage" + (status === "Applying" ? " applying" : ""), status || "Researching"); }
  function deadline(value) {
    if (!value) return "Not set";
    const date = new Date(value + "T00:00:00");
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }
  async function api(route) {
    const response = await fetch(route, { cache: "no-store" });
    if (!response.ok) throw new Error("Could not load workspace");
    return response.json();
  }
  function updateNavigationButtons() {
    get("nav-back").disabled = navigationIndex === 0;
    get("nav-forward").disabled = navigationIndex === navigationEnd;
  }
  function updateUrl(replace = false) {
    const url = new URL(location.href);
    if (state.view === "list") url.searchParams.set("view", "list"); else url.searchParams.delete("view");
    if (state.selected) url.searchParams.set("university", state.selected); else url.searchParams.delete("university");
    for (const name of ["country", "status", "search"]) {
      if (elements[name].value) url.searchParams.set(name, elements[name].value); else url.searchParams.delete(name);
    }
    if (!replace && url.href === location.href) return;
    if (replace) history.replaceState({ gradCompassIndex: navigationIndex }, "", url);
    else {
      navigationIndex++;
      navigationEnd = navigationIndex;
      history.pushState({ gradCompassIndex: navigationIndex }, "", url);
    }
    updateNavigationButtons();
  }
  function setView(view, record = true) {
    state.view = view;
    document.querySelector(".workspace").classList.toggle("list-view", view === "list");
    get("map").hidden = view !== "map";
    get("map-key").hidden = view !== "map";
    get("map-message").hidden = view !== "map" || !state.mapError;
    get("list-container").hidden = view !== "list";
    get("map-view").setAttribute("aria-pressed", String(view === "map"));
    get("list-view").setAttribute("aria-pressed", String(view === "list"));
    if (record) updateUrl();
    if (state.map) requestAnimationFrame(() => state.map.invalidateSize());
  }
  function closeInspector(restoreFocus = true, record = true) {
    state.detailSequence++;
    state.selected = null;
    elements.inspector.hidden = true;
    document.querySelector(".workspace").classList.remove("has-inspector");
    if (record) updateUrl();
    render();
    if (restoreFocus) elements.search.focus({ preventScroll: true });
  }
  function metadata(label, value) {
    const row = node("div", "metadata-row");
    row.append(node("span", "", label), node("span", "", value));
    return row;
  }
  async function selectUniversity(id, focusMap = true, record = true) {
    const sequence = ++state.detailSequence;
    state.selected = id;
    elements.inspector.hidden = false;
    document.querySelector(".workspace").classList.add("has-inspector");
    elements.inspector.replaceChildren(node("p", "empty-state", "Loading university details…"));
    if (record) updateUrl();
    render();
    try {
      const detail = await api("/api/universities/" + id);
      if (sequence !== state.detailSequence) return;
      const university = detail.university;
      const top = node("div", "inspector-top");
      const close = node("button", "inspector-close", "×");
      close.type = "button";
      close.setAttribute("aria-label", "Close university details");
      close.addEventListener("click", closeInspector);
      top.append(node("span", "eyebrow", "UNIVERSITY DETAILS"), close);
      elements.inspector.replaceChildren(top, node("div", "institution-symbol", "⌂"), node("h2", "", university.name), node("p", "", countryFlag(university.country_code) + " " + [university.city, countryName(university.country_code)].filter(Boolean).join(", ")), stage(university.status));
      const facts = node("div", "metadata");
      facts.append(metadata("Target deadline", deadline(university.deadline)), metadata("Map location", hasCoordinates(university) ? "Located" : "Not yet located"));
      elements.inspector.append(facts);
      const portal = safeExternalUrl(university.portal_url);
      if (portal) {
        const link = node("a", "portal-link", "Open university website ↗");
        link.href = portal; link.target = "_blank"; link.rel = "noopener noreferrer";
        elements.inspector.append(link);
      }
      elements.inspector.append(node("h3", "", "Faculty contacts"));
      if (!detail.professors.length) elements.inspector.append(node("p", "", "No faculty contacts saved yet."));
      for (const professor of detail.professors) {
        const card = node("div", "detail-card");
        card.append(node("strong", "", professor.name), node("p", "", professor.research_interests || "Research focus not recorded"), stage(professor.outreach_status));
        elements.inspector.append(card);
      }
      elements.inspector.append(node("h3", "", "Next steps"));
      if (!detail.tasks.length) elements.inspector.append(node("p", "", "No linked tasks yet."));
      for (const task of detail.tasks) {
        const item = node("div", "task-line");
        item.append(node("span", "task-bullet", task.is_completed ? "✓" : "○"), node("span", "", task.title + (task.due_date ? " · " + deadline(task.due_date) : "")));
        elements.inspector.append(item);
      }
      elements.inspector.focus({ preventScroll: true });
      if (state.map) {
        state.map.invalidateSize();
        if (focusMap && hasCoordinates(university)) state.map.flyTo([university.latitude, university.longitude], 5, { animate: !matchMedia("(prefers-reduced-motion: reduce)").matches });
      }
    } catch {
      if (sequence !== state.detailSequence) return;
      const back = node("button", "inspector-close", "Close");
      back.addEventListener("click", closeInspector);
      elements.inspector.replaceChildren(node("p", "", "Could not load this university. Close and select it again to retry."), back);
    }
  }
  function renderResults() {
    elements.results.replaceChildren();
    get("result-count").textContent = state.filtered.length;
    get("mapped-count").textContent = state.filtered.filter(hasCoordinates).length + " of " + state.filtered.length + " universities mapped";
    if (!state.filtered.length) elements.results.append(node("p", "empty-state", "No universities match these filters. Try another country or search."));
    for (const university of state.filtered) {
      const card = node("button", "university-card" + (state.selected === university.id ? " selected" : ""));
      card.type = "button";
      card.setAttribute("aria-pressed", String(state.selected === university.id));
      card.append(node("span", "country-tag", countryFlag(university.country_code) + " " + countryName(university.country_code)), node("span", "university-name", university.name));
      const meta = node("span", "card-meta");
      meta.append(node("span", "", university.city || "City not recorded"), stage(university.status));
      card.append(meta);
      if (!hasCoordinates(university)) card.append(node("span", "no-pin", "Map location not yet available"));
      card.addEventListener("click", () => selectUniversity(university.id));
      elements.results.append(card);
    }
    const container = get("university-table");
    if (!state.filtered.length) { container.replaceChildren(node("p", "empty-state", "No matching universities. Your filters apply to both views.")); return; }
    const table = node("table");
    const head = node("thead"); const headings = node("tr");
    for (const title of ["University", "Location", "Stage"]) { const cell = node("th", "", title); cell.scope = "col"; headings.append(cell); }
    head.append(headings); table.append(head);
    const body = node("tbody");
    for (const university of state.filtered) {
      const row = node("tr", state.selected === university.id ? "selected" : "");
      const name = node("td"); const button = node("button", "", university.name);
      button.addEventListener("click", () => selectUniversity(university.id)); name.append(button);
      const progress = node("td"); progress.append(stage(university.status));
      row.append(name, node("td", "location-cell", countryName(university.country_code)), progress); body.append(row);
    }
    table.append(body); container.replaceChildren(table);
  }
  function renderMap() {
    if (!state.map) return;
    const countries = new Set(state.filtered.map(university => university.country_code));
    state.polygons.eachLayer(layer => {
      const code = resolveCountryFeature(layer.feature).code;
      const selected = code === elements.country.value;
      layer.setStyle({ fillColor: selected ? "#85c2d4" : countries.has(code) ? "#cce5ee" : "#fff",
        fillOpacity: 1, color: selected ? "#087ba4" : "#b6cbd6", weight: selected ? 1.8 : .7 });
      layer.getElement()?.setAttribute("aria-pressed", String(selected));
      layer.getElement()?.setAttribute("tabindex", selected ? "0" : "-1");
      if (selected) layer.bringToFront();
    });
    state.markers.clearLayers();
    for (const university of state.filtered.filter(hasCoordinates)) {
      const selected = state.selected === university.id;
      const marker = L.circleMarker([university.latitude, university.longitude], { radius: selected ? 10 : 7, color: "#fff", weight: 3, fillColor: selected ? "#d99d30" : "#087ba4", fillOpacity: 1 });
      marker.bindTooltip(node("span", "", university.name), { direction: "top" });
      marker.on("click", () => selectUniversity(university.id)); marker.addTo(state.markers);
    }
    requestAnimationFrame(() => state.map.invalidateSize());
  }
  function render() {
    state.filtered = filterUniversities(state.universities, { search: elements.search.value, country: elements.country.value, status: elements.status.value });
    renderResults(); renderMap();
  }
  function focusCountry(code) {
    const feature = state.geometry?.features.find(feature => resolveCountryFeature(feature).code === code);
    const bounds = dominantLandmassBounds(feature);
    if (state.map && bounds) state.map.fitBounds(bounds, { padding: [30, 30], maxZoom: 5, animate: !matchMedia("(prefers-reduced-motion: reduce)").matches });
  }
  function resetMap() {
    state.map?.setView([29, 2], 2.4, { animate: false });
  }
  function goBack() { if (navigationIndex > 0) history.back(); }
  function goForward() { if (navigationIndex < navigationEnd) history.forward(); }
  // The desktop mouse buttons call the same navigation as browser history.
  window.GradCompassNavigation = Object.freeze({ back: goBack, forward: goForward });
  function applyLocation() {
    const url = new URL(location.href);
    for (const name of ["country", "status", "search"]) elements[name].value = url.searchParams.get(name) || "";
    setView(url.searchParams.get("view") === "list" ? "list" : "map", false);
    closeInspector(false, false);
    if (elements.country.value) focusCountry(elements.country.value); else resetMap();
    const id = url.searchParams.get("university");
    if (/^[1-9][0-9]*$/.test(id || "") && state.universities.some(university => university.id === Number(id))) selectUniversity(Number(id), false, false);
  }
  async function loadMap() {
    if (state.map) return;
    try {
      const data = await api("/api/map");
      state.geometry = data;
      state.map = L.map("map", { center: [29, 2], zoom: 2.4, zoomSnap: .2, minZoom: 1.5, maxZoom: 12, zoomControl: false, attributionControl: false });
      L.control.zoom({ position: "bottomright" }).addTo(state.map);
      state.polygons = L.geoJSON({ ...data, features: data.features.filter(feature => resolveCountryFeature(feature).code !== "ATA") }, {
        className: "country-outline",
        onEachFeature(feature, layer) {
          const country = resolveCountryFeature(feature);
          layer.on("add", () => {
            const path = layer.getElement();
            path.setAttribute("data-country", country.code);
            path.setAttribute("tabindex", "-1");
            path.setAttribute("role", "button");
            path.setAttribute("aria-label", "Explore " + country.name);
            path.addEventListener("keydown", event => {
              if (event.key === "Enter" || event.key === " ") { event.preventDefault(); layer.fire("click"); }
            });
          });
          layer.bindTooltip(node("span", "", country.name), { sticky: true });
          layer.on("click", () => {
            if (![...elements.country.options].some(option => option.value === country.code)) {
              const option = node("option", "", country.flag + " " + country.name);
              option.value = country.code; elements.country.append(option);
            }
            elements.country.value = country.code; closeInspector(false);
            focusCountry(country.code);
          });
        }
      }).addTo(state.map);
      state.markers = L.layerGroup().addTo(state.map);
      state.mapError = false; get("map-message").hidden = true; renderMap();
    } catch {
      get("map-message").textContent = "The map could not load. You can still explore your universities in the list view.";
      state.mapError = true; get("map-message").hidden = state.view !== "map";
    }
  }
  async function loadWorkspace() {
    get("error").hidden = true;
    try {
      const result = await api("/api/workspace");
      state.universities = result.universities;
      render();
      await loadMap();
    } catch {
      elements.results.replaceChildren(node("p", "empty-state", "Your workspace could not be loaded."));
      get("error-text").textContent = "Could not load the workspace. Please try again."; get("error").hidden = false;
    }
  }
  get("map-view").addEventListener("click", () => setView("map"));
  get("list-view").addEventListener("click", () => setView("list"));
  document.querySelector(".brand").addEventListener("click", event => {
    event.preventDefault();
    elements.country.value = ""; elements.status.value = ""; elements.search.value = "";
    editingSearch = false; setView("map", false); closeInspector(false, false); resetMap(); updateUrl();
  });
  for (const element of [elements.country, elements.status]) element.addEventListener("change", () => {
    editingSearch = false;
    closeInspector(false);
    if (element === elements.country) { if (element.value) focusCountry(element.value); else resetMap(); }
  });
  elements.search.addEventListener("input", () => {
    closeInspector(false, false);
    updateUrl(editingSearch);
    editingSearch = true;
  });
  elements.search.addEventListener("blur", () => { editingSearch = false; });
  get("nav-back").addEventListener("click", goBack);
  get("nav-forward").addEventListener("click", goForward);
  window.addEventListener("popstate", event => {
    navigationIndex = Number.isInteger(event.state?.gradCompassIndex) ? event.state.gradCompassIndex : 0;
    navigationEnd = Math.max(navigationEnd, navigationIndex);
    editingSearch = false;
    applyLocation();
    updateNavigationButtons();
  });
  get("retry").addEventListener("click", loadWorkspace);
  document.addEventListener("keydown", event => {
    if (event.altKey && ["ArrowLeft", "ArrowRight"].includes(event.key)) {
      event.preventDefault();
      if (event.key === "ArrowLeft") goBack(); else goForward();
    } else if (event.key === "Escape") {
      event.preventDefault();
      if (state.selected) closeInspector();
      else if (elements.country.value || elements.status.value || elements.search.value) {
        elements.country.value = ""; elements.status.value = ""; elements.search.value = "";
        editingSearch = false; closeInspector(false); resetMap();
      } else if (state.view === "list") setView("map");
    }
  });
  document.addEventListener("auxclick", event => {
    if ([3, 4].includes(event.button)) {
      event.preventDefault();
      if (event.button === 3) goBack(); else goForward();
    }
  });
  for (const country of typeof WORLD_COUNTRIES !== "undefined" ? WORLD_COUNTRIES : []) {
    const option = node("option", "", country.flag + " " + country.name); option.value = country.code; elements.country.append(option);
  }
  history.replaceState({ gradCompassIndex: 0 }, "", location.href);
  updateNavigationButtons();
  setView(new URL(location.href).searchParams.get("view") === "list" ? "list" : "map", false);
  loadWorkspace().then(() => {
    applyLocation();
  });
}
