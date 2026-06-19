<script>
  import { store, toggleSaved } from "./data.svelte.js";
  let { list = [], selectedId = null, hoverId = null, onselect, onhover } = $props();

  function stop(e) { e.stopPropagation(); }
  function share(e, l) { stop(e);
    const url = l.url || location.href;
    if (navigator.share) navigator.share({ title: "Rental on zuckerbroker", url }).catch(() => {});
    else navigator.clipboard?.writeText(url);
  }
  function directions(e, l) { stop(e);
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${l.lat},${l.lng}`, "_blank");
  }
  const fmt = (n) => (n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN"));
  const typeLabel = (t) => ({ entire_flat: "Entire flat", flatmate: "Flatmate", private_room: "Private room", pg_hostel: "PG" }[t] || "—");
  const rentLabel = (l) =>
    l.rent_min != null && l.rent_max != null && l.rent_min !== l.rent_max
      ? `${fmt(l.rent_min)}–${fmt(l.rent_max)}` : fmt(l.rent);

  let shown = $derived([...list].sort((a, b) => (a.rent ?? 1e12) - (b.rent ?? 1e12)).slice(0, 200));

  let listEl;
  // selection OR hover scrolls that card into view (pin -> card link)
  $effect(() => {
    const id = selectedId || hoverId;
    if (id && listEl) listEl.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
</script>

<div class="sidebar">
  <div class="sbhead">
    {#if !store.loaded}Loading homes…{:else}{list.length} homes in view{#if list.length > 200} · 200 cheapest{/if}{/if}
  </div>
  <div class="sblist" bind:this={listEl}>
    {#if !store.loaded}
      {#each Array(7) as _}
        <div class="item skel"><div class="thumb sh"></div><div class="info">
          <div class="sh ln lg"></div><div class="sh ln md"></div><div class="sh ln sm"></div></div></div>
      {/each}
    {:else if !list.length}
      <div class="empty">
        <div class="eico">🗺️</div>
        <div class="etitle">No homes here</div>
        <div class="esub">Zoom out, pan the map, or clear a filter to see more listings.</div>
      </div>
    {:else}
      {#each shown as l (l.id)}
        <div class="item {selectedId === l.id ? 'sel' : ''} {hoverId === l.id ? 'hov' : ''}"
             data-id={l.id} onclick={() => onselect?.(l)}
             onmouseenter={() => onhover?.(l.id)} onmouseleave={() => onhover?.(null)}>
          <div class="thumb">
            {#if l.images?.length}
              <img loading="lazy" src={l.images[0]} alt="" />
              {#if l.images.length > 1}<span class="ph">1/{l.images.length}</span>{/if}
            {:else}<div class="noimg">no photo</div>{/if}
            {#if l.audience === 'female_only'}<span class="femtag">Female only</span>{/if}
            <div class="qa">
              <button class="qb {store.saved[l.id] ? 'on' : ''}" title="Save"
                      onclick={(e) => { stop(e); toggleSaved(l.id); }}>{store.saved[l.id] ? "♥" : "♡"}</button>
              <button class="qb" title="Share" onclick={(e) => share(e, l)}>⤴</button>
              <button class="qb" title="Directions" onclick={(e) => directions(e, l)}>📍</button>
            </div>
          </div>
          <div class="info">
            <div class="top">
              <span class="rent">{rentLabel(l)}<span class="mo">/mo</span></span>
              <span class="type {l.listing_type === 'entire_flat' ? 'flat' : ''}">{typeLabel(l.listing_type)}</span>
            </div>
            <div class="loc">{l.bhk ? l.bhk + " · " : ""}{l.location || "Location unknown"}</div>
            <div class="sub">
              <span>Dep {fmt(l.deposit)}</span>
              {#if l.furnishing}<span>{l.furnishing}</span>{/if}
              {#if l.available_from}<span>{l.available_from}</span>{/if}
            </div>
            {#if l.dup_count > 1}<div class="dup">{l.dup_count} brokers listed this</div>{/if}
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>
