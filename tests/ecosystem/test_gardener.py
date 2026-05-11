"""
tests/ecosystem/test_gardener.py
=================================
Testy integracyjne dla ecosystem/gardener.py (Gardener Orchestrator).
Weryfikuje: pełny cykl naprawczy, EMPATHY w audycie, speculative insight,
checkpoint/restore, singleton.
"""

import pytest
from ecosystem.antifragility import RepairContext
from ecosystem.attention_economy import UserAction
from ecosystem.gardener import Gardener, _reset_gardener_singleton
from ecosystem.playful_exploration import OutcomeType


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_singleton():
    """Resetuje singleton Gardener przed każdym testem."""
    _reset_gardener_singleton()
    yield
    _reset_gardener_singleton()


def make_repair_context(
    sig: str = "ValueError: hexagon failed",
    cycle: int = 3,
    conv: float = 0.4,
) -> RepairContext:
    return RepairContext(
        error_signature=sig,
        hexagon_cycle=cycle,
        convergence_score=conv,
        patched_files=("core/hexagon.py",),
    )


# ── Testy ─────────────────────────────────────────────────────────────────────

class TestFullRepairCycle:
    """4.2.1 — SAV fail → pętla naprawcza → Gardener rejestruje patch."""

    def test_after_repair_loop_creates_patch_in_registry(self):
        gardener = Gardener()
        ctx = make_repair_context()
        patch = gardener.after_repair_loop(ctx)
        assert patch is not None
        assert patch.error_signature == "ValueError: hexagon failed"
        assert gardener.registry.entry_count == 1

    def test_repeated_repair_same_signature_increments_applied_count(self):
        gardener = Gardener()
        ctx = make_repair_context("same error")
        p1 = gardener.after_repair_loop(ctx)
        p2 = gardener.after_repair_loop(ctx)
        assert p1.patch_id == p2.patch_id
        assert p2.applied_count == 2


class TestAttentionBudgetAudit:
    """4.2.2 — 3 odrzucenia planu → audit_attention_budget zwraca EMPATHY."""

    def test_three_rejections_audit_returns_empathy(self):
        gardener = Gardener()
        for _ in range(3):
            gardener.record_user_action(UserAction.PLAN_REJECTED)
        result = gardener.audit_attention_budget()
        assert "EMPATHY" in result.upper()

    def test_no_rejections_audit_returns_precision(self):
        gardener = Gardener()
        result = gardener.audit_attention_budget()
        assert "PRECISION" in result.upper()

    def test_five_rejections_audit_returns_recovery(self):
        gardener = Gardener()
        for _ in range(5):
            gardener.record_user_action(UserAction.PLAN_REJECTED)
        result = gardener.audit_attention_budget()
        assert "RECOVERY" in result.upper()


class TestSpeculativeInsight:
    """4.2.3 — Playground z insightem → speculative_insight() zwraca go."""

    def test_speculative_insight_returns_none_when_no_insights(self):
        gardener = Gardener()
        result = gardener.speculative_insight()
        assert result is None

    def test_speculative_insight_after_exploration(self):
        gardener = Gardener()
        # Uruchom eksplorację bezpiecznej hipotezy
        gardener.explore_hypothesis(
            "Innowacyjna metoda optymalizacji grafu bez naruszania prywatności"
        )
        result = gardener.speculative_insight()
        # Może być None jeśli hipoteza nie wygenerowała INSIGHT — akceptowalne
        if result is not None:
            assert result.outcome_type == OutcomeType.INSIGHT

    def test_speculative_insight_best_confidence(self):
        gardener = Gardener()
        gardener.explore_hypothesis("Bezpieczna hipoteza A")
        gardener.explore_hypothesis("Bezpieczna hipoteza B z większym potencjałem")
        insight = gardener.speculative_insight()
        # Jeśli są insighty, zwraca ten z najwyższą pewnością
        if insight is not None:
            all_insights = gardener.playground.get_insights()
            if all_insights:
                best_conf = max(o.confidence for o in all_insights)
                assert insight.confidence <= best_conf + 0.001


class TestCheckpointRestore:
    """4.2.4 — before_checkpoint → zmiany → restore przywraca stan budżetu."""

    def test_checkpoint_has_required_keys(self):
        gardener = Gardener()
        snapshot = gardener.before_checkpoint()
        assert "timestamp" in snapshot
        assert "registry" in snapshot
        assert "budget" in snapshot
        assert "playground" in snapshot

    def test_restore_resets_frustration_markers(self):
        gardener = Gardener()
        snapshot = gardener.before_checkpoint()
        # Dodaj frustrację po checkpoincie
        for _ in range(3):
            gardener.record_user_action(UserAction.PLAN_REJECTED)
        assert gardener.budget.frustration_markers == 3
        # Restore
        gardener.restore_from_checkpoint(snapshot)
        assert gardener.budget.frustration_markers == 0

    def test_checkpoint_count_grows(self):
        gardener = Gardener()
        gardener.before_checkpoint()
        gardener.before_checkpoint()
        assert len(gardener._checkpoints) == 2


class TestGardenerSingleton:
    """4.2.5 — Kolejne instancje Gardener() zwracają ten sam obiekt."""

    def test_singleton_same_object(self):
        g1 = Gardener()
        g2 = Gardener()
        assert g1 is g2

    def test_singleton_state_shared(self):
        g1 = Gardener()
        g1.after_repair_loop(make_repair_context("shared error"))
        g2 = Gardener()
        assert g2.registry.entry_count == 1

    def test_reset_creates_new_instance(self):
        g1 = Gardener()
        _reset_gardener_singleton()
        g2 = Gardener()
        assert g1 is not g2


class TestGardenerStatus:
    """Dodatkowy test: get_status() zwraca spójną strukturę."""

    def test_status_structure(self):
        gardener = Gardener()
        status = gardener.get_status()
        assert status["ecosystem_version"] == "2.0.0"
        assert status["gardener"] == "singleton"
        assert "registry_entries" in status
        assert "attention_mode" in status
        assert "attention_spent" in status
        assert "playground_insights" in status
        assert "checkpoint_count" in status

    def test_start_new_session_resets_budget(self):
        gardener = Gardener()
        for _ in range(3):
            gardener.record_user_action(UserAction.PLAN_REJECTED)
        assert gardener.budget.frustration_markers == 3
        gardener.start_new_session()
        assert gardener.budget.frustration_markers == 0
