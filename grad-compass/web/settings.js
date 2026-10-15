/* Display preferences belong to this local workspace, independently of research data. */
(() => {
  const scales = {standard: 1, comfortable: 1.15, large: 1.3, "extra-large": 1.5};
  const root = document.documentElement;
  const dialog = document.getElementById("settings-dialog");
  const select = document.getElementById("text-size");
  const status = document.getElementById("settings-status");
  let session;
  let saved = "standard";
  function apply(size) {
    root.style.setProperty("--text-scale", scales[size]);
    select.value = size;
  }
  function layout() {
    const toolsTop = document.querySelector(".topbar").getBoundingClientRect().bottom + 12;
    root.style.setProperty("--map-tools-top", `${toolsTop}px`);
    const tools = document.getElementById("map-selection-controls");
    const top = tools.hidden ? toolsTop + 8 : toolsTop + tools.getBoundingClientRect().height + 12;
    root.style.setProperty("--content-top", `${top}px`);
    const filters = document.querySelector(".filter-controls").getBoundingClientRect().height;
    root.style.setProperty("--mobile-list-top", `${top + filters + 14}px`);
    const panel = document.querySelector(".results-panel").getBoundingClientRect();
    root.style.setProperty("--map-controls-bottom", `${innerHeight - panel.top + 12}px`);
  }
  let layoutFrame;
  function scheduleLayout() {
    if (layoutFrame) return;
    layoutFrame = requestAnimationFrame(() => { layoutFrame = null; layout(); });
  }
  const observer = new ResizeObserver(scheduleLayout);
  observer.observe(document.querySelector(".topbar"));
  observer.observe(document.querySelector(".filter-controls"));
  observer.observe(document.querySelector(".results-panel"));
  observer.observe(document.getElementById("map-selection-controls"));
  addEventListener("resize", scheduleLayout);
  layout();
  document.getElementById("open-settings").addEventListener("click", () => dialog.showModal());
  document.getElementById("close-settings").addEventListener("click", () => dialog.close());
  async function load() {
    try {
      const response = await fetch("/api/display-preferences");
      const data = await response.json();
      if (!response.ok || !Object.hasOwn(scales, data.text_size)) throw new Error("Could not load your text-size preference.");
      session = data.session;
      saved = data.text_size;
      apply(saved);
      select.disabled = false;
      status.textContent = "Saved on this device. Applies throughout the app.";
    } catch (error) {
      status.textContent = error.message;
    }
  }
  select.addEventListener("change", async () => {
    const chosen = select.value;
    apply(chosen);
    select.disabled = true;
    status.textContent = "Saving…";
    try {
      const response = await fetch("/api/display-preferences", {
        method: "POST", headers: {"Content-Type": "application/json", "X-Grad-Compass-Session": session},
        body: JSON.stringify({text_size: chosen})
      });
      if (!response.ok) throw new Error("Could not save. Your previous text size has been restored.");
      saved = chosen;
      status.textContent = "Saved on this device. Applies throughout the app.";
    } catch (error) {
      apply(saved);
      status.textContent = error.message;
    } finally { select.disabled = false; }
  });
  load();
})();
