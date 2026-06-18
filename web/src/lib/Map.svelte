<script>
  import { onMount } from "svelte";
  import maplibregl from "maplibre-gl";
  import { store, getListings } from "./data.js";

  let { onlist, selectedId } = $props();
  let map;
  const DARK = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

  function bbox() { const b = map.getBounds(); return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]; }
  function center() { const c = map.getCenter(); return [c.lng, c.lat]; }
  function gj(list) {
    return { type: "FeatureCollection", features: list.map((l) => ({
      type: "Feature", geometry: { type: "Point", coordinates: [l.lng, l.lat] },
      properties: { id: l.id } })) };
  }
  function refresh() {
    store.list = getListings(bbox(), store.filters, center());
    map.getSource("listings")?.setData(gj(store.list));
    onlist?.(store.list);
  }
  export function panTo(l) { if (l && map) map.easeTo({ center: [l.lng, l.lat] }); }
  export function applyFiltersNow() { if (map && map.loaded()) refresh(); }

  let t;
  const debounce = () => { clearTimeout(t); t = setTimeout(refresh, 200); };

  onMount(() => {
    map = new maplibregl.Map({ container: "map", style: DARK, center: [77.62, 12.95], zoom: 11 });
    window.__map_flyto = (l) => map.flyTo({ center: [l.lng, l.lat], zoom: 14 });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }));
    map.on("load", () => {
      map.addSource("listings", { type: "geojson", data: gj([]), cluster: true, clusterRadius: 50, clusterMaxZoom: 14 });
      map.addLayer({ id: "clusters", type: "circle", source: "listings", filter: ["has", "point_count"],
        paint: { "circle-color": "#0066cc", "circle-radius": ["step", ["get", "point_count"], 16, 50, 22, 200, 30] } });
      map.addLayer({ id: "cluster-count", type: "symbol", source: "listings", filter: ["has", "point_count"],
        layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Open Sans Regular"] },
        paint: { "text-color": "#fff" } });
      map.addLayer({ id: "pt", type: "circle", source: "listings", filter: ["!", ["has", "point_count"]],
        paint: { "circle-color": "#0066cc", "circle-radius": 7, "circle-stroke-width": 2, "circle-stroke-color": "#fff" } });
      map.on("click", "clusters", (e) => {
        const f = map.queryRenderedFeatures(e.point, { layers: ["clusters"] })[0];
        map.getSource("listings").getClusterExpansionZoom(f.properties.cluster_id).then((z) =>
          map.easeTo({ center: f.geometry.coordinates, zoom: z })); });
      map.on("click", "pt", (e) => { selectedId?.set?.(e.features[0].properties.id); });
      map.on("mouseenter", "clusters", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseenter", "pt", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("moveend", debounce);
      refresh();
    });
  });
</script>

<div id="map"></div>
