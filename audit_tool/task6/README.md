# Task 6: UI Accessibility & Usability Compliance Checker

This module automates code-level static checks from the UI Accessibility & Usability compliance rules (Task 6 roadmap). Because static analysis (AST parsing) doesn't run code in a real browser, some rules are fully automated while others intrinsically require manual validation.

## ✅ In-Scope (Automated by Static Analysis)
The `accessibility_checker.py` leverages `tree-sitter-vue` to deeply parse BOTH the HTML templates and CSS styles to find code defects:
1. **FOCUS_OUTLINE_REMOVED (Critical)**: Parses `<style>` ASTs (via `tree-sitter-css`) to identify `outline: none` or `outline: 0`.
2. **MISSING_ALT_TEXT (High)**: Identifies `<img>` tags missing `alt` or `:alt` attributes.
3. **UNLABELED_INPUT (High)**: Identifies form inputs that lack a wrapping `<label>` or a matching `<label for="...">` ID pointer.
4. **MISSING_ARIA_LABEL (High)**: Identifies `<button>` tags mapping purely to icons (e.g., `<svg>`, `<v-icon>`, `<i>`) with no text content and no `aria-label`.
5. **PLACEHOLDER_USED_AS_LABEL (Medium)**: Identifies `<input>` elements using placeholders in place of proper accessible labels.
6. **DYNAMIC_CONTENT_NO_ARIA_LIVE (Medium)**: Identifies dynamically conditional elements (`v-if`, `v-show`) without `aria-live` on themselves or parent wrappers.
7. **REQUIRED_FIELD_NOT_MARKED (Medium)**: Identifies inputs marked as `required` but missing `aria-required="true"`.
8. **NON_INTERACTIVE_WITH_CLICK (High)**: Flags traditional non-interactive elements (`<div>`, `<span>`, `<p>`) using `@click` events but missing `role="button"` or `tabindex="0"`.
9. **EMPTY_LINK (Medium)**: Highlights `<a>` tags mimicking buttons by lacking `href`/destinations & textual components (`aria-label`).

## ❌ Out-of-Scope (Requires Manual QA / Browser Testing)
The following tests are inherently impossible to test reliably with 100% confidence using static code scans:
1. **Contrast Ratios (3.5 Form Accessibility)**: The visual color contrast relies on runtime cascade overrides and parent containers. Must be checked by rendering the page (e.g., Axe / Lighthouse).
2. **"Error messages must appear near the field" (3.5)**: Layout positioning relies on the CSS box model parsing at runtime.
3. **Zoom & Responsive Behaviors (3.6)**: 100%, 150%, and 200% screen resolution and scaling testing can only be done dynamically.
4. **44x44 pixels Touch Target Size (3.7)**: Final dimensional layouts evaluate at browser rendering time based on percentages, `ems`, viewports, etc.
5. **Screen Reader Pronunciation/Announcements (3.4)**: Static analysis tells us `aria-label` *exists*, but it takes real QA tests to verify the content text *makes logical sense* when natively read aloud.
