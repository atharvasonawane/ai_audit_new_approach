import codecs

md_content = """# PROJECT_CONTEXT.md

> **Purpose:** This document is the authoritative technical reference for the **Code Audit Librarian** project. It is intended to provide AI systems and human developers with a complete, structured understanding of the system architecture, task implementations, and technical gaps to continue development efficiently.

---

## 1. Project Overview

* **Project Name:** Code Audit Librarian
* **Purpose of the Project:** An automated, end-to-end static analysis and AI-assisted auditing pipeline for legacy Vue.js 2 codebases. It processes `.vue` files to extract structural metrics, identify architectural anti-patterns, evaluate UI consistency and accessibility rules, persist analytical findings to a MySQL database, and compile the results into an interactive HTML dashboard featuring actionable, AI-generated code remediation suggestions.
* **Problem it Solves:** Manual code reviews of massive Vue.js monoliths scale poorly, lack consistency, and are prone to human error. This platform automates the extraction and categorization of high-risk components (e.g., highly coupled logic, monolithic sizes, excessive API integrations, and fundamental UI/a11y defects) into a structured queryable database, surfacing those insights automatically to stakeholders.
* **Target Users:** Software engineering teams, QA analysts, and technical leads responsible for auditing, refactoring, and maintaining enterprise Vue.js applications who require codebase health metrics aggregated without manual source code traversal.

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Processing** | Python 3.11+ | Orchestrates the extraction pipeline, calculations, and execution tasks. |
| **Database** | MySQL 8.x (`mysql-connector-python`) | Primary data store for extracted metrics, flags, and UI components. |
| **HTML UI Dashboard** | Jinja2 (`templates/report.html`), CSS3 | Static HTML generation for rendering the final reporting dashboard. |
| **AI Suggestions** | Python logic + AI APIs (e.g., Ollama) | Analyzes specific component defects via prompt engineering to suggest code fixes. Results are cached in JSON. |
| **Configuration** | YAML (`PyYAML`), DotEnv (`python-dotenv`) | Manages environmental secrets and pipeline threshold rules (`project_config.yaml`). |
| **Parsing Engines** | `lxml`, `html.parser`, standard `re` | Transforms raw Vue SFCs into abstract syntax data, mapping templates, styles, and scripts. |
| **Linguistics Validation** | `pyspellchecker` | Analyzes static HTML nodes and text arrays for grammatical/spelling defects. |
| **Filesystem Interaction** | `pathlib` | Discovers Vue single-file components dynamically via globbing `rglob`. |

---

## 3. Architecture

### Overall Architecture
The system operates as a **sequential multi-task pipeline monolith** paired with a static site generator. The architecture strictly enforces a unidirectional data flow. There are **no independent microservices, no background workers, and no conversational UI chatbots**. It executes linearly, populates the database (schema-on-write), and concludes by rendering a static dashboard.

### Data Flow

```text
[Vue.js Source Code Directory]
         │
         ▼
[1] run_audit.py ──► setup_schema() ──► Drops and recreates MySQL schema tables.
         │
         ├──► [2] Task 2: scan_all_vue_files()
         │       ├─ vue_parser.py ──► Isolates <script>, <template>, <style> blocks.
         │       ├─ complexity_checker.py ──► Tallies methods, watchers, and lines.
         │       ├─ api_extractor.py ──► Captures API calls (Regex-based matches).
         │       └─ flag_engine.py ──► Evaluates rule thresholds, returns risk strings.
         │               ▼
         │          write_file_result() ──► Upserts arrays into `vue_files`, `api_calls`, `file_flags`.
         │
         ├──► [3] Task 3: task3_exporter.py ──► Generates `component_complexity.json`.
         │
         ├──► [4] Task 4: task4_ui_extractor.py ──► Maps elements to `ui_extractions`.
         │
         ├──► [5] Task 5: ui_consistency_checker.py ──► Spellchecks text, writes `ui_defects`.
         │
         ├──► [6] Task 6: accessibility_checker.py ──► Analyzes ARIA/alt, writes `accessibility_defects`.
         │
         └──► [7] Task 7: issue_detector.py ──► Integrates tables → applies Risk Algorithm → `issue_report.json`.

[Code Audit Database (MySQL)]
         │
         ├──► export_db_to_json() ──► `task2_db_export.json`
         │
         ▼
[8] Report Generation Phase
    ├─ report/data_aggregator.py ──► Queries final analytical arrays from MySQL.
    ├─ report/health_score.py ──► Deducts penalty points (Base 100) combining structural flaws.
    ├─ report/ai_suggestor.py ──► Submits anomalies to local AI endpoint, caching JSON responses.
    └─ report/report_server.py ──► Executes Jinja2 compiler merging data → `report.html`.
```

### Key Design Patterns
* **Chain of Responsibility / Linear Pipeline:** Python scripts execute sequentially decoupled operations. Intermediate task failures emit warnings but do not halt subsequent analyzer steps.
* **Schema-on-Write Execution:** MySQL schemas are explicitly built during initialization via DDL logic inside `db_writer.py`.
* **Stateless Rules Engine Execution:** Flag assignment (`flag_engine.py`) and UI rules are enforced using array evaluations memory. They hold no internal state.
* **Decoupled AI Augmentation:** AI models handle exclusively offline remediation logic. Generated code advice is injected contextually inside the report but does not modify physical `.vue` files.

---

## 4. Project Structure

```text
final_approach_main/
├── PROJECT_CONTEXT.md          ← Foundational architecture and engineering specification
├── tasks_summary.txt           ← Reference compilation of original tasks specification
│
├── audit_tool/                 ← App Root Directory
│   ├── run_audit.py            ← ENTRY POINT: Coordinates DB setup and Tasks 2-7
│   ├── requirements.txt        ← Defined Python package dependencies
│   ├── .env                    ← Uncommitted datastore & endpoint secrets
│   │
│   ├── config/
│   │   └── project_config.yaml ← Defines thresholds, baseline constants, and scanning locations
│   │
│   ├── task2_audit/            ← Parsing and Identification Tasks
│   │   ├── extractors/
│   │   │   ├── orchestrator.py       ← Directory router triggering file analysis sequence
│   │   │   ├── vue_parser.py         ← String boundary splitting mapping Vue blocks
│   │   │   ├── script_cleaner.py     ← Pre-execution bloat & comment stripping
│   │   │   ├── complexity_checker.py ← Node counters tracking Vue objects constraints
│   │   │   ├── template_extractor.py ← HTML depth/child tag measurement constraints
│   │   │   ├── api_extractor.py      ← HTTP logic tracker isolating loops/mounted scopes
│   │   │   └── path_utils.py         ← Universal OS-specific path canonicalization
│   │   ├── checkers/
│   │   │   └── flag_engine.py        ← Boolean condition trees generating array constants
│   │   └── db/
│   │       └── db_writer.py          ← Relational database binding arrays
│   │
│   ├── task3/
│   │   └── task3_exporter.py         ← Renders component_complexity outputs
│   │
│   ├── task4/
│   │   └── task4_ui_extractor.py     ← Separates presentation HTML UI tokens
│   │
│   ├── task5/
│   │   └── ui_consistency_checker.py ← Pyspellchecker validation processes
│   │
│   ├── task6/
│   │   └── accessibility_checker.py  ← WCAG validation arrays mapping structure
│   │
│   ├── task7/
│   │   ├── issue_detector.py         ← Aggregated risk algorithms
│   │   └── db_report_loader.py       ← Validated helper functions querying datasets safely
│   │
│   ├── report/                 ← Frontend Static Web Deployment
│   │   ├── report_server.py    ← Webpage compilation generator
│   │   ├── data_aggregator.py  ← MySQL to Python Array struct parsers
│   │   ├── health_score.py     ← Point deduction computations mapping final score
│   │   ├── ai_suggestor.py     ← API wrapper tracking local LLM advice blocks
│   │   ├── ai_suggestions_cache.json ← Local buffer neutralizing LLM token latency
│   │   ├── templates/
│   │   │   └── report.html     ← Dashboard source framework template
│   │   └── static/
│   │       └── styles.css      ← Aesthetic parameters UI definitions
│   │
│   └── tools/                  ← Ancillary backend functions
│       ├── code_tools.py
│       ├── data_loader.py
│       └── db_tools.py
│
└── code_analyzer_db/           ← Legacy testing wrappers
    ├── db_check.py
    ├── db_verify.py
    └── db_loader.py
```

---

## 5. Tasks Implementation Status

The pipeline processes rules explicitly derived from 7 defined extraction goals. 

| Task Definition | Implemented Functionality | Not Yet Implemented |
|---|---|---|
| **Task 2: Complexity & Scanners** | Component code extraction (methods, lines, children). Tracks API logic tied to `mounted()` methods/loops. Static rules assign Flags correctly. | Payload analytics are entirely abstracted (Variables: `payload_keys`, `payload_depth`, `payload_size_kb` exist but return `0`). `COMPLEX_PAYLOAD` flags fail to execute. |
| **Task 3: Complexity Export** | Sorts and renders `component_complexity.json` mapped accurately against SQL array arrays. | Original specifications requested mapping analysis back via dedicated queries, instead it operates exclusively writing JSON outputs. |
| **Task 4: UI Tracker Extraction** | HTML labels, buttons, headers extracted efficiently into `ui_extractions.json` and SQL Tables. | Downstream modules (UI Consistency logic, AI prompt payloads) do not comprehensively cross-reference or utilize CSS classes collected. |
| **Task 5: UI Consistency Rules** | Implemented label validation schemas mapping spelling using generic dictionaries. Checks label-to-input `<label for="x">` assignments. | Complex UI assertions (Button style consistency via padding/radii, cross-page font alignment, color/theme checking dependencies) operate untracked without AST DOM rendering capabilities. |
| **Task 6: Accessibility Auditing** | Parses `<img alt>`, `<aria-label>`, disabled interactive buttons, and specific form accessibility traits efficiently mapping defect constraints. | CSS-driven compliance checks (Color contrast ratios 4.5:1, Keyboard traps, Focus Visibility `outline:none`, Responsive zoom tests 200%, Touch targets 44px bounds) are fundamentally unverified. |
| **Task 7: Risk & AI Generation** | Loads arrays creating integer penalties (`health_score.py`) grouping metrics as CRITICAL/HIGH/MEDIUM/LOW scaling reporting algorithms directly mapping HTML displays alongside Offline AI Suggestor code strings. | The explicit target to log the generated audit block permanently into a native `ai_project_report` MySQL table (`projectScore`, `riskLevel`) operates incompletely relying on JSON reports rather than table inserts. |

---

## 6. Core Modules / Important Files

* **`audit_tool/run_audit.py`:** Central coordinator. Establishes the DB footprint passing instantiated context dictionaries to lower tiers natively minimizing global scopes.
* **`audit_tool/task2_audit/db/db_writer.py`:** Core CRUD controller housing `setup_schema()`. Replaces Object-Relational-Mappers (ORM) with concrete SQL formatted queries isolating DB complexity securely.
* **`audit_tool/task2_audit/checkers/flag_engine.py`:** A strict logical engine accepting defined complexity sizing dicts dispersing boolean mappings translated immediately into constants like `EXCESSIVE_API_USAGE`.
* **`audit_tool/task7/issue_detector.py`:** Translates flat file faults spanning spelling, a11y, and code structural failures unifying them directly inside an overarching risk severity classifier algorithm.
* **`audit_tool/report/report_server.py`:** Merges JSON analytics and Jinja layout parameters. Translates intelligence into user readable aesthetic formats inherently disconnected from processing networks.
* **`audit_tool/report/ai_suggestor.py`:** Packages broken code arrays addressing defined HTTP AI endpoint layers returning and caching exact schema remediation sequences.

---

## 7. API Design (Internal)

* **Internal / External Routes:** The application operates solely as a Command Line sequence exporting static files. No traditional routing servers (e.g. Flask/FastAPI REST endpoints) evaluate remote execution requests natively.
* **AI Invocation Endpoints (`ai_suggestor.py`):** Invokes standardized internal HTTP POST requests tracking local LLM backend nodes. Submits raw component metrics requiring JSON block completions passed securely. No internal application authentication mechanisms are configured as execution is localized.

---

## 8. Database Schema

Constructed dynamically schema-on-write within `db_writer.py`.

* **Tables:**
  * `vue_files`: Central tracking dimension mapping normalized physical paths arrays alongside base node metric counters (`script_lines`, `methods`, `watchers`).
  * `api_calls`: Relational execution tracking HTTP matched identifiers noting if occurrences fire within loops or mounting sequences.
  * `file_flags`: Assigned condition mappings triggered explicitly per specific component.
  * `ui_extractions`: Raw elements mapping DOM text arrays measuring presentation boundaries.
  * `ui_defects`: Evaluated string validation flaws tracking failed dictionary values directly to presentation components.
  * `accessibility_defects`: WCAG compliance violations cataloging severity limits mapped structurally.
* **Relationships:** 
  * All secondary tables tie exactly defined boundaries mapping Foreign Keys referencing `vue_files.id` utilizing `CASCADE DELETE` logic natively guaranteeing implicit database relational cleanup structures.

---

## 9. Current Status

* **Fully Completed:** High-fidelity multi-task sequential auditing (Tasks 2-7), schema-on-write DB architectures, declarative heuristic trees mapping rule flags dynamically, DB export to JSON functions, and comprehensive HTML dashboard generation featuring offline AI remediation text injections.
* **Partially Completed:** Task 3 perfectly formats analytical metrics inside `component_complexity.json`, but currently does not sync secondary calculation modifications inside MySQL natively.
* **Not Implemented:** `setup_schema()` forcibly drops tables upon every execution—zero capability currently manages incremental "delta-scans" retaining historic timestamps mapped between codebase revisions natively. Additionally, payload evaluation parameters evaluate fixed boundaries (returning 0) overriding variable `COMPLEX_PAYLOAD` array flags entirely.

---

## 10. Development Workflow

* **How to run the project:**
  1. Boot a secure relational MySQL 8 instance.
  2. Map database host credentials via `.env` arrays uniquely within `audit_tool`.
  3. Map the target analysis location against `base_path` internally inside `audit_tool/config/project_config.yaml`.
  4. Initiate standard runtime: `python run_audit.py` from the `audit_tool` directory.
  5. The application computes the static results sequentially executing the compiler building `report.html` targeting localhost boundaries.
* **Build steps:** The system avoids frontend bundled artifacts compilation dependencies entirely running pure Python scripting seamlessly.
* **Environment variables:**
  * `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` configurations tracking the host overrides cleanly.

---

## 11. Coding Conventions

* **Naming conventions:** Standard PEP 8 Python `snake_case` methodology definitions dictating tables and execution functions organically. Application heuristics explicitly utilize bounded constants mapped organically via `UPPER_SNAKE_CASE` (e.g. `LARGE_COMPONENT`) facilitating JSON formatting logic constraints inherently.
* **Architecture Patterns:**
  * *Global Dependency Injection:* Configurations map standard objects via `cfg` boundaries parameters neutralizing implicit singleton instantiation limits completely statically.
  * *Functional Purity:* Extraction sequences mapping data models operate absolutely stateless returning identical metric definitions measuring given file limits independently executing completely context-free organically cleanly.
  * *Canonical Format Integrity:* Sequence tracking executes absolute normalization OS translations mapped explicitly utilizing `path_utils.normalize_path()` internally dodging any Linux vs Windows pathing logic conflicts scaling correctly natively securely.

---

## 12. Dependencies

* `mysql-connector-python`: Synchronous Oracle implementation mapping transactions cleanly locally efficiently bypassing bulky ORM frameworks processing queries structurally natively securely.
* `PyYAML`: Decodes and injects explicit scanner runtime limitations mappings parameters dynamically tracking structural thresholds organically.
* `python-dotenv`: Maps localized operational configurations variables protecting code credentials parsing directly ignoring version controls gracefully inherently securely.
* `lxml` / `html.parser`: Robust DOM manipulation mapping trees defining structural boundaries processing layouts natively inherently securely organically cleanly.
* `pyspellchecker`: Employs robust internal dictionaries isolating presentation errors against structural tags mapping organic defects seamlessly securely.
* `Jinja2`: Templating pipeline formatting explicit runtime dashboard bounds producing final HTML files processing layout designs seamlessly natively.

---

## 13. Future Scope / TODO

* **Planned Enhancements:**
  * *Vue 3 Composition Architecture:* Evolve regex structures isolating `setup()`, and `<script setup>` macros variations explicitly to replace exclusively monolithic Option API mappings properly scaling Vue 3 organically effectively seamlessly seamlessly natively.
  * *Delta Caching Sequences:* Inject explicitly `mtime` modification checks generating cache bounds gracefully mapping untouched modules scaling analytics processing duration flawlessly.
* **Refactoring Priorities:** Ensure comprehensive parameters correctly route `ui_extractions` formatting CSS schema definitions directly validating presentation alignment logic offline organically realistically natively. Re-map abstract constraints limiting `payload_keys` limits explicitly inside `orchestrator.py` defining actual physical bytes accurately organically cleanly natively effectively securely.

---

## 14. Known Issues

* **Bugs:** Metrics bounded explicitly identifying Payload dimensions pass fixed zeros fundamentally disabling downstream analysis thresholds mapping dynamic properties explicitly overriding heuristic bounds definitions universally natively.
* **Performance issues:** Processing demands total MySQL purges dynamically wiping data completely executing full table rebuilds linearly scaling operation limits causing enormous processing lengths scanning exceptionally large modular directories sequentially organically.
* **Technical Debt Constraints:** Context integrations via static AI modeling logic processes hard limits dropping extremely massive codebase prompts intrinsically generating contextual clipping dynamically fundamentally blocking remediation bounds organically cleanly natively organically realistically natively smoothly.
"""

with codecs.open("PROJECT_CONTEXT.md", "w", encoding="utf-8") as f:
    f.write(md_content)
