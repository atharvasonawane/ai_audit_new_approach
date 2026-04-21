"""
schema_models.py
================
Single source of truth for the V4 pipeline's data contract.

Every tool adapter (ESLint, CSpell, Stylelint, vue-mess-detector, etc.)
MUST produce a list[SARIFResult] before any data touches the database.

Fields are 1-to-1 with Section 4 of MASTER_ARCHITECTURE.md:
  tool_name | rule_id | severity | category | file_path | line | column | message | snippet
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    """
    Normalized severity levels accepted by the pipeline.
    All tool-specific levels (e.g. ESLint 0/1/2) must map to these three values.
    """
    ERROR   = "error"
    WARNING = "warning"
    INFO    = "info"


class Category(str, Enum):
    """
    Domain bucket that every finding belongs to.
    Drives dashboard grouping and DB rule_violations.category column.
    """
    ACCESSIBILITY = "accessibility"
    COMPLEXITY    = "complexity"
    STYLE         = "style"
    ARCHITECTURE  = "architecture"
    SECURITY      = "security"
    SPELLING      = "spelling"
    DUPLICATION   = "duplication"


# ─────────────────────────────────────────────────────────────────────────────
# Core Finding Model
# ─────────────────────────────────────────────────────────────────────────────

class SARIFResult(BaseModel):
    """
    The unified schema for every single finding produced by the V4 pipeline.

    Constraints (from MASTER_ARCHITECTURE.md §4):
      - tool_name  : free string, e.g. "eslint", "cspell", "stylelint"
      - rule_id    : tool-prefixed, e.g. "vue/no-mutating-props", "cspell:unknown-word"
      - severity   : MUST be one of the Severity enum values
      - category   : MUST be one of the Category enum values
      - file_path  : MUST be relative to base_path (enforced by path_utils at adapter level)
      - line       : 1-indexed, minimum 1
      - column     : 0-indexed (or 1-indexed — normalized to int, tool-dependent)
      - message    : human-readable description, non-empty
      - snippet    : optional 1-2 lines of surrounding source code
    """

    tool_name : str      = Field(..., description="Name of the tool that produced this finding")
    rule_id   : str      = Field(..., description="Tool-prefixed rule identifier")
    severity  : Severity = Field(..., description="Normalized severity: error | warning | info")
    category  : Category = Field(..., description="Domain bucket for dashboard grouping")
    file_path : str      = Field(..., description="File path relative to base_path")
    line      : int      = Field(..., ge=1,  description="Line number (1-indexed)")
    column    : int      = Field(..., ge=0,  description="Column number (0 or 1-indexed)")
    message   : str      = Field(..., min_length=1, description="Human-readable description")
    snippet   : Optional[str] = Field(None, description="1-2 surrounding lines of source code")

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("tool_name", "rule_id", "file_path", "message", mode="before")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        """Strip whitespace and reject blank strings."""
        v = v.strip()
        if not v:
            raise ValueError("Field must not be blank or whitespace-only.")
        return v

    @field_validator("file_path", mode="before")
    @classmethod
    def reject_absolute_paths(cls, v: str) -> str:
        """
        Enforce that file_path is always relative (not absolute).
        path_utils.normalize_path() in each adapter must handle this BEFORE
        constructing the model.
        """
        import os
        v = v.strip().replace("\\", "/")
        if os.path.isabs(v):
            raise ValueError(
                f"file_path must be relative to base_path, got absolute path: '{v}'. "
                "Run it through path_utils.normalize_path() first."
            )
        return v

    @field_validator("snippet", mode="before")
    @classmethod
    def clamp_snippet(cls, v: Optional[str]) -> Optional[str]:
        """Enforce max 2 lines in the snippet field."""
        if v is None:
            return None
        lines = v.strip().splitlines()
        if len(lines) > 2:
            lines = lines[:2]
        return "\n".join(lines)

    class Config:
        use_enum_values = True


# ─────────────────────────────────────────────────────────────────────────────
# Tool-level Severity Mapping Helpers
# ─────────────────────────────────────────────────────────────────────────────

# ESLint uses numeric severity: 0=off, 1=warn, 2=error
ESLINT_SEVERITY_MAP: dict[int, Severity] = {
    0: Severity.INFO,
    1: Severity.WARNING,
    2: Severity.ERROR,
}

# CSpell only produces one level — treat as warning
CSPELL_SEVERITY_DEFAULT = Severity.WARNING

# Stylelint: "error" | "warning"
STYLELINT_SEVERITY_MAP: dict[str, Severity] = {
    "error"  : Severity.ERROR,
    "warning": Severity.WARNING,
}

# ESLint plugin → Category inference table
# Maps rule_id prefix / plugin name to a Category bucket
RULE_CATEGORY_MAP: dict[str, Category] = {
    "vue/":                  Category.COMPLEXITY,
    "vuejs-accessibility/":  Category.ACCESSIBILITY,
    "complexity":            Category.COMPLEXITY,
    "cspell":                Category.SPELLING,
    "stylelint":             Category.STYLE,
    "import/":               Category.ARCHITECTURE,
    "no-duplicate-imports":  Category.DUPLICATION,
    "security/":             Category.SECURITY,
}


def infer_category(rule_id: str, tool_name: str) -> Category:
    """
    Best-effort category inference from rule_id prefix or tool_name.
    Falls back to Category.STYLE if no match found.

    Usage in adapters:
        category = infer_category(rule_id="vue/no-mutating-props", tool_name="eslint")
        # → Category.COMPLEXITY
    """
    for prefix, category in RULE_CATEGORY_MAP.items():
        if rule_id.startswith(prefix):
            return category
    # Fall back to tool name
    if tool_name == "cspell":
        return Category.SPELLING
    if tool_name == "stylelint":
        return Category.STYLE
    return Category.STYLE


# ─────────────────────────────────────────────────────────────────────────────
# Report Container
# ─────────────────────────────────────────────────────────────────────────────

class SARIFReport(BaseModel):
    """
    Top-level container for one complete pipeline scan run.
    Written to DB as a single scan_run row, with all results as child rows.
    """

    project   : str
    base_path : str
    results   : list[SARIFResult] = Field(default_factory=list)

    # ── Aggregation helpers ───────────────────────────────────────────────────

    def count_by_severity(self) -> dict[str, int]:
        """Returns {severity_value: count} for all results."""
        counts: dict[str, int] = {s.value: 0 for s in Severity}
        for r in self.results:
            counts[r.severity] += 1
        return counts

    def count_by_category(self) -> dict[str, int]:
        """Returns {category_value: count} for all results."""
        counts: dict[str, int] = {c.value: 0 for c in Category}
        for r in self.results:
            counts[r.category] += 1
        return counts

    def health_score(self) -> float:
        """
        Aggregate health score (0–100) for the scanned project.

        Formula (from MASTER_ARCHITECTURE.md §3, Phase 3):
            penalty = Σ weight(severity) for each result
            score   = max(0, 100 - penalty)

        Severity weights:
            error   → 5 points deducted
            warning → 3 points deducted
            info    → 1 point  deducted
        """
        weights = {
            Severity.ERROR.value  : 5,
            Severity.WARNING.value: 3,
            Severity.INFO.value   : 1,
        }
        penalty = sum(weights.get(r.severity, 1) for r in self.results)
        return round(max(0.0, 100.0 - penalty), 2)

    def top_offending_files(self, n: int = 10) -> list[dict]:
        """
        Returns the top-n files with the most findings, sorted descending.
        Useful for the dashboard's 'Most Flagged Files' table.
        """
        from collections import Counter
        counts = Counter(r.file_path for r in self.results)
        return [{"file": f, "count": c} for f, c in counts.most_common(n)]

    def summary(self) -> dict:
        """Compact summary dict for console printing and scan_runs DB row."""
        return {
            "project"        : self.project,
            "total_findings" : len(self.results),
            "by_severity"    : self.count_by_severity(),
            "by_category"    : self.count_by_category(),
            "health_score"   : self.health_score(),
            "top_files"      : self.top_offending_files(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Structural Extractions
# ─────────────────────────────────────────────────────────────────────────────

class ComponentMetricsModel(BaseModel):
    file_path: str          # relative to base_path
    script_lang: str        # "js" | "ts"
    is_script_setup: bool
    loc_script: int         # lines of code in <script>
    loc_template: int       # lines of code in <template>
    method_count: int
    computed_count: int
    watcher_count: int
    prop_count: int
    max_nesting_depth: int


class UINodeModel(BaseModel):
    file_path: str
    element_type: str       # "header" | "button" | "visible_text"
    text_content: str
    is_dynamic: bool        # True if content has {{ }} interpolation
    line: int


class PropsEmitsModel(BaseModel):
    file_path: str
    props: list[str]        # ["title", "isActive", ...]
    emits: list[str]        # ["update:modelValue", "close", ...]


class ESLintMessageModel(BaseModel):
    """Raw message schema from ESLint JSON output."""
    ruleId: Optional[str] = None
    severity: int
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    nodeText: Optional[str] = None

class RuleViolationModel(BaseModel):
    """Raw top-level schema from ESLint JSON output per file."""
    filePath: str
    messages: list[ESLintMessageModel]
