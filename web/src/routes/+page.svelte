<script>
  import "../app.css";
  import { onMount } from "svelte";
  import { load, store } from "$lib/data.svelte.js";
  import Map from "$lib/Map.svelte";
  import Sidebar from "$lib/Sidebar.svelte";
  import Filters from "$lib/Filters.svelte";
  let mapComp = $state(null);
  let list = $state([]);
  let selectedId = $state(null);
  onMount(load);
  function onlist(l) { list = l; }
  function onselect(l) { selectedId = l.id; mapComp?.flyTo(l); }   // card click -> fly map to the house
  function onpin(id) { selectedId = id; }                          // pin click -> highlight in sidebar (no pan)
</script>

<div class="nav">
  <Filters onchange={() => mapComp?.applyFiltersNow()} />
  <div class="count">{list.length} in view · {store.total} total</div>
</div>
<Map bind:this={mapComp} {onlist} {onpin} />
<Sidebar {list} {selectedId} {onselect} />
