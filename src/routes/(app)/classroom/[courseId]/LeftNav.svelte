<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';        // <-- import as `user`

  export let courseId: string;
  export let iconsOnly = true;

  // paths
  $: base = `/classroom/${courseId ?? $page.params.courseId ?? ''}`.replace(/\/$/, '');
  $: pathname = $page.url.pathname;

  // nav items (add roles if you want RBAC)
  const items = [
    { id: 'overview',  label: 'Overview',  icon: 'home' },
    { id: 'materials', label: 'Materials', icon: 'file' },
    { id: 'chat',      label: 'Chat',      icon: 'chat' },
  ];

  // show all unless item has roles and user lacks them
  $: visible = items.filter(i => !i.roles || ($user && i.roles.includes($user.role)));

  // compute active from URL
  $: active = (() => {
    const seg = pathname.startsWith(base)
      ? (pathname.slice(base.length + 1).split('/')[0] || 'overview')
      : 'overview';
    return visible.some(v => v.id === seg) ? seg : 'overview';
  })();

  function go(id: string) { if (id !== active) goto(`${base}/${id}`); }

  // tiny inline icons
  function icon(name: string, on: boolean) {
    const stroke = 'currentColor';
    const op = on ? '1' : '0.75';
    if (name === 'home')
      return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:${op}"><path d="M3 11l9-8 9 8"/><path d="M9 22V12h6v10"/></svg>`;
    if (name === 'file')
      return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:${op}"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>`;
    if (name === 'chat')
      return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:${op}"><path d="M21 15a4 4 0 0 1-4 4H7l-4 4V5a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/></svg>`;
    return '';
  }
</script>

<nav class="p-2" aria-label="Course sections">
  {#if iconsOnly}
    <ul class="flex lg:flex-col gap-2">
      {#each visible as t}
        <li>
          <button
            class="w-10 h-10 rounded-md border flex items-center justify-center transition
                   {active === t.id
                      ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900 border-transparent'
                      : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'}"
            on:click={() => go(t.id)}
            aria-current={active === t.id ? 'page' : undefined}
            aria-label={t.label}
            title={t.label}
          >
            {@html icon(t.icon, active === t.id)}
          </button>
        </li>
      {/each}
    </ul>
  {:else}
    <ul class="space-y-1">
      {#each visible as t}
        <li>
          <button
            on:click={() => go(t.id)}
            class="w-full text-left px-3 py-2 rounded-md text-sm border flex items-center gap-2 transition
                   {active === t.id
                     ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900 border-transparent'
                     : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800'}"
            aria-current={active === t.id ? 'page' : undefined}
          >
            <span class="shrink-0" aria-hidden="true">{@html icon(t.icon, active === t.id)}</span>
            <span class="truncate">{t.label}</span>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</nav>
