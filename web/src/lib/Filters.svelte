<script>
  import { store, searchPlace } from "./data.svelte.js";
  let { onchange, onplace } = $props();
  let q = $state("");
  let open = $state(null);

  const TYPE = [["entire_flat","Entire flat"],["flatmate","Flatmate"],["private_room","Private room"],["pg_hostel","PG / Hostel"]];
  const BHK = [["1","1 BHK"],["2","2 BHK"],["3","3 BHK"],["4+","4+ BHK"]];
  const FURN = [["furnished","Furnished"],["semi","Semi-furnished"],["unfurnished","Unfurnished"]];

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
  function toggleFemale() {
    store.filters.hideFemaleOnly = store.filters.hideFemaleOnly ? undefined : true;
    onchange?.();
  }
  function search(e) {
    e.preventDefault();
    const m = searchPlace(q);
    if (m) onplace?.(m);
  }
</script>

<div class="brand"><span class="bdot"></span> zuckerbroker</div>
<form class="search" onsubmit={search}>
  <input placeholder="Jump to a locality, society, metro…" bind:value={q} />
  <button type="submit">→</button>
</form>
<div class="chips">
  <span class="chip {active('rentMin')||active('rentMax')?'on':''}" onclick={() => open = open==='rent'?null:'rent'}>Rent ▾
    {#if open==='rent'}<div class="pop" onclick={(e)=>e.stopPropagation()}><div class="rentrow">
      <input type="number" placeholder="min" value={store.filters.rentMin||''} onchange={(e)=>setRent(e.target.value, store.filters.rentMax)}>
      <span>–</span>
      <input type="number" placeholder="max" value={store.filters.rentMax||''} onchange={(e)=>setRent(store.filters.rentMin, e.target.value)}>
    </div></div>{/if}
  </span>
  {#each [["BHK","bhk",BHK],["Type","type",TYPE],["Furnishing","furnishing",FURN]] as [label,key,opts]}
    <span class="chip {active(key)?'on':''}" onclick={() => open = open===key?null:key}>{label} ▾
      {#if open===key}<div class="pop" onclick={(e)=>e.stopPropagation()}>
        {#each opts as [v,lbl]}
          <label><input type="checkbox" checked={(store.filters[key]||[]).includes(v)} onchange={() => toggle(key, v)}> {lbl}</label>
        {/each}
      </div>{/if}
    </span>
  {/each}
  <span class="chip {store.filters.hideFemaleOnly?'on':''}" onclick={toggleFemale}>Hide female-only</span>
</div>
