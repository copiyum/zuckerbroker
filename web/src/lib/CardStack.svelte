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

<style>
  .empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #999;
    font-size: 14px;
  }

  .pos {
    position: absolute;
    top: 12px;
    right: 12px;
    font-size: 12px;
    color: #666;
    background: rgba(255, 255, 255, 0.8);
    padding: 4px 8px;
    border-radius: 4px;
    z-index: 10;
  }

  .stage {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }

  .detail {
    position: absolute;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    transition: transform 0.3s ease, opacity 0.3s ease;
  }

  .detail.front {
    transform: translateY(0);
    opacity: 1;
    z-index: 3;
  }

  .detail.b1 {
    transform: translateY(16px);
    opacity: 0.85;
    z-index: 2;
  }

  .detail.b2 {
    transform: translateY(32px);
    opacity: 0.7;
    z-index: 1;
  }

  .gal {
    flex: 1;
    overflow: hidden;
    background: #f0f0f0;
    display: flex;
    gap: 0;
  }

  .gal img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    flex-shrink: 0;
  }

  .noimg {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ccc;
    font-size: 13px;
  }

  .main {
    background: white;
    padding: 16px;
    overflow-y: auto;
    flex: 0 0 auto;
  }

  .top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
  }

  .rent {
    font-size: 20px;
    font-weight: 600;
    color: #333;
  }

  .type {
    font-size: 12px;
    color: #888;
    padding: 2px 6px;
    background: #f5f5f5;
    border-radius: 3px;
  }

  .type.flat {
    background: #e8f5e9;
    color: #2e7d32;
  }

  .loc {
    font-size: 13px;
    color: #666;
    margin-bottom: 12px;
  }

  .stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 12px;
  }

  .stat {
    border: 1px solid #eee;
    padding: 8px;
    border-radius: 4px;
    font-size: 12px;
  }

  .stat .k {
    color: #999;
    display: block;
    margin-bottom: 2px;
  }

  .stat .v {
    color: #333;
    font-weight: 500;
  }

  .foot {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .cta {
    flex: 1;
    min-width: 120px;
    padding: 8px 12px;
    background: #1976d2;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    font-size: 13px;
    text-align: center;
    border: none;
    cursor: pointer;
  }

  .cta.ghost {
    background: white;
    color: #1976d2;
    border: 1px solid #1976d2;
  }

  .cta:hover {
    opacity: 0.85;
  }
</style>
