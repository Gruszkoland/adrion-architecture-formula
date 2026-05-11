# ADRION 369 — Ecosystem v2.0

> Layer filozoficzny: **Ekosystem, który uczy się, czuje i eksploruje**

## Opis

Ecosystem v2.0 to warstwa operacyjna ADRION 369 rozszerzająca MASTER ORCHESTRATOR
o trzy zasadnicze właściwości, których brakowało w v1.x:

| Właściwość | Moduł | Metafora |
|---|---|---|
| **Antykruchość** | `antifragility.py` | System rośnie z błędów |
| **Empatia** | `attention_economy.py` | System wyczuwa frustrację |
| **Spekulacja** | `playful_exploration.py` | System śni bez ryzyka |
| **Integracja** | `gardener.py` | Ogrodnik, który to łączy |

---

## Architektura

```
MASTER ORCHESTRATOR
│
├── Krok 1.5 (RBC) ──────────────── Gardener.before_checkpoint()
│                                         │
│                                    [snapshot = stan ekosystemu]
│
├── Krok 2.5 (SAV fail) ─────────── Gardener.after_repair_loop(context)
│                                         │
│                                    AntifragilityRegistry.learn_from_repair()
│                                         │
│                                    [patch dodany do append-only logu]
│
├── Krok 3 (Audyt) ──────────────── Gardener.audit_attention_budget()
│                                         │
│                                    AttentionBudget.get_current_mode()
│                                         │
│                                    "PRECISION" / "EMPATHY" / "RECOVERY"
│
└── Krok 5 (SUA) ────────────────── Gardener.speculative_insight()
                                          │
                                     SandboxedPlayground.get_insights()
                                          │
                                     [najlepszy insight jako CTA]
```

---

## Moduły

### `antifragility.py` — Silnik Antykruchości

**Problem rozwiązywany**: System v1.x zawsze zaczynał pętlę naprawczą od zera,
nie ucząc się z poprzednich błędów.

**Rozwiązanie**: `AntifragilityRegistry` — append-only log sygnatur błędów
i mikro-łatek (`MicroHeuristicPatch`) modyfikujących strategię naprawy.

```python
registry = AntifragilityRegistry()
patch = registry.learn_from_repair(repair_context)   # po SAV fail → pass
existing = registry.query_patch(task_vector)          # ≥ 85% podobieństwo
if existing:
    strategy = registry.apply_patch(existing, ctx)   # nowy dict bez mutacji
```

**Klasy:**
- `RepairContext(frozen=True)` — dane wejściowe pętli naprawczej
- `MicroHeuristicPatch` — modyfikacja strategii + statystyki sukcesu
- `AntifragilityRegistry(__slots__)` — thread-safe, append-only

---

### `attention_economy.py` — Ekonomia Uwagi

**Problem rozwiązywany**: System nie wykrywał frustracji użytkownika i oferował
kosztowne protokoły (FULL_PROTOCOL_333) w złym momencie.

**Rozwiązanie**: `AttentionBudget` śledzi markery frustracji i przełącza tryb
komunikacji: PRECISION → EMPATHY → RECOVERY.

```python
budget = AttentionBudget(max_cost=100.0)
budget.record_user_action(UserAction.PLAN_REJECTED)   # +1 marker
mode = budget.get_current_mode()                       # "EMPATHY" po 3+
if not budget.can_afford("FULL_PROTOCOL_333"):
    print(budget.suggest_downgrade())
```

**Tryby:**
| Markery frustracji | Tryb | Ograniczenia |
|---|---|---|
| 0–2 | PRECISION | brak |
| 3–4 | EMPATHY | blokuje operacje > 10 jednostek |
| 5+ | RECOVERY | blokuje operacje > 5 jednostek |

---

### `playful_exploration.py` — Laboratorium Spekulatywne

**Problem rozwiązywany**: Agent nie miał przestrzeni do eksperymentowania bez
ryzyka wpływu na decyzje produkcyjne.

**Rozwiązanie**: `SandboxedPlayground` — izolowana przestrzeń decyzyjna,
gdzie G1-G6 nie blokują eksploracji. **G7 i G8 zawsze na poziomie CRITICAL**.

```python
playground = SandboxedPlayground()
results = playground.explore("hipoteza architektoniczna")
insights = playground.get_insights()          # tylko INSIGHT, nie DEAD_END
success = playground.promote_to_main(insight) # pełna walidacja prod
```

**Gwarancje Guardian:**
- `G7 (Privacy)` — `CRITICAL` w sandboxie i produkcji. Nigdy nie obniżane.
- `G8 (Nonmaleficence)` — `CRITICAL` w sandboxie i produkcji. Nigdy nie obniżane.
- `G1-G6` — `LOW` w sandboxie (flagi, bez blokowania), `HIGH/MEDIUM` w produkcji.

---

### `gardener.py` — Ogrodnik (Singleton)

**Rola**: Singleton-integrator wszystkich trzech modułów. Udostępnia hooki
dla MASTER ORCHESTRATOR i zarządza cyklem życia ekosystemu.

```python
gardener = Gardener()  # singleton — każde wywołanie zwraca ten sam obiekt

# Hooki pętli operacyjnej:
snapshot = gardener.before_checkpoint()              # Krok 1.5
gardener.after_repair_loop(repair_context)           # Krok 2.5
mode_msg = gardener.audit_attention_budget()         # Krok 3
insight = gardener.speculative_insight()             # Krok 5

# Zarządzanie sesją:
gardener.start_new_session()                         # FAZA_0
gardener.record_user_action(UserAction.PLAN_REJECTED)
gardener.restore_from_checkpoint(snapshot)
```

---

## Prawa Guardian — zastosowanie

| Guardian | Poziom | Gdzie egzekwowane |
|---|---|---|
| G1 Autonomy | LOW (sandbox) / HIGH (prod) | `RelaxedGuardians` |
| G2 Harmony | MEDIUM | `AttentionBudget` — tryb EMPATHY |
| G3 Rhythm | LOW (sandbox) | `SandboxedPlayground._estimate_confidence` |
| G4 Causality | HIGH | `AntifragilityRegistry._derive_strategy` |
| G5 Transparency | MEDIUM | `to_genesis_format()` — pełny audit trail |
| G6 Authenticity | HIGH | `promote_to_main()` — full validation |
| **G7 Privacy** | **CRITICAL** | **`RelaxedGuardians._violates_g7()`** |
| **G8 Nonmaleficence** | **CRITICAL** | **`RelaxedGuardians._violates_g8()`** |

---

## Testy

```
tests/ecosystem/
├── __init__.py
├── test_antifragility.py       # 7 klas, ~20 testów
├── test_attention_economy.py   # 8 klas, ~25 testów
├── test_playful_exploration.py # 8 klas, ~22 testów
└── test_gardener.py            # 6 klas, ~18 testów
```

Uruchomienie:

```powershell
cd "C:\Users\adiha\Desktop\NAPRAWA REPO\push_staging"
C:\Users\adiha\.1_Projekty\162 demencje w schemacie 369\.venv\Scripts\python -m pytest tests\ecosystem -v
```

---

## Konwencje implementacyjne

- **Immutability**: `__slots__` + `object.__setattr__` w `__init__`; `frozen=True` dla `RepairContext`
- **Thread safety**: `threading.RLock()` na wszystkich współdzielonych stanach
- **Append-only**: `AntifragilityRegistry._entries` — brak metody usuwania wpisów
- **Singleton**: `Gardener.__new__` z podwójnym lockiem
- **Brak zależności od core/**: moduły ekosystemu są samodzielne — core/
  wywołuje hooki Gardener, nie odwrotnie

---

## Wersjonowanie

- `ecosystem/__init__.py`: `__version__ = "2.0.0"`
- Zgodne z ADRION 369 v5.6-B7
- CHANGELOG: `[B7-FIX] Ecosystem v2.0 — antifragility, attention, playground, gardener`
