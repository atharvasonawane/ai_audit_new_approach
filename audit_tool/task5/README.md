# Task 5: UI Consistency and Spell Checker

This module analyzes the output of Task 4 to find UI inconsistencies and spelling errors across the project.

## In Scope
* Spelling errors in visible, static text and buttons (interpolations skipped)
* Button capitalization consistency (compared to project-wide dominant casing)
* Button CSS class consistency (compared to project-wide dominant CSS class usage)

## Out of Scope
* **Rule 3.4 (Alignment)** and **Rule 3.5 (Font/Color consistency)** cannot be reliably verified from static AST template data alone, as they depend on the final rendered DOM and cascading styling. These are explicitly **out of scope** for this static analysis phase.
