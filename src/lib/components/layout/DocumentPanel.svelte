<!-- filepath: c:\Users\germa\Documents\aula-mifral\src\lib\components\layout\DocumentPanel.svelte -->
<script lang="ts">
  import { getContext } from 'svelte';
  const i18n = getContext('i18n');
  // Minimal, additive stub to satisfy imports; replace with richer UI as needed.
  export let title: string | undefined;
</script>

<div class="h-full w-full overflow-y-auto bg-white dark:bg-gray-850">
  <div class="p-4 border-b border-gray-200 dark:border-gray-700">
  <h2 class="text-sm font-semibold text-gray-900 dark:text-white">{title ?? ($i18n?.t ? $i18n.t('Course Materials') : 'Course Materials')}</h2>
    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
  {$i18n?.t ? $i18n.t('Manage and view course materials here.') : 'Manage and view course materials here.'}
    </p>
  </div>
  <div class="p-4 text-sm text-gray-600 dark:text-gray-300">
    <slot>
  {$i18n?.t ? $i18n.t('No documents yet.') : 'No documents yet.'}
    </slot>
  </div>
</div>
