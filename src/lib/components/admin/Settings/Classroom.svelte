<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { user, settings } from '$lib/stores';
  import { config } from '$lib/stores';
  import { classroomEnabled, classroomEmbedInChat } from '$lib/stores/classroom';
  import { getClassroomToggle, listCourses, createCourse, getCourse, updateCourse } from '$lib/apis/classroom';
  import { uploadFile } from '$lib/apis/files';
  // svelte-sonner will be dynamically imported on mount to avoid missing package errors
  import { fetchAllModels } from '$lib/apis/models/fetchAllModels';
  import type { AggregatedModel } from '$lib/apis/models/fetchAllModels';

  import { get } from 'svelte/store';

  let toast: any;

  // Feature toggle state
  let enabled = false;
  let embedPref = false;
  let loading = true;
  let saving = false;

  // View state: 'list' | 'create' | { edit: string }
  type ViewState = 'list' | 'create' | { edit: string };
  let view: ViewState = 'list';

  // Courses
  let courses: any[] = [];
  let coursesLoading = false;
  let courseFilter: 'all' | 'active' | 'draft' | 'archived' = 'all';
  function setCourseFilter(f: string){ courseFilter = f as 'all' | 'active' | 'draft' | 'archived'; }

  // Search + Sort (client-side)
  let searchQuery = '';
  let debouncedSearch = '';
  let searchTimeout: any;
  let sortKey: 'updated' | 'title' | 'status' = 'updated';

  $: {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(()=>{ debouncedSearch = searchQuery.trim().toLowerCase(); }, 300);
  }

  // Derived filtered + sorted courses
  $: filteredCourses = courses
    .filter(c => (courseFilter === 'all' || c.status === courseFilter))
    .filter(c => {
      if (!debouncedSearch) return true;
      const s = debouncedSearch;
      return String(c.title || '').toLowerCase().includes(s)
        || String(c.code || c.meta_json?.code || '').toLowerCase().includes(s)
        || String(c.description || '').toLowerCase().includes(s);
    })
    .slice()
    .sort((a,b) => {
      if (sortKey === 'title') {
        return String(a.title || '').localeCompare(String(b.title || ''));
      } else if (sortKey === 'status') {
        return String(a.status || '').localeCompare(String(b.status || ''));
      } else {
        // updated desc fallback: try updated_at, updated, created_at
        const av = a.updated_at ?? a.updated ?? a.created_at ?? 0;
        const bv = b.updated_at ?? b.updated ?? b.created_at ?? 0;
        return Number(bv) - Number(av);
      }
    });

  // Overview counts
  $: totalCount = courses.length;
  $: activeCount = courses.filter(c => c.status === 'active').length;
  $: draftCount = courses.filter(c => c.status === 'draft').length;
  $: archivedCount = courses.filter(c => c.status === 'archived').length;

  // Create form state
  const initialForm = () => ({
    title: '',
    code: '',
    description: '',
    term: '',
    schedule: '',
    instructorsInput: '', // comma separated entry
    linksInput: '',
    youtubeInput: '',
    visibility: 'public',
    model_id: '',
    system_prompt: '',
    temperature: 0.4,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    max_tokens: 1024,
    tools_json: '',
    retrieval_json: '',
    safety_json: '',
    docFiles: [] as { id: string; name: string }[],
    activateNow: false
  });
  let form = initialForm();
  let submitting = false;
  let showAdvanced = false;
  let archiveConfirm: string | null = null; // course id being archived
  let restoreConfirm: string | null = null;

  async function deleteCourseAndRelated(id: string) {
    const token = localStorage.token || '';
    const course = courses.find(c => c.id === id);
    if (!course) return toast.error('Course not found');
    if (!confirm('Are you sure you want to permanently delete this course and all related knowledge/documents?')) return;
    try {
      // Delete course
      const resCourse = await fetch(`/api/classroom/courses/${id}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
      });
      if (!resCourse.ok) throw await resCourse.json();

      // Delete knowledge if present
      if (course.preset?.knowledge_id) {
        const resKnowledge = await fetch(`/api/knowledge/${course.preset.knowledge_id}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
        });
        if (!resKnowledge.ok) throw await resKnowledge.json();
      }

      // Delete documents related to course (assuming endpoint exists)
      const resDocs = await fetch(`/api/classroom/courses/${id}/documents`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
      });
      if (!resDocs.ok) throw await resDocs.json();

      toast.success('Course and related knowledge/documents deleted.');
      await loadCourses();
    } catch (e) {
      toast.error('Failed to delete course or related data.');
      console.error(e);
    }
  }

  // Model picker
  let models: AggregatedModel[] = [];
  let modelSearch = '';
  let debouncedModelSearch = '';
  let modelSearchTimeout: any;
  let focusedModelIndex = -1;
  let filteredModels: any[] = [];
  let modelsLoading = false;
  let showModelsDropdown = false;

  // Editing
  let editingCourseId: string | null = null;
  let fieldErrors: Record<string,string> = {};
  let editingPreset: any = null;

  const isTeacherOrAdmin = () => {
    const role = $user?.role ?? '';
    return ['admin','teacher'].includes(role);
  };

  const isEditView = (v: ViewState): v is { edit: string } => typeof v === 'object' && v !== null && 'edit' in v;
  // Horizontal tab state for Courses
  let settingsTab: 'courses';

  // Dismiss model dropdown on outside click
  function handleClickOutside(event: MouseEvent){
    const target = event.target as HTMLElement;
    if (showModelsDropdown && !target.closest('[data-model-picker]')) {
      showModelsDropdown = false;
    }
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('click', handleClickOutside);
  }

  onDestroy(()=>{
    if (typeof window !== 'undefined') {
      window.removeEventListener('click', handleClickOutside);
    }
  });

  // Debounce model search
  $: {
    clearTimeout(modelSearchTimeout);
    modelSearchTimeout = setTimeout(()=>{ debouncedModelSearch = modelSearch; }, 350);
  }

  // Filter models by search and exclude embeddings
  $: filteredModels = models.filter(m => !m.is_embedding && (!debouncedModelSearch || (m.label||m.id||'').toLowerCase().includes(debouncedModelSearch.toLowerCase())));
  $: { if (focusedModelIndex >= filteredModels.length) focusedModelIndex = -1; }
  $: editingPreset = editingCourseId ? courses.find(c=>c.id===editingCourseId)?.preset : null;

  function handleModelKeydown(e: KeyboardEvent){
    if (!showModelsDropdown) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); if (filteredModels.length){ focusedModelIndex = (focusedModelIndex + 1) % filteredModels.length; } }
    else if (e.key === 'ArrowUp') { e.preventDefault(); if (filteredModels.length){ focusedModelIndex = (focusedModelIndex - 1 + filteredModels.length) % filteredModels.length; } }
    else if (e.key === 'Enter') { if (focusedModelIndex>=0 && filteredModels[focusedModelIndex]) { const m = filteredModels[focusedModelIndex]; form.model_id = m.id; showModelsDropdown=false; fieldErrors.model_id && delete fieldErrors.model_id; } }
    else if (e.key === 'Escape') { showModelsDropdown = false; }
  }

  onMount(async () => {
    // dynamic import for toast to avoid hard dependency at build time
    try {
      const sonner = await import('svelte-sonner');
      toast = sonner.toast;
    } catch (e) {
      // toast may be unavailable in some dev setups; continue without it
      // console.warn('svelte-sonner not available:', e);
    }

    // Load feature toggle and always attempt to load courses.
    // Previously we only loaded courses when the toggle was enabled which caused
    // the admin page to show an empty list when the feature flag was off.
    try {
      await loadToggle();
      // Always attempt to load courses so admins can inspect/manage them even when the toggle is off.
      await loadCourses();

      // Load models for create/edit view only when classroom is enabled and view requires it
      if (enabled && (view === 'create' || isEditView(view))) {
        await loadModels();
      }
    } catch (e) {
      console.error('[ClassroomSettings] Error:', e);
    }
    loading = false;
  });

  async function loadToggle(){
    try {
      const data = await getClassroomToggle(localStorage.token || '');
      enabled = !!data.enabled;
      classroomEnabled.set(enabled);
    } catch (e) {
      console.error('[ClassroomSettings] Failed to load classroom toggle:', e);
      enabled = false;
      classroomEnabled.set(false);
    }
    try { const pref = localStorage.getItem('classroom:embed'); if (pref!==null) { embedPref = pref==='true'; classroomEmbedInChat.set(embedPref); } } catch{}
  }

  async function saveToggle(){
    saving = true;
    try {
      const res = await fetch('/api/admin/classroom', { method:'PUT', headers:{ 'Content-Type':'application/json', Accept:'application/json', authorization:`Bearer ${localStorage.token}`}, body: JSON.stringify({ enabled }) });
      if (res.ok){ classroomEnabled.set(enabled); if (enabled) await loadCourses(); }
    } finally { saving = false; }
  }

  function saveEmbedPref(){
    classroomEmbedInChat.set(embedPref);
    try { localStorage.setItem('classroom:embed', String(embedPref)); } catch{}
    toast.success('Preference saved');
  }

  // Allow admin to force-load courses even when the global classroom feature toggle is off.
  // This supports the "View courses anyway" button in the UI banner.
  async function forceLoad(){
    try {
      await loadCourses();
    } catch (e) {
      console.error('[AdminClassroom] forceLoad failed:', e);
      toast?.error?.('Failed to load courses');
    }
  }

  let loadCoursesError: string | null = null;

  async function loadCourses(){
    coursesLoading = true;
    loadCoursesError = null;
    try {
      // Primary attempt: use API wrapper (respects WEBUI_BASE_URL)
      courses = await listCourses(localStorage.token);
      console.debug('[AdminClassroom] listCourses(main) returned', courses?.length ?? 0, 'items');
    } catch(e:any){
      console.error('[AdminClassroom] listCourses(main) failed:', e);
      loadCoursesError = e?.detail || e?.message || String(e);
      // Try fallback: relative fetch to current origin (helps debug base URL mismatches)
      try {
        const token = localStorage.token || '';
        const res = await fetch(`/api/classroom/courses`, { headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }});
        if (res.ok) {
          const json = await res.json().catch(()=>null);
          if (Array.isArray(json)) {
            courses = json;
            console.debug('[AdminClassroom] listCourses(fallback) returned', courses.length, 'items');
            loadCoursesError = null;
          } else {
            console.warn('[AdminClassroom] fallback returned non-array:', json);
            loadCoursesError = 'Fallback returned unexpected response';
            courses = [];
          }
        } else {
          const text = await res.text().catch(()=>null);
          console.error('[AdminClassroom] fallback fetch failed:', res.status, res.statusText, text);
          loadCoursesError = `Fallback error: ${res.status} ${res.statusText}`;
          courses = [];
        }
      } catch(fe:any){
        console.error('[AdminClassroom] fallback fetch exception:', fe);
        loadCoursesError = fe?.detail || fe?.message || String(fe);
        courses = [];
      }
    } finally {
      coursesLoading = false;
    }
  }

  async function loadModels() {
    modelsLoading = true;
    try {
      models = await fetchAllModels(localStorage.token);
    } catch (e) {
      console.error('[AdminClassroom] Failed to load models:', e);
      models = [];
    } finally {
      modelsLoading = false;
    }
  }

  async function startEdit(id:string){
    try {
      const c = await getCourse(localStorage.token, id);
      editingCourseId = id;
      form = initialForm();
      form.title = c.title;
      form.description = c.description || '';
      form.code = c.meta_json?.code || '';
      form.term = c.meta_json?.term || '';
      form.schedule = c.meta_json?.schedule || '';
      form.instructorsInput = (c.meta_json?.instructors || []).join(', ');
      form.linksInput = (c.meta_json?.links || []).join('\n');
      form.youtubeInput = (c.meta_json?.videos || []).join('\n');
      form.visibility = c.meta_json?.visibility || 'public';
      // We can't recover original doc id list easily (need knowledge fetch). Skip for now.
      // Model & params via preset if present
      if (c.preset){
        form.model_id = c.preset.model_id || '';
        form.system_prompt = c.preset.system_prompt_md || '';
        form.temperature = c.preset.temperature ?? form.temperature;
        form.max_tokens = c.preset.max_tokens ?? form.max_tokens;
      }
      view = { edit: id };
      await loadModels();
    } catch(e:any){ toast.error(e?.detail || 'Failed to load course'); }
  }
  // New course
  function goNewCourse() {
    goto('/classroom/courses/new');
  }
  async function restoreCourse(id:string){
    restoreConfirm = null;
    try {
      const meta = courses.find(c=>c.id===id) || await getCourse(localStorage.token,id);
      const original = courses.map(c=>({...c}));
      courses = courses.map(c=> c.id===id ? { ...c, status:'draft' } : c);
      await fetch(`/api/classroom/courses/${id}`, { method:'PUT', headers:{'Content-Type':'application/json', Accept:'application/json', authorization:`Bearer ${localStorage.token}`}, body: JSON.stringify({ title: meta?.title || 'Course', status:'draft' }) });
      toast.success('Course restored to draft');
      loadCourses();
    } catch(e:any){ toast.error(e?.detail || 'Restore failed'); }
  }

  function resetForm(){ form = initialForm(); showAdvanced = false; }

  async function handleFileSelect(e: Event){
    const input = e.target as HTMLInputElement;
    if (!input.files) return;
    for (const f of Array.from(input.files)){
      try {
        const uploaded = await uploadFile(localStorage.token, f);
        form.docFiles.push({ id: uploaded.id, name: f.name });
      } catch(err){ toast.error('Upload failed: '+err); }
    }
  }

  function removeDoc(i:number){ form.docFiles.splice(i,1); }

  async function submitCreate(){
    fieldErrors = {};
    if (!form.title.trim()) { fieldErrors.title='Title required'; toast.error('Title required'); }
    if (!form.model_id.trim()) { fieldErrors.model_id='Model required'; toast.error('Model ID required'); }
    if (form.docFiles.length < 1) { fieldErrors.docFiles='At least one document required'; toast.error('At least one document required'); }
    if (Object.keys(fieldErrors).length) return;
    submitting = true;
    try {
      const body:any = {
        title: form.title.trim(),
        description: form.description || undefined,
        code: form.code || undefined,
        term: form.term || undefined,
        schedule: form.schedule || undefined,
        instructors: form.instructorsInput.split(',').map(s=>s.trim()).filter(Boolean),
        links: form.linksInput.split('\n').map(s=>s.trim()).filter(Boolean),
        youtube_embeds: form.youtubeInput.split('\n').map(s=>s.trim()).filter(Boolean),
        visibility: form.visibility,
        doc_file_ids: form.docFiles.map(f=>f.id),
        model_id: form.model_id,
        system_prompt: form.system_prompt || undefined,
        temperature: form.temperature,
        top_p: form.top_p,
        frequency_penalty: form.frequency_penalty,
        presence_penalty: form.presence_penalty,
        max_tokens: form.max_tokens,
      };
      if (form.tools_json) { try { body.tools_json = JSON.parse(form.tools_json);} catch{ toast.error('Invalid tools JSON'); submitting=false; return;}}
      if (form.retrieval_json) { try { body.retrieval_json = JSON.parse(form.retrieval_json);} catch{ toast.error('Invalid retrieval JSON'); submitting=false; return;}}
      if (form.safety_json) { try { body.safety_json = JSON.parse(form.safety_json);} catch{ toast.error('Invalid safety JSON'); submitting=false; return;}}
      const newCourse = await createCourse(localStorage.token, body);
      if (form.activateNow) {
        try {
          const res = await fetch(`/api/classroom/courses/${newCourse.id}/activate`, { method:'POST', headers:{ Accept:'application/json', authorization:`Bearer ${localStorage.token}` }});
          if (!res.ok) {
            const err = await res.json().catch(()=>({detail:'Activation failed'}));
            toast.error(err.detail || 'Activation failed');
          } else {
            toast.success('Course created & activated');
          }
        } catch (e:any) { toast.error('Activation request failed'); }
      } else {
        toast.success('Course created');
      }
      resetForm();
      await loadCourses();
      view = 'list';
    } catch(err:any){ toast.error(err?.detail || 'Create failed'); }
    finally { submitting = false; }
  }

  async function submitEdit(){
    if (!editingCourseId) return;
    fieldErrors = {};
    if (!form.title.trim()) { fieldErrors.title='Title required'; toast.error('Title required'); return; }
    submitting = true;
    try {
      // Note: backend update_course currently stub-like; sending minimal fields
      const res = await fetch(`/api/classroom/courses/${editingCourseId}`, { method:'PUT', headers:{ 'Content-Type':'application/json', Accept:'application/json', authorization:`Bearer ${localStorage.token}` }, body: JSON.stringify({ title: form.title.trim(), description: form.description || undefined }) });
      if (!res.ok){ const err = await res.json().catch(()=>({detail:'Update failed'})); toast.error(err.detail);} else { toast.success('Course updated'); await loadCourses(); view='list'; editingCourseId=null; }
    } catch(e:any){ toast.error(e?.detail || 'Update failed'); }
    finally { submitting=false; }
  }

  // Basic JSON validation helpers for on-blur validation of textarea fields
  function validateJsonField(value: string, fieldName: string){
    if (!value) { delete fieldErrors[fieldName]; return true; }
    try { JSON.parse(value); delete fieldErrors[fieldName]; return true; } catch { fieldErrors[fieldName] = 'Invalid JSON'; return false; }
  }

  // Event handlers moved to script to avoid inline TS assertions in markup
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
</script>

<div class="p-4 space-y-6">
  {#if loading}
    <div class="text-sm text-gray-500">Loading classroom settings…</div>
  {/if}

  <!-- Header + controls -->
  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div class="min-w-0">
      <h1 class="text-2xl font-semibold" style="font-family: Helvetica, Arial, sans-serif;">Classroom</h1>
      <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
        Manage virtual classroom courses. Only teachers &amp; admins can modify.
      </p>
    </div>
  </div>

  {#if !isTeacherOrAdmin()}
    <div class="p-4 rounded-md border border-yellow-300/40 bg-yellow-50 dark:bg-yellow-900/20 text-sm">
      Access restricted. Contact an administrator.
    </div>
{:else}

  <!-- Two columns only for this section: 70% content / 30% spacer -->
  <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,70%)_minmax(0,30%)] gap-4">
    {#if !enabled}
      <!-- Banner shown to admins when classroom feature global toggle is disabled.
          We still attempt to load courses (admin can inspect/manage), and the button
          allows forcing a refresh if the backend becomes reachable. -->
      <div class="p-3 rounded-md border border-gray-200 bg-gray-50 dark:bg-gray-800 text-sm flex items-center justify-between gap-4">
        <div class="text-sm text-neutral-700 dark:text-neutral-200">
          Classroom feature is currently disabled globally. Administrators can still view and manage courses.
        </div>
        <div class="flex items-center gap-2">
          <button class="px-3 py-1 rounded-md bg-white border text-sm hover:bg-gray-50 dark:bg-neutral-700 dark:border-neutral-700 dark:text-neutral-100" on:click={saveToggle} disabled={saving}>
            Toggle enabled
          </button>
          <button class="px-3 py-1 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700" on:click={forceLoad}>
            View courses anyway
          </button>
        </div>
      </div>
    {/if}
    <!-- LEFT COLUMN (everything lives here) -->
    <section class="min-w-0 space-y-4">
      <!-- Header (fixed to Courses) + primary action -->
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-2">
          <button
            class="h-9 px-3 rounded-md bg-blue-600 text-white text-sm"
            on:click={() => goto('/classroom/courses/new')}
          >New Course</button>
        </div>
      </div>

      <!-- Overview strip -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <button class="p-3 rounded-lg border hover:shadow-sm text-left focus:outline-none focus:ring-2 focus:ring-blue-500">
          <div class="text-xs text-gray-500">Active</div>
          <div class="text-lg font-semibold">{activeCount}</div>
        </button>
        <button class="p-3 rounded-lg border hover:shadow-sm text-left focus:outline-none focus:ring-2 focus:ring-blue-500">
          <div class="text-xs text-gray-500">Draft</div>
          <div class="text-lg font-semibold">{draftCount}</div>
        </button>
        <div class="p-3 rounded-lg border text-left">
          <div class="text-xs text-gray-500">Total</div>
          <div class="text-lg font-semibold">{totalCount}</div>
        </div>
      </div>

      <!-- Course grid -->
      <div class="mt-4 rounded-lg border border-gray-200 dark:border-gray-800">
        {#if coursesLoading}
          <div class="text-sm text-gray-500">Loading courses…</div>
        {:else if courses.length === 0}
          <div class="p-10 border border-dashed rounded-lg text-center text-sm text-gray-500 dark:text-gray-400">
            <div class="mb-2 font-medium">No courses yet</div>
            <div class="mb-4">Create your first course to get started.</div>
            <button
              class="h-9 px-3 rounded-md bg-blue-600 text-white text-sm"
              on:click={() => goto('/classroom/courses/new')}
            >Create First Course</button>
          </div>
        {:else}
          <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each filteredCourses as c}
              <article class="p-4 rounded-lg border border-gray-200 dark:border-gray-800 bg-white/60 dark:bg-gray-900/40 relative shadow-sm">
                {#if c.status==='archived'}
                  <div class="absolute inset-0 bg-gray-100/40 dark:bg-black/40 rounded-lg pointer-events-none"></div>
                {/if}

                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <h3 class="font-semibold text-sm line-clamp-1" title={c.title} style="font-family: Helvetica, Arial, sans-serif;">
                      {c.title}
                    </h3>
                    <div class="mt-1 text-[11px] inline-flex items-center gap-2">
                      <span class="px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wide {c.status==='active' ? 'bg-green-50 text-green-700' : c.status==='archived' ? 'bg-gray-100 text-gray-600' : 'bg-yellow-50 text-yellow-800'}">
                        {c.status}
                      </span>
                      <span class="text-neutral-500 truncate">
                        {c.meta_json?.code || c.code || '—'}{c.meta_json?.term ? ` · ${c.meta_json.term}` : ''}
                      </span>
                    </div>
                    {#if c.description}
                      <p class="text-xs text-neutral-600 dark:text-neutral-300 mt-2 line-clamp-2">{c.description}</p>
                    {/if}
                  </div>

                  <div class="flex flex-col items-end gap-2">
                    <div class="text-xs text-neutral-500">{(c.documents && c.documents.length) ?? c.doc_count ?? '—'}</div>
                    <div class="text-[11px] text-neutral-400">{c.updated_at ? new Date(c.updated_at).toLocaleDateString() : ''}</div>
                  </div>
                </div>

                <div class="flex items-center justify-end gap-2 mt-3">
                  <button
                    class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 disabled:opacity-40 focus:ring-2 focus:ring-blue-500"
                    on:click={() => goto(`/classroom/courses/${c.id}/edit`)}
                    disabled={c.status==='archived'}
                    aria-label={`Edit ${c.title}`}
                  >Edit</button>

                  {#if c.status!=='archived'}
                    <button
                      class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 focus:ring-2 focus:ring-blue-500"
                      on:click={() => archiveConfirm=c.id}
                      aria-label={`Archive ${c.title}`}
                    >Archive</button>
                  {:else}
                    <button
                      class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 focus:ring-2 focus:ring-blue-500"
                      on:click={() => restoreConfirm=c.id}
                      aria-label={`Restore ${c.title}`}
                    >Restore</button>
                  {/if}
                </div>
              </article>
            {/each}
          </div>

          <!-- Restore modal -->
          {#if restoreConfirm}
            <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-40" role="dialog" aria-modal="true" aria-label="Restore course">
              <div class="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-md space-y-4 text-sm focus:outline-none" tabindex="0">
                <div class="font-medium">Restore course?</div>
                <p>Restoring returns the course to Draft status.</p>
                <div class="flex justify-end gap-2">
                  <button class="px-3 py-1.5 text-xs rounded bg-gray-200 dark:bg-gray-800" on:click={() => restoreConfirm=null}>Cancel</button>
                  <button class="px-3 py-1.5 text-xs rounded bg-blue-600 text-white" on:click={() => restoreConfirm && restoreCourse(restoreConfirm)}>Restore</button>
                </div>
              </div>
            </div>
          {/if}
        {/if}
      </div>
    </section>

    <!-- RIGHT COLUMN (spacer / future filters) -->
    <aside class="hidden lg:block"></aside>
  </div>
{/if}
</div>
