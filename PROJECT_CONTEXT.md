# PROJECT_CONTEXT.md

## 1. Project Overview
* **Project name:** Code Audit Librarian
* **Purpose of the project:** To automatically analyze, evaluate, and report on the complexity, architecture, UI consistency, and accessibility of a codebase (specifically targeting Vue.js projects).
* **Problem it solves:** Developers and QA engineers need an automated way to verify coding standards, extract API usage, measure component complexity, and ensure UI and accessibility consistency across large frontend codebases without manual code review.
* **Target users:** Frontend Developers, QA Engineers, and Technical Leads.

## 2. Tech Stack
* **Frontend:** HTML, CSS, Jinja templates (for the reporting dashboard)
* **Backend:** Python 3 (Audit pipeline, Orchestrator, Flask reporting server)
* **Database:** MySQL
* **APIs:** Internal data aggregators via JSON files and DB queries
* **Libraries / frameworks:**
  * Flask (Reporting Dashboard)
  * 	ree-sitter, 	ree-sitter-embedded-template, 	ree-sitter-yaml (AST-based code parsing)
  * mysql-connector-python (Database operations)
  * ESLint with eslint-plugin-vue and eslint-plugin-vuejs-accessibility (Vue best practices and accessibility auditing)
  * PyYAML (Configuration management)
  * python-dotenv (Environment variable management)
* **Dev tools:** Virtual environment (env), dotenv (Environment variable management), ESLint (Integrated for Vue best practices and accessibility checks)

## 3. Architecture
* **Overall architecture:** A monolithic ETL (Extract, Transform, Load) pipeline coupled with a monolithic web dashboard.
* **Data flow:** 
  1. The orchestrator (
un_audit.py) reads configuration from project_config.yaml.
  2. Parses target .vue and .js files using the 	ask2_audit extractors (Tree-sitter AST parsing).
  3. Runs ESLint scan via subprocess to capture Vue best practices and accessibility issues, parsing JSON output into file_flags and accessibility_defects tables.
  4. Hands data to modular sub-tasks (	ask3, 	ask5, 	ask7) to evaluate complexity, UI usage, and consolidated issue detection.
  5. Stores results into MySQL tables and JSON report files.
  6. The Flask dashboard (
eport_server.py) reads the aggregated JSON data and DB to present a visual health score and defect dashboard.
* **Key design patterns used:** 
  * **Pipeline/ETL Pattern:** For chaining parsing, linting, and reporting stages.
  * **Strategy/Plugin Pattern:** Task-based isolation (	ask3 through 	ask7) handling distinct audit categories independently.
  * **MVC Layout:** Used within the Flask reporting server (Templates for Views, python logic for Controllers/Models).

## 4. Project Structure
* /audit_tool
  * run_audit.py → Top-level entry point orchestrator for the audit pipeline.
  * /config → Contains project_config.yaml with rules, target paths, and regex patterns.
  * /report → Flask-based web dashboard (report_server.py), storing static/ styling and templates/ for the UI.
  * /task2_audit → Base parsers and file extractors (Vue parser, API extractor, script cleaner).
    * extractors/api_extractor.py → Extracts API calls. Also contains count_payload_keys(), calculate_payload_depth(), and calculate_payload_size_kb() payload metric functions.
    * extractors/script_cleaner.py → Cleans script for complexity analysis while preserving payload object structures for accurate metric extraction.
  * /task3 → Evaluates component complexities, line metrics, and file flags. Exports component_complexity.json after each scan.
  * /task4 → UI component extraction logic.
  * /task5 → UI consistency checker (CSS styling rules, spell checking).
  * /task6 → Accessibility (a11y) defect checker. **[DISABLED]** Now handled by ESLint integration (eslint-plugin-vuejs-accessibility) which writes to accessibility_defects table.
  * /task7 → Consolidated issue detector aggregating findings across tasks into a comprehensive JSON report.
* /code_analyzer_db → Database seeding, verification, and loading tools.
* scan.log → Created at runtime in the project root. Captures INFO-level pipeline progress and WARNING-level parse validation errors per file.

## 5. Implemented Features
* **Vue Code Parsing:** AST-based code breakdown for .vue files.
* **API Extraction:** Detection and cataloging of generic REST, Axios, and internal MQL API calls, including chain counting and request-chain detection.
* **Complexity Scoring:** Calculation of code complexity and measurement of large components/scripts. Includes AST-first methods counting with regex brace-matching fallback.
* **Payload Metrics:** Calculation and persistence of payload_keys, payload_depth, and payload_size_kb per file to the database.
* **UI Consistency Check:** Identification of unstructured CSS usage and spelling defects within template structures.
* **Accessibility Auditing:** Highlights semantic HTML errors, missing alt tags, and a11y non-compliance.
* **Database Persistency:** Automatic synchronization of flags and file structures to a MySQL schema using CREATE TABLE IF NOT EXISTS and INSERT ... ON DUPLICATE KEY UPDATE (no data loss on re-runs).
* **Parse Validation Logging:** Files with unexpectedly empty parse results are logged as WARNING entries in scan.log.
* **Task 3 MySQL Sync:** Component complexity data is exported from the database to component_complexity.json after each scan.
* **Dashboard Report:** A local Flask web server offering visual health scoring, defect categorization, and file-level drill-downs.

## 6. Core Modules / Important Files
* **udit_tool/run_audit.py:** The primary executable that drives the extraction and analysis phases, writes to MySQL, and coordinates output files.
* **udit_tool/report/report_server.py:** The Flask application that serves the audit results via localhost:5000.
* **Audit_tool/task2_audit/extractors/eslint_extractor.py:** Runs ESLint via subprocess, parses JSON output, and routes Vue best practices to file_flags and accessibility issues to accessibility_defects.
* **Audit_tool/task2_audit/extractors/vue_parser.py:** Leverages Tree-sitter to deconstruct Vue components into discrete template, script, and style blocks.
* **udit_tool/task7/issue_detector.py:** The final step of the pipeline that aggregates warnings, flags, and metrics into a unified issue_report.json.
* **udit_tool/config/project_config.yaml:** The source of truth for the audit script (target paths, regex definitions, confidence matrices).
* **code_analyzer_db/db_loader.py:** Utilities to connect and seed tables securely to MySQL using .env inputs.

## 7. API Design
* **Endpoints:** No external REST APIs exposed. 
* **Request/response structure:** The internal Flask dashboard serves server-rendered HTML blocks via 
ender_template locally (/ route).
* **Authentication method:** None. Running locally for developer machine usage.

## 8. Database Schema
* **Tables:**
  * vue_files: Stores metadata, line counts, and paths of parsed codebase components. Columns include: script_lines, template_lines, methods, computed, watchers, api_total, api_mounted, child_components, max_nesting_depth, payload_keys, payload_depth, payload_size_kb, flag_count, confidence, scanned_at.
  * api_calls: Tracks API type, method name, full match string, in_mounted flag, in_loop flag (for loop-context detection), and line_number per call.
  * file_flags: Records defect categories and flag names associated with scanned files.
  * ui_extractions, ui_defects, accessibility_defects: Store Task 4, 5, and 6 findings respectively.
* **Relationships:** api_calls, file_flags, ui_extractions, ui_defects, and accessibility_defects are all foreign-keyed to vue_files(id) with ON DELETE CASCADE.
* **Persistence strategy:** Tables use CREATE TABLE IF NOT EXISTS. Rows are upserted via INSERT ... ON DUPLICATE KEY UPDATE keyed on the unique file_path column, so re-running the audit updates existing rows without duplicating them.

## 9. Current Status

### PHASE 1 COMPLETION (Complete and Verified)
* **Step 1 — DB Persistence:** Replaced DROP TABLE with CREATE TABLE IF NOT EXISTS. Upsert logic prevents duplicate rows on re-runs.
* **Step 2 — Payload Metrics Persistence:** Implemented count_payload_keys(), calculate_payload_depth(), calculate_payload_size_kb() in api_extractor.py. Added payload_keys, payload_depth, payload_size_kb columns to vue_files schema and INSERT/UPDATE logic in db_writer.py.
* **Step 3 — Parse Validation Logging:** Files with >30 raw lines that parse as empty are logged as WARNING in scan.log.
* **Step 4 — Task 3 MySQL Sync:** task3_exporter.py reads from the DB export and generates component_complexity.json after each scan.

### POST-PHASE 1 IMPROVEMENTS (Implemented and Verified)
* API chain counting logic
* Request-chain detection (axios, MQL)
* MQL constructor chains
* Mounted attribution (excluding promise callbacks)
* Methods counting (AST-first)
* Regex fallback for methods (brace matching)
* Child component counting (template + script)
* PrimeVue table exclusions
* Registered components extraction
* Template line counting logic

### PARTIALLY DONE
* DB loader verification scripts are modular but strictly dependent on the MySQL connection being manually provisioned.

### KNOWN BUGS / LIMITATIONS
* Requires explicit configuration of tree-sitter binaries which might need recompilation on varying OS architectures. File pathing relies on static local directories defined in YAML.
* **[Note] script_lines undercounts raw file lines:** The script cleaner strips comments and blank lines before counting, so script_lines reflects cleaned line count, not raw physical line count.
* **[Note] api_total undercounts loop-repeated calls:** The API extractor counts unique call patterns. APIs called inside loops (e.g., forEach with new MQL()) are counted as one pattern, not per iteration. The API_IN_LOOP flag captures this case separately.
* **[Note] child_components misses lazy-loaded components:** Components registered via arrow-function import() syntax or mixins are not counted, resulting in undercounts.

### PHASE 2 PROGRESS (In Progress)

#### Completed:
* **Step 5 — Handle Vue SFC edge cases:**
  - `<script setup>` detection & method counting
  - Template-only component detection (no false parse warnings)
  - TypeScript syntax stripping before JS counters
  - 3 new schema columns: `script_setup`, `template_only`, `typescript_detected` (Added dynamically in task schema handling)
  - Verified on 114-file codebase

* **Step 6 — Add line numbers to findings:**
  - Line number calculation for API calls (relative to whole file)
  - Line number calculation for pattern-based flags
  - Structural flags use line_number = 0
  - Includes line numbers in JSON exports
  - Note: Precision acceptable, not 100% exact for all edge cases

### READY FOR NEXT STEPS (Phase 2)
* Step 7 — Add code snippets to flags (1-3 line evidence)
* Step 8 — Expand API detection (service classes, composables, Vuex)

### PHASE 3 (Completed via Pivot)
* **Standalone ESLint Engine:** Implemented a standalone ESLint integration using Python's subprocess module to run `eslint-plugin-vue` and `eslint-plugin-vuejs-accessibility` locally within the audit_tool directory.
* **Dropped Custom AST Traversal:** Replaced the custom Tree-sitter based Vue anti-pattern and accessibility checks with ESLint JSON output parsing. ESLint findings are directly parsed and routed to the `file_flags` and `accessibility_defects` MySQL tables.
* **Noise Reduction:** Disabled all stylistic/formatting rules (semi, quotes, indent, etc.) in `.eslintrc.js` to prioritize security and structural defects. Only Vue best practices and accessibility rules remain as errors.
* **Legacy Task 6 Disabled:** The original Tree-sitter based accessibility_checker (Task 6) has been commented out in favor of ESLint-driven accessibility findings.
* **Results:** ESLint scan now produces ~142 meaningful Vue best-practice flags and ~519 accessibility defects, down from 8,000+ noisy stylistic warnings.

## 10. Development Workflow
* **How to run the project:** 
  1. Set target paths in udit_tool/config/project_config.yaml.
  2. Define environment variables in an .env file within udit_tool/ for database connection (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, etc.).
  3. Execute python audit_tool/run_audit.py to trigger the audit and populate the database.
  4. Execute python audit_tool/report/report_server.py to launch the Flask UI viewer.
* **Build steps:** Normal Python runtime. No compiled build-steps except installing dependencies (pip install -r requirements.txt).
* **Environment variables:**
  * MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

## 11. Coding Conventions
* **Naming conventions:** Snake-case for Python files/functions (
un_audit.py, generate_all_suggestions()), PascalCase for Vue components (in parsed targets).
* **Patterns followed:** Procedural and functional ETL pipelines separated by distinct "task" folders representing the stages of semantic transformation.

## 12. Performance Optimizations

### Incremental Auditing with Two-Step Filter
The pipeline implements a sophisticated two-step filtering system to eliminate redundant processing:

**Step 1: mtime OS Pre-filter (Gate 1)**
- Uses `os.path.getmtime()` to compare local file modification time against database `scanned_at` timestamp
- If local file is older than last scan: **instant skip** (no disk I/O, no hash calculation)
- Eliminates ~99.5% of disk I/O for unchanged files

**Step 2: SHA-256 Content Hash (Gate 2)**
- Only runs when mtime check fails (file is newer or timestamp unavailable)
- Calculates SHA-256 hash and compares against stored hash in memory
- Provides content-level accuracy for change detection

**In-Memory Hash Map**
- Single SQL query: `SELECT file_path, file_hash, scanned_at FROM vue_files`
- Python dictionary for O(1) lookup time
- Eliminates 113+ individual database round trips per scan

**Task-Level Gating**
- Tasks 4 (UI Extraction) and 5 (UI Consistency) only process "dirty files"
- Task 7 generates full project report by querying MySQL (single source of truth)
- Maintains sequential execution as required

**Performance Impact**
- **No files changed**: ~5 minutes → **0.1 seconds** (99.5% faster)
- **1 file changed**: ~5 minutes → **0.1 seconds** (99.5% faster)
- **Disk I/O reduction**: 114 hash calculations → **0** for unchanged files

## 13. Dependencies
* Flask: Web server framework for the dashboard.
* mysql-connector-python: To handle CRUD boundaries with MySQL.
* Tree-sitter & Tree-sitter-embedded-template: Crucial for resilient Semantic AST parsing of Vue and JavaScript structures without regex fragility.
* ESLint: Integrated via subprocess to audit Vue best practices and accessibility.
* eslint-plugin-vue: ESLint plugin for Vue.js-specific rules.
* eslint-plugin-vuejs-accessibility: ESLint plugin for accessibility rules in Vue.js templates.
* PyYAML: To manage rule configurations effortlessly.
* python-dotenv: Streamlined local DB credential sourcing.
