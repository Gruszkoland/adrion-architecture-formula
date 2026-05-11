"""Tests for Protocol333 — full decision pipeline orchestrator."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture()
def valid_perspectives():
    return {"material": 0.8, "intellectual": 0.7, "essential": 0.9}


@pytest.fixture()
def low_perspectives():
    return {"material": 0.1, "intellectual": 0.1, "essential": 0.1}


@pytest.fixture()
def context():
    return {"task": "test_decision", "domain": "unit_test"}


# ─────────────────────────────────────────────────────────────────────
# Import + instantiation
# ─────────────────────────────────────────────────────────────────────


class TestProtocol333Import:
    def test_imports(self):
        from core.protocol333 import Protocol333, Protocol333Result
        assert Protocol333 is not None
        assert Protocol333Result is not None

    def test_instantiate(self):
        from core.protocol333 import Protocol333
        p = Protocol333()
        assert p is not None

    def test_has_execute(self):
        from core.protocol333 import Protocol333
        p = Protocol333()
        assert callable(p.execute)


# ─────────────────────────────────────────────────────────────────────
# execute() — basic happy path (mocked deps)
# ─────────────────────────────────────────────────────────────────────


class TestProtocol333Execute:
    def test_execute_returns_result(self, valid_perspectives, context):
        from core.protocol333 import Protocol333, Protocol333Result
        p = Protocol333()
        result = p.execute(valid_perspectives, context, session_id="test_session_1")
        assert isinstance(result, Protocol333Result)

    def test_result_has_session_id(self, valid_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context, session_id="sess_abc")
        assert result.session_id == "sess_abc"

    def test_result_auto_session_id(self, valid_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context)
        assert result.session_id.startswith("p333_")

    def test_result_has_trinity_scores(self, valid_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context)
        assert "material" in result.trinity_scores
        assert "intellectual" in result.trinity_scores
        assert "essential" in result.trinity_scores

    def test_result_has_duration_ms(self, valid_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context)
        assert result.duration_ms > 0

    def test_result_to_dict(self, valid_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "approved" in d
        assert "trinity_scores" in d
        assert "hexagon_combined_score" in d


# ─────────────────────────────────────────────────────────────────────
# Pipeline logic — approval chain
# ─────────────────────────────────────────────────────────────────────


class TestProtocol333ApprovalChain:
    def test_high_scores_approved(self, valid_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context)
        # With high scores and no security issues, hexagon should approve
        assert result.hexagon_approved is True

    def test_low_scores_not_approved(self, low_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(low_perspectives, context)
        # Very low scores fail hexagon (inventory threshold 0.3)
        assert result.hexagon_approved is False
        assert result.approved is False

    def test_rejection_reason_set_on_failure(self, low_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(low_perspectives, context)
        assert result.rejection_reason is not None

    def test_approved_requires_hexagon_and_security(self, valid_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context)
        expected = result.hexagon_approved and result.security_passed
        assert result.approved == expected


# ─────────────────────────────────────────────────────────────────────
# Resilience — ecosystem not installed (graceful degradation)
# ─────────────────────────────────────────────────────────────────────


class TestProtocol333GracefulDegradation:
    def test_works_without_ecosystem(self, valid_perspectives, context, monkeypatch):
        """Protocol333 must work even when ecosystem/ is not importable."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith("ecosystem"):
                raise ImportError("ecosystem not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context)
        # Should complete without ecosystem hooks
        assert result is not None
        assert result.attention_mode == "PRECISION"  # default fallback

    def test_attention_mode_is_string(self, valid_perspectives, context):
        from core.protocol333 import Protocol333
        p = Protocol333()
        result = p.execute(valid_perspectives, context)
        assert isinstance(result.attention_mode, str)


# ─────────────────────────────────────────────────────────────────────
# Protocol333Result dataclass
# ─────────────────────────────────────────────────────────────────────


class TestProtocol333Result:
    def test_result_fields(self):
        from core.protocol333 import Protocol333Result
        r = Protocol333Result(
            session_id="s1",
            approved=True,
            trinity_scores={"material": 0.8},
            hexagon_approved=True,
            hexagon_combined_score=0.75,
            security_passed=True,
            attention_mode="PRECISION",
            duration_ms=123.4,
        )
        assert r.session_id == "s1"
        assert r.approved is True
        assert r.hexagon_combined_score == 0.75
        assert r.rejection_reason is None
        assert r.ecosystem_status == {}

    def test_to_dict_keys(self):
        from core.protocol333 import Protocol333Result
        r = Protocol333Result(
            session_id="s2",
            approved=False,
            trinity_scores={},
            hexagon_approved=False,
            hexagon_combined_score=0.0,
            security_passed=True,
            attention_mode="RECOVERY",
            duration_ms=50.0,
            rejection_reason="test rejection",
        )
        d = r.to_dict()
        expected_keys = {
            "session_id", "approved", "trinity_scores",
            "hexagon_approved", "hexagon_combined_score",
            "security_passed", "attention_mode", "duration_ms",
            "rejection_reason", "ecosystem_status",
        }
        assert expected_keys.issubset(d.keys())
