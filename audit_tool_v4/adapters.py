"""
adapters.py
===========
Phase 3, Step 5 of MASTER_ARCHITECTURE.md.

One mapping function per tool. Each function:
  - Accepts raw JSON (list or dict) captured from the tool's stdout/file
  - Returns a list[SARIFResult] — the unified Pydantic data contract
  - Handles every missing or malformed field gracefully (never raises)

Entry-point: adapt_all(tool_results, base_path, project) -> SARIFReport
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit_tool"))
from schema_models import (
    Category,
    SARIFReport,
    SARIFResult,
    Severity,
    ESLINT_SEVERITY_MAP,
    STYLELINT_SEVERITY_MAP,
    CSPELL_SEVERITY_DEFAULT,
    infer_category,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rel(raw_path: str, base_path: str) -> str:
    """
    Convert an absolute path to a path relative to base_path.

    Handles:
      - Forward and back slashes
      - file:// URI scheme (CSpell uses these)
      - Paths that are already relative (returned unchanged)
      - Windows drive letters

    Returns an empty string on total failure (caller must skip the record).
    """
    if not raw_path:
        return ""

    # Unwrap file:// URIs
    if raw_path.startswith("file://"):
        try:
            raw_path = urlparse(raw_path).path.lstrip("/")
            # On Windows urlparse gives /C:/... — strip leading slash
            if re.match(r"^[A-Za-z]:/", raw_path[1:]):
                raw_path = raw_path[1:]
        except Exception:
            pass

    # Normalise slashes
    raw_path  = raw_path.replace("\\", "/")
    base_norm = base_path.replace("\\", "/").rstrip("/") + "/"

    if raw_path.lower().startswith(base_norm.lower()):
        return raw_path[len(base_norm):]

    # Fallback: strip Windows drive reference
    if re.match(r"^[A-Za-z]:/", raw_path):
        raw_path = "/".join(raw_path.split("/")[1:])  # drop drive letter segment

    return raw_path.lstrip("/") or raw_path


def _safe_int(val: Any, default: int = 1) -> int:
    """Coerce val to int, clamped to >= default."""
    try:
        return max(default, int(val))
    except (TypeError, ValueError):
        return default


def _safe_str(val: Any, default: str = "") -> str:
    """Coerce val to stripped str."""
    if val is None:
        return default
    return str(val).strip() or default


# ─────────────────────────────────────────────────────────────────────────────
# Adapter 1: ESLint
# ─────────────────────────────────────────────────────────────────────────────

def adapt_eslint(raw_json: list[dict], base_path: str) -> list[SARIFResult]:
    """
    Map ESLint JSON output → list[SARIFResult].

    ESLint JSON shape:
    [
      {
        "filePath": "/abs/path/to/file.vue",
        "messages": [
          {
            "ruleId":   "vue/no-mutating-props",  # may be null for parse errors
            "severity": 2,                         # 0=off, 1=warn, 2=error
            "message":  "Unexpected mutation...",
            "line":     10,
            "column":   5,
            "source":   null                       # deprecated; snippet unavailable here
          }
        ]
      }
    ]

    Notes:
      - ruleId can be null (parse/config errors) — mapped to "eslint:parse-error"
      - severity 0 is silenced (filtered out)
      - Accessibility rules (vuejs-accessibility/*) → Category.ACCESSIBILITY
    """
    if not isinstance(raw_json, list):
        logger.warning("[adapt_eslint] Expected list, got %s — skipping.", type(raw_json).__name__)
        return []

    results: list[SARIFResult] = []
    skipped = 0

    for file_entry in raw_json:
        if not isinstance(file_entry, dict):
            continue

        file_path_raw = _safe_str(file_entry.get("filePath"))
        rel_path      = _rel(file_path_raw, base_path)

        if not rel_path:
            skipped += 1
            continue

        # Source text available on the file entry (pre-ESLint 8 format)
        source_text = file_entry.get("source") or ""

        messages = file_entry.get("messages") or []
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            raw_sev = msg.get("severity", 1)
            severity = ESLINT_SEVERITY_MAP.get(int(raw_sev), Severity.WARNING)

            # Ignore severity-0 (off) messages
            if raw_sev == 0:
                continue

            rule_id  = _safe_str(msg.get("ruleId"), "eslint:parse-error")
            line     = _safe_int(msg.get("line"), 1)
            column   = _safe_int(msg.get("column"), 0)
            message  = _safe_str(msg.get("message"), "ESLint violation")
            category = infer_category(rule_id, "eslint")

            # Build snippet from nodeText or endLine context if available
            snippet: str | None = None
            if msg.get("nodeText"):
                snippet = _safe_str(msg["nodeText"])[:200]

            try:
                results.append(SARIFResult(
                    tool_name = "eslint",
                    rule_id   = rule_id,
                    severity  = severity,
                    category  = category,
                    file_path = rel_path,
                    line      = line,
                    column    = column,
                    message   = message,
                    snippet   = snippet or None,
                ))
            except Exception as exc:
                logger.debug("[adapt_eslint] Skipped record (%s): %s", rel_path, exc)
                skipped += 1

    logger.info("[adapt_eslint] %d findings, %d skipped.", len(results), skipped)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Adapter 2: Stylelint
# ─────────────────────────────────────────────────────────────────────────────

def adapt_stylelint(raw_json: list[dict], base_path: str) -> list[SARIFResult]:
    """
    Map Stylelint JSON output → list[SARIFResult].

    Stylelint JSON shape:
    [
      {
        "source": "/abs/path/to/file.vue",
        "warnings": [
          {
            "rule":     "color-named",
            "severity": "error",      # "error" | "warning"
            "text":     "Unexpected named color \"red\" (color-named)",
            "line":     5,
            "column":   3,
            "word":     "red"         # optional — the offending token
          }
        ]
      }
    ]
    """
    if not isinstance(raw_json, list):
        logger.warning("[adapt_stylelint] Expected list, got %s — skipping.", type(raw_json).__name__)
        return []

    results: list[SARIFResult] = []
    skipped = 0

    for file_entry in raw_json:
        if not isinstance(file_entry, dict):
            continue

        file_path_raw = _safe_str(file_entry.get("source"))
        rel_path      = _rel(file_path_raw, base_path)

        if not rel_path:
            skipped += 1
            continue

        warnings = file_entry.get("warnings") or []
        for warn in warnings:
            if not isinstance(warn, dict):
                continue

            raw_sev  = _safe_str(warn.get("severity"), "warning").lower()
            severity = STYLELINT_SEVERITY_MAP.get(raw_sev, Severity.WARNING)

            rule_id  = _safe_str(warn.get("rule"), "stylelint:unknown")
            # Prefix rule_id so infer_category recognises it
            prefixed_rule = f"stylelint:{rule_id}" if not rule_id.startswith("stylelint") else rule_id
            line     = _safe_int(warn.get("line"), 1)
            column   = _safe_int(warn.get("column"), 0)

            # Stylelint embeds the rule name in the text — strip it for cleaner message
            raw_text = _safe_str(warn.get("text"), rule_id)
            message  = re.sub(r"\s*\(" + re.escape(rule_id) + r"\)\s*$", "", raw_text).strip()
            if not message:
                message = raw_text or rule_id

            # Use the offending word as a minimal snippet if available
            word    = warn.get("word")
            snippet = f"offending token: {word}" if word else None

            try:
                results.append(SARIFResult(
                    tool_name = "stylelint",
                    rule_id   = prefixed_rule,
                    severity  = severity,
                    category  = Category.STYLE,
                    file_path = rel_path,
                    line      = line,
                    column    = column,
                    message   = message,
                    snippet   = snippet,
                ))
            except Exception as exc:
                logger.debug("[adapt_stylelint] Skipped record (%s): %s", rel_path, exc)
                skipped += 1

    logger.info("[adapt_stylelint] %d findings, %d skipped.", len(results), skipped)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Adapter 3: CSpell
# ─────────────────────────────────────────────────────────────────────────────

def adapt_cspell(raw_json: dict | list, base_path: str) -> list[SARIFResult]:
    """
    Map CSpell JSON output → list[SARIFResult].

    CSpell --reporter json writes a JSON object to stdout:
    {
      "issues": [
        {
          "uri":         "file:///abs/path/to/file.vue",
          "filename":    "/abs/path/to/file.vue",   # alternative field
          "row":         10,
          "col":         5,
          "text":        "misspeled",
          "message":     "Unknown word (misspeled)",
          "suggestions": ["misspelled", "misspelled"]
        }
      ],
      "files":          100,
      "filesWithIssues": 5,
      "issues":         10   # top-level count — conflicts with inner key in some versions
    }

    Note: In some CSpell versions the top-level JSON is an array of issue objects.
    Both shapes are handled.
    """
    issues: list[dict] = []

    if isinstance(raw_json, dict):
        # Standard shape: {"issues": [...], ...}
        v = raw_json.get("issues", [])
        if isinstance(v, list):
            issues = v
        # Fallback: {"result": {"issues": [...]}}
        elif isinstance(raw_json.get("result"), dict):
            issues = raw_json["result"].get("issues", [])
    elif isinstance(raw_json, list):
        # Some reporter versions output a bare array
        issues = raw_json
    else:
        logger.warning("[adapt_cspell] Unexpected JSON shape %s — skipping.", type(raw_json).__name__)
        return []

    results: list[SARIFResult] = []
    skipped = 0

    for issue in issues:
        if not isinstance(issue, dict):
            continue

        # Resolve file path — CSpell may use "uri" (file://) or "filename"
        file_path_raw = (
            _safe_str(issue.get("uri"))
            or _safe_str(issue.get("filename"))
        )
        rel_path = _rel(file_path_raw, base_path)

        if not rel_path:
            skipped += 1
            continue

        word     = _safe_str(issue.get("text"), "?")
        line     = _safe_int(issue.get("row"),  1)
        column   = _safe_int(issue.get("col"),  0)
        message  = _safe_str(
            issue.get("message"),
            f"Unknown word: {word!r}",
        )

        # Build a helpful snippet: "word → [suggestion1, suggestion2]"
        suggestions = issue.get("suggestions") or []
        if suggestions and isinstance(suggestions, list):
            snippet = f"{word!r} → suggestions: {', '.join(str(s) for s in suggestions[:3])}"
        else:
            snippet = f"Unrecognised word: {word!r}"

        try:
            results.append(SARIFResult(
                tool_name = "cspell",
                rule_id   = "cspell:unknown-word",
                severity  = CSPELL_SEVERITY_DEFAULT,
                category  = Category.SPELLING,
                file_path = rel_path,
                line      = line,
                column    = column,
                message   = message,
                snippet   = snippet,
            ))
        except Exception as exc:
            logger.debug("[adapt_cspell] Skipped record (%s): %s", rel_path, exc)
            skipped += 1

    logger.info("[adapt_cspell] %d findings, %d skipped.", len(results), skipped)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Adapter 4: vue-mess-detector (VMD)
# ─────────────────────────────────────────────────────────────────────────────

def adapt_vue_mess_detector(raw_json: dict | list, base_path: str) -> list[SARIFResult]:
    """
    Map vue-mess-detector JSON output → list[SARIFResult].

    VMD (v0.68.0) outputs a dict with a "codeHealthOutput" key:
    {
      "codeHealthOutput": [
        {
          "id":          "simpleName",
          "description": "Rule description",
          "filesAffected": 3,
          "errors": [
            {
              "file":    "src/views/Foo.vue",   # may be absolute or relative
              "message": "Component name is not descriptive enough",
              "severity": "error"               # "error" | "warning" | "info"
            }
          ]
        }
      ]
    }

    Alternative flat shape seen in some versions:
    [
      {
        "file":    "...",
        "rule":    "simpleName",
        "message": "...",
        "severity": "error"
      }
    ]

    Both shapes are handled gracefully.
    """
    VMD_SEVERITY_MAP = {
        "error":   Severity.ERROR,
        "warning": Severity.WARNING,
        "info":    Severity.INFO,
        "hint":    Severity.INFO,
    }

    results: list[SARIFResult] = []
    skipped = 0

    def _process_error(rule_id: str, error: dict) -> None:
        nonlocal skipped

        file_path_raw = _safe_str(
            error.get("file") or error.get("filePath") or error.get("filename")
        )
        rel_path  = _rel(file_path_raw, base_path)
        if not rel_path:
            skipped += 1
            return

        raw_sev  = _safe_str(error.get("severity"), "warning").lower()
        severity = VMD_SEVERITY_MAP.get(raw_sev, Severity.WARNING)

        line    = _safe_int(error.get("line") or error.get("lineNumber"), 1)
        column  = _safe_int(error.get("column") or error.get("col"), 0)
        message = _safe_str(error.get("message"), f"VMD rule violation: {rule_id}")

        try:
            results.append(SARIFResult(
                tool_name = "vue-mess-detector",
                rule_id   = f"vmd:{rule_id}",
                severity  = severity,
                category  = Category.COMPLEXITY,   # VMD is always a complexity tool
                file_path = rel_path,
                line      = line,
                column    = column,
                message   = message,
                snippet   = None,
            ))
        except Exception as exc:
            logger.debug("[adapt_vmd] Skipped (%s/%s): %s", rule_id, rel_path, exc)
            skipped += 1

    # ── Shape 1: {"codeHealthOutput": [...]} ─────────────────────────────────
    if isinstance(raw_json, dict):
        health_output = raw_json.get("codeHealthOutput") or raw_json.get("output") or []
        if isinstance(health_output, list):
            for rule_block in health_output:
                if not isinstance(rule_block, dict):
                    continue
                rule_id = _safe_str(rule_block.get("id") or rule_block.get("rule"), "unknown")
                errors  = rule_block.get("errors") or rule_block.get("violations") or []
                if isinstance(errors, list):
                    for error in errors:
                        if isinstance(error, dict):
                            _process_error(rule_id, error)
        else:
            logger.warning("[adapt_vmd] Unrecognised dict shape — no 'codeHealthOutput' key.")

    # ── Shape 2: flat list of findings ───────────────────────────────────────
    elif isinstance(raw_json, list):
        for item in raw_json:
            if not isinstance(item, dict):
                continue
            rule_id = _safe_str(item.get("rule") or item.get("id"), "unknown")
            _process_error(rule_id, item)
    else:
        logger.warning("[adapt_vmd] Unexpected JSON shape %s — skipping.", type(raw_json).__name__)

    logger.info("[adapt_vmd] %d findings, %d skipped.", len(results), skipped)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Master entry-point
# ─────────────────────────────────────────────────────────────────────────────

# Maps each tool name (as stored in ToolResult.tool) to its adapter function
_ADAPTER_MAP = {
    "eslint"           : adapt_eslint,
    "stylelint"        : adapt_stylelint,
    "cspell"           : adapt_cspell,
    "vue-mess-detector": adapt_vue_mess_detector,
    # dependency-cruiser and jscpd adapters deferred (Phase 4)
}


def adapt_all(
    tool_results: list,   # list[ToolResult] from run_audit.py
    base_path:    str,
    project:      str,
) -> SARIFReport:
    """
    Run all available adapters over the captured ToolResults and accumulate
    findings into a single SARIFReport.

    Args:
        tool_results: list of ToolResult dataclass instances from run_audit.py
        base_path:    absolute path to the scanned repo (used for path normalization)
        project:      project name string (written into SARIFReport.project)

    Returns:
        A validated SARIFReport containing all findings from all tools.
    """
    all_results: list[SARIFResult] = []
    adapter_stats: dict[str, int]  = {}

    for tr in tool_results:
        tool_name = tr.tool
        adapter   = _ADAPTER_MAP.get(tool_name)

        if adapter is None:
            logger.info("[adapt_all] No adapter registered for '%s' — skipping.", tool_name)
            continue

        if tr.raw_json is None:
            logger.warning("[adapt_all] '%s' produced no JSON — skipping adapter.", tool_name)
            continue

        try:
            findings = adapter(tr.raw_json, base_path)
        except Exception as exc:
            logger.error("[adapt_all] Adapter for '%s' raised: %s", tool_name, exc)
            findings = []

        adapter_stats[tool_name] = len(findings)
        all_results.extend(findings)

    report = SARIFReport(
        project   = project,
        base_path = base_path,
        results   = all_results,
    )

    logger.info(
        "[adapt_all] Normalisation complete. %d total findings from %d tools.",
        len(all_results), len(adapter_stats),
    )
    for tool, count in adapter_stats.items():
        logger.info("  %-25s %d findings", tool, count)

    return report
