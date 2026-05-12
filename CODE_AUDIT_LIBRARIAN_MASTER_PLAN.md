# Code Audit Librarian — Master Plan
### For AI Assistants: Read This Entire Document Before Writing Any Code

---

## 0. Document Purpose

This is the single source of truth for building the Code Audit Librarian tool. The developer will hand you this document and ask you to implement one section at a time. Your job is to build exactly what is described here. Do not suggest architectural changes. Do not over-engineer. Every decision in this document is finalized.

---

## 1. What This Tool Does

The Code Audit Librarian is a developer productivity tool that:

1. Accepts a Vue.js codebase directory path as input
2. Scans every `.vue` and `.js` file using deterministic Python extractors (AST parsing + ESLint)
3. Stores all findings in a local SQLite database (zero setup required from the user)
4. Uses a local LLM (Gemma 3 via Ollama) to generate intelligent architectural analysis for every file
5. Produces a Vue.js-based interactive report dashboard showing per-file findings, metrics, and an executive summary

**The tool runs entirely locally. No cloud APIs. No paid services. No external database setup.**

**Every file in the codebase is analyzed. No file is skipped.**

---

## 2. The Long-Term Vision (Context Only — Not Being Built Now)

The final form of this tool is a VS Code / IDE extension where a developer opens any Vue.js project, clicks one button, and gets a full audit report without any setup. No MySQL, no config files, no manual environment variables. Everything is automatic.

**This is NOT being built right now.** The current goal is a working Python CLI tool with a Vue.js report dashboard. The architecture must be designed to support the extension path later without rewrites.

---

## 3. Current State of the Codebase (What Already Exists)

The developer has an existing codebase on the `main` branch with the following already working:

### What is working and must NOT be touched:
- `task2_audit/` — Vue parser (Tree-sitter), API extractor, script cleaner, import extractor
- `task3/` — Component complexity scoring
- `task4/` — UI component extraction
- `task5/` — UI consistency checking
- ESLint integration via Python subprocess (splits Vue best-practice flags and accessibility defects)
- MySQL database persistence (all findings stored across multiple tables)
- Incremental scanning: mtime pre-filter + SHA-256 hash check — unchanged files are skipped in ~0.1 seconds
- Flask-based dashboard (`report_server.py`) — currently serves Jinja HTML templates
- `run_audit.py` — top-level orchestrator

### What is being replaced / added:
- The Flask Jinja dashboard is being replaced with a standalone Vue.js frontend
- The LLM integration (currently urllib-based calls) is being rebuilt using a proper FastMCP server approach
- MySQL is being replaced with SQLite for zero-setup portability (critical for the IDE extension future)
- A new `mcp_agent/` folder will be added containing the FastMCP server and LLM agent

### The Rule:
**Freeze the extractors. Replace the LLM pipeline and the frontend.**

---

## 4. Why This Architecture Was Chosen

### Why SQLite instead of MySQL
The long-term goal is an IDE extension where the user provides only a project path. MySQL requires a running server, credentials, and manual provisioning — none of which can be assumed in an extension context. SQLite is a single file, requires zero installation, is built into Python, and handles codebases of any size without memory limits.

### Why FastMCP instead of direct urllib LLM calls
The previous approach fed large batches of pre-packaged data to the LLM in a single call. This had two problems: the LLM had no agency to investigate further, and context windows would fill up on large codebases. With FastMCP, the LLM acts as an intelligent analyst — it can call tools to request exactly the data it needs for each file, follow up on findings, and generate a richer report. The LLM is no longer a passive receiver of data dumps.

### Why Gemma 3 via Ollama
Free, runs locally, privacy-preserving, no API costs. Gemma 3 is capable of structured JSON output and intelligent code analysis. The tool works offline after the model is downloaded.

### Why Vue.js frontend instead of Flask/Jinja templates
The report dashboard needs to be interactive — per-file drill-downs, tabs, collapsible sections, live search. Vue.js (Composition API + Vite) handles this cleanly. The Flask backend is kept only as an API server; the Vue frontend is a fully decoupled SPA.

### Why keep AST and ESLint if LLM analyzes files anyway
The LLM reads code and reasons qualitatively. AST and ESLint provide ground-truth quantitative facts: exact method counts, exact nesting depths, exact API call line numbers. When the LLM is told "this file has 14 API calls, 3 inside loops, nesting depth of 8" as facts, its analysis becomes much more accurate and focused. These tools complement each other.

---

## 5. Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.10+ | All backend and pipeline logic |
| AST Parsing | Tree-sitter + tree-sitter-vue | Already implemented — do not change |
| Linting | ESLint via Python subprocess | Already implemented — do not change |
| Database | SQLite (built into Python) | Replaces MySQL. Zero user setup required |
| MCP Framework | FastMCP | Exposes SQLite data as tools the LLM can call |
| LLM | Gemma 3 via Ollama | Local, free, offline after initial download |
| LLM Protocol | OpenAI-compatible API (Ollama endpoint) | Simple, debuggable, synchronous |
| Report Frontend | Vue 3 + Vite + Composition API | Interactive SPA dashboard |
| Report API | Flask + Flask-CORS | Serves SQLite data as JSON to the Vue frontend |
| Config | project_config.yaml + PyYAML | Already implemented — keep as is |
| Entry Point | Python CLI (run_audit.py) | Already implemented — extend, do not replace |

---

## 6. Folder Structure (Target State)

```
audit_tool/
│
├── run_audit.py                    ← Existing orchestrator. Extend with new phases.
├── project_config.yaml             ← Existing config. Add SQLite path + Ollama settings.
│
├── task2_audit/                    ← FROZEN. All extractors stay exactly as they are.
├── task3/                          ← FROZEN.
├── task4/                          ← FROZEN.
├── task5/                          ← FROZEN.
│
├── db/
│   ├── db_init.py                  ← NEW. Creates all SQLite tables with correct schema.
│   └── db_writer.py                ← NEW. Upsert functions for every table.
│
├── mcp_agent/
│   ├── server.py                   ← NEW. FastMCP server. Exposes SQLite data as tools.
│   └── agent.py                    ← NEW. Drives Gemma 3 through the MCP tools to analyze each file.
│
├── report/
│   ├── api_server.py               ← NEW. Flask API server. Reads SQLite, serves JSON to Vue frontend.
│   └── frontend/                   ← NEW. Vue 3 + Vite project.
│       ├── src/
│       │   ├── App.vue
│       │   ├── components/
│       │   │   ├── ExecutiveSummary.vue
│       │   │   ├── FileExplorer.vue
│       │   │   ├── FileDetailView.vue
│       │   │   ├── MetricsTab.vue
│       │   │   ├── ApiCallsTab.vue
│       │   │   ├── AccessibilityTab.vue
│       │   │   ├── EslintTab.vue
│       │   │   └── AiIssuesTab.vue
│       │   └── main.js
│       ├── vite.config.js
│       └── package.json
│
├── audit_history.db                ← Auto-created by db_init.py at first run.
└── scan.log                        ← Auto-created at runtime.
```

---

## 7. SQLite Database Schema

Every SQLite connection must set:
```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

### Table: vue_files
The central table. One row per scanned file. All metrics computed by the deterministic extractors.

Columns: id, project_name, file_path, file_hash, script_lines, template_lines, style_lines, methods, computed, watchers, props, emits, api_total, api_in_mounted, api_in_loop, child_components, max_nesting_depth, cyclomatic_complexity, payload_size_kb, eslint_flag_count, script_setup (boolean), template_only (boolean), typescript_detected (boolean), last_modified (real timestamp), scanned_at (timestamp).

Unique constraint: (project_name, file_path). All writes use upsert (INSERT OR REPLACE).

### Table: api_calls
One row per detected API call. Foreign key to vue_files.

Columns: id, vue_file_id, project_name, file_path, api_type (axios/fetch/mql/graphql/etc), method_name, endpoint, in_mounted (boolean), in_loop (boolean), line_number.

### Table: file_flags
One row per ESLint finding. Foreign key to vue_files.

Columns: id, vue_file_id, project_name, file_path, category (either 'eslint' or 'accessibility'), rule, message, severity, line_number, column_number.

The `category` column is critical — it separates Vue best-practice flags from accessibility defects so the frontend can display them in separate tabs.

### Table: accessibility_defects
One row per accessibility issue. Foreign key to vue_files.

Columns: id, vue_file_id, project_name, file_path, rule, message, wcag_criterion, wcag_level (A/AA/AAA), line_number, column_number.

WCAG metadata (criterion name, level, explanation) is looked up from a static Python dictionary keyed by ESLint rule name — it is NEVER generated by the LLM.

### Table: component_relationships
Import graph for the whole codebase.

Columns: id, project_name, parent_file, child_file, relationship_type. Unique constraint: (project_name, parent_file, child_file).

### Table: ai_issues
Every finding the LLM generates, from all analysis phases.

Columns: id, vue_file_id, project_name, file_path, phase (one of: 'dependency', 'file_analysis', 'synthesis'), issue_category, title, description, severity (High/Medium/Low), line_number, code_snippet, recommendation, created_at.

Code snippets are extracted in Python using the line number from the LLM response — they are NEVER generated by the LLM directly.

### Table: audit_runs
Tracks each full audit execution for crash recovery.

Columns: id, project_name, started_at, status (in_progress/completed/failed), last_completed_file, synthesis_text (the executive summary written by the LLM), completed_at.

---

## 8. The Full Pipeline — Step by Step

### Phase 1: Scout (Deterministic — No LLM)

This phase is already implemented in the existing extractors. The only change is replacing MySQL writes with SQLite writes.

**What happens:**
1. `run_audit.py` reads `project_config.yaml` to get the target directory paths and project name
2. `db/db_init.py` runs and creates all SQLite tables if they do not exist
3. A single SQL query loads all existing file_path + file_hash + last_modified from `vue_files` into a Python dictionary (O(1) lookup for the cache check)
4. For every `.vue` and `.js` file in the target directories:
   - Gate 1: Compare `os.path.getmtime()` against stored `last_modified`. If the file is older than the last scan, skip it instantly.
   - Gate 2: If newer, compute SHA-256 hash. If hash matches stored hash, skip it.
   - If the file passes both gates (it is new or changed), extract metrics using the existing extractors and write to SQLite via upsert.
5. ESLint runs in batches of 30 files via subprocess. Output is parsed and written to `file_flags` and `accessibility_defects` tables.
6. The skeleton map is built from SQLite — a compact plain-text summary of every file and its key metrics.

**Performance target:** On unchanged codebases, Phase 1 completes in under 1 second.

### Phase 2: MCP Agent (LLM-Driven Analysis)

This is the new phase replacing the old urllib-based ai_pipeline.

**How it works:**

The FastMCP server (`mcp_agent/server.py`) exposes the SQLite database as a set of callable tools. The agent (`mcp_agent/agent.py`) starts a conversation with Gemma 3 via Ollama's OpenAI-compatible API and gives it access to those tools.

The LLM acts as an analyst. For each file (or batch of small files), it:
1. Calls `get_file_metrics(file_path)` to see structural complexity
2. Calls `get_file_flags(file_path)` to see ESLint findings
3. Calls `get_file_api_calls(file_path)` to see API usage patterns
4. Calls `get_accessibility_defects(file_path)` if relevant
5. Calls `get_raw_source(file_path)` if it needs to read the actual code
6. Generates a structured JSON response with its findings

The agent collects all findings and writes them to the `ai_issues` table via `db/db_writer.py`.

**Why this is better than the old approach:**
- The LLM is not given a data dump. It decides what to look at and asks for it.
- Token usage is lower because it only fetches what it needs.
- The analysis is more focused and more accurate because the LLM is in control of its investigation.
- The MCP server can be reused later as the backbone of the IDE extension.

### Phase 3: Executive Synthesis

After all files are analyzed, the agent runs one final pass:
1. Fetches `get_project_summary()` — aggregate stats for the whole codebase
2. Fetches `get_worst_offenders(10)` — the 10 most problematic files
3. Fetches all `ai_issues` grouped by severity
4. Generates a plain-text executive summary covering: overall health score, top critical components, recurring patterns, prioritized recommendations, and suggested refactoring sequence
5. Stores the synthesis text in the `audit_runs` table

### Phase 4: Report Generation

The Vue.js frontend (`report/frontend/`) runs as a local development server (or can be built to static files). It fetches all data from the Flask API server (`report/api_server.py`).

The user opens their browser to `http://localhost:3000` after the pipeline completes.

---

## 9. The FastMCP Server — Tool Definitions

The FastMCP server exposes exactly the following tools. No more, no less. Every tool reads from SQLite and returns structured data.

**Tool 1: get_all_files()**
Returns a list of all scanned file paths in the project. The LLM uses this to know what files exist before deciding which ones to investigate.

**Tool 2: get_file_metrics(file_path: str)**
Returns the full row from `vue_files` for the given file: all structural metrics (methods, computed, watchers, nesting depth, API counts, line counts, complexity score, etc.).

**Tool 3: get_file_flags(file_path: str)**
Returns all rows from `file_flags` for the given file where category = 'eslint'. These are Vue best-practice violations.

**Tool 4: get_file_api_calls(file_path: str)**
Returns all rows from `api_calls` for the given file: API type, method name, endpoint, in_mounted flag, in_loop flag, line number.

**Tool 5: get_accessibility_defects(file_path: str)**
Returns all rows from `accessibility_defects` for the given file: rule, message, WCAG criterion, WCAG level, line number.

**Tool 6: get_raw_source(file_path: str)**
Reads the actual file from disk and returns its content as a string. The LLM calls this when it needs to read the source code directly. The raw unmodified file is always returned — no cleaning, no stripping.

**Tool 7: get_worst_offenders(limit: int = 10)**
Returns the top N files ranked by a composite score of flag_count, eslint_flag_count, api_in_loop count, and max_nesting_depth.

**Tool 8: get_project_summary()**
Returns aggregate statistics: total files, total flags, total API calls, average nesting depth, files with accessibility issues, files with high severity LLM findings.

**Tool 9: get_component_relationships(file_path: str)**
Returns the import relationships for a given file: which files it imports from and which files import it.

---

## 10. LLM Behavior — Critical Rules

These rules apply to every LLM interaction. They must be enforced via the system prompt and post-processing validation in Python.

**Rule 1: Structured JSON output only.**
Every LLM response must be valid JSON matching a defined schema. No markdown fences. No preamble. No plain text explanations. If the response is not valid JSON, retry once with an explicit correction message.

**Rule 2: Line numbers must be real.**
Every issue reported by the LLM must include a line_number. After the LLM responds, Python code validates that the line number exists in the actual file. If a line number is out of range, the issue is discarded and a warning is logged.

**Rule 3: Code snippets are extracted in Python, never by the LLM.**
The LLM provides only the line number. Python uses that line number to extract 2 lines of context above and 2 lines below from the raw file, with the target line marked. The LLM never generates code snippet text.

**Rule 4: Raw unmodified source is always sent to the LLM.**
When calling `get_raw_source()`, the file is read directly from disk with no modifications. No comment stripping, no cleaning, no reformatting. Line 45 in the file must be line 45 in what the LLM sees.

**Rule 5: WCAG metadata comes from Python, never from the LLM.**
A static Python dictionary maps every ESLint accessibility rule name to its WCAG criterion number, level (A/AA/AAA), and a plain-English explanation. The LLM never generates WCAG metadata.

**Rule 6: Severity must be exactly one of: High, Medium, Low.**
Any other value is corrected to 'Low' before writing to SQLite.

**Rule 7: If a file looks fine, return an empty findings array.**
The LLM must not invent issues to appear useful. The system prompt must explicitly instruct it that returning an empty array for a clean file is correct and expected behavior.

**Rule 8: No hallucinated file paths.**
The LLM must only reference file paths that appear in the get_all_files() response. Any finding that references a file path not in that list is discarded.

---

## 11. The Vue.js Report Dashboard

The dashboard is a standalone Vue 3 + Vite SPA. It communicates with the Flask API server running on localhost:5000. The Vue dev server runs on localhost:3000.

### Layout

The dashboard has two sections:

**Left sidebar:** A searchable file explorer listing all scanned files. Each file shows a small badge with its total issue count. Clicking a file loads the File Detail View on the right.

**Right main area:** Either the Dashboard Overview (default) or the File Detail View for the selected file.

### Dashboard Overview (default view)

- Executive Summary card: Shows the synthesis text written by the LLM in Phase 3 — overall health score and key findings
- Summary Stats: Total files, total issues by severity (High/Medium/Low), total ESLint flags, total accessibility defects
- Worst Offenders table: Top 10 files by composite score with their key metrics
- Issues by Category chart: Visual breakdown of finding types across the whole codebase

### File Detail View

When a file is selected from the sidebar, a tabbed view appears with 5 tabs:

**Tab 1 — Metrics**
A grid of metric cards showing: script lines, template lines, methods, computed properties, watchers, props, emits, max nesting depth, API total, API in mounted, API in loop, child components, cyclomatic complexity, ESLint flag count.

Each metric card is color-coded: green (healthy), yellow (moderate), red (critical). Thresholds are defined in the config and must be applied consistently.

**Tab 2 — API Calls**
A table listing every detected API call with columns: API type, method name, line number, in_mounted (badge), in_loop (warning badge). Clicking a row expands a code snippet showing the call in context.

**Tab 3 — Accessibility**
A list of accessibility findings with: WCAG rule name, WCAG criterion, WCAG level (A/AA/AAA badge), a plain-English explanation from the Python WCAG dictionary, and the code snippet from Python. Summary bar at top showing count by level.

**Tab 4 — ESLint Flags**
A table of all non-accessibility ESLint findings grouped by severity (errors first, then warnings). Columns: severity icon, rule name, message, line number. Clicking a row expands the code snippet.

**Tab 5 — AI Issues**
All findings from the LLM stored in `ai_issues` for this file. Each finding shows: issue category, title, severity badge, description, code snippet (extracted by Python from the LLM's reported line number), and recommendation. Grouped by severity (High first).

### Design Requirements
- Dark theme preferred. Developer-tool aesthetic.
- No external CDN fonts. Use system fonts or bundle fonts with Vite.
- The dashboard must be fully functional with the Flask API running. It must show a clear loading state while data is being fetched and a clear error state if the API is unreachable.
- The file explorer sidebar must support keyword search/filter.
- All tabs must show a count badge so the user knows at a glance how many issues exist in each category for the selected file.

---

## 12. Flask API Server Endpoints

The Flask API server reads from SQLite and serves JSON. It runs on `http://localhost:5000/api`.

All endpoints return JSON. All endpoints include CORS headers for the Vue frontend.

**GET /api/summary**
Returns aggregate project statistics: total files, total issues by severity, total flags, average complexity.

**GET /api/worst-offenders?limit=10**
Returns the top N files by composite score with their key metrics.

**GET /api/files**
Returns a list of all scanned files with their issue counts and severity summary. Used to populate the sidebar file explorer.

**GET /api/file-metrics/\<path:file_path\>**
Returns the full metrics row for the file from `vue_files`.

**GET /api/file-api-calls/\<path:file_path\>**
Returns all API calls for the file. Each call includes a Python-generated code snippet.

**GET /api/file-accessibility/\<path:file_path\>**
Returns all accessibility defects for the file. Each defect includes WCAG metadata from the Python dictionary and a Python-generated code snippet.

**GET /api/file-eslint/\<path:file_path\>**
Returns all ESLint flags (non-accessibility) for the file. Each flag includes a Python-generated code snippet.

**GET /api/file-ai-issues/\<path:file_path\>**
Returns all LLM-generated issues for the file from `ai_issues`. Each issue already has a code snippet stored in the database.

**GET /api/executive-summary**
Returns the synthesis_text from the `audit_runs` table for the most recent completed run.

**GET /api/run-status**
Returns the status of the most recent audit run: status, started_at, last_completed_file. Used by the frontend to show pipeline progress.

---

## 13. Incremental Scanning Logic (Must be Preserved)

The existing mtime + SHA-256 two-gate caching must be preserved exactly. This is one of the most valuable features of the tool.

**Gate 1 (mtime):** At the start of every scan, a single SQL query loads all (file_path, file_hash, last_modified) from `vue_files` into a Python dictionary. For each file found on disk, compare `os.path.getmtime()` to the stored `last_modified`. If the file on disk is older than the last scan, skip immediately — no disk I/O, no hash computation.

**Gate 2 (SHA-256):** If the mtime check fails (file is newer or no stored timestamp), compute SHA-256 of the file content. If it matches the stored hash, the file content has not changed — skip it.

**Only files that pass both gates** (are genuinely new or changed) go through the full extraction pipeline.

**Performance target:** On a 100+ file codebase with no changes, Phase 1 must complete in under 1 second.

---

## 14. Configuration File (project_config.yaml)

This is the only file the developer needs to edit before running the tool. It must be simple and self-documenting.

Key settings:
- `project.name` — used as the namespace in the database (allows multiple projects in one DB)
- `project.target_paths` — list of directories to scan relative to the project root
- `project.exclude_paths` — directories to skip (always includes node_modules, dist, .git)
- `scout.file_extensions` — [".vue", ".js"] by default
- `scout.eslint_batch_size` — how many files per ESLint subprocess call (30 by default, due to Windows CLI length limits)
- `scout.parallel_workers` — ThreadPoolExecutor worker count (8 by default)
- `ai.model` — Ollama model name (e.g. "gemma3")
- `ai.base_url` — Ollama API endpoint (http://localhost:11434/v1 by default)
- `ai.temperature` — LLM temperature (0.2 recommended for structured output)
- `ai.timeout_seconds` — per-request timeout (90 seconds)
- `db.path` — path to the SQLite file (default: audit_history.db in the tool root)
- `report.frontend_port` — port for the Vue dev server (3000 by default)
- `report.api_port` — port for the Flask API server (5000 by default)

---

## 15. Build Order — Follow This Exactly

Each stage must be completed and verified before starting the next. Do not skip stages.

### Stage 1 — SQLite Migration
Replace all MySQL writes with SQLite writes. Create `db/db_init.py` and `db/db_writer.py`. Run the existing extractors against a test codebase and verify all data appears correctly in SQLite. The existing MySQL code can be left in place but disabled — do not delete it yet.

Verification: Open the SQLite file with a viewer. Confirm vue_files, api_calls, file_flags, accessibility_defects all have correct data for every scanned file.

### Stage 2 — FastMCP Server
Build `mcp_agent/server.py` using FastMCP. Implement all 9 tools listed in Section 9. Test each tool independently by calling it directly against the populated SQLite database. Verify every tool returns the correct data.

Verification: Run the FastMCP server standalone. Call each tool manually and inspect the output. Every tool must return data for at least 3 real files from the test codebase.

### Stage 3 — LLM Agent (Single File Test)
Build `mcp_agent/agent.py`. Connect it to Gemma 3 via Ollama's OpenAI-compatible endpoint. Pick one complex file from the test codebase. Drive the LLM through the MCP tools for that one file. Verify it produces valid JSON findings. Verify Python validates and writes those findings to `ai_issues`. Verify code snippets are extracted correctly in Python.

Verification: Query `ai_issues` in SQLite. The test file must have at least one finding with a valid line number, a code snippet that matches the actual file, and a severity of High/Medium/Low.

### Stage 4 — Full Codebase Agent Run
Extend the agent to process every file in the codebase. Implement crash recovery: on startup, check `audit_runs` for any `in_progress` runs. If found, offer to resume from `last_completed_file`. Process complex files (>= 150 lines) individually. Process simple files in batches of 8.

Verification: Run against the full test codebase. Every file must appear in `ai_issues` (even if with an empty findings array). Kill the process mid-run and verify it resumes correctly.

### Stage 5 — Executive Synthesis
Add the final synthesis pass to the agent. After all files are processed, generate the executive summary and store it in `audit_runs.synthesis_text`.

Verification: Query `audit_runs`. The synthesis_text must reference real file names from the codebase and real patterns found during analysis.

### Stage 6 — Flask API Server
Build `report/api_server.py`. Implement all endpoints listed in Section 12. Test every endpoint with curl. Verify code snippets are generated correctly for API calls, ESLint flags, and accessibility defects.

Verification: curl each endpoint and inspect the JSON response. Every response must have the correct structure as described in Section 12.

### Stage 7 — Vue.js Dashboard
Build the Vue 3 + Vite frontend in `report/frontend/`. Build components in this order: FileExplorer sidebar → Dashboard Overview → File Detail View with all 5 tabs. Connect every component to its Flask API endpoint.

Verification: Run the full pipeline against the test codebase. Open the dashboard. Every file must appear in the sidebar. Clicking a file must load all 5 tabs with correct data. The executive summary must display.

### Stage 8 — Orchestrator Update
Update `run_audit.py` to include the new phases. The CLI must support:
- `--scout-only` — run only Phase 1
- `--ai-only` — run only Phase 2 and 3 (assumes Scout has already run)
- `--report-only` — start only the Flask and Vue servers (assumes full pipeline has already run)
- `--resume` — resume a previously interrupted run
- No flags — run the full pipeline end to end

### Stage 9 — End-to-End Verification
Run the complete pipeline from scratch on the test codebase. Time it. Target: under 8 minutes for a 100+ file codebase including LLM analysis. Open the dashboard and verify every section.

---

## 16. Known Issues in the Existing Extractors (Must Be Fixed During Stage 1)

These are accuracy problems in the existing `main` branch extractors. They must be fixed as part of the SQLite migration, before the MCP agent is built, because the agent's analysis depends on these facts being correct.

**Problem 1: Method counting misses Vue patterns.**
The current extractor counts all function declarations in the script block. It must instead navigate the AST to the `methods` property of the Vue component's default export object and count only its properties that are functions. For `<script setup>` files, it must count top-level function declarations and arrow functions while excluding lifecycle hooks (onMounted, onUnmounted, etc.) and imported functions.

**Problem 2: API detection has false positives and false negatives.**
A call only counts as an API call if: it is a function call expression (not a string literal, not inside a comment node in the AST), and its callee matches the defined patterns (axios.get, axios.post, fetch, this.$http.get, $apollo.query, etc.). The in_mounted and in_loop flags must be determined by walking up the AST from the call node to check for the relevant ancestor node types.

**Problem 3: Nesting depth measures the wrong thing.**
Max nesting depth must measure HTML element depth in the template block only. It must not measure JavaScript object nesting, CSS selector nesting, or AST node depth. Only HTML element tags count — text nodes and comment nodes are excluded.

**Problem 4: Child component counting misses some patterns.**
Only components that are both imported as .vue files AND used in the template (as PascalCase or kebab-case tags) should be counted. Components imported but not used in the template do not count.

---

## 17. What the LLM Receives at Each Phase

| Phase | What the LLM sees |
|---|---|
| Per-file analysis (complex file) | Raw source of one file + its metrics + its ESLint flags + its API calls |
| Per-file analysis (simple file batch) | Raw source of up to 8 files + metrics + flags + API calls for each |
| Executive synthesis | Project summary stats + all findings from ai_issues grouped by severity + skeleton map |

The LLM never receives all raw source files at once. Local models have limited context windows and attention degrades on long inputs. The file-by-file approach achieves complete coverage without context limit problems.

---

## 18. Crash Recovery

The `audit_runs` table tracks every run. At startup, the agent checks for any row with status = 'in_progress'. If found, it prompts the user in the terminal:

```
Found interrupted run started at [timestamp].
Last completed file: [file_path]
Resume? (y/n):
```

If yes, it skips all files already in `ai_issues` for this run and continues from where it stopped. If no, it marks the old run as 'failed' and starts fresh.

---

## 19. Logging Rules

- All pipeline phase changes, progress updates, and errors go through a logger module. No bare `print()` statements anywhere in the pipeline code.
- Log levels: INFO for normal progress, WARNING for validation failures (discarded LLM findings, files that failed to parse), ERROR for unrecoverable failures.
- The log file is `scan.log` in the tool root directory.
- The terminal shows INFO and above during a run so the developer can see progress in real time.

---

## 20. Future Extension Path (Design Constraints for Now)

These are not being built now but the architecture must not block them.

**IDE Extension:** The FastMCP server (`mcp_agent/server.py`) is designed to run as a subprocess spawned by the extension. The extension passes the project path via CLI argument. The MCP server self-initializes the SQLite database at that path. No MySQL, no manual setup, no config files needed from the user — the extension provides the project path and everything else is automatic.

**Multi-project support:** The `project_name` column in every table allows multiple projects to coexist in a single SQLite database. This is already built into the schema. The extension can use the VS Code workspace folder name as the project_name automatically.

**Jump to line:** The AI issues stored in `ai_issues` each have a `file_path` and `line_number`. The IDE extension can use these to implement "click a finding, jump to that exact line in the editor." This is only possible in the extension context, not in the browser dashboard.

---

## 21. Summary — The 3 Core Rules

1. **The extractors are ground truth.** AST, ESLint, and API extraction produce exact facts. The LLM uses these facts as grounding data. Never remove them, never let the LLM replace them.

2. **The LLM is an analyst, not a data source.** The LLM generates insights and recommendations. It does not generate metrics, WCAG metadata, code snippets, or any other data that can be computed deterministically.

3. **Zero user setup for the end goal.** Every architectural decision must be compatible with a future IDE extension where the user provides only a project path. No external databases, no manual credential management, no compilation steps.
