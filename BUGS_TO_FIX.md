# AI Agency — Known Issues & Fixes Needed

## Critical Issues (App doesn't work without manual intervention)

### BUG-1: Builder uses wrong Gemini model names
**Problem:** Builder generates code with `gemini-1.5-flash-001` or `gemini-1.5-pro` instead of working models.
**Impact:** Generated apps crash on first run with 404 model not found.
**Fix:** Add model name enforcement in builder system prompt: "ALWAYS use gemini-2.5-pro or gemini-2.5-flash. NEVER use gemini-1.5-*"

### BUG-2: Colon in project directory names on Windows
**Problem:** `_extract_build_tasks` returns titles with colons (`:`) which are invalid for Windows paths.
**Impact:** Builder crashes with `[WinError 267] The directory name is invalid`
**Fix:** Already partially fixed in builder_agent.py but _extract_build_tasks output still contains colons.

### BUG-3: Builder splits project into microservices instead of one app
**Problem:** When the project is complex, the planner creates separate stories that get built as separate folders.
**Impact:** User gets 4 disconnected folders instead of one working app.
**Fix:** Change `run_full_project` to build ONE unified app, not per-story builds.

### BUG-4: `in_progress` status requires assignee
**Problem:** Paperclip rejects `status="in_progress"` if no agent is assigned.
**Impact:** Pipeline crashes on status update.
**Fix:** Already fixed — using "todo" instead.

### BUG-5: Vertex AI `global` not supported by vertexai SDK
**Problem:** `vertexai.init(location="global")` throws error — only google-genai SDK supports global.
**Impact:** Generated code using vertexai SDK for Gemini 3.1 fails.
**Fix:** Builder must use OpenAI-compatible endpoint instead of vertexai SDK for Gemini 3.1.

### BUG-6: Pipeline creates generic build tasks instead of project-specific ones
**Problem:** `run_full_project` had hardcoded generic tasks ("Set up infrastructure", "Build landing page").
**Impact:** Wrong code gets built regardless of what was planned.
**Fix:** Already fixed — now uses Gemini to extract tasks from planner output.

### BUG-7: Paperclip agents heartbeat with no URL configured
**Problem:** HTTP adapter agents with empty adapterConfig cause red errors in dashboard.
**Impact:** Dashboard full of red error indicators, confusing the user.
**Fix:** Already fixed — set URLs and cleaned failed runs from DB.

## Medium Issues (App works but with problems)

### BUG-8: JSON parsing fails on large Gemini responses
**Problem:** Gemini sometimes returns truncated JSON when response exceeds max_tokens.
**Impact:** Builder generates 0 files, falls back to individual generation.
**Fix:** Already improved with multi-strategy parsing + repair logic.

### BUG-9: No auto-fix loop for failing tests
**Problem:** Builder generates code, tests fail, but no retry to fix the failing tests.
**Impact:** Every project has failing tests that user must fix manually.
**Fix:** Add a retry loop: if tests fail, send error to Gemini and regenerate the failing file.

### BUG-10: QA agent doesn't actually fix bugs
**Problem:** QA finds bugs but only reports them — doesn't auto-fix.
**Impact:** User gets a bug report but still has to fix everything manually.
**Fix:** Add auto-fix step: for each bug found, generate a fix and apply it.
