import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, File, UploadFile
from pydantic import BaseModel

from open_webui.models.courses import (
    Courses,
    CourseDocs,
    Enrollments,
    StudentFeedbacks,
    CourseForm,
    CourseModel,
    CourseResponse,
    TaskForm,
    FeedbackForm,
    EnrollmentForm,
)
from open_webui.models.users import Users
from open_webui.models.files import Files, FileForm
from open_webui.utils.auth import get_verified_user
from open_webui.env import SRC_LOG_LEVELS
from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


def get_user_role_in_course(course_id: str, user_id: str) -> str:
    """Get user's role in a course or return 'none' if not enrolled"""
    role = Enrollments.get_user_role_in_course(course_id, user_id)
    return role if role else "none"


def check_course_permission(course_id: str, user_id: str, required_role: str = "student"):
    """Check if user has required permission in course"""
    user_role = get_user_role_in_course(course_id, user_id)
    
    if user_role == "none":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Not enrolled in this course."
        )
    
    if required_role == "teacher" and user_role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Teacher privileges required."
        )


############################
# Get Courses
############################


@router.get("/", response_model=list[CourseModel])
async def get_courses(user=Depends(get_verified_user)):
    """Get courses accessible to the user (enrolled courses)"""
    try:
        courses = Courses.get_courses_by_enrollment(user.id)
        return courses
    except Exception as e:
        log.exception(f"Error getting courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Get Course by ID
############################


@router.get("/{course_id}", response_model=CourseModel)
async def get_course_by_id(course_id: str, user=Depends(get_verified_user)):
    """Get course by ID (requires enrollment)"""
    check_course_permission(course_id, user.id, "student")
    
    course = Courses.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return course


############################
# Create Course
############################


@router.post("/", response_model=CourseModel)
async def create_course(form_data: CourseForm, user=Depends(get_verified_user)):
    """Create a new course (teachers only based on role permissions)"""
    # Check if user has teacher role in system
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Teacher privileges required."
        )
    
    try:
        course = Courses.insert_new_course(user.id, form_data)
        if course:
            # Automatically enroll creator as teacher
            Enrollments.insert_enrollment(course.id, user.id, "teacher")
            return course
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create course"
            )
    except Exception as e:
        log.exception(f"Error creating course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Update Course
############################


@router.put("/{course_id}", response_model=CourseModel)
async def update_course(
    course_id: str, form_data: CourseForm, user=Depends(get_verified_user)
):
    """Update course (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    try:
        course = Courses.update_course_by_id(course_id, form_data)
        if course:
            return course
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update course"
            )
    except Exception as e:
        log.exception(f"Error updating course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Delete Course
############################


@router.delete("/{course_id}")
async def delete_course(course_id: str, user=Depends(get_verified_user)):
    """Delete course (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    try:
        result = Courses.delete_course_by_id(course_id)
        if result:
            return {"detail": "Course deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete course"
            )
    except Exception as e:
        log.exception(f"Error deleting course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Course Tasks
############################


class TaskResponse(BaseModel):
    tasks: list[dict]


@router.post("/{course_id}/tasks", response_model=TaskResponse)
async def add_task_to_course(
    course_id: str, task_form: TaskForm, user=Depends(get_verified_user)
):
    """Add task to course (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    course = Courses.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    try:
        # Add new task to existing tasks
        tasks = course.tasks or []
        new_task = {
            "id": len(tasks) + 1,  # Simple ID generation
            **task_form.model_dump(),
        }
        tasks.append(new_task)
        
        # Update course with new tasks
        course_form = CourseForm(
            title=course.title,
            description=course.description,
            main_topics=course.main_topics,
            objectives=course.objectives,
            files=course.files,
            links=course.links,
            tasks=tasks,
            youtube_url=course.youtube_url,
            access_control=course.access_control,
        )
        
        updated_course = Courses.update_course_by_id(course_id, course_form)
        if updated_course:
            return TaskResponse(tasks=updated_course.tasks)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add task"
            )
    except Exception as e:
        log.exception(f"Error adding task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/{course_id}/tasks/{task_id}")
async def delete_task_from_course(
    course_id: str, task_id: int, user=Depends(get_verified_user)
):
    """Delete task from course (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    course = Courses.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    try:
        # Remove task from existing tasks
        tasks = course.tasks or []
        tasks = [task for task in tasks if task.get("id") != task_id]
        
        # Update course with filtered tasks
        course_form = CourseForm(
            title=course.title,
            description=course.description,
            main_topics=course.main_topics,
            objectives=course.objectives,
            files=course.files,
            links=course.links,
            tasks=tasks,
            youtube_url=course.youtube_url,
            access_control=course.access_control,
        )
        
        updated_course = Courses.update_course_by_id(course_id, course_form)
        if updated_course:
            return {"detail": "Task deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete task"
            )
    except Exception as e:
        log.exception(f"Error deleting task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Student Feedback
############################


@router.post("/{course_id}/feedback")
async def submit_feedback(
    course_id: str, feedback_form: FeedbackForm, user=Depends(get_verified_user)
):
    """Submit feedback for course (students)"""
    check_course_permission(course_id, user.id, "student")
    
    try:
        feedback = StudentFeedbacks.insert_feedback(
            course_id, user.id, feedback_form.content
        )
        if feedback:
            return {"detail": "Feedback submitted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to submit feedback"
            )
    except Exception as e:
        log.exception(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{course_id}/feedback")
async def get_course_feedback(course_id: str, user=Depends(get_verified_user)):
    """Get all feedback for course (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    try:
        feedback_list = StudentFeedbacks.get_feedback_by_course_id(course_id)
        
        # Add user information to feedback
        enriched_feedback = []
        for feedback in feedback_list:
            user_info = Users.get_user_by_id(feedback.user_id)
            enriched_feedback.append({
                **feedback.model_dump(),
                "user_name": user_info.name if user_info else "Unknown User"
            })
        
        return {"feedback": enriched_feedback}
    except Exception as e:
        log.exception(f"Error getting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Course Documents/Files
############################


@router.post("/{course_id}/docs")
async def upload_course_document(
    course_id: str,
    file: UploadFile = File(...),
    user=Depends(get_verified_user)
):
    """Upload document to course (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    try:
        # First save the file using the existing Files system
        file_content = await file.read()
        file_form = FileForm(
            id=f"course_{course_id}_{file.filename}",
            filename=file.filename,
            path=f"courses/{course_id}/{file.filename}",
            data={"content": file_content.decode('utf-8') if file.content_type.startswith('text') else None},
            meta={
                "name": file.filename,
                "content_type": file.content_type,
                "size": len(file_content),
            }
        )
        
        saved_file = Files.insert_new_file(user.id, file_form)
        if not saved_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to save file"
            )
        
        # Create course document record
        course_doc = CourseDocs.insert_new_course_doc(
            course_id=course_id,
            file_id=saved_file.id,
            name=file.filename,
            mime_type=file.content_type
        )
        
        if course_doc:
            return {"detail": "Document uploaded successfully", "doc_id": course_doc.id}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create course document record"
            )
            
    except Exception as e:
        log.exception(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Enrollment Management
############################


@router.post("/{course_id}/enroll")
async def enroll_users(
    course_id: str, enrollment_form: EnrollmentForm, user=Depends(get_verified_user)
):
    """Enroll users in course (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    try:
        enrolled_users = []
        for user_id in enrollment_form.user_ids:
            enrollment = Enrollments.insert_enrollment(
                course_id, user_id, enrollment_form.role
            )
            if enrollment:
                enrolled_users.append(user_id)
        
        return {
            "detail": f"Successfully enrolled {len(enrolled_users)} users",
            "enrolled_users": enrolled_users
        }
    except Exception as e:
        log.exception(f"Error enrolling users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/{course_id}/enroll/{user_id}")
async def unenroll_user(
    course_id: str, user_id: str, user=Depends(get_verified_user)
):
    """Unenroll user from course (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    try:
        result = Enrollments.delete_enrollment(course_id, user_id)
        if result:
            return {"detail": "User unenrolled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to unenroll user"
            )
    except Exception as e:
        log.exception(f"Error unenrolling user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )


@router.get("/{course_id}/enrollments")
async def get_course_enrollments(course_id: str, user=Depends(get_verified_user)):
    """Get course enrollments (teachers only)"""
    check_course_permission(course_id, user.id, "teacher")
    
    try:
        enrollments = Enrollments.get_enrollments_by_course_id(course_id)
        
        # Add user information to enrollments
        enriched_enrollments = []
        for enrollment in enrollments:
            user_info = Users.get_user_by_id(enrollment.user_id)
            enriched_enrollments.append({
                **enrollment.model_dump(),
                "user_name": user_info.name if user_info else "Unknown User",
                "user_email": user_info.email if user_info else "Unknown Email"
            })
        
        return {"enrollments": enriched_enrollments}
    except Exception as e:
        log.exception(f"Error getting enrollments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT()
        )
