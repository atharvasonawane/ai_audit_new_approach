# Code Audit Librarian — Master Implementation Guide

> **For any AI assistant reading this:**
> This document is the complete, final specification for the Code Audit Librarian tool.
> The developer will work with you step by step to build this.
> Your job is to help implement exactly what is described here — one stage at a time.
> Do not suggest architectural changes unless the developer asks.
> Do not over-engineer. Every decision here is already finalized.

---

## 0. What Is This Tool

The Code Audit Librarian is a developer tool that:

1. Takes a Vue.js codebase as input (a directory path)
2. Scans every `.vue` and `.js` file using Python AST parsing and ESLint
3. Sends file data to a local LLM (Ollama) for architectural analysis
4. Generates a single self-contained HTML report covering every file in the codebase

The report shows every architectural issue found, with exact line numbers, the problematic code snippet, severity level, and a recommendation. It also includes an AI-written executive summary of the whole project's health.

**No file is ever skipped or filtered out.** Every file in the codebase gets analyzed regardless of size or complexity.

---

## 1. Core Principles — Read These First

**Principle 1: No file is skipped.**
A small 30-line file can be critical (an auth service, a router config, a shared composable). Size and complexity metrics do not determine importance. Every `.vue` and `.js` file in the target codebase gets analyzed.

**Principle 2: AST and ESLint are non-negotiable.**
The LLM cannot count things precisely. AST counts methods, nesting depth, and API calls with 100% accuracy. ESLint catches Vue violations deterministically. These facts are given to the LLM as grounding data. Removing them makes LLM analysis worse, not simpler.

**Principle 3: Direct synchronous LLM calls only.**
No MCP. No tool-use. No agentic loops. Local LLMs (Llama 3, Mistral via Ollama) are unreliable at tool-use. Direct synchronous calls with a strict JSON response schema are predictable, debuggable, and fast to build.

**Principle 4: SQLite as the single source of truth.**
All Scout data, all LLM findings, and all run state live in SQLite. This enables crash recovery (resume interrupted runs), complex queries for report ranking, and zero memory limits regardless of codebase size.

**Principle 5: Static HTML report.**
The final output is one self-contained HTML file with embedded CSS. No npm server. No external dependencies. Open in any browser, share via email, works offline.

**Principle 6: Build CLI first, VS Code extension second.**
The entire analysis pipeline runs as a Python CLI tool. The VS Code extension is a thin shell built on top of the working CLI. Do not start the extension until the CLI works end-to-end.

---

## 2. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.10+ | Existing codebase, strong AST libraries |
| AST Parsing | Tree-sitter + tree-sitter-vue | Reliable Vue SFC structural extraction |
| Parallel Scanning | `concurrent.futures.ThreadPoolExecutor` | Scan all files simultaneously — 10x faster than sequential |
| Linting | ESLint via Python subprocess | Deterministic Vue best-practice and accessibility rules |
| Database | SQLite (`sqlite3` — built into Python) | Zero installation, crash recovery, complex queries |
| LLM | Ollama running locally (Llama 3 or Mistral) | Free, offline, no API costs, privacy-preserving |
| LLM SDK | `openai` Python SDK with Ollama base URL | OpenAI-compatible API, simple synchronous calls |
| Report | Static HTML + embedded CSS + embedded JS | Portable, no server, works anywhere |
| Config | `project_config.yaml` + PyYAML | Single config file per project |
| Entry Point | Python CLI (`run_audit.py`) | Run from terminal or spawned by VS Code extension |

---

## 3. Folder Structure

```
audit_tool/
│
├── run_audit.py                        ← Entry point. Runs all phases in sequence.
├── project_config.yaml                 ← All project settings live here.
│
├── scout/                              ← Phase 1: Deterministic scanning (no LLM)
│   ├── scanner.py                      ← ThreadPoolExecutor file walker
│   ├── vue_parser.py                   ← Tree-sitter SFC block splitter
│   ├── metrics_extractor.py            ← Counts methods, nesting, complexity, LOC
│   ├── import_extractor.py             ← Reads real import/export statements
│   ├── api_extractor.py                ← Detects API calls, type, line, context
│   ├── eslint_runner.py                ← Subprocess ESLint + JSON output parser
│   ├── script_cleaner.py               ← Strips comments, preserves structure
│   ├── db_writer.py                    ← Upsert all Scout results to SQLite
│   └── skeleton_builder.py             ← Builds skeleton_map.txt from SQLite
│
├── ai_pipeline/                        ← Phase 2: Three sequential AI scripts
│   ├── ai_dependency_builder.py        ← LLM analyzes component relationships
│   ├── ai_reporter.py                  ← LLM analyzes every file, logs issues
│   └── ai_architecture_analyzer.py    ← LLM writes whole-codebase synthesis
│
├── report/
│   └── report_generator.py             ← Reads SQLite, generates HTML report
│
├── audit_history.db                    ← SQLite DB (auto-created at runtime)
├── skeleton_map.txt                    ← Compact codebase summary (auto-generated)
├── audit_report.html                   ← Final output report (auto-generated)
└── scan.log                            ← Runtime log (auto-created)
```

---

## 4. SQLite Database Schema

Every connection must run:
```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

### Table: `vue_files`
Stores Scout-extracted structural facts for every file.
```sql
CREATE TABLE IF NOT EXISTS vue_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    script_lines INTEGER DEFAULT 0,
    template_lines INTEGER DEFAULT 0,
    style_lines INTEGER DEFAULT 0,
    methods INTEGER DEFAULT 0,
    computed INTEGER DEFAULT 0,
    watchers INTEGER DEFAULT 0,
    props INTEGER DEFAULT 0,
    emits INTEGER DEFAULT 0,
    api_total INTEGER DEFAULT 0,
    api_in_mounted INTEGER DEFAULT 0,
    api_in_loop INTEGER DEFAULT 0,
    child_components INTEGER DEFAULT 0,
    max_nesting_depth INTEGER DEFAULT 0,
    cyclomatic_complexity INTEGER DEFAULT 0,
    payload_size_kb REAL DEFAULT 0,
    eslint_flag_count INTEGER DEFAULT 0,
    script_setup BOOLEAN DEFAULT 0,
    template_only BOOLEAN DEFAULT 0,
    typescript_detected BOOLEAN DEFAULT 0,
    last_modified REAL,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_name, file_path)
);
```

### Table: `file_flags`
ESLint findings per file.
```sql
CREATE TABLE IF NOT EXISTS file_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vue_file_id INTEGER NOT NULL,
    project_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    rule TEXT,
    message TEXT,
    severity TEXT,
    line_number INTEGER DEFAULT 0,
    column_number INTEGER DEFAULT 0,
    FOREIGN KEY (vue_file_id) REFERENCES vue_files(id) ON DELETE CASCADE
);
```

### Table: `api_calls`
Every API call detected per file.
```sql
CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vue_file_id INTEGER NOT NULL,
    project_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    api_type TEXT,
    method_name TEXT,
    endpoint TEXT,
    in_mounted BOOLEAN DEFAULT 0,
    in_loop BOOLEAN DEFAULT 0,
    line_number INTEGER DEFAULT 0,
    FOREIGN KEY (vue_file_id) REFERENCES vue_files(id) ON DELETE CASCADE
);
```

### Table: `component_relationships`
Import graph extracted from real import statements by AST.
```sql
CREATE TABLE IF NOT EXISTS component_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    parent_file TEXT NOT NULL,
    child_file TEXT NOT NULL,
    relationship_type TEXT,
    UNIQUE(project_name, parent_file, child_file)
);
```

### Table: `ai_issues`
Every issue the LLM identifies, from all three AI phases.
```sql
CREATE TABLE IF NOT EXISTS ai_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    phase TEXT NOT NULL,
    issue_category TEXT,
    description TEXT,
    severity TEXT CHECK(severity IN ('High', 'Medium', 'Low')),
    line_number INTEGER DEFAULT 0,
    code_snippet TEXT,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table: `audit_runs`
Tracks run state for crash recovery and progress display.
```sql
CREATE TABLE IF NOT EXISTS audit_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    current_phase TEXT DEFAULT 'scout',
    status TEXT DEFAULT 'in_progress',
    last_completed_file TEXT,
    total_files INTEGER DEFAULT 0,
    completed_files INTEGER DEFAULT 0,
    synthesis_text TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

---

## 5. Phase 1 — The Scout

### What It Does
The Scout extracts structural facts from every file using AST and ESLint. It does not call the LLM. It is fast (seconds, not minutes) and 100% accurate.

### How Files Are Selected
`scanner.py` walks the target directories from `project_config.yaml`. It processes every file with extensions `.vue` or `.js`. It skips:
- `node_modules/`
- `dist/`
- `.git/`
- `coverage/`
- Files ending in `.test.js`, `.spec.js`, `.min.js`
- Files listed in `exclude_paths` in config

**Application logic files are never skipped regardless of size.**

### Incremental Scanning (Skip Unchanged Files)
Before processing any file, the Scout checks SQLite:
1. Compare file's `os.path.getmtime()` against `last_modified` in `vue_files`
2. If mtime matches → file unchanged → skip entirely
3. If mtime differs → calculate SHA-256 hash
4. If hash matches stored `file_hash` → content unchanged → skip
5. If hash differs → file genuinely changed → run full extraction

On a second run after one file changes, only that one file is re-scanned.

### Parallel Scanning
`scanner.py` uses `ThreadPoolExecutor` with `max_workers` from config (default: 8). All eligible files are submitted simultaneously. Results are written to SQLite as each file completes.

### What Is Extracted Per File

**From Tree-sitter AST (`vue_parser.py` + `metrics_extractor.py`):**
- Template block, script block, style block (split cleanly)
- `script_lines` — lines in the script block
- `template_lines` — lines in the template block
- `methods` — count of methods in the `methods: {}` object
- `computed` — count of computed properties
- `watchers` — count of watch properties
- `props` — count of declared props
- `emits` — count of declared emits
- `max_nesting_depth` — deepest HTML element nesting in template
- `cyclomatic_complexity` — number of decision points (if/else/for/while/ternary)
- `script_setup` — boolean, true if using `<script setup>`
- `template_only` — boolean, true if no script block
- `typescript_detected` — boolean, true if `lang="ts"` on script tag

**From `import_extractor.py`:**
- All import statements parsed from the script block
- Each import resolved to a relative file path where possible
- Written to `component_relationships` table as `parent_file → child_file`

**From `api_extractor.py`:**
- Every `axios`, `fetch`, `$http`, `useQuery`, `useMutation` call detected
- For each: type, method name, endpoint, line number
- `in_mounted` — true if call is inside `mounted()` or `onMounted()`
- `in_loop` — true if call is inside a `for`, `forEach`, `map`, or `while`

**From `eslint_runner.py`:**
- ESLint runs via subprocess with `--format json`
- Every finding written to `file_flags` with rule, message, severity, line number

### After All Files Are Scanned: Skeleton Builder

`skeleton_builder.py` generates `skeleton_map.txt` — one line per file:

```
src/components/Checkout.vue | 340 lines | 12 methods | 8 APIs (1 in loop) | nesting:5 | complexity:14 | eslint:[no-unused-vars, alt-text] | a11y:2
src/components/UserProfile.vue | 180 lines | 4 methods | 2 APIs (0 in loop) | nesting:2 | complexity:5 | eslint:[] | a11y:0
src/components/PaymentForm.vue | 520 lines | 18 methods | 14 APIs (3 in loop) | nesting:7 | complexity:22 | eslint:[prop-drilling, unused-vars] | a11y:5
src/services/authService.js | 45 lines | 3 methods | 2 APIs (0 in loop) | nesting:0 | complexity:6 | eslint:[] | a11y:0
src/router/index.js | 38 lines | 0 methods | 0 APIs | nesting:0 | complexity:4 | eslint:[] | a11y:0
```

This is the LLM's bird's-eye view of the entire codebase. For 114 files it is approximately 4,000–6,000 tokens — fits in any local LLM context window.

---

## 6. The File Bundle

Every file has a bundle assembled from SQLite and disk. This is what the LLM receives per file during analysis.

```json
{
  "file_path": "src/components/Checkout.vue",
  "source_code": "< full raw file contents as string >",
  "metrics": {
    "script_lines": 340,
    "template_lines": 180,
    "methods": 12,
    "computed": 4,
    "watchers": 2,
    "props": 6,
    "emits": 3,
    "api_total": 8,
    "api_in_mounted": 3,
    "api_in_loop": 1,
    "max_nesting_depth": 5,
    "cyclomatic_complexity": 14,
    "payload_size_kb": 2.4
  },
  "imports": [
    "src/components/UserCard.vue",
    "src/services/cartService.js"
  ],
  "eslint_flags": [
    { "rule": "vue/no-unused-vars", "line": 23, "severity": "warn" },
    { "rule": "vuejs-accessibility/alt-text", "line": 67, "severity": "error" }
  ],
  "api_calls": [
    { "type": "axios", "method": "fetchCart", "line": 45, "in_mounted": true, "in_loop": false },
    { "type": "axios", "method": "updateItem", "line": 112, "in_mounted": false, "in_loop": true }
  ]
}
```

---

## 7. Phase 2 — AI Pipeline

Three scripts run sequentially. Each makes direct synchronous calls to Ollama using the `openai` SDK.

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

response = client.chat.completions.create(
    model="llama3",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.2
)

result = response.choices[0].message.content
```

**Every prompt expecting JSON must end with:**
> "Return a JSON array only. No preamble. No explanation. No markdown code fences."

**If LLM returns malformed JSON:** Retry once with "Your previous response was not valid JSON. Return JSON only." If still malformed: log to `scan.log`, skip that file/batch.

---

### AI Script 1: `ai_dependency_builder.py`

**Job:** Analyze the component relationship graph to find structural dependency problems across the whole codebase.

**Receives:** Full `skeleton_map.txt` + full `component_relationships` table.
**Does NOT receive:** Raw source code.

**System prompt:**
```
You are a Senior Frontend Architect analyzing a Vue.js component
dependency graph.

You will receive:
1. A skeleton map of the entire codebase with metrics per file
2. A list of component relationships (who imports who)

Identify these dependency problems:
- Prop Drilling Chain: props passed down 3+ levels
- God Component: imports 8+ other components
- Circular Dependency: A imports B which imports A
- Orphaned Component: no parent imports it
- Over-coupled Service: imported by 10+ components

Return a JSON array only. No preamble. No markdown.

Schema:
[{
  "issue_category": "Prop Drilling Chain",
  "description": "Specific explanation",
  "severity": "High",
  "affected_files": ["src/components/A.vue"],
  "recommendation": "Concrete fix"
}]
```

**User prompt:**
```
Skeleton Map:
[skeleton_map.txt contents]

Component Relationships:
[component_relationships formatted as: ParentFile → ChildFile]
```

**Output:** Each item in JSON array → inserted into `ai_issues` with `phase = 'dependency'`.

**Console output:**
```
[AI Phase 1/3] Analyzing dependency graph...
[AI Phase 1/3] Complete. 6 dependency issues found.
```

---

### AI Script 2: `ai_reporter.py`

**Job:** Analyze every file and identify per-file architectural issues with line numbers and code snippets.

**Rule: Every file is analyzed. No file is skipped.**

**Batching strategy — for efficiency, not filtering:**

```python
COMPLEX_THRESHOLD = 150  # script_lines
BATCH_SIZE = 8

complex_files = [f for f in all_files if f['script_lines'] >= COMPLEX_THRESHOLD]
simple_files  = [f for f in all_files if f['script_lines'] < COMPLEX_THRESHOLD]
```

- Complex files (150+ script lines): one LLM call per file, full focused attention
- Simple files (under 150 lines): grouped into batches of 8, one LLM call per batch
- Both groups get analyzed. Nothing is discarded.

**System prompt for complex files (individual):**
```
You are a Senior Frontend Architect reviewing a single Vue.js component.
You have the full source code plus AST metrics and ESLint findings.

Do NOT report ESLint syntax violations — those are captured separately.

Focus ONLY on architectural issues:
- State Management Bloat: unrelated state crowded into data()
- Prop Drilling: receiving props only to pass them to children
- Component Over-responsibility: doing too many jobs
- API Flow Issues: calls in wrong lifecycle hooks or inside loops
- Logic Misplacement: business logic that belongs in a service or composable
- Performance Risks: expensive operations in watchers or computed

For every issue you MUST provide:
- Exact line number
- 3 to 5 line code snippet showing the problem
- Concrete actionable recommendation

Return a JSON array only. No preamble. No markdown.

Schema:
[{
  "issue_category": "State Management Bloat",
  "description": "Specific explanation for this file",
  "severity": "High",
  "line_number": 112,
  "code_snippet": "relevant lines from source",
  "recommendation": "Concrete fix"
}]

If no issues found, return: []
```

**User prompt (individual):**
```
File: [file_path]
[full bundle JSON]
```

**System prompt for simple files (batched):**
Same as above, plus:
```
You will receive multiple small Vue.js components.
Analyze each one separately.

Return a JSON object where each key is the file_path and
the value is an array of issues for that file.

Schema:
{
  "src/components/FileA.vue": [...issues...],
  "src/components/FileB.vue": [],
  "src/components/FileC.vue": [...issues...]
}
```

**User prompt (batch):**
```
File 1: src/components/HeaderNav.vue
[bundle JSON]

File 2: src/components/FooterBar.vue
[bundle JSON]

[up to 8 files]
```

**Output:** All issues → inserted into `ai_issues` with `phase = 'per_file'`.

**Console output:**
```
[AI Phase 2/3] [12/114] Analyzing PaymentForm.vue → 4 issues (2H 1M 1L)
[AI Phase 2/3] [13/114] Analyzing Checkout.vue → 2 issues (1H 1M)
[AI Phase 2/3] [14-21/114] Batch: 8 simple files → 3 issues total
```

**Crash recovery:** After each file/batch, update `audit_runs.last_completed_file`. On resume, skip files already in `ai_issues`.

---

### AI Script 3: `ai_architecture_analyzer.py`

**Job:** Synthesize all findings into a whole-codebase executive assessment.

**Receives:** Full `skeleton_map.txt` + all `ai_issues` rows + summary statistics.
**Does NOT receive:** Raw source code.

**System prompt:**
```
You are a Senior Frontend Architect writing an executive
architectural report for a Vue.js codebase.

You have been given the skeleton map, all identified issues,
and summary statistics.

Write a structured assessment with EXACTLY these sections:

HEALTH SCORE
Score from 0 to 100. Two sentence justification.

TOP 5 CRITICAL COMPONENTS
The 5 most problematic components and exactly why.

RECURRING PATTERNS
Patterns appearing across multiple components.
Be specific about counts. Example: "API calls inside
v-for loops appear in 8 components."

PRIORITIZED RECOMMENDATIONS
Numbered list. High priority first. Concrete and actionable.

SUGGESTED REFACTORING SEQUENCE
In what order should the team fix things and why.

Write in plain text. Use the exact headings above.
Do not use JSON. Do not add extra sections.
```

**User prompt:**
```
Skeleton Map:
[skeleton_map.txt]

All Issues Found:
[ai_issues formatted as readable list grouped by file]

Statistics:
- Total files: 114
- Files with issues: 67
- High severity: 23 | Medium: 41 | Low: 18
- Most problematic: PaymentForm.vue (7 issues)
```

**Output:** Plain text → saved to `audit_runs.synthesis_text`.

---

## 8. Phase 3 — Report Generator

`report/report_generator.py` reads entirely from SQLite and generates one self-contained HTML file. All CSS and JS embedded inline. No external resources.

### Report Sections

**Section 1 — Executive Summary**
- AI synthesis from `audit_runs.synthesis_text`
- Health score extracted from synthesis
- Audit date, project name, total files scanned
- Four stat boxes: Total Issues / High / Medium / Low

**Section 2 — Audit Statistics**

| Metric | Value |
|---|---|
| Total files scanned | 114 |
| Files with AI issues | 67 |
| Files with no issues | 47 |
| Total ESLint flags | 187 |
| Accessibility defects | 23 |
| Dependency issues | 6 |

**Section 3 — Worst Offenders**

Top 10 files by score:
```
score = (High × 3) + (Medium × 2) + (Low × 1) + (api_in_loop × 2) + (eslint_flag_count × 0.5)
```

Table: Rank / Component / High / Medium / Low / Score / Top Issue

**Section 4 — Dependency Issues**
All `ai_issues` where `phase = 'dependency'`, grouped by category.

**Section 5 — Per-Component Findings**
One collapsible section per file that has issues. For each file:

```
▼ src/components/PaymentForm.vue                          🔴 HIGH

  Scout Metrics:
  520 lines | 18 methods | 14 APIs (3 in loops) | Nesting: 7 | Complexity: 22

  ESLint Flags:
  Line 45 — vue/prop-drilling (error)
  Line 89 — no-unused-vars (warn)

  Architectural Issues:

  🔴 HIGH — State Management Bloat @ line 112
  ┌─────────────────────────────────────────────┐
  │ 110  data() {                               │
  │ 111    return {                             │
  │►112      cartItems: [],                     │
  │ 113      userDetails: {},                   │
  │ 114      paymentMethods: [],                │
  └─────────────────────────────────────────────┘
  Description: [LLM description]
  Recommendation: [LLM recommendation]

  🟡 MEDIUM — API Call in Loop @ line 223
  [code snippet]
  Recommendation: [LLM recommendation]
```

Files sorted: highest severity first, then alphabetically.

**Section 6 — ESLint Flags Appendix**
All `file_flags` grouped by file.

**Section 7 — Accessibility Defects Appendix**
All accessibility-related `file_flags` grouped by file.

### Health Badge Color Logic
- 🔴 RED: file has any High severity issue
- 🟡 YELLOW: Medium issues, no High
- 🟢 GREEN: Low issues only or no issues

---

## 9. The Orchestrator — `run_audit.py`

### CLI Flags
```bash
python run_audit.py --project my-vue-app
python run_audit.py --project my-vue-app --scout-only
python run_audit.py --project my-vue-app --ai-only
python run_audit.py --project my-vue-app --resume
python run_audit.py --project my-vue-app --report-only
```

### Full Execution Sequence
```
1. Load project_config.yaml
2. Initialize SQLite (all tables, WAL mode)
3. Check audit_runs for in_progress run → offer resume

── PHASE 1: SCOUT ──────────────────────────────────────
4. Create audit_runs row: phase='scout'
5. ThreadPoolExecutor: scan all files in parallel
6. Write results to SQLite as files complete
7. Print: [87/114] files scanned...
8. Run skeleton_builder → write skeleton_map.txt
9. Print: Scout complete. 114 files in 5.3s

── PHASE 2: AI PIPELINE ────────────────────────────────
10. Check Ollama reachable (GET localhost:11434)
    → If not: print error with instructions, exit
11. Run ai_dependency_builder.py
    Print: [AI 1/3] Dependency analysis complete. 6 issues.
12. Run ai_reporter.py (progress per file/batch)
    Print: [AI 2/3] Per-file analysis complete. 82 issues.
13. Run ai_architecture_analyzer.py
    Print: [AI 3/3] Synthesis complete.
14. Update audit_runs: status='complete'

── PHASE 3: REPORT ─────────────────────────────────────
15. Run report_generator.py → write audit_report.html
16. Print: Report generated: audit_report.html
17. Auto-open in default browser
```

### Crash Recovery
```python
existing = db.query(
    "SELECT * FROM audit_runs WHERE project_name=? AND status='in_progress'",
    [project_name]
)
if existing:
    print(f"Interrupted run found. Phase: {existing.current_phase}. "
          f"Progress: {existing.completed_files}/{existing.total_files}")
    choice = input("Resume? [Y/n]: ")
    if choice.lower() != 'n':
        # Skip scout (data in SQLite)
        # Skip completed files in ai_reporter
        # Continue from current_phase
```

---

## 10. Error Handling

| Scenario | Behaviour |
|---|---|
| Scout fails on a single file | Log WARNING to scan.log, skip that file, continue |
| ESLint not installed | Log WARNING, skip ESLint, continue with AST only |
| Tree-sitter parse fails | Log WARNING, write partial metrics, continue |
| Ollama not reachable at startup | Print error with install instructions. Exit. |
| LLM returns malformed JSON | Retry once. If still bad: log to scan.log, skip file. |
| LLM call times out | Log WARNING, skip that file/batch, continue |
| SQLite write fails | Log ERROR, stop immediately. Do not corrupt state. |
| Process killed mid-run | On next run: offer resume from last_completed_file |

---

## 11. Configuration — `project_config.yaml`

```yaml
project:
  name: "my-vue-app"
  target_paths:
    - "src/components"
    - "src/views"
    - "src/pages"
    - "src/services"
    - "src/composables"
    - "src/router"
    - "src/store"
  exclude_paths:
    - "node_modules"
    - "dist"
    - "coverage"
    - ".git"

scout:
  file_extensions: [".vue", ".js"]
  eslint_config_path: ".eslintrc.js"
  eslint_batch_size: 30
  parallel_workers: 8

ai:
  provider: "ollama"
  model: "llama3"
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
  temperature: 0.2
  timeout_seconds: 90
  complex_file_threshold_lines: 150
  batch_size_simple_files: 8
  max_retries: 1

report:
  output_path: "audit_report.html"
  top_offenders_count: 10
  auto_open_browser: true
```

---

## 12. VS Code Extension (Build This Last)

**Do not start this until the CLI works end-to-end.**

The extension is a thin TypeScript shell. All analysis logic stays in Python.

**Extension responsibilities only:**
1. Detect workspace path via `vscode.workspace.workspaceFolders`
2. Check Python and Ollama available on activation
3. Show setup guide if dependencies missing
4. Spawn `run_audit.py` as a child process
5. Open VS Code Webview panel
6. Stream Python stdout to Webview in real time
7. Render final HTML report inside Webview
8. Enable "Jump to line" — clicking a finding opens that file at that line in editor

### UX Flow
```
User opens VS Code with Vue project
  → Extension activates
  → Checks Python ✅ and Ollama ✅
  → Scout runs silently in background (seconds)
  → Sidebar shows project file tree + Scout metrics
  → Banner: "Scout complete. 114 files scanned."
  → Button: "Run AI Analysis"
  → User clicks
  → Live progress feed in Webview
  → Full report renders in Webview when complete
  → Click any finding → jump to that exact line in editor
```

"Jump to line" is the killer feature only possible in VS Code. It makes findings immediately actionable without leaving the IDE.

---

## 13. Build Order — Follow This Exactly

### Stage 1 — SQLite Foundation
- Write `db_init.py` to create all tables
- Write `db_writer.py` with upsert functions for every table
- Test: insert one row into every table, query it back

### Stage 2 — Scout: Single File
- Get Tree-sitter parsing one `.vue` file
- Verify template/script/style block splitting
- Verify `metrics_extractor.py` counts methods correctly
- Verify `import_extractor.py` reads real import statements
- Verify `api_extractor.py` detects API calls with line numbers
- Verify `eslint_runner.py` subprocess returns valid JSON
- Write all results to SQLite for that one file
- Inspect SQLite — verify every field is populated correctly

### Stage 3 — Scout: Full Parallel
- Wrap in `ThreadPoolExecutor`
- Run against full test codebase
- Verify all files in SQLite
- Run again — verify mtime/hash skipping (zero re-scans of unchanged files)
- Run `skeleton_builder.py`
- Inspect `skeleton_map.txt` — verify readable and accurate

### Stage 4 — LLM JSON Validation (Critical Gate)
**Do not proceed to Stage 5 until this passes cleanly.**
- Manually call Ollama with one file bundle
- Verify response is valid JSON matching the schema
- Test 5 different files: complex component, simple component, template-only, JS service, router file
- If LLM adds preamble: fix system prompt
- If LLM wraps in markdown fences: add "No markdown code fences" to prompt
- If wrong schema: fix prompt, retest

### Stage 5 — AI Dependency Builder
- Build `ai_dependency_builder.py`
- Run standalone, verify JSON output
- Inspect `ai_issues` table — verify correct rows with `phase='dependency'`

### Stage 6 — AI Reporter
- Build `ai_reporter.py` with complex/simple split
- Test with 10 mixed files
- Verify all 10 appear in `ai_issues`
- Test crash recovery: kill mid-run, resume, verify no duplicates

### Stage 7 — AI Architecture Analyzer
- Build `ai_architecture_analyzer.py`
- Run standalone
- Read synthesis text from SQLite — verify it references real file names and real patterns

### Stage 8 — Orchestrator
- Build `run_audit.py` with all CLI flags
- Run full end-to-end on test codebase
- Test `--scout-only`, `--resume`, `--report-only`

### Stage 9 — Report Generator
- Build `report_generator.py`
- Generate HTML and open in browser
- Verify all sections render correctly
- Verify code snippets show correct line numbers with highlighted line
- Verify worst-offenders ranking formula is correct
- Verify report is fully self-contained (view source — no external URLs)

### Stage 10 — VS Code Extension
- Build extension shell: workspace detection, Webview
- Spawn `run_audit.py` as subprocess
- Stream stdout to Webview
- Render final HTML in Webview
- Add "Jump to line" via VS Code API

---

## 14. What the LLM Receives at Each Phase

| Phase | Skeleton Map | Raw Source | AST Metrics | ESLint Flags | All Findings |
|---|---|---|---|---|---|
| ai_dependency_builder | ✅ Full codebase | ❌ Never | ❌ Summarized in skeleton | ❌ Summarized in skeleton | ❌ |
| ai_reporter (complex) | ❌ | ✅ One file | ✅ One file | ✅ One file | ❌ |
| ai_reporter (batch) | ❌ | ✅ Up to 8 files | ✅ All in batch | ✅ All in batch | ❌ |
| ai_architecture_analyzer | ✅ Full codebase | ❌ Never | ❌ Summarized in skeleton | ❌ Summarized in skeleton | ✅ All |

The LLM never receives all raw source files at once. It gets either the skeleton (whole-codebase summary, small) or individual/batched file bundles (focused, one file or small group at a time).

---

## 15. Key Questions Answered

**Why not pass all raw source files to the LLM at once?**
114 Vue files = 100,000–150,000 tokens. Local LLMs have 8,000–32,000 token windows. It does not fit. Even with a large window, LLM attention degrades badly on long inputs — files in the middle get missed or hallucinated. The skeleton + file-by-file approach achieves the same result without the context limit problem.

**Why no MCP or tool-use?**
Local LLMs are inconsistent at calling functions with correct parameters. They sometimes return plain text, sometimes call the wrong tool, sometimes hallucinate parameters. Direct synchronous calls with a strict JSON schema are simpler and more reliable for local models.

**Why keep AST and ESLint if the LLM analyzes files anyway?**
The LLM reads source code and reasons about architecture. When told "this file has 14 API calls, 3 inside loops" from AST, the LLM can immediately reason about that as a pattern. Without those facts, it might miss them or count incorrectly. AST and ESLint give the LLM grounding data that makes analysis more accurate and focused.

**Why is no application file ever skipped?**
A 30-line `authService.js` with insecure token storage is more critical than a 500-line component with redundant code. Size does not equal importance. Batching small files together (8 per LLM call) ensures they all get analyzed efficiently without wasting individual LLM calls.

**Why SQLite instead of JSON files?**
JSON files in memory fail on large codebases (RAM limits). They cannot be queried. They have no crash recovery. SQLite writes incrementally, supports queries for ranking and filtering, enables resume-from-crash, and requires zero installation (built into Python).

**Why static HTML report instead of a running frontend?**
A static HTML file works anywhere — email it, share it, open it offline. An npm frontend requires a running development server. For a portable audit artifact, static HTML is strictly better.

**Why build CLI before VS Code extension?**
The CLI contains 95% of the value. It can be developed and tested without VS Code. Building the extension first couples development to the VS Code environment unnecessarily and slows everything down. Finish the Python pipeline, verify end-to-end, then add the extension as a thin shell.
