<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getCourse } from '$lib/apis/classroom';
  import { listMaterials } from '$lib/apis/classroom';

  $: courseId = $page.params.courseId;

  let loading = true;
  let error: string | null = null;

  let course: any = null;
  let kbFiles: any[] = [];     // files coming from course knowledge
  let apiMaterials: any[] = []; // optional separate materials list

  $: items = normalizeFiles(kbFiles, apiMaterials);

  function normalizeFiles(kb: any[], mats: any[]) {
    const out: any[] = [];
    if (kb?.length) {
      for (const f of kb) {
        out.push({
          id: f.id,
          name: f.name || f.filename || `file-${f.id}`,
          kind: f.kind || f.mime || f.mimetype || 'file',
          size: f.size || f.bytes || null,
          url: f.url || f.download_url || null,
          source: 'knowledge'
        });
      }
    }
    if (mats?.length) {
      for (const m of mats) {
        out.push({
          id: m.id,
          name: m.title || m.name || `material-${m.id}`,
          kind: m.kind || 'material',
          size: m.size || null,
          url: m.url || null,
          source: 'materials'
        });
      }
    }
    return out;
  }

  function formatBytes(n?: number | null) {
    if (!n || n <= 0) return '';
    const k = 1024, units = ['B','KB','MB','GB','TB'];
    const i = Math.floor(Math.log(n) / Math.log(k));
    return `${(n / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
  }

  onMount(async () => {
    loading = true; error = null;
    try {
      const token = typeof window !== 'undefined' ? (localStorage.token || '') : '';
      const [courseRes, matsRes] = await Promise.all([
        getCourse(token, courseId),
        typeof listMaterials === 'function' ? listMaterials(token, courseId) : Promise.resolve([])
      ]);

      course = courseRes?.course ?? courseRes;

      // Prefer server-provided knowledge files; fallbacks if your API uses different fields
      kbFiles =
          courseRes?.knowledge_files ??
          course?.knowledge_files ??
          course?.documents ?? [];

      apiMaterials = matsRes ?? [];
    } catch (e: any) {
      error = e?.detail || e?.message || 'Failed to load materials';
    } finally {
      loading = false;
    }
  });
</script>

<section class="space-y-3">
  <h1 class="text-xl font-semibold">Materials</h1>

  {#if loading}
    <p class="text-sm text-neutral-500">Loading…</p>
  {:else if error}
    <p class="text-sm text-red-500">{error}</p>
  {:else if !items?.length}
    <div class="rounded-md border border-neutral-200 dark:border-neutral-800 p-6 text-sm text-neutral-600 dark:text-neutral-400">
      No materials yet.
    </div>
  {:else}
    <ul class="space-y-2">
      {#each items as f}
        <li class="rounded-md border border-neutral-200 dark:border-neutral-800 p-3 flex items-center justify-between gap-3">
          <div class="min-w-0">
            <div class="text-sm font-medium truncate">
              {#if f.url}
                <a class="hover:underline" href={f.url} target="_blank" rel="noreferrer">{f.name}</a>
              {:else}
                {f.name}
              {/if}
            </div>
            <div class="text-xs text-neutral-500">
              {f.kind}{formatBytes(f.size) ? ` • ${formatBytes(f.size)}` : ''}{f.source ? ` • ${f.source}` : ''}
            </div>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
