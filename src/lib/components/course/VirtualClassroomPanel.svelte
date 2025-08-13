<script lang="ts">
  // Additive wrapper: reuse the existing DocumentPanel UI for the classroom sidebar.
  // This satisfies Chat.svelte's import path without touching upstream components.
  import DocumentPanel from '$lib/components/layout/DocumentPanel.svelte';
</script>

<DocumentPanel />

<style>
  /* No custom styles; rely on upstream tokens/spacing/typography */
</style>
