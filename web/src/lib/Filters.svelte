<script>
  import { onMount } from "svelte";
  import { store, searchPlace, setTheme, getSaved, toggleSaved } from "./data.svelte.js";
  let { onchange, onplace, viewMode, setViewMode } = $props();
  let q = $state("");
  let open = $state(null);
  let chipsEl;
  let popStyle = $state("");
  let showSheet = $state(false);

  const TYPE = [["entire_flat","Entire flat"],["flatmate","Flatmate"],["private_room","Private room"],["pg_hostel","PG / Hostel"]];
  const BHK = [["1","1 BHK"],["2","2 BHK"],["3","3 BHK"],["4+","4+ BHK"]];
  const FURN = [["furnished","Furnished"],["semi","Semi-furnished"],["unfurnished","Unfurnished"]];
  const RENT_BINS = [0, 5000, 8000, 10000, 12000, 15000, 18000, 20000, 25000, 30000, 40000, 50000, 75000, 100000];
  const BIN_LABELS = ["0", "5k", "8k", "10k", "12k", "15k", "18k", "20k", "25k", "30k", "40k", "50k", "75k", "1L"];

  function toggle(key, v) {
    const cur = new Set(store.filters[key] || []);
    cur.has(v) ? cur.delete(v) : cur.add(v);
    store.filters[key] = cur.size ? [...cur] : undefined;
    onchange?.();
  }
  function setRent(mn, mx) {
    store.filters.rentMin = mn ? +mn : undefined;
    store.filters.rentMax = mx ? +mx : undefined;
    onchange?.();
  }
  function active(key) { return !!store.filters[key]; }
  let activeCount = $derived(
    (store.filters.rentMin || store.filters.rentMax ? 1 : 0)
    + ["bhk", "type", "furnishing"].filter((k) => store.filters[k]?.length).length
    + (store.filters.hideFemaleOnly ? 1 : 0)
  );
  function clearAll() { store.filters = {}; open = null; onchange?.(); }
  function toggleFemale() {
    store.filters.hideFemaleOnly = store.filters.hideFemaleOnly ? undefined : true;
    onchange?.();
  }
  function search(e) {
    e.preventDefault();
    const m = searchPlace(q);
    if (m) onplace?.(m);
  }

  function togglePopup(key, e) {
    if (open === key) { open = null; }
    else { open = key; const rect = e.currentTarget.getBoundingClientRect(); popStyle = `position:fixed;top:${rect.bottom + 8}px;left:${rect.left}px;z-index:1000`; }
  }

  function toggleView(mode) { setViewMode?.(mode); }

  let savedCount = $derived(getSaved().length);

  let rentHistogram = $derived.by(() => {
    const bins = new Array(RENT_BINS.length - 1).fill(0);
    for (const l of store.all) {
      const r = l.rent;
      if (r == null) continue;
      for (let i = 0; i < RENT_BINS.length - 1; i++) {
        if (r >= RENT_BINS[i] && r < RENT_BINS[i + 1]) { bins[i]++; break; }
      }
    }
    const max = Math.max(...bins, 1);
    return bins.map((c, i) => {
      const binStart = RENT_BINS[i], binEnd = RENT_BINS[i + 1];
      const inRange = (!store.filters.rentMin || binEnd > store.filters.rentMin) &&
                      (!store.filters.rentMax || binStart < store.filters.rentMax);
      return { count: c, pct: c / max, inRange };
    });
  });

  $effect(() => {
    function handleClickOutside(e) {
      if (open && !e.target.closest('.pop') && !e.target.closest('.chip')) { open = null; }
    }
    function handleKey(e) { if (e.key === 'Escape' && open) { open = null; e.stopPropagation(); } }
    document.addEventListener('click', handleClickOutside, true);
    document.addEventListener('keydown', handleKey);
    return () => { document.removeEventListener('click', handleClickOutside, true); document.removeEventListener('keydown', handleKey); };
  });
</script>

<div class="brand"><span class="bdot"></span> zuckerbroker</div>

<form class="search" onsubmit={search}>
  <input placeholder="Locality, society, metro…" bind:value={q} aria-label="Search location" />
  <button type="submit" aria-label="Search">→</button>
</form>

<div class="chips" bind:this={chipsEl}>
  <div class="chip-group">
    <span class="chip {active('rentMin')||active('rentMax')?'on':''}" onclick={(e) => togglePopup('rent', e)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && togglePopup('rent', e)}>
      <span class="chip-icon">₹</span> Rent
    </span>
    {#each [["BHK","bhk",BHK],["Type","type",TYPE],["Furnishing","furnishing",FURN]] as [label,key,opts]}
      <span class="chip {active(key)?'on':''}" onclick={(e) => togglePopup(key, e)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && togglePopup(key, e)}>
        {label} <span class="chip-icon">▾</span>
      </span>
    {/each}
  </div>
  <div class="chip-group">
    <span class="chip {store.filters.hideFemaleOnly?'on':''}" onclick={toggleFemale} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && toggleFemale()}>
      <span class="chip-icon">🚫</span> Hide female-only
    </span>
    {#if activeCount}<span class="chip clear" onclick={clearAll} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && clearAll()}>Clear ({activeCount})</span>{/if}
  </div>
</div>

<div class="active-filters" role="status" aria-live="polite">
  {#if store.filters.rentMin || store.filters.rentMax}
    <span class="filter-pill">₹{store.filters.rentMin || 0}–{store.filters.rentMax || '∞'}<button onclick={() => { store.filters.rentMin = undefined; store.filters.rentMax = undefined; onchange?.(); }}>&times;</button></span>
  {/if}
  {#each ["bhk","type","furnishing"] as key}
    {#if store.filters[key]?.length}
      {#each store.filters[key] as v}
        <span class="filter-pill">{v}<button onclick={() => toggle(key, v)}>&times;</button></span>
      {/each}
    {/if}
  {/each}
  {#if store.filters.hideFemaleOnly}
    <span class="filter-pill">Hide female-only<button onclick={() => { store.filters.hideFemaleOnly = undefined; onchange?.(); }}>&times;</button></span>
  {/if}
</div>

{#if open}
  <div class="pop fixed" style={popStyle} onclick={(e)=>e.stopPropagation()} role="dialog" aria-label="Filter options" tabindex="-1" onkeydown={(e) => e.key === 'Escape' && (open = null)}>
    {#if open === 'rent'}
      <div class="rentrow">
        <input type="number" placeholder="min" value={store.filters.rentMin||''} onchange={(e)=>setRent(e.target.value, store.filters.rentMax)} aria-label="Minimum rent" />
        <span style="color:var(--text-muted)">–</span>
        <input type="number" placeholder="max" value={store.filters.rentMax||''} onchange={(e)=>setRent(store.filters.rentMin, e.target.value)} aria-label="Maximum rent" />
      </div>
      <div class="hist-labels"><span>{BIN_LABELS[0]}</span><span>{BIN_LABELS[BIN_LABELS.length - 1]}</span></div>
      <div class="hist" role="img" aria-label="Rent price distribution">
        {#each rentHistogram as bin}
          <div class="hist-bar {bin.inRange ? 'range' : ''}" style="height:{Math.max(bin.pct * 100, 4)}%" title="{bin.count} listings"></div>
        {/each}
      </div>
    {:else}
      {#each (open === 'bhk' ? BHK : open === 'type' ? TYPE : FURN) as [v,lbl]}
        <label><input type="checkbox" checked={(store.filters[open]||[]).includes(v)} onchange={() => toggle(open, v)} /> {lbl}</label>
      {/each}
    {/if}
  </div>
{/if}

<div class="view-toggle" role="group" aria-label="View mode">
  <button class="view-btn {viewMode === 'map' ? 'on' : ''}" onclick={() => toggleView('map')} aria-label="Map view" aria-pressed={viewMode === 'map'} title="Map">▢</button>
  <button class="view-btn {viewMode === 'list' ? 'on' : ''}" onclick={() => toggleView('list')} aria-label="List view" aria-pressed={viewMode === 'list'} title="List">☰</button>
</div>

<button class="saved-btn" title="Saved properties ({savedCount})" aria-label="Saved properties" onclick={() => {}}>
  ♡
  {#if savedCount > 0}<span class="saved-count">{savedCount}</span>{/if}
</button>

<button class="theme" title="Toggle theme" onclick={() => setTheme(store.theme === "dark" ? "light" : "dark")}>
  {store.theme === "dark" ? "☀︎" : "☾"}
</button>

<button class="menu-btn" aria-label="Filters" onclick={() => (showSheet = !showSheet)} aria-expanded={showSheet}>☰</button>

{#if showSheet}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div class="sheet-overlay" onclick={() => (showSheet = false)} role="presentation"></div>
  <div class="sheet" role="dialog" aria-label="Filter options">
    <div class="sheet-handle" onclick={() => (showSheet = false)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && (showSheet = false)}></div>
    <div class="sheet-body">
      <div class="sheet-section">
        <div class="sheet-label">Rent range</div>
        <div class="rentrow">
          <input type="number" placeholder="Min" value={store.filters.rentMin||''} onchange={(e)=>setRent(e.target.value, store.filters.rentMax)} aria-label="Minimum rent" />
          <span style="color:var(--text-muted)">–</span>
          <input type="number" placeholder="Max" value={store.filters.rentMax||''} onchange={(e)=>setRent(store.filters.rentMin, e.target.value)} aria-label="Maximum rent" />
        </div>
      </div>
      <div class="sheet-section">
        <div class="sheet-label">BHK</div>
        <div class="sheet-chips">
          {#each BHK as [v,lbl]}
            <span class="chip {(store.filters.bhk||[]).includes(v)?'on':''}" onclick={() => toggle('bhk', v)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && toggle('bhk', v)}>{lbl}</span>
          {/each}
        </div>
      </div>
      <div class="sheet-section">
        <div class="sheet-label">Type</div>
        <div class="sheet-chips">
          {#each TYPE as [v,lbl]}
            <span class="chip {(store.filters.type||[]).includes(v)?'on':''}" onclick={() => toggle('type', v)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && toggle('type', v)}>{lbl}</span>
          {/each}
        </div>
      </div>
      <div class="sheet-section">
        <div class="sheet-label">Furnishing</div>
        <div class="sheet-chips">
          {#each FURN as [v,lbl]}
            <span class="chip {(store.filters.furnishing||[]).includes(v)?'on':''}" onclick={() => toggle('furnishing', v)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && toggle('furnishing', v)}>{lbl}</span>
          {/each}
        </div>
      </div>
      <div class="sheet-section">
        <label class="sheet-row"><input type="checkbox" checked={!!store.filters.hideFemaleOnly} onchange={toggleFemale} /> Hide female-only</label>
      </div>
      {#if activeCount}
        <button class="chip clear" onclick={clearAll} style="width:100%;justify-content:center">Clear all filters ({activeCount})</button>
      {/if}
    </div>
  </div>
{/if}