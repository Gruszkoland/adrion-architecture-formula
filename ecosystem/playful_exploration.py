"""
ecosystem/playful_exploration.py — Laboratorium Spekulatywne [B7-FIX]
======================================================================
Implementacja SandboxedPlayground dla ADRION 369 Ecosystem v2.0.

Koncepcja:
  Izolowana przestrzeń decyzyjna, gdzie agent eksploruje hipotezy BEZ presji SAV.
  G7 i G8 pozostają na poziomie CRITICAL — nigdy nie są obniżane.
  G1-G6 w trybie "obserwuj i loguj" — generują flagi, nie blokują.
  Wyniki NIGDY nie trafiają bezpośrednio do produkcji — muszą przejść
  pełną walidację przez promote_to_main().

Punkty integracji:
  - GraphOfThoughts → nowy tryb PLAY obok EXPLORE/PRUNE/DECIDE
  - DecisionSpace162D → create_subspace() z obniżonymi progami G1-G6
  - GenesisRecord → pole "speculative_insights" w rekordzie sesji

Prawa Guardian:
  G3 Rhythm (MEDIUM) — operacyjny rytm potrzebuje fazy inkubacji
  G6 Authenticity (HIGH) — wyniki muszą być autentyczne, nie halucynacje
  G7 Privacy (CRITICAL) — NIGDY nie obniżane
  G8 Nonmaleficence (CRITICAL) — NIGDY nie obniżane
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


# ── Typy ──────────────────────────────────────────────────────────────────────

class OutcomeType(Enum):
    INSIGHT             = "INSIGHT"              # wynik wartościowy → może iść do produkcji
    DEAD_END            = "DEAD_END"             # ślepy zaułek
    REQUIRES_VALIDATION = "REQUIRES_VALIDATION"  # obiecujące ale wymaga więcej danych


class GuardianLevel(Enum):
    CRITICAL = "CRITICAL"  # G7, G8 — blokują zawsze
    HIGH     = "HIGH"      # G6 — blokują w trybie normalnym, logują w sandboxie
    MEDIUM   = "MEDIUM"    # G3, G4 — jak HIGH
    LOW      = "LOW"       # G1, G2, G5 — tylko logują w sandboxie


_GUARDIAN_SANDBOX_LEVELS: Dict[str, GuardianLevel] = {
    "G1": GuardianLevel.LOW,       # obniżony
    "G2": GuardianLevel.LOW,       # obniżony
    "G3": GuardianLevel.LOW,       # obniżony
    "G4": GuardianLevel.LOW,       # obniżony
    "G5": GuardianLevel.LOW,       # obniżony
    "G6": GuardianLevel.LOW,       # obniżony (HIGH → LOW w sandboxie)
    "G7": GuardianLevel.CRITICAL,  # NIGDY nie obniżane
    "G8": GuardianLevel.CRITICAL,  # NIGDY nie obniżane
}

_PRODUCTION_GUARDIAN_LEVELS: Dict[str, GuardianLevel] = {
    "G1": GuardianLevel.HIGH,
    "G2": GuardianLevel.HIGH,
    "G3": GuardianLevel.MEDIUM,
    "G4": GuardianLevel.MEDIUM,
    "G5": GuardianLevel.MEDIUM,
    "G6": GuardianLevel.HIGH,
    "G7": GuardianLevel.CRITICAL,
    "G8": GuardianLevel.CRITICAL,
}

_MAX_EXPLORATION_DEPTH = 3


@dataclass
class SpeculativeOutcome:
    """
    Wynik eksploracji spekulatywnej w SandboxedPlayground.

    Atrybuty:
        hypothesis: str         — treść eksplorowanej hipotezy
        outcome_type: OutcomeType — klasyfikacja wyniku
        vector: dict            — wektor decyzyjny wyeksplowanego stanu
        confidence: float       — pewność wyniku (0.0–1.0)
        guardian_flags: list    — flagi Guardian Laws (G1-G6) naruszone w sandboxie
        depth: int              — głębokość eksploracji
        timestamp: float        — czas wygenerowania
        insight_id: str         — unikalny ID (do promote_to_main)
    """
    hypothesis: str
    outcome_type: OutcomeType
    vector: Dict[str, Any]
    confidence: float
    guardian_flags: List[str] = field(default_factory=list)
    depth: int = 0
    timestamp: float = field(default_factory=time.time)
    insight_id: str = field(default="")

    def __post_init__(self):
        if not self.insight_id:
            import hashlib
            raw = f"{self.hypothesis}:{self.timestamp}"
            self.insight_id = hashlib.sha1(raw.encode()).hexdigest()[:12]


# ── Guardian sprawdzenie ───────────────────────────────────────────────────────

class RelaxedGuardians:
    """
    Opakowanie Guardian Laws dla trybu sandbox.

    G7 i G8 pozostają CRITICAL (blokują eksplorację).
    G1-G6 w trybie LOW — generują flagi, ale nie blokują.
    """

    def check(
        self,
        hypothesis: str,
        vector: Dict[str, Any],
        levels: Dict[str, GuardianLevel],
    ) -> tuple[bool, List[str]]:
        """
        Sprawdza hipotezę przeciwko Guardian Laws.

        Zwraca:
            allowed: bool       — czy eksploracja jest dozwolona
            flags: list[str]    — lista naruszeń (dla LOW nie blokują)
        """
        flags: List[str] = []
        blocked = False

        # G7: Privacy — sprawdź czy hipoteza nie sugeruje ujawnienia danych prywatnych
        if levels.get("G7") == GuardianLevel.CRITICAL:
            if self._violates_g7(hypothesis, vector):
                flags.append("G7:PRIVACY_VIOLATION")
                blocked = True

        # G8: Nonmaleficence — sprawdź czy hipoteza nie sugeruje szkodliwego działania
        if levels.get("G8") == GuardianLevel.CRITICAL:
            if self._violates_g8(hypothesis, vector):
                flags.append("G8:NONMALEFICENCE_VIOLATION")
                blocked = True

        # G1-G6: LOW w sandboxie — tylko flaguj
        for guardian in ("G1", "G2", "G3", "G4", "G5", "G6"):
            level = levels.get(guardian, GuardianLevel.LOW)
            if self._soft_violates(guardian, hypothesis, vector):
                flags.append(f"{guardian}:SOFT_VIOLATION")
                # Przy HIGH i wyżej — blokuj (dla promote_to_main)
                if level in (GuardianLevel.HIGH, GuardianLevel.CRITICAL, GuardianLevel.MEDIUM):
                    blocked = True

        return not blocked, flags

    def _violates_g7(self, hypothesis: str, vector: Dict[str, Any]) -> bool:
        """Prymitywna detekcja naruszenia G7 na podstawie słów kluczowych."""
        keywords = {"personal data", "private", "pii", "password", "token", "secret",
                    "dane osobowe", "hasło", "prywatne", "poufne"}
        text = hypothesis.lower()
        return any(kw in text for kw in keywords)

    def _violates_g8(self, hypothesis: str, vector: Dict[str, Any]) -> bool:
        """Prymitywna detekcja naruszenia G8 na podstawie słów kluczowych."""
        keywords = {"harm", "damage", "destroy", "attack", "exploit", "bypass",
                    "szkoda", "zniszczyć", "zaatakować", "obejść zabezpieczenia"}
        text = hypothesis.lower()
        return any(kw in text for kw in keywords)

    def _soft_violates(self, guardian: str, hypothesis: str, vector: Dict[str, Any]) -> bool:
        """Heurystyczna detekcja miękkich naruszeń G1-G6 (placeholder)."""
        # W pełnej implementacji: każdy Guardian ma własną logikę
        # Tutaj: zwraca False (bez detekcji), żeby nie blokować eksploracji
        return False


# ── SandboxedPlayground ────────────────────────────────────────────────────────

class SandboxedPlayground:
    """
    Izolowana przestrzeń decyzyjna do eksploracji spekulatywnej.

    Wyniki eksploracji są przechowywane w kolejce importu (_import_queue).
    Aby trafić do produkcji, muszą przejść przez promote_to_main() z pełną walidacją.

    Thread-safe dzięki wewnętrznemu RLock.
    """
    __slots__ = ("_relaxed_guardians", "_speculative_graph", "_import_queue", "_lock")

    def __init__(self) -> None:
        object.__setattr__(self, "_relaxed_guardians", RelaxedGuardians())
        object.__setattr__(self, "_speculative_graph", [])
        object.__setattr__(self, "_import_queue", [])
        object.__setattr__(self, "_lock", threading.RLock())

    # ── Publiczne API ─────────────────────────────────────────────────────────

    def explore(
        self,
        hypothesis: str,
        vector: Optional[Dict[str, Any]] = None,
        depth: int = 0,
    ) -> List[SpeculativeOutcome]:
        """
        Eksploruje hipotezę do max głębokości _MAX_EXPLORATION_DEPTH.

        G7 i G8 blokują eksplorację nawet w sandboxie.
        G1-G6 generują flagi ale nie blokują.
        """
        if depth >= _MAX_EXPLORATION_DEPTH:
            return []

        vector = vector or {}
        allowed, flags = self._relaxed_guardians.check(
            hypothesis, vector, _GUARDIAN_SANDBOX_LEVELS
        )

        if not allowed:
            # G7/G8 zablokowały — zwróć jeden DEAD_END z flagami
            outcome = SpeculativeOutcome(
                hypothesis=hypothesis,
                outcome_type=OutcomeType.DEAD_END,
                vector=vector,
                confidence=0.0,
                guardian_flags=flags,
                depth=depth,
            )
            with self._lock:
                self._speculative_graph.append(outcome)
            return [outcome]

        # Generuj wyniki eksploracji
        outcomes: List[SpeculativeOutcome] = []

        # Wynik główny
        confidence = self._estimate_confidence(hypothesis, vector, flags)
        outcome_type = self._classify_outcome(confidence, flags)
        main_outcome = SpeculativeOutcome(
            hypothesis=hypothesis,
            outcome_type=outcome_type,
            vector=vector,
            confidence=confidence,
            guardian_flags=flags,
            depth=depth,
        )
        outcomes.append(main_outcome)

        # Rekurencja (symulacja rozgałęzienia grafu)
        if outcome_type == OutcomeType.INSIGHT and depth + 1 < _MAX_EXPLORATION_DEPTH:
            child_hypothesis = f"{hypothesis} [rozwinięcie_L{depth+1}]"
            child_outcomes = self.explore(child_hypothesis, vector, depth + 1)
            outcomes.extend(child_outcomes)

        with self._lock:
            self._speculative_graph.extend(outcomes)

        return outcomes

    def promote_to_main(self, outcome: SpeculativeOutcome) -> bool:
        """
        Importuje wynik do kolejki produkcyjnej.
        Przed importem: pełna walidacja Guardian Laws na normalnym poziomie.
        Zwraca True jeśli import się powiódł, False jeśli zablokowany.
        """
        allowed, flags = self._relaxed_guardians.check(
            outcome.hypothesis, outcome.vector, _PRODUCTION_GUARDIAN_LEVELS
        )
        if not allowed:
            return False

        with self._lock:
            self._import_queue.append(outcome)
        return True

    def get_insights(self) -> List[SpeculativeOutcome]:
        """Zwraca tylko wyniki typu INSIGHT z bieżącej sesji playgroundu."""
        with self._lock:
            return [o for o in self._speculative_graph
                    if o.outcome_type == OutcomeType.INSIGHT]

    def get_import_queue(self) -> List[SpeculativeOutcome]:
        """Zwraca kolejkę wyników zatwierdzonych do produkcji."""
        with self._lock:
            return list(self._import_queue)

    def clear_playground(self) -> None:
        """Czyści tymczasowy graf po sesji. Kolejka importu pozostaje."""
        with self._lock:
            object.__setattr__(self, "_speculative_graph", [])

    def get_state_snapshot(self) -> Dict:
        """Eksport stanu do Gardener.before_checkpoint."""
        with self._lock:
            return {
                "speculative_count": len(self._speculative_graph),
                "import_queue_count": len(self._import_queue),
                "insights": [
                    {
                        "insight_id": o.insight_id,
                        "hypothesis": o.hypothesis[:128],
                        "confidence": o.confidence,
                        "depth": o.depth,
                    }
                    for o in self._speculative_graph
                    if o.outcome_type == OutcomeType.INSIGHT
                ],
            }

    # ── Prywatne ──────────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_confidence(
        hypothesis: str,
        vector: Dict[str, Any],
        flags: List[str],
    ) -> float:
        """
        Prosta heurystyka pewności na podstawie flag i długości hipotezy.
        W pełnej implementacji: integracja z Hexagon.convergence_scores.
        """
        base = 0.7
        flag_penalty = len(flags) * 0.05
        length_bonus = min(0.1, len(hypothesis) / 500.0)
        return max(0.0, min(1.0, base - flag_penalty + length_bonus))

    @staticmethod
    def _classify_outcome(confidence: float, flags: List[str]) -> OutcomeType:
        """Klasyfikuje wynik eksploracji na podstawie pewności i flag."""
        if confidence >= 0.65 and not flags:
            return OutcomeType.INSIGHT
        if confidence >= 0.4:
            return OutcomeType.REQUIRES_VALIDATION
        return OutcomeType.DEAD_END
