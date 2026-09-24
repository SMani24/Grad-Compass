/**
 * Grad Compass - Operational Pipeline & To-Do Dashboard
 * Handles tasks, faculty outreach radar, and university admissions pipeline.
 */

document.addEventListener("DOMContentLoaded", () => {
  const tabButtons = document.querySelectorAll(".pipeline-tab-bar .tab-btn");
  const tabPanes = document.querySelectorAll(".pipeline-content .tab-pane");

  // Task Elements
  const tasksContainer = document.getElementById("tasks-container");
  const inputTaskTitle = document.getElementById("input-task-title");
  const inputTaskDue = document.getElementById("input-task-due");
  const btnCreateTask = document.getElementById("btn-create-task");

  // Outreach Elements
  const outreachContainer = document.getElementById("outreach-grid-container");
  const filterOutreach = document.getElementById("filter-outreach-status");

  // Tab Navigation
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const target = document.getElementById(btn.getAttribute("data-tab"));
      if (target) target.classList.add("active");

      window.loadPipelineTab(btn.getAttribute("data-tab"));
    });
  });

  // Global tab loader exposed for app.js state changes
  window.loadPipelineTab = function(tabId = "tab-tasks") {
    // Sync tab buttons active state
    tabButtons.forEach(btn => {
      if (btn.getAttribute("data-tab") === tabId) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    tabPanes.forEach(pane => {
      if (pane.id === tabId) {
        pane.classList.add("active");
      } else {
        pane.classList.remove("active");
      }
    });

    if (tabId === "tab-tasks") renderTasks();
    if (tabId === "tab-outreach") renderOutreach();
    if (tabId === "tab-admissions") renderAdmissionsBoard();
  };

  // --- 1. Tasks Management ---
  async function renderTasks() {
    if (!window.pywebview || !window.pywebview.api || !tasksContainer) return;
    const tasks = await window.pywebview.api.get_tasks();
    tasksContainer.innerHTML = "";

    if (tasks.length === 0) {
      tasksContainer.innerHTML = `<p style="font-size:13px; color:#8e8e93; margin-top:10px;">No to-dos yet. Add one above!</p>`;
      return;
    }

    tasks.forEach(t => {
      const item = document.createElement("div");
      item.className = `task-item ${t.is_completed ? 'completed' : ''}`;
      item.innerHTML = `
        <div class="task-left">
          <input type="checkbox" class="task-checkbox" ${t.is_completed ? 'checked' : ''} />
          <div>
            <span class="task-title">${t.title}</span>
            ${t.due_date ? `<span class="task-due">📅 Due: ${t.due_date}</span>` : ''}
          </div>
        </div>
        <button class="icon-btn task-del" title="Delete Task">✕</button>
      `;

      item.querySelector(".task-checkbox").addEventListener("change", async e => {
        await window.pywebview.api.toggle_task(t.id, e.target.checked);
        renderTasks();
      });

      item.querySelector(".task-del").addEventListener("click", async () => {
        await window.pywebview.api.delete_task(t.id);
        renderTasks();
      });

      tasksContainer.appendChild(item);
    });
  }

  if (btnCreateTask) {
    btnCreateTask.addEventListener("click", async () => {
      const title = inputTaskTitle.value.trim();
      const due = inputTaskDue.value;
      if (!title) return;

      await window.pywebview.api.add_task(title, due);
      inputTaskTitle.value = "";
      inputTaskDue.value = "";
      renderTasks();
    });
  }

  // --- 2. Outreach Radar ---
  async function renderOutreach() {
    if (!window.pywebview || !window.pywebview.api || !outreachContainer) return;
    const allProfs = await window.pywebview.api.get_outreach_professors();
    const filter = filterOutreach ? filterOutreach.value : "ALL";

    const filtered = filter === "ALL" 
      ? allProfs 
      : allProfs.filter(p => p.outreach_status === filter);

    outreachContainer.innerHTML = "";
    if (filtered.length === 0) {
      outreachContainer.innerHTML = `<p style="font-size:13px; color:#8e8e93; grid-column:1/-1;">No contacts match the selected status.</p>`;
      return;
    }

    filtered.forEach(p => {
      const card = document.createElement("div");
      card.className = "outreach-card";
      card.innerHTML = `
        <div>
          <h4>${p.name}</h4>
          <div class="outreach-card-sub">${p.university_name} (${p.country_code})</div>
          <p style="font-size:12px; margin-bottom:12px;">${p.research_interests || 'No research specified'}</p>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <select class="form-select prof-status-select" style="font-size:12px; padding:4px 8px;">
            <option value="Not Contacted" ${p.outreach_status === 'Not Contacted' ? 'selected' : ''}>Not Contacted</option>
            <option value="Cold Emailed" ${p.outreach_status === 'Cold Emailed' ? 'selected' : ''}>Cold Emailed</option>
            <option value="Follow-up Needed" ${p.outreach_status === 'Follow-up Needed' ? 'selected' : ''}>Follow-up Needed</option>
            <option value="Replied / In Touch" ${p.outreach_status === 'Replied / In Touch' ? 'selected' : ''}>Replied / In Touch</option>
            <option value="Interview Scheduled" ${p.outreach_status === 'Interview Scheduled' ? 'selected' : ''}>Interview Scheduled</option>
          </select>
          ${p.email ? `<a href="mailto:${p.email}" class="btn-text" style="font-size:12px;">Email</a>` : ''}
        </div>
      `;

      card.querySelector(".prof-status-select").addEventListener("change", async e => {
        await window.pywebview.api.update_professor_status(p.id, e.target.value);
      });

      outreachContainer.appendChild(card);
    });
  }

  if (filterOutreach) {
    filterOutreach.addEventListener("change", renderOutreach);
  }

  // --- 3. Admissions Lifecycle Kanban ---
  async function renderAdmissionsBoard() {
    if (!window.pywebview || !window.pywebview.api) return;
    const unis = await window.pywebview.api.get_pipeline_universities();

    const cols = {
      "Researching": document.getElementById("col-researching"),
      "Applying": document.getElementById("col-applying"),
      "Submitted": document.getElementById("col-submitted"),
      "Decided": document.getElementById("col-decided")
    };

    const counts = { "Researching": 0, "Applying": 0, "Submitted": 0, "Decided": 0 };
    Object.values(cols).forEach(c => { if (c) c.innerHTML = ""; });

    unis.forEach(u => {
      let bucket = u.status || "Researching";
      if (bucket === "Accepted" || bucket === "Rejected") bucket = "Decided";
      if (!cols[bucket]) bucket = "Researching";

      counts[bucket]++;

      const card = document.createElement("div");
      card.className = "kanban-item";
      card.innerHTML = `
        <h5>${u.name}</h5>
        <div class="kanban-meta">${u.country_name || u.country_code} ${u.deadline ? '• 📅 ' + u.deadline : ''}</div>
        <div class="kanban-actions">
          <select class="form-select uni-status-select" style="font-size:11px; padding:3px 6px;">
            <option value="Researching" ${u.status === 'Researching' ? 'selected' : ''}>Researching</option>
            <option value="Applying" ${u.status === 'Applying' ? 'selected' : ''}>Applying</option>
            <option value="Submitted" ${u.status === 'Submitted' ? 'selected' : ''}>Submitted</option>
            <option value="Accepted" ${u.status === 'Accepted' ? 'selected' : ''}>Accepted</option>
            <option value="Rejected" ${u.status === 'Rejected' ? 'selected' : ''}>Rejected</option>
          </select>
        </div>
      `;

      card.querySelector(".uni-status-select").addEventListener("change", async e => {
        await window.pywebview.api.update_university_status(u.id, e.target.value);
        renderAdmissionsBoard();
      });

      if (cols[bucket]) cols[bucket].appendChild(card);
    });

    const setColCount = (id, count) => {
      const el = document.getElementById(id);
      if (el) el.innerText = count;
    };

    setColCount("count-researching", counts["Researching"]);
    setColCount("count-applying", counts["Applying"]);
    setColCount("count-submitted", counts["Submitted"]);
    setColCount("count-decided", counts["Decided"]);
  }
});