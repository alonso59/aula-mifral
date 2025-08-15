<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user as userStore } from '$lib/stores';
  import { listCourses, deleteCourse } from '$lib/apis/classroom';
  import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';

  let toast;
  onMount(async () => {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    const sonner = await import('svelte-sonner');
    // @ts-ignore
    toast = sonner.toast;
    await loadCourses();
  });

  // State
  let courses: any[] = [];
  let loading = true;
  let error: string | null = null;

  // Filters / Sort
  type StatusFilter = 'active';
  let statusFilter: StatusFilter = 'active';
  let sortMode: 'updated' | 'title' | 'status' = 'updated';

  $: filteredCourses = courses
    .filter((c) => (statusFilter !== 'all' ? c.status === statusFilter : true))
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

  async function loadCourses() {
    loading = true;
    try {
      const token = typeof window !== 'undefined' ? (localStorage.token || '') : '';
      courses = await listCourses(token);
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load courses';
    } finally {
      loading = false;
    }
  }

  function isTeacherOrAdmin($user: any) {
    const r = ($user?.role ?? '') as string;
    return r === 'admin' || r === 'teacher';
  }

  function editCourse(c: any) {
    goto(`/classroom/courses/${c.id}/edit`);
  }

  // Delete modal
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
    try {
      const token = typeof window !== 'undefined' ? (localStorage.token || '') : '';
      await deleteCourse(token, modalCourse.id);
      const idx = courses.findIndex((x) => x.id === modalCourse.id);
      if (idx >= 0) courses.splice(idx, 1);
      toast?.({ message: 'Course deleted', timeout: 2000 });
    } catch (e: any) {
      let msg = e?.detail || e?.message || 'Failed to delete course';
      toast?.({ message: msg, type: 'error', timeout: 4000 });
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

<section class="min-h-[100dvh] h-[100dvh] p-0 bg-white dark:bg-gray-900" style="font-family: Helvetica, Arial, sans-serif;">
  <!-- Simple header (catalog only) -->
  <header class="sticky top-0 z-20 backdrop-blur-sm bg-white/60 dark:bg-neutral-900/40 border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex items-center gap-3 justify-between">
    <h1 class="text-lg font-semibold truncate">Classroom</h1>
    {#if isTeacherOrAdmin($userStore)}
      <button
        class="px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-sm hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        on:click={() => goto('/admin/classroom')}
      >
        Manage
      </button>
    {/if}
  </header>

  <!-- Catalog content -->
  <main class="flex-1 h-full overflow-auto" style="min-height: calc(100vh - 4rem);">
    <div class="w-full max-w-[1200px] h-full px-4 md:px-6 mx-auto">
      {#if loading}
        <div class="text-sm text-neutral-500 py-6">Loading…</div>
      {:else if error}
        <div class="text-sm text-red-500 py-6">{error}</div>
      {:else}
        <div class="py-6">
          <!-- Filter chips (keep minimal for now) -->
          <div class="flex items-center gap-3 mb-4 flex-wrap">
            <button
              class="px-3 py-1.5 rounded-full text-sm border {statusFilter==='active' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-gray-200 dark:border-gray-700'} focus:outline-none focus:ring-2 focus:ring-blue-500"
              on:click={() => (statusFilter = 'active')}
            >
              Active
            </button>
          </div>

          <!-- Grid of course cards -->
          {#if filteredCourses.length === 0}
            <div class="text-sm text-neutral-500 py-12">No courses found.</div>
          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              {#each filteredCourses as c (c.id)}
                <article class="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition" aria-labelledby={"title-" + c.id}>
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
                        <button
                          class="text-sm px-2 py-1 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          on:click={() => goto(`/classroom/${c.id}/overview`)}
                        >
                          Open
                        </button>

                        <button
                          class="text-sm px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          on:click={() => editCourse(c)}
                          aria-label="Edit course"
                        >
                          Edit
                        </button>

                        {#if isTeacherOrAdmin($userStore)}
                          <button
                            class="text-sm px-2 py-1 rounded-md bg-red-600 text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            on:click={() => openDeleteModal(c)}
                          >
                            Delete
                          </button>
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

  <!-- Confirm modal -->
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
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>