<script lang="ts">
  import Tabs from '../Tabs.svelte';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { getCoursePreset, getCoursePresetTemplate, previewCoursePreset, upsertCoursePreset, setCoursePresetDefault } from '$lib/apis/classroom';
  import type { CoursePreset } from '$lib/types/course';

  $: courseId = $page.params.courseId;

  let step: number = 0;
  let draft: any = {};
  let preview: any = null;
  let loading = false;
  let error: string | null = null;
  let toolsJsonText = '';
  let retrievalJsonText = '';
  let safetyJsonText = '';

  const steps = ['Model', 'Knowledge', 'Prompt', 'Tools', 'Retrieval', 'Safety', 'Defaults'];

  async function load() {
    try {
      const token = localStorage.token;
      const preset = await getCoursePreset(token, courseId).catch(() => null);
      const template = await getCoursePresetTemplate(token, courseId);
  draft = {
        name: template.name ?? 'Study & Learn',
        is_default: preset?.is_default ?? false,
        provider: preset?.provider ?? template.provider ?? null,
        model_id: preset?.model_id ?? template.model_id ?? null,
        temperature: preset?.temperature ?? template.temperature ?? 0.4,
        max_tokens: preset?.max_tokens ?? template.max_tokens ?? 1024,
        system_prompt_md: preset?.system_prompt_md ?? template.system_prompt_md ?? '',
        tools_json: preset?.tools_json ?? template.tools_json ?? { enabled: ['citations'], disabled: ['web_browse', 'code_exec'] },
        retrieval_json: preset?.retrieval_json ?? template.retrieval_json ?? { top_k: 6, max_context_tokens: 6000, return_citations: true },
        safety_json: preset?.safety_json ?? template.safety_json ?? null,
        knowledge_id: preset?.knowledge_id ?? null
      } as Partial<CoursePreset> & any;
  toolsJsonText = JSON.stringify(draft.tools_json ?? {}, null, 2);
  retrievalJsonText = JSON.stringify(draft.retrieval_json ?? {}, null, 2);
  safetyJsonText = JSON.stringify(draft.safety_json ?? {}, null, 2);
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load preset/template';
    }
  }

  onMount(load);

  async function doPreview() {
    try {
      loading = true;
      const token = localStorage.token;
      preview = await previewCoursePreset(token, courseId, draft as any, []);
    } catch (e: any) {
      error = e?.detail ?? 'Preview failed';
    } finally {
      loading = false;
    }
  }

  async function saveDraft(setDefault = false) {
    try {
      loading = true;
      const token = localStorage.token;
      const saved = await upsertCoursePreset(token, courseId, { ...(draft as any), is_default: setDefault ? true : draft.is_default });
      if (setDefault) {
        await setCoursePresetDefault(token, courseId);
      }
      await load();
    } catch (e: any) {
      error = e?.detail ?? 'Save failed';
    } finally {
      loading = false;
    }
  }

  function discard() {
    load();
  }
</script>

<Tabs {courseId} />

<section class="space-y-4">
  <h1 class="text-xl font-semibold">Study &amp; Learn — Preset Builder</h1>

  <div class="flex gap-4">
    <div class="flex-1 space-y-3">
      <div class="flex items-center gap-2 flex-wrap">
        {#each steps as label, i}
          <button class="px-2 py-1 rounded text-sm border border-neutral-300 dark:border-neutral-700 {i === step ? 'bg-neutral-200 dark:bg-neutral-800' : ''}" on:click={() => (step = i)}>{i + 1}. {label}</button>
        {/each}
      </div>

      {#if step === 0}
        <div class="space-y-2">
          <label class="block text-sm">Provider</label>
          <input class="input input-bordered w-full" bind:value={draft.provider} placeholder="openai|ollama|..." />
          <label class="block text-sm">Model ID</label>
          <input class="input input-bordered w-full" bind:value={draft.model_id} placeholder="gpt-4o-mini|ai/smollm2:360M-Q4_K_M" />
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-sm">Temperature</label>
              <input class="input input-bordered w-full" type="number" min="0" max="2" step="0.1" bind:value={draft.temperature} />
            </div>
            <div>
              <label class="block text-sm">Max Tokens</label>
              <input class="input input-bordered w-full" type="number" min="1" bind:value={draft.max_tokens} />
            </div>
          </div>
        </div>
      {:else if step === 1}
        <div class="space-y-2">
          <label class="block text-sm">Knowledge ID</label>
          <input class="input input-bordered w-full" bind:value={draft.knowledge_id} placeholder="kb_..." />
        </div>
      {:else if step === 2}
        <div class="space-y-2">
          <label class="block text-sm">System Prompt (Markdown)</label>
          <textarea class="textarea textarea-bordered w-full min-h-[200px]" bind:value={draft.system_prompt_md}></textarea>
        </div>
      {:else if step === 3}
        <div class="space-y-2">
          <label class="block text-sm">Tools JSON</label>
          <textarea
            class="textarea textarea-bordered w-full min-h-[160px]"
            bind:value={toolsJsonText}
            on:change={(e)=>{ try { draft.tools_json = JSON.parse(e.target.value); } catch {} }}
          ></textarea>
        </div>
      {:else if step === 4}
        <div class="space-y-2">
          <label class="block text-sm">Retrieval JSON</label>
          <textarea
            class="textarea textarea-bordered w-full min-h-[160px]"
            bind:value={retrievalJsonText}
            on:change={(e)=>{ try { draft.retrieval_json = JSON.parse(e.target.value); } catch {} }}
          ></textarea>
        </div>
      {:else if step === 5}
        <div class="space-y-2">
          <label class="block text-sm">Safety JSON</label>
          <textarea
            class="textarea textarea-bordered w-full min-h-[160px]"
            bind:value={safetyJsonText}
            on:change={(e)=>{ try { draft.safety_json = JSON.parse(e.target.value); } catch {} }}
          ></textarea>
        </div>
      {:else}
        <div class="space-y-2">
          <label class="inline-flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={draft.is_default} /> Set as default after save</label>
          <label class="block text-sm">Name</label>
          <input class="input input-bordered w-full" bind:value={draft.name} placeholder="Study & Learn" />
        </div>
      {/if}

      <div class="flex gap-2">
        <button class="btn" disabled={loading} on:click={() => saveDraft(false)}>Save Draft</button>
        <button class="btn btn-primary" disabled={loading} on:click={() => saveDraft(true)}>Save & Set as Default</button>
        <button class="btn btn-ghost" on:click={discard}>Discard</button>
        <button class="btn" disabled={loading} on:click={doPreview}>Preview</button>
      </div>
      {#if error}
        <div class="text-sm text-red-600">{error}</div>
      {/if}
    </div>

    <div class="w-[420px] border border-neutral-200 dark:border-neutral-800 rounded p-3">
      <div class="text-sm font-medium mb-2">Live Preview</div>
      {#if preview}
        <pre class="text-xs whitespace-pre-wrap">{JSON.stringify(preview, null, 2)}</pre>
      {:else}
        <div class="text-xs text-neutral-500">No preview yet. Click Preview to render a stubbed response. Citations included if enabled.</div>
      {/if}
    </div>
  </div>
</section>
