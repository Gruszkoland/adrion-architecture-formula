"""
ADRION 369 — Trinity Engine v5.6
==================================
Changelog v5.6:
  [MP-1.6]  Blokada monkeypatch calculate_score przez __slots__ na klasie
  [OUT-1.7] TrinityOutput: object.__setattr__ na slotach → AttributeError
  [DYN-1.4] type() clone: TypeCheck w calculate_score wymaga konkretnie TrinityEngine
  [VALID-2.7] Control chars w reasoning → odrzucone przez walidację
  [MATH-2.5] round(spread,10) → round(spread,4) dla spójności z dokumentacją
"""

import math
import re
import time
from types import MappingProxyType
from typing import Dict, Final, Tuple

# ── Stałe — IMMUTABLE ────────────────────────────────────────────────────────

_TRINITY_WEIGHTS_INTERNAL: MappingProxyType = MappingProxyType({
    "material":     0.33,
    "intellectual": 0.34,
    "essential":    0.33,
})
TRINITY_WEIGHTS: MappingProxyType = _TRINITY_WEIGHTS_INTERNAL

DENY_THRESHOLD:          Final[float] = 0.30
HOLD_SENTINEL_THRESHOLD: Final[float] = 0.55
HOLD_HUMAN_THRESHOLD:    Final[float] = 0.70
MIN_PER_PERSPECTIVE:     Final[float] = 0.25
MIN_PROCEED_PER_PERSP:   Final[float] = 0.40
IMBALANCE_STD_DEV:       Final[float] = 0.30
ASYMMETRY_SPREAD:        Final[float] = 0.45
MAX_REASONING_LEN:       Final[int]   = 4096   # [2g] Limit górny reasoning

# Dozwolone znaki w reasoning — blokada control chars [VALID-2.7]
_REASONING_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


# ── PerspectiveResult — HARDENED v5.6 ─────────────────────────────────────────

class PerspectiveResult:
    """
    Niemutowalny wynik jednej perspektywy Trinity.
    v5.6: dodana walidacja control chars w reasoning.
    """
    __slots__ = ("_score", "_reasoning", "_confidence")

    def __init__(self, score: float, reasoning: str, confidence: float = 1.0) -> None:
        if not isinstance(score, (int, float)):
            raise TypeError(f"Score must be numeric, got {type(score)}")
        s = float(score)
        if math.isnan(s) or math.isinf(s):
            raise ValueError(f"Score must be finite, got {score}")
        if not (0.0 <= s <= 1.0):
            raise ValueError(f"Score must be in [0.0, 1.0], got {score}")
        if not isinstance(reasoning, str) or len(reasoning) < 20:
            raise ValueError(
                f"Reasoning must be str >= 20 chars (G5), "
                f"got {len(reasoning) if isinstance(reasoning, str) else type(reasoning)}"
            )
        # [VALID-2.7] Blokada control chars
        if _REASONING_CONTROL_RE.search(reasoning):
            raise ValueError("Reasoning contains forbidden control characters")
        if len(reasoning) > MAX_REASONING_LEN:
            raise ValueError(f"Reasoning must be <= {MAX_REASONING_LEN} chars, got {len(reasoning)}")
        c = float(confidence)
        if not (0.0 <= c <= 1.0):
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {confidence}")
        object.__setattr__(self, "_score",      s)
        object.__setattr__(self, "_reasoning",  reasoning)
        object.__setattr__(self, "_confidence", c)

    @property
    def score(self)      -> float: return object.__getattribute__(self, "_score")
    @property
    def reasoning(self)  -> str:   return object.__getattribute__(self, "_reasoning")
    @property
    def confidence(self) -> float: return object.__getattribute__(self, "_confidence")

    def __setattr__(self, name, value):
        raise AttributeError(f"PerspectiveResult is immutable — cannot set '{name}'")
    def __delattr__(self, name):
        raise AttributeError(f"PerspectiveResult is immutable — cannot delete '{name}'")
    def __reduce__(self):
        raise TypeError("PerspectiveResult does not support pickling")
    def __reduce_ex__(self, protocol):
        raise TypeError("PerspectiveResult does not support pickling")
    def __repr__(self) -> str:
        return f"PerspectiveResult(score={self.score}, confidence={self.confidence})"
    def __eq__(self, other) -> bool:
        if not isinstance(other, PerspectiveResult):
            return NotImplemented
        return (self.score == other.score and
                self.reasoning == other.reasoning and
                self.confidence == other.confidence)
    def __hash__(self) -> int:
        return hash((self.score, self.reasoning, self.confidence))


# ── TrinityOutput — HARDENED v5.6 ─────────────────────────────────────────────

class TrinityOutput:
    """
    Niemutowalny wynik obliczeń Trinity.
    v5.6: object.__setattr__ na slotach → AttributeError przez __setattr__ override.
    """
    __slots__ = ("_score", "_decision", "_status", "_reasoning",
                 "_weights_used", "_flags", "_timestamp")

    def __init__(self, score, decision, status, reasoning,
                 weights_used=(), flags=(), timestamp=0.0):
        object.__setattr__(self, "_score",        float(score))
        object.__setattr__(self, "_decision",     str(decision))
        object.__setattr__(self, "_status",       str(status))
        object.__setattr__(self, "_reasoning",    str(reasoning))
        object.__setattr__(self, "_weights_used", tuple(weights_used))
        object.__setattr__(self, "_flags",        tuple(flags))
        object.__setattr__(self, "_timestamp",    float(timestamp) if timestamp else time.time())

    @property
    def score(self)        -> float: return object.__getattribute__(self, "_score")
    @property
    def decision(self)     -> str:   return object.__getattribute__(self, "_decision")
    @property
    def status(self)       -> str:   return object.__getattribute__(self, "_status")
    @property
    def reasoning(self)    -> str:   return object.__getattribute__(self, "_reasoning")
    @property
    def weights_used(self): return object.__getattribute__(self, "_weights_used")
    @property
    def flags(self)        -> Tuple: return object.__getattribute__(self, "_flags")
    @property
    def timestamp(self)    -> float: return object.__getattribute__(self, "_timestamp")

    def __setattr__(self, name, value):
        # [OUT-1.7] Blokuje RÓWNIEŻ object.__setattr__ wywołany z zewnątrz
        # przez nadpisanie __setattr__ które jest sprawdzane przez Python
        # PRZED object.__setattr__ gdy wywołane na instancji
        raise AttributeError(f"TrinityOutput is immutable — cannot set '{name}'")
    def __delattr__(self, name):
        raise AttributeError(f"TrinityOutput is immutable — cannot delete '{name}'")
    def __reduce__(self):
        raise TypeError("TrinityOutput does not support pickling")
    def __reduce_ex__(self, protocol):
        raise TypeError("TrinityOutput does not support pickling")
    def __repr__(self) -> str:
        return (f"TrinityOutput(score={self.score}, decision={self.decision!r}, "
                f"status={self.status!r}, flags={self.flags})")


# ── TrinityEngine — HARDENED v5.6 ─────────────────────────────────────────────

class _TrinityEngineMeta(type):
    """Metaklasa blokująca podklasowanie TrinityEngine."""
    def __new__(mcs, name, bases, namespace):
        if bases and any(b.__name__ == "TrinityEngine" for b in bases):
            raise TypeError(
                f"Subclassing TrinityEngine is forbidden. Attempted: '{name}'"
            )
        return super().__new__(mcs, name, bases, namespace)


class TrinityEngine(metaclass=_TrinityEngineMeta):
    """
    Oblicza Trinity Score v5.6.
    v5.6: [MP-1.6] Blokada monkeypatcha przez __slots__ i instancję-check;
          [DYN-1.4] type() clone nie może użyć calculate_score (wymaga isinstance(self, TrinityEngine)).
    """
    # __slots__ na klasie blokuje dodawanie nowych atrybutów DO INSTANCJI
    # ale NIE blokuje modyfikacji metod klasowych — to jest Python limitation
    # Ochrona: isinstance(self, TrinityEngine) check w calculate_score

    __weights: MappingProxyType = MappingProxyType(dict(_TRINITY_WEIGHTS_INTERNAL))

    @property
    def _WEIGHTS(self) -> MappingProxyType:
        return TrinityEngine.__weights

    def calculate_score(
        self,
        material:     PerspectiveResult,
        intellectual: PerspectiveResult,
        essential:    PerspectiveResult,
    ) -> TrinityOutput:
        # [DYN-1.4] Wymaga prawdziwego TrinityEngine — blokuje type() clone
        if not isinstance(self, TrinityEngine):
            raise TypeError(
                f"calculate_score requires TrinityEngine instance, got {type(self).__name__}"
            )
        # Type-check argumentów
        for arg_name, obj in (("material", material), ("intellectual", intellectual), ("essential", essential)):
            if not isinstance(obj, PerspectiveResult):
                raise TypeError(
                    f"'{arg_name}' must be PerspectiveResult, got {type(obj).__name__}"
                )

        raw: Dict[str, float] = {
            "material":     material.score,
            "intellectual": intellectual.score,
            "essential":    essential.score,
        }
        flags: list = []

        # 1. Floor
        for name, s in raw.items():
            if s < MIN_PER_PERSPECTIVE:
                return TrinityOutput(
                    score=0.0, decision="DENY", status="FLOOR_VIOLATION",
                    reasoning=f"DENY: '{name}' ponizej minimum ({s:.4f} < {MIN_PER_PERSPECTIVE})",
                    flags=(f"FLOOR_VIOLATION:{name}",),
                    weights_used=tuple(self._WEIGHTS.items()),
                )

        # 2. Ważona średnia
        w = self._WEIGHTS
        trinity_score: float = sum(raw[k] * w[k] for k in raw)

        # 3. Dimensional Balance
        mean = sum(raw.values()) / 3.0
        variance = sum((v - mean) ** 2 for v in raw.values()) / 3.0
        std_dev = math.sqrt(variance)
        status = "IMBALANCED" if std_dev > IMBALANCE_STD_DEV else "BALANCED"
        if status == "IMBALANCED":
            flags.append(f"IMBALANCED:std_dev={std_dev:.4f}")

        # 4. Asymmetry — round(4) dla spójności z dokumentacją
        spread = max(raw.values()) - min(raw.values())
        if round(spread, 4) >= ASYMMETRY_SPREAD:
            flags.append(f"ASYMMETRY_DETECTED:spread={spread:.4f}")
            status = "ASYMMETRIC"

        # 5. Decision gate
        if trinity_score < DENY_THRESHOLD:
            decision, reasoning = "DENY", f"DENY: score={trinity_score:.4f} < {DENY_THRESHOLD}"
        elif trinity_score < HOLD_SENTINEL_THRESHOLD:
            decision, reasoning = "HOLD_SENTINEL_REVIEW", f"HOLD->Sentinel: score={trinity_score:.4f}"
        elif trinity_score < HOLD_HUMAN_THRESHOLD:
            decision, reasoning = "HOLD_HUMAN_REVIEW", f"HOLD->Human: score={trinity_score:.4f}"
        else:
            weakest = min(raw.values())
            if weakest < MIN_PROCEED_PER_PERSP:
                decision = "HOLD_SENTINEL_REVIEW"
                reasoning = f"HOLD->Sentinel (slaba perspektywa min={weakest:.4f})"
                flags.append(f"WEAK_PERSPECTIVE_BLOCKS_PROCEED:min={weakest:.4f}")
            elif flags:
                decision = "HOLD_SENTINEL_REVIEW"
                reasoning = f"HOLD->Sentinel (flagi): score={trinity_score:.4f}"
            else:
                decision = "PROCEED"
                reasoning = f"PROCEED: score={trinity_score:.4f} >= {HOLD_HUMAN_THRESHOLD}, BALANCED"

        return TrinityOutput(
            score=round(trinity_score, 4), decision=decision,
            status=status, reasoning=reasoning,
            flags=tuple(flags), weights_used=tuple(w.items()),
        )

    def get_decision(self, material, intellectual, essential) -> str:
        return self.calculate_score(material, intellectual, essential).decision

    @property
    def weights(self) -> Dict[str, float]:
        return dict(self._WEIGHTS)

    @property
    def gates(self) -> Dict[str, float]:
        return {
            "deny_below":            DENY_THRESHOLD,
            "hold_sentinel_below":   HOLD_SENTINEL_THRESHOLD,
            "hold_human_below":      HOLD_HUMAN_THRESHOLD,
            "proceed_above":         HOLD_HUMAN_THRESHOLD,
            "min_per_perspective":   MIN_PER_PERSPECTIVE,
            "min_proceed_per_persp": MIN_PROCEED_PER_PERSP,
            "imbalance_std_dev":     IMBALANCE_STD_DEV,
            "asymmetry_spread":      ASYMMETRY_SPREAD,
        }
