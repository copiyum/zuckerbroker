<script>
  import { store, toggleSaved, getPage, checkHasMore, nextPage, resetPage } from "./data.svelte.js";
  let { list = [], selectedId = null, hoverId = null, onselect, onhover, ontoast } = $props();

  function stop(e) { e.stopPropagation(); }
  function share(e, l) {
    stop(e);
    const url = l.url || location.href;
    if (navigator.share) navigator.share({ title: "Rental on zuckerbroker", url }).catch(() => {});
    else navigator.clipboard?.writeText(url).then(() => ontoast?.("Link copied"));
  }
  function directions(e, l) {
    stop(e);
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${l.lat},${l.lng}`, "_blank");
  }
  const fmt = (n) => (n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN"));
  const typeLabel = (t) => ({ entire_flat: "Entire flat", flatmate: "Flatmate", private_room: "Private room", pg_hostel: "PG" }[t] || "");
  const rentLabel = (l) =>
    l.rent_min != null && l.rent_max != null && l.rent_min !== l.rent_max
      ? `${fmt(l.rent_min)}–${fmt(l.rent_max)}` : fmt(l.rent);

  /* sorted + paginated view */
  let sorted = $derived([...list].sort((a, b) => (a.rent ?? 1e12) - (b.rent ?? 1e12)));
  let shown = $derived(getPage(sorted));

  /* sync hasMore outside of derived */
  $effect(() => { checkHasMore(sorted); });

  let listEl;
  let showBackTop = $state(false);
  let sentinelEl = $state(null);

  /* reset page when list changes (filter/map move) */
  $effect(() => { list; resetPage(); });

  /* infinite scroll via IntersectionObserver */
  $effect(() => {
    if (!sentinelEl) return;
    const obs = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting && store.hasMore) {
        nextPage();
      }
    }, { root: listEl, rootMargin: "100px" });
    obs.observe(sentinelEl);
    return () => obs.disconnect();
  });

  /* selection OR hover scrolls that card into view */
  $effect(() => {
    const id = selectedId || hoverId;
    if (id && listEl) {
      const el = listEl.querySelector(`[data-id="${id}"]`);
      if (el) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  });

  /* track scroll for back-to-top */
  function onScroll() {
    showBackTop = listEl && listEl.scrollTop > 300;
  }
  function scrollToTop() {
    listEl?.scrollTo({ top: 0, behavior: "smooth" });
  }

  /* mobile: swipe down to collapse */
  let touchStartY = 0;
  function onTouchStart(e) { touchStartY = e.touches[0].clientY; }
  function onTouchEnd(e) {
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (dy > 60 && listEl && listEl.scrollTop < 10) {
      listEl.parentElement?.classList.add("collapsed");
    } else if (dy < -60) {
      listEl.parentElement?.classList.remove("collapsed");
    }
  }
</script>

<div class="sidebar">
  <div class="sbhead" role="button" tabindex="0" onclick={() => document.querySelector('.sidebar')?.classList.toggle('collapsed')}
       onkeydown={(e) => e.key === 'Enter' && document.querySelector('.sidebar')?.classList.toggle('collapsed')}>
    {#if !store.loaded}Loading homes…{:else}
      <span>{list.length} homes in view{list.length > 200 ? ' · 200 cheapest' : ''}</span>
    {/if}
  </div>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="sblist" bind:this={listEl} onscroll={onScroll}
       ontouchstart={onTouchStart} ontouchend={onTouchEnd}>
    {#if !store.loaded}
      {#each Array(7) as _}
        <div class="item skel"><div class="thumb sh"></div><div class="info">
          <div class="sh lg"></div><div class="sh md"></div><div class="sh sm"></div></div></div>
      {/each}
    {:else if !shown.length}
      <div class="empty">
        <div class="eico">🗺️</div>
        <div class="etitle">No homes here</div>
        <div class="esub">Zoom out, pan the map, or clear a filter to see more listings.</div>
      </div>
    {:else}
      {#each shown as l (l.id)}
        <div class="item {selectedId === l.id ? 'sel' : ''} {hoverId === l.id ? 'hov' : ''}"
             data-id={l.id} onclick={() => onselect?.(l)}
             onmouseenter={() => onhover?.(l.id)} onmouseleave={() => onhover?.(null)}
             role="button" tabindex="0"
             onkeydown={(e) => e.key === 'Enter' && onselect?.(l)}>
          <div class="thumb">
            {#if l.images?.length}
              <img loading="lazy" src={l.images[0]} alt="" />
              {#if l.images.length > 1}<span class="ph">{l.images.length} photos</span>{/if}
            {:else}<div class="noimg">no photo</div>{/if}
            {#if l.audience === 'female_only'}<span class="femtag">Female only</span>{/if}
            <div class="qa">
              <button class="qb {store.saved[l.id] ? 'on' : ''}" title="Save"
                      onclick={(e) => { stop(e); toggleSaved(l.id); ontoast?.(store.saved[l.id] ? "Saved" : "Removed"); }}>
                {store.saved[l.id] ? "♥" : "♡"}
              </button>
              <button class="qb" title="Share" onclick={(e) => share(e, l)}>⤴</button>
              <button class="qb" title="Directions" onclick={(e) => directions(e, l)}>📍</button>
            </div>
          </div>
          <div class="info">
            <div class="top">
              <span class="rent">{rentLabel(l)}<span class="mo">/mo</span></span>
              {#if l.listing_type}<span class="type {l.listing_type === 'entire_flat' ? 'flat' : ''}">{typeLabel(l.listing_type)}</span>{/if}
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
      <!-- infinite scroll sentinel -->
      {#if store.hasMore}
        <div bind:this={sentinelEl} class="item skel" style="height:1px;border:none;padding:0;">
          <div class="info" style="padding:4px 0;text-align:center;">
            <div class="sh sm" style="width:60%;margin:0 auto;height:8px;"></div>
          </div>
        </div>
      {/if}
    {/if}
  </div>
  <button class="back-top {showBackTop ? 'visible' : ''}" onclick={scrollToTop} aria-label="Back to top">↑</button>
</div>
