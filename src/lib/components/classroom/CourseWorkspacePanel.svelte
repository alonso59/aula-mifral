<script lang="ts">
  // Lightweight, additive panel inspired by LMS UIs (Canvas/Moodle)
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';

  export let course: any = null;
  let active = 'overview';

  // Materials & knowledge files state
  let materials: any[] = [];
  let knowledgeFiles: any[] = [];
  let loadingMaterials = false;
  let error: string | null = null;
  let lastCourseId: string | null = null;

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'materials', label: 'Materials' },
    { id: 'topics', label: 'Topics' },
    { id: 'assignments', label: 'Assignments' },
    { id: 'videos', label: 'Videos' }
  ];

  async function loadMaterialsForCourse(courseId: string) {
    if (!browser || !courseId) return;
    loadingMaterials = true;
    error = null;
    try {
      const [mRes, cRes] = await Promise.allSettled([
        fetch(`/api/classroom/courses/${courseId}/materials`),
        fetch(`/api/classroom/courses/${courseId}`)
      ]);

      // materials
      if (mRes.status === 'fulfilled' && mRes.value.ok) {
        try {
          materials = await mRes.value.json();
        } catch (e) {
          materials = [];
        }
      } else {
        materials = [];
      }

      // course details -> knowledge_files
      if (cRes.status === 'fulfilled' && cRes.value.ok) {
        try {
          const cd = await cRes.value.json();
          knowledgeFiles = cd?.knowledge_files || [];
        } catch (e) {
          knowledgeFiles = [];
        }
      } else {
        knowledgeFiles = [];
      }
    } catch (e: any) {
      error = e?.message ?? String(e);
    } finally {
      loadingMaterials = false;
    }
  }

  // Load on initial mount (browser-only)
  onMount(() => {
    if (browser && course?.id) {
      lastCourseId = course.id;
      loadMaterialsForCourse(course.id);
    }
  });

  // If course prop changes while running in the browser, refresh materials
  $: if (browser && course?.id && course.id !== lastCourseId) {
    lastCourseId = course.id;
    loadMaterialsForCourse(course.id);
  }
</script>

<div class="h-full w-full flex flex-col overflow-hidden">
  <div class="flex-none border-b border-gray-200 dark:border-gray-800 px-3 py-2">
    <div class="flex gap-2 text-sm">
      {#each tabs as t}
        <button
          class="px-2 py-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900 transition {active===t.id ? 'bg-gray-100 dark:bg-gray-900' : ''}"
          on:click={() => (active = t.id)}
        >{t.label}</button>
      {/each}
    </div>
  </div>

  <div class="flex-1 overflow-auto p-3 text-sm">
    {#if active === 'overview'}
      <div class="space-y-2">
        <div class="text-base font-semibold">Course Details</div>
        <div class="text-gray-600 dark:text-gray-300">{course?.description ?? 'No details available yet.'}</div>
        <div class="grid grid-cols-2 gap-2">
          <div class="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
            <div class="text-xs text-gray-500">Progress</div>
            <div class="mt-1 h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
              <div class="h-full bg-blue-500" style="width: 0%" />
            </div>
          </div>
          <div class="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
            <div class="text-xs text-gray-500">Next Due</div>
            <div class="mt-1 text-gray-700 dark:text-gray-200">—</div>
          </div>
        </div>
      </div>
    {/if}

    {#if active === 'materials'}
      <div class="space-y-3">
        {#if loadingMaterials}
          <div class="rounded-lg border border-gray-200 dark:border-gray-800 p-4 text-center text-sm text-gray-600">
            Loading materials…
          </div>
        {:else}
          {#if error}
            <div class="rounded-lg border border-red-200 dark:border-red-800 p-4 text-sm text-red-600">
              Error loading materials: {error}
            </div>
          {/if}

          <!-- Documents added as Materials -->
          <div>
            <div class="text-sm font-semibold mb-2">Course Materials</div>
            {#if materials && materials.length > 0}
              <ul class="space-y-2">
                {#each materials as m}
                  <li class="flex items-center justify-between rounded-md border p-2">
                    <div class="flex items-center gap-3">
                      <div class="text-sm font-medium">{m.title}</div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">{m.kind}</div>
                    </div>
                    {#if m.uri_or_blob_id}
                      <a
                        class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                        href={`/api/v1/files/${m.uri_or_blob_id}/content`}
                        target="_blank"
                        rel="noopener noreferrer"
                        >Open</a
                      >
                    {:else}
                      <div class="text-xs text-gray-500">—</div>
                    {/if}
                  </li>
                {/each}
              </ul>
            {:else}
              <div class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-4 text-sm text-gray-500 text-center">
                No materials added to this course.
              </div>
            {/if}
          </div>

          <!-- Knowledge files (from linked knowledge base) -->
          <div>
            <div class="text-sm font-semibold mt-4 mb-2">Knowledge Files</div>
            {#if knowledgeFiles && knowledgeFiles.length > 0}
              <ul class="space-y-2">
                {#each knowledgeFiles as f}
                  <li class="flex items-center justify-between rounded-md border p-2">
                    <div class="flex items-center gap-3">
                      <div class="text-sm font-medium">{f.filename ?? f.name ?? f.title ?? f.id}</div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">{f.content_type ?? (f.meta?.content_type ?? '')}</div>
                    </div>
                    {#if f.id}
                      <a
                        class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                        href={`/api/v1/files/${f.id}/content`}
                        target="_blank"
                        rel="noopener noreferrer"
                        >Open</a
                      >
                    {:else}
                      <div class="text-xs text-gray-500">—</div>
                    {/if}
                  </li>
                {/each}
              </ul>
            {:else}
              <div class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-4 text-sm text-gray-500 text-center">
                No knowledge files linked to this course.
              </div>
            {/if}
          </div>
        {/if}
      </div>
    {/if}

    {#if active === 'topics'}
      <div class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-gray-500">
        Learning topics will appear here.
      </div>
    {/if}

    {#if active === 'assignments'}
      <div class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-gray-500">
        Assignments will appear here.
      </div>
    {/if}

    {#if active === 'videos'}
      <div class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-gray-500">
        Course videos will appear here.
      </div>
    {/if}
  </div>
</div>

<style>
  :global(.dark) .shadow-subtle { box-shadow: 0 1px 0 0 rgba(255,255,255,0.06) inset; }
</style>
