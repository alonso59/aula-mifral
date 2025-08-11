<script lang="ts">
  import Tabs from '../Tabs.svelte';
  import { page } from '$app/stores';
  import CourseChat from '$lib/components/chat/CourseChat.svelte';
  $: courseId = $page.params.courseId;
</script>

<Tabs {courseId} />

<section>
  <CourseChat {courseId} />
</section>
