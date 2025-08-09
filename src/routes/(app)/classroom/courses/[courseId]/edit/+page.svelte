<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getModels } from '$lib/apis';
  import { uploadFile } from '$lib/apis/files';
  import { getCourse, updateCourse, getCoursePresetTemplate } from '$lib/apis/classroom';
  import { user } from '$lib/stores';

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
  let visibility: 'private' | 'org' | 'public' = 'private';

  // Model Configuration
  let modelId = '';
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

  onMount(async () => {
    if ($user && $user.role && !['admin','teacher'].includes($user.role)) {
      await goto('/classroom');
      return;
    }
    try {
      // Load models, course data, and preset template in parallel
      const [modelsRes, courseRes, templateRes] = await Promise.all([
        getModels(localStorage.token),
        getCourse(localStorage.token, courseId),
        getCoursePresetTemplate(localStorage.token, courseId)
      ]);
      
      models = modelsRes;
      course = courseRes;
      presetTemplate = templateRes;
      
      // Pre-fill form with existing course data
      if (course) {
        title = course.title || '';
        code = course.code || '';
        description = course.description || '';
        term = course.term || '';
        schedule = course.schedule || '';
        instructors = course.instructors ? course.instructors.join(', ') : '';
        links = course.links ? course.links.join(', ') : '';
        youtube = course.youtube_embeds ? course.youtube_embeds.join(', ') : '';
        visibility = course.visibility || 'private';
        modelId = course.model_id || '';
        system_prompt = course.system_prompt || '';
        temperature = course.temperature || 0.4;
        max_tokens = course.max_tokens || 1024;
        docFileIds = course.doc_file_ids || [];
      }
      
      // Auto-select model if not set
      if (!modelId && models.length > 0) {
        const defaultModel = models.find(m => 
          m.name?.toLowerCase().includes('llama') || 
          m.id?.toLowerCase().includes('llama')
        ) || models[0];
        modelId = defaultModel.id;
      }
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load course data';
    } finally {
      loading = false;
    }
  });

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
                  currentStep === 2 ? docFileIds.length > 0 : 
                  currentStep === 3 ? modelId : false;

  $: disabled = !title.trim() || !modelId || docFileIds.length < 1;

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
        model_id: modelId,
        system_prompt,
        temperature,
        max_tokens,
        doc_file_ids: docFileIds
      };
      await updateCourse(localStorage.token, courseId, body as any);
      await goto(`/classroom/${courseId}/overview`);
    } catch (e: any) {
      error = e?.detail ?? 'Update failed';
    } finally {
      updating = false;
    }
  };
</script>

{#if loading}
  <section class="space-y-6 max-w-4xl">
    <div class="flex items-center space-x-2">
      <span class="loading loading-spinner loading-sm"></span>
      <span>Loading course data...</span>
    </div>
  </section>
{:else}
  <section class="space-y-6 max-w-4xl">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Edit Course</h1>
      <div class="flex space-x-2">
        <a href="/classroom/{courseId}/overview" class="btn btn-ghost btn-sm">← Back to Course</a>
        <a href="/classroom" class="btn btn-ghost btn-sm">Classroom</a>
      </div>
    </div>

    {#if $user && !['admin','teacher'].includes($user.role)}
      <div class="alert alert-warning">
        <div class="text-sm">You don't have permission to edit courses.</div>
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
        <!-- Step 2: Learning Materials -->
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
              <div class="text-sm font-medium mb-2">Course Materials:</div>
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

      {:else if currentStep === 3}
        <!-- Step 3: AI Assistant Configuration -->
        <div class="space-y-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text font-medium">AI Model *</span>
            </label>
            <select class="select select-bordered w-full" bind:value={modelId}>
              <option value="">Select a model…</option>
              {#each models as m}
                <option value={m.id}>{m.name || m.id}</option>
              {/each}
            </select>
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
              The AI assistant will use your uploaded course materials to provide contextual answers 
              and help students understand the content better.
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
            disabled={disabled || uploading || updating} 
            on:click={onUpdate}
          >
            {#if updating}
              <span class="loading loading-spinner loading-sm"></span>
              Updating Course...
            {:else}
              Update Course
            {/if}
          </button>
        {/if}
      </div>
    </div>

    {/if}
  </section>
{/if}
