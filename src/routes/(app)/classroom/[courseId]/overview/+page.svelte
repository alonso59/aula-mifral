<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { getCourse } from '$lib/apis/classroom';
  import { user } from '$lib/stores';

  $: courseId = $page.params.courseId;

  let loading = true;
  let error: string | null = null;
  let course: any = null;
  let preset: any = null;
  let kbFiles: any[] = [];

  onMount(async () => {
    loading = true;
    error = null;
    try {
      const token = typeof window !== 'undefined' ? localStorage.token : '';
      const res = await getCourse(token, courseId);
      course  = res?.course ?? res;
      preset  = res?.preset ?? res?.course?.preset ?? null;
      kbFiles = res?.knowledge_files ?? [];
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load course';
    } finally {
      loading = false;
    }
  });
</script>

<section class="space-y-3">
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold">Overview</h1>
    {#if $user && ['admin','teacher'].includes($user.role) && course}
      <a
        href={`/classroom/courses/${courseId}/edit`}
        class="btn btn-outline btn-sm"
      >
        Edit Course
      </a>
    {/if}
  </div>

  {#if loading}
    <p class="text-sm text-neutral-500">Loading…</p>
  {:else if error}
    <p class="text-sm text-red-500">{error}</p>
  {:else if !course}
    <p class="text-sm text-neutral-600 dark:text-neutral-400">Course not found.</p>
  {:else}
    <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-4 space-y-3">
      <div>
        <div class="text-lg font-medium">{course.title}</div>
        {#if course.description}
          <div class="text-sm text-neutral-600 dark:text-neutral-400">{course.description}</div>
        {/if}
      </div>

      {#if course.meta_json}
        <div class="grid grid-cols-2 gap-3 text-sm">
          {#if course.meta_json.code}<div><span class="text-neutral-500">Code:</span> {course.meta_json.code}</div>{/if}
          {#if course.meta_json.term}<div><span class="text-neutral-500">Term:</span> {course.meta_json.term}</div>{/if}
          {#if course.meta_json.schedule}<div class="col-span-2"><span class="text-neutral-500">Schedule:</span> {course.meta_json.schedule}</div>{/if}
          {#if course.meta_json.instructors?.length}<div class="col-span-2"><span class="text-neutral-500">Instructors:</span> {course.meta_json.instructors.join(', ')}</div>{/if}
          {#if course.meta_json.links?.length}
            <div class="col-span-2 flex gap-2 flex-wrap">
              <span class="text-neutral-500">Links:</span>
              {#each course.meta_json.links as link}
                <a class="link" href={link} target="_blank" rel="noreferrer">{link}</a>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      {#if course.meta_json?.youtube_embeds?.length}
        <div class="space-y-2">
          <div class="text-sm font-medium">Videos</div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            {#each course.meta_json.youtube_embeds as url}
              <iframe class="w-full aspect-video rounded"
                      src={url}
                      title="Course video"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowfullscreen />
            {/each}
          </div>
        </div>
      {/if}

      {#if preset}
        <div class="text-sm">
          <span class="text-neutral-500">Model:</span>
          <span class="ml-1">{preset.model_id || preset.name || 'N/A'}</span>
          {#if preset.temperature != null}<span class="ml-2 text-neutral-500">Temp {preset.temperature}</span>{/if}
          {#if preset.max_tokens}<span class="ml-2 text-neutral-500">Max {preset.max_tokens}</span>{/if}
        </div>
      {/if}

      <div class="space-y-2">
        <div class="text-sm font-medium">Knowledge Base Files</div>
        {#if kbFiles?.length}
          <ul class="list-disc pl-5 text-sm">
            {#each kbFiles as f}
              <li>{f.name || f.filename || f.id}</li>
            {/each}
          </ul>
        {:else}
          <div class="text-sm text-neutral-500">No files indexed yet.</div>
        {/if}
      </div>
    </div>
  {/if}
</section>
