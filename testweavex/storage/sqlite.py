from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from testweavex.core.exceptions import RecordNotFound, StorageError
from testweavex.core.models import (
    Gap,
    GapStatus,
    RunSummary,  # noqa: F401
    ScoringSignals,
    TestCase,
    TestResult,
    TestRun,
    TestStatus,
    TestType,
    generate_stable_id,  # noqa: F401
)
from testweavex.storage.base import StorageRepository
from testweavex.storage.models import (
    Base,
    FeatureORM,  # noqa: F401
    GapORM,
    TestCaseORM,
    TestResultORM,
    TestRunORM,
)



def _orm_to_test_case(row: TestCaseORM) -> TestCase:
    return TestCase(
        id=row.id,
        title=row.title,
        feature_id=row.feature_id,
        gherkin=row.gherkin,
        test_type=TestType(row.test_type),
        skill=row.skill,
        status=TestStatus(row.status),
        is_automated=row.is_automated,
        tcm_id=row.tcm_id,
        tags=json.loads(row.tags) if row.tags else [],
        priority=row.priority,
        source_file=row.source_file,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _orm_to_test_run(row: TestRunORM) -> TestRun:
    return TestRun(
        id=row.id,
        suite=row.suite,
        environment=row.environment,
        browser=row.browser,
        triggered_by=row.triggered_by,
        started_at=row.started_at,
        completed_at=row.completed_at,
        result_ids=[],
    )


def _orm_to_gap(row: GapORM) -> Gap:
    return Gap(
        id=row.id,
        test_case_id=row.test_case_id,
        priority_score=row.priority_score,
        gap_reason=row.gap_reason,
        suggested_gherkin=row.suggested_gherkin,
        status=GapStatus(row.status),
        detected_at=row.detected_at,
        closed_at=row.closed_at,
    )


class SQLiteRepository(StorageRepository):

    def __init__(self, db_url: Optional[str] = None) -> None:
        if db_url is None:
            db_url = "sqlite:///:memory:"

        self._engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self._engine)

    def _session(self) -> Session:
        return Session(self._engine)

    # ── TestCase ──────────────────────────────────────────────────────────

    def upsert_test_case(self, tc: TestCase) -> None:
        try:
            with self._session() as s:
                row = TestCaseORM(
                    id=tc.id,
                    title=tc.title,
                    feature_id=tc.feature_id,
                    gherkin=tc.gherkin,
                    test_type=tc.test_type.value,
                    skill=tc.skill,
                    status=tc.status.value,
                    is_automated=tc.is_automated,
                    tcm_id=tc.tcm_id,
                    tags=json.dumps(tc.tags),
                    priority=tc.priority,
                    source_file=tc.source_file,
                    created_at=tc.created_at,
                    updated_at=tc.updated_at,
                )
                s.merge(row)
                s.commit()
        except Exception as exc:
            raise StorageError(f"Failed to upsert test case {tc.id}") from exc

    def get_test_case(self, id: str) -> TestCase:
        with self._session() as s:
            row = s.get(TestCaseORM, id)
            if row is None:
                raise RecordNotFound(f"TestCase not found: {id}")
            return _orm_to_test_case(row)

    # ── TestRun / TestResult ──────────────────────────────────────────────

    def start_run(self, suite: str, environment: str = "local",
                  browser: Optional[str] = None, triggered_by: str = "tw") -> TestRun:
        run_id = str(uuid.uuid4())
        now = datetime.utcnow()
        try:
            with self._session() as s:
                row = TestRunORM(
                    id=run_id,
                    suite=suite,
                    environment=environment,
                    browser=browser,
                    triggered_by=triggered_by,
                    started_at=now,
                )
                s.add(row)
                s.commit()
        except Exception as exc:
            raise StorageError("Failed to start test run") from exc
        return TestRun(
            id=run_id,
            suite=suite,
            environment=environment,
            browser=browser,
            triggered_by=triggered_by,
            started_at=now,
        )

    def end_run(self, run_id: str) -> None:
        try:
            with self._session() as s:
                row = s.get(TestRunORM, run_id)
                if row is None:
                    raise RecordNotFound(f"TestRun not found: {run_id}")
                row.completed_at = datetime.utcnow()
                s.commit()
        except RecordNotFound:
            raise
        except Exception as exc:
            raise StorageError(f"Failed to end run {run_id}") from exc

    def get_run(self, run_id: str) -> TestRun:
        with self._session() as s:
            row = s.get(TestRunORM, run_id)
            if row is None:
                raise RecordNotFound(f"TestRun not found: {run_id}")
            return _orm_to_test_run(row)

    def save_result(self, r: TestResult) -> None:
        try:
            with self._session() as s:
                row = TestResultORM(
                    id=r.id,
                    run_id=r.run_id,
                    test_case_id=r.test_case_id,
                    status=r.status.value,
                    duration_ms=r.duration_ms,
                    error_message=r.error_message,
                    screenshot_path=r.screenshot_path,
                    retry_count=r.retry_count,
                )
                s.add(row)
                s.commit()
        except Exception as exc:
            raise StorageError(f"Failed to save result {r.id}") from exc

    # ── Coverage ──────────────────────────────────────────────────────────

    def get_coverage_percentage(self) -> float:
        with self._session() as s:
            total = s.query(TestCaseORM).count()
            if total == 0:
                return 0.0
            automated = s.query(TestCaseORM).filter(TestCaseORM.is_automated.is_(True)).count()
            return round(automated / total * 100, 2)

    def get_coverage_trend(self, weeks: int) -> list[dict]:
        return []

    # ── Gaps ──────────────────────────────────────────────────────────────

    def get_gaps(self, limit: int = 50, status: str = "open") -> list[Gap]:
        with self._session() as s:
            rows = (
                s.query(GapORM)
                .filter(GapORM.status == status)
                .order_by(GapORM.priority_score.desc())
                .limit(limit)
                .all()
            )
            return [_orm_to_gap(r) for r in rows]

    def save_gaps(self, gaps: list[Gap]) -> None:
        try:
            with self._session() as s:
                for g in gaps:
                    row = GapORM(
                        id=g.id,
                        test_case_id=g.test_case_id,
                        priority_score=g.priority_score,
                        gap_reason=g.gap_reason,
                        suggested_gherkin=g.suggested_gherkin,
                        status=g.status.value,
                        detected_at=g.detected_at,
                        closed_at=g.closed_at,
                    )
                    s.merge(row)
                s.commit()
        except Exception as exc:
            raise StorageError("Failed to save gaps") from exc

    def mark_uncollected_as_gaps(self, collected_ids: list[str]) -> None:
        now = datetime.utcnow()
        with self._session() as s:
            all_ids = [row.id for row in s.query(TestCaseORM.id).all()]
            existing_open_gap_tc_ids = {
                row.test_case_id
                for row in s.query(GapORM.test_case_id)
                .filter(GapORM.status == "open")
                .all()
            }
            collected_set = set(collected_ids)
            new_gaps = []
            for tc_id in all_ids:
                if tc_id not in collected_set and tc_id not in existing_open_gap_tc_ids:
                    new_gaps.append(GapORM(
                        id=str(uuid.uuid4()),
                        test_case_id=tc_id,
                        priority_score=0.0,
                        gap_reason="Not collected in last test run",
                        status="open",
                        detected_at=now,
                    ))
            if new_gaps:
                s.add_all(new_gaps)
                s.commit()

    # ── Flakiness ─────────────────────────────────────────────────────────

    def get_flaky_tests(self, min_runs: int = 5) -> list[TestCase]:
        sql = text("""
            SELECT test_case_id
            FROM test_results
            GROUP BY test_case_id
            HAVING COUNT(*) >= :min_runs
               AND SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) > 0
               AND SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) > 0
            ORDER BY CAST(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) DESC
        """)
        with self._session() as s:
            rows = s.execute(sql, {"min_runs": min_runs}).fetchall()
            result = []
            for (tc_id,) in rows:
                try:
                    result.append(self.get_test_case(tc_id))
                except RecordNotFound:
                    pass
            return result

    # ── ScoringSignals ────────────────────────────────────────────────────

    def get_scoring_signals(self, tc_id: str) -> ScoringSignals:
        tc = self.get_test_case(tc_id)
        with self._session() as s:
            executions_90d_sql = text("""
                SELECT COUNT(*) FROM test_results tr
                JOIN test_runs run ON tr.run_id = run.id
                WHERE tr.test_case_id = :tc_id
                  AND run.started_at >= datetime('now', '-90 days')
            """)
            executions_90d = s.execute(executions_90d_sql, {"tc_id": tc_id}).scalar() or 0

            last_run_sql = text("""
                SELECT run.started_at FROM test_results tr
                JOIN test_runs run ON tr.run_id = run.id
                WHERE tr.test_case_id = :tc_id
                ORDER BY run.started_at DESC LIMIT 1
            """)
            last_run_row = s.execute(last_run_sql, {"tc_id": tc_id}).fetchone()
            if last_run_row:
                last_run_dt = last_run_row[0]
                if isinstance(last_run_dt, str):
                    last_run_dt = datetime.fromisoformat(last_run_dt)
                days_since = (datetime.utcnow() - last_run_dt).days
            else:
                days_since = 999

        return ScoringSignals(
            test_priority=tc.priority,
            test_type=tc.test_type,
            defect_count=0,
            executions_90d=executions_90d,
            days_since_run=days_since,
        )
