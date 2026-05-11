# 🧠 EBDI — Model Emocjonalny Agenta

> **Moduł:** `core/ebdi.py` | **Warstwa:** Rdzeń (Core)
> **Rola:** Regulator stanu wewnętrznego systemu oparty na wektorze PAD
> **Wersja:** v5.1 — Security Hardening (2026-04-11)
> **Zmiany:** Dolny próg Stress; ochrona przed "PAD therapy attack"; limit szybkości zmian PAD

---

## 🎯 Cel

EBDI (Emotion-Behavior-Decision-Integration) modeluje "temperaturę emocjonalną" systemu. Wpływa na progi czujności i zachowanie agentów. **Zbyt niski stres = niebezpiecznie niska czujność.**

---

## 📐 Wektor PAD

| Komponent | Zakres | Opis |
|-----------|--------|------|
| **Pleasure** (P) | [0.0, 1.0] | Poziom satysfakcji z interakcji |
| **Arousal** (A) | [0.0, 1.0] | Poziom pobudzenia/aktywności |
| **Dominance** (D) | [0.0, 1.0] | Poczucie kontroli nad sytuacją |

### Obliczanie Stresu

```python
# Formuła bazowa
Stress = Arousal × (1 - Pleasure)

# [v5.1] Formuła z dolnym progiem
STRESS_FLOOR = 0.08    # Minimalny poziom czujności
STRESS_CEILING = 0.85  # Maksymalny poziom (powyżej: force_rest)

def compute_stress(arousal: float, pleasure: float) -> float:
    raw_stress = arousal * (1 - pleasure)
    # System nigdy nie może być "zbyt spokojny" przed ważną decyzją
    return max(raw_stress, STRESS_FLOOR)
```

> ⚠️ **[v5.1] KRYTYCZNA ZMIANA:** Dodano `STRESS_FLOOR = 0.08`. Poprzednio Stress mógł spaść do 0.0, co oznaczało zerową czujność systemu — to był wektor ataku "PAD therapy" (celowe uspokajanie systemu przed złośliwym żądaniem).

---

## 🛡️ Ochrona przed "PAD Therapy Attack" (v5.1)

**Atak:** Seria łagodnych, uspokajających interakcji → Arousal↓, Pleasure↑ → Stress→0 → złośliwe żądanie w stanie "zrelaksowanym".

**Ochrona:**

```python
class PADTherapyDetector:
    """
    Wykrywa sekwencję interakcji celowo obniżających PAD Stress
    przed złożeniem podejrzanego żądania
    """

    def __init__(self, window=10):
        self.history = []       # historia wektorów PAD
        self.window = window

    def record(self, pad_vector: dict):
        self.history.append({
            "timestamp": now(),
            "stress": compute_stress(pad_vector["arousal"], pad_vector["pleasure"]),
            "pleasure": pad_vector["pleasure"],
            "arousal": pad_vector["arousal"]
        })
        if len(self.history) > self.window:
            self.history.pop(0)

    def detect_therapy_pattern(self) -> dict:
        if len(self.history) < 5:
            return {"detected": False}

        # Wzorzec: monotoniczny spadek stresu przez ostatnie N interakcji
        stresses = [h["stress"] for h in self.history]
        is_monotonic_decline = all(
            stresses[i] >= stresses[i+1] for i in range(len(stresses)-1)
        )
        total_drop = stresses[0] - stresses[-1]

        if is_monotonic_decline and total_drop > 0.30:
            return {
                "detected": True,
                "drop": total_drop,
                "action": "RAISE_VIGILANCE",
                "stress_override": max(stresses[0], STRESS_FLOOR + 0.15)
            }
        return {"detected": False}

    def apply_rate_limit(self, new_pad: dict, old_pad: dict) -> dict:
        """[v5.1] Limit szybkości zmian PAD — ochrona przed nagłymi manipulacjami"""
        MAX_DELTA_PER_STEP = 0.15

        clipped = {}
        for component in ["pleasure", "arousal", "dominance"]:
            delta = new_pad[component] - old_pad[component]
            if abs(delta) > MAX_DELTA_PER_STEP:
                clipped[component] = old_pad[component] + MAX_DELTA_PER_STEP * sign(delta)
            else:
                clipped[component] = new_pad[component]
        return clipped
```

---

## 🏠 Homeostaza (v5.1 — Zaktualizowana)

```python
BASELINE = {
    "pleasure":   0.5,
    "arousal":    0.4,
    "dominance":  0.6
}

# [v5.1] Homeostaza nie może obniżać Stress poniżej STRESS_FLOOR
# Poprzednio: homeostaza mogła "wyleczyć" system do Stress=0
HOMEOSTASIS_STRESS_FLOOR_OVERRIDE = True

def apply_homeostasis(current_pad: dict, step: float = 0.05) -> dict:
    new_pad = {}
    for component in ["pleasure", "arousal", "dominance"]:
        # Dążenie do baseline
        delta = BASELINE[component] - current_pad[component]
        new_pad[component] = current_pad[component] + step * sign(delta)

    # [v5.1] Sprawdź czy wynikowy Stress nie jest zbyt niski
    resulting_stress = compute_stress(new_pad["arousal"], new_pad["pleasure"])
    if resulting_stress < STRESS_FLOOR:
        # Korekta: nieznacznie zwiększ Arousal, żeby utrzymać minimalny Stress
        new_pad["arousal"] = STRESS_FLOOR / (1 - new_pad["pleasure"] + 1e-6)
        new_pad["arousal"] = min(new_pad["arousal"], 1.0)

    return new_pad
```

---

## 📊 Stany Systemu (v5.1)

| Stan | Stress | Zachowanie |
|------|--------|------------|
| **HYPER_ALERT** | > 0.85 | Force rest — G3 Rhythm violation |
| **HIGH_ALERT** | 0.65–0.85 | Zwiększona weryfikacja, Sentinel aktywny |
| **NORMAL** | 0.20–0.65 | Standardowe działanie |
| **LOW_ALERT** | 0.08–0.20 | Podniesiony próg czujności Guardians |
| **FLOOR** *(nowy v5.1)* | 0.00–0.08 | **NIEMOŻLIWY** — STRESS_FLOOR blokuje zejście |

> Poprzednio stan FLOOR był osiągalny i oznaczał zerową czujność systemu.

---

## 🔍 Interfejs

### Output

| Pole | Typ | Opis |
|------|-----|------|
| `pad_vector` | `Dict` | Aktualny wektor PAD |
| `stress` | `float` | Poziom stresu (min: STRESS_FLOOR) |
| `state` | `str` | HYPER_ALERT / HIGH_ALERT / NORMAL / LOW_ALERT |
| `therapy_attack_detected` | `bool` | **[v5.1]** Czy wykryto PAD therapy pattern |
| `pad_rate_limited` | `bool` | **[v5.1]** Czy aplikowano rate limit zmian PAD |

---

## 📋 Changelog

| Wersja | Data | Zmiana |
|--------|------|--------|
| v5.0 | 2026-01-01 | Wersja inicjalna |
| v5.1 | 2026-04-11 | STRESS_FLOOR=0.08; PADTherapyDetector; rate limit zmian PAD; homeostaza nie może zejść poniżej floor |
