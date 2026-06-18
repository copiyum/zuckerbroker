<script>
  let { list = [], onselect } = $props();
  let idx = $state(0);
  $effect(() => { if (idx > list.length - 1) idx = 0; });
  $effect(() => { if (list[idx]) onselect?.(list[idx]); });

  const fmt = (n) => (n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN"));
  const typeLabel = (t) => ({ entire_flat:"Entire flat", flatmate:"Flatmate", private_room:"Private room", pg_hostel:"PG" }[t] || "—");
  function advance(d) { if (list.length) idx = Math.max(0, Math.min(list.length - 1, idx + d)); }
  export function jumpTo(id) { const i = list.findIndex((x) => x.id === id); if (i >= 0) idx = i; }

  let wheelLock = 0;
  function onwheel(e) {
    if (Math.abs(e.deltaX) < 8 && Math.abs(e.deltaY) < 8) return;
    const now = Date.now(); if (now - wheelLock < 300) return; wheelLock = now;
    advance((e.deltaX || e.deltaY) > 0 ? 1 : -1);
  }
  function onkey(e) { if (e.key === "ArrowRight") advance(1); if (e.key === "ArrowLeft") advance(-1); }
</script>

<svelte:window onkeydown={onkey} />

{#if !list.length}
  <div class="empty">No homes in view — zoom out or clear filters</div>
{:else}
  <div class="pos">{idx + 1} of {list.length}</div>
  <div class="stage" onwheel={onwheel}>
    {#each [2, 1, 0] as d (d)}
      {#if list[idx + d]}
        {@const l = list[idx + d]}
        <div class="detail {d === 0 ? 'front' : d === 1 ? 'b1' : 'b2'}">
          <div class="gal">
            {#if l.images?.length}
              {#each l.images as src}<img loading="lazy" src={src} alt="" />{/each}
            {:else}<div class="noimg">no photo</div>{/if}
          </div>
          <div class="main">
            <div class="top"><span class="rent">{fmt(l.rent)}</span>
              <span class="type {l.listing_type === 'entire_flat' ? 'flat' : ''}">{typeLabel(l.listing_type)}</span></div>
            <div class="loc">{l.bhk ? l.bhk + " · " : ""}{l.location || ""}</div>
            <div class="stats">
              <div class="stat"><div class="k">Deposit</div><div class="v">{fmt(l.deposit)}</div></div>
              <div class="stat"><div class="k">Maint.</div><div class="v">{fmt(l.maintenance)}</div></div>
              <div class="stat"><div class="k">Available</div><div class="v">{l.available_from || "—"}</div></div>
              <div class="stat"><div class="k">Furnishing</div><div class="v">{l.furnishing || "—"}</div></div>
            </div>
            <div class="foot">
              <a class="cta" href={l.url} target="_blank" rel="noopener">View post ↗</a>
              {#if l.contact}<a class="cta ghost" href={"tel:" + l.contact}>📞 {l.contact}</a>{/if}
            </div>
          </div>
        </div>
      {/if}
    {/each}
  </div>
{/if}
