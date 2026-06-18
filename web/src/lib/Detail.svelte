<script>
  let { listing = null, onclose } = $props();
  const fmt = (n) => (n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN"));
  const typeLabel = (t) => ({ entire_flat: "Entire flat", flatmate: "Flatmate", private_room: "Private room", pg_hostel: "PG / Hostel" }[t] || "—");
  // show the broker's advertised spread when dedup recorded a range
  let rentText = $derived(
    listing && listing.rent_min != null && listing.rent_max != null && listing.rent_min !== listing.rent_max
      ? `${fmt(listing.rent_min)} – ${fmt(listing.rent_max)}`
      : fmt(listing?.rent));
</script>

{#if listing}
  <div class="detail">
    <button class="dclose" onclick={() => onclose?.()} aria-label="Close">×</button>
    <div class="dgal">
      {#if listing.images?.length}
        {#each listing.images as src}<img loading="lazy" src={src} alt="" />{/each}
      {:else}<div class="dnoimg">no photos</div>{/if}
    </div>
    <div class="dbody">
      <div class="drent">{rentText}<span class="dpermo">/mo</span></div>
      <div class="dtags">
        <span class="type {listing.listing_type === 'entire_flat' ? 'flat' : ''}">{typeLabel(listing.listing_type)}</span>
        {#if listing.bhk}<span class="dtag">{listing.bhk}</span>{/if}
        {#if listing.audience === 'female_only'}<span class="dtag fem">Female only</span>{/if}
        {#if listing.dup_count > 1}<span class="dtag">{listing.dup_count} reposts</span>{/if}
      </div>
      <div class="dloc">{listing.location || "Location unknown"}</div>
      <dl class="dfacts">
        <div><dt>Deposit</dt><dd>{fmt(listing.deposit)}</dd></div>
        <div><dt>Maintenance</dt><dd>{fmt(listing.maintenance)}</dd></div>
        <div><dt>Furnishing</dt><dd>{listing.furnishing || "—"}</dd></div>
        <div><dt>Available</dt><dd>{listing.available_from || "—"}</dd></div>
      </dl>
      <div class="dactions">
        {#if listing.contact}
          <a class="dbtn call" href="tel:{listing.contact}">📞 {listing.contact}</a>
        {/if}
        {#if listing.url}
          <a class="dbtn fb" href={listing.url} target="_blank" rel="noopener">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M22 12a10 10 0 10-11.56 9.88v-6.99H7.9V12h2.54V9.8c0-2.5 1.49-3.89 3.78-3.89 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56V12h2.78l-.44 2.89h-2.34v6.99A10 10 0 0022 12z"/></svg>
            Open Facebook post
          </a>
        {/if}
      </div>
    </div>
  </div>
{/if}
