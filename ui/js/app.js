const navHistory = [];
let historyIndex = -1;

let currentCountry = { name: "", code: "" };
let currentUniversity = null;

const SCALE_MAP = { "Normal": 1.0, "Medium": 1.15, "Large": 1.30, "XL": 1.45 };

document.addEventListener("DOMContentLoaded", () => {
  const mapContainer = document.getElementById("map-container");
  const gatewayOverlay = document.getElementById("gateway-overlay");
  const btnExploreMap = document.getElementById("btn-explore-map");

  const countryDrawer = document.getElementById("country-drawer");
  const uniDrawer = document.getElementById("uni-drawer");
  const btnCloseCountryDrawer = document.getElementById("btn-close-country-drawer");
  const btnCountryBack = document.getElementById("btn-country-back");
  const btnCloseUniDrawer = document.getElementById("btn-close-uni-drawer");
  const btnBackToCountry = document.getElementById("btn-back-to-country");

  const countryDrawerTitle = document.getElementById("country-drawer-title");
  const countryDrawerSubtitle = document.getElementById("country-drawer-subtitle");
  const countryUniList = document.getElementById("country-uni-list");

  const uniDrawerTitle = document.getElementById("uni-drawer-title");
  const uniDrawerSubtitle = document.getElementById("uni-drawer-subtitle");
  const uniAttachmentsList = document.getElementById("uni-attachments-list");
  const professorsContainer = document.getElementById("professors-container");

  const addUniModal = document.getElementById("add-uni-modal");
  const addProfModal = document.getElementById("add-prof-modal");
  const settingsModal = document.getElementById("settings-modal");

  const btnNavBack = document.getElementById("btn-nav-back");
  const btnNavForward = document.getElementById("btn-nav-forward");

  const selectFontScale = document.getElementById("select-font-scale");
  const inputMapZoom = document.getElementById("input-map-zoom");
  const zoomValueLabel = document.getElementById("zoom-value-label");

  // Step 1: Synchronous config restore from localStorage
  let activeConfig = { font_scale: "Normal", map_zoom: 3.0 };
  const cachedConfig = localStorage.getItem("grad_compass_config");
  if (cachedConfig) {
    try {
      activeConfig = { ...activeConfig, ...JSON.parse(cachedConfig) };
    } catch (e) {}
  }
  applyConfig(activeConfig);
  initMap(parseFloat(activeConfig.map_zoom));

  // Step 2: Backend sync once pywebview is ready
  async function syncBackendConfig() {
    if (window.pywebview && window.pywebview.api) {
      try {
        const backendCfg = await window.pywebview.api.get_config();
        if (backendCfg) {
          activeConfig = { ...activeConfig, ...backendCfg };
          applyConfig(activeConfig);
          localStorage.setItem("grad_compass_config", JSON.stringify(activeConfig));
          if (window.setInitialZoom) {
            window.setInitialZoom(parseFloat(activeConfig.map_zoom));
          }
        }
      } catch (e) {
        console.error("Config sync failed:", e);
      }
    }
  }

  if (window.pywebview) {
    syncBackendConfig();
  } else {
    window.addEventListener("pywebviewready", syncBackendConfig);
  }

  pushState({ view: "gateway" });

  function pushState(state) {
    if (historyIndex < navHistory.length - 1) {
      navHistory.splice(historyIndex + 1);
    }
    navHistory.push(state);
    historyIndex++;
    updateNavButtons();
  }

  function updateNavButtons() {
    btnNavBack.disabled = historyIndex <= 0;
    btnNavForward.disabled = historyIndex >= navHistory.length - 1;
  }

  function applyState(state) {
    if (state.view === "gateway") {
      document.body.classList.remove("drawer-open");
      gatewayOverlay.classList.remove("hidden");
      mapContainer.classList.add("blurred");
      countryDrawer.classList.remove("open");
      uniDrawer.classList.remove("open");
      if (window.setMapInteractive) window.setMapInteractive(false);
    } else if (state.view === "map") {
      document.body.classList.remove("drawer-open");
      gatewayOverlay.classList.add("hidden");
      mapContainer.classList.remove("blurred");
      countryDrawer.classList.remove("open");
      uniDrawer.classList.remove("open");
      if (window.setMapInteractive) window.setMapInteractive(true);
      resetToWorldView();
    } else if (state.view === "country") {
      document.body.classList.add("drawer-open");
      gatewayOverlay.classList.add("hidden");
      mapContainer.classList.remove("blurred");
      if (window.setMapInteractive) window.setMapInteractive(true);
      uniDrawer.classList.remove("open");
      countryDrawer.classList.add("open");
      loadCountryUniversities(state.code, state.name);
    } else if (state.view === "university") {
      document.body.classList.add("drawer-open");
      gatewayOverlay.classList.add("hidden");
      mapContainer.classList.remove("blurred");
      if (window.setMapInteractive) window.setMapInteractive(true);
      countryDrawer.classList.remove("open");
      uniDrawer.classList.add("open");
      loadUniversityDetails(state.university);
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
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.close_app();
      }
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

  window.onCountrySelected = (countryName, countryCode, recordHistory = true) => {
    currentCountry = { name: countryName, code: countryCode };
    countryDrawerTitle.innerText = countryName;
    countryDrawerSubtitle.innerText = `Country Code: ${countryCode || 'N/A'}`;
    document.body.classList.add("drawer-open");
    countryDrawer.classList.add("open");
    uniDrawer.classList.remove("open");

    loadCountryUniversities(countryCode, countryName);

    if (recordHistory) {
      pushState({ view: "country", name: countryName, code: countryCode });
    }
  };

  async function loadCountryUniversities(code, name) {
    if (!window.pywebview || !window.pywebview.api) return;
    const unis = await window.pywebview.api.get_universities(code);
    renderUniversityPins(unis);

    countryUniList.innerHTML = "";
    if (unis.length === 0) {
      countryUniList.innerHTML = `<p style="font-size:13px; color:#8e8e93; margin-top:10px;">No universities added yet.</p>`;
      return;
    }

    unis.forEach(u => {
      const card = document.createElement("div");
      card.className = "entity-card";
      card.innerHTML = `
        <h4>${u.name}</h4>
        <p>${u.city ? u.city + ' • ' : ''}${u.deadline ? 'Deadline: ' + u.deadline : 'No deadline set'}</p>
      `;
      card.addEventListener("click", () => window.onUniversitySelected(u));
      countryUniList.appendChild(card);
    });
  }

  window.onUniversitySelected = uni => {
    currentUniversity = uni;
    countryDrawer.classList.remove("open");
    uniDrawer.classList.add("open");
    document.body.classList.add("drawer-open");

    if (uni.latitude && uni.longitude) {
      focusUniversityPin(uni.latitude, uni.longitude);
    }

    loadUniversityDetails(uni);
    pushState({ view: "university", university: uni });
  };

  async function loadUniversityDetails(uni) {
    uniDrawerTitle.innerText = uni.name;
    uniDrawerSubtitle.innerText = uni.city ? `${uni.city}, ${currentCountry.name}` : currentCountry.name;
    loadAttachments("university", uni.id);
    loadProfessors(uni.id);
  }

  async function loadProfessors(uniId) {
    professorsContainer.innerHTML = "";
    const profs = await window.pywebview.api.get_professors(uniId);
    if (profs.length === 0) {
      professorsContainer.innerHTML = `<p style="font-size:13px; color:#8e8e93;">No professors added yet.</p>`;
      return;
    }

    profs.forEach(p => {
      const card = document.createElement("div");
      card.className = "entity-card";
      const statusClass = (p.outreach_status || "Not-Contacted").replace(/[^a-zA-Z0-9]/g, "-");

      card.innerHTML = `
        <h4>${p.name}</h4>
        <p>${p.research_interests || 'No research focus specified'}</p>
        <span class="status-pill ${statusClass}">${p.outreach_status}</span>
        <div style="margin-top:8px; display:flex; gap:10px;">
          ${p.email ? `<a href="mailto:${p.email}" class="btn-text" style="font-size:12px;">Email</a>` : ''}
          <button class="btn-text btn-prof-attach" data-id="${p.id}" style="font-size:12px;">+ Attach File</button>
        </div>
        <div class="file-chip-container" id="prof-files-${p.id}"></div>
      `;

      card.querySelector(".btn-prof-attach").addEventListener("click", async e => {
        e.stopPropagation();
        const res = await window.pywebview.api.pick_and_attach_file("professor", p.id);
        if (res.success) loadProfFiles(p.id);
      });

      professorsContainer.appendChild(card);
      loadProfFiles(p.id);
    });
  }

  async function loadAttachments(type, id) {
    uniAttachmentsList.innerHTML = "";
    const files = await window.pywebview.api.get_attachments(type, id);
    files.forEach(f => {
      const chip = createAttachmentChip(f);
      uniAttachmentsList.appendChild(chip);
    });
  }

  async function loadProfFiles(profId) {
    const container = document.getElementById(`prof-files-${profId}`);
    if (!container) return;
    container.innerHTML = "";
    const files = await window.pywebview.api.get_attachments("professor", profId);
    files.forEach(f => {
      const chip = createAttachmentChip(f, () => loadProfFiles(profId));
      container.appendChild(chip);
    });
  }

  function createAttachmentChip(fileRecord, onDeleteCallback) {
    const chip = document.createElement("span");
    chip.className = "file-chip";
    chip.innerHTML = `📄 <span>${fileRecord.file_name}</span> <span class="file-chip-del" title="Delete">✕</span>`;

    chip.addEventListener("click", () => {
      window.pywebview.api.open_file(fileRecord.stored_path);
    });

    chip.querySelector(".file-chip-del").addEventListener("click", async e => {
      e.stopPropagation();
      await window.pywebview.api.delete_attachment(fileRecord.id);
      if (onDeleteCallback) onDeleteCallback();
      else if (currentUniversity) loadAttachments("university", currentUniversity.id);
    });

    return chip;
  }

  // Drawer Navigation
  btnCountryBack.addEventListener("click", () => {
    pushState({ view: "map" });
    applyState({ view: "map" });
  });

  btnCloseCountryDrawer.addEventListener("click", () => {
    pushState({ view: "map" });
    applyState({ view: "map" });
  });

  btnBackToCountry.addEventListener("click", () => {
    pushState({ view: "country", name: currentCountry.name, code: currentCountry.code });
    applyState({ view: "country", name: currentCountry.name, code: currentCountry.code });
  });

  btnCloseUniDrawer.addEventListener("click", () => {
    pushState({ view: "map" });
    applyState({ view: "map" });
  });

  // Modal Triggers
  document.getElementById("btn-show-add-uni").addEventListener("click", () => {
    addUniModal.classList.remove("hidden");
    document.getElementById("input-uni-name").focus();
  });

  document.getElementById("btn-show-add-prof").addEventListener("click", () => {
    addProfModal.classList.remove("hidden");
    document.getElementById("input-prof-name").focus();
  });

  document.getElementById("btn-attach-uni-file").addEventListener("click", async () => {
    if (!currentUniversity) return;
    const res = await window.pywebview.api.pick_and_attach_file("university", currentUniversity.id);
    if (res.success) loadAttachments("university", currentUniversity.id);
  });

  document.querySelectorAll(".btn-modal-dismiss").forEach(btn => {
    btn.addEventListener("click", e => {
      e.target.closest(".modal-backdrop").classList.add("hidden");
    });
  });

  // Submissions
  document.getElementById("btn-submit-uni").addEventListener("click", async () => {
    const name = document.getElementById("input-uni-name").value.trim();
    const city = document.getElementById("input-uni-city").value.trim();
    const deadline = document.getElementById("input-uni-deadline").value;
    const url = document.getElementById("input-uni-url").value.trim();

    if (!name) return;

    await window.pywebview.api.add_university(
      currentCountry.code, currentCountry.name, name, city, deadline, url
    );

    markCountryActive(currentCountry.code);
    addUniModal.classList.add("hidden");
    document.getElementById("input-uni-name").value = "";
    document.getElementById("input-uni-city").value = "";

    loadCountryUniversities(currentCountry.code, currentCountry.name);
  });

  document.getElementById("btn-submit-prof").addEventListener("click", async () => {
    const name = document.getElementById("input-prof-name").value.trim();
    const email = document.getElementById("input-prof-email").value.trim();
    const research = document.getElementById("input-prof-research").value.trim();
    const status = document.getElementById("select-prof-status").value;

    if (!name || !currentUniversity) return;

    await window.pywebview.api.add_professor(currentUniversity.id, name, email, research, status);
    addProfModal.classList.add("hidden");
    document.getElementById("input-prof-name").value = "";
    document.getElementById("input-prof-email").value = "";
    document.getElementById("input-prof-research").value = "";

    loadProfessors(currentUniversity.id);
  });

  // Preferences Management
  document.getElementById("btn-open-settings").addEventListener("click", () => {
    selectFontScale.value = activeConfig.font_scale || "Normal";
    inputMapZoom.value = activeConfig.map_zoom || 3.0;
    zoomValueLabel.innerText = inputMapZoom.value;
    settingsModal.classList.remove("hidden");
  });

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

    if (window.setInitialZoom) {
      window.setInitialZoom(chosenZoom);
    }

    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.save_settings(updates);
    }
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