export type Course = {
  id: string;
  title: string;
  description?: string | null;
  status: 'draft' | 'active' | 'archived';
  created_by: string;
  created_at: number;
  updated_at?: number | null;
  meta_json?: Record<string, any> | null;
};

export type CoursePreset = {
  id: string;
  course_id: string;
  name?: string | null;
  is_default?: boolean;
  provider?: string | null;
  model_id?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
  system_prompt_md?: string | null;
  tools_json?: Record<string, any> | null;
  retrieval_json?: Record<string, any> | null;
  safety_json?: Record<string, any> | null;
  knowledge_id?: string | null;
  created_at: number;
  updated_at?: number | null;
};

export type Material = {
  id: string;
  course_id: string;
  kind: 'doc' | 'link' | 'video' | string;
  title: string;
  uri_or_blob_id?: string | null;
  meta_json?: Record<string, any> | null;
  created_at: number;
};

export type Assignment = {
  id: string;
  course_id: string;
  title: string;
  body_md?: string | null;
  due_at?: number | null;
  attachments_json?: Record<string, any> | null;
  created_at: number;
};
