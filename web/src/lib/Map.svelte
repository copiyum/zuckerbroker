<script>
  import { onMount } from "svelte";
  import maplibregl from "maplibre-gl";
  import { store, getListings } from "./data.svelte.js";

  let { onlist, onpin, selectedId = null } = $props();
  let map;
  const LIGHT = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

  function bbox() { const b = map.getBounds(); return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]; }
  function gj(list) {
    return { type: "FeatureCollection", features: list.map((l) => ({
      type: "Feature", geometry: { type: "Point", coordinates: [l.lng, l.lat] },
      properties: { id: l.id } })) };
  }
  // map move only updates the in-view list (sidebar). It never selects or pans — keeps panning smooth.
  function refresh() {
    store.list = getListings(bbox(), store.filters);
    map.getSource("listings")?.setData(gj(store.list));
    onlist?.(store.list);
  }
  export function flyTo(l) { if (l && map) map.flyTo({ center: [l.lng, l.lat], zoom: Math.max(map.getZoom(), 15), speed: 0.9 }); }
  export function applyFiltersNow() { if (map && map.loaded()) refresh(); }

  let t;
  const debounce = () => { clearTimeout(t); t = setTimeout(refresh, 200); };

  // Paint ONLY the currently-selected pin red (no zoom/pan on selection).
  $effect(() => {
    const id = selectedId ?? "__none__";
    if (!map || !map.getLayer || !map.getLayer("pt")) return;
    const sel = ["==", ["get", "id"], id];
    map.setPaintProperty("pt", "circle-color", ["case", sel, "#e0143c", "#0066cc"]);
    map.setPaintProperty("pt", "circle-radius", ["case", sel, 11, 7]);
    map.setPaintProperty("pt", "circle-stroke-width", ["case", sel, 3, 2]);
  });

  onMount(() => {
    map = new maplibregl.Map({ container: "map", style: LIGHT, center: [77.62, 12.95], zoom: 11 });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      map.addSource("listings", { type: "geojson", data: gj([]), cluster: true, clusterRadius: 50, clusterMaxZoom: 14 });
      map.addLayer({ id: "clusters", type: "circle", source: "listings", filter: ["has", "point_count"],
        paint: { "circle-color": "#0066cc", "circle-opacity": 0.9,
          "circle-radius": ["step", ["get", "point_count"], 16, 50, 22, 200, 30] } });
      map.addLayer({ id: "cluster-count", type: "symbol", source: "listings", filter: ["has", "point_count"],
        layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Open Sans Regular"] },
        paint: { "text-color": "#fff" } });
      map.addLayer({ id: "pt", type: "circle", source: "listings", filter: ["!", ["has", "point_count"]],
        paint: { "circle-color": "#0066cc", "circle-radius": 7, "circle-stroke-width": 2, "circle-stroke-color": "#fff" } });
      map.on("click", "clusters", (e) => {
        const f = map.queryRenderedFeatures(e.point, { layers: ["clusters"] })[0];
        map.getSource("listings").getClusterExpansionZoom(f.properties.cluster_id).then((z) =>
          map.easeTo({ center: f.geometry.coordinates, zoom: z })); });
      map.on("click", "pt", (e) => { onpin?.(e.features[0].properties.id); });
      map.on("mouseenter", "clusters", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseenter", "pt", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("moveend", debounce);
      refresh();
    });
  });
</script>

<div id="map"></div>
