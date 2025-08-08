<script lang="ts">
  import Chat from '$lib/components/chat/Chat.svelte';
  import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { user } from '$lib/stores';

  export let courseId: string;

  let preset: any = null;
  let blocked = false;
  let loading = true;
  let error: string | null = null;
  let discuss: string | null = null;

  // Badges data
  $: badges = [
    preset?.model_id && { label: preset.model_id },
    typeof preset?.temperature === 'number' && { label: `temp ${preset.temperature}` },
    preset?.knowledge_id && { label: `KB linked` }
  ].filter(Boolean) as { label: string }[];

  onMount(async () => {
    try {
  discuss = $page.url.searchParams.get('discuss');
      const token = '';
      // Fetch preset to lock model selector and display badges
      const res = await fetch(`/api/classroom/courses/${courseId}/preset`, {
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
      });
      if (!res.ok) throw await res.json();
      preset = await res.json();
    } catch (e: any) {
      // No preset yet is fine; badges remain empty
    } finally {
      loading = false;
    }
  });
</script>

<div class="flex items-center justify-between mb-3">
  <h1 class="text-xl font-semibold">Course Chat</h1>
  <div class="flex gap-2 text-xs text-neutral-600 dark:text-neutral-400">
    {#if badges.length}
      {#each badges as b}
        <span class="inline-flex items-center rounded-full border border-neutral-200 dark:border-neutral-800 px-2 py-0.5">{b.label}</span>
      {/each}
    {:else}
      <span class="text-neutral-500">No preset configured</span>
    {/if}
  </div>
</div>

<!-- Hide the Model Selector; the course preset controls the model -->
<Chat {courseId} showModelSelector={false} initialUserPrompt={discuss ? `Discuss assignment: ${discuss}` : undefined} />
