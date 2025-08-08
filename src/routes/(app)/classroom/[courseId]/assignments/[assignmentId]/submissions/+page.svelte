<script lang="ts">
  import Tabs from '../../../Tabs.svelte';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { listSubmissions, createSubmission } from '$lib/apis/classroom';

  $: courseId = $page.params.courseId;
  $: assignmentId = $page.params.assignmentId;

  let submissions: any[] = [];
  let loading = true;
  let error: string | null = null;
  let text = '';
  let creating = false;

  async function load() {
    try {
      const token = localStorage.token ?? '';
      submissions = await listSubmissions(token, assignmentId);
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load submissions';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  async function onSubmit() {
    try {
      creating = true;
      const token = localStorage.token;
      const res = await createSubmission(token, assignmentId, { text });
      submissions = [res, ...submissions];
      text = '';
    } catch (e: any) {
      error = e?.detail ?? 'Submit failed';
    } finally {
      creating = false;
    }
  }
</script>

<Tabs {courseId} />

<section class="space-y-3">
  <h1 class="text-xl font-semibold">Submissions</h1>
  <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-4 space-y-2">
    <div class="text-sm font-medium">New submission</div>
    <textarea class="textarea textarea-bordered w-full" rows="4" bind:value={text} placeholder="Write your answer or notes here" />
    <button class="btn btn-primary" disabled={creating || !text.trim()} on:click={onSubmit}>Submit</button>
  </div>

  {#if loading}
    <p class="text-sm text-neutral-500">Loading…</p>
  {:else if error}
    <p class="text-sm text-red-500">{error}</p>
  {:else if !submissions?.length}
    <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-6 text-sm text-neutral-600 dark:text-neutral-400">No submissions yet.</div>
  {:else}
    <ul class="space-y-2">
      {#each submissions as s}
        <li class="rounded-md border border-neutral-200 dark:border-neutral-800 p-3">
          <div class="text-sm">{s.text}</div>
          <div class="text-xs text-neutral-500">status: {s.status}</div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
