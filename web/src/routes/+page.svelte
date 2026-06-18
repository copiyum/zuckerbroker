<script>
  import "../app.css";
  import { onMount } from "svelte";
  import { load, store } from "$lib/data.js";
  import Map from "$lib/Map.svelte";
  let mapComp = $state(null);
  let selectedId = $state(null);
  onMount(load);
  function onlist() {}
</script>

<div class="nav"><div class="brand"><span class="bdot"></span> zuckerbroker</div>
  <div class="count">{store.list.length} in view · {store.total} total</div></div>
<Map bind:this={mapComp} {onlist} selectedId={{ set: (id) => (selectedId = id) }} />
