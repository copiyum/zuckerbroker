import { inBbox, applyFilters, byDistance, matchPlace } from "./filters.js";

export const store = $state({
  all: [], list: [], filters: {}, drawFilter: null, selectedId: null, total: 0, loaded: false,
  saved: {}, theme: "light",
  /* pagination */
  page: 0, pageSize: 50, hasMore: true,
});

export async function load() {
  try { store.saved = JSON.parse(localStorage.getItem("zb-saved") || "{}"); } catch { /* ignore */ }
  store.theme = localStorage.getItem("zb-theme") || "light";
  store.all = await fetch("/listings.json").then((r) => r.json());
  store.total = store.all.length;
  store.loaded = true;
  store.page = 0;
  store.hasMore = store.all.length > store.pageSize;
}
export function getSaved() {
  return Object.keys(store.saved);
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
  l = applyFilters(l, filters, store.drawFilter);
  if (center) l = byDistance(l, center);
  return l;
}
export function searchPlace(q) { return matchPlace(q, store.all); }

/* ── Pagination helpers ─────────────────────────────────── */
/** Get the current page slice from the filtered list (pure — no side effects) */
export function getPage(list) {
  const end = (store.page + 1) * store.pageSize;
  return list.slice(0, end);
}
/** Check if there are more items to load */
export function checkHasMore(list) {
  const end = (store.page + 1) * store.pageSize;
  store.hasMore = list.length > end;
}
/** Load next page */
export function nextPage() {
  store.page++;
}
/** Reset pagination (e.g. on filter change) */
export function resetPage() {
  store.page = 0;
  store.hasMore = true;
}
