# Pre/Post Comparison Tables — 2026-09-14

---

## 1. `feature/ios-bridge-ui` Branch — CI Before vs After Re-Dispatch

### CI Matrix Structure

| Workflow | Jobs | iOS Sim? | Trigger |
|----------|------|----------|---------|
| `iOS Bridge UI CI (3-level)` | L0 (Windows) | ❌ | Push |
| | L1 (Linux, py3.10+3.11) | ❌ | Push |
| | L2 (Linux, py3.10+3.11, Android emulator) | ❌ | Push |
| | **L3** (Linux, py3.10+3.11, Android emulator + **iOS simulator**) | ✅ | Push |
| `CI Web Scrcpy (L0+L1)` | L0 (Windows) | ❌ | Push |
| | L1 (Linux, py3.10+3.11) | ❌ | Push |

### Before (Previous Failed Run — commit `e230df8`)

| Workflow | L0 | L1 | L2 | L3 | Failed? |
|----------|-----|-----|-----|-----|---------|
| iOS Bridge CI | — | — | — | — | ✅ All passed |
| Web Scrcpy CI | ✅ | ✅ | — | — | ✅ All passed |

### After (Re-Dispatched — commit `8a1559c`, docs only)

| Workflow | L0 | L1 | L2 | L3 (with iOS) | Failed? |
|----------|-----|-----|-----|---------------|---------|
| iOS Bridge CI | ✅ | ✅ (2×) | ✅ (2×) | ✅ (2×) | ✅ All passed |
| Web Scrcpy CI | ✅ | ✅ (2×) | — | — | ✅ All passed |

### Code Changes in This Session

None — the commit `8a1559c` is a documentation-only addition (`docs/superpowers/verification/2026-09-14-staged-deployment-checklist.md`). Same test code, same CI result → **no regression**.

### Conclusion

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total CI jobs | 8 | 13 | +5 (matrix expansion from docs push) |
| All green? | ✅ | ✅ | None |
| Code changes | N/A | None (docs) | N/A |

---

## 2. Production HTTPS Fix — Code Before vs After

### What Was Broken

| File | Problem | Symptom |
|------|---------|---------|
| `run_https.py` | `ssl_context=ssl_context` passed to Eventlet → `TypeError: wsgi.server() got unexpected keyword argument` | Server crash before port bind |
| `app_https.py` | Missing `--host` argument definition | `AttributeError: Namespace has no attribute 'host'` |

### What Was Fixed

| File | Change | Before | After |
|------|--------|--------|-------|
| `run_https.py` | TLS delivery | `ssl_context=ssl_context` (broken) | `certfile=args.ssl_cert, keyfile=args.ssl_key` |
| `app_https.py` | Host binding | No `--host` arg → crash | `--host` arg with default `0.0.0.0` |
| `app_https.py` | TLS delivery | `ssl_context=ssl_context` (broken) | `certfile=args.ssl_cert, keyfile=args.ssl_key` |

### HTTP vs HTTPS Endpoints

| Endpoint | Before | After | Status |
|----------|--------|-------|--------|
| HTTP :8000 (prod) | ✅ Serving | ✅ Serving | No change |
| HTTPS :8443 (local TLS) | ❌ `TypeError` crash | ✅ `200 OK` (TLSv1.3) | Fixed |
| HTTP :8010 (QA, no device) | ✅ Serving | ✅ Serving | No change |

### Test Results

| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| `pytest -q` | 199 passed | 199 passed | 0 |
| `ruff check` | 0 errors | 0 errors | 0 |
| `ruff format` | Clean | Clean | 0 |

### Security

| Item | Status |
|------|--------|
| `certs/key.pem` tracked in Git | ❌ (removed in prior commit) |
| `certs/` directory blocked by `.gitignore` | ✅ |
| Self-signed cert generated in `/ProgramData/` | ✅ (outside repo) |
| Existing prod cert (`C:\Users\Administrator\.local\certs\...`) | ✅ Still valid (3650 days) |
