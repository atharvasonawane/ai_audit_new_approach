# **Vue AI Audit Pipeline: Master Architecture & Implementation Plan**

**Purpose:** This document serves as the absolute single source of truth for the modernized Vue Static Analysis Pipeline. It dictates the architectural philosophy, the exact toolchain, the data flow, and the phased implementation roadmap. Any AI agent or developer working on this codebase must adhere strictly to these guidelines.

## **1\. Core Architectural Philosophy**

1. **Python is the Commander, Node.js is the Engine:** The orchestrator (run\_audit.py) remains in Python. It executes deterministic open-source Node.js parsers via the subprocess module, captures their JSON stdout, and processes the data natively in Python.  
2. **Zero Regex for Structural Parsing:** Regular expressions are strictly forbidden for parsing context-free grammars (Vue SFCs, deeply nested HTML/JS).  
3. **AST is Mandatory:** All core code analysis relies on Abstract Syntax Tree (AST) tools (ESLint, stylelint, ast-grep). Custom manual AST traversal (like the legacy tree-sitter heuristic scripts) is deprecated in favor of mature, maintained linters.  
4. **Unified Data Schema:** Fragmented JSON outputs (task3.json, task4.json, etc.) are obsolete. All tool outputs are aggressively normalized into a single **SARIF v2.1.0** (Static Analysis Results Interchange Format) schema using **Pydantic** before touching the database.  
5. **AI is for Adjudication, Not Detection:** LLMs are never used for primary scanning to prevent hallucinations and latency. They are reserved exclusively for post-processing (e.g., explaining complex SARIF alerts).

---

## **2\. The Deterministic Toolchain**

| Domain | Tool | Execution Strategy via Python Orchestrator |
| :---- | :---- | :---- |
| **Parsing Base** | vue-eslint-parser | Configured inside ESLint to natively separate \<template\>, \<script\>, and \<style\>. Deprecates legacy vue\_parser.py. |
| **Syntax/Quality** | eslint \+ eslint-plugin-vue | subprocess.run(\["npx", "eslint", ".", "--format", "json"\]). Replaces manual script checks. |
| **Complexity** | vue-mess-detector | subprocess.run(\["npx", "vue-mess-detector", "analyze", ".", "--format", "json"\]). Calculates cyclomatic complexity and Vue smells. Deprecates legacy component\_complexity.py. |
| **Accessibility** | eslint-plugin-vuejs-accessibility | Runs within the ESLint pass. Checks WCAG compliance on the template AST. Deprecates legacy accessibility\_checker.py. |
| **CSS Quality** | stylelint | subprocess.run(\["npx", "stylelint", "\*\*/\*.{vue,css}", "--formatter", "json"\]). Enforces UI/CSS consistency. |
| **Orthography** | cspell | subprocess.run(\["npx", "cspell", "\*\*/\*.{vue,js}", "--reporter", "json"\]). Replaces legacy spell-checking logic. |
| **Architecture** | dependency-cruiser | subprocess.run(\["npx", "depcruise", ".", "--output-type", "json"\]). Maps import graphs and circular dependencies. |
| **API/Structure Search** | ast-grep (via ast-grep-py) | Python-native bindings used to perform structural search (e.g., axios.get($$$)) to populate code\_analyzer.apis. |
| **Duplication** | jscpd | subprocess.run(\["npx", "jscpd", ".", "--reporters", "json"\]). Detects copy/pasted logic. |

---

## **3\. Pipeline Execution Flow (V4 Architecture)**

The pipeline executes strictly in this order:

Plaintext  
\[ project\_config.yaml \] \-\> Supplies \`base\_path\` and target configs.  
       |  
\[ run\_audit.py \] (The Orchestrator)  
       |  
       v  
  Phase 1: Parallel Node.js Execution (Subprocess Pool)  
   ├── Thread A: ESLint (Vue, JS, A11y plugins)  
   ├── Thread B: Stylelint (CSS validation)  
   ├── Thread C: Vue-Mess-Detector (Complexity)  
   ├── Thread D: CSpell (Orthography)  
   ├── Thread E: Dependency-Cruiser (Architecture graph)  
   ├── Thread F: ast-grep-py (API/Node extraction natively in Python)  
       |  
       v  
  Phase 2: Data Normalization (Pydantic Adapter Layer)  
   ├── Python captures raw JSON from \`stdout\` of all threads.  
   ├── Raw JSON is passed into Pydantic SARIF models (\`schema\_models.py\`).  
   ├── \`path\_utils.py\` ensures all filepaths are relative to \`base\_path\`.  
       |  
       v  
  Phase 3: Scoring & Penalties  
   ├── Python script calculates aggregate "Health Score" (0-100).  
   ├── Applies severity weights (Critical=5, Major=3, Minor=1).  
       |  
       v  
  Phase 4: Database Ingestion  
   └── \[ db\_loader.py \] \-\> Syncs the unified SARIF JSON seamlessly into MySQL (\`code\_audit\_db\`).

---

## **4\. The Pydantic SARIF Schema (schema\_models.py)**

All outputs MUST be coerced into this shape before database ingestion:

* **tool\_name**: The analyzer that found it (e.g., "eslint", "cspell").  
* **rule\_id**: The specific rule (e.g., "vue/no-mutating-props").  
* **severity**: Normalized to error, warning, or info.  
* **category**: Mapped to accessibility, complexity, style, architecture, security, spelling.  
* **file\_path**: Must pass through path\_utils.normalize\_path().  
* **line / column**: Exact location integer coordinates.  
* **message**: Human-readable description.  
* **snippet** *(Optional)*: 1-2 lines of surrounding code.

---

## **5\. Agentic IDE Implementation Roadmap**

When feeding this into an Agentic IDE (like Cursor, GitHub Copilot Chat, or Devin), follow these exact steps sequentially:

### **Phase 1: Setup & Schema Standardization**

1. **Create schema\_models.py:** Define the Pydantic BaseModel classes for the unified SARIF schema.  
2. **Refactor db\_loader.py:** Update the MySQL ingestion logic to accept the new SARIF models rather than the old fragmented taskX formats. Map SARIF category and severity to the existing rule\_violations and metrics tables.

### **Phase 2: Orchestrator Modernization**

3. **Setup Node.js Environment:** Generate a package.json at the root and install the required NPM packages (eslint, vue-eslint-parser, stylelint, cspell, etc.) and create their respective config files (.eslintrc.js, .stylelintrc.json, etc.).  
4. **Rewrite run\_audit.py:** Strip out the manual calls to the legacy taskX Python scripts. Implement an asyncio or concurrent.futures pool to execute the Node.js CLI tools via subprocess and capture their JSON output.

### **Phase 3: Adapters & Replacements**

5. **Write Adapter Functions:** For each tool (ESLint, CSpell, etc.), write a small Python mapping function that converts its specific JSON output shape into the Pydantic SARIF model.  
6. **Implement API Extraction (ast\_extractor.py):** Install ast-grep-py. Write a Python script to structurally hunt for API calls (replacing the "unwritten" API mappings).

### **Phase 4: Cleanup**

7. **Deprecate Legacy Code:** Safely delete vue\_parser.py, component\_complexity.py, ui\_consistency.py, and accessibility\_checker.py.  
8. **Final Testing:** Run the pipeline against a test Vue repository, verify no node\_modules are scanned, ensure path\_utils operates correctly, and confirm the MySQL database populates perfectly.

---

### **Pro-Tip for your New Chat / Agentic IDE**

When you open your new chat with your Agentic IDE, simply upload this MASTER\_ARCHITECTURE.md file and say:

*"Read the attached MASTER\_ARCHITECTURE.md file carefully. It contains the exact roadmap, toolchain, and constraints for refactoring our Vue.js Python Audit Pipeline. Start by executing Phase 1, Step 1: Create the schema\_models.py Pydantic models."*

