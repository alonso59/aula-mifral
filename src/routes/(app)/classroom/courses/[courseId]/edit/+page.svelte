<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getModels } from '$lib/apis';
  import { uploadFile } from '$lib/apis/files';
  import { getCourse, updateCourse, getCoursePresetTemplate } from '$lib/apis/classroom';
  import { user, models as modelsStore } from '$lib/stores';
  import ModelSelector from '$lib/components/chat/ModelSelector.svelte';

  $: courseId = $page.params.courseId;

  // Course Basic Info
  let title = '';
  let code = '';
  let description = '';
  let term = '';
  let schedule = '';
  let instructors = '';
  let links = '';
  let youtube = '';
  let visibility: 'private' | 'org' | 'public' = 'public';

  // Model Configuration (preserve modelId for payload compatibility)
  let modelId = '';
  let selectedModels: string[] = [''];
  let system_prompt = '';
  let temperature: number = 0.4;
  let max_tokens: number = 1024;

  // UI State
  let uploading = false;
  let updating = false;
  let loading = true;
  let error: string | null = null;
  let models: any[] = [];
  let docFileIds: string[] = [];
  let currentStep = 1;
  let presetTemplate: any = null;
  let course: any = null;

  const steps = [
    { title: 'Course Details', subtitle: 'Basic information about your course' },
    { title: 'Learning Materials', subtitle: 'Upload documents for the AI assistant' },
    { title: 'AI Assistant', subtitle: 'Configure how students interact with content' }
  ];

  async function safeToken() {
    return (typeof window !== 'undefined' ? (localStorage.token || '') : '');
  }

  onMount(async () => {
    if ($user && $user.role && !['admin','teacher'].includes($user.role)) {
      await goto('/classroom');
      return;
    }
    try {
      loading = true;
      const token = await safeToken();
      const [modelsRes, courseRes, templateRes] = await Promise.all([
        getModels(token),
        getCourse(token, courseId),
        getCoursePresetTemplate(token, courseId)
      ]);

      models = modelsRes ?? [];
      course = courseRes ?? null;
      presetTemplate = templateRes ?? null;

      // Pre-fill form with existing course data
      if (course) {
        title = course.title || '';
        code = course.code || '';
        description = course.description || '';
        term = course.term || '';
        schedule = course.schedule || '';
        instructors = course.instructors ? course.instructors.join(', ') : '';
        links = course.links ? course.links.join(',\n') : '';
        youtube = course.youtube_embeds ? course.youtube_embeds.join(',\n') : '';
        visibility = course.visibility || 'public';
        modelId = course.model_id || '';
        system_prompt = course.system_prompt || '';
        temperature = course.temperature ?? 0.4;
        max_tokens = course.max_tokens ?? 1024;
        docFileIds = course.doc_file_ids ? [...course.doc_file_ids] : [];
      }

      // Populate models store (used by ModelSelector) and auto-select model
      modelsStore.set(models);
      if (!modelId && models.length > 0) {
        const defaultModel = models.find(m =>
          (m.name || '').toLowerCase().includes('llama') ||
          (m.id || '').toLowerCase().includes('llama')
        ) || models[0];
        modelId = defaultModel.id;
      }
      // keep selectedModels in sync for the selector
      selectedModels = [modelId || (models[0]?.id ?? '')];
    } catch (e: any) {
      console.error('[CourseEdit] Initialization error:', e);
      error = e?.detail ?? 'Failed to load course data';
    } finally {
      loading = false;
    }
  });

  // File upload handler reused (uploads files and stores ids)
  const onUpload = async (e: Event) => {
    const input = e.target as HTMLInputElement;
    const files = input.files;
    if (!files || !files.length) return;
    uploading = true;
    try {
      const token = await safeToken();
      for (const f of Array.from(files)) {
        const res = await uploadFile(token, f, null);
        if (res?.id) docFileIds.push(res.id);
      }
      docFileIds = [...docFileIds]; // Trigger reactivity
    } catch (e: any) {
      console.error('[CourseEdit] Upload failed', e);
      error = e?.detail ?? 'Upload failed';
    } finally {
      uploading = false;
      if (input) input.value = '';
    }
  };

  const removeFile = (index: number) => {
    docFileIds = docFileIds.filter((_, i) => i !== index);
  };

  $: canProceed = currentStep === 1 ? title.trim() :
                  currentStep === 2 ? docFileIds.length > 0 :
                  currentStep === 3 ? (selectedModels && selectedModels[0]) : false;

  $: disabled = !title.trim() || !selectedModels[0] || docFileIds.length < 1;

  const nextStep = () => {
    if (currentStep < 3) currentStep++;
  };

  const prevStep = () => {
    if (currentStep > 1) currentStep--;
  };

  const onUpdate = async () => {
    updating = true;
    error = null;
    try {
      const token = await safeToken();
      const body = {
        title,
        description,
        code: code || undefined,
        term: term || undefined,
        schedule: schedule || undefined,
        instructors: instructors ? instructors.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        links: links ? links.split(/\r?\n|,\s*/).map((s) => s.trim()).filter(Boolean) : undefined,
        youtube_embeds: youtube ? youtube.split(/\r?\n|,\s*/).map((s) => s.trim()).filter(Boolean) : undefined,
        visibility,
        model_id: selectedModels && selectedModels[0] ? selectedModels[0] : modelId,
        system_prompt,
        temperature,
        max_tokens,
        doc_file_ids: docFileIds
      };
      await updateCourse(token, courseId, body as any);
      await goto(`/classroom/${courseId}/overview`);
    } catch (e: any) {
      console.error('[CourseEdit] Update failed:', e);
      error = e?.detail ?? 'Update failed';
    } finally {
      updating = false;
    }
  };
</script>

{#if loading}
  <section class="space-y-6 max-w-6xl mx-auto p-4">
    <div class="flex items-center space-x-2">
      <svg class="animate-spin h-5 w-5 text-neutral-500" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>
      <span class="text-sm text-neutral-500">Loading course data...</span>
    </div>
  </section>
{:else}
  <section class="max-w-6xl mx-auto p-4" style="font-family: Helvetica, Arial, sans-serif;">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">Edit Course</h1>
        <div class="text-sm text-neutral-500">Update course details, materials and AI assistant configuration.</div>
      </div>
      <div class="flex items-center gap-3">
        <a href={"/classroom/" + courseId + "/overview"} class="text-sm px-3 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500">← Back to Course</a>
        <a href="/classroom" class="text-sm px-3 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500">Classroom</a>
      </div>
    </div>

    <!-- Stepper (thin) -->
    <div class="mb-6">
      <nav class="flex items-center gap-3 text-sm" aria-label="Steps">
        {#each steps as step, i}
          <button
            class="px-3 py-2 rounded-md text-sm font-medium {currentStep === i+1 ? 'bg-blue-600 text-white' : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border border-gray-200 dark:border-gray-700'} focus:outline-none focus:ring-2 focus:ring-blue-500"
            on:click={() => currentStep = i+1}
            aria-current={currentStep === i+1}
          >
            {step.title}
          </button>
        {/each}
      </nav>
    </div>

    <form on:submit|preventDefault={onUpdate} class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main content (2/3) -->
      <div class="lg:col-span-2 space-y-6">
        <div class="p-4 border rounded-md bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-800">
          <h3 class="text-lg font-medium mb-2">{steps[currentStep - 1].title}</h3>
          <p class="text-sm text-neutral-500 mb-4">{steps[currentStep - 1].subtitle}</p>

          {#if currentStep === 1}
            <!-- Step 1: Course Details -->
            <div class="space-y-4">
              <div>
                <label class="text-sm font-medium block mb-1">Course Title *</label>
                <input class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-3 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="e.g., Introduction to Machine Learning" bind:value={title} />
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="text-sm font-medium block mb-1">Course Code</label>
                  <input class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="e.g., CS101" bind:value={code} />
                </div>
                <div>
                  <label class="text-sm font-medium block mb-1">Term</label>
                  <input class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="e.g., Fall 2024" bind:value={term} />
                </div>
              </div>

              <div>
                <label class="text-sm font-medium block mb-1">Description</label>
                <textarea class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-3 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" rows="4" placeholder="Briefly describe what students will learn in this course" bind:value={description}></textarea>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label class="text-sm font-medium block mb-1">Schedule</label>
                  <input class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="e.g., MWF 10-11am" bind:value={schedule} />
                </div>
                <div>
                  <label class="text-sm font-medium block mb-1">Instructors</label>
                  <input class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="Comma-separated names" bind:value={instructors} />
                </div>
              </div>
          </div>
          {:else if currentStep === 2}
            <!-- Step 2: Materials -->
            <div class="space-y-4">
              <div>
                <label class="text-sm font-medium block mb-1">Upload Course Materials *</label>
                <div class="text-xs text-neutral-400 mb-2">PDFs, docs, slides, etc.</div>
                <input type="file" class="w-full" multiple accept=".pdf,.doc,.docx,.txt,.md,.ppt,.pptx" on:change={onUpload} disabled={uploading} />
                <div class="text-xs text-neutral-500 mt-2">{uploading ? 'Uploading...' : `${docFileIds.length} file(s) uploaded`}</div>
              </div>

              {#if docFileIds.length > 0}
                <div class="space-y-2">
                  {#each docFileIds as fileId, i}
                    <div class="flex items-center justify-between bg-white/50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md px-3 py-2 text-sm">
                      <div>File {i + 1} — ID: {fileId}</div>
                      <button class="text-sm text-red-500" on:click={() => removeFile(i)}>Remove</button>
                    </div>
                  {/each}
                </div>
              {/if}

              <div class="text-sm text-neutral-500">
                Upload course materials that the AI assistant will use to answer student questions.
              </div>
            </div>
          {:else}
            <!-- Step 3: AI Assistant Configuration -->
            <div class="space-y-4">
              <div>
                <label class="text-sm font-medium block mb-1">Assigned Model *</label>
                <div class="text-xs text-neutral-400 mt-2">Select the AI model that students will use for this course.</div>
                {#if models.length === 0}
                  <div class="p-3 border border-dashed rounded-md text-sm text-red-500">No models available</div>
                {:else}
                  <div class="mt-2">
                    <ModelSelector bind:selectedModels />
                  </div>
                {/if}
              </div>

              <div>
                <label class="text-sm font-medium block mb-1">System Instructions</label>
                <textarea rows="6" class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-3 focus-visible:outline-2 focus-visible:outline-blue-500 text-sm" placeholder="Define the AI assistant's role, teaching style, and guidelines..." bind:value={system_prompt}></textarea>
                {#if presetTemplate && presetTemplate.system_prompt_md}
                  <div class="mt-2 text-xs">
                    <button type="button" class="text-blue-400 hover:underline" on:click={() => system_prompt = presetTemplate.system_prompt_md}>Use default educational template</button>
                  </div>
                {/if}
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="text-sm font-medium block mb-1">Temperature</label>
                  <div class="flex items-center gap-3">
                    <input type="range" min="0" max="2" step="0.1" bind:value={temperature} class="w-full" />
                    <div class="text-sm font-mono w-10 text-right">{temperature}</div>
                  </div>
                </div>

                <div>
                  <label class="text-sm font-medium block mb-1">Max Tokens</label>
                  <input type="number" min="1" max="128000" step="1" bind:value={max_tokens} class="w-full rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 text-sm" />
                </div>
              </div>

              <div class="text-sm text-neutral-500">
                The AI assistant will use your uploaded course materials to provide contextual answers and help students.
              </div>
            </div>
          {/if}
        </div>
      </div>

      <!-- Right column: materials overview + actions -->
      <div class="space-y-6">
        <div class="p-4 border rounded-md bg-white dark:bg-gray-900 border-gray-100 dark:border-gray-800 space-y-3">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-semibold">Status</div>
              <div class="text-xs text-neutral-400">Draft</div>
            </div>
            <div class="text-sm text-neutral-500">{docFileIds.length} docs</div>
          </div>

          <div>
            <div class="text-sm font-semibold mb-2">Materials</div>
            <div class="text-xs text-neutral-500 mb-2">Upload more files or remove existing ones</div>
            <input type="file" class="w-full" multiple accept=".pdf,.doc,.docx,.txt,.md,.ppt,.pptx" on:change={onUpload} disabled={uploading} />
          </div>

          <div class="flex items-center gap-3 justify-end pt-2">
            <button type="button" class="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-700 text-sm" on:click={() => { currentStep = 1; }}>Edit Details</button>
            <button type="button" class="px-3 py-2 rounded-md bg-blue-600 text-white text-sm" disabled={disabled || uploading || updating} on:click={onUpdate}>
              {#if updating}
                Updating…
              {:else}
                Update Course
              {/if}
            </button>
          </div>
        </div>

        {#if error}
          <div class="p-3 text-sm text-red-500">{error}</div>
        {/if}
      </div>
    </form>
  </section>
{/if}

<style>
  /* keep a compact clamp utility if needed by other components */
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
