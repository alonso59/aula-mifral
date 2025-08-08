<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import { classroomEnabled } from '$lib/stores/classroom';

  let enabled = false;
  let loading = true;
  let saving = false;

  onMount(async () => {
    if ($user?.role !== 'admin') {
      goto('/');
      return;
    }

    try {
      const res = await fetch('/api/admin/settings/classroom', { headers: { Accept: 'application/json', authorization: `Bearer ${localStorage.token}` }});
      if (res.ok) {
        const data = await res.json();
        enabled = !!data.enabled;
        classroomEnabled.set(enabled);
      }
    } finally {
      loading = false;
    }
  });

  async function save() {
    saving = true;
    try {
      const res = await fetch('/api/admin/settings/classroom', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json', authorization: `Bearer ${localStorage.token}` },
        body: JSON.stringify({ enabled })
      });
      if (res.ok) {
        classroomEnabled.set(enabled);
      }
    } finally {
      saving = false;
    }
  }
</script>

<div class="p-4 space-y-4">
  <div>
    <h1 class="text-lg font-semibold">Classroom</h1>
    <p class="text-sm text-gray-600 dark:text-gray-300">Toggle the Virtual Classroom and manage courses and groups.</p>
  </div>

  <div class="rounded-xl border border-gray-200 dark:border-gray-800 p-4">
    {#if loading}
      <div class="text-sm text-gray-500">Loading…</div>
    {:else}
      <label class="flex items-center gap-3">
        <input type="checkbox" bind:checked={enabled} />
        <span>Enable Classroom</span>
      </label>
      <div class="mt-3">
        <button class="px-3 py-1.5 rounded-md bg-blue-600 text-white disabled:opacity-60" on:click={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
      </div>
    {/if}
  </div>

  <div class="grid md:grid-cols-2 gap-4">
    <div class="rounded-xl border border-gray-200 dark:border-gray-800 p-4">
      <div class="font-medium mb-1">Courses</div>
      <div class="text-sm text-gray-600 dark:text-gray-300 mb-3">Create, edit, and archive courses.</div>
      <div class="flex gap-2">
        <a href="/classroom" class="px-3 py-1.5 rounded-md bg-gray-100 dark:bg-gray-900">Open Classroom</a>
        <button class="px-3 py-1.5 rounded-md bg-gray-100 dark:bg-gray-900" on:click={() => alert('Course creation UI coming soon')}>New Course</button>
      </div>
    </div>

    <div class="rounded-xl border border-gray-200 dark:border-gray-800 p-4">
      <div class="font-medium mb-1">Groups</div>
      <div class="text-sm text-gray-600 dark:text-gray-300 mb-3">Manage student groups and enrollment (admin only).</div>
      <button class="px-3 py-1.5 rounded-md bg-gray-100 dark:bg-gray-900" on:click={() => alert('Groups management UI coming soon')}>Open Groups</button>
    </div>
  </div>
</div>
