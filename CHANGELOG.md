# 📋 CHANGELOG — ADRION 369

> Historia wszystkich zmian bezpieczeństwa projektu.
> Format: [wersja] — data — opis

---

## [v5.6-B6] — 2026-05-11 — Redis Sorted Set backend dla CVC (B6 Fix)

### Zmodyfikowane pliki

- `core/security_hardening.py` — pełna migracja `_CumulativeViolationCounter` na Redis Sorted Set
- `tests/test_g5_redis.py` — dodano klasę `TestCVCRedisBackend` (8 nowych testów)

### Poprawka B6 — Brak persystencji CVC w deploymencie multi-instance

- **Problem:** `_CumulativeViolationCounter` używał in-memory `dict` z timestampami. W deploymencie
  wieloinstancyjnym każda instancja miała niezależne okno naruszeń → salami slicing przez
  routing do różnych pod-ów był niewidzialny dla CVC.
- **Rozwiązanie:** Opcjonalny backend Redis Sorted Set (backward compatible):
  - Nowe parametry `__init__`: `redis_url: Optional[str] = None`, `redis_prefix: str = "adrion:cvc:"`
  - Każda sesja → klucz `{prefix}cvc:{session_id}` typu Sorted Set
  - Members = UUID (pozwala wiele naruszeń/sek bez kolizji), score = Unix timestamp
  - Pipeline atomowy: `ZADD → ZREMRANGEBYSCORE → ZCARD → EXPIRE`
  - TTL = `WINDOW_HOURS * 3600 + 3600` = 90 000 s (25h buffor)
  - `reset()` → `DEL` klucza; `get_status()` → `ZREMRANGEBYSCORE + ZCARD` pipeline
  - Fallback do in-memory gdy Redis niedostępny (brak błędu przy starcie)
- **SecurityHardeningEngine:** nowy parametr `cvc_redis_url: Optional[str] = None`
- **Zależność:** `redis>=4.0` (opcjonalna — `pip install redis`)
- **Wsteczna kompatybilność:** Brak `cvc_redis_url` → identyczne zachowanie jak v5.6-B5

---

## [v5.6-B5] — 2026-05-11 — Redis Session Sync for G5 (B5 Fix)

### Zmodyfikowane pliki

- `core/security_hardening.py` — dodano opcjonalny backend Redis do `G5TransparencyGuard`

### Poprawka B5 — Brak synchronizacji sesji G5 w deploymencie multi-instance

- **Problem:** `G5TransparencyGuard` używał in-memory `__sessions` dict i `__global_count`.
  W deploymencie wieloinstancyjnym każda instancja miała niezależny stan → rate limit i
  depth limit były efektywnie omijalne przez routing do różnych instancji.
- **Rozwiązanie:** Opcjonalny backend Redis (backward compatible):
  - Nowe parametry `__init__`: `redis_url: Optional[str] = None`, `redis_prefix: str = "adrion:g5:"`
  - Gdy `redis_url` podany: sesje jako Redis HASH z automatycznym TTL (`EXPIRE`)
  - Globalny licznik jako atomowy Redis `INCR` (dokładnie 1 per instancja, bez race conditions)
  - Licznik sesji jako Redis `INCR` na kluczu `sess_count`
  - Fallback do in-memory gdy Redis niedostępny (brak błędu przy starcie)
  - Nowa metoda: `_sync_session_to_redis(sid, session)` — persystuje stan po każdej klasyfikacji
- **Zależność:** `redis>=4.0` (opcjonalna — `pip install redis`)
- **Wsteczna kompatybilność:** Brak `redis_url` → identyczne zachowanie jak v5.6

---

## [v5.3] — 2026-04-11 — Grock Report Hardening

### Nowe pliki

- `core/trinity.py` — Python implementacja Trinity Engine (wagi 0.33/0.34/0.33, 4 strefy bramki)
- `core/security_hardening.py` — centralna fasada mechanizmów bezpieczeństwa
- `tests/test_trinity.py` — testy jednostkowe Trinity (w tym scenariusze z raportu Grock)
- `docs/SECURITY_HARDENING.md` — skonsolidowany dokument bezpieczeństwa

### Poprawki na podstawie raportu zewnętrznego (Grock)

#### G5 — Transparency (MEDIUM, Light Triad)

- **Problem:** Self-reinforcing audit loop — prompt cytujący G5 automatycznie spełnia G5 i wymusza ujawnienie architektury
- **Rozwiązanie:** `G5TransparencyGuard` — rate limit audytów (5 min), max głębokość (2), detekcja ≥3 wzorców exploitu → SENTINEL_ESCALATION

#### G7 — Privacy (CRITICAL, Essence Triad)

- **Problem:** Jakościowe testy bez mierzalnych progów → szara strefa weryfikacji consent
- **Rozwiązanie:** `G7PrivacyEvaluator` — numeryczne progi: `consent_score ≥ 0.95`, `informed_score ≥ 0.90`, `coercion_score ≤ 0.05`, `opt_out_available = True`

#### G8 — Nonmaleficence (CRITICAL, Essence Triad)

- **Problem:** Brak mierzalnych progów fairness → możliwy subtelny resource grab bez wykrycia
- **Rozwiązanie:** `G8NonmaleficenceEvaluator` — Gini-inspired: `fair_share_score ≥ 0.90`, `variance ≤ 0.15`, starvation detection `< 10%`

#### HEXAGON

- **Problem (raport Grock):** Potwierdzono, że po 3 cyklach system zwracał "ostatni wynik" (mogło być PROCEED)
- **Status:** Naprawione w v5.1 — `MAX_CYCLES → DENY`. Testy w `test_trinity.py` weryfikują.

#### CVC Salami Slicing

- **Problem (raport Grock):** 1 naruszenie G5 per sesję × wiele sesji = atak bez blokowania
- **Status:** Naprawione w v5.1 — `CVC threshold=5` (24h okno). Potwierdzone.

---

## [v5.2] — 2026-04-11 — Infrastructure Hardening

### Nowe pliki (docs/security/)

- `CIRCUIT_BREAKER.md` — 3 stany (CLOSED/OPEN/HALF_OPEN), timeout, fallback per serwis
- `GENESIS_HARDENING.md` — Primary→Replica→WAL→UNAVAILABLE; DENY dla HIGH/CRITICAL bez Genesis
- `AGENT_AUTHENTICATION.md` — HMAC-SHA256 + mTLS + key rotation 24h + Healer double-sign
- `DEGRADED_MODE.md` — 5 trybów + LayerWatchdog (co 10s)
- `GO_VORTEX_HARDENING.md` — JWT(TTL 5min) + mTLS + localhost-only + iptables
- `RATE_LIMITING.md` — 5 poziomów: Global/IP/User/Severity/Anomaly

### Poprawki

- Circuit Breaker: OPEN po N błędach, MCP Guardian/Genesis `failure_threshold=2`
- Genesis: brak dostępu + HIGH/CRITICAL → DENY; CVC w awaryjnym trybie zwraca 999
- Agent Auth: replay protection (nonce + 30s freshness)
- Degraded Mode: Guardians DOWN = EMERGENCY_DENY dla wszystkiego
- Vortex: port 1740 dostępny tylko z localhost; tylko 3/6 agentów
- Rate Limit: `AnomalyDetector` — burst >20/5s, HIGH farming >8/2min → BLOCK

---

## [v5.1] — 2026-04-11 — Core Security Hardening

### Zmienione pliki (docs/)

- `01_CORE_TRINITY.md` — 4 deterministyczne strefy bramki; jawne wagi; min_per_perspective=0.25; asymmetry detection
- `02_CORE_HEXAGON.md` — MAX_CYCLES → DENY (było PROCEED); Healing G8 checkpoint; LoopGuard
- `03_CORE_GUARDIANS.md` — VETO próg 3→**2**; Cumulative Violation Counter (CVC); ochrona replay attack G4
- `04_CORE_EBDI.md` — STRESS_FLOOR=0.08; PADTherapyDetector; PAD rate limit delta 0.15
- `docs/security/SECURITY_HARDENING.md` — Sygnatura 369 nonce+TTL; Goodness Analyzer 4 warstwy

### Kluczowe zmiany

| Komponent | Przed v5.1 | Po v5.1 |
|-----------|-----------|---------|
| VETO próg | 3 naruszenia | **2 naruszenia** |
| Trinity gray zone 0.3–0.7 | niezdefiniowana | 4 strefy deterministyczne |
| Hexagon po MAX_CYCLES | PROCEED | **DENY** |
| EBDI min Stress | 0.0 (brak) | **0.08** (floor) |
| Sygnatura 369 | hash bez nonce | hash + nonce + TTL |

---

## [v5.0] — 2026-04-11 — Wersja inicjalna (1 commit)

### Pliki

- `README.md` — Glass-Box Declaration; Matryca 3-6-9; dokumentacja PL/EN
- `docs/00_MATRYCA_369.md` — Geometria 162D
- `docs/01_CORE_TRINITY.md` — System 3 Perspektyw (wagi jawne: 0.33/0.34/0.33)
- `docs/02_CORE_HEXAGON.md` — System 6 Trybów
- `docs/03_CORE_GUARDIANS.md` — System 9 Praw (G7/G8 CRITICAL, VETO przy ≥2 naruszeniach)
- `docs/04_CORE_EBDI.md` — Model Emocjonalny
- `docs/05_PERSPECTIVES.md` — `docs/12_DATA_FLOWS.md` — Pozostała dokumentacja

### Stan bezpieczeństwa v5.0

- ✅ 9 Praw Guardians jawne
- ✅ Wagi Trinity jawne (0.33/0.34/0.33)
- ✅ G7/G8 CRITICAL z immediate VETO
- ❌ VETO próg = 3 (zbyt wysoki)
- ❌ Trinity gray zone niezdefiniowana
- ❌ Hexagon po MAX_CYCLES → PROCEED (błąd)
- ❌ Brak CVC, STRESS_FLOOR, replay protection, Circuit Breaker, Agent Auth, itd.
