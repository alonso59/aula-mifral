<script lang="ts">
  // Placeholder course list page; real list to be implemented after backend list endpoint
  let courses: any[] = [];
</script>

<section class="space-y-3">
  <h1 class="text-xl font-semibold">Classroom</h1>
  {#if !courses.length}
    <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-6 text-sm text-neutral-600 dark:text-neutral-400">No courses yet.</div>
  {/if}
</section>
