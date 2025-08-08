<script lang="ts">
  // Lightweight, additive panel inspired by LMS UIs (Canvas/Moodle)
  export let course: any = null;
  let active = 'overview';

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'materials', label: 'Materials' },
    { id: 'topics', label: 'Topics' },
    { id: 'assignments', label: 'Assignments' },
    { id: 'videos', label: 'Videos' }
  ];
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
      <div class="rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-gray-500">
        Materials will appear here.
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
