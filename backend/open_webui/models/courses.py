import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.files import FileMetadataResponse
from open_webui.models.users import Users, UserResponse
from open_webui.utils.access_control import has_access

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Boolean

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Course DB Schema
####################


class Course(Base):
    __tablename__ = "course"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    title = Column(Text)
    description = Column(Text)
    main_topics = Column(JSON, nullable=True)  # list of strings
    objectives = Column(JSON, nullable=True)  # list of strings
    files = Column(JSON, nullable=True)  # list of file references
    links = Column(JSON, nullable=True)  # list of link objects
    tasks = Column(JSON, nullable=True)  # list of task objects
    youtube_url = Column(Text, nullable=True)

    access_control = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class CourseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    title: str
    description: str
    main_topics: list[str] = []
    objectives: list[str] = []
    files: list[dict] = []
    links: list[dict] = []
    tasks: list[dict] = []
    youtube_url: Optional[str] = None

    access_control: Optional[dict] = None
    is_active: bool = True

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Course Document DB Schema
####################


class CourseDoc(Base):
    __tablename__ = "course_doc"

    id = Column(Text, unique=True, primary_key=True)
    course_id = Column(Text)
    file_id = Column(Text)  # Reference to files table
    name = Column(Text)
    mime_type = Column(Text, nullable=True)
    storage_uri = Column(Text, nullable=True)
    chunk_config = Column(JSON, nullable=True)
    embed_status = Column(Text, default="pending")  # pending, processing, completed, error

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class CourseDocModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    file_id: str
    name: str
    mime_type: Optional[str] = None
    storage_uri: Optional[str] = None
    chunk_config: Optional[dict] = None
    embed_status: str = "pending"

    created_at: int
    updated_at: int


####################
# Enrollment DB Schema
####################


class Enrollment(Base):
    __tablename__ = "enrollment"

    id = Column(Text, unique=True, primary_key=True)
    course_id = Column(Text)
    user_id = Column(Text)
    role = Column(Text)  # "student" | "teacher"

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class EnrollmentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    user_id: str
    role: str

    created_at: int
    updated_at: int


####################
# Student Feedback DB Schema
####################


class StudentFeedback(Base):
    __tablename__ = "student_feedback"

    id = Column(Text, unique=True, primary_key=True)
    course_id = Column(Text)
    user_id = Column(Text)
    content = Column(Text)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class StudentFeedbackModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    user_id: str
    content: str

    created_at: int
    updated_at: int


####################
# Forms
####################


class CourseForm(BaseModel):
    title: str
    description: str
    main_topics: list[str] = []
    objectives: list[str] = []
    files: list[dict] = []
    links: list[dict] = []
    tasks: list[dict] = []
    youtube_url: Optional[str] = None
    access_control: Optional[dict] = None


class CourseResponse(CourseModel):
    user: Optional[UserResponse] = None
    enrollments: list[EnrollmentModel] = []


class TaskForm(BaseModel):
    title: str
    description: str
    due_date: Optional[str] = None
    status: str = "pending"


class FeedbackForm(BaseModel):
    content: str


class EnrollmentForm(BaseModel):
    user_ids: list[str]
    role: str = "student"


####################
# Course Table
####################


class CourseTable:
    def insert_new_course(
        self, user_id: str, form_data: CourseForm
    ) -> Optional[CourseModel]:
        with get_db() as db:
            course = CourseModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Course(**course.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return CourseModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error inserting a new course: {e}")
                return None

    def get_courses(self) -> list[CourseModel]:
        with get_db() as db:
            return [
                CourseModel.model_validate(course)
                for course in db.query(Course).order_by(Course.updated_at.desc()).all()
            ]

    def get_courses_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> list[CourseModel]:
        courses = self.get_courses()
        return [
            course
            for course in courses
            if course.user_id == user_id
            or has_access(user_id, permission, course.access_control)
        ]

    def get_course_by_id(self, id: str) -> Optional[CourseModel]:
        try:
            with get_db() as db:
                course = db.query(Course).filter_by(id=id).first()
                return CourseModel.model_validate(course) if course else None
        except Exception:
            return None

    def update_course_by_id(
        self, id: str, form_data: CourseForm
    ) -> Optional[CourseModel]:
        try:
            with get_db() as db:
                db.query(Course).filter_by(id=id).update(
                    {
                        **form_data.model_dump(),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_course_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def delete_course_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Course).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def get_course_collections(self, course_id: str) -> list[str]:
        """Get collection names for course documents (for RAG retrieval)"""
        try:
            course_docs = CourseDocs.get_course_docs_by_course_id(course_id)
            # Collection names are typically the file_id of course documents
            collection_names = [f"course-{course_id}-{doc.file_id}" for doc in course_docs]
            return collection_names
        except Exception as e:
            log.exception(f"Error getting course collections: {e}")
            return []

    def get_courses_by_enrollment(self, user_id: str) -> list[CourseModel]:
        """Get courses where user is enrolled as student or teacher"""
        with get_db() as db:
            # Get enrolled course IDs
            enrolled_course_ids = [
                enrollment.course_id
                for enrollment in db.query(Enrollment).filter_by(user_id=user_id).all()
            ]
            
            if not enrolled_course_ids:
                return []
                
            courses = db.query(Course).filter(Course.id.in_(enrolled_course_ids)).all()
            return [CourseModel.model_validate(course) for course in courses]


####################
# Course Documents Table
####################


class CourseDocTable:
    def insert_new_course_doc(
        self, course_id: str, file_id: str, name: str, mime_type: Optional[str] = None
    ) -> Optional[CourseDocModel]:
        with get_db() as db:
            course_doc = CourseDocModel(
                id=str(uuid.uuid4()),
                course_id=course_id,
                file_id=file_id,
                name=name,
                mime_type=mime_type,
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )

            try:
                result = CourseDoc(**course_doc.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return CourseDocModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error inserting a new course document: {e}")
                return None

    def get_course_docs_by_course_id(self, course_id: str) -> list[CourseDocModel]:
        with get_db() as db:
            course_docs = db.query(CourseDoc).filter_by(course_id=course_id).all()
            return [CourseDocModel.model_validate(doc) for doc in course_docs]

    def update_embed_status(
        self, doc_id: str, status: str
    ) -> Optional[CourseDocModel]:
        try:
            with get_db() as db:
                db.query(CourseDoc).filter_by(id=doc_id).update(
                    {
                        "embed_status": status,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                
                doc = db.query(CourseDoc).filter_by(id=doc_id).first()
                return CourseDocModel.model_validate(doc) if doc else None
        except Exception as e:
            log.exception(e)
            return None

    def delete_course_doc_by_id(self, doc_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(CourseDoc).filter_by(id=doc_id).delete()
                db.commit()
                return True
        except Exception:
            return False


####################
# Enrollment Table
####################


class EnrollmentTable:
    def insert_enrollment(
        self, course_id: str, user_id: str, role: str = "student"
    ) -> Optional[EnrollmentModel]:
        with get_db() as db:
            # Check if enrollment already exists
            existing = db.query(Enrollment).filter_by(
                course_id=course_id, user_id=user_id
            ).first()
            
            if existing:
                # Update existing enrollment
                db.query(Enrollment).filter_by(
                    course_id=course_id, user_id=user_id
                ).update({
                    "role": role,
                    "updated_at": int(time.time()),
                })
                db.commit()
                return EnrollmentModel.model_validate(existing)

            enrollment = EnrollmentModel(
                id=str(uuid.uuid4()),
                course_id=course_id,
                user_id=user_id,
                role=role,
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )

            try:
                result = Enrollment(**enrollment.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return EnrollmentModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error inserting enrollment: {e}")
                return None

    def get_enrollments_by_course_id(self, course_id: str) -> list[EnrollmentModel]:
        with get_db() as db:
            enrollments = db.query(Enrollment).filter_by(course_id=course_id).all()
            return [EnrollmentModel.model_validate(e) for e in enrollments]

    def get_enrollments_by_user_id(self, user_id: str) -> list[EnrollmentModel]:
        with get_db() as db:
            enrollments = db.query(Enrollment).filter_by(user_id=user_id).all()
            return [EnrollmentModel.model_validate(e) for e in enrollments]

    def delete_enrollment(self, course_id: str, user_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Enrollment).filter_by(
                    course_id=course_id, user_id=user_id
                ).delete()
                db.commit()
                return True
        except Exception:
            return False

    def get_user_role_in_course(self, course_id: str, user_id: str) -> Optional[str]:
        with get_db() as db:
            enrollment = db.query(Enrollment).filter_by(
                course_id=course_id, user_id=user_id
            ).first()
            return enrollment.role if enrollment else None


####################
# Student Feedback Table
####################


class StudentFeedbackTable:
    def insert_feedback(
        self, course_id: str, user_id: str, content: str
    ) -> Optional[StudentFeedbackModel]:
        with get_db() as db:
            feedback = StudentFeedbackModel(
                id=str(uuid.uuid4()),
                course_id=course_id,
                user_id=user_id,
                content=content,
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )

            try:
                result = StudentFeedback(**feedback.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return StudentFeedbackModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error inserting feedback: {e}")
                return None

    def get_feedback_by_course_id(self, course_id: str) -> list[StudentFeedbackModel]:
        with get_db() as db:
            feedback_list = db.query(StudentFeedback).filter_by(course_id=course_id).all()
            return [StudentFeedbackModel.model_validate(f) for f in feedback_list]

    def get_feedback_by_user_and_course(
        self, course_id: str, user_id: str
    ) -> list[StudentFeedbackModel]:
        with get_db() as db:
            feedback_list = db.query(StudentFeedback).filter_by(
                course_id=course_id, user_id=user_id
            ).all()
            return [StudentFeedbackModel.model_validate(f) for f in feedback_list]


# Initialize instances
Courses = CourseTable()
CourseDocs = CourseDocTable()
Enrollments = EnrollmentTable()
StudentFeedbacks = StudentFeedbackTable()
