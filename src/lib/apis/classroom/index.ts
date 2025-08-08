import { WEBUI_BASE_URL } from '$lib/constants';
import type { Course, CoursePreset, Material, Assignment } from '$lib/types/course';

export const getClassroomToggle = async (token: string): Promise<{ enabled: boolean }> => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/admin/settings/classroom`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const listCourses = async (token: string): Promise<Course[]> => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const getCourse = async (token: string, courseId: string): Promise<Course> => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const getCoursePreset = async (token: string, courseId: string): Promise<CoursePreset | null> => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}/preset`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (res.status === 404) return null;
  if (!res.ok) throw await res.json();
  return res.json();
};

export const getCoursePresetTemplate = async (token: string, courseId: string): Promise<Partial<CoursePreset> & { retrieval_json?: any; safety_json?: any; tools_json?: any; name?: string; is_default?: boolean }> => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}/preset/template`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export type PresetUpsert = Partial<Pick<CoursePreset, 'provider' | 'model_id' | 'temperature' | 'max_tokens' | 'system_prompt_md' | 'tools_json' | 'knowledge_id'>> & {
  name?: string;
  is_default?: boolean;
  retrieval_json?: any;
  safety_json?: any;
};

export const upsertCoursePreset = async (token: string, courseId: string, draft: PresetUpsert): Promise<CoursePreset> => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}/preset`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) },
    body: JSON.stringify(draft)
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const previewCoursePreset = async (token: string, courseId: string, draft: PresetUpsert, messages: Array<{ role: string; content: string }> = []) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}/preset/preview`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) },
    body: JSON.stringify({ draft, messages })
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const setCoursePresetDefault = async (token: string, courseId: string) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}/preset/set-default`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const listMaterials = async (token: string, courseId: string): Promise<Material[]> => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}/materials`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const listAssignments = async (token: string, courseId: string): Promise<Assignment[]> => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}/assignments`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const createAssignment = async (
  token: string,
  courseId: string,
  body: { title: string; body_md?: string; due_at?: number; attachments_json?: any }
) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/courses/${courseId}/assignments`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const updateAssignment = async (
  token: string,
  assignmentId: string,
  body: { title: string; body_md?: string; due_at?: number; attachments_json?: any }
) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/assignments/${assignmentId}`, {
    method: 'PUT',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const deleteAssignment = async (token: string, assignmentId: string) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/assignments/${assignmentId}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const listSubmissions = async (token: string, assignmentId: string) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/assignments/${assignmentId}/submissions`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const createSubmission = async (
  token: string,
  assignmentId: string,
  body: { text?: string; files_json?: any }
) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/assignments/${assignmentId}/submissions`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const updateSubmission = async (
  token: string,
  submissionId: string,
  body: { text?: string; files_json?: any; status?: string; grade_json?: any }
) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/submissions/${submissionId}`, {
    method: 'PUT',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const deleteSubmission = async (token: string, submissionId: string) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/classroom/submissions/${submissionId}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};
