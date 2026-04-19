from __future__ import annotations

import json
import uuid
from datetime import datetime

import pytest

from testweavex.core.models import (
    Gap,
    GapStatus,
    ScoringSignals,
    TestCase,
    TestResult,
    TestRun,
    TestStatus,
    TestType,
    generate_stable_id,
)
from testweavex.storage.sqlite import SQLiteRepository


@pytest.fixture
def repo():
    """In-memory SQLite repo — isolated per test."""
    return SQLiteRepository(db_url="sqlite:///:memory:")


def _make_test_case(feature_path: str = "features/login.feature",
                    scenario: str = "User logs in") -> TestCase:
    now = datetime.utcnow()
    return TestCase(
        id=generate_stable_id(feature_path, scenario),
        title=scenario,
        feature_id=generate_stable_id(feature_path),
        gherkin="Given I am on the login page\nWhen I enter valid credentials\nThen I am logged in",
        test_type=TestType.smoke,
        skill="functional/smoke",
        created_at=now,
        updated_at=now,
    )


class TestUpsertAndGetTestCase:
    def test_insert_then_retrieve(self, repo):
        tc = _make_test_case()
        repo.upsert_test_case(tc)
        retrieved = repo.get_test_case(tc.id)
        assert retrieved.id == tc.id
        assert retrieved.title == tc.title
        assert retrieved.test_type == TestType.smoke

    def test_upsert_updates_existing(self, repo):
        tc = _make_test_case()
        repo.upsert_test_case(tc)
        updated = tc.model_copy(update={"title": "Updated title", "is_automated": True})
        repo.upsert_test_case(updated)
        retrieved = repo.get_test_case(tc.id)
        assert retrieved.title == "Updated title"
        assert retrieved.is_automated is True

    def test_get_nonexistent_raises(self, repo):
        from testweavex.core.exceptions import RecordNotFound
        with pytest.raises(RecordNotFound):
            repo.get_test_case("nonexistent-id")


class TestRunLifecycle:
    def test_start_and_end_run(self, repo):
        tc = _make_test_case()
        repo.upsert_test_case(tc)

        run = repo.start_run(suite="regression", environment="ci")
        assert run.id
        assert run.completed_at is None

        result = TestResult(
            id=str(uuid.uuid4()),
            run_id=run.id,
            test_case_id=tc.id,
            status=TestStatus.passed,
            duration_ms=1500,
        )
        repo.save_result(result)
        repo.end_run(run.id)

        retrieved = repo.get_run(run.id)
        assert retrieved.completed_at is not None
        assert retrieved.suite == "regression"
        assert retrieved.environment == "ci"

    def test_get_nonexistent_run_raises(self, repo):
        from testweavex.core.exceptions import RecordNotFound
        with pytest.raises(RecordNotFound):
            repo.get_run("nonexistent-run-id")


class TestCoveragePercentage:
    def test_empty_db_returns_zero(self, repo):
        assert repo.get_coverage_percentage() == 0.0

    def test_all_automated(self, repo):
        tc = _make_test_case()
        automated = tc.model_copy(update={"is_automated": True})
        repo.upsert_test_case(automated)
        assert repo.get_coverage_percentage() == 100.0

    def test_mixed_automated(self, repo):
        for i in range(4):
            tc = _make_test_case(scenario=f"Scenario {i}")
            is_auto = i < 2
            repo.upsert_test_case(tc.model_copy(update={"is_automated": is_auto}))
        pct = repo.get_coverage_percentage()
        assert pct == 50.0
