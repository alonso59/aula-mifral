import os
import uuid

import pytest
from sqlalchemy import text

from open_webui.test.util.abstract_integration_test import AbstractPostgresTest


class TestClassroomPhase4(AbstractPostgresTest):
    @classmethod
    def setup_class(cls):
        # Ensure classroom feature is enabled for tests
        os.environ["CLASSROOM_MODE"] = "true"
        super().setup_class()

    def _seed_course(self, course_id: str, created_by: str = "u-teacher"):
        from open_webui.internal.db import Session

        Session.execute(
            text(
                """
                INSERT INTO courses (id, title, description, status, created_by, created_at, updated_at)
                VALUES (:id, :title, :description, :status, :created_by, 0, 0)
                """
            ),
            {
                "id": course_id,
                "title": "Course A",
                "description": "desc",
                "status": "draft",
                "created_by": created_by,
            },
        )
        Session.commit()

    def _enroll(self, course_id: str, user_id: str, is_teacher: bool = False):
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

    def _create_kb(self) -> str:
        from open_webui.internal.db import Session

        kb_id = str(uuid.uuid4())
        Session.execute(
            text(
                """
                INSERT INTO knowledge (id, user_id, name, description, data, meta, access_control, created_at, updated_at)
                VALUES (:id, :user_id, :name, :description, '{}', '{}', '{}', 0, 0)
                """
            ),
            {
                "id": kb_id,
                "user_id": "u-teacher",
                "name": "KB",
                "description": "kb",
            },
        )
        Session.commit()
        return kb_id

    def test_preset_crud_and_activation_and_chat_gating(self):
        client = self.fast_api_client
        course_id = "c-1"
        teacher_id = "u-teacher"
        student_id = "u-student"

        # Seed course and enrollments
        self._seed_course(course_id, created_by=teacher_id)
        self._enroll(course_id, teacher_id, is_teacher=True)
        self._enroll(course_id, student_id, is_teacher=False)

        # Upsert preset with no knowledge (not sufficient for activation under Phase 4B)
        from open_webui.test.util.mock_user import mock_user
        from open_webui.main import app

        with mock_user(app, id=teacher_id, role="user"):
            res = client.put(
                f"/api/classroom/courses/{course_id}/preset",
                json={
                    "provider": "openai",
                    "model_id": "gpt-4o-mini",
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "system_prompt_md": "You are helpful",
                    "tools_json": {"use": []},
                },
            )
        assert res.status_code == 200
        preset = res.json()
        assert preset["course_id"] == course_id
        assert preset["provider"] == "openai"

        # Activation should fail because no default and missing knowledge
        with mock_user(app, id=teacher_id, role="user"):
            res = client.post(f"/api/classroom/courses/{course_id}/activate")
        assert res.status_code == 400

        # Create knowledge and update preset with knowledge_id
        kb_id = self._create_kb()
        with mock_user(app, id=teacher_id, role="user"):
            res = client.put(
                f"/api/classroom/courses/{course_id}/preset",
                json={"knowledge_id": kb_id},
            )
        assert res.status_code == 200

        # Set as default
        with mock_user(app, id=teacher_id, role="user"):
            res = client.post(f"/api/classroom/courses/{course_id}/preset/set-default")
        assert res.status_code == 200

        # Now activation should succeed -> course active
        with mock_user(app, id=teacher_id, role="user"):
            res = client.post(f"/api/classroom/courses/{course_id}/activate")
        assert res.status_code == 200
        assert res.json()["status"] == "active"

        # Student can chat now (was blocked when inactive)
        with mock_user(app, id=student_id, role="user"):
            res = client.post(
                f"/api/classroom/courses/{course_id}/chat/completions",
                json={"messages": [{"role": "user", "content": "hi"}]},
            )
        assert res.status_code == 200
        assert res.json()["object"] == "chat.completion"
        assert res.json()["preset"]["model_id"] == "gpt-4o-mini"

    def test_activation_requires_valid_default_and_knowledge(self):
        client = self.fast_api_client
        course_id = "c-2"
        teacher_id = "u2"

        self._seed_course(course_id, created_by=teacher_id)
        self._enroll(course_id, teacher_id, is_teacher=True)

        from open_webui.test.util.mock_user import mock_user
        from open_webui.main import app

        # Upsert preset with a non-existent knowledge_id
        with mock_user(app, id=teacher_id, role="user"):
            res = client.put(
                f"/api/classroom/courses/{course_id}/preset",
                json={"knowledge_id": "non-existent"},
            )
        assert res.status_code == 200

        # Setting default should still fail activation due to invalid knowledge
        with mock_user(app, id=teacher_id, role="user"):
            res = client.post(f"/api/classroom/courses/{course_id}/preset/set-default")
        assert res.status_code == 200

        with mock_user(app, id=teacher_id, role="user"):
            res = client.post(f"/api/classroom/courses/{course_id}/activate")
        assert res.status_code == 400

        # Create a knowledge base and update preset
        kb_id = self._create_kb()
        with mock_user(app, id=teacher_id, role="user"):
            res = client.put(
                f"/api/classroom/courses/{course_id}/preset",
                json={"knowledge_id": kb_id},
            )
        assert res.status_code == 200

    # Now activation should succeed (default already set and knowledge valid)
        with mock_user(app, id=teacher_id, role="user"):
            res = client.post(f"/api/classroom/courses/{course_id}/activate")
        assert res.status_code == 200
        assert res.json()["status"] == "active"
