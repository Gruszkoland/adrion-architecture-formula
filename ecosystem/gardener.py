"""
ecosystem/gardener.py — Ogrodnik: Orkiestrator Ekosystemu [B7-FIX]
===================================================================
Implementacja Gardener dla ADRION 369 Ecosystem v2.0.

Koncepcja:
  Gardener jest singleton-wtyczką do istniejącego MASTER ORCHESTRATOR.
  Nie zastępuje orkiestratora — tylko podpina się pod 4 punkty jego pętli
  operacyjnej (Kroki 1.5, 2.5, 3, 5).

Punkty integracji w MASTER ORCHESTRATOR:
  Krok 1.5 (RBC) → Gardener.before_checkpoint()
  Krok 2.5 (SAV fail) → Gardener.after_repair_loop(repair_context)
  Krok 3 (Audyt) → Gardener.audit_attention_budget()
  Krok 5 (SUA) → Gardener.speculative_insight()

Prawa Guardian — żadnych nowych praw. Gardener respektuje wszystkie G1-G8.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from .antifragility import AntifragilityRegistry, RepairContext, MicroHeuristicPatch
from .attention_economy import AttentionBudget, UserAction, AttentionMode
from .playful_exploration import SandboxedPlayground, SpeculativeOutcome, OutcomeType


# ── Singleton ─────────────────────────────────────────────────────────────────

_gardener_lock = threading.Lock()
_gardener_instance: Optional["Gardener"] = None


class Gardener:
    """
    Singleton-orkiestrator ekosystemu ADRION 369 v2.0.

    Integruje AntifragilityRegistry, AttentionBudget i SandboxedPlayground
    i udostępnia hooki do punktów pętli operacyjnej MASTER ORCHESTRATOR.

    Użycie:
        gardener = Gardener()  # zwraca ten sam obiekt przy każdym wywołaniu
        gardener.before_checkpoint()
        gardener.after_repair_loop(repair_ctx)
        mode = gardener.audit_attention_budget()
        insight = gardener.speculative_insight()
    """
    __slots__ = ("_registry", "_budget", "_playground", "_checkpoints", "_lock")

    def __new__(cls) -> "Gardener":
        global _gardener_instance
        with _gardener_lock:
            if _gardener_instance is None:
                instance = object.__new__(cls)
                object.__setattr__(instance, "_registry", AntifragilityRegistry())
                object.__setattr__(instance, "_budget", AttentionBudget(max_cost=100.0))
                object.__setattr__(instance, "_playground", SandboxedPlayground())
                object.__setattr__(instance, "_checkpoints", [])
                object.__setattr__(instance, "_lock", threading.RLock())
                _gardener_instance = instance
            return _gardener_instance

    # ── Hooki orkiestratora ───────────────────────────────────────────────────

    def before_checkpoint(self) -> Dict[str, Any]:
        """
        Hook przed Krok 1.5 (RBC).
        Zapisuje stan ekosystemu (rejestry, budżet, playground) do snapshotu.
        Zwraca słownik snapshotu.
        """
        with self._lock:
            snapshot = {
                "timestamp": time.time(),
                "registry": self._registry.to_genesis_format(),
                "budget": self._budget.get_session_summary(),
                "playground": self._playground.get_state_snapshot(),
            }
            self._checkpoints.append(snapshot)
            return snapshot

    def after_repair_loop(self, repair_context: RepairContext) -> MicroHeuristicPatch:
        """
        Hook po pętli naprawczej (Krok 2.5, SAV fail → SAV pass).
        Wywołuje AntifragilityRegistry.learn_from_repair() i zwraca patch.
        """
        return self._registry.learn_from_repair(repair_context)

    def audit_attention_budget(self) -> str:
        """
        Hook przed Krok 3 (Audyt).
        Sprawdza AttentionBudget i zwraca rekomendację trybu komunikacji.
        """
        mode = self._budget.get_current_mode()
        markers = self._budget.frustration_markers

        if mode == AttentionMode.RECOVERY.value:
            return (
                f"RECOVERY: {markers} markerów frustracji. "
                "Wymuś RECOVERY_PROTOCOL — jeden krok, proste pytanie zamknięte."
            )
        if mode == AttentionMode.EMPATHY.value:
            return (
                f"EMPATHY: {markers} markery frustracji. "
                "Przełącz na EMPATHY_FIRST — krótkie podsumowanie, mniejsze kroki, "
                "brak pełnego PROTOCOL333."
            )
        return f"PRECISION: tryb normalny ({markers} markerów)."

    def speculative_insight(self) -> Optional[SpeculativeOutcome]:
        """
        Hook przed Krok 5 (SUA).
        Jeśli playground ma nowe insighty, zwraca najlepszy jako 'dziką kartę' do CTA.
        Insight jest automatycznie dodawany do kolejki importu.
        """
        insights = self._playground.get_insights()
        if not insights:
            return None

        # Wybierz insight z najwyższą pewnością
        best = max(insights, key=lambda o: o.confidence)
        self._playground.promote_to_main(best)
        return best

    # ── Checkpoint / Restore ──────────────────────────────────────────────────

    def restore_from_checkpoint(self, snapshot: Dict[str, Any]) -> None:
        """
        Odtwarza stan ekosystemu z snapshotu.
        Uwaga: registry jest append-only, więc restore nie usuwa wpisów —
        resetuje tylko budżet i playground do stanu z checkpointu.
        """
        with self._lock:
            budget_snap = snapshot.get("budget", {})
            if "frustration_markers" in budget_snap:
                # Reset sesji i ponowne zasymulowanie stanu (uproszczenie)
                self._budget.reset_session()

            # Playground: wyczyść graf spekulatywny (kolejka importu pozostaje)
            self._playground.clear_playground()

    # ── Akcje użytkownika (delegacja do AttentionBudget) ─────────────────────

    def record_user_action(self, action: UserAction) -> None:
        """Rejestruje akcję użytkownika w AttentionBudget."""
        self._budget.record_user_action(action)

    def start_new_session(self) -> None:
        """Resetuje sesję AttentionBudget (wywołaj przy FAZA_0 SessionLifecycle)."""
        self._budget.reset_session()
        self._playground.clear_playground()

    # ── Eksploracja spekulatywna (delegacja do Playground) ───────────────────

    def explore_hypothesis(self, hypothesis: str, vector: Optional[Dict] = None) -> list:
        """Uruchamia eksplorację w SandboxedPlayground."""
        return self._playground.explore(hypothesis, vector or {})

    # ── Stan i diagnostyka ────────────────────────────────────────────────────

    @property
    def registry(self) -> AntifragilityRegistry:
        return self._registry

    @property
    def budget(self) -> AttentionBudget:
        return self._budget

    @property
    def playground(self) -> SandboxedPlayground:
        return self._playground

    def get_status(self) -> Dict[str, Any]:
        """Pełny status ekosystemu (do logów Genesis Record)."""
        return {
            "ecosystem_version": "2.0.0",
            "gardener": "singleton",
            "registry_entries": self._registry.entry_count,
            "attention_mode": self._budget.get_current_mode(),
            "attention_spent": self._budget.spent,
            "playground_insights": len(self._playground.get_insights()),
            "checkpoint_count": len(self._checkpoints),
        }


# ── Reset singletona (tylko do testów) ────────────────────────────────────────

def _reset_gardener_singleton() -> None:
    """
    Resetuje singleton Gardener.
    TYLKO do użycia w testach — nie wywoływać w kodzie produkcyjnym.
    """
    global _gardener_instance
    with _gardener_lock:
        _gardener_instance = None
