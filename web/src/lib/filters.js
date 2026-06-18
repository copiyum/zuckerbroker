export function inBbox(l, [minLng, minLat, maxLng, maxLat]) {
  return l.lng >= minLng && l.lng <= maxLng && l.lat >= minLat && l.lat <= maxLat;
}
function bhkNum(l) { const m = String(l.bhk || "").match(/(\d+)/); return m ? parseInt(m[1], 10) : null; }
function furnishClass(l) {
  const s = String(l.furnishing || "").toLowerCase();
  if (s.includes("semi")) return "semi";
  if (s.includes("unfurnish") || s.includes("no furnish")) return "unfurnished";
  if (s.includes("furnish")) return "furnished";
  return null;
}
export function applyFilters(list, f = {}) {
  return list.filter((l) => {
    if (f.rentMin != null && (l.rent == null || l.rent < f.rentMin)) return false;
    if (f.rentMax != null && (l.rent == null || l.rent > f.rentMax)) return false;
    if (f.bhk && f.bhk.length) {
      const n = bhkNum(l);
      if (!f.bhk.some((v) => (v === "4+" ? n >= 4 : String(n) === v))) return false;
    }
    if (f.type && f.type.length && !f.type.includes(l.listing_type)) return false;
    if (f.furnishing && f.furnishing.length && !f.furnishing.includes(furnishClass(l))) return false;
    if (f.hideFemaleOnly && l.audience === "female_only") return false;
    return true;
  });
}
export function byDistance(list, [clng, clat]) {
  const d = (l) => (l.lng - clng) ** 2 + (l.lat - clat) ** 2;
  return [...list].sort((a, b) => d(a) - d(b));
}
export function matchPlace(query, list) {
  const q = (query || "").trim().toLowerCase(); if (!q) return null;
  let best = null, bestScore = -1;
  for (const l of list) {
    const loc = String(l.location || "").toLowerCase(); if (!loc) continue;
    let s = loc === q ? 100 : loc.startsWith(q) ? 50 : loc.includes(q) ? 25 : 0;
    if (s > bestScore) { bestScore = s; best = l; }
  }
  return bestScore > 0 ? best : null;
}
