<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { getModels } from '$lib/apis';
  import { uploadFile } from '$lib/apis/files';
  import { createCourse, getCoursePresetTemplate, upsertCoursePreset } from '$lib/apis/classroom';
  import { user, config, settings, models, models as modelsStore } from '$lib/stores';
  import ModelSelector from '$lib/components/chat/ModelSelector.svelte';
  let toast: any;

  // Typography: ensure Helvetica where required via inline style in markup.

  // Course Basic Info (kept as original state shape for compatibility)
  let title = '';
  let code = '';
  let description = '';
  let term = '';
  let schedule = '';
  let instructors = ''; // serialized form (comma separated) kept for payload compatibility
  let links = '';
  let youtube = '';
  let visibility: 'private' | 'org' | 'public' = 'public';

  // For dynamic instructor rows (UI-only). We will sync to `instructors` before submit.
  type InstructorRow = { name: string; email?: string; id?: number };
  let instructorRows: InstructorRow[] = [{ name: '', email: '', id: 1 }];
  let nextInstructorId = 2;

  // Model Configuration
  let selectedModels = [''];
  let system_prompt = '';
  let temperature: number = 0.4;
  let top_p: number = 1.0;
  let frequency_penalty: number = 0.0;
  let presence_penalty: number = 0.0;
  let max_tokens: number = 1024;

  // UI State
  let uploading = false;
  let creating = false;
  let error: string | null = null;
  let docFileIds: string[] = [];
  let presetTemplate: any = null;
  let modelsLoading = true;
  let showAdvanced = false;

  // Activate immediately
  let activateNow = false;

  // Validation state
  let fieldErrors: Record<string, string> = {};

  // Dropzone file input ref
  let fileInput: HTMLInputElement | null = null;

  // Load models (same method as chat)
  async function loadModels() {
    try {
      modelsLoading = true;
      const token = typeof window !== 'undefined' ? (localStorage.token || '') : '';
      const modelsRes = await getModels(
        token,
        $config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
      );
      modelsStore.set(modelsRes);
    } catch (e) {
      console.error('[CourseCreate] Failed to load models:', e);
      toast.error('Failed to load models');
    } finally {
      modelsLoading = false;
    }
  }

  onMount(async () => {
    // dynamic import for optional toast dependency
    try { const sonner = await import('svelte-sonner'); toast = sonner.toast; } catch {}
    if ($user && $user.role && !['admin'].includes($user.role)) {
      await goto('/classroom');
      return;
    }
    try {
      const token = typeof window !== 'undefined' ? (localStorage.token || '') : '';
      presetTemplate = await getCoursePresetTemplate(token, 'new');
      if ($config && $settings) {
        await loadModels();
      }
      if (presetTemplate) {
        system_prompt = presetTemplate.system_prompt_md || '';
        temperature = presetTemplate.temperature ?? temperature;
        max_tokens = presetTemplate.max_tokens ?? max_tokens;
      }
      // Auto-select a suitable model if available
      if ($models.length > 0) {
        const defaultModel = $models.find((m) =>
          m.id === 'ai/smollm2:latest' ||
          (m.name || '').toLowerCase().includes('smollm') ||
          (m.id || '').toLowerCase().includes('smollm') ||
          (m.name || '').toLowerCase().includes('llama') ||
          (m.id || '').toLowerCase().includes('llama')
        ) || $models[0];
        selectedModels = [defaultModel.id];
      }
    } catch (e: any) {
      console.error('[CourseCreate] Initialization error:', e);
      error = e?.detail ?? 'Failed to load initialization data';
    }
  });

  // File upload handler reused (uploads files and stores ids)
  const onUpload = async (e: Event) => {
    const input = e.target as HTMLInputElement;
    const files = input.files;
    if (!files || !files.length) return;
    uploading = true;
    try {
      for (const f of Array.from(files)) {
        const res = await uploadFile(typeof window !== 'undefined' ? (localStorage.token || '') : '', f, null);
        if (res?.id) docFileIds.push(res.id);
      }
      docFileIds = [...docFileIds]; // trigger reactivity
    } catch (e: any) {
      console.error('[CourseCreate] Upload failed', e);
      toast.error('Upload failed');
    } finally {
      uploading = false;
      if (input) input.value = '';
    }
  };

  // Dropzone handlers
  function onDropzoneClick() {
    fileInput?.click();
  }
  function onDropzoneKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput?.click();
    }
  }
  function onDrop(e: DragEvent) {
    e.preventDefault();
    const files = e.dataTransfer?.files;
    if (files && files.length) {
      // reuse upload logic by setting file input.files is not allowed; call upload directly
      (async () => {
        uploading = true;
        try {
          for (const f of Array.from(files)) {
            const res = await uploadFile(typeof window !== 'undefined' ? (localStorage.token || '') : '', f, null);
            if (res?.id) docFileIds.push(res.id);
          }
          docFileIds = [...docFileIds];
        } catch (err) {
          console.error('[CourseCreate] Drop upload failed', err);
          toast.error('Drop upload failed');
        } finally {
          uploading = false;
        }
      })();
    }
  }
  function onDragOver(e: DragEvent) { e.preventDefault(); }

  const removeFile = (index: number) => {
    docFileIds = docFileIds.filter((_, i) => i !== index);
  };

  // Instructors dynamic rows
  function addInstructor() {
    instructorRows = [...instructorRows, { name: '', email: '', id: nextInstructorId++ }];
  }
  function removeInstructor(id: number) {
    if (instructorRows.length === 1) {
      instructorRows = [{ name: '', email: '', id: nextInstructorId++ }];
    } else {
      instructorRows = instructorRows.filter(r => r.id !== id);
    }
  }
  $: // sync instructors string for backwards compatibility (comma separated names)
    instructors = instructorRows.map(r => r.name.trim()).filter(Boolean).join(', ');

  // JSON validation helper used in advanced fields
  function validateJsonField(value: string, fieldName: string) {
    if (!value) { delete fieldErrors[fieldName]; return true; }
    try {
      JSON.parse(value);
      delete fieldErrors[fieldName];
      return true;
    } catch {
      fieldErrors[fieldName] = 'Invalid JSON';
      toast.error('Invalid JSON in ' + fieldName);
      return false;
    }
  }

  // Move on:blur handlers to script to avoid inline expressions in markup
  function handleToolsBlur(e: FocusEvent) {
    const t = e.target as HTMLTextAreaElement | null;
    validateJsonField(t?.value ?? '', 'tools_json');
  }
  function handleRetrievalBlur(e: FocusEvent) {
    const t = e.target as HTMLTextAreaElement | null;
    validateJsonField(t?.value ?? '', 'retrieval_json');
  }
  function handleSafetyBlur(e: FocusEvent) {
    const t = e.target as HTMLTextAreaElement | null;
    validateJsonField(t?.value ?? '', 'safety_json');
  }

  // Derived validation & disabled state (preserve same rules)
  $: disabled = !title.trim() || !selectedModels[0] || docFileIds.length < 1 || modelsLoading;

  // Create submit
  const onCreate = async () => {
    // local validations (title, model, ≥1 document) - keep behavior and toasts
    fieldErrors = {};
    if (!title.trim()) {
      fieldErrors.title = 'Title required';
      toast.error('Title required');
      return;
    }
    if (!selectedModels[0] || selectedModels[0] === '') {
      fieldErrors.model = 'Model required';
      toast.error('Model required');
      return;
    }
    if (docFileIds.length < 1) {
      fieldErrors.docFiles = 'At least one document required';
      toast.error('At least one document required');
      return;
    }

    creating = true;
    error = null;
    try {
      const body: any = {
        title: title.trim(),
        description: description || undefined,
        code: code || undefined,
        term: term || undefined,
        schedule: schedule || undefined,
        instructors: instructors ? instructors.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        links: links ? links.split('\n').map((s) => s.trim()).filter(Boolean) : undefined,
        youtube_embeds: youtube ? youtube.split('\n').map((s) => s.trim()).filter(Boolean) : undefined,
        visibility,
        doc_file_ids: docFileIds,
        model_id: selectedModels[0],
        system_prompt: system_prompt || undefined,
        temperature,
        top_p,
        frequency_penalty,
        presence_penalty,
        max_tokens
      };

      // Advanced JSON fields validation (if present in UI, here not added to payload unless set)
      // send payload as before
      const token = typeof window !== 'undefined' ? (localStorage.token || '') : '';
      const created = await createCourse(token, body as any);

      if (activateNow) {
        try {
          const res = await fetch(`/api/classroom/courses/${created.id}/activate`, {
            method: 'POST',
            headers: { Accept: 'application/json', authorization: `Bearer ${token}` }
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Activation failed' }));
            toast.error(err.detail || 'Activation failed');
          } else {
            toast.success('Course created & activated');
          }
        } catch (e: any) {
          toast.error('Activation request failed');
        }
      } else {
        toast.success('Course created');
      }

      await goto(`/classroom/${created.id}/overview`);
    } catch (e: any) {
      console.error('[CourseCreate] Creation failed:', e);
      const msg = e?.detail ?? 'Failed to create course';
      toast.error(msg);
      error = msg;
    } finally {
      creating = false;
    }
  };
</script>

<section class="max-w-6xl mx-auto p-4" style="font-family: Helvetica, Arial, sans-serif;">
  <div class="mb-6">
    <!-- Back to Admin Classroom Settings -->
    <div class="mb-3">
      <button type="button" class="text-sm px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700" on:click={() => goto('/admin/classroom')}>
        ← Back to Classroom Settings
      </button>
    </div>

    <h1 class="text-2xl font-semibold mb-1">Create New Course</h1>
    <div class="h-[1px] bg-neutral-800/10 dark:bg-neutral-700/20 w-full mb-6"></div>
  </div>

  <form on:submit|preventDefault={onCreate} class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Left: primary form (2/3 width) -->
    <div class="lg:col-span-2 space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="text-sm font-medium block mb-1" for="title">Course Title *</label>
          <input id="title" class="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-3 py-3 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="e.g., Introduction to Web Development" bind:value={title} aria-required="true" />
          {#if fieldErrors.title}<div class="text-xs text-red-500 mt-1">{fieldErrors.title}</div>{/if}
        </div>

        <div>
          <label class="text-sm font-medium block mb-1" for="code">Course Code</label>
          <input id="code" class="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-3 py-3 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="e.g., CS101" bind:value={code} />
        </div>
      </div>

      <div>
        <label class="text-sm font-medium block mb-1" for="description">Description</label>
        <textarea id="description" rows="4" class="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-3 py-3 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="Short, friendly summary for students." bind:value={description}></textarea>
        <div class="text-xs text-neutral-400 mt-1">Describe what students will learn in this course.</div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="text-sm font-medium block mb-1" for="term">Term</label>
          <input id="term" class="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-3 py-3 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="e.g., Fall 2024" bind:value={term} />
        </div>

        <div>
          <label class="text-sm font-medium block mb-1" for="schedule">Schedule</label>
          <input id="schedule" class="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-3 py-3 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="e.g., Mon/Wed/Fri 10:00-11:30" bind:value={schedule} />
        </div>
      </div>

      <!-- Model picker -->
      <div>
        <div class="flex items-center justify-between">
          <label class="text-sm font-medium block mb-1">Assigned Model *</label>
          <button type="button" class="text-xs text-neutral-400" on:click={() => showAdvanced = !showAdvanced} aria-expanded={showAdvanced}>{showAdvanced ? 'Hide' : 'Show'} Advanced</button>
        </div>
        <div class="text-xs text-neutral-400 mt-2">Select the AI model that students will use for this course.</div>
        {#if modelsLoading}
          <div class="p-3 border border-dashed rounded-md text-sm text-neutral-500">Loading models…</div>
        {:else if $models.length === 0}
          <div class="p-3 border border-dashed rounded-md text-sm text-red-500">No models available</div>
        {:else}
          <div class="mt-2">
            <ModelSelector bind:selectedModels={selectedModels} />
            {#if fieldErrors.model}<div class="text-xs text-red-500 mt-1">{fieldErrors.model}</div>{/if}
          </div>
        {/if}
      </div>

      <!-- Instructors -->
      <div>
        <label class="text-sm font-medium block mb-2">Instructors</label>
        <div class="space-y-3">
          {#each instructorRows as row (row.id)}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 items-center">
              <input aria-label="Instructor name" class="rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="Instructor name" bind:value={row.name} on:input={() => { instructorRows = [...instructorRows]; }} />
              <div class="flex items-center gap-2">
                <input aria-label="Instructor email" class="flex-1 rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="Email (optional)" bind:value={row.email} on:input={() => { instructorRows = [...instructorRows]; }} />
                <button type="button" class="text-sm text-red-500 px-2 py-1 hover:bg-red-50 rounded-md" on:click={() => removeInstructor(row.id)} aria-label="Remove instructor">×</button>
              </div>
            </div>
          {/each}
        </div>
        <button type="button" class="text-sm text-blue-400 mt-2 hover:underline" on:click={addInstructor}>+ Add Instructor</button>
      </div>

      <!-- Links & YouTube -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="text-sm font-medium block mb-1">Links (one per line)</label>
          <textarea rows="3" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="https://example.com" bind:value={links}></textarea>
          <div class="text-xs text-neutral-400 mt-1">Provide links to external resources (one per line).</div>
        </div>

        <div>
          <label class="text-sm font-medium block mb-1">YouTube URLs (one per line)</label>
          <textarea rows="3" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="https://youtube.com/watch?v=..." bind:value={youtube}></textarea>
          <div class="text-xs text-neutral-400 mt-1">Optional videos to surface in the course.</div>
        </div>
      </div>

      <!-- Advanced (collapsed) -->
      {#if showAdvanced}
        <div class="p-4 border rounded-md border-gray-200 dark:border-gray-700 space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="text-sm font-medium block mb-1">Temperature</label>
              <input type="number" step="0.01" min="0" max="1" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" bind:value={temperature} />
            </div>
            <div>
              <label class="text-sm font-medium block mb-1">Top P</label>
              <input type="number" step="0.01" min="0" max="1" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" bind:value={top_p} />
            </div>
            <div>
              <label class="text-sm font-medium block mb-1">Max tokens</label>
              <input type="number" step="1" min="16" max="65536" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" bind:value={max_tokens} />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="text-sm font-medium block mb-1">Frequency penalty</label>
              <input type="number" step="0.01" min="-2" max="2" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" bind:value={frequency_penalty} />
            </div>
            <div>
              <label class="text-sm font-medium block mb-1">Presence penalty</label>
              <input type="number" step="0.01" min="-2" max="2" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" bind:value={presence_penalty} />
            </div>
            <div class="text-sm text-neutral-500"> </div>
          </div>

          <div>
            <label class="text-sm font-medium block mb-1">Tools JSON</label>
            <textarea rows="4" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" on:blur={handleToolsBlur}></textarea>
            {#if fieldErrors.tools_json}<div class="text-xs text-red-500 mt-1">{fieldErrors.tools_json}</div>{/if}
          </div>

          <div>
            <label class="text-sm font-medium block mb-1">Retrieval JSON</label>
            <textarea rows="4" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" on:blur={handleRetrievalBlur}></textarea>
            {#if fieldErrors.retrieval_json}<div class="text-xs text-red-500 mt-1">{fieldErrors.retrieval_json}</div>{/if}
          </div>

          <div>
            <label class="text-sm font-medium block mb-1">Safety JSON</label>
            <textarea rows="4" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" on:blur={handleSafetyBlur}></textarea>
            {#if fieldErrors.safety_json}<div class="text-xs text-red-500 mt-1">{fieldErrors.safety_json}</div>{/if}
          </div>
        </div>
      {/if}
    </div>

    <!-- Right: side column for materials + actions (1/3 width) -->
    <div class="space-y-6">
      <!-- Materials (dropzone) -->
      <div>
        <label class="text-sm font-medium block mb-2">Course Materials *</label>
        <div class="flex items-center justify-between mb-2">
          <div class="text-xs text-neutral-400">At least one document required for knowledge base</div>
          <div class="text-xs text-neutral-400">PDF, Word, PowerPoint, Text</div>
        </div>

        <div
          role="button"
          tabindex="0"
          class="border-2 border-dashed rounded-md p-6 text-center hover:bg-gray-50 dark:hover:bg-gray-800 focus-visible:outline-2 focus-visible:outline-blue-500 cursor-pointer bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700"
          on:click={onDropzoneClick}
          on:keydown={onDropzoneKeydown}
          on:drop={onDrop}
          on:dragover={onDragOver}
          aria-label="Upload course materials"
        >
          <input bind:this={fileInput} type="file" accept=".pdf,.doc,.docx,.txt,.md,.ppt,.pptx" multiple class="hidden" on:change={onUpload} />
          <div class="text-neutral-500 mb-3 text-2xl">⬆️</div>
          <div class="font-medium">Drop files here or click to upload</div>
          {#if fieldErrors.docFiles}
            <div class="text-xs text-red-500 mt-2">{fieldErrors.docFiles}</div>
          {:else}
            <div class="text-xs text-neutral-400 mt-2">Upload documents which the assistant will index for the course</div>
          {/if}
        </div>

        {#if docFileIds.length > 0}
          <div class="mt-3 space-y-2">
            {#each docFileIds as id, i}
              <div class="flex items-center justify-between bg-white/50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md px-3 py-2 text-sm">
                <div class="truncate">Document {i + 1} — ID: {id}</div>
                <button type="button" class="text-sm text-red-500" on:click={() => removeFile(i)}>Remove</button>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Actions card -->
      <div class="p-4 border rounded-md border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm font-semibold">Create Course</div>
            <div class="text-xs text-neutral-400">When ready, create the course and optionally activate it.</div>
          </div>
          <div class="text-sm text-neutral-500">Status: Draft</div>
        </div>

        <label class="inline-flex items-center gap-2">
          <input type="checkbox" class="w-4 h-4 rounded focus:ring-2 focus:ring-blue-500" bind:checked={activateNow} />
          <span class="text-sm">Activate course immediately</span>
        </label>

        <div class="flex items-center gap-3 justify-end pt-2">
          <button type="button" class="px-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 text-sm hover:bg-gray-50 dark:hover:bg-gray-800" on:click={() => {
            // Reset form safely (preserve models loading)
            title=''; code=''; description=''; term=''; schedule=''; instructorRows=[{name:'', email:'', id: nextInstructorId++}]; links=''; youtube=''; docFileIds=[]; selectedModels=['']; activateNow=false; toast.success('Form reset');
          }}>Reset</button>

          <button type="submit" class="px-4 py-2 rounded-md bg-blue-600 text-white text-sm" disabled={disabled || uploading || creating || modelsLoading} aria-disabled={disabled || uploading || creating || modelsLoading}>
            {#if creating}
              Creating…
            {:else}
              Create Course
            {/if}
          </button>
        </div>
      </div>
    </div>

    <!-- Full-width footer spacing handled by grid -->
  </form>
</section>

<style>
  /* Slightly larger dropzone icon and clamp lines for description previews */
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
