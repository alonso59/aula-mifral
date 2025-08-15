<script lang="ts">
  import { showSidebar } from '$lib/stores';
  import MenuLines from '$lib/components/icons/MenuLines.svelte';
  import { getContext } from 'svelte';
  const i18n = getContext('i18n');
</script>

<svelte:head>
  <title>{$i18n.t('Aula Mifral')}</title>
</svelte:head>

<div class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar ? 'md:max-w-[calc(100%-260px)]' : ''} max-w-full">
  <nav class="px-2.5 pt-1 backdrop-blur-xl w-full drag-region" aria-label="Classroom shell">
    <div class="flex items-center">
      <div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
        <button
          id="sidebar-toggle-button"
          class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
          on:click={() => showSidebar.set(!$showSidebar)}
          aria-label="Toggle Sidebar"
        >
          <div class="m-auto self-center">
            <MenuLines />
          </div>
        </button>
      </div>
    </div>
  </nav>

  <!-- Keep this as the scroll container; the left nav in [courseId]/+layout.svelte will be sticky relative to it -->
  <div class="flex-1 max-h-full overflow-y-auto">
    <slot />
  </div>
</div>
