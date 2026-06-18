import { inBbox, applyFilters, byDistance, matchPlace } from "./filters.js";

export const store = $state({ all: [], list: [], filters: {}, selectedId: null, total: 0 });

export async function load() {
  store.all = await fetch("/listings.json").then((r) => r.json());
  store.total = store.all.length;
}
export function getListings(bbox, filters, center) {
  let l = store.all.filter((x) => inBbox(x, bbox));
  l = applyFilters(l, filters);
  if (center) l = byDistance(l, center);
  return l;
}
export function searchPlace(q) { return matchPlace(q, store.all); }
