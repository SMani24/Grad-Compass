/**
 * Grad Compass - Country Drawer Controller
 * Manages university listing, multi-select batch operations, and quick-action context menus.
 */

window.CountryDrawer = (() => {
  const countryUniList = document.getElementById("country-uni-list");
  const uniBatchToolbar = document.getElementById("uni-batch-toolbar");
  const checkSelectAllUnis = document.getElementById("check-select-all-unis");
  const batchSelectedCount = document.getElementById("batch-selected-count");
  const selectBatchStatus = document.getElementById("select-batch-status");
  const btnBatchDelete = document.getElementById("btn-batch-delete");
  const btnBatchCancel = document.getElementById("btn-batch-cancel");

  const uniContextMenu = document.getElementById("uni-context-menu");
  const cmenuEditUni = document.getElementById("cmenu-edit-uni");
  const cmenuOpenUrl = document.getElementById("cmenu-open-url");
  const cmenuDeleteUni = document.getElementById("cmenu-delete-uni");

  let selectedUniIds = new Set();
  let activeContextMenuUni = null;
  let activeCountryContext = { code: "", name: "" };

  document.addEventListener("DOMContentLoaded", () => {
    // Add University button
    document.getElementById("btn-show-add-uni")?.addEventListener("click", () => {
      window.Modals.openAddUniversity(activeCountryContext.code, activeCountryContext.name, () => {
        if (window.markCountryActive) window.markCountryActive(activeCountryContext.code);
        load(activeCountryContext.code, activeCountryContext.name);
      });
    });

    // Dismiss context popover on external click
    document.addEventListener("click", e => {
      if (!e.target.closest(".context-menu-popover") && !e.target.closest(".btn-uni-context")) {
        hideContextMenu();
      }
    });

    // Context Menu Items
    cmenuEditUni.addEventListener("click", () => {
      if (!activeContextMenuUni) return;
      const uni = activeContextMenuUni;
      hideContextMenu();
      window.Modals.openEditUniversity(uni, activeCountryContext.name, () => {
        load(activeCountryContext.code, activeCountryContext.name);
      });
    });

    cmenuOpenUrl.addEventListener("click", () => {
      if (!activeContextMenuUni || !activeContextMenuUni.portal_url) return;
      const url = activeContextMenuUni.portal_url;
      hideContextMenu();
      window.open(url, "_blank");
    });

    cmenuDeleteUni.addEventListener("click", () => {
      if (!activeContextMenuUni) return;
      const uni = activeContextMenuUni;
      hideContextMenu();
      window.Modals.showConfirm({
        title: "Delete University",
        message: `Are you sure you want to delete ${uni.name}? All attached faculty, documents, and tasks will be permanently removed.`,
        confirmText: "Delete",
        onConfirm: async () => {
          await window.pywebview.api.delete_university(uni.id);
          if (window.refreshActiveCountries) {
            await window.refreshActiveCountries();
          }
          load(activeCountryContext.code, activeCountryContext.name);
        }
      });
    });

    // Batch Actions
    checkSelectAllUnis.addEventListener("change", () => {
      const isChecked = checkSelectAllUnis.checked;
      const cards = countryUniList.querySelectorAll(".entity-card");
      cards.forEach(card => {
        const id = parseInt(card.getAttribute("data-id"));
        const cb = card.querySelector(".uni-card-check");
        if (cb) cb.checked = isChecked;
        if (isChecked) {
          selectedUniIds.add(id);
          card.classList.add("card-selected");
        } else {
          selectedUniIds.delete(id);
          card.classList.remove("card-selected");
        }
      });
      updateBatchToolbar();
    });

    btnBatchCancel.addEventListener("click", clearSelection);

    selectBatchStatus.addEventListener("change", async () => {
      const status = selectBatchStatus.value;
      if (!status || selectedUniIds.size === 0) return;

      await window.pywebview.api.batch_update_university_status(Array.from(selectedUniIds), status);
      selectBatchStatus.value = "";
      clearSelection();
      load(activeCountryContext.code, activeCountryContext.name);
    });

    btnBatchDelete.addEventListener("click", () => {
      if (selectedUniIds.size === 0) return;
      const count = selectedUniIds.size;
      const ids = Array.from(selectedUniIds);

      window.Modals.showConfirm({
        title: "Batch Delete Universities",
        message: `Are you sure you want to permanently delete ${count} selected universities? All associated faculty contacts, tasks, and documents will be removed.`,
        confirmText: `Delete ${count} Items`,
        onConfirm: async () => {
          await window.pywebview.api.delete_universities_batch(ids);
          if (window.refreshActiveCountries) {
            await window.refreshActiveCountries();
          }
          clearSelection();
          load(activeCountryContext.code, activeCountryContext.name);
        }
      });
    });
  });

  async function load(countryCode, countryName) {
    activeCountryContext = { code: countryCode, name: countryName };
    if (!window.pywebview || !window.pywebview.api) return;

    const unis = await window.pywebview.api.get_universities(countryCode);
    if (window.renderUniversityPins) window.renderUniversityPins(unis);

    countryUniList.innerHTML = "";
    if (unis.length === 0) {
      countryUniList.innerHTML = `<p style="font-size:13px; color:#8e8e93; margin-top:10px;">No universities added yet.</p>`;
      clearSelection();
      // Ensure the map updates when the list becomes empty
      if (window.refreshActiveCountries) {
        window.refreshActiveCountries();
      }
      return;
    }

    unis.forEach(u => {
      const card = document.createElement("div");
      card.className = `entity-card ${selectedUniIds.has(u.id) ? 'card-selected' : ''}`;
      card.setAttribute("data-id", u.id);

      card.innerHTML = `
        <div class="card-select-wrap">
          <input type="checkbox" class="card-checkbox uni-card-check" data-id="${u.id}" ${selectedUniIds.has(u.id) ? 'checked' : ''} />
        </div>
        <div class="card-content">
          <h4>${u.name}</h4>
          <p>${u.city ? u.city + ' • ' : ''}${u.deadline ? 'Deadline: ' + u.deadline : 'No deadline set'}</p>
        </div>
        <button class="icon-btn-sm btn-uni-context" data-id="${u.id}" title="Actions">•••</button>
      `;

      card.addEventListener("click", e => {
        if (e.target.closest(".card-select-wrap") || e.target.closest(".btn-uni-context")) return;
        window.onUniversitySelected(u);
      });

      const checkbox = card.querySelector(".uni-card-check");
      checkbox.addEventListener("click", e => {
        e.stopPropagation();
        toggleSelection(u.id, checkbox.checked);
      });

      const menuBtn = card.querySelector(".btn-uni-context");
      menuBtn.addEventListener("click", e => {
        e.stopPropagation();
        showContextMenu(u, menuBtn);
      });

      countryUniList.appendChild(card);
    });

    updateBatchToolbar();
  }

  function toggleSelection(uniId, isChecked) {
    const id = parseInt(uniId);
    if (isChecked) selectedUniIds.add(id);
    else selectedUniIds.delete(id);

    const card = countryUniList.querySelector(`.entity-card[data-id="${id}"]`);
    if (card) {
      card.classList.toggle("card-selected", isChecked);
    }
    updateBatchToolbar();
  }

  function updateBatchToolbar() {
    const totalCount = countryUniList.querySelectorAll(".entity-card").length;
    const selectedCount = selectedUniIds.size;

    if (selectedCount > 0) {
      uniBatchToolbar.classList.remove("hidden");
      batchSelectedCount.innerText = `${selectedCount} selected`;
      checkSelectAllUnis.checked = totalCount > 0 && selectedCount === totalCount;
      checkSelectAllUnis.indeterminate = selectedCount > 0 && selectedCount < totalCount;
    } else {
      uniBatchToolbar.classList.add("hidden");
      checkSelectAllUnis.checked = false;
      checkSelectAllUnis.indeterminate = false;
    }
  }

  function clearSelection() {
    selectedUniIds.clear();
    countryUniList.querySelectorAll(".entity-card").forEach(c => c.classList.remove("card-selected"));
    countryUniList.querySelectorAll(".uni-card-check").forEach(c => c.checked = false);
    updateBatchToolbar();
  }

  function showContextMenu(uni, anchorBtn) {
    activeContextMenuUni = uni;
    const rect = anchorBtn.getBoundingClientRect();

    uniContextMenu.style.top = `${rect.bottom + 4}px`;
    uniContextMenu.style.left = `${Math.min(rect.left - 80, window.innerWidth - 160)}px`;

    cmenuOpenUrl.style.display = uni.portal_url ? "flex" : "none";
    uniContextMenu.classList.remove("hidden");
  }

  function hideContextMenu() {
    uniContextMenu.classList.add("hidden");
    activeContextMenuUni = null;
  }

  return {
    load,
    clearSelection,
    hideContextMenu
  };
})();