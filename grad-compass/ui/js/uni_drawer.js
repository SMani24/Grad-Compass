/**
 * Grad Compass - University Inspector Drawer Controller
 * Manages hero banners, vault documents, faculty roster, and inspector header actions.
 */

window.UniDrawer = (() => {
  const uniDrawerTitle = document.getElementById("uni-drawer-title");
  const uniDrawerSubtitle = document.getElementById("uni-drawer-subtitle");
  const heroBanner = document.getElementById("uni-hero-banner");
  const uniAttachmentsList = document.getElementById("uni-attachments-list");
  const professorsContainer = document.getElementById("professors-container");

  const btnEditUni = document.getElementById("btn-edit-uni");
  const btnDeleteUni = document.getElementById("btn-delete-uni");
  const btnAttachUniFile = document.getElementById("btn-attach-uni-file");
  const btnShowAddProf = document.getElementById("btn-show-add-prof");

  let activeUniversity = null;
  let activeCountry = null;

  document.addEventListener("DOMContentLoaded", () => {
    // Edit University
    btnEditUni.addEventListener("click", () => {
      if (!activeUniversity || !activeCountry) return;
      window.Modals.openEditUniversity(activeUniversity, activeCountry.name, updated => {
        load(updated, activeCountry);
        window.CountryDrawer.load(activeCountry.code, activeCountry.name);
      });
    });

    // Delete University
    btnDeleteUni.addEventListener("click", () => {
      if (!activeUniversity || !activeCountry) return;
      window.Modals.showConfirm({
        title: "Delete University",
        message: `Are you sure you want to delete ${activeUniversity.name}? All attached faculty, documents, and tasks will be permanently removed.`,
        confirmText: "Delete",
        onConfirm: async () => {
          await window.pywebview.api.delete_university(activeUniversity.id);
          if (window.refreshActiveCountries) {
            await window.refreshActiveCountries();
          }
          window.navigateBackToCountry();
        }
      });
    });

    // Add Faculty Contact
    btnShowAddProf.addEventListener("click", () => {
      if (!activeUniversity) return;
      window.Modals.openAddProfessor(activeUniversity.id, () => {
        loadProfessors(activeUniversity.id);
      });
    });

    // Attach University Document
    btnAttachUniFile.addEventListener("click", async () => {
      if (!activeUniversity) return;
      const res = await window.pywebview.api.pick_and_attach_file("university", activeUniversity.id);
      if (res.success) loadAttachments("university", activeUniversity.id);
    });
  });

  async function load(uni, country) {
    activeUniversity = uni;
    activeCountry = country;

    uniDrawerTitle.innerHTML = `<span>${uni.name}</span>`;
    uniDrawerSubtitle.innerText = uni.city ? `${uni.city}, ${country.name}` : country.name;

    if (heroBanner) {
      if (uni.image_url) {
        heroBanner.style.backgroundImage = `url('${uni.image_url}')`;
        heroBanner.classList.remove("hidden");
      } else {
        heroBanner.classList.add("hidden");
      }
    }

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
      card.style.flexDirection = "column";
      card.style.alignItems = "stretch";
      const statusClass = (p.outreach_status || "Not-Contacted").replace(/[^a-zA-Z0-9]/g, "-");

      card.innerHTML = `
        <div class="card-header-row">
          <h4>${p.name}</h4>
          <div class="card-actions-row">
            <button class="icon-btn-sm btn-prof-edit" title="Edit Contact">✏️</button>
            <button class="icon-btn-sm icon-btn-danger btn-prof-delete" title="Delete Contact">🗑️</button>
          </div>
        </div>
        <p>${p.research_interests || 'No research focus specified'}</p>
        <div><span class="status-pill ${statusClass}">${p.outreach_status}</span></div>
        <div style="margin-top:8px; display:flex; gap:10px;">
          ${p.email ? `<a href="mailto:${p.email}" class="btn-text" style="font-size:12px;">Email</a>` : ''}
          <button class="btn-text btn-prof-attach" data-id="${p.id}" style="font-size:12px;">+ Attach File</button>
        </div>
        <div class="file-chip-container" id="prof-files-${p.id}"></div>
      `;

      card.querySelector(".btn-prof-edit").addEventListener("click", e => {
        e.stopPropagation();
        window.Modals.openEditProfessor(p, () => loadProfessors(uniId));
      });

      card.querySelector(".btn-prof-delete").addEventListener("click", e => {
        e.stopPropagation();
        window.Modals.showConfirm({
          title: "Delete Faculty Contact",
          message: `Are you sure you want to remove ${p.name}? All documents attached to this contact will be deleted.`,
          confirmText: "Delete",
          onConfirm: async () => {
            await window.pywebview.api.delete_professor(p.id);
            loadProfessors(uniId);
          }
        });
      });

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
      else if (activeUniversity) loadAttachments("university", activeUniversity.id);
    });

    return chip;
  }

  return {
    load
  };
})();