<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { user } from '$lib/stores';

  $: courseId = $page.params.courseId;

  let enrollments: any[] = [];
  let loading = true;
  let error: string | null = null;
  let newUserId = '';
  let isTeacher = false;
  let adding = false;

  const isTeacherOrAdmin = () => $user && ['admin', 'teacher'].includes($user.role);

  onMount(async () => {
    if (!isTeacherOrAdmin()) {
      error = 'Access denied';
      loading = false;
      return;
    }
    await loadEnrollments();
  });

  async function loadEnrollments() {
    loading = true;
    error = null;
    try {
      const res = await fetch(`/api/classroom/courses/${courseId}/enrollments`, {
        headers: { authorization: `Bearer ${localStorage.token}` }
      });
      if (!res.ok) throw await res.json();
      enrollments = await res.json();
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load enrollments';
    } finally {
      loading = false;
    }
  }

  async function addEnrollment() {
    if (!newUserId.trim()) return;
    adding = true;
    try {
      const res = await fetch(`/api/classroom/courses/${courseId}/enrollments`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          authorization: `Bearer ${localStorage.token}` 
        },
        body: JSON.stringify({ user_id: newUserId.trim(), is_teacher: isTeacher })
      });
      if (!res.ok) throw await res.json();
      newUserId = '';
      isTeacher = false;
      await loadEnrollments();
    } catch (e: any) {
      error = e?.detail ?? 'Failed to add enrollment';
    } finally {
      adding = false;
    }
  }

  async function removeEnrollment(userId: string) {
    if (!confirm('Remove this enrollment?')) return;
    try {
      const res = await fetch(`/api/classroom/courses/${courseId}/enrollments/${userId}`, {
        method: 'DELETE',
        headers: { authorization: `Bearer ${localStorage.token}` }
      });
      if (!res.ok) throw await res.json();
      await loadEnrollments();
    } catch (e: any) {
      error = e?.detail ?? 'Failed to remove enrollment';
    }
  }
</script>

<div class="space-y-4">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold">Course Enrollments</h1>
    <a href="/classroom/{courseId}" class="btn btn-ghost btn-sm">← Back to Course</a>
  </div>

  {#if !isTeacherOrAdmin()}
    <div class="text-sm text-red-500">Access denied</div>
  {:else if loading}
    <div class="text-sm text-neutral-500">Loading…</div>
  {:else}
    {#if error}
      <div class="text-sm text-red-500">{error}</div>
    {/if}

    <!-- Add new enrollment -->
    <div class="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4 space-y-3">
      <h2 class="text-sm font-semibold">Add Enrollment</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <input 
          class="input input-bordered w-full" 
          placeholder="User ID" 
          bind:value={newUserId}
        />
        <label class="flex items-center gap-2">
          <input type="checkbox" bind:checked={isTeacher} />
          <span class="text-sm">Teacher role</span>
        </label>
        <button 
          class="btn btn-primary" 
          disabled={!newUserId.trim() || adding} 
          on:click={addEnrollment}
        >
          {adding ? 'Adding…' : 'Add'}
        </button>
      </div>
    </div>

    <!-- Enrollments list -->
    <div class="rounded-lg border border-neutral-200 dark:border-neutral-800">
      <div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-800">
        <h2 class="text-sm font-semibold">Current Enrollments ({enrollments.length})</h2>
      </div>
      {#if !enrollments.length}
        <div class="p-4 text-sm text-neutral-500">No enrollments yet.</div>
      {:else}
        <div class="divide-y divide-neutral-200 dark:divide-neutral-800">
          {#each enrollments as enrollment}
            <div class="px-4 py-3 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="text-sm font-medium">{enrollment.user_id}</div>
                {#if enrollment.is_teacher}
                  <span class="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">Teacher</span>
                {:else}
                  <span class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded">Student</span>
                {/if}
              </div>
              <button 
                class="btn btn-ghost btn-xs text-red-600 hover:text-red-700"
                on:click={() => removeEnrollment(enrollment.user_id)}
              >
                Remove
              </button>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>
