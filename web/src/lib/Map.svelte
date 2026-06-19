<script>
  import { onMount } from "svelte";
  import maplibregl from "maplibre-gl";
  import { store, getListings } from "./data.svelte.js";

  let { onlist, onpin, onhover, selectedId = null, hoverId = null, theme = "light" } = $props();
  let map;
  const STYLES = {
    light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  };
  let appliedTheme = theme;

  // compact money: 30000 -> ₹30k, 125000 -> ₹1.3L
  const pill = (n) =>
    n == null ? "—"
    : n >= 100000 ? "₹" + (n / 100000).toFixed(n % 100000 ? 1 : 0) + "L"
    : n >= 1000 ? "₹" + Math.round(n / 1000) + "k"
    : "₹" + n;

  function bbox() { const b = map.getBounds(); return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]; }
  function gj(list) {
    return { type: "FeatureCollection", features: list.map((l) => ({
      type: "Feature", geometry: { type: "Point", coordinates: [l.lng, l.lat] },
      properties: { id: l.id, label: pill(l.rent) } })) };
  }

  const markers = {};          // key -> { marker, el }
  let onScreen = {};

  function priceEl(id, label) {
    const el = document.createElement("div");
    el.className = "lab";
    el.dataset.id = id;
    el.innerHTML = `<span>${label}</span>`;
    el.addEventListener("click", (e) => { e.stopPropagation(); onpin?.(id); });
    el.addEventListener("mouseenter", () => onhover?.(id));
    el.addEventListener("mouseleave", () => onhover?.(null));
    return el;
  }
  function clusterEl(cid, count, coords) {
    const el = document.createElement("div");
    el.className = "clus";
    el.textContent = count >= 1000 ? (count / 1000).toFixed(1) + "k" : count;
    el.addEventListener("click", () => {
      map.getSource("listings").getClusterExpansionZoom(cid).then((z) =>
        map.easeTo({ center: coords, zoom: z, duration: 600 }));
    });
    return el;
  }

  function applyStates() {
    for (const k in onScreen) {
      const el = onScreen[k].el;
      if (!el.classList.contains("lab")) continue;
      const sel = k === selectedId, hov = k === hoverId;
      el.classList.toggle("sel", sel);
      el.classList.toggle("hov", hov);
      el.style.zIndex = sel ? "4" : hov ? "3" : "";
    }
  }

  function updateMarkers() {
    const next = {};
    for (const f of map.querySourceFeatures("listings")) {
      const p = f.properties, coords = f.geometry.coordinates;
      const key = p.cluster ? "c" + p.cluster_id : p.id;
      let m = markers[key];
      if (!m) {
        const el = p.cluster ? clusterEl(p.cluster_id, p.point_count, coords) : priceEl(p.id, p.label);
        m = markers[key] = { el, marker: new maplibregl.Marker({ element: el }).setLngLat(coords) };
      }
      next[key] = m;
      if (!onScreen[key]) m.marker.addTo(map);
    }
    for (const k in onScreen) if (!next[k]) onScreen[k].marker.remove();
    onScreen = next;
    applyStates();
  }

  // map move updates only the in-view list (sidebar) + source; never selects/pans (smooth)
  function refresh() {
    store.list = getListings(bbox(), store.filters);
    map.getSource("listings")?.setData(gj(store.list));
    onlist?.(store.list);
  }
  export function flyTo(l) { if (l && map) map.flyTo({ center: [l.lng, l.lat], zoom: Math.max(map.getZoom(), 15), speed: 0.9 }); }
  export function applyFiltersNow() { if (map && map.loaded()) refresh(); }

  let t;
  const debounce = () => { clearTimeout(t); t = setTimeout(refresh, 200); };

  // source + invisible tiling layer (re-added after every setStyle, which wipes them)
  function ensureSource() {
    if (map.getSource("listings")) return;
    map.addSource("listings", { type: "geojson", data: gj(store.list), cluster: true, clusterRadius: 60, clusterMaxZoom: 14 });
    map.addLayer({ id: "_src", type: "circle", source: "listings", paint: { "circle-radius": 0, "circle-opacity": 0 } });
  }

  $effect(() => { selectedId; hoverId; if (map) applyStates(); });
  // re-render the source once listings.json finishes loading (data arrives after map 'load')
  $effect(() => { if (store.all.length && map && map.getSource("listings")) refresh(); });
  // light/dark switch — setStyle wipes sources, so re-add + refresh on style.load
  $effect(() => {
    const t = theme;                          // read first so it's always tracked
    if (!map || t === appliedTheme) return;
    appliedTheme = t;
    map.setStyle(STYLES[t]);
    map.once("style.load", () => { ensureSource(); refresh(); });
  });

  onMount(() => {
    map = new maplibregl.Map({ container: "map", style: STYLES[theme], center: [77.62, 12.95], zoom: 11 });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      ensureSource();
      map.on("render", () => { if (map.isSourceLoaded("listings")) updateMarkers(); });
      map.on("moveend", debounce);
      refresh();
    });
  });
</script>

<div id="map"></div>
