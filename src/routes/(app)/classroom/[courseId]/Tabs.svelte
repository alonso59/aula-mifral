<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  export let courseId: string;
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'materials', label: 'Materials' },
    { id: 'assignments', label: 'Assignments' },
    { id: 'chat', label: 'Chat' },
    { id: 'settings', label: 'Settings', roles: ['admin','teacher'] }
  ];
  $: current = ($page.url.pathname.split('/').pop()) || 'overview';
  const go = (id: string) => goto(`/classroom/${courseId}/${id}`);
  $: visibleTabs = tabs.filter(t => !t.roles || ($user && t.roles.includes($user.role)));
  $: currentValid = visibleTabs.find(t => t.id === current) ? current : 'overview';
  if (current !== currentValid) {
    // Redirect if user cannot access current tab
    go(currentValid);
  }
</script>

<nav class="border-b border-neutral-200 dark:border-neutral-800 mb-4">
  <ul class="flex gap-4 text-sm">
    {#each visibleTabs as t}
      <li>
        <button
          class="py-2 px-1 border-b-2 transition-colors"
          class:border-primary-500={currentValid === t.id}
          class:border-transparent={currentValid !== t.id}
          on:click={() => go(t.id)}
        >{t.label}</button>
      </li>
    {/each}
  </ul>
</nav>

<slot />
