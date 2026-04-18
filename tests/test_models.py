import pytest
from datetime import datetime
from testweavex.core.models import generate_stable_id, TestStatus, TestType, GapStatus


class TestGenerateStableId:
    def test_deterministic(self):
        id1 = generate_stable_id("features/login.feature", "User can log in")
        id2 = generate_stable_id("features/login.feature", "User can log in")
        assert id1 == id2

    def test_returns_64_hex_chars(self):
        result = generate_stable_id("features/login.feature", "User can log in")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_inputs_different_ids(self):
        id1 = generate_stable_id("features/login.feature", "User can log in")
        id2 = generate_stable_id("features/login.feature", "User can log out")
        id3 = generate_stable_id("features/register.feature", "User can log in")
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

    def test_single_part(self):
        result = generate_stable_id("features/login.feature")
        assert len(result) == 64

    def test_separator_matters(self):
        id1 = generate_stable_id("a", "b")
        id2 = generate_stable_id("ab", "")
        assert id1 != id2


class TestEnums:
    def test_test_status_values(self):
        assert TestStatus.pending == "pending"
        assert TestStatus.passed == "passed"
        assert TestStatus.failed == "failed"
        assert TestStatus.skipped == "skipped"
        assert TestStatus.flaky == "flaky"

    def test_test_type_values(self):
        expected = {
            "smoke", "sanity", "happy_path", "edge_cases", "data_driven",
            "integration", "system", "e2e", "accessibility", "cross_browser"
        }
        actual = {t.value for t in TestType}
        assert actual == expected

    def test_gap_status_values(self):
        assert GapStatus.open == "open"
        assert GapStatus.pending_review == "pending_review"
        assert GapStatus.closed == "closed"
        assert GapStatus.dismissed == "dismissed"


class TestTestCase:
    def test_valid_construction(self):
        from testweavex.core.models import TestCase
        now = datetime.utcnow()
        tc = TestCase(
            id=generate_stable_id("features/login.feature", "User logs in"),
            title="User logs in",
            feature_id=generate_stable_id("features/login.feature"),
            gherkin="Given I am on the login page\nWhen I enter valid credentials\nThen I am logged in",
            test_type=TestType.smoke,
            skill="functional/smoke",
            created_at=now,
            updated_at=now,
        )
        assert tc.status == TestStatus.pending
        assert tc.is_automated is False
        assert tc.priority == 2
        assert tc.tags == []

    def test_invalid_test_type_raises(self):
        from testweavex.core.models import TestCase
        now = datetime.utcnow()
        with pytest.raises(Exception):
            TestCase(
                id="x" * 64,
                title="t",
                feature_id="f" * 64,
                gherkin="g",
                test_type="not_a_type",
                skill="functional/smoke",
                created_at=now,
                updated_at=now,
            )


class TestGap:
    def test_priority_score_defaults_to_zero(self):
        from testweavex.core.models import Gap
        gap = Gap(
            id="g" * 64,
            test_case_id="t" * 64,
            detected_at=datetime.utcnow(),
        )
        assert gap.priority_score == 0.0
        assert gap.status == GapStatus.open

    def test_priority_score_accepts_valid_range(self):
        from testweavex.core.models import Gap
        gap = Gap(
            id="g" * 64,
            test_case_id="t" * 64,
            priority_score=0.85,
            detected_at=datetime.utcnow(),
        )
        assert gap.priority_score == 0.85

    def test_priority_score_rejects_above_one(self):
        from testweavex.core.models import Gap
        with pytest.raises(Exception):
            Gap(
                id="g" * 64,
                test_case_id="t" * 64,
                priority_score=1.5,
                detected_at=datetime.utcnow(),
            )

    def test_priority_score_rejects_below_zero(self):
        from testweavex.core.models import Gap
        with pytest.raises(Exception):
            Gap(
                id="g" * 64,
                test_case_id="t" * 64,
                priority_score=-0.1,
                detected_at=datetime.utcnow(),
            )


class TestRunAndResult:
    def test_test_run_defaults(self):
        from testweavex.core.models import TestRun
        run = TestRun(
            id="r" * 36,
            suite="regression",
            started_at=datetime.utcnow(),
        )
        assert run.environment == "local"
        assert run.triggered_by == "tw"
        assert run.completed_at is None
        assert run.result_ids == []

    def test_test_result_construction(self):
        from testweavex.core.models import TestResult
        r = TestResult(
            id="x" * 36,
            run_id="r" * 36,
            test_case_id="t" * 64,
            status=TestStatus.passed,
            duration_ms=1234,
        )
        assert r.retry_count == 0
        assert r.error_message is None
