# Project Knowledge Base: Code Audit Librarian Pipeline

> **Notice for AI Assistants:** This document contains the absolute source of truth regarding the architecture, methodologies, current status, and tooling for the project. Use this context to correctly understand the codebase. 

## 1. Core Purpose
This project is a highly robust, fully generalized, and project-agnostic **Static Code Analysis and Defect Extraction engine**. It primarily targets frontend JavaScript frameworks (specifically Vue.js). It programmatically scans targeted codebases to count complexities, flag code smells, extract dynamic UI elements, and catch accessibility/spelling failures, persisting the findings to a relational database for a local metrics dashboard.

## 2. Tools Used
- **Python (Core Engine)**: Drives the execution loop, parsing logic, file I/O operations, and database ingestion.
- **Tree-Sitter (`tree-sitter-javascript`, `tree-sitter-html`)**: Deep AST (Abstract Syntax Tree) parsing engine. Used to intelligently divide single-file components (.vue) into template strings, script setups, and style blocks for deeper analysis.
- **MySQL Database**: Target relationship store serving as the single source of truth for the reporting dashboard (`code_analyzer` and `code_audit_db`). Stores mappings for normalized codebase paths, rules, metrics, and ui components.
- **Local LLMs (Ollama)**: Enables AI-powered code fix suggestions on the dashboard, completely isolating codebase context without leaking data to external proprietary API endpoints.

*(Note: Legacy chatbot components using Gradio exist in the repository but have been deprecated in favor of a local reporting dashboard/VS Code Extension setup. They are NOT actively used).*

## 3. Techniques and Approaches
- **Project-Agnostic File Processing**: Powered by `project_config.yaml`, the system requires only a `base_path` variable and dynamically traverses thousands of target codebase files while automatically ignoring compiled/vendor directories like `node_modules`, `dist`, and `.git`.
- **Dynamic Path Normalization**: Intercepts absolute paths and refactors them dynamically relative to the `base_path` (e.g., `views/App.vue`), keeping data in the database pristine and detached from local host machines.
- **Graceful AST Parsing (Vue 2 / Vue 3 fallback)**: Logic dynamically parses both Vue 2 Options API (methods, computed properties) and Vue 3 Composition API (`<script setup>`). If AST traversal defaults, it falls back to functional string-scanning smoothly and never halts execution on bad nodes.
- **Unified Issue Distillation & Thresholding**: Applies industry-standard heuristics (e.g., triggering `MANY_METHODS` if methods > 10, or `LARGE_TEMPLATE` if HTML LOC > 100). All violations (Code, Spelling, WCAG Accessibility, Semantics) are flattened and unified into a `rule_violations` database schema.

## 4. Extracted Data Focus
The core objective of the statically applied AST logic is to accurately extract qualitative metrics across the entire codebase. The specific tools and data points isolated include:
- **Component Complexity Metrics (Task 3)**: Extracts line-of-code (LOC) weights for scripts and templates. Counts occurrences of methods, `computed` properties, `watchers`, props, and evaluates the levels of HTML template nesting limit. *(Powered by `tree-sitter-javascript` and `tree-sitter-html` AST parsing)*.
- **Targeted UI Contextual Elements (Task 4)**: Extracts text content for structural UI elements including `headers` (e.g., h1-h6), `buttons`, and general `visibleTexts`. Critically tracks dynamic/evaluated template strings (e.g., `{{ variable }}`) linking them seamlessly to source files for localization tracking. *(Powered by `tree-sitter-html` node extraction)*.
- **Defect and Spelling Analytics (Task 5)**: Detects and scrapes typographical mistakes or spelling defects occurring inside visible text portions evaluated against defined dictionaries. *(Powered by the `pyspellchecker` Python library)*.
- **Accessibility and Compliance Tracking (Task 6)**: Identifies missing structural compliances such as absent W3C ARIA attributes, missing `alt` properties on images, and tracks missing best-practice tags for interactive nodes. *(Logic evaluated natively via AST tag property mapping)*.
- **Architectural Heuristics (Task 7)**: Compiles thresholds against extracted metrics, triggering distinct warning flags like `MANY_METHODS` (methods > 10), `OVERSIZED_COMPONENT` (script LOC > 300), `LARGE_TEMPLATE` (template LOC > 100), and `DEEP_NESTED_TEMPLATE` (HTML nesting > 4). *(Handled by custom Python threshold evaluation operators)*.

## 5. Project Structure
- **`audit_tool/`**: The core data generation pipeline.
  - `run_audit.py`: The master execution orchestrator. Kicks off parsing loops, delegates schema builds, and runs the entire task suite sequentially.
  - `project_config.yaml`: Contains configuration targets (like `base_path`).
  - `task2_audit/`: Extracts absolute code blocks, generates tree-sitter chunking, normalizes local paths.
  - `task3/`: Astigmatic measurements. Evaluates Javascript code complexity and counts logical component branches/methods.
  - `task4/`: UI Node Database. Scrapes textual templates forming structured JSON for all visible headers, interactive buttons, and visible text contexts maps to translation endpoints.
  - `task5/`: Cross-references spelling defects and internal consistency violations.
  - `task6/`: Evaluates UI Accessibility tracking missing ARIA tags and failed Web Content Accessibility Guidelines.
  - `task7/`: Flag tracking engine. Handles the logic for rule validation, identifying structural violations against project-level limits.
- **`code_analyzer_db/`**: The database ingestion layer.
  - `db_loader.py`: Reads the JSON payloads exported by Tasks 3 through 7. Normalizes and indexes everything robustly into MySQL representing relationships like `ui_nodes`, `files`, and `metrics`.

## 6. Workflow Execution
1. Update `project_config.yaml` to configure the target `base_path` pointing to the target Vue.js application.
2. Execute `run_audit.py` to trigger the sequential task pipeline per `.vue`/`.js` file within the configured directory.
3. System statically dissects AST branches and assesses the core components sequentially from Task 3 through Task 7.
4. Extracted components, codebase issues, accessibility metrics, and UI configurations are temporarily held in JSON chunks within isolated task directories.
5. Ingestion Engine (`db_loader.py` within `code_analyzer_db/`) automatically sweeps the JSON payloads and synchronizes the fully linked metrics into target MySQL tables.
6. Local reporting dashboards interface directly with MySQL queries to display insights and ping Ollama-LLMs.

## 7. Current Status
- The core AI Code Audit Librarian successfully runs as a hardened, dynamic static analysis pipeline scaling to full monolithic codebases.
- Local mapping successfully captures structural logic (Component Metadata), visible text rendering (UI Strings), structural health (Missing Accessibility elements), and explicit rule logic (Spelling/Nesting metrics).
- The team has successfully pivoted to ensuring the system operates reliably as a pipeline driving an industry-grade localhost dashboard/VS Code extension metric system rather than legacy chat interfaces. 
- The MySQL Database loaders actively work with 100% traversal metrics. API payload connections in AST scraping remain scoped for future development, while current implementations focus entirely on structural UI tracking and LLM report mapping representations via a native web-engine.
