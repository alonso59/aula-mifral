<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  export let courses: any[] = [];
  export let selectedCourseId: string | null = null;
  export let loading = false;
  export let error: string | null = null;
  const dispatch = createEventDispatcher();

  // keyboard nav
  let listEl: HTMLElement | null = null;
  function onKeyNav(e: KeyboardEvent) {
    if (!courses?.length) return;
    const idx = courses.findIndex((c) => c.id === selectedCourseId);
    if (e.key === 'ArrowDown') {
      const next = courses[Math.min(courses.length - 1, idx + 1)];
      if (next) dispatch('select', next);
    } else if (e.key === 'ArrowUp') {
      const prev = courses[Math.max(0, idx - 1)];
      if (prev) dispatch('select', prev);
    } else if (e.key === 'Enter') {
      if (idx >= 0) dispatch('select', courses[idx]);
    }
  }

  onMount(() => {
    // add keydown handler to the list for keyboard navigation
    const handler = (e: Event) => onKeyNav(e as KeyboardEvent);
    listEl?.addEventListener('keydown', handler as EventListener);
    return () => listEl?.removeEventListener('keydown', handler as EventListener);
  });
</script>

<div class="h-full flex flex-col overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-md">
  <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-10 bg-inherit/95">
    <div class="flex items-center gap-2">
      <h2 class="text-sm font-semibold">Courses</h2>
      <span class="text-xs text-neutral-500">{courses?.length ?? 0}</span>
    </div>
    <div class="flex items-center gap-2">
      <input placeholder="Search" class="text-sm px-2 py-1 rounded-md border border-gray-200 dark:border-gray-700 bg-transparent" />
    </div>
  </div>

  <div bind:this={listEl} tabindex="0" class="flex-1 overflow-auto p-3 scrollbar-hidden">
    {#if loading}
      <div class="space-y-2">
        <div class="h-4 bg-gray-200 dark:bg-gray-800 rounded w-3/4" />
        <div class="h-4 bg-gray-200 dark:bg-gray-800 rounded w-1/2" />
      </div>
    {:else if error}
      <div class="text-sm text-red-500">{error}</div>
    {:else if !courses?.length}
      <div class="rounded-md border border-dashed px-3 py-6 text-sm text-neutral-600 dark:text-neutral-400">No courses available.</div>
    {:else}
      <ul class="space-y-2">
        {#each courses as c}
          <li>
            <button
              class="w-full text-left rounded-md p-2 flex items-start gap-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
              aria-current={selectedCourseId === c.id ? 'true' : undefined}
              on:click={() => dispatch('select', c)}
            >
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate">{c.title}</div>
                {#if c.description}
                  <div class="text-xs text-neutral-500 truncate">{c.description}</div>
                {/if}
              </div>
              <div class="text-xs text-neutral-400 ml-2">{c.status}</div>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<style>
  :global(.scrollbar-hidden) { scrollbar-width: none; -ms-overflow-style: none; }
  :global(.scrollbar-hidden::-webkit-scrollbar) { display: none; }
</style>
