<script>
  import "../app.css";
  import { onMount } from "svelte";
  import { load, store } from "$lib/data.svelte.js";
  import Map from "$lib/Map.svelte";
  import CardStack from "$lib/CardStack.svelte";
  let mapComp = $state(null), stackComp = $state(null);
  let list = $state([]);
  onMount(load);
  function onlist(l) { list = l; }
  function onselect(l) { mapComp?.panTo(l); }
  function onpin(id) { stackComp?.jumpTo(id); }
</script>

<div class="nav"><div class="brand"><span class="bdot"></span> zuckerbroker</div>
  <div class="count">{list.length} in view · {store.total} total</div></div>
<Map bind:this={mapComp} {onlist} selectedId={{ set: onpin }} />
<CardStack bind:this={stackComp} {list} {onselect} />
