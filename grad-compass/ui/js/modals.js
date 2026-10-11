/**
 * Grad Compass - Modals & Dialogs Controller
 * Manages adding/editing universities & professors, and delete confirmations.
 */

window.Modals = (() => {
  let onUniSavedCallback = null;
  let onProfSavedCallback = null;
  let onConfirmCallback = null;

  let activeCountryContext = { code: "", name: "" };
  let activeUniContextId = null;

  // DOM references resolved safely on invocation
  const getEl = id => document.getElementById(id);

  document.addEventListener("DOMContentLoaded", () => {
    // Global Dismiss Handlers
    document.querySelectorAll(".btn-modal-dismiss").forEach(btn => {
      btn.addEventListener("click", e => {
        const modal = e.target.closest(".modal-backdrop");
        if (modal) modal.classList.add("hidden");
      });
    });

    // University Submit Handler
    const btnSubmitUni = getEl("btn-submit-uni");
    if (btnSubmitUni) {
      btnSubmitUni.addEventListener("click", async () => {
        const nameInput = getEl("input-uni-name");
        const cityInput = getEl("input-uni-city");
        const deadlineInput = getEl("input-uni-deadline");
        const urlInput = getEl("input-uni-url");
        const idInput = getEl("input-uni-id");
        const uniModal = getEl("uni-modal");

        const name = nameInput.value.trim();
        const city = cityInput.value.trim();
        const deadline = deadlineInput.value;
        const url = urlInput.value.trim();
        const uniId = idInput.value;

        if (!name) {
          nameInput.focus();
          return;
        }

        btnSubmitUni.disabled = true;

        try {
          if (uniId) {
            // Edit Mode
            const updated = await window.pywebview.api.update_university(
              parseInt(uniId), name, city, deadline, url, activeCountryContext.name
            );
            if (uniModal) uniModal.classList.add("hidden");
            if (onUniSavedCallback) onUniSavedCallback(updated, false);
          } else {
            // Add Mode
            const created = await window.pywebview.api.add_university(
              activeCountryContext.code, activeCountryContext.name, name, city, deadline, url
            );
            if (uniModal) uniModal.classList.add("hidden");
            if (onUniSavedCallback) onUniSavedCallback(created, true);
          }
        } catch (err) {
          console.error("Failed to save university:", err);
        } finally {
          btnSubmitUni.disabled = false;
        }
      });
    }

    // Professor Submit Handler
    const btnSubmitProf = getEl("btn-submit-prof");
    if (btnSubmitProf) {
      btnSubmitProf.addEventListener("click", async () => {
        const nameInput = getEl("input-prof-name");
        const emailInput = getEl("input-prof-email");
        const researchInput = getEl("input-prof-research");
        const statusSelect = getEl("select-prof-status");
        const idInput = getEl("input-prof-id");
        const profModal = getEl("prof-modal");

        const name = nameInput.value.trim();
        const email = emailInput.value.trim();
        const research = researchInput.value.trim();
        const status = statusSelect.value;
        const profId = idInput.value;

        if (!name) {
          nameInput.focus();
          return;
        }

        btnSubmitProf.disabled = true;

        try {
          if (profId) {
            // Edit Mode
            const updated = await window.pywebview.api.update_professor(
              parseInt(profId), name, email, research, status
            );
            if (profModal) profModal.classList.add("hidden");
            if (onProfSavedCallback) onProfSavedCallback(updated, false);
          } else {
            // Add Mode
            const created = await window.pywebview.api.add_professor(
              activeUniContextId, name, email, research, status
            );
            if (profModal) profModal.classList.add("hidden");
            if (onProfSavedCallback) onProfSavedCallback(created, true);
          }
        } catch (err) {
          console.error("Failed to save professor:", err);
        } finally {
          btnSubmitProf.disabled = false;
        }
      });
    }

    // Confirmation Action Handler
    const btnConfirmAction = getEl("btn-confirm-action");
    const confirmModal = getEl("confirm-modal");
    if (btnConfirmAction) {
      btnConfirmAction.addEventListener("click", async () => {
        btnConfirmAction.disabled = true;
        try {
          if (onConfirmCallback) await onConfirmCallback();
        } catch (err) {
          console.error("Confirm action failed:", err);
        } finally {
          btnConfirmAction.disabled = false;
          if (confirmModal) confirmModal.classList.add("hidden");
        }
      });
    }
  });

  // --- Public APIs ---
  function openAddUniversity(countryCode, countryName, onSaved) {
    activeCountryContext = { code: countryCode, name: countryName };
    onUniSavedCallback = onSaved;

    const get = id => document.getElementById(id);
    const uniModal = get("uni-modal");
    get("input-uni-id").value = "";
    get("input-uni-name").value = "";
    get("input-uni-city").value = "";
    get("input-uni-deadline").value = "";
    get("input-uni-url").value = "";

    get("uni-modal-title").innerText = `Add University (${countryName})`;
    get("btn-submit-uni").innerText = "Save & Fetch Info";
    if (uniModal) uniModal.classList.remove("hidden");
    get("input-uni-name").focus();
  }

  function openEditUniversity(uni, countryName, onSaved) {
    activeCountryContext = { code: uni.country_code, name: countryName };
    onUniSavedCallback = onSaved;

    const get = id => document.getElementById(id);
    const uniModal = get("uni-modal");
    get("input-uni-id").value = uni.id;
    get("input-uni-name").value = uni.name || "";
    get("input-uni-city").value = uni.city || "";
    get("input-uni-deadline").value = uni.deadline || "";
    get("input-uni-url").value = uni.portal_url || "";

    get("uni-modal-title").innerText = "Edit University";
    get("btn-submit-uni").innerText = "Save Changes";
    if (uniModal) uniModal.classList.remove("hidden");
    get("input-uni-name").focus();
  }

  function openAddProfessor(uniId, onSaved) {
    activeUniContextId = uniId;
    onProfSavedCallback = onSaved;

    const get = id => document.getElementById(id);
    const profModal = get("prof-modal");
    get("input-prof-id").value = "";
    get("input-prof-name").value = "";
    get("input-prof-email").value = "";
    get("input-prof-research").value = "";
    get("select-prof-status").value = "Not Contacted";

    get("prof-modal-title").innerText = "Add Faculty Contact";
    get("btn-submit-prof").innerText = "Save Contact";
    if (profModal) profModal.classList.remove("hidden");
    get("input-prof-name").focus();
  }

  function openEditProfessor(prof, onSaved) {
    activeUniContextId = prof.university_id;
    onProfSavedCallback = onSaved;

    const get = id => document.getElementById(id);
    const profModal = get("prof-modal");
    get("input-prof-id").value = prof.id;
    get("input-prof-name").value = prof.name || "";
    get("input-prof-email").value = prof.email || "";
    get("input-prof-research").value = prof.research_interests || "";
    get("select-prof-status").value = prof.outreach_status || "Not Contacted";

    get("prof-modal-title").innerText = "Edit Faculty Contact";
    get("btn-submit-prof").innerText = "Save Changes";
    if (profModal) profModal.classList.remove("hidden");
    get("input-prof-name").focus();
  }

  function showConfirm({ title = "Confirm Deletion", message = "Are you sure?", confirmText = "Delete", onConfirm }) {
    const get = id => document.getElementById(id);
    const confirmModal = get("confirm-modal");
    get("confirm-modal-title").innerText = title;
    get("confirm-modal-message").innerText = message;
    get("btn-confirm-action").innerText = confirmText;
    onConfirmCallback = onConfirm;

    if (confirmModal) confirmModal.classList.remove("hidden");
  }

  return {
    openAddUniversity,
    openEditUniversity,
    openAddProfessor,
    openEditProfessor,
    showConfirm
  };
})();