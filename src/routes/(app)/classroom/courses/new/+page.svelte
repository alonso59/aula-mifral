<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { getModels } from '$lib/apis';
  import { uploadFile } from '$lib/apis/files';
  import { createCourse, getCoursePresetTemplate } from '$lib/apis/classroom';
  import { user, config, settings, models } from '$lib/stores';
  import ModelSelector from '$lib/components/chat/ModelSelector.svelte';

  // Course Basic Info
  let title = '';
  let code = '';
  let description = '';
  let term = '';
  let schedule = '';
  let instructors = '';
  let links = '';
  let youtube = '';
  let visibility: 'private' | 'org' | 'public' = 'private';

  // Model Configuration
  let selectedModels = [''];
  let system_prompt = '';
  let temperature: number = 0.4;
  let max_tokens: number = 1024;

  // UI State
  let uploading = false;
  let creating = false;
  let error: string | null = null;
  let docFileIds: string[] = [];
  let currentStep = 1;
  let presetTemplate: any = null;

  const steps = [
    { title: 'Course Details', subtitle: 'Basic information about your course' },
    { title: 'AI Assistant', subtitle: 'Configure how students interact with content' },
    { title: 'Learning Materials', subtitle: 'Upload documents for the AI assistant' }
  ];

  let modelsLoading = true;

  // Load models using exact same method as chat interface
  const loadModels = async () => {
    try {
      modelsLoading = true;
      console.log('[CourseCreate] Loading models...');
      
      // Use exact same call as chat interface with direct connections
      const modelsRes = await getModels(
        localStorage.token,
        $config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
      );
      
      console.log('[CourseCreate] Loaded models:', modelsRes);
      
      // Set in global store (same as chat interface)
      models.set(modelsRes);
      
      // Find Docker model for debugging
      const dockerModel = modelsRes.find(m => m.id === 'ai/smollm2:latest');
      if (dockerModel) {
        console.log('[CourseCreate] Found Docker model:', dockerModel);
      } else {
        console.warn('[CourseCreate] Docker model ai/smollm2:latest not found in models list');
        console.log('[CourseCreate] Available model IDs:', modelsRes.map(m => m.id));
      }
      
    } catch (error) {
      console.error('[CourseCreate] Failed to load models:', error);
      error = 'Failed to load available models';
    } finally {
      modelsLoading = false;
    }
  };

  // Reactive loading when config/settings become available
  $: if ($config && $settings && modelsLoading) {
    loadModels();
  }

  onMount(async () => {
    if ($user && $user.role && !['admin','teacher'].includes($user.role)) {
      await goto('/classroom');
      return;
    }
    try {
      // Load preset template
      presetTemplate = await getCoursePresetTemplate(localStorage.token, 'new');
      
      // Initial model load if config/settings already available
      if ($config && $settings) {
        await loadModels();
      }
      
      // Pre-fill with smart defaults from template
      if (presetTemplate) {
        system_prompt = presetTemplate.system_prompt_md || '';
        temperature = presetTemplate.temperature || 0.4;
        max_tokens = presetTemplate.max_tokens || 1024;
      }
      
      // Auto-select a suitable model when models are available
      if ($models.length > 0) {
        const defaultModel = $models.find(m =>
          m.id === 'ai/smollm2:latest' ||
          m.name?.toLowerCase().includes('smollm') ||
          m.id?.toLowerCase().includes('smollm') ||
          m.name?.toLowerCase().includes('llama') ||
          m.id?.toLowerCase().includes('llama')
        ) || $models[0];
        selectedModels = [defaultModel.id];
        console.log('[CourseCreate] Auto-selected model:', defaultModel.id);
      }
      
    } catch (e: any) {
      console.error('[CourseCreate] Initialization error:', e);
      error = e?.detail ?? 'Failed to load initialization data';
    }
  });

  // Auto-select model when models become available
  $: if ($models.length > 0 && (!selectedModels[0] || selectedModels[0] === '')) {
    const defaultModel = $models.find(m =>
      m.id === 'ai/smollm2:latest' ||
      m.name?.toLowerCase().includes('smollm') ||
      m.id?.toLowerCase().includes('smollm') ||
      m.name?.toLowerCase().includes('llama') ||
      m.id?.toLowerCase().includes('llama')
    ) || $models[0];
    selectedModels = [defaultModel.id];
    console.log('[CourseCreate] Auto-selected model on store update:', defaultModel.id);
  }

  const onUpload = async (e: Event) => {
    const input = e.target as HTMLInputElement;
    const files = input.files;
    if (!files || !files.length) return;
    uploading = true;
    try {
      for (const f of Array.from(files)) {
        const res = await uploadFile(localStorage.token, f, null);
        if (res?.id) docFileIds.push(res.id);
      }
      docFileIds = [...docFileIds]; // Trigger reactivity
    } catch (e: any) {
      error = e?.detail ?? 'Upload failed';
    } finally {
      uploading = false;
      (e.target as HTMLInputElement).value = '';
    }
  };

  const removeFile = (index: number) => {
    docFileIds = docFileIds.filter((_, i) => i !== index);
  };

  $: canProceed = currentStep === 1 ? title.trim() : 
                  currentStep === 2 ? (selectedModels.length > 0 && selectedModels[0]) : 
                  currentStep === 3 ? docFileIds.length > 0 : false;

  $: disabled = !title.trim() || !selectedModels[0] || docFileIds.length < 1 || modelsLoading;

  const nextStep = () => {
    if (currentStep < 3) currentStep++;
  };

  const prevStep = () => {
    if (currentStep > 1) currentStep--;
  };

  const onCreate = async () => {
    creating = true;
    error = null;
    
    try {
      // Validate model selection
      const selectedModel = selectedModels[0];
      if (!selectedModel || selectedModel === '') {
        error = 'Please select a model for the AI assistant';
        return;
      }
      
      console.log('[CourseCreate] Creating course with model:', selectedModel);
      console.log('[CourseCreate] Available models:', $models.map(m => m.id));
      
      // Validate required fields
      if (!title.trim()) {
        error = 'Course title is required';
        return;
      }
      
      if (docFileIds.length < 1) {
        error = 'At least one document is required';
        return;
      }
      
      const body = {
        title,
        description,
        code: code || undefined,
        term: term || undefined,
        schedule: schedule || undefined,
        instructors: instructors ? instructors.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        links: links ? links.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        youtube_embeds: youtube ? youtube.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        visibility,
        model_id: selectedModel,
        system_prompt,
        temperature,
        max_tokens,
        doc_file_ids: docFileIds
      };
      
      console.log('[CourseCreate] Submitting course data:', body);
      
      const created = await createCourse(localStorage.token, body as any);
      
      console.log('[CourseCreate] Course created successfully:', created);
      
      // Redirect to course chat for immediate interaction
      await goto(`/classroom/${created.id}/chat`);
      
    } catch (e: any) {
      console.error('[CourseCreate] Creation failed:', e);
      error = e?.detail ?? 'Failed to create course';
    } finally {
      creating = false;
    }
  };
</script>

<section class="space-y-6 max-w-4xl">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-semibold">Create New Course</h1>
    <a href="/classroom" class="btn btn-ghost btn-sm">← Back to Classroom</a>
  </div>

  {#if $user && !['admin','teacher'].includes($user.role)}
    <div class="alert alert-warning">
      <div class="text-sm">You don't have permission to create courses.</div>
    </div>
  {:else}

  <!-- Progress Steps -->
  <div class="steps steps-horizontal w-full">
    {#each steps as step, i}
      <div class="step" class:step-primary={currentStep > i + 1} class:step-accent={currentStep === i + 1}>
        {step.title}
      </div>
    {/each}
  </div>

  {#if error}
    <div class="alert alert-error">
      <div class="text-sm">{error}</div>
    </div>
  {/if}

  <div class="bg-base-200 rounded-lg p-6">
    <div class="mb-4">
      <h3 class="text-lg font-medium">{steps[currentStep - 1].title}</h3>
      <p class="text-sm opacity-70">{steps[currentStep - 1].subtitle}</p>
    </div>

    {#if currentStep === 1}
      <!-- Step 1: Course Details -->
      <div class="space-y-4">
        <div class="form-control">
          <label class="label">
            <span class="label-text font-medium">Course Title *</span>
          </label>
          <input 
            class="input input-bordered w-full" 
            placeholder="e.g., Introduction to Machine Learning" 
            bind:value={title} 
          />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">Course Code</span>
            </label>
            <input 
              class="input input-bordered w-full" 
              placeholder="e.g., CS101" 
              bind:value={code} 
            />
          </div>
          <div class="form-control">
            <label class="label">
              <span class="label-text">Term</span>
            </label>
            <input 
              class="input input-bordered w-full" 
              placeholder="e.g., Fall 2024" 
              bind:value={term} 
            />
          </div>
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text">Description</span>
          </label>
          <textarea 
            class="textarea textarea-bordered w-full" 
            rows="3" 
            placeholder="Briefly describe what students will learn in this course" 
            bind:value={description} 
          />
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">Schedule</span>
            </label>
            <input 
              class="input input-bordered w-full" 
              placeholder="e.g., MWF 10-11am" 
              bind:value={schedule} 
            />
          </div>
          <div class="form-control">
            <label class="label">
              <span class="label-text">Visibility</span>
            </label>
            <select class="select select-bordered w-full" bind:value={visibility}>
              <option value="private">Private</option>
              <option value="org">Organization</option>
              <option value="public">Public</option>
            </select>
          </div>
          <div class="form-control">
            <label class="label">
              <span class="label-text">Instructors</span>
            </label>
            <input 
              class="input input-bordered w-full" 
              placeholder="Comma-separated names" 
              bind:value={instructors} 
            />
          </div>
        </div>

        <details class="collapse collapse-arrow bg-base-100">
          <summary class="collapse-title text-sm font-medium">Additional Resources (Optional)</summary>
          <div class="collapse-content space-y-3">
            <div class="form-control">
              <label class="label">
                <span class="label-text">Course Links</span>
              </label>
              <input 
                class="input input-bordered w-full" 
                placeholder="Comma-separated URLs" 
                bind:value={links} 
              />
            </div>
            <div class="form-control">
              <label class="label">
                <span class="label-text">YouTube Videos</span>
              </label>
              <input 
                class="input input-bordered w-full" 
                placeholder="Comma-separated YouTube URLs" 
                bind:value={youtube} 
              />
            </div>
          </div>
        </details>
      </div>

    {:else if currentStep === 2}
      <!-- Step 2: AI Assistant Configuration -->
      <div class="space-y-4">
        <div class="form-control">
          <label class="label">
            <span class="label-text font-medium">AI Model *</span>
          </label>
          {#if modelsLoading}
            <div class="p-4 border border-dashed rounded-lg text-center text-gray-500">
              <div class="loading loading-spinner loading-sm mr-2"></div>
              Loading available models...
            </div>
          {:else if $models.length === 0}
            <div class="p-4 border border-dashed rounded-lg text-center text-red-500">
              <div class="font-medium">No models available</div>
              <div class="text-sm mt-1">Please contact your administrator or check server configuration</div>
            </div>
          {:else}
            <div class="w-full">
              <!-- Unified ModelSelector for model selection -->
              <ModelSelector bind:selectedModels={selectedModels} disabled={creating} showSetDefault={false} />
              <div class="text-xs text-gray-400 mt-2">
                Debug: {$models.length} models loaded | Selected: {selectedModels[0] || 'none'}
              </div>
            </div>
          {/if}
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text font-medium">System Instructions</span>
            <span class="label-text-alt">How should the AI assistant behave?</span>
          </label>
          <textarea 
            class="textarea textarea-bordered w-full" 
            rows="6" 
            placeholder="Define the AI assistant's role, teaching style, and guidelines..."
            bind:value={system_prompt} 
          />
          {#if presetTemplate && presetTemplate.system_prompt_md}
            <div class="label">
              <button 
                class="label-text-alt link" 
                on:click={() => system_prompt = presetTemplate.system_prompt_md}
              >
                Use default educational template
              </button>
            </div>
          {/if}
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">Temperature</span>
              <span class="label-text-alt">Creativity (0-2)</span>
            </label>
            <div class="flex items-center space-x-3">
              <input 
                type="range" 
                min="0" 
                max="2" 
                step="0.1" 
                class="range range-sm" 
                bind:value={temperature} 
              />
              <span class="text-sm font-mono w-8">{temperature}</span>
            </div>
            <div class="label">
              <span class="label-text-alt">Lower = more focused, Higher = more creative</span>
            </div>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">Max Tokens</span>
              <span class="label-text-alt">Response length</span>
            </label>
            <input 
              class="input input-bordered w-full" 
              type="number" 
              min="1" 
              max="128000" 
              step="1" 
              bind:value={max_tokens} 
            />
          </div>
        </div>

        <div class="alert alert-success">
          <div class="text-sm">
            The AI assistant will use course materials to provide contextual answers 
            and help students understand the content better.
          </div>
        </div>
      </div>

    {:else if currentStep === 3}
      <!-- Step 3: Learning Materials -->
      <div class="space-y-4">
        <div class="form-control">
          <label class="label">
            <span class="label-text font-medium">Upload Course Materials *</span>
            <span class="label-text-alt">PDFs, docs, slides, etc.</span>
          </label>
          <input 
            type="file" 
            class="file-input file-input-bordered w-full" 
            multiple 
            accept=".pdf,.doc,.docx,.txt,.md,.ppt,.pptx" 
            on:change={onUpload} 
            disabled={uploading}
          />
          <div class="label">
            <span class="label-text-alt">
              {#if uploading}
                Uploading...
              {:else}
                {docFileIds.length} file(s) uploaded
              {/if}
            </span>
          </div>
        </div>

        {#if docFileIds.length > 0}
          <div class="bg-base-100 rounded-lg p-4">
            <div class="text-sm font-medium mb-2">Uploaded Files:</div>
            <div class="space-y-2">
              {#each docFileIds as fileId, i}
                <div class="flex items-center justify-between bg-base-200 rounded px-3 py-2">
                  <span class="text-sm">File {i + 1}</span>
                  <button 
                    class="btn btn-ghost btn-xs text-error" 
                    on:click={() => removeFile(i)}
                  >
                    Remove
                  </button>
                  </div>
              {/each}
            </div>
          </div>
        {/if}

        <div class="alert alert-info">
          <div class="text-sm">
            Upload course materials that the AI assistant will use to answer student questions. 
            The more relevant content you provide, the better the assistant will perform.
          </div>
        </div>
      </div>

  {/if}
  </div>

  <!-- Navigation Buttons -->
  <div class="flex justify-between items-center pt-4">
    <div>
      {#if currentStep > 1}
        <button class="btn btn-outline" on:click={prevStep}>
          ← Previous
        </button>
      {/if}
    </div>

    <div class="flex items-center space-x-2">
      {#if currentStep < 3}
        <button 
          class="btn btn-primary" 
          disabled={!canProceed} 
          on:click={nextStep}
        >
          Next →
        </button>
      {:else}
        <button 
          class="btn btn-primary" 
          disabled={disabled || uploading || creating || modelsLoading} 
          on:click={onCreate}
        >
          {#if creating}
            <span class="loading loading-spinner loading-sm"></span>
            Creating Course...
          {:else if modelsLoading}
            <span class="loading loading-spinner loading-sm"></span>
            Loading Models...
          {:else}
            Create Course
          {/if}
        </button>
      {/if}
    </div>
  </div>

  {/if}
</section>
