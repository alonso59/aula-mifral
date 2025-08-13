<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  export let params: { courseId: string };

  // This page was removed as part of a legacy enrollment feature cleanup.
  // Keep a simple informative placeholder so existing links don't break.
  let courseId = params?.courseId;
</script>

<section class="p-6 max-w-3xl mx-auto">
  <h1 class="text-2xl font-semibold mb-3">Enrollments — Removed</h1>
  <p class="text-sm text-neutral-600 mb-4">
    The legacy enrollment feature has been removed from this application. Enrollments are no longer managed here.
  </p>

  <p class="text-sm text-neutral-600 mb-4">
    If you were looking for enrollment-related functionality, please use the Course settings or contact an administrator.
  </p>

  <div class="flex gap-2">
    <button class="px-3 py-1 rounded bg-blue-600 text-white" on:click={() => goto(`/classroom/courses/${courseId}/edit`)}>Open Course Settings</button>
    <button class="px-3 py-1 rounded border" on:click={() => goto('/classroom')}>Back to Courses</button>
  </div>
</section>

<style>
  /* Minimal styling to match app */
  .text-neutral-600 { color: #6b7280; }
</style>
