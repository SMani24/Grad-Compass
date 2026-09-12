document.addEventListener("DOMContentLoaded", () => {
  const mapContainer = document.getElementById("map-container");
  const gatewayOverlay = document.getElementById("gateway-overlay");
  const btnExploreMap = document.getElementById("btn-explore-map");
  const inspectorDrawer = document.getElementById("inspector-drawer");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");
  const drawerTitle = document.getElementById("drawer-title");
  const drawerSubtitle = document.getElementById("drawer-subtitle");

  btnExploreMap.addEventListener("click", () => {
    gatewayOverlay.classList.add("hidden");
    mapContainer.classList.remove("blurred");

    // Allow CSS transition to finish, then recalculate map dimensions
    setTimeout(() => {
      if (window.map) {
        window.map.invalidateSize();
      }
    }, 300);
  });

  window.onCountrySelected = (countryName, countryCode) => {
    drawerTitle.innerText = countryName;
    drawerSubtitle.innerText = `Country Code: ${countryCode || 'N/A'}`;
    inspectorDrawer.classList.add("open");

    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.log(`Selected: ${countryName} [${countryCode}]`);
    }
  };

  btnCloseDrawer.addEventListener("click", () => {
    inspectorDrawer.classList.remove("open");
    resetToWorldView();
  });
});