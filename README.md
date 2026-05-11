# ADRION 369 — Architecture & Security

[![CI](https://github.com/Gruszkoland/adrion-369-architecture/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Gruszkoland/adrion-369-architecture/actions/workflows/ci.yml)

Security-hardened architecture, core Python pipeline, and Ecosystem v2.0 for the **ADRION 369** autonomous decision system.

## Structure

```
arbitrage/        # HexagonProcessor — 6-stage decision pipeline (Ecosystem v2.0 hooks)
core/             # TrinityEngine · SecurityHardeningEngine · Protocol333 orchestrator
ecosystem/        # Gardener · Antifragility · AttentionEconomy · PlayfulExploration
tests/            # 204 green tests (core + ecosystem + protocol333)
docs/             # Security hardening docs (v5.1–v5.6)
```

## Tests

```bash
pip install pytest pytest-cov
PYTHONPATH=. pytest tests/ -v --tb=short
```

**204 tests — all green:**
- 99/99 core (trinity + security_hardening + penetration)
- 88/88 ecosystem (antifragility + attention + gardener)
- 17/17 protocol333 (Trinity→Hexagon→Security pipeline)

## Architecture

- **Protocol333** — full pipeline orchestrator: Trinity → Hexagon (6 stages) → Security Hardening, with Gardener hooks at every stage
- **HexagonProcessor** — 6-stage sequential decision engine (Inventory → Empathy → Process → Debate → Healing → Action) with Ecosystem v2.0 Gardener repair hooks
- **TrinityEngine** — 3-zone scoring (Material / Intellectual / Essential)
- **SecurityHardeningEngine** — HMAC auth, rate limiting, circuit breaker, CVC

## Versions

| Tag | What changed |
|-----|-------------|
| B10 | `arbitrage/__init__.py` — formal Python package |
| B9  | `arbitrage/hexagon.py` — Gardener hooks stages 1-6 |
| B8  | `core/protocol333.py` — Protocol333 orchestrator |
| B7  | Ecosystem v2.0 (antifragility / attention / gardener) |
| v5.6 | Final hardening, 99/99 tests green |

## License

MIT — Gruszkoland/ADRION 369
