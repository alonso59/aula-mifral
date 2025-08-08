import os
import uuid

import pytest
from fastapi import HTTPException, status
from sqlalchemy import text

from open_webui.test.util.abstract_integration_test import AbstractPostgresTest


class TestClassroomRBAC(AbstractPostgresTest):
    @classmethod
    def setup_class(cls):
        # Enable classroom mode before importing app/config
        os.environ["CLASSROOM_MODE"] = "true"
        super().setup_class()

    def _insert_enrollment(self, course_id: str, user_id: str, is_teacher: bool):
        from open_webui.internal.db import Session

        Session.execute(
            text(
                """
                INSERT INTO course_enrollments (id, course_id, user_id, is_teacher, created_at)
                VALUES (:id, :course_id, :user_id, :is_teacher, 0)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "course_id": course_id,
                "user_id": user_id,
                "is_teacher": is_teacher,
            },
        )
        Session.commit()

    def test_require_course_enrollment(self):
        from open_webui.utils.auth import requireCourseEnrollment

        user = type("U", (), {"id": "u1", "role": "user"})()
        course_id = "c1"

        # enrolled
        self._insert_enrollment(course_id, user.id, False)
        dep = requireCourseEnrollment(course_id)
        assert dep(user=user) is user

        # not enrolled
        other_course = "c2"
        dep2 = requireCourseEnrollment(other_course)
        with pytest.raises(HTTPException) as ex:
            dep2(user=user)
        assert ex.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_require_course_teacher_and_admin_bypass(self):
        from open_webui.utils.auth import requireCourseTeacher

        course_id = "c3"
        student = type("U", (), {"id": "stu", "role": "user"})()
        teacher = type("U", (), {"id": "tea", "role": "user"})()
        admin = type("U", (), {"id": "adm", "role": "admin"})()

        # add enrollments
        self._insert_enrollment(course_id, student.id, False)
        self._insert_enrollment(course_id, teacher.id, True)

        # teacher passes
        dep = requireCourseTeacher(course_id)
        assert dep(user=teacher) is teacher

        # student fails
        with pytest.raises(HTTPException):
            dep(user=student)

        # admin bypass
        assert dep(user=admin) is admin
