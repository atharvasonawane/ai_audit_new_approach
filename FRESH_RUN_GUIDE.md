# Code Audit Librarian — Fresh Run Guide

All commands run from the project root:
`C:\Users\Atharvaso\Desktop\final_approach_main`

---

## Prerequisites

Before starting, make sure you have:
- Python 3.11+ installed
- Node.js 18+ installed
- The target Vue.js project folder accessible (configured in `audit_tool/config/project_config.yaml`)
- The LLM endpoint reachable (configured in `.env`)

---

## Step 1 — Stop any running servers

If Flask or Vite are already running, kill them first (Ctrl+C in their terminals, or close the terminals).

---

## Step 2 — Delete the existing database

```bash
del audit_history.db
del audit_history.db-shm
del audit_history.db-wal
```

These three files together make up the SQLite database. Deleting them gives you a completely clean slate.

**Verify:** Run `dir *.db` — you should see no files listed.

---

## Step 3 — Run Phase 1: Scout (Deterministic Analysis)

```bash
audit_tool\venv\Scripts\python.exe audit_tool\run_audit.py
```

This scans every `.vue` and `.js` file in the target directory using AST parsing and ESLint.

**What to watch for in the output:**
```
[orchestrator] [1/75] Processing SomeFile.vue
[orchestrator] [2/75] Processing AnotherFile.vue
...
INCREMENTAL SCAN SUMMARY
  Total files found   : 75
  Files processed     : 75
  Files skipped       : 0
  Errors              : 0
  DB : sqlite (75 new/updated rows)
```

**Verify it worked:**
```bash
audit_tool\venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('audit_history.db'); print('Files:', c.execute('SELECT COUNT(*) FROM vue_files').fetchone()[0]); print('ESLint flags:', c.execute('SELECT COUNT(*) FROM file_flags').fetchone()[0]); print('A11y defects:', c.execute('SELECT COUNT(*) FROM accessibility_defects').fetchone()[0])"
```

Expected output:
```
Files: 75
ESLint flags: 58
A11y defects: 271
```

Phase 1 is fast — typically under 2 seconds.

---

## Step 4 — Run Phase 2: LLM Agent Analysis

```bash
audit_tool\venv\Scripts\python.exe mcp_agent\agent.py
```

This sends every file to the LLM (Gemma 3) for intelligent analysis. It processes complex files individually and batches simple ones.

**What to watch for in the output:**
```
LLM AGENT: Full codebase analysis + executive synthesis (Stages 4-5)
[AI Agent] Started audit run id=1.
[AI Agent] Queue: 40 complex (script_lines>=150), 35 simple.
[Complex 1/40] Processing cancelAdmission__1.vue...
✓ Wrote 2 issues to database
[Complex 2/40] Processing updateABCID__1.vue...
✓ Wrote 2 issues to database
...
[Batch 1/5] Processing 7 simple files...
...
[Executive synthesis] Saved to audit_runs id=1 (4675 chars); status=completed.
[AI Agent] Audit run 1 completed successfully (including executive synthesis).
```

**This takes time** — roughly 3–5 minutes for 75 files depending on LLM speed.

**Verify it worked:**
```bash
audit_tool\venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('audit_history.db'); print('AI issues:', c.execute('SELECT COUNT(*) FROM ai_issues').fetchone()[0]); r=c.execute('SELECT status, synthesis_text FROM audit_runs ORDER BY id DESC LIMIT 1').fetchone(); print('Run status:', r[0]); print('Synthesis length:', len(r[1] or ''), 'chars')"
```

Expected output:
```
AI issues: 107
Run status: completed
Synthesis length: 4675 chars
```

---

## Step 5 — Start the Flask API Server

Open a new terminal and run:

```bash
audit_tool\venv\Scripts\python.exe report\api_server.py
```

**What to watch for:**
```
============================================================
Code Audit Librarian — Flask API Server (Stage 6)
============================================================
Project: new_university
Database: audit_history.db
Starting server on http://localhost:5000
============================================================
* Running on http://127.0.0.1:5000
* Debugger is active!
```

**Verify it's working — open a second terminal and run:**
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "database": "audit_history.db",
  "database_exists": true,
  "project_name": "new_university",
  "status": "ok"
}
```

Then verify data is being served:
```bash
curl http://localhost:5000/api/summary
```

Expected response:
```json
{
  "ai_issues_total": 107,
  "total_files": 75,
  "total_eslint_flags": 58,
  "total_accessibility_defects": 271,
  "project_name": "new_university",
  "ai_issues_by_severity": {
    "High": 14,
    "Medium": 44,
    "Low": 49
  }
}
```

Keep this terminal open — the API must stay running.

---

## Step 6 — Start the Vue Frontend

Open another new terminal and run:

```bash
cd report\frontend
npm run dev
```

**What to watch for:**
```
  VITE v8.0.12  ready in 526 ms
  ➜  Local:   http://localhost:5173/
```

Keep this terminal open too.

---

## Step 7 — Open the Browser

Navigate to:

- **Dashboard:** http://localhost:5173/dashboard
- **Audit Explorer:** http://localhost:5173/audit
- **Home:** http://localhost:5173

**What you should see on the Dashboard:**
- Executive Synthesis panel with AI-generated summary
- 6 metric cards (Total Files, Total Issues, ESLint Flags, A11y Defects, Avg Complexity, High Severity)
- Severity pie chart (High / Medium / Low breakdown)
- Category bar chart (AI Issues / ESLint / Accessibility)
- Worst Offenders list (top 10 files by composite score)

**What you should see in the Audit Explorer:**
- Left pane: full file list with issue badges
- Click any file → right pane loads with tabs (AI Issues, ESLint, Accessibility, API Calls)
- Each tab shows issues with code snippets and line numbers

---

## Quick Verification Checklist

After completing all steps, confirm:

| Check | Command / URL | Expected |
|---|---|---|
| DB has files | sqlite3 check (Step 3) | 75 rows |
| DB has AI issues | sqlite3 check (Step 4) | 100+ rows |
| API health | `curl localhost:5000/api/health` | `"status": "ok"` |
| API has data | `curl localhost:5000/api/summary` | `total_files: 75` |
| Frontend loads | http://localhost:5173 | No blank screen |
| Dashboard shows data | http://localhost:5173/dashboard | Charts + metrics visible |

---

## Summary of All Commands (in order)

### Option A: The Unified Orchestrator (New)
```bash
# 1. Delete old database
del audit_history.db audit_history.db-shm audit_history.db-wal

# 2. Run the full pipeline (Scout -> AI Agent -> Start Servers automatically)
audit_tool\venv\Scripts\python.exe audit_tool\run_audit.py

# You can also run stages independently using the unified CLI:
# audit_tool\venv\Scripts\python.exe audit_tool\run_audit.py --scout-only
# audit_tool\venv\Scripts\python.exe audit_tool\run_audit.py --ai-only
# audit_tool\venv\Scripts\python.exe audit_tool\run_audit.py --report-only
```

### Option B: Individual Scripts (Legacy)
```bash
# 1. Delete old database
del audit_history.db audit_history.db-shm audit_history.db-wal

# 2. Phase 1 — Scout (run once, wait for it to finish)
audit_tool\venv\Scripts\python.exe audit_tool\run_audit.py --scout-only

# 3. Phase 2 — LLM Analysis (run once, wait ~5 min for it to finish)
audit_tool\venv\Scripts\python.exe mcp_agent\agent.py

# 4. Start API server (keep terminal open)
audit_tool\venv\Scripts\python.exe report\api_server.py

# 5. Start frontend (keep terminal open, run from project root)
cd report\frontend && npm run dev

# 6. Open browser
# http://localhost:5173/dashboard
```

---

## Troubleshooting

**"No module named flask"**
```bash
audit_tool\venv\Scripts\pip install flask flask-cors
```

**"Database not found" in API**
- Make sure you ran Steps 2 and 3 first
- Check `audit_history.db` exists in the project root

**Frontend shows no data / loading spinner stuck**
- Make sure the Flask API is running (Step 5)
- Check browser console for CORS or network errors
- Verify `curl http://localhost:5000/api/summary` returns data

**LLM agent hangs or times out**
- Check your `.env` has correct `OPENWEBUI_BASE_URL` and `OPENWEBUI_API_KEY`
- Check the LLM endpoint is reachable: `curl http://164.52.196.104:8084/api/v1/models`
- Set `AI_FILE_LIMIT=5` in `.env` to test with just 5 files first

**Port already in use**
- Flask default: 5000. Kill any process using it.
- Vite default: 5173. Kill any process using it.
- On Windows: `netstat -ano | findstr :5000` then `taskkill /PID <pid> /F`
