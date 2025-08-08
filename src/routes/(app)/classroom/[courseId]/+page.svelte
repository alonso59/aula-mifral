<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { selectedCourse } from '$lib/stores';
  import Tabs from './Tabs.svelte';

  $: courseId = $page.params.courseId;
  onMount(() => {
    // Optionally load course metadata here in future
  })
</script>

<Tabs {courseId} />
