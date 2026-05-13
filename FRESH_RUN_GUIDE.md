# Complete Fresh Run Guide - Code Audit Librarian

## Overview
This guide will walk you through running the entire Code Audit Librarian pipeline from scratch:
1. Delete existing database
2. Run Phase 1 (Scout - AST/ESLint extraction)
3. Run Phase 2-3 (LLM Agent analysis)
4. Start Flask API server
5. Start Vue.js frontend
6. View results in browser

---

## Prerequisites Check

Before starting, verify you have:
- ✅ Python 3.10+ installed
- ✅ Node.js 18+ installed
- ✅ Ollama running with Gemma 3 model (or OpenWebUI configured)
- ✅ `.env` file configured with LLM credentials

---

## Step 1: Stop All Running Servers

If you have any servers running, stop them first:

```bash
# Press Ctrl+C in any terminal running:
# - Flask API server
# - Vue.js dev server
# - Any other processes
```

---

## Step 2: Delete Existing Database

```bash
# Delete the SQLite database
rm audit_history.db

# Or on Windows:
del audit_history.db
```

**What this does:** Removes all previous scan data so we start fresh.

---

## Step 3: Verify Configuration

Check your `.env` file has the correct settings:

```bash
# View your .env file
cat .env

# Or on Windows:
type .env
```

**Required variables:**
```env
OPENWEBUI_BASE_URL=http://your-llm-endpoint/api/v1
OPENWEBUI_API_KEY=your-api-key
LLM_MODEL=gemma3:latest
LLM_TIMEOUT_SECONDS=90
OPENWEBUI_DISABLE_TOOLS=0
```

**Optional (for testing with limited files):**
```env
AI_FILE_LIMIT=10
```

---

## Step 4: Run Phase 1 (Scout - Deterministic Analysis)

This phase scans all Vue files and extracts metrics using AST parsing and ESLint.

```bash
# Run the scout phase
python audit_tool/run_audit.py
```

**What happens:**
- Scans all `.vue` and `.js` files in the target directory
- Extracts metrics (methods, computed, watchers, API calls, etc.)
- Runs ESLint to find Vue best-practice violations
- Runs ESLint accessibility plugin to find a11y issues
- Stores everything in SQLite database
- Creates `audit_history.db` file

**Expected output:**
```
[Scout] Starting Phase 1: Deterministic Analysis
[Scout] Found 75 Vue files
[Scout] Processing files...
[Scout] Running ESLint...
[Scout] Phase 1 complete: 75 files scanned
```

**Time:** ~30 seconds to 2 minutes (depending on codebase size)

---

## Step 5: Verify Database Was Created

```bash
# Check if database exists
ls -la audit_history.db

# Or on Windows:
dir audit_history.db
```

**Expected:** File should exist and be several MB in size.

---

## Step 6: Run Phase 2-3 (LLM Agent Analysis)

This phase uses the LLM to analyze each file and generate insights.

```bash
# Run the LLM agent
python mcp_agent/agent.py
```

**What happens:**
- Starts MCP server to expose database as tools
- Connects to LLM (Gemma 3 via Ollama or OpenWebUI)
- Analyzes each file (complex files individually, simple files in batches)
- Generates AI issues and stores in database
- Creates executive synthesis summary
- Marks audit run as completed

**Expected output:**
```
[AI Agent] Started audit run id=1
[AI Agent] Queue: 15 complex (script_lines>=150), 60 simple.
[Complex 1/15] Processing Sidebar.vue...
✓ Wrote 4 issues to database
[Complex 2/15] Processing ImportStudentABCID.vue...
✓ Wrote 9 issues to database
...
[Batch 1/8] Processing 8 simple files...
✓ Wrote 0 issues to database
...
[Executive synthesis] Saved to audit_runs id=1 (2000 chars); status=completed.
[AI Agent] Audit run 1 completed successfully (including executive synthesis).
```

**Time:** 
- With local Ollama: 5-15 minutes (depending on codebase size)
- With online LLM: 2-5 minutes (faster but may have rate limits)

**Note:** If you set `AI_FILE_LIMIT=10` in `.env`, it will only analyze 10 files for testing.

---

## Step 7: Verify LLM Analysis Completed

```bash
# Check if ai_issues table has data
python -c "import sqlite3; conn = sqlite3.connect('audit_history.db'); print(f'AI Issues: {conn.execute(\"SELECT COUNT(*) FROM ai_issues\").fetchone()[0]}'); print(f'Audit Runs: {conn.execute(\"SELECT status FROM audit_runs ORDER BY id DESC LIMIT 1\").fetchone()[0]}')"
```

**Expected output:**
```
AI Issues: 17
Audit Runs: completed
```

---

## Step 8: Start Flask API Server

Open a **new terminal** (Terminal 1):

```bash
# Start Flask API server
python report/api_server.py
```

**Expected output:**
```
============================================================
Code Audit Librarian — Flask API Server (Stage 6)
============================================================
Project: new_university
Database: audit_history.db
Base Path: C:/Users/.../StudentManagement/client/app/src
============================================================
Starting server on http://localhost:5000
API endpoints available at http://localhost:5000/api/*
============================================================
 * Running on http://127.0.0.1:5000
```

**Keep this terminal open!** The server must stay running.

---

## Step 9: Test Flask API

Open a **new terminal** (Terminal 2) to test the API:

```bash
# Test health endpoint
curl http://localhost:5000/api/health

# Test files endpoint
curl http://localhost:5000/api/files

# Test summary endpoint
curl http://localhost:5000/api/summary
```

**Expected:** All should return JSON with 200 OK status.

---

## Step 10: Start Vue.js Frontend

In **Terminal 2** (or a new Terminal 3):

```bash
# Navigate to frontend directory
cd report/frontend

# Start Vue dev server
npm run dev
```

**Expected output:**
```
  VITE v8.0.12  ready in 611 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**Keep this terminal open!** The dev server must stay running.

---

## Step 11: Open Browser

Open your web browser and navigate to:

```
http://localhost:3000
```

**What you should see:**

### Sidebar (Left):
- "Code Audit Librarian" title in blue
- Project name "new_university"
- Search box
- List of all scanned files with badges:
  - Red badges: High severity issues
  - Yellow badges: Medium severity issues
  - Gray badges: ESLint flags
  - Purple badges: Accessibility issues
- Footer with file counts

### Main Area (Right):
- Welcome screen with 📊 icon
- "Welcome to Code Audit Librarian" heading
- Stats showing total files and total issues

### Try These Actions:
1. **Search**: Type in the search box to filter files
2. **Select File**: Click any file in the sidebar
3. **View Details**: See the file detail placeholder
4. **Close**: Click the ✕ button to return to welcome screen

---

## Step 12: Verify Everything Works

### Check Flask API Logs (Terminal 1):
You should see API requests:
```
127.0.0.1 - - [13/May/2026 02:00:00] "GET /api/files HTTP/1.1" 200 -
127.0.0.1 - - [13/May/2026 02:00:00] "GET /api/summary HTTP/1.1" 200 -
```

### Check Vue Dev Server Logs (Terminal 2/3):
Should show no errors, just:
```
  ➜  Local:   http://localhost:3000/
```

### Check Browser Console (F12):
- No red errors
- Should see successful API calls in Network tab

---

## Troubleshooting

### Problem: "Database not found"
**Solution:**
```bash
# Make sure you ran Phase 1 first
python audit_tool/run_audit.py
```

### Problem: "Failed to connect to API server"
**Solution:**
```bash
# Make sure Flask API is running
python report/api_server.py

# Check if port 5000 is available
netstat -ano | findstr :5000
```

### Problem: "Port 3000 already in use"
**Solution:**
```bash
# Kill process on port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Or change port in vite.config.js
```

### Problem: "LLM connection failed"
**Solution:**
```bash
# Check .env file has correct credentials
cat .env

# Test LLM endpoint
curl -X POST http://your-llm-endpoint/api/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma3:latest","messages":[{"role":"user","content":"test"}]}'
```

### Problem: "No files showing in sidebar"
**Solution:**
```bash
# Check if database has data
python -c "import sqlite3; conn = sqlite3.connect('audit_history.db'); print(conn.execute('SELECT COUNT(*) FROM vue_files').fetchone()[0])"

# If 0, run Phase 1 again
python audit_tool/run_audit.py
```

---

## Quick Reference: All Commands

```bash
# 1. Delete database
rm audit_history.db

# 2. Run Phase 1 (Scout)
python audit_tool/run_audit.py

# 3. Run Phase 2-3 (LLM Agent)
python mcp_agent/agent.py

# 4. Start Flask API (Terminal 1)
python report/api_server.py

# 5. Start Vue Frontend (Terminal 2)
cd report/frontend
npm run dev

# 6. Open browser
# http://localhost:3000
```

---

## Expected Timeline

| Phase | Time | What Happens |
|-------|------|--------------|
| Phase 1 (Scout) | 30s - 2min | AST parsing, ESLint scanning |
| Phase 2-3 (LLM) | 2-15min | LLM analysis of each file |
| Flask API | Instant | Server starts immediately |
| Vue Frontend | 5-10s | Vite dev server starts |
| **Total** | **3-17min** | Complete fresh run |

---

## What Gets Created

```
audit_history.db          # SQLite database with all findings
scan.log                  # Log file (if configured)
```

**Database tables populated:**
- `vue_files` - 75 files with metrics
- `api_calls` - All detected API calls
- `file_flags` - ESLint findings
- `accessibility_defects` - A11y issues
- `ai_issues` - LLM-generated findings
- `audit_runs` - Run metadata with synthesis
- `component_relationships` - Import graph

---

## Success Criteria

✅ Database created and populated  
✅ Flask API returns data on all endpoints  
✅ Vue frontend loads without errors  
✅ Sidebar shows all files with badges  
✅ Search filtering works  
✅ File selection works  
✅ No console errors in browser  
✅ API logs show successful requests  

---

## Next Steps After Fresh Run

Once everything is working:

1. **Explore the data**: Click through different files
2. **Test search**: Filter files by name
3. **Check API responses**: Use curl to inspect data
4. **Review executive summary**: Check `/api/executive-summary`
5. **Proceed to Stage 7 Part 2**: Build Dashboard Overview

---

## Stop Everything

When you're done:

```bash
# Terminal 1 (Flask API)
Ctrl+C

# Terminal 2/3 (Vue Frontend)
Ctrl+C
```

---

**You're ready to run everything from scratch!** 🚀

Follow the steps in order, and you'll have a complete fresh analysis in 3-17 minutes.
