<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  export let courseId: string;
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'materials', label: 'Materials' },
    { id: 'assignments', label: 'Assignments' },
    { id: 'chat', label: 'Chat' },
    { id: 'settings', label: 'Settings' }
  ];
  $: current = ($page.url.pathname.split('/').pop()) || 'overview';
  const go = (id: string) => goto(`/classroom/${courseId}/${id}`);
</script>

<nav class="border-b border-neutral-200 dark:border-neutral-800 mb-4">
  <ul class="flex gap-4 text-sm">
    {#each tabs as t}
      <li>
        <button
          class="py-2 px-1 border-b-2 transition-colors"
          class:border-primary-500={current === t.id}
          class:border-transparent={current !== t.id}
          on:click={() => go(t.id)}
        >{t.label}</button>
      </li>
    {/each}
  </ul>
</nav>

<slot />
