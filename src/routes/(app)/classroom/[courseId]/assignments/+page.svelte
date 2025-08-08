<script lang="ts">
  import { onMount } from 'svelte';
  import Tabs from '../Tabs.svelte';
  import { page } from '$app/stores';
  import { listAssignments, createAssignment } from '$lib/apis/classroom';
  import { user } from '$lib/stores';

  let assignments: any[] = [];
  let loading = true;
  let error: string | null = null;
  let creating = false;
  let newTitle = '';
  let newBody = '';
  $: courseId = $page.params.courseId;

  onMount(async () => {
    try {
      const token = '';
      assignments = await listAssignments(token, courseId);
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load assignments';
    } finally {
      loading = false;
    }
  });

  async function onCreate() {
    try {
      creating = true;
      const token = localStorage.token;
      const res = await createAssignment(token, courseId, { title: newTitle, body_md: newBody });
      assignments = [res, ...assignments];
      newTitle = '';
      newBody = '';
    } catch (e: any) {
      error = e?.detail ?? 'Create failed';
    } finally {
      creating = false;
    }
  }
</script>

<Tabs {courseId} />

<section class="space-y-3">
  <h1 class="text-xl font-semibold">Assignments</h1>
  {#if loading}
    <p class="text-sm text-neutral-500">Loading…</p>
  {:else if error}
    <p class="text-sm text-red-500">{error}</p>
  {:else if !assignments?.length}
    <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-6 text-sm text-neutral-600 dark:text-neutral-400">No assignments yet.</div>
  {:else}
    {#if $user?.role === 'admin' || $user?.role === 'teacher'}
      <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-4 space-y-2">
        <div class="text-sm font-medium">Create assignment</div>
        <input class="input input-bordered w-full" placeholder="Title" bind:value={newTitle} />
        <textarea class="textarea textarea-bordered w-full" rows="3" placeholder="Body (optional)" bind:value={newBody} />
        <button class="btn btn-primary" disabled={creating || !newTitle.trim()} on:click={onCreate}>Create</button>
      </div>
    {/if}
    <ul class="space-y-2">
      {#each assignments as a}
        <li class="rounded-md border border-neutral-200 dark:border-neutral-800 p-3">
          <div class="text-sm font-medium">{a.title}</div>
          {#if a.body_md}
            <div class="text-xs text-neutral-500">{a.body_md}</div>
          {/if}
          <div class="mt-2 flex gap-3 text-xs">
            <a class="link" href="/classroom/{courseId}/chat?discuss={encodeURIComponent(a.title)}">Discuss with Course Assistant</a>
            <a class="link" href="/classroom/{courseId}/assignments/{a.id}/submissions">View submissions</a>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
