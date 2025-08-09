<script lang="ts">
  import Chat from '$lib/components/chat/Chat.svelte';
  import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { user, models } from '$lib/stores';
  import { getCourse } from '$lib/apis/classroom';

  export let courseId: string;

  let preset: any = null;
  let course: any = null;
  let courseModel: string | null = null;
  let selectedModels: string[] = [];
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
      const token = localStorage.token || '';
      
      // Fetch course data to get model information
      course = await getCourse(token, courseId);
      
      // Fetch preset to lock model selector and display badges
      const res = await fetch(`/api/classroom/courses/${courseId}/preset`, {
        headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
      });
      if (!res.ok) throw await res.json();
      preset = await res.json();
      
      // Auto-select course model if available
      if (preset?.model_id) {
        courseModel = preset.model_id;
        selectedModels = [preset.model_id];
        
        // Verify the model exists in available models
        const modelExists = $models.find(m => m.id === courseModel);
        if (!modelExists) {
          console.warn(`Course model ${courseModel} not found in available models`);
          error = 'Course AI model not available. Please contact your instructor.';
        }
      }
    } catch (e: any) {
      console.error('Failed to load course data:', e);
      error = 'Failed to load course configuration';
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
{#if loading}
  <div class="flex justify-center items-center h-64">
    <div class="loading loading-spinner loading-lg"></div>
  </div>
{:else if error}
  <div class="alert alert-error mb-4">
    <div class="text-sm">{error}</div>
  </div>
{:else}
  <Chat
    {courseId}
    showModelSelector={false}
    selectedModels={courseModel ? [courseModel] : []}
    atSelectedModel={courseModel ? { id: courseModel, name: `${course?.title || 'Course'} AI Assistant` } : undefined}
    initialUserPrompt={discuss ? `Discuss assignment: ${discuss}` : undefined}
    completionBaseUrl={`/api/classroom/courses/${courseId}`}
  />
{/if}
