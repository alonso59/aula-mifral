<script lang="ts">
  import Tabs from '../Tabs.svelte';
  import { page } from '$app/stores';
  $: courseId = $page.params.courseId;
</script>

<Tabs {courseId} />

<section class="space-y-2">
  <h1 class="text-xl font-semibold">Overview</h1>
  <p class="text-sm text-neutral-600 dark:text-neutral-400">No overview yet.</p>
</section>
