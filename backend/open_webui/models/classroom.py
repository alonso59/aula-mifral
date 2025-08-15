import time
import uuid
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Float, Integer, JSON, String, Text

from open_webui.internal.db import Base, get_db


####################
# ORM models (Classroom)
####################


class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="draft")
    created_by = Column(String, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=True)
    # Additional metadata for compatibility without breaking schema
    # Stores: code, term, schedule, instructors (list), links (list), videos (list), visibility
    meta_json = Column(JSON, nullable=True)


# class CourseEnrollment(Base):
#     __tablename__ = "course_enrollments"

#     id = Column(String, primary_key=True)
#     course_id = Column(String, nullable=False)
#     user_id = Column(String, nullable=False)
#     is_teacher = Column(Boolean, nullable=False, default=False)
#     created_at = Column(BigInteger, nullable=False)


class CoursePreset(Base):
    __tablename__ = "course_presets"

    id = Column(String, primary_key=True)
    course_id = Column(String, nullable=False)
    name = Column(String, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    provider = Column(String, nullable=True)
    model_id = Column(String, nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    system_prompt_md = Column(Text, nullable=True)
    tools_json = Column(JSON, nullable=True)
    knowledge_id = Column(String, nullable=True)
    retrieval_json = Column(JSON, nullable=True)
    safety_json = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=True)


class Material(Base):
    __tablename__ = "materials"

    id = Column(String, primary_key=True)
    course_id = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    title = Column(Text, nullable=False)
    uri_or_blob_id = Column(Text, nullable=True)
    meta_json = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String, primary_key=True)
    course_id = Column(String, nullable=False)
    title = Column(Text, nullable=False)
    body_md = Column(Text, nullable=True)
    due_at = Column(BigInteger, nullable=True)
    attachments_json = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True)
    assignment_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    text = Column(Text, nullable=True)
    files_json = Column(JSON, nullable=True)
    submitted_at = Column(BigInteger, nullable=False)
    status = Column(String, nullable=False, default="submitted")
    grade_json = Column(JSON, nullable=True)


####################
# Pydantic mirrors (minimal)
####################


class MaterialModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    kind: str
    title: str
    uri_or_blob_id: Optional[str] = None
    meta_json: Optional[dict] = None
    created_at: int


####################
# Data access helpers
####################


class MaterialsTable:
    def insert(
        self,
        *,
        course_id: str,
        kind: str,
        title: str,
        uri_or_blob_id: Optional[str] = None,
        meta_json: Optional[dict] = None,
    ) -> Optional[MaterialModel]:
        with get_db() as db:
            now = int(time.time())
            mat = Material(
                id=str(uuid.uuid4()),
                course_id=course_id,
                kind=kind,
                title=title,
                uri_or_blob_id=uri_or_blob_id,
                meta_json=meta_json or {},
                created_at=now,
            )
            db.add(mat)
            db.commit()
            db.refresh(mat)
            return MaterialModel.model_validate(mat)

    def update_meta(self, material_id: str, patch: dict) -> Optional[MaterialModel]:
        with get_db() as db:
            mat = db.get(Material, material_id)
            if not mat:
                return None
            current = mat.meta_json or {}
            # shallow merge
            merged = {**current, **patch}
            mat.meta_json = merged
            db.commit()
            db.refresh(mat)
            return MaterialModel.model_validate(mat)

    def get_by_id(self, material_id: str) -> Optional[MaterialModel]:
        with get_db() as db:
            mat = db.get(Material, material_id)
            return MaterialModel.model_validate(mat) if mat else None

    def list_by_course(self, course_id: str) -> List[MaterialModel]:
        with get_db() as db:
            rows = db.query(Material).filter_by(course_id=course_id).all()
            return [MaterialModel.model_validate(r) for r in rows]


Materials = MaterialsTable()


class CoursePresetModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    name: Optional[str] = None
    is_default: bool = False
    provider: Optional[str] = None
    model_id: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt_md: Optional[str] = None
    tools_json: Optional[dict] = None
    knowledge_id: Optional[str] = None
    retrieval_json: Optional[dict] = None
    safety_json: Optional[dict] = None
    created_at: int
    updated_at: Optional[int] = None


class CoursePresetsTable:
    def get_by_course_id(self, course_id: str) -> Optional[CoursePresetModel]:
        with get_db() as db:
            row = db.query(CoursePreset).filter_by(course_id=course_id).first()
            return CoursePresetModel.model_validate(row) if row else None

    def list_by_course_id(self, course_id: str) -> List[CoursePresetModel]:
        """Return all presets for the given course.
        Note: Current semantics generally use a single row per course, but this
        list supports future multi-preset scenarios (e.g., multiple named presets).
        """
        with get_db() as db:
            rows = db.query(CoursePreset).filter_by(course_id=course_id).all()
            return [CoursePresetModel.model_validate(r) for r in rows]

    def upsert(
        self,
        *,
        course_id: str,
        name: Optional[str] = None,
        is_default: Optional[bool] = None,
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt_md: Optional[str] = None,
        tools_json: Optional[dict] = None,
        knowledge_id: Optional[str] = None,
        retrieval_json: Optional[dict] = None,
        safety_json: Optional[dict] = None,
    ) -> CoursePresetModel:
        with get_db() as db:
            existing = db.query(CoursePreset).filter_by(course_id=course_id).first()
            now = int(time.time())
            if existing:
                if name is not None:
                    existing.name = name
                if is_default is not None:
                    existing.is_default = bool(is_default)
                if provider is not None:
                    existing.provider = provider
                if model_id is not None:
                    existing.model_id = model_id
                if temperature is not None:
                    existing.temperature = temperature
                if max_tokens is not None:
                    existing.max_tokens = max_tokens
                if system_prompt_md is not None:
                    existing.system_prompt_md = system_prompt_md
                if tools_json is not None:
                    existing.tools_json = tools_json
                if knowledge_id is not None:
                    existing.knowledge_id = knowledge_id
                if retrieval_json is not None:
                    existing.retrieval_json = retrieval_json
                if safety_json is not None:
                    existing.safety_json = safety_json
                existing.updated_at = now
                db.commit()
                db.refresh(existing)
                return CoursePresetModel.model_validate(existing)
            else:
                row = CoursePreset(
                    id=str(uuid.uuid4()),
                    course_id=course_id,
                    name=name,
                    is_default=bool(is_default) if is_default is not None else False,
                    provider=provider,
                    model_id=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    system_prompt_md=system_prompt_md,
                    tools_json=tools_json,
                    knowledge_id=knowledge_id,
                    retrieval_json=retrieval_json,
                    safety_json=safety_json,
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
                db.commit()
                db.refresh(row)
                return CoursePresetModel.model_validate(row)


CoursePresets = CoursePresetsTable()


class CourseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    status: str
    created_by: str
    created_at: int
    updated_at: Optional[int] = None


class CoursesTable:
    def insert(
        self,
        *,
        title: str,
        description: Optional[str],
        created_by: str,
        meta_json: Optional[dict] = None,
    ) -> CourseModel:
        with get_db() as db:
            now = int(time.time())
            row = Course(
                id=str(uuid.uuid4()),
                title=title,
                description=description,
                status="draft",
                created_by=created_by,
                created_at=now,
                updated_at=now,
                meta_json=meta_json or {},
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return CourseModel.model_validate(row)

    def get_by_id(self, course_id: str) -> Optional[CourseModel]:
        with get_db() as db:
            row = db.get(Course, course_id)
            return CourseModel.model_validate(row) if row else None

    # Also add debug to the list_for_user method:
    def list_for_user(self, user_id: str, include_admin: bool = False) -> List[CourseModel]:
        """List courses visible to the user; admins can see all when include_admin=True."""
        print(f"[list_for_user] user_id: {user_id}, include_admin: {include_admin}")
        
        with get_db() as db:
            if include_admin:
                print("[list_for_user] Getting ALL courses (admin mode)")
                rows = db.query(Course).order_by(Course.created_at.desc()).all()
                print(f"[list_for_user] Found {len(rows)} total courses")
                return [CourseModel.model_validate(r) for r in rows]
            
            # Enrollment table removed. Fall back to visibility rules:
            # - Include courses the user created
            # - Include courses whose meta_json.visibility is not "private"
            rows = db.query(Course).order_by(Course.created_at.desc()).all()
            visible: List[CourseModel] = []
            for r in rows:
                try:
                    vis = (r.meta_json or {}).get("visibility")
                except Exception:
                    vis = None
                if r.created_by == user_id or (vis is not None and vis != "private"):
                    visible.append(CourseModel.model_validate(r))
            print(f"[list_for_user] Found {len(visible)} visible courses")
            return visible

    def update_status(self, course_id: str, status: str) -> Optional[CourseModel]:
        with get_db() as db:
            row = db.get(Course, course_id)
            if not row:
                return None
            row.status = status
            row.updated_at = int(time.time())
            db.commit()
            db.refresh(row)
            return CourseModel.model_validate(row)


Courses = CoursesTable()


####################
# Assignments & Submissions access
####################


class AssignmentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    title: str
    body_md: Optional[str] = None
    due_at: Optional[int] = None
    attachments_json: Optional[dict] = None
    created_at: int


class SubmissionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    user_id: str
    text: Optional[str] = None
    files_json: Optional[dict] = None
    submitted_at: int
    status: str
    grade_json: Optional[dict] = None


class AssignmentsTable:
    def list_by_course(self, course_id: str) -> List[AssignmentModel]:
        with get_db() as db:
            rows = db.query(Assignment).filter_by(course_id=course_id).order_by(Assignment.created_at.desc()).all()
            return [AssignmentModel.model_validate(r) for r in rows]

    def insert(
        self,
        *,
        course_id: str,
        title: str,
        body_md: Optional[str] = None,
        due_at: Optional[int] = None,
        attachments_json: Optional[dict] = None,
    ) -> AssignmentModel:
        with get_db() as db:
            now = int(time.time())
            row = Assignment(
                id=str(uuid.uuid4()),
                course_id=course_id,
                title=title,
                body_md=body_md,
                due_at=due_at,
                attachments_json=attachments_json or {},
                created_at=now,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return AssignmentModel.model_validate(row)

    def get_by_id(self, assignment_id: str) -> Optional[AssignmentModel]:
        with get_db() as db:
            row = db.get(Assignment, assignment_id)
            return AssignmentModel.model_validate(row) if row else None

    def update(
        self,
        assignment_id: str,
        *,
        title: Optional[str] = None,
        body_md: Optional[str] = None,
        due_at: Optional[int] = None,
        attachments_json: Optional[dict] = None,
    ) -> Optional[AssignmentModel]:
        with get_db() as db:
            row = db.get(Assignment, assignment_id)
            if not row:
                return None
            if title is not None:
                row.title = title
            if body_md is not None:
                row.body_md = body_md
            if due_at is not None:
                row.due_at = due_at
            if attachments_json is not None:
                row.attachments_json = attachments_json
            db.commit()
            db.refresh(row)
            return AssignmentModel.model_validate(row)

    def delete(self, assignment_id: str) -> bool:
        with get_db() as db:
            row = db.get(Assignment, assignment_id)
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True


Assignments = AssignmentsTable()


class SubmissionsTable:
    def list_by_assignment(self, assignment_id: str) -> List[SubmissionModel]:
        with get_db() as db:
            rows = db.query(Submission).filter_by(assignment_id=assignment_id).order_by(Submission.submitted_at.desc()).all()
            return [SubmissionModel.model_validate(r) for r in rows]

    def list_by_assignment_and_user(self, assignment_id: str, user_id: str) -> List[SubmissionModel]:
        with get_db() as db:
            rows = db.query(Submission).filter_by(assignment_id=assignment_id, user_id=user_id).order_by(Submission.submitted_at.desc()).all()
            return [SubmissionModel.model_validate(r) for r in rows]

    def get_by_id(self, submission_id: str) -> Optional[SubmissionModel]:
        with get_db() as db:
            row = db.get(Submission, submission_id)
            return SubmissionModel.model_validate(row) if row else None

    def insert(
        self,
        *,
        assignment_id: str,
        user_id: str,
        text: Optional[str] = None,
        files_json: Optional[dict] = None,
    ) -> SubmissionModel:
        with get_db() as db:
            now = int(time.time())
            row = Submission(
                id=str(uuid.uuid4()),
                assignment_id=assignment_id,
                user_id=user_id,
                text=text,
                files_json=files_json or {},
                submitted_at=now,
                status="submitted",
                grade_json=None,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return SubmissionModel.model_validate(row)

    def update(
        self,
        submission_id: str,
        *,
        text: Optional[str] = None,
        files_json: Optional[dict] = None,
        status: Optional[str] = None,
        grade_json: Optional[dict] = None,
    ) -> Optional[SubmissionModel]:
        with get_db() as db:
            row = db.get(Submission, submission_id)
            if not row:
                return None
            if text is not None:
                row.text = text
            if files_json is not None:
                row.files_json = files_json
            if status is not None:
                row.status = status
            if grade_json is not None:
                row.grade_json = grade_json
            db.commit()
            db.refresh(row)
            return SubmissionModel.model_validate(row)

    def delete(self, submission_id: str) -> bool:
        with get_db() as db:
            row = db.get(Submission, submission_id)
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True


# class CourseEnrollmentsTable:
#     def insert(self, *, course_id: str, user_id: str, is_teacher: bool) -> Optional[dict]:
#         with get_db() as db:
#             row = CourseEnrollment(
#                 id=str(uuid.uuid4()),
#                 course_id=course_id,
#                 user_id=user_id,
#                 is_teacher=bool(is_teacher),
#                 created_at=int(time.time()),
#             )
#             db.add(row)
#             db.commit()
#             db.refresh(row)
#             return {
#                 "id": row.id,
#                 "course_id": row.course_id,
#                 "user_id": row.user_id,
#                 "is_teacher": row.is_teacher,
#                 "created_at": row.created_at,
#             }

#     def list_by_course(self, course_id: str) -> List[dict]:
#         with get_db() as db:
#             rows = db.query(CourseEnrollment).filter_by(course_id=course_id).all()
#             return [
#                 {
#                     "id": r.id,
#                     "course_id": r.course_id,
#                     "user_id": r.user_id,
#                     "is_teacher": r.is_teacher,
#                     "created_at": r.created_at,
#                 }
#                 for r in rows
#             ]

#     def delete_by_course_and_user(self, course_id: str, user_id: str) -> bool:
#         with get_db() as db:
#             row = (
#                 db.query(CourseEnrollment)
#                 .filter_by(course_id=course_id, user_id=user_id)
#                 .first()
#             )
#             if not row:
#                 return False
#             db.delete(row)
#             db.commit()
#             return True


# CourseEnrollments = CourseEnrollmentsTable()


Submissions = SubmissionsTable()
