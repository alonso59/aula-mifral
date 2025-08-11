let errorMsg = '';
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { user, settings } from '$lib/stores';
  import { config } from '$lib/stores';
  import { classroomEnabled, classroomEmbedInChat } from '$lib/stores/classroom';
  import { listCourses, createCourse, getCourse, updateCourse } from '$lib/apis/classroom';
  import { uploadFile } from '$lib/apis/files';
  import { toast } from 'svelte-sonner';
// TODO: Ensure svelte-sonner is installed in your project
  import { fetchAllModels, AggregatedModel } from '$lib/apis/models/fetchAllModels';

import { get } from 'svelte/store';

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
    visibility: 'private',
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

  let deleteConfirm: string | null = null; // course id being deleted

  async function deleteCourseAndRelated(id: string) {
    deleteConfirm = null;
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
  let enrollments: Array<{ id:string; user_id:string; is_teacher:boolean; created_at:number }> = [];
  let enrollmentsLoading = false;
  let enrollmentInput = '';
  let enrollmentAdding = false;
  let fieldErrors: Record<string,string> = {};
  let editingPreset: any = null;

  const isTeacherOrAdmin = () => {
    const role = $user?.role ?? '';
    return ['admin','teacher'].includes(role);
  };
let errorMsg = '';
  const isEditView = (v: ViewState): v is { edit: string } => typeof v === 'object' && v !== null && 'edit' in v;
  // Horizontal tab state for General / Courses
  let settingsTab: 'general' | 'courses' = 'courses';

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
    if (typeof window !== 'undefined') window.removeEventListener('click', handleClickOutside);
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
    // Only allow admins/teachers to access management UI; others see message
    try {
      await loadToggle();
      if (enabled) await loadCourses();
      // Load models for create/edit view
      if (enabled && (view === 'create' || isEditView(view))) {
        await loadModels();
      }
    } catch (e) {
      errorMsg = 'Failed to load classroom settings: ' + (e && typeof e === 'object' && 'message' in e ? (e as any).message : String(e));
      console.error('[ClassroomSettings] Error:', errorMsg);
    }
    loading = false;
  });

  async function loadToggle(){
    try {
      const res = await fetch('/api/admin/settings/classroom', { headers: { Accept: 'application/json', authorization: `Bearer ${localStorage.token}` }});
      if (res.ok){
        const data = await res.json();
        enabled = !!data.enabled; classroomEnabled.set(enabled);
      } else {
        errorMsg = `Failed to load classroom settings: ${res.status} ${res.statusText}`;
        console.error(errorMsg);
      }
    } catch(e){
      errorMsg = `Error loading classroom settings: ` + (e && typeof e === 'object' && 'message' in e ? (e as any).message : String(e));
      console.error(errorMsg);
    }
    try { const pref = localStorage.getItem('classroom:embed'); if (pref!==null) { embedPref = pref==='true'; classroomEmbedInChat.set(embedPref); } } catch{}
  }

  async function saveToggle(){
    saving = true;
    try {
      const res = await fetch('/api/admin/settings/classroom', { method:'PUT', headers:{ 'Content-Type':'application/json', Accept:'application/json', authorization:`Bearer ${localStorage.token}`}, body: JSON.stringify({ enabled }) });
      if (res.ok){ classroomEnabled.set(enabled); if (enabled) await loadCourses(); }
    } finally { saving = false; }
  }

  function saveEmbedPref(){
    classroomEmbedInChat.set(embedPref);
    try { localStorage.setItem('classroom:embed', String(embedPref)); } catch{}
    toast.success('Preference saved');
  }

  async function loadCourses(){
    coursesLoading = true;
    try { courses = await listCourses(localStorage.token); } catch(e){ console.error(e);} finally { coursesLoading = false; }
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
      form.visibility = c.meta_json?.visibility || 'private';
      // We can't recover original doc id list easily (need knowledge fetch). Skip for now.
      // Model & params via preset if present
      if (c.preset){
        form.model_id = c.preset.model_id || '';
        form.system_prompt = c.preset.system_prompt_md || '';
        form.temperature = c.preset.temperature ?? form.temperature;
        form.max_tokens = c.preset.max_tokens ?? form.max_tokens;
      }
      view = { edit: id };
      await loadEnrollments(id);
      await loadModels();
    } catch(e:any){ toast.error(e?.detail || 'Failed to load course'); }
  }

  async function archiveCourse(id:string){
    archiveConfirm = null;
    try {
      // fetch to preserve title
      const meta = courses.find(c=>c.id===id) || await getCourse(localStorage.token,id);
  // Optimistic update
  const original = courses.map(c=>({...c}));
  courses = courses.map(c=> c.id===id ? { ...c, status:'archived' } : c);
      await fetch(`/api/classroom/courses/${id}`, { method:'PUT', headers:{'Content-Type':'application/json', Accept:'application/json', authorization:`Bearer ${localStorage.token}`}, body: JSON.stringify({ title: meta?.title || 'Course', status:'archived' }) });
      toast.success('Course archived');
  // Background refresh to reconcile
  loadCourses();
    } catch(e:any){ toast.error(e?.detail || 'Archive failed'); }
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

  async function loadEnrollments(courseId:string){
    enrollmentsLoading = true;
    try {
      const res = await fetch(`/api/classroom/courses/${courseId}/enrollments`, { headers:{ Accept:'application/json', authorization:`Bearer ${localStorage.token}`}});
      if (res.ok) enrollments = await res.json();
    } catch(e){ console.error(e);} finally { enrollmentsLoading=false; }
  }

  async function addEnrollment(){
    if (!enrollmentInput.trim()) return;
    enrollmentAdding = true;
    try {
      const body = { user_id: enrollmentInput.trim(), is_teacher:false };
      const res = await fetch(`/api/classroom/courses/${editingCourseId}/enrollments`, { method:'POST', headers:{'Content-Type':'application/json', Accept:'application/json', authorization:`Bearer ${localStorage.token}`}, body: JSON.stringify(body) });
      if (!res.ok){ const err = await res.json().catch(()=>({detail:'Add failed'})); toast.error(err.detail); }
      else { toast.success('Enrollment added'); enrollmentInput=''; await loadEnrollments(editingCourseId!); }
    } finally { enrollmentAdding=false; }
  }

  async function removeEnrollment(uid:string){
    try {
      const res = await fetch(`/api/classroom/courses/${editingCourseId}/enrollments/${uid}`, { method:'DELETE', headers:{ Accept:'application/json', authorization:`Bearer ${localStorage.token}`}});
      if (!res.ok){ const err = await res.json().catch(()=>({detail:'Remove failed'})); toast.error(err.detail);} else { toast.success('Removed'); await loadEnrollments(editingCourseId!);} }
    catch(e:any){ toast.error(e?.detail || 'Remove failed'); }
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
</script>

  <div class="p-4 space-y-6">
    {#if loading}
      <div class="text-sm text-gray-500">Loading classroom settings…</div>
    {/if}
    {#if errorMsg}
  <div class="p-4 rounded-md border border-red-300 bg-red-50 text-sm text-red-700">{errorMsg}</div>
    {/if}
  <div>
    <h1 class="text-lg font-semibold">Classroom</h1>
    <p class="text-sm text-gray-600 dark:text-gray-300">Manage virtual classroom courses. Only teachers & admins can modify.</p>
  </div>

  {#if !isTeacherOrAdmin()}
    <div class="p-4 rounded-md border border-yellow-300/40 bg-yellow-50 dark:bg-yellow-900/20 text-sm">Access restricted. Contact an administrator.</div>
  {:else}
    <div class="rounded-xl border border-gray-200 dark:border-gray-800 p-4 space-y-4">
      {#if loading}
        <div class="text-sm text-gray-500">Loading…</div>
      {:else}
        <div class="flex flex-col gap-3">
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-2 text-sm">
              <input type="checkbox" bind:checked={enabled} />
              <span>Enable Classroom</span>
            </label>
            <button class="px-2.5 py-1 rounded-md bg-blue-600 text-white text-xs disabled:opacity-60" on:click={saveToggle} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
          </div>
          {#if enabled && ($user?.role==='admin' || $user?.role==='teacher')}
            <div class="flex items-center gap-3">
              <label class="flex items-center gap-2 text-sm">
                <input type="checkbox" bind:checked={embedPref} />
                <span>Embed Classroom in Chat (personal)</span>
              </label>
              <button class="px-2.5 py-1 rounded-md bg-gray-200 dark:bg-gray-700 text-xs" type="button" on:click={saveEmbedPref}>Apply</button>
            </div>
          {/if}
        </div>
      {/if}
    </div>

    {#if enabled}
      <!-- Horizontal tabs: General | Courses -->
      <div class="flex items-center justify-between gap-4 mt-2">
        <div class="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 rounded-md p-1">
          <button
            class="px-3 py-1 text-sm rounded-md {settingsTab==='general' ? 'bg-white dark:bg-gray-900 shadow' : 'hover:bg-gray-200 dark:hover:bg-gray-700'}"
            on:click={() => { settingsTab = 'general'; }}
          >General</button>
          <button
            class="px-3 py-1 text-sm rounded-md {settingsTab==='courses' ? 'bg-white dark:bg-gray-900 shadow' : 'hover:bg-gray-200 dark:hover:bg-gray-700'}"
            on:click={() => { settingsTab = 'courses'; }}
          >Courses</button>
        </div>

        <div class="flex gap-2">
          {#if settingsTab === 'courses'}
            {#if view === 'list'}
              <button class="px-3 py-1.5 rounded-md bg-blue-600 text-white text-xs" on:click={() => { resetForm(); view = 'create'; }}>New Course</button>
            {:else}
              <button class="px-3 py-1.5 rounded-md bg-gray-200 dark:bg-gray-800 text-xs" on:click={() => { view = 'list'; }}>Back to List</button>
            {/if}
          {:else}
            <div class="text-sm text-neutral-600 dark:text-neutral-400">Manage general classroom settings</div>
          {/if}
        </div>
      </div>

      {#if view==='list'}
        <div class="mt-3">
          {#if coursesLoading}
            <div class="text-sm text-gray-500">Loading courses…</div>
          {:else if courses.length === 0}
            <div class="p-10 border border-dashed rounded-lg text-center text-sm text-gray-500 dark:text-gray-400">
              <div class="mb-2 font-medium">No courses yet</div>
              <div class="mb-4">Create your first course to get started.</div>
              <button class="px-3 py-1.5 rounded-md bg-blue-600 text-white text-xs" on:click={()=>{ resetForm(); view='create'; }}>Create Course</button>
            </div>
          {:else}
            <div class="flex gap-2 mb-3 text-xs">
              {#each ['all','active','draft','archived'] as f}
                <button type="button"
                  class="px-2 py-1 rounded-full border transition-colors focus:outline-none focus:ring-1 focus:ring-blue-500 {courseFilter===f ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800'}"
                  on:click={()=>setCourseFilter(f)}
                >{f.charAt(0).toUpperCase()+f.slice(1)}</button>
              {/each}
            </div>
            <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {#each courses.filter(c=>courseFilter==='all' || c.status===courseFilter) as c}
                <div class="p-4 rounded-lg border border-gray-200 dark:border-gray-800 flex flex-col gap-2 bg-white/60 dark:bg-gray-900/40 relative">
                  {#if c.status==='archived'}<div class="absolute inset-0 bg-gray-200/30 dark:bg-black/30 backdrop-blur-[1px] rounded-lg pointer-events-none"></div>{/if}
                  <div class="flex justify-between">
                    <h3 class="font-medium text-sm line-clamp-1" title={c.title}>{c.title}</h3>
                    <span class="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 {c.status==='active' ? 'text-green-600' : c.status==='archived' ? 'text-gray-500' : 'text-yellow-600'}">{c.status}</span>
                  </div>
                  {#if c.description}<p class="text-xs line-clamp-2 min-h-[2.25rem]">{c.description}</p>{/if}
                  <div class="flex justify-end gap-2 pt-1">
                    <button class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 disabled:opacity-40" on:click={()=>startEdit(c.id)} disabled={c.status==='archived'}>Edit</button>
                    {#if c.status!=='archived'}
                        <button class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800" on:click={()=>archiveConfirm=c.id}>Archive</button>
                        {#if isTeacherOrAdmin()}
                          <button class="text-xs px-2 py-1 rounded bg-red-100 dark:bg-red-900 text-red-700" on:click={()=>deleteConfirm=c.id}>Delete</button>
                        {/if}
                    {:else}
                      <button class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800" on:click={()=>restoreConfirm=c.id}>Restore</button>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
            {#if archiveConfirm}
              <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-40">
                <div class="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-sm space-y-4 text-sm">
                  <div class="font-medium">Archive course?</div>
                  <p>Archiving hides the course from active use. You can restore later.</p>
                  <div class="flex justify-end gap-2">
                    <button class="px-3 py-1.5 text-xs rounded bg-gray-200 dark:bg-gray-800" on:click={()=>archiveConfirm=null}>Cancel</button>
                    <button class="px-3 py-1.5 text-xs rounded bg-amber-600 text-white" on:click={()=>archiveConfirm && archiveCourse(archiveConfirm)}>Archive</button>
                  </div>
                </div>
              </div>
            {/if}
              {#if deleteConfirm}
                <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-40">
                  <div class="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-sm space-y-4 text-sm">
                    <div class="font-medium">Delete course?</div>
                    <p>This will permanently delete the course and all related knowledge/documents. This action cannot be undone.</p>
                    <div class="flex justify-end gap-2">
                      <button class="px-3 py-1.5 text-xs rounded bg-gray-200 dark:bg-gray-800" on:click={()=>deleteConfirm=null}>Cancel</button>
                      <button class="px-3 py-1.5 text-xs rounded bg-red-600 text-white" on:click={()=>deleteConfirm && deleteCourseAndRelated(deleteConfirm)}>Delete</button>
                    </div>
                  </div>
                </div>
              {/if}
            {#if restoreConfirm}
              <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-40">
                <div class="bg-white dark:bg-gray-900 rounded-lg p-6 w-full max-w-sm space-y-4 text-sm">
                  <div class="font-medium">Restore course?</div>
                  <p>Restoring returns the course to Draft status.</p>
                  <div class="flex justify-end gap-2">
                    <button class="px-3 py-1.5 text-xs rounded bg-gray-200 dark:bg-gray-800" on:click={()=>restoreConfirm=null}>Cancel</button>
                    <button class="px-3 py-1.5 text-xs rounded bg-blue-600 text-white" on:click={()=>restoreConfirm && restoreCourse(restoreConfirm)}>Restore</button>
                  </div>
                </div>
              </div>
            {/if}
          {/if}
        </div>
  {:else if view==='create' || isEditView(view)}
        <form class="mt-4 space-y-10 max-w-4xl leading-snug" on:submit|preventDefault={view==='create' ? submitCreate : submitEdit}>
          <!-- Basics -->
          <section class="space-y-3">
            <h2 class="text-sm font-semibold tracking-wide">Basics</h2>
            <div class="grid md:grid-cols-2 gap-4 text-sm">
              <div class="flex flex-col gap-1">
                <label class="font-medium">Title *</label>
                <input class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.title} placeholder="Course title" required />
                {#if fieldErrors.title}<div class="text-[11px] text-red-600">{fieldErrors.title}</div>{/if}
              </div>
              <div class="flex flex-col gap-1">
                <label class="font-medium">Code</label>
                <input class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.code} placeholder="e.g. CS101" />
              </div>
              <div class="md:col-span-2 flex flex-col gap-1">
                <label class="font-medium">Description</label>
                <textarea class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm min-h-24" bind:value={form.description} placeholder="Brief description" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="font-medium">Term</label>
                <input class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.term} placeholder="Fall 2024" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="font-medium">Schedule</label>
                <input class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.schedule} placeholder="Mon/Wed 10:00" />
              </div>
              <div class="md:col-span-2 flex flex-col gap-1">
                <label class="font-medium">Instructors (comma separated)</label>
                <input class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.instructorsInput} placeholder="prof@example.com, ta@example.com" />
              </div>
            </div>
          </section>

          <!-- AI Model -->
          <section class="space-y-3">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-semibold tracking-wide">AI Model</h2>
              <button type="button" class="text-xs underline" on:click={()=>showAdvanced = !showAdvanced}>{showAdvanced ? 'Hide' : 'Show'} Advanced</button>
            </div>
            <div class="grid md:grid-cols-2 gap-4 text-sm">
              <div class="flex flex-col gap-1">
                <label class="font-medium">Base Model *</label>
                <div data-model-picker class="relative">
                  <button type="button" class="w-full text-left rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 text-sm" on:click={()=>{ if(models.length===0) loadModels(); showModelsDropdown = !showModelsDropdown; focusedModelIndex=-1; }}>{form.model_id ? (models.find(m=>m.id===form.model_id)?.label || form.model_id) : 'Choose a model'}</button>
                  {#if fieldErrors.model_id}<div class="text-[11px] text-red-600 mt-1">{fieldErrors.model_id}</div>{/if}
                  {#if showModelsDropdown}
                    <div class="absolute z-10 mt-1 max-h-56 overflow-y-auto w-full rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-xs shadow-lg">
                      <div class="p-1 flex items-center justify-between">
                        <input class="w-full px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-transparent text-xs" placeholder="Search" bind:value={modelSearch} on:keydown={handleModelKeydown} />
                        <button type="button" class="ml-2 px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-xs" on:click={loadModels} title="Reload models">Reload</button>
                      </div>
                      {#if modelsLoading}
                        <div class="px-2 py-2 text-gray-500">Loading…</div>
                      {:else if filteredModels.length === 0}
                        <div class="px-2 py-2 text-gray-500">No matches</div>
                      {:else}
                        {#each filteredModels as m, i}
                          <div class="px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer flex justify-between {focusedModelIndex===i ? 'bg-gray-100 dark:bg-gray-800' : ''}" on:click={()=>{ form.model_id = m.id; showModelsDropdown=false; fieldErrors.model_id && delete fieldErrors.model_id; }}>
                            <span class="truncate" title={m.label}>{m.label} <span class="text-gray-400">({m.provider})</span></span>{#if form.model_id===m.id}<span>✓</span>{/if}
                          </div>
                        {/each}
                      {/if}
                    </div>
                  {/if}
                </div>
                {#if fieldErrors.model_id && !showModelsDropdown}<div class="text-[11px] text-red-600">{fieldErrors.model_id}</div>{/if}
              </div>
              <div class="md:col-span-2 flex flex-col gap-1">
                <label class="font-medium">System Prompt</label>
                <textarea class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm min-h-24" bind:value={form.system_prompt} placeholder="Instructions for the course assistant" />
              </div>
              {#if showAdvanced}
                <div class="flex flex-col gap-1"><label class="font-medium">Temperature</label><input type="number" step="0.01" min="0" max="2" class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.temperature} /></div>
                <div class="flex flex-col gap-1"><label class="font-medium">Top P</label><input type="number" step="0.01" min="0" max="1" class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.top_p} /></div>
                <div class="flex flex-col gap-1"><label class="font-medium">Frequency Penalty</label><input type="number" step="0.01" min="-2" max="2" class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.frequency_penalty} /></div>
                <div class="flex flex-col gap-1"><label class="font-medium">Presence Penalty</label><input type="number" step="0.01" min="-2" max="2" class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.presence_penalty} /></div>
                <div class="flex flex-col gap-1"><label class="font-medium">Max Tokens</label><input type="number" min="1" max="128000" class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.max_tokens} /></div>
                <div class="md:col-span-2 grid md:grid-cols-3 gap-4">
                  <div class="flex flex-col gap-1"><label class="font-medium">Tools JSON</label><textarea class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm min-h-24" bind:value={form.tools_json} placeholder='Example tools JSON' /></div>
                  <div class="flex flex-col gap-1"><label class="font-medium">Retrieval JSON</label><textarea class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm min-h-24" bind:value={form.retrieval_json} placeholder='Example retrieval JSON' /></div>
                  <div class="flex flex-col gap-1"><label class="font-medium">Safety JSON</label><textarea class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm min-h-24" bind:value={form.safety_json} placeholder='Example safety JSON' /></div>
                </div>
              {/if}
            </div>
          </section>

          <!-- Content -->
          <section class="space-y-3">
            <h2 class="text-sm font-semibold tracking-wide">Content</h2>
            <div class="grid md:grid-cols-2 gap-4 text-sm">
              <div class="flex flex-col gap-1 md:col-span-2">
                <label class="font-medium">Documents *</label>
                <input type="file" multiple on:change={handleFileSelect} class="block text-xs" />
                {#if form.docFiles.length === 0}
                  <div class="text-xs text-gray-500">Select at least one file.</div>
                  {#if fieldErrors.docFiles}<div class="text-[11px] text-red-600">{fieldErrors.docFiles}</div>{/if}
                {:else}
                  <ul class="text-xs mt-1 space-y-1 max-h-32 overflow-y-auto">
                    {#each form.docFiles as f, i}
                      <li class="flex justify-between gap-2"><span class="truncate">{f.name}</span><button type="button" class="text-red-500" on:click={()=>removeDoc(i)}>×</button></li>
                    {/each}
                  </ul>
                {/if}
              </div>
              <div class="flex flex-col gap-1">
                <label class="font-medium">Links (one per line)</label>
                <textarea class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm min-h-24" bind:value={form.linksInput} placeholder="https://example.com" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="font-medium">YouTube URLs (one per line)</label>
                <textarea class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm min-h-24" bind:value={form.youtubeInput} placeholder="https://youtube.com/watch?v=..." />
              </div>
            </div>
          </section>

            <!-- Access & Options -->
            <section class="space-y-3">
              <h2 class="text-sm font-semibold tracking-wide">Access & Options</h2>
              <div class="grid md:grid-cols-3 gap-4 text-sm">
                <div class="flex flex-col gap-1">
                  <label class="font-medium">Visibility</label>
                  <select class="rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm" bind:value={form.visibility}>
                    <option value="private">Private</option>
                    <option value="org">Org</option>
                    <option value="public">Public</option>
                  </select>
                </div>
                <label class="flex items-center gap-2 text-xs mt-6 md:col-span-2"><input type="checkbox" bind:checked={form.activateNow} /> Activate immediately</label>
              </div>
            </section>

          <div class="pt-2 flex gap-3">
            {#if view==='create'}
              <button type="submit" class="px-4 py-2 rounded-md bg-blue-600 text-white text-sm disabled:opacity-60" disabled={submitting}>{submitting ? 'Creating…' : 'Create Course'}</button>
              <button type="button" class="px-4 py-2 rounded-md bg-gray-200 dark:bg-gray-800 text-sm" on:click={()=>resetForm()}>Reset</button>
            {:else if isEditView(view)}
              <button type="submit" class="px-4 py-2 rounded-md bg-blue-600 text-white text-sm disabled:opacity-60" disabled={submitting}>{submitting ? 'Saving…' : 'Save Changes'}</button>
            {/if}
          </div>
          {#if isEditView(view)}
            <div class="border-t border-gray-200 dark:border-gray-800 pt-6 space-y-4">
              <h3 class="text-sm font-semibold tracking-wide">Enrollments</h3>
              {#if enrollmentsLoading}
                <div class="text-xs text-gray-500">Loading enrollments…</div>
              {:else}
                <ul class="text-xs space-y-1 max-h-40 overflow-y-auto">
                  {#each enrollments as en}
                    <li class="flex justify-between items-center gap-2 py-0.5 px-2 rounded bg-gray-100 dark:bg-gray-800">
                      <span class="truncate" title={en.user_id}>{en.user_id}{en.is_teacher ? ' (teacher)' : ''}</span>
                      {#if isTeacherOrAdmin() && !en.is_teacher}
                        <button class="text-red-500" type="button" on:click={()=>removeEnrollment(en.user_id)}>×</button>
                      {/if}
                    </li>
                  {/each}
                  {#if enrollments.length===0}
                    <li class="text-gray-500">No enrollments yet.</li>
                  {/if}
                </ul>
                {#if isTeacherOrAdmin()}
                  <div class="flex gap-2 mt-2">
                    <input class="flex-1 rounded-md border border-gray-300 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 text-xs" placeholder="User ID or email" bind:value={enrollmentInput} />
                    <button type="button" class="px-3 py-1.5 rounded-md bg-gray-200 dark:bg-gray-700 text-xs disabled:opacity-50" on:click={addEnrollment} disabled={enrollmentAdding}>{enrollmentAdding ? 'Adding…' : 'Add'}</button>
                  </div>
                {/if}
              {/if}
              <!-- Preset (read-only) -->
              {#if editingCourseId}
                <div class="border-t border-gray-200 dark:border-gray-800 pt-4 space-y-2">
                  <h4 class="text-xs uppercase tracking-wide font-semibold text-gray-600 dark:text-gray-300">Preset (Read-only)</h4>
                  {#key editingCourseId}
          {#if editingPreset}
                      <div class="grid text-[11px] sm:grid-cols-2 gap-x-6 gap-y-1">
                        <div class="font-semibold col-span-2 mt-1 text-gray-700 dark:text-gray-300">Provider / Model</div>
            <div class="text-gray-500">Provider</div><div>{editingPreset.provider || '—'}</div>
            <div class="text-gray-500">Model ID</div><div class="truncate" title={editingPreset.model_id}>{editingPreset.model_id || '—'}</div>
                        <div class="font-semibold col-span-2 mt-2 text-gray-700 dark:text-gray-300">Generation Params</div>
            <div class="text-gray-500">Temperature</div><div>{editingPreset.temperature ?? '—'}</div>
            <div class="text-gray-500">Max Tokens</div><div>{editingPreset.max_tokens ?? '—'}</div>
            <div class="text-gray-500">System Prompt</div><div class="truncate" title={editingPreset.system_prompt_md}>{editingPreset.system_prompt_md ? editingPreset.system_prompt_md.slice(0,80)+(editingPreset.system_prompt_md.length>80?'…':'') : '—'}</div>
                        <div class="font-semibold col-span-2 mt-2 text-gray-700 dark:text-gray-300">Tools / Safety</div>
            <div class="text-gray-500">Tools</div><div>{editingPreset.tools_json ? Object.keys(editingPreset.tools_json).length : 0}</div>
            <div class="text-gray-500">Safety</div><div>{editingPreset.safety_json ? Object.keys(editingPreset.safety_json).length : 0}</div>
            <div class="text-gray-500">Retrieval</div><div>{editingPreset.retrieval_json ? Object.keys(editingPreset.retrieval_json).length : 0}</div>
                        <div class="font-semibold col-span-2 mt-2 text-gray-700 dark:text-gray-300">Knowledge</div>
            <div class="text-gray-500">Knowledge ID</div><div class="truncate" title={editingPreset.knowledge_id}>{editingPreset.knowledge_id || '—'}</div>
                      </div>
                    {:else}
                      <div class="text-[11px] text-gray-500">No preset found.</div>
                    {/if}
                  {/key}
                </div>
              {/if}
            </div>
          {/if}
        </form>
      {/if}
    {/if}
  {/if}
</div>

<!-- Removed custom @apply style to avoid build issues; utility classes inlined. -->
