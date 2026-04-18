import pytest
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
