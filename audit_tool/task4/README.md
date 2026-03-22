# Task 4 UI Extractor

This module contains `task4_ui_extractor.py`, which is responsible for statically analyzing the `<template>` blocks of all Vue components in `src/components` and `src/views`. 

## Output
The script generates `ui_extraction.json`, which contains a catalog of:
1. Buttons
2. Headers (H1-H6, PageHeader, BaseHeader)
3. Visible UI Text

Each item has an explicit `type` identifying if it relies on static text, Vue i18n (`{{ $t('...') }}`), or a mix of both.

## How to run
```bash
python task4/task4_ui_extractor.py
```

## Extraction Assumptions
- Evaluates tree-sitter AST nodes directly to extract visible UI elements dynamically.
- `{{ ... }}` interpolated strings are preserved natively with a "type" string.
- Buttons without text or interpolations (only containing icons like `<i>` or `<svg>`) are ignored.
- Text strings <= 2 characters, strictly numeric strings, or empty whitespaces are filtered out to reduce noise.
