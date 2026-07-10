<script>
  import { onMount } from "svelte";
  import { Tween } from "svelte/motion";
  import { cubicOut } from "svelte/easing";
  import { load, store } from "$lib/data.svelte.js";
  import Map from "$lib/Map.svelte";
  import Sidebar from "$lib/Sidebar.svelte";
  import Detail from "$lib/Detail.svelte";
  import Filters from "$lib/Filters.svelte";

  let mapComp = $state(null);
  let list = $state([]);
  let selectedId = $state(null);
  let hoverId = $state(null);
  let toasts = $state([]);
  let viewMode = $state("map");
  let drawMode = $state(false);

  onMount(load);
  let selected = $derived(store.all.find((x) => x.id === selectedId) || null);

  const count = new Tween(0, { duration: 350, easing: cubicOut });
  $effect(() => { count.target = list.length; });

  function onlist(l) { list = l; }
  function onselect(l) { selectedId = l.id; }
  function onpin(id) { selectedId = id; }
  function onhover(id) { hoverId = id; }

  function applyFilters() { mapComp?.applyFiltersNow(); }
  function flyTo(l) { mapComp?.flyTo(l); }
  function setDrawMode(on) { drawMode = on; mapComp?.setDrawMode?.(on); }

  $effect(() => {
    if (store.theme === "dark") document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
  });

  function handlePopState() {
    if (selectedId) { selectedId = null; return; }
  }
  $effect(() => {
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  });

  let toastId = 0;
  function ontoast(msg) {
    const id = ++toastId;
    toasts = [...toasts, { id, msg }];
    setTimeout(() => { toasts = toasts.filter((t) => t.id !== id); }, 2000);
  }
</script>

<div class="nav">
  <Filters
    onchange={applyFilters}
    onplace={flyTo}
    {viewMode}
    setViewMode={(m) => (viewMode = m)}
  />
  <div class="count">{Math.round(count.current)} in view · {store.total} total</div>
</div>
<Map
  bind:this={mapComp}
  {onlist}
  {onpin}
  {onhover}
  {selectedId}
  {hoverId}
  {drawMode}
  theme={store.theme}
  viewMode={viewMode}
/>
<Sidebar {list} {selectedId} {hoverId} {onselect} {onhover} {ontoast} />
<Detail listing={selected} onclose={() => (selectedId = null)} {ontoast} />

{#if toasts.length}
  <div class="toast-container">
    {#each toasts as t (t.id)}
      <div class="toast">{t.msg}</div>
    {/each}
  </div>
{/if}