<script>
  import { fly, fade } from "svelte/transition";
  import { store, toggleSaved } from "./data.svelte.js";
  let { listing = null, onclose, ontoast } = $props();

  let osm = $derived.by(() => {
    if (!listing?.lat) return null;
    const d = 0.004, lo = listing.lng, la = listing.lat;
    return `https://www.openstreetmap.org/export/embed.html?bbox=${lo - d},${la - d},${lo + d},${la + d}&layer=mapnik&marker=${la},${lo}`;
  });
  function share() {
    const url = listing?.url || location.href;
    if (navigator.share) navigator.share({ title: "Rental on zuckerbroker", url }).catch(() => {});
    else navigator.clipboard?.writeText(url).then(() => ontoast?.("Link copied"));
  }
  function directions() {
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${listing.lat},${listing.lng}`, "_blank");
  }
  const fmt = (n) => (n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN"));
  const typeLabel = (t) => ({ entire_flat: "Entire flat", flatmate: "Flatmate", private_room: "Private room", pg_hostel: "PG / Hostel" }[t] || "—");
  let rentText = $derived(
    listing && listing.rent_min != null && listing.rent_max != null && listing.rent_min !== listing.rent_max
      ? `${fmt(listing.rent_min)} – ${fmt(listing.rent_max)}` : fmt(listing?.rent));
  let imgs = $derived(listing?.images ?? []);
  let wa = $derived.by(() => {
    const d = (listing?.contact || "").replace(/\D/g, "");
    if (!d) return null;
    return "https://wa.me/" + (d.length === 10 ? "91" + d : d);
  });

  let idx = $state(0);
  let descExpanded = $state(false);
  let imgLoaded = $state({});

  $effect(() => { listing; idx = 0; descExpanded = false; imgLoaded = {}; });
  function go(d) { idx = Math.max(0, Math.min(imgs.length - 1, idx + d)); }
  function key(e) {
    if (!listing) return;
    if (e.key === "ArrowRight") go(1);
    else if (e.key === "ArrowLeft") go(-1);
    else if (e.key === "Escape") onclose?.();
  }
  function onImgLoad(src) { imgLoaded[src] = true; }
</script>

<svelte:window onkeydown={key} />

{#if listing}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div class="mobile-overlay" role="presentation" onclick={onclose}></div>
  <div class="detail" transition:fly={{ x: 420, duration: 260, easing: (t) => 1 - Math.pow(1 - t, 3) }}>
    <div class="dgal">
      {#if imgs.length}
        <div class="track" style="transform:translateX(-{idx * 100}%)">
          {#each imgs as src}
            <img loading="lazy" src={src} alt=""
                 style={imgLoaded[src] ? '' : 'opacity:0'}
                 onload={() => onImgLoad(src)} />
          {/each}
        </div>
        {#if imgs.length > 1}
          <button class="nav prev" onclick={() => go(-1)} disabled={idx === 0} aria-label="Previous">‹</button>
          <button class="nav next" onclick={() => go(1)} disabled={idx === imgs.length - 1} aria-label="Next">›</button>
          <div class="dots">{#each imgs as _, i}<span class="dot {i === idx ? 'on' : ''}" onclick={() => (idx = i)} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && (idx = i)}></span>{/each}</div>
        {/if}
      {:else}<div class="dnoimg">no photos</div>{/if}
      <button class="dclose" onclick={() => onclose?.()} aria-label="Close">×</button>
    </div>

    <div class="dhead">
      <span class="drent">{rentText}<span class="dpermo">/mo</span></span>
    </div>

    <div class="dbody">
      <div class="dtags">
        {#if listing.listing_type}<span class="type {listing.listing_type === 'entire_flat' ? 'flat' : ''}">{typeLabel(listing.listing_type)}</span>{/if}
        {#if listing.bhk}<span class="dtag">{listing.bhk}</span>{/if}
        {#if listing.audience === 'female_only'}<span class="dtag fem">Female only</span>{/if}
        {#if listing.dup_count > 1}<span class="dtag">{listing.dup_count} brokers</span>{/if}
      </div>
      <div class="dloc">{listing.location || "Location unknown"}</div>
      <dl class="dfacts">
        <div><dt>Deposit</dt><dd>{fmt(listing.deposit)}</dd></div>
        <div><dt>Maintenance</dt><dd>{fmt(listing.maintenance)}</dd></div>
        <div><dt>Furnishing</dt><dd>{listing.furnishing || "—"}</dd></div>
        <div><dt>Available</dt><dd>{listing.available_from || "—"}</dd></div>
      </dl>

      {#if listing.description}
        <div class="dsec">Description</div>
        <p class="ddesc {descExpanded ? '' : 'collapsed'}">{listing.description}</p>
        {#if listing.description.length > 300}
          <button class="expand-btn" onclick={() => descExpanded = !descExpanded}>
            {descExpanded ? 'Show less' : 'Show more'}
          </button>
        {/if}
      {/if}

      {#if osm}
        <div class="dsec">Location</div>
        <iframe class="dmap" title="location" src={osm} loading="lazy"></iframe>
      {/if}

      <div class="dquick">
        <button class="qb2 {store.saved[listing.id] ? 'on' : ''}" onclick={() => { toggleSaved(listing.id); ontoast?.(store.saved[listing.id] ? "Saved" : "Removed"); }}>
          {store.saved[listing.id] ? "♥ Saved" : "♡ Save"}
        </button>
        <button class="qb2" onclick={share}>⤴ Share</button>
        <button class="qb2" onclick={directions}>📍 Directions</button>
      </div>

      <div class="dactions">
        {#if wa}
          <a class="dbtn wa" href={wa} target="_blank" rel="noopener">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor" aria-hidden="true"><path d="M.06 24l1.68-6.13A11.86 11.86 0 010 11.94 11.94 11.94 0 0111.94 0a11.94 11.94 0 018.45 20.4A11.94 11.94 0 016.1 22.3L.06 24zm6.6-3.8l.36.22a9.9 9.9 0 005.05 1.38 9.92 9.92 0 100-19.84 9.92 9.92 0 00-8.4 15.2l.24.38-1 3.63 3.75-.97zm11.4-5.46c-.15-.25-.55-.4-1.15-.7s-1.35-.66-1.55-.74c-.2-.07-.36-.11-.5.12-.16.22-.6.74-.74.9-.13.14-.27.16-.5.05a8.1 8.1 0 01-2.38-1.47 9 9 0 01-1.65-2.05c-.17-.3 0-.46.13-.6.11-.12.25-.3.37-.46.13-.15.17-.26.26-.43.08-.18.04-.33-.02-.46-.06-.12-.5-1.34-.7-1.83-.18-.46-.36-.4-.5-.41h-.42c-.15 0-.4.06-.6.3-.21.23-.8.78-.8 1.9s.82 2.2.94 2.36c.11.15 1.6 2.46 3.9 3.45.54.24.96.38 1.3.48.54.18 1.04.15 1.43.1.43-.07 1.35-.56 1.54-1.1.2-.53.2-1 .14-1.1z"/></svg>
            WhatsApp
          </a>
        {/if}
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
