import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.models.test_schemas import DifficultyMix, TestStartRequest, SubmitRequest
from app.routes.test import (
    matches_test_filters,
    select_test_questions,
    start_test,
    submit_answers,
    to_projected_sat_score,
)


class TestPrepLogicTests(unittest.TestCase):
    def test_sat_projection_uses_question_bands(self):
        answers = [
            {"is_correct": True, "sat_band": "1000-1200"},
            {"is_correct": False, "sat_band": "1200-1400"},
            {"is_correct": True, "sat_band": "1400+"},
        ]

        self.assertEqual(to_projected_sat_score(answers), 1330)

    def test_sat_projection_falls_back_to_difficulty(self):
        answers = [
            {"is_correct": False, "difficulty": "easy"},
            {"is_correct": True, "difficulty": "medium"},
            {"is_correct": False, "difficulty": "hard"},
        ]

        self.assertEqual(to_projected_sat_score(answers), 1270)

    def test_sat_projection_prefers_difficulty_over_stale_sat_band(self):
        answers = [
            {
                "is_correct": True,
                "difficulty": "easy",
                "sat_band": "1200-1400",
            },
            {
                "is_correct": False,
                "difficulty": "easy",
                "sat_band": "1200-1400",
            },
        ]

        self.assertEqual(to_projected_sat_score(answers), 1100)

    def test_filters_match_subject_and_sat_range(self):
        question = {
            "id": "q1",
            "subject": "Math",
            "difficulty": "medium",
            "sat_band": "1200-1400",
        }

        self.assertTrue(matches_test_filters(question, ["Math"], "1200-1400"))
        self.assertFalse(matches_test_filters(question, ["English"], "1200-1400"))
        self.assertFalse(matches_test_filters(question, ["Math"], "1400+"))

    def test_previous_incorrect_questions_are_always_prioritized(self):
        questions = [
            {"id": "q1"},
            {"id": "q2"},
            {"id": "q3"},
            {"id": "q4"},
        ]

        selected = select_test_questions(
            questions=questions,
            total=3,
            correct_question_ids={"q1", "q2"},
            incorrect_question_ids={"q3"},
            include_previous_correct=False,
        )

        selected_ids = {q["id"] for q in selected}
        self.assertIn("q3", selected_ids)
        self.assertNotIn("q1", selected_ids)
        self.assertNotIn("q2", selected_ids)

    def test_previous_correct_can_be_reused_when_enabled(self):
        questions = [
            {"id": "q1"},
            {"id": "q2"},
        ]

        selected = select_test_questions(
            questions=questions,
            total=2,
            correct_question_ids={"q1"},
            incorrect_question_ids=set(),
            include_previous_correct=True,
        )

        selected_ids = {q["id"] for q in selected}
        self.assertEqual(selected_ids, {"q1", "q2"})

class FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class FakeSupabase:
    def __init__(self, role="student"):
        self.role = role
        self.inserted_answers = []
        self.updated_sessions = []
        self.questions = [
            {
                "id": "q1",
                "subject": "Math",
                "difficulty": "easy",
                "sat_band": "1000-1200",
                "question": "New easy math",
                "options": ["A", "B"],
                "correct_answer": "A",
                "explanation": "q1 explanation",
            },
            {
                "id": "q2",
                "subject": "Math",
                "difficulty": "easy",
                "sat_band": "1000-1200",
                "question": "Previously correct",
                "options": ["A", "B"],
                "correct_answer": "A",
                "explanation": "q2 explanation",
            },
            {
                "id": "q3",
                "subject": "Math",
                "difficulty": "easy",
                "sat_band": "1000-1200",
                "question": "Previously incorrect",
                "options": ["A", "B"],
                "correct_answer": "A",
                "explanation": "q3 explanation",
            },
            {
                "id": "q4",
                "subject": "Math",
                "difficulty": "hard",
                "sat_band": "1400+",
                "question": "Hard math",
                "options": ["A", "B"],
                "correct_answer": "A",
                "explanation": "q4 explanation",
            },
        ]
        self.prior_answers = [
            {"question_id": "q2", "is_correct": True},
            {"question_id": "q3", "is_correct": False},
        ]

    def table(self, name):
        return FakeQuery(self, name)


class FakeQuery:
    def __init__(self, fake, table_name):
        self.fake = fake
        self.table_name = table_name
        self.filters = {}
        self.in_filters = {}
        self.insert_payload = None
        self.update_payload = None
        self.single_requested = False

    def select(self, *_args):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, key, value):
        self.in_filters[key] = value
        return self

    def single(self):
        self.single_requested = True
        return self

    def insert(self, payload):
        self.insert_payload = payload
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.table_name == "profiles":
            return FakeExecuteResult({"id": "u1", "role": self.fake.role})

        if self.table_name == "test_sessions" and self.insert_payload:
            return FakeExecuteResult([{"id": "session-1"}])

        if self.table_name == "test_sessions" and self.update_payload:
            self.fake.updated_sessions.append(self.update_payload)
            return FakeExecuteResult([self.update_payload])

        if self.table_name == "test_sessions":
            return FakeExecuteResult([{"id": "previous-session"}])

        if self.table_name == "test_answers" and self.insert_payload:
            self.fake.inserted_answers.extend(self.insert_payload)
            return FakeExecuteResult(self.insert_payload)

        if self.table_name == "test_answers":
            return FakeExecuteResult(self.fake.prior_answers)

        if self.table_name == "questions":
            question_id = self.filters.get("id")
            if question_id:
                question = next(q for q in self.fake.questions if q["id"] == question_id)
                return FakeExecuteResult(question)
            return FakeExecuteResult(self.fake.questions)

        return FakeExecuteResult([])


class TestPrepRouteTests(unittest.IsolatedAsyncioTestCase):
    def test_start_test_allows_admin_and_prioritizes_previous_incorrect(self):
        fake = FakeSupabase(role="admin")
        req = TestStartRequest(
            user_id="u1",
            subjects=["Math"],
            total_questions=2,
            sat_range="1000-1200",
            include_previous_correct=False,
            difficulty_mix=DifficultyMix(easy=1, medium=0, hard=0),
        )

        with patch("app.routes.test.get_supabase", return_value=fake):
            result = start_test(req)

        selected_ids = {question["id"] for question in result["questions"]}
        self.assertIn("q3", selected_ids)
        self.assertNotIn("q2", selected_ids)
        self.assertEqual(result["included_previous_incorrect"], 1)
        self.assertTrue(result["excluded_previous_correct"])

    def test_start_test_blocks_parent_generation(self):
        fake = FakeSupabase(role="parent")
        req = TestStartRequest(
            user_id="u1",
            subjects=["Math"],
            total_questions=2,
            sat_range="1000-1200",
            include_previous_correct=True,
            difficulty_mix=DifficultyMix(easy=1, medium=0, hard=0),
        )

        with patch("app.routes.test.get_supabase", return_value=fake):
            with self.assertRaises(HTTPException) as raised:
                start_test(req)

        self.assertEqual(raised.exception.status_code, 403)

    async def test_submit_answers_persists_results_and_projects_score(self):
        fake = FakeSupabase(role="student")
        req = SubmitRequest(
            session_id="session-1",
            answers=[
                {"question_id": "q1", "selected_answer": "A"},
                {"question_id": "q4", "selected_answer": "B"},
            ],
        )

        with patch("app.routes.test.get_supabase", return_value=fake):
            result = await submit_answers(req)

        self.assertEqual(result["score"], 1)
        self.assertEqual(result["incorrect"], 1)
        self.assertEqual(result["projected_sat_score"], 1300)
        self.assertEqual(len(fake.inserted_answers), 2)
        self.assertEqual(fake.updated_sessions[0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
