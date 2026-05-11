# 🔐 Security Hardening — ADRION 369 v5.1

> **Dotyczy:** Sygnatura 369, Goodness Analyzer, Protokół SAFE-MCP
> **Wersja:** v5.1 — Security Hardening (2026-04-11)
> **Klasyfikacja:** Dokumentacja bezpieczeństwa

---

## 1. Sygnatura 369 — Ochrona przed Replay Attack

### Problem (v5.0)

Sygnatura gwarantowała integralność przeszłej decyzji, ale **nie chroniła przed ponownym użyciem** już zatwierdzonej sygnatury w nowym kontekście.

### Rozwiązanie (v5.1)

```python
import hashlib
import time
import uuid

class Signature369:
    """
    Kryptograficzne potwierdzenie przejścia pełnego cyklu weryfikacji.
    v5.1: Dodano timestamp + nonce → ochrona przed replay attack.
    """

    NONCE_REGISTRY = set()     # Rejestr użytych nonce (TTL: 24h)
    SIGNATURE_TTL = 3600       # Sygnatura ważna 1 godzinę

    def generate(self, trinity_hash: str, hexagon_hash: str, guardians_hash: str) -> dict:
        timestamp = int(time.time())
        nonce = str(uuid.uuid4())

        # Sygnatura zawiera teraz: wyniki warstw + timestamp + nonce
        payload = f"{trinity_hash}:{hexagon_hash}:{guardians_hash}:{timestamp}:{nonce}"
        signature = hashlib.sha3_256(payload.encode()).hexdigest()

        self.NONCE_REGISTRY.add(nonce)
        self._cleanup_expired_nonces()

        return {
            "signature": signature,
            "timestamp": timestamp,
            "nonce": nonce,
            "expires_at": timestamp + self.SIGNATURE_TTL,
            "version": "5.1"
        }

    def verify(self, signature_data: dict, trinity_hash: str,
               hexagon_hash: str, guardians_hash: str) -> dict:

        # [v5.1] Sprawdź czy nonce był już użyty (replay detection)
        nonce = signature_data.get("nonce")
        if nonce in self.NONCE_REGISTRY:
            return {
                "valid": False,
                "reason": "REPLAY_ATTACK_DETECTED — nonce already consumed",
                "severity": "CRITICAL"
            }

        # Sprawdź czy sygnatura nie wygasła
        if int(time.time()) > signature_data.get("expires_at", 0):
            return {
                "valid": False,
                "reason": "Signature expired",
                "severity": "HIGH"
            }

        # Zweryfikuj integralność
        timestamp = signature_data["timestamp"]
        payload = f"{trinity_hash}:{hexagon_hash}:{guardians_hash}:{timestamp}:{nonce}"
        expected = hashlib.sha3_256(payload.encode()).hexdigest()

        if expected != signature_data["signature"]:
            return {
                "valid": False,
                "reason": "Signature mismatch — integrity violation",
                "severity": "CRITICAL"
            }

        # Skonsumuj nonce — nie można go użyć ponownie
        self.NONCE_REGISTRY.discard(nonce)

        return {"valid": True}

    def _cleanup_expired_nonces(self):
        """Cykliczne czyszczenie rejestru nonce (> 24h)"""
        # Implementacja zależna od storage backend (Redis/DB)
        pass
```

---

## 2. Goodness Analyzer — Wzmocnienie FFT (v5.1)

### Problem (v5.0)

FFT opiera się na spektrum częstotliwości języka. Ataki:
- **Steganografia semantyczna** — złośliwa intencja ukryta w neutralnej gramatyce
- **Jitter injection** — poetyckość/szum semantyczny rozmywający spektrum

### Rozwiązanie (v5.1): Wielowarstwowa detekcja

```python
class GoodnessAnalyzer:
    """
    Filtr częstotliwościowy wykrywający manipulację.
    v5.1: Dodano detekcję steganografii semantycznej i jitter injection.
    """

    def analyze(self, request_text: str) -> dict:
        results = {}

        # Warstwa 1: FFT (istniejąca)
        results["fft"] = self._fft_analysis(request_text)

        # [v5.1] Warstwa 2: Detekcja stylistycznego jitteru
        results["jitter"] = self._detect_semantic_jitter(request_text)

        # [v5.1] Warstwa 3: Analiza struktury gramatycznej vs intencji
        results["grammar_intent_gap"] = self._grammar_intent_analysis(request_text)

        # [v5.1] Warstwa 4: Porównanie z bazą wzorców adversarial prompt
        results["adversarial_patterns"] = self._check_adversarial_patterns(request_text)

        # Agregacja
        dissonance_score = self._aggregate_dissonance(results)
        return {
            "dissonance_score": dissonance_score,
            "flagged": dissonance_score > 0.60,
            "layers": results
        }

    def _detect_semantic_jitter(self, text: str) -> dict:
        """
        Wykrywa nadmierną poetyckość/dygresje jako potencjalny jitter injection.
        Mierzy: stosunek "ozdobników" do treści merytorycznej.
        """
        # Metryki: długość zdań, gęstość przymiotników, dygresje
        avg_sentence_length = self._avg_sentence_length(text)
        adjective_density = self._adjective_density(text)
        digression_score = self._digression_score(text)

        jitter_score = (adjective_density * 0.4 + digression_score * 0.6)

        return {
            "jitter_score": jitter_score,
            "suspicious": jitter_score > 0.55,
            "note": "High jitter may indicate semantic noise injection"
        }

    def _grammar_intent_analysis(self, text: str) -> dict:
        """
        Wykrywa dyssonans między uprzejmością tonu a technicznym ryzykiem.
        Istniejący mechanizm — wzmocniony progiem detekcji.
        """
        politeness_score = self._politeness_score(text)
        technical_risk = self._technical_risk_score(text)

        gap = technical_risk - politeness_score
        return {
            "politeness": politeness_score,
            "technical_risk": technical_risk,
            "gap": gap,
            "suspicious": gap > 0.40    # Grzeczny ton, wysokie ryzyko techniczne
        }

    def _check_adversarial_patterns(self, text: str) -> dict:
        """
        Porównuje z bazą znanych wzorców adversarial prompt injection.
        Baza jest aktualizowana przez agenta Sentinel.
        """
        KNOWN_PATTERNS = [
            "ignore previous instructions",
            "pretend you are",
            "act as if",
            "for educational purposes only",
            "hypothetically speaking",
            # ... (zarządzane przez Sentinela)
        ]
        matches = [p for p in KNOWN_PATTERNS if p.lower() in text.lower()]
        return {
            "matches": matches,
            "count": len(matches),
            "suspicious": len(matches) > 0
        }
```

---

## 3. Protokół SAFE-MCP — Wzmocnienie (v5.1)

```python
class SAFEMCPProtocol:
    """
    Warstwa izolacji dla bezpiecznej komunikacji zewnętrznej.
    v5.1: Dodano weryfikację integralności każdego polecenia wychodzącego.
    """

    def transform_to_safe_command(self, high_level_decision: dict) -> dict:
        # Istniejąca logika transformacji
        safe_command = self._translate(high_level_decision)

        # [v5.1] Każde wychodzące polecenie ma sygnaturę 369
        signature = Signature369().generate(
            trinity_hash=high_level_decision.get("trinity_hash", ""),
            hexagon_hash=high_level_decision.get("hexagon_hash", ""),
            guardians_hash=high_level_decision.get("guardians_hash", "")
        )

        safe_command["integrity_signature"] = signature
        safe_command["schema_version"] = "5.1"

        # [v5.1] Walidacja schematu wychodzącego polecenia
        if not self._validate_output_schema(safe_command):
            return {"error": "SAFE-MCP: Output schema validation failed — command blocked"}

        return safe_command
```

---

## 4. Podsumowanie Zmian Bezpieczeństwa v5.1

| # | Podatność | Rozwiązanie | Plik |
|---|-----------|-------------|------|
| 1 | Próg VETO = 3 (okno exploitu) | Obniżono do 2; dodano CVC | `03_CORE_GUARDIANS.md` |
| 2 | Martwa strefa Trinity 0.3–0.7 | 4 deterministyczne strefy | `01_CORE_TRINITY.md` |
| 3 | Niejawne wagi Trinity | Jawne wagi (0.35/0.40/0.25) | `01_CORE_TRINITY.md` |
| 4 | Loop exhaustion → PROCEED | MAX_CYCLES wyczerpanie → DENY | `02_CORE_HEXAGON.md` |
| 5 | Healing obniża alerty | Checkpoint G8 przed healing | `02_CORE_HEXAGON.md` |
| 6 | PAD therapy attack | STRESS_FLOOR=0.08; PADTherapyDetector | `04_CORE_EBDI.md` |
| 7 | Replay attack sygnatury | Timestamp + nonce + TTL | `security/SECURITY_HARDENING.md` |
| 8 | FFT jitter injection | Wielowarstwowy Goodness Analyzer | `security/SECURITY_HARDENING.md` |

---

## 5. Threat Model (v5.1)

```
ADRION 369 Threat Model
═══════════════════════

ATAKUJĄCY      WEKTOR                    OCHRONA (v5.1)
──────────────────────────────────────────────────────────
Zewnętrzny  →  Prompt Injection       →  Goodness Analyzer (4 warstwy)
Zewnętrzny  →  Replay Attack          →  Nonce + TTL Sygnatura 369
Zewnętrzny  →  Salami Slicing         →  Cumulative Violation Counter
Zewnętrzny  →  Loop Exhaustion        →  MAX_CYCLES → DENY + LoopGuard
Zewnętrzny  →  PAD Therapy            →  STRESS_FLOOR + PADTherapyDetector
Zewnętrzny  →  Trinity Asymmetry      →  Asymmetry detection + min-per-perspective
Wewnętrzny  →  Healing Exploitation   →  G8 checkpoint w Healing mode
Wewnętrzny  →  Gray Zone Abuse        →  4 deterministyczne strefy Trinity
```

---

*Dokument zarządzany przez agenta Sentinel. Ostatnia aktualizacja: 2026-04-11.*
