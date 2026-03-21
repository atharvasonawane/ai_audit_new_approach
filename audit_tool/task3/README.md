# Task 3: Vue Component Complexity Scanner

This directory contains the script for Task 3, which generates a report measuring how complex each Vue component is internally.

## 🚀 How to Run

Since Task 2 already securely parsed all files using a highly accurate `tree-sitter` AST pipeline, we reuse its data rather than running an inferior regex parse.

Ensure you have run the main master script from the root first (`run_audit.py` from Task 2) so that `task2_db_export.json` exists.

Run the exporter from the root of the project:
```bash
python task3/task3_exporter.py
```

This will automatically read the data, calculate accurate lines of code, evaluate the metrics against the Task 3 flag thresholds, and generate `component_complexity.json` inside this folder.

## 🧠 Assumptions Made

1. **Reusing Robust Data Extraction:** Instead of re-parsing everything with basic regex (which often fails on complex nested blocks and custom MQL syntax), we reused the accurate metrics (methods count, computed, watchers, component counts) already extracted by the AST parser in Task 2. This fulfills the requirement of "Simple non-complex extraction" by leveraging the data we *already have*.
2. **True Lines of Code:** The JSON structure asks for total lines. The script re-opens each `.vue` file to count exactly how many lines are in it so that the new `VERY_LARGE_COMPONENT` (> 800) flag is perfectly accurate.
3. **Task 3 Isolation:** We isolated the flags strictly to the ones requested in Task 3 (LOC, Methods, Computed, Watchers, Template loops, Child components), ignoring the API flags present in Task 2.
