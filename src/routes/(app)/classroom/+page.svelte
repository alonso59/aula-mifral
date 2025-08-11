<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { user } from '$lib/stores';
  import { listCourses } from '$lib/apis/classroom';
  import CourseChat from '$lib/components/chat/CourseChat.svelte';
  import CourseList from '$lib/components/classroom/CourseList.svelte';
  import ClassroomRightPanel from '$lib/components/classroom/ClassroomRightPanel.svelte';
  import { showCourseList, showRightPanel } from '$lib/stores/classroom';

  let courses: any[] = [];
  let loading = true;
  let error: string | null = null;

  // UI state for panel view
  let selectedCourseId: string | null = null;
  let selectedCourse: any = null;

  $: // sync selected course object when id changes
  if (selectedCourseId) selectedCourse = courses.find((c) => c.id === selectedCourseId) ?? selectedCourse;

  async function loadCourses() {
    loading = true;
    try {
      courses = await listCourses(localStorage.token);
      // auto-open first course if none selected
      if (courses && courses.length && !selectedCourseId) {
        selectedCourseId = courses[0].id;
        selectedCourse = courses[0];
      }
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load courses';
    } finally {
      loading = false;
    }
  }

  function onGlobalKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      showCourseList.set(false);
      showRightPanel.set(false);
    }
  }

  onMount(async () => {
    await loadCourses();
    window.addEventListener('keydown', onGlobalKey);
  });

  onDestroy(() => {
    window.removeEventListener('keydown', onGlobalKey);
  });

  function openCourse(c: any) {
    selectedCourseId = c.id;
    selectedCourse = c;
    showCourseList.set(false);
  }
</script>

<section class="min-h-[100dvh] h-[100dvh] grid grid-cols-1 lg:grid-cols-[280px_minmax(640px,1fr)_380px] gap-4 p-4">
  <!-- Left: course list (kept as first DOM column to ensure left placement) -->
  <aside class="hidden lg:block h-full">
    <CourseList {courses} bind:selectedCourseId loading={loading} error={error} on:select={(e) => openCourse(e.detail)} />
  </aside>

  <!-- Center: main course surface -->
  <main class="w-full min-h-0 flex flex-col overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-md">
    <div class="sticky top-0 z-20 bg-inherit/95 backdrop-blur px-4 py-3 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
      <div class="flex items-center gap-3 min-w-0">
        <div class="text-xl font-semibold truncate">{selectedCourse?.title ?? 'Classroom'}</div>
        {#if selectedCourse}
          <div class="text-xs rounded-full px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-neutral-700 dark:text-neutral-200">{selectedCourse.status}</div>
        {/if}
      </div>

      <div class="flex items-center gap-2">
        <button class="btn btn-ghost btn-xs lg:hidden" on:click={() => showCourseList.update(v => !v)} aria-label="Toggle course list">☰</button>
        <button class="btn btn-ghost btn-xs" on:click={() => showRightPanel.update(v => !v)} aria-label="Toggle right panel">≡</button>
      </div>
    </div>

    <!-- Tab bar -->
    <div class="flex items-center gap-3 px-4 py-2 border-b border-gray-100 dark:border-gray-800 sticky top-[52px] z-10 bg-inherit/95">
      <nav class="flex items-center gap-2 text-sm">
        <a class="text-sm link" href="#" aria-current="page">Overview</a>
        <a class="text-sm link" href="#">Materials</a>
        <a class="text-sm link" href="#">Assignments</a>
        <a class="text-sm link" href="#">Chat</a>
        <a class="text-sm link" href="#">Settings</a>
      </nav>
    </div>

    <!-- Content area -->
    <div class="flex-1 overflow-auto p-4 scrollbar-hidden">
      {#if loading}
        <div class="text-sm text-neutral-500">Loading…</div>
      {:else if error}
        <div class="text-sm text-red-500">{error}</div>
      {:else}
        {#if !selectedCourseId}
          <div class="text-sm text-neutral-500">Select a course to begin.</div>
        {:else}
          <div class="mx-auto max-w-[960px] px-4 sm:px-6">
            <!-- reuse CourseChat embedded (matches main chat width) -->
            <CourseChat courseId={selectedCourseId} embedded={true} />
          </div>
        {/if}
      {/if}
    </div>
  </main>

  <!-- Right: workspace/create panel -->
  <aside class="hidden lg:block h-full">
    <ClassroomRightPanel open bind:course={selectedCourse} on:close={() => showRightPanel.set(false)} />
  </aside>

  <!-- Drawers for small screens -->
  {#if $showCourseList}
    <div class="fixed inset-0 z-40 lg:hidden">
      <div class="absolute inset-0 bg-black/40" on:click={() => showCourseList.set(false)} />
      <div class="absolute left-0 top-0 bottom-0 w-72 p-4">
        <CourseList {courses} bind:selectedCourseId loading={loading} error={error} on:select={(e) => { openCourse(e.detail); showCourseList.set(false); }} />
      </div>
    </div>
  {/if}

  {#if $showRightPanel}
    <div class="fixed inset-0 z-40 lg:hidden">
      <div class="absolute inset-0 bg-black/40" on:click={() => showRightPanel.set(false)} />
      <div class="absolute right-0 top-0 bottom-0 w-80 p-4">
        <ClassroomRightPanel open on:close={() => showRightPanel.set(false)} />
      </div>
    </div>
  {/if}
</section>

<style>
  :global(.scrollbar-hidden) { scrollbar-width: none; -ms-overflow-style: none; }
  :global(.scrollbar-hidden::-webkit-scrollbar) { display: none; }
</style>
