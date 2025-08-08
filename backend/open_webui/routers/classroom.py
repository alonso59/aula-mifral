import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from open_webui.env import CLASSROOM_MODE
from open_webui.utils.auth import (
    get_verified_user,
    requireCourseEnrollment,
    requireCourseTeacher,
)
from open_webui.models.classroom import (
    Materials,
    MaterialModel,
    CoursePresets,
    Courses,
    Assignments,
    AssignmentModel,
    Submissions,
    SubmissionModel,
)
from open_webui.models.files import Files
from open_webui.retrieval.loaders.main import Loader
from open_webui.routers.retrieval import save_docs_to_vector_db
from open_webui.utils.misc import calculate_sha256_string
from open_webui.constants import ERROR_MESSAGES
from langchain_core.documents import Document
from open_webui.utils.feature_flags import is_classroom_enabled
from open_webui.models.knowledge import Knowledges


def require_feature_enabled():
    # ENV has precedence, but allow DB-backed toggle
    if not (CLASSROOM_MODE or is_classroom_enabled()):
        # Hide feature when disabled to avoid noisy 401s
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not Found")


router = APIRouter(dependencies=[Depends(require_feature_enabled)])


# ---------------
# Schemas
# ---------------


class CourseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    description: Optional[str] = None
    status: Optional[str] = Field(None, description="draft|active|archived")


class Course(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str = "draft"
    created_by: str
    created_at: int
    updated_at: Optional[int] = None


class EnrollmentCreate(BaseModel):
    user_id: str
    is_teacher: bool = False


class Enrollment(BaseModel):
    id: str
    user_id: str
    is_teacher: bool
    created_at: int


class PresetUpsert(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = False
    provider: Optional[str] = None
    model_id: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    system_prompt_md: Optional[str] = None
    tools_json: Optional[dict] = None
    retrieval_json: Optional[dict] = None
    safety_json: Optional[dict] = None
    knowledge_id: Optional[str] = None


class Preset(BaseModel):
    id: str
    course_id: str
    created_at: int
    updated_at: Optional[int] = None
    name: Optional[str] = None
    is_default: bool = False
    provider: Optional[str] = None
    model_id: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt_md: Optional[str] = None
    tools_json: Optional[dict] = None
    retrieval_json: Optional[dict] = None
    safety_json: Optional[dict] = None
    knowledge_id: Optional[str] = None


class MaterialCreate(BaseModel):
    kind: str = Field(..., description="doc|link|video")
    title: str = Field(..., min_length=1)
    uri_or_blob_id: Optional[str] = None
    meta_json: Optional[dict] = None


class Material(BaseModel):
    id: str
    course_id: str
    kind: str
    title: str
    uri_or_blob_id: Optional[str] = None
    meta_json: Optional[dict] = None
    created_at: int


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1)
    body_md: Optional[str] = None
    due_at: Optional[int] = None
    attachments_json: Optional[dict] = None


class Assignment(BaseModel):
    id: str
    course_id: str
    title: str
    body_md: Optional[str] = None
    due_at: Optional[int] = None
    attachments_json: Optional[dict] = None
    created_at: int


class SubmissionCreate(BaseModel):
    text: Optional[str] = None
    files_json: Optional[dict] = None


class Submission(BaseModel):
    id: str
    assignment_id: str
    user_id: str
    text: Optional[str]
    files_json: Optional[dict]
    submitted_at: int
    status: str = "submitted"
    grade_json: Optional[dict] = None


class ChatProxyMessage(BaseModel):
    role: str
    content: str


class ChatProxyRequest(BaseModel):
    messages: List[ChatProxyMessage]
    stream: Optional[bool] = False


# ---------------
# Endpoints — Stubs
# ---------------


@router.get("/courses", response_model=List[Course])
def list_courses(user=Depends(get_verified_user)):
    return []


@router.post("/courses", response_model=Course)
def create_course(form: CourseCreate, user=Depends(get_verified_user)):
    now = int(time.time())
    return Course(
        id="stub",
        title=form.title,
        description=form.description,
        status="draft",
        created_by=user.id,
        created_at=now,
        updated_at=now,
    )


@router.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseEnrollment)):
    return Course(
        id=course_id,
        title="stub",
        description=None,
        status="draft",
        created_by=user.id,
        created_at=0,
    )


@router.put("/courses/{course_id}", response_model=Course)
def update_course(course_id: str, form: CourseUpdate, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    now = int(time.time())
    return Course(
        id=course_id,
        title=form.title or "stub",
        description=form.description,
        status=form.status or "draft",
        created_by=user.id,
        created_at=now,
        updated_at=now,
    )


@router.delete("/courses/{course_id}")
def delete_course(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    return {"ok": True}


@router.post("/courses/{course_id}/activate")
def activate_course(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    # Phase 4B: Validate exactly one default preset exists and has both model_id & knowledge_id
    presets = CoursePresets.list_by_course_id(course_id)
    if not presets:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("no presets found; configure a preset before activation"))

    default_presets = [p for p in presets if bool(p.is_default)]
    if len(default_presets) != 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("exactly one default preset is required for activation"),
        )

    preset = default_presets[0]
    if not (preset.model_id and preset.knowledge_id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("default preset must include model_id and knowledge_id"),
        )

    kb = Knowledges.get_knowledge_by_id(preset.knowledge_id)
    if not kb:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("invalid knowledge_id on preset"))

    updated = Courses.update_status(course_id, "active")
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("course not found"))
    return {"ok": True, "status": updated.status}


# Enrollments
@router.get("/courses/{course_id}/enrollments", response_model=List[Enrollment])
def list_enrollments(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    return []


@router.post("/courses/{course_id}/enrollments", response_model=Enrollment)
def add_enrollment(course_id: str, form: EnrollmentCreate, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    return Enrollment(id="stub", user_id=form.user_id, is_teacher=form.is_teacher, created_at=int(time.time()))


@router.delete("/courses/{course_id}/enrollments/{user_id}")
def remove_enrollment(course_id: str, user_id: str, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    return {"ok": True}


# Preset
@router.get("/courses/{course_id}/preset", response_model=Optional[Preset])
def get_course_preset(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseEnrollment)):
    row = CoursePresets.get_by_course_id(course_id)
    if not row:
        return None
    return Preset(
        id=row.id,
        course_id=row.course_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    name=row.name,
    is_default=row.is_default,
        provider=row.provider,
        model_id=row.model_id,
        temperature=row.temperature,
        max_tokens=row.max_tokens,
        system_prompt_md=row.system_prompt_md,
        tools_json=row.tools_json,
    retrieval_json=row.retrieval_json,
    safety_json=row.safety_json,
        knowledge_id=row.knowledge_id,
    )


@router.put("/courses/{course_id}/preset", response_model=Preset)
@router.post("/courses/{course_id}/preset", response_model=Preset)
def upsert_course_preset(course_id: str, form: PresetUpsert, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    # Validate knowledge_id if provided
    if form.knowledge_id:
        kb = Knowledges.get_knowledge_by_id(form.knowledge_id)
        if not kb:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("invalid knowledge_id"))

    # Enforce default rules: cannot set is_default=true unless knowledge_id & model_id present
    existing = CoursePresets.get_by_course_id(course_id)
    effective_model_id = form.model_id or (existing.model_id if existing else None)
    effective_knowledge_id = form.knowledge_id or (existing.knowledge_id if existing else None)
    if (form.is_default or False) and (not effective_model_id or not effective_knowledge_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("model_id and knowledge_id required to set default"))

    row = CoursePresets.upsert(
        course_id=course_id,
        name=form.name,
        is_default=form.is_default,
        provider=form.provider,
        model_id=form.model_id,
        temperature=form.temperature,
        max_tokens=form.max_tokens,
        system_prompt_md=form.system_prompt_md,
        tools_json=form.tools_json,
        knowledge_id=form.knowledge_id,
        retrieval_json=form.retrieval_json,
        safety_json=form.safety_json,
    )
    return Preset(
        id=row.id,
        course_id=row.course_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        name=row.name,
        is_default=row.is_default,
        provider=row.provider,
        model_id=row.model_id,
        temperature=row.temperature,
        max_tokens=row.max_tokens,
        system_prompt_md=row.system_prompt_md,
        tools_json=row.tools_json,
        retrieval_json=row.retrieval_json,
        safety_json=row.safety_json,
        knowledge_id=row.knowledge_id,
    )


# Preset template for Study & Learn builder
@router.get("/courses/{course_id}/preset/template")
def get_course_preset_template(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    # We don't need course metadata for now; template uses placeholder
    template_prompt = (
        "## Role\n"
        "You are the Study & Learn tutor for {{course_title}}.\n\n"
        "## Priorities\n"
        "1) Teach step-by-step; check understanding briefly before final answers.\n"
        "2) Prefer course materials; cite filenames/sections when used.\n"
        "3) Encourage metacognition; suggest a short \"try yourself\" item.\n\n"
        "## Boundaries\n"
        "- Do not reveal answer keys or full solutions for graded tasks unless allowed.\n"
        "- If outside course scope, say so and summarize briefly.\n\n"
        "## Formatting\n"
        "- Use concise bullets for steps.\n"
        "- End with a short \"Check Yourself\" question.\n"
    )
    return {
        "name": "Study & Learn",
        "is_default": False,
        "provider": None,
        "model_id": None,
        "temperature": 0.4,
        "max_tokens": 1024,
        "system_prompt_md": template_prompt,
        "tools_json": {"enabled": ["citations"], "disabled": ["web_browse", "code_exec"]},
        "retrieval_json": {"top_k": 6, "max_context_tokens": 6000, "return_citations": True},
        "safety_json": None,
        "knowledge_id": None,
    }


class PresetPreviewRequest(BaseModel):
    draft: PresetUpsert
    messages: List[ChatProxyMessage] = []


@router.post("/courses/{course_id}/preset/preview")
def preview_course_preset(course_id: str, body: PresetPreviewRequest, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    # Dry run: don't persist; don't hit external LLM here (stub)
    draft = body.draft
    citations_enabled = bool((draft.retrieval_json or {}).get("return_citations", True))
    return {
        "preview": True,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "[Preview] Study & Learn response would appear here.",
                },
                "citations": [] if citations_enabled else None,
            }
        ],
        "preset": {
            "provider": draft.provider,
            "model_id": draft.model_id,
            "temperature": draft.temperature or 0.4,
            "max_tokens": draft.max_tokens or 1024,
            "retrieval_json": draft.retrieval_json or {"top_k": 6, "max_context_tokens": 6000, "return_citations": True},
            "tools_json": draft.tools_json or {"enabled": ["citations"], "disabled": ["web_browse", "code_exec"]},
        },
    }


@router.post("/courses/{course_id}/preset/set-default")
def set_course_preset_default(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    row = CoursePresets.get_by_course_id(course_id)
    if not row:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("preset not found"))
    # Enforce rule: model_id & knowledge_id required
    if not (row.model_id and row.knowledge_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("model_id and knowledge_id required to set default"))

    # Unset others and set this one as default (single-row semantics currently)
    # With single-row per course, just toggle flag
    CoursePresets.upsert(course_id=course_id, is_default=True)
    return {"ok": True}


# Materials
def _course_collection_name(course_id: str) -> str:
    # Keep short, vector dbs like Chroma may limit to 63 chars
    return f"course-{course_id}"[:63]


@router.get("/courses/{course_id}/materials", response_model=List[Material])
def list_materials(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseEnrollment)):
    rows = Materials.list_by_course(course_id)
    return [
        Material(
            id=r.id,
            course_id=r.course_id,
            kind=r.kind,
            title=r.title,
            uri_or_blob_id=r.uri_or_blob_id,
            meta_json=r.meta_json,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/courses/{course_id}/materials", response_model=Material)
def create_material(
    request: Request,
    course_id: str,
    form: MaterialCreate,
    user=Depends(get_verified_user),
    _=Depends(requireCourseTeacher),
):
    # Create the DB row first with ingestion status (queued if doc with file)
    meta = form.meta_json or {}
    if form.kind.lower() == "doc" and form.uri_or_blob_id:
        meta = {
            **meta,
            "ingestion": {
                "status": "queued",
                "started_at": int(time.time()),
            },
        }

    row = Materials.insert(
        course_id=course_id,
        kind=form.kind,
        title=form.title,
        uri_or_blob_id=form.uri_or_blob_id,
        meta_json=meta,
    )

    # If it's a doc backed by an uploaded file, index it into per-course collection
    if row and form.kind.lower() == "doc" and form.uri_or_blob_id:
        try:
            file = Files.get_file_by_id(form.uri_or_blob_id)
            if not file:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid file id")

            # Build docs from file (uploaded docs only). No web/youtube ingestion here.
            if file.path:
                file_path = file.path
                from open_webui.storage.provider import Storage

                file_path = Storage.get_file(file_path)
                loader = Loader(
                    engine=request.app.state.config.CONTENT_EXTRACTION_ENGINE,
                    DATALAB_MARKER_API_KEY=request.app.state.config.DATALAB_MARKER_API_KEY,
                    DATALAB_MARKER_LANGS=request.app.state.config.DATALAB_MARKER_LANGS,
                    DATALAB_MARKER_SKIP_CACHE=request.app.state.config.DATALAB_MARKER_SKIP_CACHE,
                    DATALAB_MARKER_FORCE_OCR=request.app.state.config.DATALAB_MARKER_FORCE_OCR,
                    DATALAB_MARKER_PAGINATE=request.app.state.config.DATALAB_MARKER_PAGINATE,
                    DATALAB_MARKER_STRIP_EXISTING_OCR=request.app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR,
                    DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION=request.app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
                    DATALAB_MARKER_USE_LLM=request.app.state.config.DATALAB_MARKER_USE_LLM,
                    DATALAB_MARKER_OUTPUT_FORMAT=request.app.state.config.DATALAB_MARKER_OUTPUT_FORMAT,
                    EXTERNAL_DOCUMENT_LOADER_URL=request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
                    EXTERNAL_DOCUMENT_LOADER_API_KEY=request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
                    TIKA_SERVER_URL=request.app.state.config.TIKA_SERVER_URL,
                    DOCLING_SERVER_URL=request.app.state.config.DOCLING_SERVER_URL,
                    DOCLING_PARAMS={
                        "ocr_engine": request.app.state.config.DOCLING_OCR_ENGINE,
                        "ocr_lang": request.app.state.config.DOCLING_OCR_LANG,
                        "do_picture_description": request.app.state.config.DOCLING_DO_PICTURE_DESCRIPTION,
                        "picture_description_mode": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_MODE,
                        "picture_description_local": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_LOCAL,
                        "picture_description_api": request.app.state.config.DOCLING_PICTURE_DESCRIPTION_API,
                    },
                    PDF_EXTRACT_IMAGES=request.app.state.config.PDF_EXTRACT_IMAGES,
                    DOCUMENT_INTELLIGENCE_ENDPOINT=request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                    DOCUMENT_INTELLIGENCE_KEY=request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
                    MISTRAL_OCR_API_KEY=request.app.state.config.MISTRAL_OCR_API_KEY,
                )
                content_type = (file.meta or {}).get("content_type") or "application/octet-stream"
                docs = loader.load(file.filename, content_type, file_path)
                docs = [
                    Document(
                        page_content=doc.page_content,
                        metadata={
                            **doc.metadata,
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                            "course_id": course_id,
                            "material_id": row.id,
                        },
                    )
                    for doc in docs
                ]
            else:
                text = (file.data or {}).get("content", "")
                docs = [
                    Document(
                        page_content=text,
                        metadata={
                            **(file.meta or {}),
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                            "course_id": course_id,
                            "material_id": row.id,
                        },
                    )
                ]

            text_content = " ".join([d.page_content for d in docs])
            file_hash = calculate_sha256_string(text_content)
            Files.update_file_hash_by_id(file.id, file_hash)
            Files.update_file_data_by_id(file.id, {"content": text_content})

            collection_name = _course_collection_name(course_id)
            save_docs_to_vector_db(
                request,
                docs=docs,
                collection_name=collection_name,
                metadata={
                    "file_id": file.id,
                    "name": file.filename,
                    "hash": file_hash,
                    "course_id": course_id,
                    "material_id": row.id,
                },
                add=True,
                user=user,
            )

            # Mark ingestion done
            Materials.update_meta(
                row.id,
                {
                    "ingestion": {
                        "status": "done",
                        "started_at": (meta.get("ingestion", {}) or {}).get("started_at", int(time.time())),
                        "completed_at": int(time.time()),
                        "collection": collection_name,
                    }
                },
            )
        except Exception as e:
            Materials.update_meta(
                row.id,
                {
                    "ingestion": {
                        "status": "error",
                        "error": str(e),
                        "completed_at": int(time.time()),
                    }
                },
            )
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT(str(e)))

    if not row:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT("material not created"))

    return Material(
        id=row.id,
        course_id=row.course_id,
        kind=row.kind,
        title=row.title,
        uri_or_blob_id=row.uri_or_blob_id,
        meta_json=row.meta_json,
        created_at=row.created_at,
    )


@router.delete("/courses/{course_id}/materials/{material_id}")
def delete_material(course_id: str, material_id: str, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    return {"ok": True}


# Assignments
@router.get("/courses/{course_id}/assignments", response_model=List[Assignment])
def list_assignments(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseEnrollment)):
    rows: List[AssignmentModel] = Assignments.list_by_course(course_id)
    return [
        Assignment(
            id=r.id,
            course_id=r.course_id,
            title=r.title,
            body_md=r.body_md,
            due_at=r.due_at,
            attachments_json=r.attachments_json,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/courses/{course_id}/assignments", response_model=Assignment)
def create_assignment(course_id: str, form: AssignmentCreate, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    row = Assignments.insert(
        course_id=course_id,
        title=form.title,
        body_md=form.body_md,
        due_at=form.due_at,
        attachments_json=form.attachments_json,
    )
    return Assignment(
        id=row.id,
        course_id=row.course_id,
        title=row.title,
        body_md=row.body_md,
        due_at=row.due_at,
        attachments_json=row.attachments_json,
        created_at=row.created_at,
    )


@router.get("/assignments/{assignment_id}", response_model=Assignment)
def get_assignment(assignment_id: str, user=Depends(get_verified_user)):
    row = Assignments.get_by_id(assignment_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    return Assignment(
        id=row.id,
        course_id=row.course_id,
        title=row.title,
        body_md=row.body_md,
        due_at=row.due_at,
        attachments_json=row.attachments_json,
        created_at=row.created_at,
    )


@router.put("/assignments/{assignment_id}", response_model=Assignment)
def update_assignment(assignment_id: str, form: AssignmentCreate, user=Depends(get_verified_user)):
    # Require teacher/admin in the related course
    cur = Assignments.get_by_id(assignment_id)
    if not cur:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    requireCourseTeacher(cur.course_id)(user=user)
    row = Assignments.update(
        assignment_id,
        title=form.title,
        body_md=form.body_md,
        due_at=form.due_at,
        attachments_json=form.attachments_json,
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    return Assignment(
        id=row.id,
        course_id=row.course_id,
        title=row.title,
        body_md=row.body_md,
        due_at=row.due_at,
        attachments_json=row.attachments_json,
        created_at=row.created_at,
    )


@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: str, user=Depends(get_verified_user)):
    cur = Assignments.get_by_id(assignment_id)
    if not cur:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    requireCourseTeacher(cur.course_id)(user=user)
    ok = Assignments.delete(assignment_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    return {"ok": True}


# Submissions
@router.get("/assignments/{assignment_id}/submissions", response_model=List[Submission])
def list_submissions(assignment_id: str, user=Depends(get_verified_user)):
    # Teachers/Admins see all, students see their own
    if getattr(user, "role", None) == "admin":
        rows = Submissions.list_by_assignment(assignment_id)
    else:
        # Check if user is a teacher in the course of the assignment
        a = Assignments.get_by_id(assignment_id)
        if not a:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
        try:
            requireCourseTeacher(a.course_id)(user=user)
            rows = Submissions.list_by_assignment(assignment_id)
        except HTTPException:
            rows = Submissions.list_by_assignment_and_user(assignment_id, user.id)

    return [
        Submission(
            id=r.id,
            assignment_id=r.assignment_id,
            user_id=r.user_id,
            text=r.text,
            files_json=r.files_json,
            submitted_at=r.submitted_at,
            status=r.status,
            grade_json=r.grade_json,
        )
        for r in rows
    ]


@router.post("/assignments/{assignment_id}/submissions", response_model=Submission)
def create_submission(assignment_id: str, form: SubmissionCreate, user=Depends(get_verified_user)):
    a = Assignments.get_by_id(assignment_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    # Enrolled users can submit
    requireCourseEnrollment(a.course_id)(user=user)
    row = Submissions.insert(
        assignment_id=assignment_id,
        user_id=user.id,
        text=form.text,
        files_json=form.files_json,
    )
    return Submission(
        id=row.id,
        assignment_id=row.assignment_id,
        user_id=row.user_id,
        text=row.text,
        files_json=row.files_json,
        submitted_at=row.submitted_at,
        status=row.status,
        grade_json=row.grade_json,
    )


@router.get("/submissions/{submission_id}", response_model=Submission)
def get_submission(submission_id: str, user=Depends(get_verified_user)):
    row = Submissions.get_by_id(submission_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("submission not found"))
    # Authorization: student can read own; teachers/admins in course can read all
    a = Assignments.get_by_id(row.assignment_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    try:
        requireCourseTeacher(a.course_id)(user=user)
    except HTTPException:
        if row.user_id != user.id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)
    return Submission(
        id=row.id,
        assignment_id=row.assignment_id,
        user_id=row.user_id,
        text=row.text,
        files_json=row.files_json,
        submitted_at=row.submitted_at,
        status=row.status,
        grade_json=row.grade_json,
    )


class SubmissionUpdate(BaseModel):
    text: Optional[str] = None
    files_json: Optional[dict] = None
    status: Optional[str] = Field(None, description="submitted|returned")
    grade_json: Optional[dict] = None


@router.put("/submissions/{submission_id}", response_model=Submission)
def update_submission(submission_id: str, form: SubmissionUpdate, user=Depends(get_verified_user)):
    row = Submissions.get_by_id(submission_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("submission not found"))
    a = Assignments.get_by_id(row.assignment_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    # Student can edit their own content (text/files) while status is submitted; teachers/admins can update status/grade
    try:
        requireCourseTeacher(a.course_id)(user=user)
        # Teacher/Admin path
        updated = Submissions.update(
            submission_id,
            text=form.text,
            files_json=form.files_json,
            status=form.status,
            grade_json=form.grade_json,
        )
    except HTTPException:
        # Student path
        if row.user_id != user.id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)
        # Students can't change status or grade
        updated = Submissions.update(
            submission_id,
            text=form.text,
            files_json=form.files_json,
        )
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("submission not found"))
    return Submission(
        id=updated.id,
        assignment_id=updated.assignment_id,
        user_id=updated.user_id,
        text=updated.text,
        files_json=updated.files_json,
        submitted_at=updated.submitted_at,
        status=updated.status,
        grade_json=updated.grade_json,
    )


@router.delete("/submissions/{submission_id}")
def delete_submission(submission_id: str, user=Depends(get_verified_user)):
    row = Submissions.get_by_id(submission_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("submission not found"))
    a = Assignments.get_by_id(row.assignment_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("assignment not found"))
    # Teacher/Admin can delete; student can delete own while submitted
    try:
        requireCourseTeacher(a.course_id)(user=user)
        ok = Submissions.delete(submission_id)
    except HTTPException:
        if row.user_id != user.id or row.status != "submitted":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)
        ok = Submissions.delete(submission_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("submission not found"))
    return {"ok": True}


# Chat proxy (OpenAI-compatible completion style stub)
@router.post("/courses/{course_id}/chat/completions")
def chat_proxy(course_id: str, req: ChatProxyRequest, user=Depends(get_verified_user), _=Depends(requireCourseEnrollment)):
    # Block unless active
    course = Courses.get_by_id(course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("course not found"))
    if course.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT("course is not active"))

    preset = CoursePresets.get_by_course_id(course_id)
    if not preset:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("preset not configured"))

    # Stubbed completion; forwarding will be implemented later
    return {
        "id": "stub",
        "object": "chat.completion",
        "choices": [],
        "preset": {
            "provider": preset.provider,
            "model_id": preset.model_id,
            "temperature": preset.temperature,
            "max_tokens": preset.max_tokens,
        },
    }
