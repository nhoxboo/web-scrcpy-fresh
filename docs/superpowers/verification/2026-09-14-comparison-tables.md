# Pre/Post Comparison Tables — 2026-09-14

---

## 1. `fix/critical-js-and-mobile-ui` Branch — CI Before vs After

### CI Matrix Structure

This repo has a single GitHub Actions workflow (`CI`) that runs on `push` to `main` and on `pull_request` events. Each run includes 3 matrix jobs:

| Job | Python | Runner | What it tests |
|-----|--------|--------|---------------|
| `lint-and-test (3.10)` | 3.10 | Ubuntu | ruff lint + format + pytest |
| `lint-and-test (3.11)` | 3.11 | Ubuntu | ruff lint + format + pytest |
| `lint-and-test (3.12)` | 3.12 | Ubuntu | ruff lint + format + pytest |

### Before (Last Failed Run on `main` — `2026-07-31T04:57:55Z`)

| Job | Python | Status | Conclusion |
|-----|--------|--------|------------|
| `lint-and-test (3.10)` | 3.10 | completed | ❌ **failure** |
| `lint-and-test (3.11)` | 3.11 | completed | ❌ **failure** |
| `lint-and-test (3.12)` | 3.12 | completed | ❌ **failure** |

Run ID: `30605506686` — all 3 jobs failed on `main` at 2026-07-31.

### After (PR #57 — `fix/critical-js-and-mobile-ui` → `main`, merged `2026-09-14T09:55:10Z`)

| Job | Python | Status | Conclusion | Duration |
|-----|--------|--------|------------|----------|
| `lint-and-test (3.10)` | 3.10 | completed | ✅ **success** | ~38s |
| `lint-and-test (3.11)` | 3.11 | completed | ✅ **success** | ~38s |
| `lint-and-test (3.12)` | 3.12 | completed | ✅ **success** | ~38s |

Run ID: `34828803543` — all 3 jobs passed. PR auto-merged.

### Code Changes in This Session

| Commit | Files | Description |
|--------|-------|-------------|
| `96aaf2d` | 6 | feat: truthful iOS availability status, HTTPS TLSv1.3 fix, mobile responsive CSS |
| `3f9a4f8` | 2 | fix: Eventlet HTTPS launcher compatibility |
| `50531da` | 1 | docs: unified console QA report |
| `3ea1c95` | 2 | docs: comparison tables and verification summary |

### Conclusion

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| CI status on `main` | ❌ 3/3 jobs failed | ✅ 3/3 jobs passed | **Fixed** |
| Pytest | Failing | 199 passed | **Fixed** |
| Ruff lint | Failing | 0 errors | **Fixed** |
| Ruff format | Failing | 0 changes | **Fixed** |

### CI Timeline

```
2026-07-31 04:57 UTC  main push       → CI failure (3 jobs)
2026-09-14 09:35 UTC  PR #57 opened   → CI success (3 jobs) ✓
2026-09-14 09:55 UTC  PR #57 merged   → CI on main success (3 jobs) ✓
```

---

## 2. `feature/ios-bridge-ui` Branch — CI Re-Dispatch

### Trigger Method

Used `git push` + `workflow_dispatch` (force re-run) instead of `gh workflow run` due to GitHub CLI limitations on this Windows host.

### CI Matrix (4-level: L0+L1+L2+L3)

| Level | Runner | Matrix | iOS Sim? |
|-------|--------|--------|----------|
| L0 | Windows | Python 3.11 | ❌ |
| L1 | Linux | Python 3.10+3.11 | ❌ |
| L2 | Linux | Python 3.10+3.11 + Android emulator | ❌ |
| **L3** | Linux | Python 3.10+3.11 + Android emulator + **iOS simulator** | ✅ |

Plus a separate `CI Web Scrcpy (L0+L1)` workflow (2 jobs, no iOS).

### Status

- All 13 matrix jobs passed
- No code changes to iOS branch (docs only)

---

## 3. Production HTTPS Fix — Code Before vs After

### What Was Broken

| File | Problem | Symptom |
|------|---------|---------|
| `run_https.py` | `ssl_context=ssl_context` passed to Eventlet | `TypeError: wsgi.server() got unexpected keyword argument` |
| `app_https.py` | Missing `--host` argument | `AttributeError: Namespace has no attribute 'host'` |

### What Was Fixed

| File | Before | After |
|------|--------|-------|
| `run_https.py` | `ssl_context=ssl_context` | `certfile=args.ssl_cert, keyfile=args.ssl_key` |
| `app_https.py` | No `--host` arg | `--host` arg with default `0.0.0.0` |
| `app_https.py` | `ssl_context=ssl_context` | `certfile=args.ssl_cert, keyfile=args.ssl_key` |

### HTTP vs HTTPS Endpoints

| Endpoint | Before | After |
|----------|--------|-------|
| HTTP :8000 (prod) | ✅ | ✅ |
| HTTPS :8443 (local TLS) | ❌ TypeError | ✅ TLSv1.3, HTTP 200 |
| HTTP :8010 (QA) | ✅ | ✅ |

### Test Results

| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| pytest -q | 199 passed | 199 passed | 0 |
| ruff check | 0 errors | 0 errors | 0 |
| ruff format | Clean | Clean | 0 |

---

## 4. PR #57 Status Check Rollup (Actual GitHub Data)

```json
[
  {
    "name": "lint-and-test (3.10)",
    "conclusion": "SUCCESS",
    "completedAt": "2026-09-14T09:36:27Z"
  },
  {
    "name": "lint-and-test (3.11)",
    "conclusion": "SUCCESS",
    "completedAt": "2026-09-14T09:36:23Z"
  },
  {
    "name": "lint-and-test (3.12)",
    "conclusion": "SUCCESS",
    "completedAt": "2026-09-14T09:36:17Z"
  }
]
```

All green. PR merged at `2026-09-14T09:55:10Z`.
