<script>
  let { list = [], selectedId = null, onselect } = $props();
  const fmt = (n) => (n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN"));
  const typeLabel = (t) => ({ entire_flat: "Entire flat", flatmate: "Flatmate", private_room: "Private room", pg_hostel: "PG" }[t] || "—");

  // stable rent-sorted view, capped for DOM perf (zoomed-out can be thousands)
  let shown = $derived([...list].sort((a, b) => (a.rent ?? 1e12) - (b.rent ?? 1e12)).slice(0, 200));

  let listEl;
  // when selection changes (e.g. a pin was clicked), scroll that item into view
  $effect(() => {
    if (selectedId && listEl) {
      const el = listEl.querySelector(`[data-id="${selectedId}"]`);
      el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  });
</script>

<div class="sidebar">
  <div class="sbhead">{list.length} homes in view{#if list.length > 200} · showing 200 cheapest{/if}</div>
  <div class="sblist" bind:this={listEl}>
    {#if !list.length}
      <div class="empty">No homes in view — zoom out or clear filters</div>
    {:else}
      {#each shown as l (l.id)}
        <div class="item {selectedId === l.id ? 'sel' : ''}" data-id={l.id} onclick={() => onselect?.(l)}>
          <div class="gal">
            {#if l.images?.length}
              {#each l.images.slice(0, 3) as src}<img loading="lazy" src={src} alt="" />{/each}
            {:else}<div class="noimg">no photo</div>{/if}
          </div>
          <div class="info">
            <div class="top"><span class="rent">{fmt(l.rent)}</span>
              <span class="type {l.listing_type === 'entire_flat' ? 'flat' : ''}">{typeLabel(l.listing_type)}</span></div>
            <div class="loc">{l.bhk ? l.bhk + " · " : ""}{l.location || ""}</div>
            <div class="sub">
              <span>Dep {fmt(l.deposit)}</span>
              {#if l.furnishing}<span>{l.furnishing}</span>{/if}
              {#if l.available_from}<span>{l.available_from}</span>{/if}
            </div>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>
