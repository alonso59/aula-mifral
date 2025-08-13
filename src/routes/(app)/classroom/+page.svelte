<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
import { listCourses, deleteCourse } from '$lib/apis/classroom';
import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
import { classroomEnabled } from '$lib/stores/classroom';
import { showCourseList, showRightPanel } from '$lib/stores/classroom';
import { tick } from 'svelte';

// ...existing code...

let toast;

onMount(async () => {
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  const sonner = await import('svelte-sonner');
  // @ts-ignore
  toast = sonner.toast;
});

  // UI state
  let courses: any[] = [];
  let loading = true;
  let error: string | null = null;

  // Selected course
  let selectedCourseId: string | null = null;
  let selectedCourse: any = null;

  // Focus mode: when a course is active, show the focus two-pane view
  $: focusView = Boolean(selectedCourseId);

  // Left content pane sizing + collapse state (persisted)
  const DEFAULT_WIDTH = 360;
  let leftWidth = DEFAULT_WIDTH;
  let contentCollapsed = false;

  // Persist keys
  const STORAGE_WIDTH = 'classroom:contentWidth';
  const STORAGE_COLLAPSED = 'classroom:contentCollapsed';
  const STORAGE_LEFT_HIDDEN = 'classroom:leftHidden';
  let leftDestroyed = false;

  // Responsive
  let isMobile = false;

  // Mini-nav inside left content
  let activeSection: 'overview' | 'materials' | 'assignments' | 'virtual' = 'overview';

  // Dragging state for splitter
  let dragging = false;
  let startX = 0;
  let startWidth = DEFAULT_WIDTH;

  // Filters / Search / Sort
  type StatusFilter = 'active';
  let statusFilter: StatusFilter = 'active';
  let searchQuery = '';
  let debounced = '';
  let searchTimer: any = null;
  let sortMode: 'updated' | 'title' | 'status' = 'updated';

  const debounce = (fn: () => void, ms = 250) => {
    return () => {
      if (searchTimer) clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        fn();
      }, ms);
    };
  };

  const applyDebounced = debounce(() => {
    debounced = searchQuery.trim().toLowerCase();
  }, 250);

  // Derived & helper functions
  function courseMatchesSearch(c: any) {
    if (!debounced) return true;
    const s = debounced;
    return (
      (c.title && c.title.toLowerCase().includes(s)) ||
      (c.code && c.code.toLowerCase().includes(s)) ||
      (c.description && c.description.toLowerCase().includes(s))
    );
  }

  $: filteredCourses = courses
    .filter((c) => {
      if (statusFilter !== 'all') return c.status === statusFilter;
      return true;
    })
    .filter((c) => courseMatchesSearch(c))
    .sort((a, b) => {
      if (sortMode === 'updated') {
        const da = new Date(a.updated_at || a.updatedAt || 0).getTime();
        const db = new Date(b.updated_at || b.updatedAt || 0).getTime();
        return db - da;
      } else if (sortMode === 'title') {
        return ((a.title || '') as string).localeCompare(b.title || '');
      } else {
        return ((a.status || '') as string).localeCompare(b.status || '');
      }
    });

  // Overview counts
  $: counts = {
    total: courses.length,
    active: courses.filter((c) => c.status === 'active').length,
  };

  // Load courses
  async function loadCourses() {
    loading = true;
    try {
      const token = typeof window !== 'undefined' ? (localStorage.token || '') : '';
      courses = await listCourses(token);

      if (selectedCourseId) {
        selectedCourse = courses.find((c) => c.id === selectedCourseId) ?? null;
      }
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load courses';
    } finally {
      loading = false;
    }
  }

  // Keep selectedCourse in sync when id changes
  $: if (selectedCourseId) {
    selectedCourse = courses.find((c) => c.id === selectedCourseId) ?? selectedCourse;
  } else {
    selectedCourse = null;
  }

  // When in focusView, ensure global side rails are hidden (remove Create / Workspace panel)
  $: if (focusView) {
    try { showCourseList.set(false); showRightPanel.set(false); } catch {}
  }

  // Helpers
  function isTeacherOrAdmin() {
    return (get(user)?.role ?? '') === 'admin' || (get(user)?.role ?? '') === 'teacher';
  }

  // Back to courses action (exit focus view)
  function backToCourses() {
    selectedCourseId = null;
    // reveal course list on small screens if necessary
    showCourseList.set(true);
  }

  // Manage action (navigate to admin settings)
  function openManage() {
    // Prefer navigating to existing settings page
    goto('/admin/classroom');
  }

  // Toggle classroom enabled
  function toggleClassroomEnabled() {
    classroomEnabled.update((v) => {
      const nv = !v;
      try { classroomEnabled.set(nv); } catch {}
      toast({ message: nv ? 'Classroom enabled' : 'Classroom disabled', timeout: 2500 });
      return nv;
    });
  }

  // Splitter handlers
  function onSplitterPointerDown(e: PointerEvent) {
    if (typeof window === 'undefined') return;
    dragging = true;
    startX = e.clientX;
    startWidth = leftWidth;
    (document as any).body.style.userSelect = 'none';
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  }

  function onPointerMove(e: PointerEvent) {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const next = Math.max(200, Math.min(window.innerWidth - 320, startWidth + dx));
    leftWidth = next;
    try { localStorage.setItem(STORAGE_WIDTH, String(leftWidth)); } catch {}
  }

  function onPointerUp() {
    dragging = false;
    (document as any).body.style.userSelect = '';
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
  }

  // Keyboard resize for accessibility on splitter
  function onSplitterKeydown(e: KeyboardEvent) {
    const step = 16;
    if (e.key === 'ArrowLeft') {
      leftWidth = Math.max(200, leftWidth - step);
      try { localStorage.setItem(STORAGE_WIDTH, String(leftWidth)); } catch {}
      e.preventDefault();
    } else if (e.key === 'ArrowRight') {
      leftWidth = Math.min(window.innerWidth - 320, leftWidth + step);
      try { localStorage.setItem(STORAGE_WIDTH, String(leftWidth)); } catch {}
      e.preventDefault();
    } else if (e.key === 'Home') {
      leftWidth = 200; try { localStorage.setItem(STORAGE_WIDTH, String(leftWidth)); } catch {}
      e.preventDefault();
    } else if (e.key === 'End') {
      leftWidth = Math.max(360, Math.floor(window.innerWidth * 0.5)); try { localStorage.setItem(STORAGE_WIDTH, String(leftWidth)); } catch {}
      e.preventDefault();
    } else if (e.key === 'Enter' || e.key === ' ') {
      // toggle collapsed when pressing Enter/Space
      toggleCollapsed();
      e.preventDefault();
    }
  }

  function toggleCollapsed() {
    contentCollapsed = !contentCollapsed;
    try { localStorage.setItem(STORAGE_COLLAPSED, String(contentCollapsed)); } catch {}
  }

  // Mobile detection and persistence load
  onMount(async () => {
    if (typeof window !== 'undefined') {
      isMobile = window.innerWidth < 1024;
      try {
        const w = localStorage.getItem(STORAGE_WIDTH);
        if (w) leftWidth = Number(w);
        const c = localStorage.getItem(STORAGE_COLLAPSED);
        if (c !== null) contentCollapsed = c === 'true';
        const l = localStorage.getItem(STORAGE_LEFT_HIDDEN);
        if (l === 'true') leftDestroyed = true;
      } catch {}
      window.addEventListener('resize', () => {
        isMobile = window.innerWidth < 1024;
      });
    }
    await loadCourses();
  });

  onDestroy(() => {
    // cleanup if necessary
  });

  // Keyboard global escape to close panels (kept behavior)
  function onGlobalKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      showCourseList.set(false);
      showRightPanel.set(false);
    }
  }

  onMount(() => {
    window.addEventListener('keydown', onGlobalKey);
  });
  onDestroy(() => {
    window.removeEventListener('keydown', onGlobalKey);
  });

  // Event when user selects a course from other components
  function openCourse(c: any) {
    selectedCourseId = c.id;
    selectedCourse = c;
    // ensure focusView picks up and side rails are hidden
    showCourseList.set(false);
  }

  // Actions for a single card (edit/archive/delete). We keep optimistic updates behavior by mutating local array only.
  function editCourse(c: any) {
    // navigate to edit route if exists; otherwise open create route with edit param
    goto(`/classroom/courses/${c.id}/edit`);
  }

  // Delete modal state & handlers
  let showDeleteModal = false;
  let modalCourse: any = null;

  function openDeleteModal(c: any) {
    modalCourse = c;
    showDeleteModal = true;
  }

  async function confirmDelete() {
    if (!modalCourse) {
      showDeleteModal = false;
      return;
    }

    // Call backend to perform full deletion (model, knowledge, vectors, DB rows)
    try {
      const token = typeof window !== 'undefined' ? (localStorage.token || '') : '';
      await deleteCourse(token, modalCourse.id);

      // Remove from local list (optimistic update after server success)
      const idx = courses.findIndex((x) => x.id === modalCourse.id);
      if (idx >= 0) {
        courses.splice(idx, 1);
      }

      // If the deleted course was open, close focus view
      if (selectedCourseId === modalCourse.id) {
        selectedCourseId = null;
        selectedCourse = null;
        // reveal course list on small screens if necessary
        showCourseList.set(true);
      }

      toast({ message: 'Course deleted', timeout: 2000 });
    } catch (e) {
      console.error('Failed to delete course', e);
      // Try to extract message from error payload if available
      let msg = 'Failed to delete course';
      try {
        if (e && e.detail) msg = e.detail;
        else if (e && e.message) msg = e.message;
      } catch {}
      toast({ message: msg, type: 'error', timeout: 4000 });
    } finally {
      modalCourse = null;
      showDeleteModal = false;
    }
  }

  function cancelDelete() {
    modalCourse = null;
    showDeleteModal = false;
  }
</script>

<!-- Design tokens note: Helvetica primary, subtle rounded cards, small shadows in light mode, neutral dark backgrounds -->
<section class="min-h-[100dvh] h-[100dvh] p-0 bg-white dark:bg-gray-900" style="font-family: Helvetica, Arial, sans-serif;">
  <!-- Top bar -->
  <header class="sticky top-0 z-20 backdrop-blur-sm bg-white/60 dark:bg-neutral-900/40 border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex items-center gap-3 justify-between">
    <div class="flex items-center gap-3 min-w-0">
      {#if focusView}
        <button class="text-sm px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={backToCourses} aria-label="Back to Courses">← Back to Courses</button>
      {/if}

      <div class="min-w-0">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-semibold truncate">{selectedCourse?.title ?? 'Classroom'}</h1>
          {#if selectedCourse}
            <span class="text-[11px] uppercase tracking-wide px-2 py-0.5 rounded-full {selectedCourse.status==='active' ? 'bg-gray-100 text-gray-600' : 'bg-yellow-50 text-yellow-800'}">{selectedCourse.status}</span>
          {/if}
        </div>
      </div>
    </div>

    <div class="flex items-center gap-3">
      {#if focusView}
        <div class="flex items-center gap-2">
          {#if isTeacherOrAdmin()}
            <button class="px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-sm hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={openManage}>Manage</button>
          {/if}
        </div>
      {:else}
        {#if isTeacherOrAdmin()}
          <button class="px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-sm hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={openManage}>Manage</button>
        {/if}
      {/if}
    </div>
  </header>

  <!-- Main two-pane area -->
  <div class="flex h-[calc(100vh-12rem)]">
    <!-- Left: content panel (student-focused). Hidden when not focusView or when collapsed on mobile -->
    {#if focusView && !leftDestroyed}
      <aside
        class="h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 overflow-auto transition-all"
        style="width: {contentCollapsed && isMobile ? 0 : leftWidth + 'px'}; min-width: {contentCollapsed && isMobile ? 0 : '200px'};"
        aria-hidden={contentCollapsed && isMobile}
      >
        <div class="p-4 space-y-4">
          <!-- Mini-nav (section headings) -->
          <div class="space-y-3">
            <h3 class="text-xs font-semibold uppercase tracking-wide">Sections</h3>
            <div class="flex flex-col gap-2">
              <button class="text-[13px] text-left px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={()=> activeSection='overview'} aria-pressed={activeSection==='overview'}>Overview</button>
              <button class="text-[13px] text-left px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={()=> activeSection='materials'} aria-pressed={activeSection==='materials'}>Materials</button>
              <button class="text-[13px] text-left px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={()=> activeSection='assignments'} aria-pressed={activeSection==='assignments'}>Assignments</button>
            </div>
          </div>

          <!-- Section content -->
          <div>
            {#if activeSection === 'overview'}
              <h4 class="text-sm font-semibold">Overview</h4>
              <p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{selectedCourse?.description ?? 'No description available.'}</p>
            {:else if activeSection === 'materials'}
              <h4 class="text-sm font-semibold">Materials</h4>
              {#if selectedCourse?.documents && selectedCourse.documents.length}
                <ul class="mt-2 space-y-2">
                  {#each selectedCourse.documents as doc}
                    <li>
                      <a class="text-[13px] block px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" href={doc.url ?? '#'}>{doc.name || doc.title || 'Document'}</a>
                    </li>
                  {/each}
                </ul>
              {:else}
                <div class="text-sm text-neutral-500 mt-2">No documents yet.</div>
              {/if}
            {:else if activeSection === 'assignments'}
              <h4 class="text-sm font-semibold">Assignments</h4>
              <div class="text-sm text-neutral-500 mt-2">No assignments yet.</div>
            {:else}
              <h4 class="text-sm font-semibold">Virtual Classroom</h4>
              <div class="text-sm text-neutral-500 mt-2">No live sessions scheduled.</div>
            {/if}
          </div>
        </div>
      </aside>

      <!-- Splitter (draggable) -->
      {#if !isMobile && !leftDestroyed}
        <div
          role="separator"
          aria-orientation="vertical"
          tabindex="0"
          class="w-1 cursor-col-resize bg-transparent hover:bg-gray-200 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          on:pointerdown={onSplitterPointerDown}
          on:keydown={onSplitterKeydown}
          style="touch-action: none;"
          aria-label="Resize content panel"
        />
      {/if}
    {/if}

    <!-- Right: Chat content / list area -->
    <main class="flex-1 h-full overflow-auto" style="min-height: calc(100vh - 4rem);">
      <div class="w-full max-w-[1200px] h-full px-4 md:px-6 mx-auto">
        {#if loading}
          <div class="text-sm text-neutral-500 py-6">Loading…</div>
        {:else if error}
          <div class="text-sm text-red-500 py-6">{error}</div>
        {:else}
            <!-- Course discovery + list with cards -->
            <div class="py-6">
              <!-- Filters chips -->
              <div class="flex items-center gap-3 mb-4 flex-wrap">
                <button class="px-3 py-1.5 rounded-full text-sm border {statusFilter==='active' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-gray-200 dark:border-gray-700'} focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => (statusFilter = 'active')}>Active</button>
              </div>

              <!-- Grid of cards -->
              {#if filteredCourses.length === 0}
                <div class="text-sm text-neutral-500 py-12">No courses found.</div>
              {:else}
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {#each filteredCourses as c (c.id)}
                    <article class="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition" role="article" tabindex="0" aria-labelledby={"title-" + c.id}>
                      <div class="flex justify-between items-start gap-3">
                        <div class="min-w-0">
                          <h3 id={"title-" + c.id} class="text-sm font-semibold truncate">{c.title}</h3>
                          <div class="text-[13px] text-neutral-500 dark:text-neutral-300 mt-1 line-clamp-2">{c.description ?? '—'}</div>
                          <div class="mt-3 text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-3">
                            <span class="px-2 py-0.5 rounded bg-gray-50 dark:bg-neutral-700 border text-xs">{c.code ?? '—'}</span>
                            <span>{c.term ?? '—'}</span>
                            <span class="ml-2">Docs: { (c.documents && c.documents.length) ? c.documents.length : '—' }</span>
                          </div>
                        </div>

                          <div class="flex flex-col items-end gap-2">
                            <div>
                              <span class="text-[11px] uppercase tracking-wide px-2 py-0.5 rounded-full {c.status==='active' ? 'bg-green-50 text-green-700' : 'bg-yellow-50 text-yellow-800'}">{c.status}</span>
                            </div>

                            <div class="flex items-center gap-2">
                              <button class="text-sm px-2 py-1 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => { goto(`/classroom/${c.id}/overview`); }}>Open</button>

                            <button class="text-sm px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => editCourse(c)} aria-label="Edit course">Edit</button>

                            {#if isTeacherOrAdmin()}
                              <button class="text-sm px-2 py-1 rounded-md bg-red-600 text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => openDeleteModal(c)}>Delete</button>
                            {/if}
                          </div>
                        </div>
                      </div>
                    </article>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
      </div>
    </main>
  </div>
  <!-- Confirm modal (accessible, focus-trapped) -->
  <ConfirmModal
    open={showDeleteModal}
    title="Delete course"
    description={modalCourse ? `Delete course \"${modalCourse.title}\"? This action cannot be undone.` : ''}
    confirmLabel="Delete"
    cancelLabel="Cancel"
    destructive={true}
    on:confirm={confirmDelete}
    on:cancel={cancelDelete}
  />

</section>

<style>
  /* Make sure splitter focus/ring visible */
  [role="separator"]:focus {
    outline: none;
  }

  /* small utility to clamp 2 lines */
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
