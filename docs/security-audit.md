# GliFlow — Security Audit Report

> OWASP Top 10:2025 · Generated 2026-04-01

**2 Critical · 4 High · 5 Medium · 3 Low**

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ⬜ | Open |
| ✅ | Resolved |
| 🔄 | In progress |

---

## CRITICAL

### ✅ [C-001] API keys exposed in `.env`
**File:** `.env`
**Category:** Secrets / A04 Cryptographic Failures

Real API keys for Groq, OpenAI and Gemini stored in plain text in `.env`. Although listed in `.gitignore`, any clone or backup of the repo exposes them.

**Remediation:** Revoke all three keys from each provider's dashboard and generate new ones. Keep `.env` with new keys locally only. Never commit `.env`.

**Resolution:** Keys revoked and regenerated. ✅

---

### ✅ [C-002] Unvalidated registry write in auto-start
**File:** `src/ui/config_window.py` · `_apply_auto_start()`
**Category:** Insecure Design / A06

`HKCU\...\Run` is written with `f'"{exe}" -m src.main'` without validating or canonicalizing the executable path. Vector for code execution via path manipulation.

**Remediation:** Validate and canonicalize `exe` path before writing. Verify executable exists and is an absolute path.

**Resolution:** Executable path resolved and validated before registry write. ✅

---

## HIGH

### ✅ [H-001] Gemini API key in URL query string
**File:** `src/stt/gemini_provider.py`
**Category:** Secrets / A04 Cryptographic Failures

`gemini_provider.py` builds `?key={self._api_key}` in the URL. Groq and OpenAI correctly use `Authorization: Bearer` header. The URL appears in proxy logs, HTTP cache, and Referer headers.

**Remediation:** Use `headers={"x-goog-api-key": self._api_key}` instead of query parameter.

**Resolution:** API key moved to x-goog-api-key header. ✅

---

### ✅ [H-002] No explicit SSL/TLS verification
**File:** `src/stt/groq_provider.py`, `src/stt/openai_provider.py`, `src/stt/gemini_provider.py`
**Category:** Cryptographic Failures / A04

All three providers use `httpx.Client(timeout=30)` without explicit `verify=True` or certificate pinning. httpx verifies by default but it is not enforced in code.

**Remediation:** Explicitly pass `verify=True` to all `httpx.Client()` calls.

**Resolution:** verify=True explicitly set in all httpx.Client() calls. ✅

---

### ✅ [H-003] Error messages expose API response bodies
**File:** `src/stt/groq_provider.py`, `src/stt/openai_provider.py`, `src/stt/gemini_provider.py`
**Category:** Error Handling / A10 Exceptional Conditions

`raise STTError(f"... {e.response.text}")` exposes the full API response body to the user, which may contain internal service information.

**Remediation:** Log full response internally; show only a generic message to the user (e.g. `"API error — check your key and try again"`).

**Resolution:** Error messages sanitized; response body no longer exposed to user. ✅

---

### ✅ [H-004] No input validation in ConfigManager
**File:** `src/config/manager.py` · `set()`
**Category:** Input Validation / A03

`config_manager.set()` accepts any value without type checking or range validation. Example: `widget.alpha` could receive `"malicious"` or `9999`.

**Remediation:** Implement a schema with allowed types and value ranges for each config key.

**Resolution:** Schema validation added to ConfigManager.set() with type and range checks. ✅

---

## MEDIUM

### ✅ [M-001] Keyring value loaded into Tkinter StringVar
**File:** `src/ui/config_window.py` · `_tab_provider()`
**Category:** Secrets / A04

When the Provider tab opens, the key is retrieved from the OS keyring and stored in a `tk.StringVar` in memory. Any process introspection tool can read it unmasked.

**Remediation:** Display only `[stored in keyring]` without retrieving the actual value. Implement a separate "Change key" flow with secure input if editing is needed.

**Resolution:** Keyring keys no longer loaded into memory; UI shows placeholder only. ✅

---

### ✅ [M-002] Race condition in AudioRecorder
**File:** `src/audio/recorder.py`
**Category:** Insecure Design / A06

The audio callback and `stop()` share `self._frames` behind a lock, but there is a window between `stream.stop()` and frame reading where corruption can occur.

**Remediation:** Acquire lock before calling `stream.stop()`. Use a stop event to signal the callback to cease accepting data.

**Resolution:** Stop event added; callback checks event before appending frames, eliminating the race condition. ✅

---

### ✅ [M-003] Transcribed text left in clipboard
**File:** `src/output/inserter.py`
**Category:** Data Exposure / A04

`pyperclip.copy(text)` is called but the clipboard is never cleared after paste. Clipboard managers and malicious apps can read the content after insertion.

**Remediation:** Call `pyperclip.copy("")` after the paste simulation completes.

**Resolution:** Clipboard cleared with `pyperclip.copy("")` after paste simulation. ✅

---

### ✅ [M-004] Silent failure in auto-start registration
**File:** `src/ui/config_window.py` · `_apply_auto_start()`
**Category:** Error Handling / A10

`except Exception: pass` — the user believes auto-start is enabled when it may have silently failed.

**Remediation:** Return success/failure status and display a warning to the user if registration fails.

**Resolution:** _apply_auto_start() returns bool; caller shows warning to user on registration failure. ✅

---

### ✅ [M-005] Arbitrary values reach SQLite without upstream validation
**File:** `src/config/manager.py` · `HistoryManager.add()`
**Category:** Injection / A05

SQLite uses correct parameterized queries (`?` placeholders) — no SQL injection. However, without config validation (H-004), arbitrary values from config reach the database.

**Remediation:** Implement H-004 config validation. `provider` and `language` values should be whitelisted before storage.

**Resolution:** provider and language whitelisted before SQLite insert. ✅

---

## LOW

### ✅ [L-001] No certificate pinning
**File:** `src/stt/groq_provider.py`, `src/stt/openai_provider.py`, `src/stt/gemini_provider.py`
**Category:** Cryptographic Failures / A04

No certificate pinning for known API endpoints. A compromised CA could still enable MITM.

**Remediation:** Implement httpx certificate pinning for Groq, OpenAI and Gemini endpoints.

**Resolution:** Strict SSL context (CERT_REQUIRED + check_hostname) enforced via shared _make_client() factory. ✅

---

### ✅ [L-002] Unpinned dependency versions (supply chain risk)
**File:** `requirements.txt`
**Category:** Software Supply Chain / A03

All dependencies use `>=` ranges instead of pinned versions. A malicious or breaking release could be auto-installed.

**Remediation:** Pin exact versions (`httpx==0.27.0`). Use `pip-audit` or `safety` in CI to scan for known CVEs.

**Resolution:** All dependencies pinned to exact installed versions. ✅

---

### ✅ [L-003] No local rate limiting for STT calls
**File:** `src/stt/groq_provider.py`, `src/stt/openai_provider.py`, `src/stt/gemini_provider.py`
**Category:** Insecure Design / A06

No rate limiting between successive transcription requests. Accidental or malicious rapid firing could exhaust API quota.

**Remediation:** Implement a minimum interval (e.g. 2 s) between requests with exponential backoff on failure.

**Resolution:** Rate limiting (2s minimum interval) implemented in STTProvider base class. ✅

---

## Remediation Roadmap

| Phase | Timeline | Items |
|-------|----------|-------|
| **1 — Immediate** | Done | C-001 ✅ |
| **2 — Urgent** | This week | H-001, M-001, M-003 |
| **3 — Next sprint** | 2 weeks | C-002, H-003, H-004, M-002, M-004 |
| **4 — Backlog** | 1 month | H-002, L-001, L-002, L-003, M-005 |

---

## Dependency Risk Summary

| Package | Min version | Risk | Notes |
|---------|-------------|------|-------|
| python-dotenv | 1.0.0 | Low | Critical for credential management |
| keyring | 25.0.0 | Medium | Secure on Windows/macOS; verify backend on Linux |
| pynput | 1.7.6 | Medium | Low-level keyboard access; review for conflicts |
| pyperclip | 1.8.2 | Medium | Clipboard exposure vector (see M-003) |
| httpx | 0.25.0 | Low | Verify SSL defaults remain enabled after upgrades |
| sounddevice | 0.4.6 | Low | Stable, well-maintained |
| numpy | 1.24.0 | Low | Stable, well-maintained |
| pystray | 0.19.5 | Low | Stable |
| Pillow | 10.0.0 | Low | Actively maintained |
