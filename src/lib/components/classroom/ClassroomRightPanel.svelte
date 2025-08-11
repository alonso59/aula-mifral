<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  export let open = false;
  export let course: any = null;
  const dispatch = createEventDispatcher();
</script>

<div class="h-full flex flex-col overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-md">
  <div class="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-10 bg-inherit/95">
    <h3 class="text-sm font-semibold">Create / Workspace</h3>
    <button class="btn btn-ghost btn-xs" on:click={() => dispatch('close')}>Close</button>
  </div>

  <div class="flex-1 overflow-auto p-4 scrollbar-hidden space-y-4">
    <div class="text-sm font-semibold">New Course</div>
    <div class="space-y-2">
      <input class="w-full px-3 py-2 rounded border border-gray-200 dark:border-gray-700 bg-transparent text-sm" placeholder="Course title" />
      <textarea class="w-full px-3 py-2 rounded border border-gray-200 dark:border-gray-700 bg-transparent text-sm" rows="4" placeholder="Description" />
      <div class="flex justify-end">
        <button class="btn btn-primary btn-sm">Create</button>
      </div>
    </div>

    <div class="pt-4 border-t border-gray-100 dark:border-gray-800">
      <div class="text-sm font-semibold">Workspace</div>
      <div class="text-xs text-neutral-500">Quick access to course tools and inspector.</div>
      <!-- Placeholder content -->
      <div class="mt-3 text-sm text-neutral-500">No workspace items.</div>
    </div>
  </div>
</div>

<style>
  :global(.scrollbar-hidden) { scrollbar-width: none; -ms-overflow-style: none; }
  :global(.scrollbar-hidden::-webkit-scrollbar) { display: none; }
</style>
