<script>
  import "../app.css";
  import { onMount } from "svelte";
  import { load, store } from "$lib/data.svelte.js";
  import Map from "$lib/Map.svelte";
  import Sidebar from "$lib/Sidebar.svelte";
  import Detail from "$lib/Detail.svelte";
  import Filters from "$lib/Filters.svelte";
  let mapComp = $state(null);
  let list = $state([]);
  let selectedId = $state(null);
  onMount(load);
  let selected = $derived(store.all.find((x) => x.id === selectedId) || null);
  function onlist(l) { list = l; }
  function onselect(l) { selectedId = l.id; mapComp?.flyTo(l); }   // card click -> open detail + fly map
  function onpin(id) { selectedId = id; }                          // pin click -> open detail (no pan)
</script>

<div class="nav">
  <Filters onchange={() => mapComp?.applyFiltersNow()} onplace={(l) => mapComp?.flyTo(l)} />
  <div class="count">{list.length} in view · {store.total} total</div>
</div>
<Map bind:this={mapComp} {onlist} {onpin} />
<Sidebar {list} {selectedId} {onselect} />
<Detail listing={selected} onclose={() => (selectedId = null)} />
