<script lang="ts">
  import { onMount } from 'svelte';
  import { user } from '$lib/stores';
  import { listCourses } from '$lib/apis/classroom';

  let courses: any[] = [];
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    try {
      courses = await listCourses(localStorage.token);
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load courses';
    } finally {
      loading = false;
    }
  });
</script>

<section class="space-y-3">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold">Classroom</h1>
    {#if $user && ['admin','teacher'].includes($user.role)}
      <a class="btn btn-primary btn-sm" href="/classroom/courses/new">Create Course</a>
    {/if}
  </div>
  {#if loading}
    <p class="text-sm text-neutral-500">Loading…</p>
  {:else if error}
    <p class="text-sm text-red-500">{error}</p>
  {:else if !courses.length}
    <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-6 text-sm text-neutral-600 dark:text-neutral-400">No courses yet.</div>
  {:else}
    <ul class="space-y-2">
      {#each courses as c}
        <li class="rounded-md border border-neutral-200 dark:border-neutral-800 p-3 flex items-center justify-between">
          <div>
            <div class="text-sm font-medium">{c.title}</div>
            {#if c.description}
              <div class="text-xs text-neutral-500">{c.description}</div>
            {/if}
          </div>
          <a class="link" href="/classroom/{c.id}/overview">Open</a>
        </li>
      {/each}
    </ul>
  {/if}
</section>
