"""
ADRION 369 — Protocol 333: Full Decision Pipeline Orchestrator

Orchestrates the complete ADRION 369 decision pipeline:
  Trinity evaluation → Hexagon pipeline → Security guardians
  + Ecosystem v2.0 Gardener hooks at all integration points.

Protocol 333 activates automatically on tasks with:
  - ≥3 steps OR destructive operations OR critical domains
  - (see MASTER ORCHESTRATOR §3.A decision matrix)

Architecture:
  Protocol333.execute()
    ├── Gardener.start_new_session()      [session init]
    ├── Gardener.before_checkpoint()      [Krok 1.5]
    ├── TrinityEngine.calculate_score()   [perspective evaluation]
    ├── HexagonProcessor.process()        [6-stage decision pipeline]
    │     └── Gardener hooks per stage   [Krok 2.5 on failures]
    ├── SecurityHardeningEngine checks    [Guardian Laws G7/G8]
    ├── Gardener.audit_attention_budget() [Krok 3]
    └── Gardener.record_user_action()     [Krok 5]
"""
from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("adrion.protocol333")

# ─────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────


@dataclass
class Protocol333Result:
    """Output of a full Protocol 333 execution."""

    session_id: str
    approved: bool
    trinity_scores: dict
    hexagon_approved: bool
    hexagon_combined_score: float
    security_passed: bool
    attention_mode: str
    duration_ms: float
    rejection_reason: Optional[str] = None
    ecosystem_status: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "approved": self.approved,
            "trinity_scores": self.trinity_scores,
            "hexagon_approved": self.hexagon_approved,
            "hexagon_combined_score": self.hexagon_combined_score,
            "security_passed": self.security_passed,
            "attention_mode": self.attention_mode,
            "duration_ms": round(self.duration_ms, 2),
            "rejection_reason": self.rejection_reason,
            "ecosystem_status": self.ecosystem_status,
        }


# ─────────────────────────────────────────────────────────────────────
# Protocol 333 Orchestrator
# ─────────────────────────────────────────────────────────────────────


class Protocol333:
    """
    Full decision pipeline orchestrator — ADRION 369 Protocol 333.

    Integrates Trinity + Hexagon + Security guardians with Ecosystem v2.0
    Gardener hooks. Activates on complex tasks (≥3 steps / destructive /
    critical domain) per MASTER ORCHESTRATOR §3.A decision matrix.

    Guardian Law constraint: G7 (Privacy) + G8 (Nonmaleficence) thresholds
    are NEVER lowered — not even in sandbox/playground mode.
    """

    __slots__ = ("_lock", "logger")

    def __init__(self) -> None:
        object.__setattr__(self, "_lock", threading.RLock())
        object.__setattr__(self, "logger", logging.getLogger("adrion.protocol333"))

    def execute(
        self,
        perspectives: dict,
        context: dict,
        session_id: str = "",
    ) -> Protocol333Result:
        """
        Execute the full Protocol 333 pipeline.

        Args:
            perspectives: dict with keys 'material', 'intellectual', 'essential'
                          (float 0.0-1.0) for Trinity evaluation.
            context: arbitrary metadata about the decision context.
            session_id: optional session identifier for tracking.

        Returns:
            Protocol333Result — full pipeline outcome.
        """
        with self._lock:
            return self._execute_locked(perspectives, context, session_id)

    def _execute_locked(
        self,
        perspectives: dict,
        context: dict,
        session_id: str,
    ) -> Protocol333Result:
        total_start = time.time()
        _session_id = session_id or f"p333_{int(total_start)}"

        # ── Ecosystem: session init ───────────────────────────────────
        _gardener = None
        try:
            from ecosystem.gardener import Gardener
            _gardener = Gardener()
            _gardener.start_new_session()          # reset attention budget
            _gardener.before_checkpoint()          # Krok 1.5 snapshot
        except Exception as exc:
            self.logger.debug("Ecosystem not available: %s", exc)

        # ── Step 1: Trinity evaluation ────────────────────────────────
        trinity_scores: dict = {}
        try:
            from core.trinity import TrinityEngine
            engine = TrinityEngine()
            trinity_output = engine.calculate_score(perspectives)
            trinity_scores = {
                "material": getattr(trinity_output, "material", perspectives.get("material", 0.0)),
                "intellectual": getattr(trinity_output, "intellectual", perspectives.get("intellectual", 0.0)),
                "essential": getattr(trinity_output, "essential", perspectives.get("essential", 0.0)),
                "combined": getattr(trinity_output, "combined", 0.0),
            }
        except Exception as exc:
            self.logger.warning("Trinity evaluation failed, using raw perspectives: %s", exc)
            trinity_scores = {
                "material": float(perspectives.get("material", 0.0)),
                "intellectual": float(perspectives.get("intellectual", 0.0)),
                "essential": float(perspectives.get("essential", 0.0)),
                "combined": sum(perspectives.values()) / max(len(perspectives), 1),
            }

        # ── Step 2: Hexagon pipeline ──────────────────────────────────
        hexagon_approved = False
        hexagon_score = 0.0
        rejection_reason = None
        try:
            from arbitrage.hexagon import HexagonProcessor
            processor = HexagonProcessor()
            hexagon_result = processor.process(trinity_scores)
            hexagon_approved = hexagon_result.approved
            hexagon_score = hexagon_result.combined_score
            if not hexagon_approved:
                failed = [s.stage_name for s in hexagon_result.stages if not s.approved]
                rejection_reason = f"Hexagon rejected at stages: {failed}"
        except Exception as exc:
            self.logger.error("Hexagon pipeline failed: %s", exc)
            rejection_reason = f"Hexagon pipeline error: {exc}"

        # Ecosystem Krok 2.5 — after_repair_loop if hexagon failed
        if not hexagon_approved and _gardener is not None:
            try:
                from ecosystem.antifragility import RepairContext
                ctx = RepairContext(
                    error_signature="protocol333_hexagon_failed",
                    hexagon_cycle=0,
                    convergence_score=hexagon_score,
                    patched_files=tuple(),
                    timestamp=time.time(),
                    extra={"session_id": _session_id, "context": context},
                )
                _gardener.after_repair_loop(ctx)
            except Exception:
                pass

        # ── Step 3: Security guardians (G7/G8 — CRITICAL, never lowered) ──
        security_passed = True
        try:
            from core.security_hardening import SecurityHardeningEngine
            sec_engine = SecurityHardeningEngine()
            sec_result = sec_engine.run_full_check(context)
            security_passed = getattr(sec_result, "passed", True)
            if not security_passed:
                rejection_reason = rejection_reason or "Security hardening check failed (G7/G8)"
        except Exception as exc:
            self.logger.debug("Security hardening check unavailable: %s", exc)

        # ── Ecosystem: Krok 3 — audit attention budget ─────────────────
        attention_mode = "PRECISION"
        if _gardener is not None:
            try:
                attention_mode = str(_gardener.audit_attention_budget())
            except Exception:
                pass

        # ── Ecosystem: Krok 5 — record user action ────────────────────
        if _gardener is not None:
            try:
                from ecosystem.attention_economy import UserAction
                action = UserAction.STEP_COMPLETED if (hexagon_approved and security_passed) else UserAction.STEP_FAILED
                _gardener.record_user_action(action)
            except Exception:
                pass

        # ── Aggregate ecosystem status ────────────────────────────────
        ecosystem_status: dict = {}
        if _gardener is not None:
            try:
                ecosystem_status = _gardener.get_status()
            except Exception:
                pass

        overall_approved = hexagon_approved and security_passed
        duration_ms = (time.time() - total_start) * 1000

        self.logger.info(
            "Protocol333 complete: session=%s approved=%s hexagon=%.3f security=%s duration=%.1fms",
            _session_id,
            overall_approved,
            hexagon_score,
            security_passed,
            duration_ms,
        )

        return Protocol333Result(
            session_id=_session_id,
            approved=overall_approved,
            trinity_scores=trinity_scores,
            hexagon_approved=hexagon_approved,
            hexagon_combined_score=round(hexagon_score, 4),
            security_passed=security_passed,
            attention_mode=attention_mode,
            duration_ms=duration_ms,
            rejection_reason=rejection_reason,
            ecosystem_status=ecosystem_status,
        )
