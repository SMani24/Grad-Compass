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

if (typeof module !== "undefined") module.exports = { hasCoordinates, filterUniversities, safeExternalUrl };

if (typeof document !== "undefined") {
  const get = id => document.getElementById(id);
  const state = { universities: [], filtered: [], selected: null, view: "map", geometry: null, map: null, polygons: null, markers: null, mapError: false, detailSequence: 0 };
  const elements = { search: get("search"), country: get("country"), status: get("status"), results: get("results"), inspector: get("inspector") };

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
  function updateUrl() {
    const url = new URL(location.href);
    if (state.view === "list") url.searchParams.set("view", "list"); else url.searchParams.delete("view");
    if (state.selected) url.searchParams.set("university", state.selected); else url.searchParams.delete("university");
    history.replaceState(null, "", url);
  }
  function setView(view) {
    state.view = view;
    get("map").hidden = view !== "map";
    get("map-key").hidden = view !== "map";
    get("map-message").hidden = view !== "map" || !state.mapError;
    get("list-container").hidden = view !== "list";
    get("map-view").setAttribute("aria-pressed", String(view === "map"));
    get("list-view").setAttribute("aria-pressed", String(view === "list"));
    updateUrl();
    if (state.map) requestAnimationFrame(() => state.map.invalidateSize());
  }
  function closeInspector(restoreFocus = true) {
    state.detailSequence++;
    state.selected = null;
    elements.inspector.hidden = true;
    document.querySelector(".workspace").classList.remove("has-inspector");
    updateUrl();
    render();
    if (restoreFocus) elements.search.focus({ preventScroll: true });
  }
  function metadata(label, value) {
    const row = node("div", "metadata-row");
    row.append(node("span", "", label), node("span", "", value));
    return row;
  }
  async function selectUniversity(id, focusMap = true) {
    const sequence = ++state.detailSequence;
    state.selected = id;
    elements.inspector.hidden = false;
    document.querySelector(".workspace").classList.add("has-inspector");
    elements.inspector.replaceChildren(node("p", "empty-state", "Loading university details…"));
    updateUrl();
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
    state.polygons.setStyle(feature => ({ fillColor: countries.has(resolveCountryFeature(feature).code) ? "#cce5ee" : "#fff", fillOpacity: 1, color: "#b6cbd6", weight: .7 }));
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
  async function loadMap() {
    if (state.map) return;
    try {
      const data = await api("/api/map");
      state.geometry = data;
      state.map = L.map("map", { center: [29, 2], zoom: 2.4, zoomSnap: .2, minZoom: 1.5, maxZoom: 12, zoomControl: false, attributionControl: false });
      L.control.zoom({ position: "bottomright" }).addTo(state.map);
      state.polygons = L.geoJSON({ ...data, features: data.features.filter(feature => resolveCountryFeature(feature).code !== "ATA") }, {
        onEachFeature(feature, layer) {
          const country = resolveCountryFeature(feature);
          layer.bindTooltip(node("span", "", country.name), { sticky: true });
          layer.on("click", () => {
            if (![...elements.country.options].some(option => option.value === country.code)) {
              const option = node("option", "", country.flag + " " + country.name);
              option.value = country.code; elements.country.append(option);
            }
            elements.country.value = country.code; closeInspector(false);
            state.map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 5, animate: !matchMedia("(prefers-reduced-motion: reduce)").matches });
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
  for (const element of [elements.search, elements.country, elements.status]) element.addEventListener(element === elements.search ? "input" : "change", () => closeInspector(false));
  get("retry").addEventListener("click", loadWorkspace);
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !elements.inspector.hidden) closeInspector(); });
  for (const country of typeof WORLD_COUNTRIES !== "undefined" ? WORLD_COUNTRIES : []) {
    const option = node("option", "", country.flag + " " + country.name); option.value = country.code; elements.country.append(option);
  }
  const initial = new URL(location.href);
  const initialSelection = initial.searchParams.get("university");
  setView(initial.searchParams.get("view") === "list" ? "list" : "map");
  loadWorkspace().then(() => {
    if (/^[1-9][0-9]*$/.test(initialSelection || "") && state.universities.some(university => university.id === Number(initialSelection))) selectUniversity(Number(initialSelection), false);
  });
}
