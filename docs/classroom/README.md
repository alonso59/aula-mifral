# Classroom Architecture & Developer Guide

## Quick Start

Follow these steps to try Classroom end-to-end using existing pipelines:

1) Enable the feature
  - Set environment variable CLASSROOM_MODE=true, or
  - As an admin, open Admin Settings → Classroom and toggle it on.

2) Upload documents
  - Use the existing file upload (top-right upload UI or Files API) to add at least one document.

3) Create a course (admin/teacher only)
  - Navigate to /classroom → Create Course.
  - Fill in Title, pick a Model, and select/upload ≥1 document; optional: code, term, schedule, links, YouTube.
  - Submit to create the Course, Knowledge Base (from your docs), and a per-course Model preset in one go.

4) View course details
  - After creation, you’ll be redirected to /classroom/{course_id}/overview showing course meta, model summary, and KB files.

RBAC: Only admins/teachers can create or edit courses; students can view. The backend enforces this.

## Virtual Classroom UI (two‑pane)

- Navigate to /classroom/{course_id} to see the two‑pane layout.
- Left pane: sticky “Virtual Classroom” navigation with sections: Overview, Materials, Topics, Tasks, Videos. Collapsible on small screens. Keyboard navigation supported.
- Right pane: the existing Chat panel remains fully functional; course preset badges appear when configured.
- Inactive class: a centered “Class Not Active” card is shown with an Activate Class CTA for teachers/admins.
- Videos: only YouTube host URLs are allowed and normalized to youtube‑nocookie embeds.

Welcome! This document explains how the Classroom feature is structured end-to-end so any external full‑stack developer can jump in quickly. It covers the frontend routes/components, backend APIs/models, feature flagging, data flow, and how everything links together.

## What is "Classroom"?
Classroom adds course-centric learning UX on top of Open WebUI: courses, materials, assignments, and submissions, plus a course assistant chat that runs with per‑course presets and retrieval.

- Admins can enable/disable the feature globally.
- Teachers manage courses and assign work.
- Students access content and submit assignments.

## High-level anatomy

- Feature flag: ENV `CLASSROOM_MODE` or DB key `app_settings.CLASSROOM_MODE`.
- Backend: FastAPI router `/api/classroom/*`, SQLAlchemy ORM tables for courses/materials/assignments/submissions, and a small admin settings router.
- Frontend: Svelte/SvelteKit routes under `/classroom` and additive panels in the main Chat UI (left navigation + right workspace panel).
- Retrieval: Course materials can be indexed into a per‑course collection for citations and grounded answers.

## Feature flagging

Two sources control availability:

1) Environment variable: `CLASSROOM_MODE` (true/false). Precedence over DB.
2) DB toggle: `app_settings` table row with key `CLASSROOM_MODE` and JSON value like `{ "enabled": true }`.

Code reference:
- Backend read helper: `backend/open_webui/utils/feature_flags.py:is_classroom_enabled()`
- Router guard: `backend/open_webui/routers/classroom.py` (dependency `require_feature_enabled` raises 404 when disabled).
- Admin endpoints: `backend/open_webui/routers/admin_settings.py` (GET/PUT `/api/admin/settings/classroom`).
- Frontend detection: `src/routes/(app)/+layout.svelte` probes `/api/classroom/courses` and sets `$classroomEnabled` store.

## Backend

### Routers
- `backend/open_webui/routers/classroom.py` — Main Classroom API. Key endpoints:
  - Courses (stubs for list/get/create/update/delete)
  - Enrollments (stubs)
  - Presets: get/upsert/template/preview/set-default
  - Materials: list/create (with optional doc ingestion + vector DB save), delete
  - Assignments: list/create/get/update/delete
  - Submissions: list/create/get/update/delete
  - Chat proxy: `/courses/{course_id}/chat/completions` (checks course active + preset configured; stubbed response)

- `backend/open_webui/routers/admin_settings.py` — Admin toggle for Classroom.
- Router wiring: `backend/open_webui/main.py` includes `/api/admin/settings` and `/api/classroom`.

### Models and DB schema
- File: `backend/open_webui/models/classroom.py`
  - ORM tables: `Course`, `CourseEnrollment`, `CoursePreset`, `Material`, `Assignment`, `Submission`.
  - Pydantic mirrors + table helpers for CRUD: `Courses`, `CoursePresets`, `Materials`, `Assignments`, `Submissions`.
- App settings: `backend/open_webui/models/settings.py` defines `app_settings` table and `AppSettings` accessors.

#### Relationships and typical flow
- A Course is created (status `draft` by default). Teachers/admins can enroll users as teachers or students.
- A CoursePreset (one per course currently) stores LLM provider/model/temperature/max_tokens, prompt, tools, and `knowledge_id` to bind retrieval to course content. Exactly one default preset is required to activate a course.
- Materials belong to a Course. For uploaded docs with `uri_or_blob_id`, the create endpoint can ingest, extract text via the configured loader, persist file hash, and index into a per‑course collection name `course-{course_id}`.
- Assignments belong to a Course; Submissions belong to an Assignment and a User.

#### Authorization helpers
- `requireCourseEnrollment(course_id)` and `requireCourseTeacher(course_id)` (imported in router) enforce that a user is enrolled or is a teacher/admin for protected actions. Admin bypass applies where appropriate.

### Migrations
- Look for Alembic migration that seeds `app_settings` with `CLASSROOM_MODE` when missing: `backend/open_webui/migrations/versions/*add_app_settings.py`.
- Classroom tables are defined via SQLAlchemy Base and created by migration or metadata sync in startup.

## Frontend

### Stores
- `src/lib/stores/classroom.ts` — `classroomEnabled` writable store used to show/hide Classroom links.
- `src/lib/stores/documentPanel.js` — visibility toggles for the left Classroom panel and the right Course Workspace panel in chat.

### API client
- `src/lib/apis/classroom/index.ts` — typed fetch helpers for all endpoints (courses, preset, materials, assignments, submissions, chat proxy).

### Routes and components
- Top-level route: `src/routes/(app)/classroom/+page.svelte` — placeholder course list.
- Per-course shell: `src/routes/(app)/classroom/[courseId]/+layout.svelte` with tabs, and child pages:
  - `overview`, `materials`, `assignments`, `chat`, `settings`.
- Chat integration: `src/lib/components/chat/Chat.svelte` includes Paneforge three‑pane layout with:
  - Left `VirtualClassroomPanel.svelte` (wraps existing `DocumentPanel`)
  - Center chat
  - Right `CourseWorkspacePanel.svelte` (tabs for Overview/Materials/Topics/Assignments/Videos)
  - Admin-only toggle buttons; non‑admins see both panels forced on.
- Admin Settings:
  - `src/lib/components/admin/Settings.svelte` exposes a Classroom tab (admin‑only) linking to `/admin/settings/classroom`.
  - `src/lib/components/admin/Settings/Classroom.svelte` screens non‑admins, toggles feature flag via `/api/admin/settings/classroom`, updates `$classroomEnabled`.
  - Route wrapper: `src/routes/(app)/admin/settings/classroom/+page.svelte`.

### Types
- `src/lib/types/course.ts` — `Course`, `CoursePreset`, `Material`, `Assignment` types used by the API client and UI.

## Data flow: end-to-end examples

1) Enable Classroom
- Admin opens Admin Settings → Classroom, flips toggle, saves → PUT `/api/admin/settings/classroom` → `app_settings.CLASSROOM_MODE={ enabled: true }` → frontend `$classroomEnabled` true → Sidebar shows Classroom link.

2) Create course preset and activate
- Teacher configures preset via `/courses/{course_id}/preset`.
- Must include `model_id` and `knowledge_id`; set as default (exactly one default allowed) → Course can be activated via `/courses/{course_id}/activate`.

3) Add materials and index
- Teacher uploads doc to Files API, then creates material with `kind='doc'` + `uri_or_blob_id`. Backend extracts text, computes SHA256, saves to vector DB with collection name `course-{course_id}`, and patches `meta_json.ingestion.status` to `done` or `error`.

4) Assignments and submissions
- Teacher creates assignment → students list and submit submissions; teachers/admins can list all, grade, or return; students can edit or delete while status is `submitted`.

## Dependencies and external services

- FastAPI + Pydantic + SQLAlchemy for API/ORM.
- Alembic for migrations.
- Svelte/SvelteKit for frontend.
- Paneforge for resizable panes in chat.
- Vector DB integration via existing retrieval pipeline `open_webui.routers.retrieval.save_docs_to_vector_db` and document loaders in `open_webui.retrieval.loaders.main.Loader`.
- Files storage via `open_webui.models.files.Files` and `open_webui.storage.provider.Storage`.
- Knowledge base entities via `open_webui.models.knowledge.Knowledges` (used to validate `knowledge_id`).

## Development notes and conventions

- Additive approach: New Classroom UI wraps existing components (e.g., left panel reuses `DocumentPanel` via `VirtualClassroomPanel.svelte`). We avoid breaking upstream code and keep a clean diff surface.
- Role rules in Chat: non‑admins always see both side panels; admin buttons can toggle visibility. Visibility is persisted in `localStorage` by `documentPanel.js`.
- Router guards: classroom router is always mounted, but returns 404 when feature is disabled. This lets the frontend probe availability without 401 noise.
- Per‑course vector collections keep names under 63 chars to satisfy common backends.

## How this was developed

1) Backend scaffolding: Created ORM models for Course, Enrollment, Preset, Material, Assignment, Submission. Added DAOs with minimal CRUD.
2) Feature flag: Implemented ENV+DB precedence with `is_classroom_enabled()`. Added admin settings router and UI to toggle.
3) Frontend wiring: Added `/classroom` routes, a small store to expose feature availability, and a chat three‑pane layout. Enforced non‑admin visibility rules.
4) Retrieval path: On material create with uploaded file, extracted text and saved to vector DB; recorded ingestion status in `meta_json`.
5) Preset lifecycle: Validations ensure a single default preset has both `model_id` and `knowledge_id` before course activation.

## Database relations (brief)

- courses (1) — (N) materials
- courses (1) — (N) assignments — (N) submissions
- courses (1) — (1) course_presets (current semantics; API supports future multi‑preset)
- courses (1) — (N) course_enrollments (teacher or student)

Key columns (selection):
- courses: id, title, description, status, created_by, created_at, updated_at
- course_presets: id, course_id, provider, model_id, temperature, max_tokens, system_prompt_md, tools_json, retrieval_json, safety_json, knowledge_id, is_default
- materials: id, course_id, kind, title, uri_or_blob_id, meta_json
- assignments: id, course_id, title, body_md, due_at, attachments_json
- submissions: id, assignment_id, user_id, text, files_json, status, grade_json

## Try it locally

- Ensure migrations are applied and the app runs (see project README for setup). To persist the DB in Docker, `docker-compose.yaml` mounts a named volume to `/app/backend/data`.
- Set `CLASSROOM_MODE=true` in env for force‑enable or use Admin Settings → Classroom to toggle at runtime.
- Create a course preset with a valid `knowledge_id` + `model_id` and set it default; activate the course.
- Upload a file via Files, then create a material pointing to that file to index into the course collection.

## Next steps (roadmap hints)

- Courses/Enrollments CRUD UI in Admin → Classroom and in `/classroom` pages.
- Wire `CourseWorkspacePanel` tabs to real data: show materials, assignments, and progress.
- Implement chat proxy forwarding using the course preset (provider/model/params/tools/safety) and retrieval from the course collection.
- Add grading workflows and basic analytics.

If you have questions or improvements, feel free to open an issue or PR.
