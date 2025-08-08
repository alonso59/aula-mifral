<script lang="ts">
  import { onMount } from 'svelte';
  import Tabs from '../Tabs.svelte';
  import { page } from '$app/stores';
  import { user } from '$lib/stores';
  import { listMaterials } from '$lib/apis/classroom';

  let materials: any[] = [];
  let loading = true;
  let error: string | null = null;
  $: courseId = $page.params.courseId;

  onMount(async () => {
    try {
      const token = '';
      materials = await listMaterials(token, courseId);
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load materials';
    } finally {
      loading = false;
    }
  });
</script>

<Tabs {courseId} />

<section class="space-y-3">
  <h1 class="text-xl font-semibold">Materials</h1>
  {#if loading}
    <p class="text-sm text-neutral-500">Loading…</p>
  {:else if error}
    <p class="text-sm text-red-500">{error}</p>
  {:else if !materials?.length}
    <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-6 text-sm text-neutral-600 dark:text-neutral-400">No materials yet.</div>
  {:else}
    <ul class="space-y-2">
      {#each materials as m}
        <li class="rounded-md border border-neutral-200 dark:border-neutral-800 p-3">
          <div class="text-sm font-medium">{m.title}</div>
          <div class="text-xs text-neutral-500">{m.kind}</div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
