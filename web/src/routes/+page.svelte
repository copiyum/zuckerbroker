<script>
  import "../app.css";
  import { onMount } from "svelte";
  import { Tween } from "svelte/motion";
  import { cubicOut } from "svelte/easing";
  import { load, store, setTheme } from "$lib/data.svelte.js";
  import Map from "$lib/Map.svelte";
  import Sidebar from "$lib/Sidebar.svelte";
  import Detail from "$lib/Detail.svelte";
  import Filters from "$lib/Filters.svelte";
  let mapComp = $state(null);
  let list = $state([]);
  let selectedId = $state(null);
  let hoverId = $state(null);
  onMount(load);
  let selected = $derived(store.all.find((x) => x.id === selectedId) || null);

  const count = new Tween(0, { duration: 350, easing: cubicOut });
  $effect(() => { count.target = list.length; });

  function onlist(l) { list = l; }
  function onselect(l) { selectedId = l.id; }                      // card click -> detail + red pin (NO zoom/pan)
  function onpin(id) { selectedId = id; }                          // pin click -> detail (no pan)
  function onhover(id) { hoverId = id; }                           // two-way list <-> map link
</script>

<div class="nav">
  <Filters onchange={() => mapComp?.applyFiltersNow()} onplace={(l) => mapComp?.flyTo(l)} />
  <div class="count">{Math.round(count.current)} in view · {store.total} total</div>
  <button class="theme" title="Toggle map theme" onclick={() => setTheme(store.theme === "dark" ? "light" : "dark")}>
    {store.theme === "dark" ? "☀︎" : "☾"}
  </button>
</div>
<Map bind:this={mapComp} {onlist} {onpin} {onhover} {selectedId} {hoverId} theme={store.theme} />
<Sidebar {list} {selectedId} {hoverId} {onselect} {onhover} />
<Detail listing={selected} onclose={() => (selectedId = null)} />
