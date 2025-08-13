<script lang="ts">
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';

  export let open: boolean = false;
  export let title: string = 'Confirm';
  export let description: string = '';
  export let confirmLabel: string = 'Confirm';
  export let cancelLabel: string = 'Cancel';
  export let destructive: boolean = false;

  const dispatch = createEventDispatcher();

  let dialogEl: HTMLDivElement | null = null;
  let previouslyFocused: Element | null = null;

  function close(reason = 'cancel') {
    dispatch(reason === 'confirm' ? 'confirm' : 'cancel');
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      close('cancel');
    } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      // allow Cmd/Ctrl+Enter to confirm
      e.preventDefault();
      close('confirm');
    }
  }

  // Basic focus trap: remember previous focus and focus the dialog
  onMount(() => {
    if (!open) return;
    previouslyFocused = document.activeElement;
    setTimeout(() => {
      dialogEl?.querySelector<HTMLButtonElement>('button[data-autofocus]')?.focus();
    }, 0);
    window.addEventListener('keydown', onKeydown);
  });

  onDestroy(() => {
    window.removeEventListener('keydown', onKeydown);
    try { (previouslyFocused as HTMLElement | null)?.focus(); } catch {}
  });

  $: if (open) {
    // when open toggles to true, ensure focus is set
    setTimeout(() => {
      dialogEl?.querySelector<HTMLButtonElement>('button[data-autofocus]')?.focus();
    }, 0);
  }
</script>

{#if open}
  <div class="fixed inset-0 z-50 flex items-center justify-center px-4">
    <div class="absolute inset-0 bg-black/50" on:click={() => close('cancel')} aria-hidden="true"></div>

    <div bind:this={dialogEl} role="dialog" aria-modal="true" aria-labelledby="confirm-title" class="relative w-full max-w-lg bg-white dark:bg-gray-900 rounded-lg shadow-lg border border-gray-200 dark:border-gray-800 p-5">
      <h2 id="confirm-title" class="text-lg font-semibold">{title}</h2>
      {#if description}
        <p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{description}</p>
      {/if}

      <div class="mt-4 flex justify-end gap-3">
        <button class="px-4 py-2 rounded-md bg-transparent border border-gray-300 dark:border-gray-700 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" on:click={() => close('cancel')}>
          {cancelLabel}
        </button>

        <button data-autofocus class="px-4 py-2 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 {destructive ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-blue-600 text-white hover:bg-blue-700'}" on:click={() => close('confirm')}>
          {confirmLabel}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  /* minimal modal styles; uses Tailwind classes in markup */
</style>
