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
* **Dev tools:** Virtual environment (env), dotenv (Environment variable management)

## 3. Architecture
* **Overall architecture:** A monolithic ETL (Extract, Transform, Load) pipeline coupled with a monolithic web dashboard.
* **Data flow:** 
  1. The orchestrator (
un_audit.py) reads configuration from project_config.yaml.
  2. Parses target .vue and .js files using the 	ask2_audit extractors.
  3. Hands data to modular sub-tasks (	ask3 through 	ask7) to evaluate complexity, UI usage, and accessibility.
  4. Stores results into MySQL tables and JSON report files.
  5. The Flask dashboard (
eport_server.py) reads the aggregated JSON data and DB to present a visual health score and defect dashboard.
* **Key design patterns used:** 
  * **Pipeline/ETL Pattern:** For chaining parsing, linting, and reporting stages.
  * **Strategy/Plugin Pattern:** Task-based isolation (	ask3 through 	ask7) handling distinct audit categories independently.
  * **MVC Layout:** Used within the Flask reporting server (Templates for Views, python logic for Controllers/Models).

## 4. Project Structure
* /audit_tool
  * 
un_audit.py → Top-level entry point orchestrator for the audit pipeline.
  * /config → Contains project_config.yaml with rules, target paths, and regex patterns.
  * /report → Flask-based web dashboard (
eport_server.py), storing static/ styling and 	emplates/ for the UI.
  * /task2_audit → Base parsers and file extractors (Vue parser, API extractor, script cleaner).
  * /task3 → Evaluates component complexities, line metrics, and file flags.
  * /task4 → UI component extraction logic.
  * /task5 → UI consistency checker (CSS styling rules, spell checking).
  * /task6 → Accessibility (a11y) defect checker.
  * /task7 → Consolidated issue detector aggregating findings across tasks into a comprehensive JSON report.
* /code_analyzer_db → Database seeding, verification, and loading tools.

## 5. Implemented Features
* **Vue Code Parsing:** AST-based code breakdown for .vue files.
* **API Extraction:** Detection and cataloging of generic REST, Axios, and internal API calls.
* **Complexity Scoring:** Calculation of code complexity and measurement of large components/scripts.
* **UI Consistency Check:** Identification of unstructured CSS usage and spelling defects within template structures.
* **Accessibility Auditing:** Highlights semantic HTML errors, missing lt tags, and a11y non-compliance.
* **Database Persistency:** Automatic synchronization of flags and file structures to a MySQL schema.
* **Dashboard Report:** A local Flask web server offering visual health scoring, defect categorization, and file-level drill-downs.

## 6. Core Modules / Important Files
* **udit_tool/run_audit.py:** The primary executable that drives the extraction and analysis phases, writes to MySQL, and coordinates output files.
* **udit_tool/report/report_server.py:** The Flask application that serves the audit results via localhost:5000.
* **udit_tool/task2_audit/extractors/vue_parser.py:** Leverages 	ree-sitter to deconstruct Vue components into discrete template, script, and style blocks.
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
  * ue_files: Stores metadata, line counts, and paths of parsed codebase components.
  * pi_calls: Tracks endpoint URLs, methods, and the originating component paths to trace network connections.
  * ile_flags: Records defect categories, complexities, and specific issue details associated with scanned files.
* **Relationships:** pi_calls and ile_flags are tied transactionally/relationally to their host components in ue_files.

## 9. Current Status
* **What is completed:** Full end-to-end AST parsing, database insertion, and local defect evaluation (Tasks 2->7). The Flask reporting dashboard accurately displays aggregated UI metrics and a11y health scores.
* **What is partially done:** DB loader verification scripts are modular but strictly dependent on the MySQL connection being manually provisioned.
* **Known bugs or limitations:** Requires explicit configuration of tree-sitter binaries which might need recompilation on varying OS architectures. The file pathing relies heavily on static local directories defined in YAML.

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

## 12. Dependencies
* lask: Web server framework for the dashboard.
* mysql-connector-python: To handle CRUD boundaries with MySQL.
* 	ree-sitter & 	ree-sitter-embedded-template: Crucial for resilient Semantic AST parsing of Vue and JavaScript structures without regex fragility.
* PyYAML: To manage rule configurations effortlessly.
* python-dotenv: Streamlined local DB credential sourcing.
