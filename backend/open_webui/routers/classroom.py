import time
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from open_webui.env import CLASSROOM_MODE
from open_webui.utils.auth import (
    get_verified_user,
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
from open_webui.models.users import Users
from open_webui.models.files import Files
from open_webui.retrieval.loaders.main import Loader
from open_webui.routers.retrieval import save_docs_to_vector_db
from open_webui.utils.misc import calculate_sha256_string
from open_webui.constants import ERROR_MESSAGES
from langchain_core.documents import Document
from open_webui.utils.feature_flags import is_classroom_enabled
from open_webui.models.knowledge import Knowledges, KnowledgeForm
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.models.classroom import Course as CourseORM, CoursePreset as CoursePresetORM, Material as MaterialORM, Assignment as AssignmentORM, Submission as SubmissionORM
from open_webui.internal.db import get_db
from open_webui.routers.retrieval import process_file, ProcessFileForm
from open_webui.models.models import Models, ModelForm, ModelMeta, ModelParams
from open_webui.utils.models import get_all_models
from open_webui.utils.models import get_all_models


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
    code: Optional[str] = Field(None, max_length=64)
    term: Optional[str] = Field(None, max_length=64)
    schedule: Optional[str] = Field(None, max_length=256)
    instructors: Optional[List[str]] = None
    links: Optional[List[str]] = None
    youtube_embeds: Optional[List[str]] = Field(None, description="YouTube video URLs only")
    visibility: Optional[str] = Field(None, description="private|org|public")


class CourseCreate(CourseBase):
    # Require at least one uploaded document (file_id)
    doc_file_ids: List[str] = Field(..., min_length=1)
    # Model template/config
    model_id: str = Field(..., description="Base model ID to use")
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(0.4, ge=0, le=2)
    top_p: Optional[float] = Field(1.0, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(0.0, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(0.0, ge=-2, le=2)
    max_tokens: Optional[int] = Field(1024, ge=1, le=128000)
    tools_json: Optional[dict] = None
    retrieval_json: Optional[dict] = None
    safety_json: Optional[dict] = None


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
    meta_json: Optional[dict] = None




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
    include_admin = getattr(user, "role", None) == "admin"
    try:
        rows = Courses.list_for_user(user.id, include_admin=include_admin)     
        # Debug: also try getting ALL courses directly to see if any exist
        with get_db() as db:
            all_courses = db.query(CourseORM).all()
        return [
            Course(
                id=r.id,
                title=r.title,
                description=r.description,
                status=r.status,
                created_by=r.created_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
                meta_json=getattr(r, "meta_json", None),
            )
            for r in rows
        ]
    except Exception as e:
        print(f"[list_courses] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def _validate_youtube_urls(urls: Optional[List[str]]) -> Tuple[bool, Optional[str]]:
    if not urls:
        return True, None
    allowed_hosts = {"www.youtube.com", "youtube.com", "youtu.be", "www.youtu.be", "www.youtube-nocookie.com", "youtube-nocookie.com"}
    from urllib.parse import urlparse
    for u in urls:
        try:
            host = urlparse(u).hostname or ""
            if host.lower() not in allowed_hosts:
                return False, f"Invalid YouTube host: {host}"
        except Exception:
            return False, "Invalid YouTube URL"
    return True, None


@router.post("/courses", response_model=Course)
async def create_course(request: Request, form: CourseCreate, user=Depends(get_verified_user)):
    # Only admins/teachers can create. Reuse permission gate: admins ok; otherwise require classroom teacher capability later
    if getattr(user, "role", None) not in {"admin", "teacher"}:
        # non-admins must have teacher role flag in info/settings; lacking explicit teacher role in schema, deny for safety
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    # Validate inputs
    ok, err = _validate_youtube_urls(form.youtube_embeds)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT(err or "invalid YouTube link"))
    if not form.doc_file_ids or len(form.doc_file_ids) < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("at least one document is required"))

    # Validate model exists (check both Models table and available base models)
    available_models = await get_all_models(request, user=user)
    model_ids = {model["id"] for model in available_models}
    
    # Debug logging for model validation
    print(f"[CourseCreate] Available models: {list(model_ids)}")
    print(f"[CourseCreate] Requested model: {form.model_id}")
    print(f"[CourseCreate] Docker models in list: {[m for m in model_ids if 'ai/' in m or 'smollm' in m.lower()]}")
    
    if form.model_id not in model_ids:
        print(f"[CourseCreate] Model validation failed: {form.model_id} not in available models")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT(f"Model '{form.model_id}' not found in available models"))

    # Create course row (draft)
    meta = {
        "code": form.code,
        "term": form.term,
        "schedule": form.schedule,
        "instructors": form.instructors or [],
        "links": form.links or [],
        "videos": form.youtube_embeds or [],
        "visibility": form.visibility or "private",
    }
    course_row = Courses.insert(
        title=form.title,
        description=form.description,
        created_by=user.id,
        meta_json=meta,
    )

    # (Enrollment feature removed — no automatic enrollments are performed)

    # Create per-course knowledge base and add documents
    knowledge_name = f"{course_row.title.replace(' ', '_')}_know"
    kb = Knowledges.insert_new_knowledge(
        user.id,
        form_data=KnowledgeForm(
            name=knowledge_name,
            description=f"Knowledge base for course: {course_row.title}",
            data={"file_ids": []},
            access_control=None,
        ),
    )
    if not kb:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT("failed to create knowledge base"))

    # Attach each file id via existing pipeline
    for fid in form.doc_file_ids:
        # Validate file exists
        f = Files.get_file_by_id(fid)
        if not f:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT(f"invalid file id: {fid}"))
        # Use existing processing pipeline to index into KB collection
        try:
            process_file(request, ProcessFileForm(file_id=fid, collection_name=kb.id), user=user)
        except Exception as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT(str(e)))
        # Update KB data with file id
        data = kb.data or {}
        file_ids = set(data.get("file_ids", []))
        file_ids.add(fid)
        kb = Knowledges.update_knowledge_data_by_id(kb.id, {**data, "file_ids": list(file_ids)}) or kb

    # Create a model clone for the course using safe pipeline with knowledge assignment
    course_model_id = f"course/{course_row.id}"
    
    print(f"[CourseCreate] Creating course model {course_model_id} based on {form.model_id}")
    
    # Create model meta with knowledge assignment (same as manual model creation)
    model_meta = ModelMeta(
        profile_image_url="/static/favicon.png",
        description=f"AI Assistant for course: {course_row.title}",
        knowledge=[{
            "id": kb.id,
            "name": knowledge_name,
            "description": f"Knowledge base for course: {course_row.title}"
        }]
    )
    
    print(f"[CourseCreate] Model meta created with knowledge: {model_meta.knowledge}")
    
    mf = ModelForm(
        id=course_model_id,
        base_model_id=form.model_id,
        name=f"MifralBot",
        meta=model_meta,
        params=ModelParams.model_validate({
            "temperature": form.temperature,
            "top_p": form.top_p,
            "frequency_penalty": form.frequency_penalty,
            "presence_penalty": form.presence_penalty,
            "max_tokens": form.max_tokens,
            "system_prompt": form.system_prompt or "",
        }),
        access_control=None,
        is_active=True,
    )
    created_model = Models.insert_new_model(mf, user.id)
    if not created_model:
        print(f"[CourseCreate] Failed to create course model: {course_model_id}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT("failed to create course model"))
    
    print(f"[CourseCreate] Successfully created course model: {created_model.id}")

    # Save preset linking model and KB
    preset = CoursePresets.upsert(
        course_id=course_row.id,
        name="Default",
        is_default=True,
        provider=None,
        model_id=course_model_id,
        temperature=form.temperature,
        max_tokens=form.max_tokens,
        system_prompt_md=form.system_prompt,
        tools_json=form.tools_json,
        knowledge_id=kb.id,
        retrieval_json=form.retrieval_json,
        safety_json=form.safety_json,
    )
    
    print(f"[CourseCreate] Created preset linking model {course_model_id} to knowledge {kb.id}")

    # Return course payload
    return Course(
        id=course_row.id,
        title=course_row.title,
        description=course_row.description,
        status=course_row.status,
        created_by=course_row.created_by,
        created_at=course_row.created_at,
    updated_at=course_row.updated_at,
    meta_json=getattr(course_row, "meta_json", None),
    )


class CourseDetails(Course):
    preset: Optional[Preset] = None
    knowledge_id: Optional[str] = None
    knowledge_files: Optional[List[dict]] = None


@router.get("/courses/{course_id}", response_model=CourseDetails)
def get_course(course_id: str, user=Depends(get_verified_user)):
    row = Courses.get_by_id(course_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("course not found"))
    preset_row = CoursePresets.get_by_course_id(course_id)
    kb_id = preset_row.knowledge_id if preset_row else None
    files = []
    if kb_id:
        kb = Knowledges.get_knowledge_by_id(kb_id)
        if kb and kb.data:
            ids = kb.data.get("file_ids", [])
            files = [f.model_dump() if hasattr(f, "model_dump") else f for f in Files.get_file_metadatas_by_ids(ids)]
    base = Course(
        id=row.id,
        title=row.title,
        description=row.description,
        status=row.status,
        created_by=row.created_by,
        created_at=row.created_at,
    updated_at=row.updated_at,
    meta_json=getattr(row, "meta_json", None),
    )
    preset_payload = None
    if preset_row:
        preset_payload = Preset(
            id=preset_row.id,
            course_id=preset_row.course_id,
            created_at=preset_row.created_at,
            updated_at=preset_row.updated_at,
            name=preset_row.name,
            is_default=preset_row.is_default,
            provider=preset_row.provider,
            model_id=preset_row.model_id,
            temperature=preset_row.temperature,
            max_tokens=preset_row.max_tokens,
            system_prompt_md=preset_row.system_prompt_md,
            tools_json=preset_row.tools_json,
            retrieval_json=preset_row.retrieval_json,
            safety_json=preset_row.safety_json,
            knowledge_id=preset_row.knowledge_id,
        )
    return CourseDetails(**base.model_dump(), preset=preset_payload, knowledge_id=kb_id, knowledge_files=files)


@router.put("/courses/{course_id}", response_model=Course)
def update_course(course_id: str, form: CourseUpdate, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    # Fetch existing row
    existing = Courses.get_by_id(course_id)
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("course not found"))
    # Only update provided fields; preserve meta_json and created fields
    new_title = form.title if form.title is not None else existing.title
    new_desc = form.description if form.description is not None else existing.description
    new_status = form.status if form.status is not None else existing.status
    # Validate status
    if new_status not in {"draft", "active", "archived"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("invalid status"))
    # Apply updates directly via DB
    from open_webui.internal.db import get_db  # correct import for get_db
    from open_webui.models.classroom import Course  # correct import for Course ORM
    with get_db() as db:
        row = db.get(Course, course_id)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("course not found"))
        changed = False
        import time as _t
        if row.title != new_title:
            row.title = new_title; changed = True
        if row.description != new_desc:
            row.description = new_desc; changed = True
        if row.status != new_status:
            row.status = new_status; changed = True
        if changed:
            row.updated_at = int(_t.time())
        db.commit()
        db.refresh(row)
        return Course(
            id=row.id,
            title=row.title,
            description=row.description,
            status=row.status,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
            meta_json=getattr(row, "meta_json", None),
        )


@router.delete("/courses/{course_id}")
def delete_course(course_id: str, user=Depends(get_verified_user), _=Depends(requireCourseTeacher)):
    # Verify course exists
    course = Courses.get_by_id(course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("course not found"))

    # Load preset to find linked model/knowledge
    preset = CoursePresets.get_by_course_id(course_id)
    model_id = getattr(preset, "model_id", None) if preset else None
    knowledge_id = getattr(preset, "knowledge_id", None) if preset else None

    # Delete associated model (if any)
    if model_id:
        try:
            Models.delete_model_by_id(model_id)
        except Exception as e:
            # Log and continue; model removal failure should not block course deletion
            print(f"[delete_course] failed to delete model {model_id}: {e}")

    # Delete associated knowledge base (if any)
    if knowledge_id:
        try:
            # Remove vector DB collection for the knowledge base if present
            try:
                if VECTOR_DB_CLIENT.has_collection(collection_name=knowledge_id):
                    VECTOR_DB_CLIENT.delete_collection(collection_name=knowledge_id)
            except Exception:
                # Best-effort only
                pass
            Knowledges.delete_knowledge_by_id(knowledge_id)
        except Exception as e:
            print(f"[delete_course] failed to delete knowledge {knowledge_id}: {e}")

    # Remove per-course collection (materials) from vector DB
    try:
        collection_name = _course_collection_name(course_id)
        try:
            if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
        except Exception:
            pass
    except Exception:
        pass

    # Remove DB rows related to the course in a single transaction
    try:
        with get_db() as db:
            # Delete materials
            db.query(MaterialORM).filter_by(course_id=course_id).delete()

            # Delete course presets
            db.query(CoursePresetORM).filter_by(course_id=course_id).delete()

            # Delete assignments and related submissions
            assignment_rows = db.query(AssignmentORM).filter_by(course_id=course_id).all()
            assignment_ids = [a.id for a in assignment_rows]
            if assignment_ids:
                db.query(SubmissionORM).filter(SubmissionORM.assignment_id.in_(assignment_ids)).delete(synchronize_session=False)
            db.query(AssignmentORM).filter_by(course_id=course_id).delete()

            # # Delete enrollments
            # db.query(CourseEnrollmentORM).filter_by(course_id=course_id).delete()

            # Finally delete the course row itself
            db.query(CourseORM).filter_by(id=course_id).delete()

            db.commit()
    except Exception as e:
        print(f"[delete_course] database cleanup failed for course {course_id}: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT(str(e)))

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






# Preset
@router.get("/courses/{course_id}/preset", response_model=Optional[Preset])
def get_course_preset(course_id: str, user=Depends(get_verified_user)):
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
def get_course_preset_template(course_id: str, user=Depends(get_verified_user)):
    # Template endpoint: does not require course-specific teacher access so frontend can request 'new'
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
def list_materials(course_id: str, user=Depends(get_verified_user)):
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
def list_assignments(course_id: str, user=Depends(get_verified_user)):
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
    # Enrollment checks removed — all authenticated users may submit
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
async def chat_proxy(request: Request, course_id: str, req: ChatProxyRequest, user=Depends(get_verified_user)):
    # Only for active courses
    course = Courses.get_by_id(course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.DEFAULT("course not found"))
    if course.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT("course is not active"))

    preset = CoursePresets.get_by_course_id(course_id)
    if not preset or not preset.model_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT("preset not configured"))

    # Build OpenAI-compatible payload using preset
    payload = {
        "model": preset.model_id,
        "messages": [m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in req.messages],
        "stream": bool(req.stream),
        # attach metadata for downstream hooks (chat id could be bound by FE)
        "metadata": {
            "classroom_course_id": course_id,
            # turn on citations if retrieval_json asks for it
            "citations": bool((preset.retrieval_json or {}).get("return_citations", True)),
        },
    }

    # Apply model params from preset similar to OpenAI router
    params = {}
    if preset.temperature is not None:
        params["temperature"] = preset.temperature
    if preset.max_tokens is not None:
        params["max_tokens"] = preset.max_tokens

    from open_webui.utils.payload import apply_model_params_to_body_openai, apply_model_system_prompt_to_body
    if params:
        payload = apply_model_params_to_body_openai(params, payload)
    if preset.system_prompt_md:
        payload = apply_model_system_prompt_to_body(preset.system_prompt_md, payload, payload.get("metadata"), user)

    # Inject retrieval via metadata.files so existing middleware picks it up
    collection_name = _course_collection_name(course_id)
    payload.setdefault("files", [
        {
            "type": "collection",
            "id": preset.knowledge_id or collection_name,
            # modern path uses collection_names array
            "collection_names": [collection_name],
        }
    ])

    # Forward to existing OpenAI-compatible completion handler
    from open_webui.routers.openai import generate_chat_completion

    res = await generate_chat_completion(request, payload, user)

    # If streaming, the handler already returns StreamingResponse
    if isinstance(res, StreamingResponse):
        return res
    return res
