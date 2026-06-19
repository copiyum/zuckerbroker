import { inBbox, applyFilters, byDistance, matchPlace } from "./filters.js";

export const store = $state({ all: [], list: [], filters: {}, selectedId: null, total: 0, loaded: false,
  saved: {}, theme: "light" });

export async function load() {
  try { store.saved = JSON.parse(localStorage.getItem("zb-saved") || "{}"); } catch { /* ignore */ }
  store.theme = localStorage.getItem("zb-theme") || "light";
  store.all = await fetch("/listings.json").then((r) => r.json());
  store.total = store.all.length;
  store.loaded = true;
}
export function toggleSaved(id) {
  const s = { ...store.saved };
  if (s[id]) delete s[id]; else s[id] = 1;
  store.saved = s;
  try { localStorage.setItem("zb-saved", JSON.stringify(s)); } catch { /* ignore */ }
}
export function setTheme(t) {
  store.theme = t;
  try { localStorage.setItem("zb-theme", t); } catch { /* ignore */ }
}
export function getListings(bbox, filters, center) {
  let l = store.all.filter((x) => inBbox(x, bbox));
  l = applyFilters(l, filters);
  if (center) l = byDistance(l, center);
  return l;
}
export function searchPlace(q) { return matchPlace(q, store.all); }
