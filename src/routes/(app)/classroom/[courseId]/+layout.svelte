<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import LeftNav from './LeftNav.svelte';

  // Current course id from the route
  $: courseId = $page.params.courseId;

  // Persisted toggle for the course left panel
  const STORAGE = 'classroom:leftOpen';
  let leftOpen = true;

  onMount(() => {
    try {
      leftOpen = JSON.parse(localStorage.getItem(STORAGE) ?? 'true');
    } catch {}
  });

  $: {
    try { localStorage.setItem(STORAGE, JSON.stringify(leftOpen)); } catch {}
  }
</script>

<div class="px-4 sm:px-6 lg:px-8 py-4">
  <!-- Header with toggle (works on lg and mobile) -->
  <div class="mb-3 flex items-center justify-between">
    <h1 class="text-base font-semibold truncate">Classroom</h1>
    <button
      class="px-3 py-1.5 rounded-md border text-sm bg-white dark:bg-gray-900
             text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800"
      on:click={() => (leftOpen = !leftOpen)}
      aria-expanded={leftOpen}
      aria-controls="course-left-rail"
    >
      {leftOpen ? 'Hide panel' : 'Show panel'}
    </button>
  </div>

  <!-- 2-col when panel is open; single column when hidden -->
  <!-- IMPORTANT: use underscore in Tailwind arbitrary value: [16rem_1fr] -->
  <div class={"grid gap-4 " + (leftOpen ? "grid-cols-1 lg:grid-cols-[16rem_1fr]" : "grid-cols-1")}>
    {#if leftOpen}
      <aside
        id="course-left-rail"
        class="lg:sticky lg:top-4 h-max
               border border-neutral-200 dark:border-neutral-800 rounded-lg overflow-hidden
               bg-white dark:bg-gray-900"
      >
        <div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-800 flex items-center justify-between">
          <h2 class="text-sm font-semibold">Course</h2>
          <button
            class="text-xs text-neutral-500 hover:underline"
            on:click={() => (leftOpen = false)}
          >
            Collapse
          </button>
        </div>
        <LeftNav {courseId} />
      </aside>
    {/if}

    <main class={"min-h-[70vh] " + (leftOpen ? "" : "lg:col-span-1")}>
      <slot />
    </main>
  </div>
</div>
