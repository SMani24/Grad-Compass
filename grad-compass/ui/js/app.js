/**
 * Grad Compass - Core Shell & State History Router
 * Manages history states, gateway transitions, global shortcuts, and settings.
 */

const navHistory = [];
let historyIndex = -1;

let currentCountry = { name: "Switzerland", code: "CHE", flag: "🇨🇭" };
let currentUniversity = null;

const SCALE_MAP = { "Normal": 1.0, "Medium": 1.15, "Large": 1.30, "XL": 1.45 };

document.addEventListener("DOMContentLoaded", () => {
  const mapContainer = document.getElementById("map-container");
  const gatewayOverlay = document.getElementById("gateway-overlay");
  const btnExploreMap = document.getElementById("btn-explore-map");
  const btnOpenPipeline = document.getElementById("btn-open-pipeline");
  const pipelineView = document.getElementById("pipeline-view");
  const btnPipelineBack = document.getElementById("btn-pipeline-back");
  const btnPipelineSettings = document.getElementById("btn-pipeline-settings");

  const countryDrawer = document.getElementById("country-drawer");
  const uniDrawer = document.getElementById("uni-drawer");
  const btnCloseCountryDrawer = document.getElementById("btn-close-country-drawer");
  const btnCountryBack = document.getElementById("btn-country-back");
  const btnCloseUniDrawer = document.getElementById("btn-close-uni-drawer");
  const btnBackToCountry = document.getElementById("btn-back-to-country");

  const countryDrawerTitle = document.getElementById("country-drawer-title");
  const countryDrawerSubtitle = document.getElementById("country-drawer-subtitle");

  const btnNavBack = document.getElementById("btn-nav-back");
  const btnNavForward = document.getElementById("btn-nav-forward");

  const settingsModal = document.getElementById("settings-modal");
  const selectFontScale = document.getElementById("select-font-scale");
  const inputMapZoom = document.getElementById("input-map-zoom");
  const zoomValueLabel = document.getElementById("zoom-value-label");

  // Config bootstrap
  let activeConfig = { font_scale: "Normal", map_zoom: 3.0 };
  const cachedConfig = localStorage.getItem("grad_compass_config");
  if (cachedConfig) {
    try { activeConfig = { ...activeConfig, ...JSON.parse(cachedConfig) }; } catch (e) {}
  }
  applyConfig(activeConfig);
  initMap(parseFloat(activeConfig.map_zoom));

  async function syncBackendConfig() {
    if (window.pywebview?.api) {
      try {
        const backendCfg = await window.pywebview.api.get_config();
        if (backendCfg) {
          activeConfig = { ...activeConfig, ...backendCfg };
          applyConfig(activeConfig);
          localStorage.setItem("grad_compass_config", JSON.stringify(activeConfig));
          if (window.setInitialZoom) window.setInitialZoom(parseFloat(activeConfig.map_zoom));
        }
      } catch (e) {
        console.error("Config sync failed:", e);
      }
    }
  }

  if (window.pywebview) syncBackendConfig();
  else window.addEventListener("pywebviewready", syncBackendConfig);

  pushState({ view: "gateway" });

  function pushState(state) {
    if (historyIndex < navHistory.length - 1) navHistory.splice(historyIndex + 1);
    navHistory.push(state);
    historyIndex++;
    updateNavButtons();
  }

  function updateNavButtons() {
    btnNavBack.disabled = historyIndex <= 0;
    btnNavForward.disabled = historyIndex >= navHistory.length - 1;
  }

  function applyState(state) {
    if (window.CountryDrawer) window.CountryDrawer.hideContextMenu();

    if (state.view === "gateway") {
      document.body.classList.remove("drawer-open", "in-pipeline-view");
      gatewayOverlay.classList.remove("hidden");
      pipelineView.classList.add("hidden");
      mapContainer.classList.add("blurred");
      countryDrawer.classList.remove("open");
      uniDrawer.classList.remove("open");
      if (window.setMapInteractive) window.setMapInteractive(false);
    } else if (state.view === "map") {
      document.body.classList.remove("drawer-open", "in-pipeline-view");
      gatewayOverlay.classList.add("hidden");
      pipelineView.classList.add("hidden");
      mapContainer.classList.remove("blurred");
      countryDrawer.classList.remove("open");
      uniDrawer.classList.remove("open");
      if (window.setMapInteractive) window.setMapInteractive(true);
      resetToWorldView();
    } else if (state.view === "country") {
      currentCountry = { name: state.name, code: state.code, flag: state.flag || "🌐" };
      document.body.classList.remove("in-pipeline-view");
      document.body.classList.add("drawer-open");
      gatewayOverlay.classList.add("hidden");
      pipelineView.classList.add("hidden");
      mapContainer.classList.remove("blurred");
      if (window.setMapInteractive) window.setMapInteractive(true);
      uniDrawer.classList.remove("open");
      countryDrawer.classList.add("open");
      countryDrawerTitle.innerHTML = `<span class="country-flag-icon">${currentCountry.flag}</span> <span>${currentCountry.name}</span>`;
      countryDrawerSubtitle.innerText = `Country Code: ${currentCountry.code}`;

      if (window.selectCountryByCode) window.selectCountryByCode(state.code);
      window.CountryDrawer.load(state.code, state.name);
    } else if (state.view === "university") {
      document.body.classList.remove("in-pipeline-view");
      document.body.classList.add("drawer-open");
      gatewayOverlay.classList.add("hidden");
      pipelineView.classList.add("hidden");
      mapContainer.classList.remove("blurred");
      if (window.setMapInteractive) window.setMapInteractive(true);
      countryDrawer.classList.remove("open");
      uniDrawer.classList.add("open");
      window.UniDrawer.load(state.university, currentCountry);
    } else if (state.view === "pipeline") {
      document.body.classList.remove("drawer-open");
      document.body.classList.add("in-pipeline-view");
      gatewayOverlay.classList.add("hidden");
      pipelineView.classList.remove("hidden");
      mapContainer.classList.add("blurred");
      countryDrawer.classList.remove("open");
      uniDrawer.classList.remove("open");
      if (window.setMapInteractive) window.setMapInteractive(false);
      if (window.loadPipelineTab) window.loadPipelineTab("tab-tasks");
    }
    updateNavButtons();
  }

  function goBack() {
    if (historyIndex > 0) {
      historyIndex--;
      applyState(navHistory[historyIndex]);
    }
  }

  function goForward() {
    if (historyIndex < navHistory.length - 1) {
      historyIndex++;
      applyState(navHistory[historyIndex]);
    }
  }

  btnNavBack.addEventListener("click", goBack);
  btnNavForward.addEventListener("click", goForward);

  window.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      e.preventDefault();
      if (window.CountryDrawer) window.CountryDrawer.hideContextMenu();
      const openModal = document.querySelector(".modal-backdrop:not(.hidden)");
      if (openModal) {
        openModal.classList.add("hidden");
        return;
      }
      goBack();
      return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "w") {
      e.preventDefault();
      window.pywebview?.api?.close_app();
      return;
    }

    if (e.altKey && e.key === "ArrowLeft") { e.preventDefault(); goBack(); }
    if (e.altKey && e.key === "ArrowRight") { e.preventDefault(); goForward(); }
  });

  btnExploreMap.addEventListener("click", () => {
    gatewayOverlay.classList.add("hidden");
    mapContainer.classList.remove("blurred");
    if (window.setMapInteractive) window.setMapInteractive(true);
    pushState({ view: "map" });
    setTimeout(() => { if (window.map) window.map.invalidateSize(); }, 300);
  });

  btnOpenPipeline.addEventListener("click", () => {
    pushState({ view: "pipeline" });
    applyState({ view: "pipeline" });
  });

  btnPipelineBack.addEventListener("click", () => {
    pushState({ view: "gateway" });
    applyState({ view: "gateway" });
  });

  // Drawer Bridges
  window.onCountrySelected = (countryName, countryCode, flagEmoji, recordHistory = true) => {
    currentCountry = { name: countryName, code: countryCode, flag: flagEmoji };
    countryDrawerTitle.innerHTML = `<span class="country-flag-icon">${flagEmoji}</span> <span>${countryName}</span>`;
    countryDrawerSubtitle.innerText = `Country Code: ${countryCode || 'N/A'}`;
    document.body.classList.add("drawer-open");
    countryDrawer.classList.add("open");
    uniDrawer.classList.remove("open");

    window.CountryDrawer.load(countryCode, countryName);
    if (recordHistory) {
      pushState({ view: "country", name: countryName, code: countryCode, flag: flagEmoji });
    }
  };

  window.onUniversitySelected = uni => {
    currentUniversity = uni;
    countryDrawer.classList.remove("open");
    uniDrawer.classList.add("open");
    document.body.classList.add("drawer-open");

    if (uni.latitude && uni.longitude) {
      focusUniversityPin(uni.latitude, uni.longitude);
    }

    window.UniDrawer.load(uni, currentCountry);
    pushState({ view: "university", university: uni });
  };

  window.navigateBackToCountry = () => {
    pushState({ view: "country", name: currentCountry.name, code: currentCountry.code, flag: currentCountry.flag });
    applyState({ view: "country", name: currentCountry.name, code: currentCountry.code, flag: currentCountry.flag });
  };

  btnCountryBack.addEventListener("click", () => {
    pushState({ view: "map" });
    applyState({ view: "map" });
  });

  btnCloseCountryDrawer.addEventListener("click", () => {
    pushState({ view: "map" });
    applyState({ view: "map" });
  });

  btnBackToCountry.addEventListener("click", window.navigateBackToCountry);

  btnCloseUniDrawer.addEventListener("click", () => {
    pushState({ view: "map" });
    applyState({ view: "map" });
  });

  // Preferences
  function openPreferences() {
    selectFontScale.value = activeConfig.font_scale || "Normal";
    inputMapZoom.value = activeConfig.map_zoom || 3.0;
    zoomValueLabel.innerText = inputMapZoom.value;
    settingsModal.classList.remove("hidden");
  }

  document.getElementById("btn-open-settings").addEventListener("click", openPreferences);
  if (btnPipelineSettings) btnPipelineSettings.addEventListener("click", openPreferences);

  inputMapZoom.addEventListener("input", e => {
    zoomValueLabel.innerText = e.target.value;
  });

  document.getElementById("btn-save-settings").addEventListener("click", async () => {
    const chosenScale = selectFontScale.value;
    const chosenZoom = parseFloat(inputMapZoom.value);
    const updates = { font_scale: chosenScale, map_zoom: chosenZoom };

    applyConfig(updates);
    activeConfig = { ...activeConfig, ...updates };
    localStorage.setItem("grad_compass_config", JSON.stringify(activeConfig));

    if (window.setInitialZoom) window.setInitialZoom(chosenZoom);
    if (window.pywebview?.api) await window.pywebview.api.save_settings(updates);
    settingsModal.classList.add("hidden");
  });

  function applyConfig(cfg) {
    if (cfg.font_scale && SCALE_MAP[cfg.font_scale]) {
      document.documentElement.style.setProperty("--font-scale", SCALE_MAP[cfg.font_scale]);
      selectFontScale.value = cfg.font_scale;
    }
    if (cfg.map_zoom) {
      inputMapZoom.value = cfg.map_zoom;
      zoomValueLabel.innerText = cfg.map_zoom;
    }
  }
});