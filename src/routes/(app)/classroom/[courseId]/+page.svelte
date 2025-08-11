<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { user } from '$lib/stores';
  import CourseChat from '$lib/components/chat/CourseChat.svelte';
  import { getCourse } from '$lib/apis/classroom';

  $: courseId = $page.params.courseId;

  // Local nav state
  const navItems: { id: string; label: string; subtitle: string; icon: string }[] = [
    { id: 'overview', label: 'Course Overview', subtitle: 'Summary and details', icon: 'home' },
    { id: 'materials', label: 'Course Materials', subtitle: 'Documents & KB', icon: 'doc' },
    { id: 'topics', label: 'Learning Topics', subtitle: 'Key concepts', icon: 'book' },
    { id: 'tasks', label: 'Tasks & Assignments', subtitle: 'Work and due dates', icon: 'tasks' },
    { id: 'videos', label: 'Course Videos', subtitle: 'YouTube only', icon: 'video' }
  ];
  let active = 'overview';
  let sidebarOpen = false;

  // Data
  let loading = true;
  let error: string | null = null;
  let course: any = null;
  let preset: any = null;
  let kbFiles: any[] = [];

  const isTeacherOrAdmin = () => $user && ['admin', 'teacher'].includes($user.role);
  const isActive = () => course?.status === 'active';

  const icon = (name: string) => {
    // Minimal inline icons to avoid new deps
    if (name === 'home') return `<svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M10 3l7 6v8a1 1 0 0 1-1 1h-4v-5H8v5H4a1 1 0 0 1-1-1V9l7-6z"/></svg>`;
    if (name === 'doc') return `<svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M6 2h5l5 5v11a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm6 6h4l-4-4v4z"/></svg>`;
    if (name === 'book') return `<svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M3 4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v12a1 1 0 0 1-1 1H6a3 3 0 0 0-3 3V4z"/></svg>`;
    if (name === 'tasks') return `<svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M7 4h10v2H7V4zm0 5h10v2H7V9zm0 5h10v2H7v-2zM3 5h2v2H3V5zm0 5h2v2H3v-2zm0 5h2v2H3v-2z"/></svg>`;
    if (name === 'video') return `<svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M2 5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2l4-2v10l-4-2v2a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5z"/></svg>`;
    if (name === 'lock') return `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><path d="M10 2a4 4 0 0 1 4 4v2h1a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1h1V6a4 4 0 0 1 4-4zm2 6V6a2 2 0 1 0-4 0v2h4z"/></svg>`;
    return '';
  };

  function whitelistYouTube(url: string): string | null {
    try {
      const u = new URL(url);
      const host = u.hostname.toLowerCase();
      const allowed = ['www.youtube.com', 'youtube.com', 'youtu.be', 'www.youtu.be', 'www.youtube-nocookie.com', 'youtube-nocookie.com'];
      if (!allowed.includes(host)) return null;
      // Normalize to youtube-nocookie when possible
      if (host.includes('youtu.be')) {
        const id = u.pathname.slice(1);
        return id ? `https://www.youtube-nocookie.com/embed/${id}` : null;
      }
      if (host.includes('youtube')) {
        const id = u.searchParams.get('v');
        if (id) return `https://www.youtube-nocookie.com/embed/${id}`;
        // Fallback to original if already embed
        if (u.pathname.startsWith('/embed/')) return `https://www.youtube-nocookie.com${u.pathname}`;
      }
      return url;
    } catch {
      return null;
    }
  }

  onMount(async () => {
    loading = true;
    error = null;
    try {
      const res = await getCourse(localStorage.token, courseId);
      course = res?.course ?? res;
      preset = res?.preset ?? res?.course?.preset ?? null;
      kbFiles = res?.knowledge_files ?? [];
    } catch (e: any) {
      error = e?.detail ?? 'Failed to load course';
    } finally {
      loading = false;
    }
  });

  function onKeyNav(e: KeyboardEvent) {
    const idx = navItems.findIndex((n) => n.id === active);
    if (e.key === 'ArrowDown') {
      const next = navItems[Math.min(navItems.length - 1, idx + 1)];
      if (next) active = next.id;
    } else if (e.key === 'ArrowUp') {
      const prev = navItems[Math.max(0, idx - 1)];
      if (prev) active = prev.id;
    } else if (e.key === 'Enter') {
      // no-op, already selected
    }
  }
</script>

<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4">
  <div class="grid grid-cols-1 md:grid-cols-[20rem,1fr] gap-4">
    <!-- Left: Virtual Classroom -->
    <aside class="md:sticky md:top-4 h-max border border-neutral-200 dark:border-neutral-800 rounded-lg">
      <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-800">
        <div class="flex items-center gap-2">
          <span class="inline-block" aria-hidden="true">{@html icon('home')}</span>
          <h2 class="text-sm font-semibold">Virtual Classroom</h2>
        </div>
        <button class="md:hidden btn btn-ghost btn-xs" on:click={() => (sidebarOpen = !sidebarOpen)} aria-label={sidebarOpen ? 'Collapse' : 'Expand'}>
          ☰
        </button>
      </div>
      <nav role="navigation" aria-label="Classroom Sections" class="{sidebarOpen ? 'block' : 'hidden'} md:block">
        <ul class="py-2" on:keydown={onKeyNav}>
          {#each navItems as item}
            <li>
              <button
                class="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-neutral-100 dark:hover:bg-neutral-900 aria-[current=page]:bg-neutral-100 dark:aria-[current=page]:bg-neutral-900"
                aria-current={active === item.id ? 'page' : undefined}
                on:click={() => (active = item.id)}
              >
                <span class="mt-0.5 text-neutral-500" aria-hidden="true">{@html icon(item.icon)}</span>
                <span>
                  <div class="text-sm font-medium">{item.label}</div>
                  <div class="text-xs text-neutral-500">{item.subtitle}</div>
                </span>
              </button>
            </li>
          {/each}
        </ul>
      </nav>

      <!-- RBAC actions -->
      <div class="px-4 py-3 border-t border-neutral-200 dark:border-neutral-800 text-sm">
        {#if isTeacherOrAdmin()}
          <div class="flex flex-wrap gap-2">
            {#if !isActive()}
              <a class="btn btn-primary btn-xs" href="/classroom/{courseId}/settings">Activate Class</a>
            {/if}
            <a class="btn btn-outline btn-xs" href="/classroom/{courseId}/materials">Manage Materials</a>
            <a class="btn btn-outline btn-xs" href="/classroom/{courseId}/settings">Edit Course</a>
          </div>
        {:else}
          <div class="text-neutral-500">Read-only access</div>
        {/if}
      </div>
    </aside>

    <!-- Right: Content + Chat panel -->
    <section class="flex flex-col gap-4 min-h-[70vh]">
      <div class="rounded-lg border border-neutral-200 dark:border-neutral-800 p-4">
        {#if loading}
          <div class="text-sm text-neutral-500">Loading…</div>
        {:else if error}
          <div class="text-sm text-red-500">{error}</div>
        {:else}
          {#if !isActive()}
            <div class="flex items-center justify-center py-16">
              <div class="text-center max-w-md">
                <div class="mx-auto mb-3 w-10 h-10 text-neutral-500">{@html icon('lock')}</div>
                <div class="text-base font-semibold">Class Not Active</div>
                <div class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">This class hasn’t been activated yet.</div>
                {#if isTeacherOrAdmin()}
                  <a class="btn btn-primary btn-sm mt-3" href="/classroom/{courseId}/settings">Activate Class</a>
                {/if}
              </div>
            </div>
          {:else}
            {#if active === 'overview'}
              <div class="space-y-2">
                <div class="text-base font-semibold">{course?.title}</div>
                {#if course?.description}
                  <div class="text-sm text-neutral-600 dark:text-neutral-400">{course.description}</div>
                {/if}
                <div class="grid grid-cols-2 gap-3 text-sm">
                  {#if course?.meta_json?.code}
                    <div><span class="text-neutral-500">Code:</span> {course.meta_json.code}</div>
                  {/if}
                  {#if course?.meta_json?.term}
                    <div><span class="text-neutral-500">Term:</span> {course.meta_json.term}</div>
                  {/if}
                  {#if course?.meta_json?.schedule}
                    <div class="col-span-2"><span class="text-neutral-500">Schedule:</span> {course.meta_json.schedule}</div>
                  {/if}
                </div>
              </div>
            {/if}

            {#if active === 'materials'}
              <div class="space-y-2">
                <div class="text-base font-semibold">Materials</div>
                {#if kbFiles?.length}
                  <ul class="list-disc pl-5 text-sm">
                    {#each kbFiles as f}
                      <li>{f.name || f.filename || f.id}</li>
                    {/each}
                  </ul>
                {:else}
                  <div class="rounded-lg border border-dashed border-neutral-300 dark:border-neutral-700 p-6 text-center text-neutral-500">No materials yet.</div>
                {/if}
              </div>
            {/if}

            {#if active === 'topics'}
              <div class="rounded-lg border border-dashed border-neutral-300 dark:border-neutral-700 p-6 text-center text-neutral-500">No topics yet.</div>
            {/if}

            {#if active === 'tasks'}
              <div class="rounded-lg border border-dashed border-neutral-300 dark:border-neutral-700 p-6 text-center text-neutral-500">No assignments yet.</div>
            {/if}

            {#if active === 'videos'}
              <div class="space-y-2">
                <div class="text-base font-semibold">Videos</div>
                {#if course?.meta_json?.youtube_embeds?.length}
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {#each course.meta_json.youtube_embeds as url}
                      {#if whitelistYouTube(url)}
                        <iframe class="w-full aspect-video rounded" src={whitelistYouTube(url)} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen title="Course video"></iframe>
                      {:else}
                        <div class="text-sm text-red-500">Invalid video host. Only YouTube is allowed.</div>
                      {/if}
                    {/each}
                  </div>
                {:else}
                  <div class="rounded-lg border border-dashed border-neutral-300 dark:border-neutral-700 p-6 text-center text-neutral-500">No videos added.</div>
                {/if}
              </div>
            {/if}
          {/if}
        {/if}
      </div>

      <!-- Chat panel stays functional -->
      <div class="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3">
        <CourseChat {courseId} />
      </div>
    </section>
  </div>
</div>
