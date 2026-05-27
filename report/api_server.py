"""
Flask API Server for Code Audit Librarian
Stage 6 — Read-only JSON API serving SQLite data to Vue.js frontend

All endpoints return JSON with CORS headers.
Dynamic code snippets generated for api_calls, file_flags, and accessibility_defects.
"""

import argparse
import ast
import json
import sqlite3
import subprocess
import os
import sys
import re
import urllib.request
import urllib.error
from pathlib import Path

# Resolve project root and insert into sys.path to allow clean imports from the root folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Any, Dict, List, Optional

import yaml

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading

# Active scan tracking process and thread safety lock
active_scan_process = None
active_scan_lock = threading.Lock()

# Configure logging
from utils.logger import logger


app = Flask(__name__)
CORS(app)

# Load configuration
CONFIG_PATH = PROJECT_ROOT / "audit_tool" / "config" / "project_config.yaml"



def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


CONFIG = _load_config()
db_config_path = CONFIG.get("db", {}).get("path")
if db_config_path:
    DB_PATH = Path(db_config_path)
    if not DB_PATH.is_absolute():
        DB_PATH = PROJECT_ROOT / DB_PATH
else:
    DB_PATH = PROJECT_ROOT / "audit_history.db"
PROJECT_NAME = CONFIG.get("project_name", "default")
BASE_PATH = CONFIG.get("base_path", "")
PATH_WALK_SKIP_DIRS = {
    "node_modules", "venv", ".venv", ".git", ".gemini", "dist",
    "out", "build", "not_important", "__pycache__", ".idea"
}
AI_FIX_MAX_CONTEXT_LINES = 500
DEFAULT_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# WCAG metadata dictionary for accessibility rules
WCAG_METADATA = {
    "vue/no-static-inline-styles": {
        "criterion": "1.3.1 Info and Relationships",
        "level": "A",
        "explanation": "Inline styles can interfere with user stylesheets and assistive technologies.",
    },
    "vuejs-accessibility/alt-text": {
        "criterion": "1.1.1 Non-text Content",
        "level": "A",
        "explanation": "Images must have alternative text for screen readers.",
    },
    "vuejs-accessibility/anchor-has-content": {
        "criterion": "2.4.4 Link Purpose",
        "level": "A",
        "explanation": "Links must have discernible text content.",
    },
    "vuejs-accessibility/aria-props": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "ARIA attributes must be valid and properly used.",
    },
    "vuejs-accessibility/aria-role": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "ARIA roles must be valid HTML5 roles.",
    },
    "vuejs-accessibility/aria-unsupported-elements": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "ARIA should not be used on elements that don't support it.",
    },
    "vuejs-accessibility/click-events-have-key-events": {
        "criterion": "2.1.1 Keyboard",
        "level": "A",
        "explanation": "Interactive elements must be keyboard accessible.",
    },
    "vuejs-accessibility/form-control-has-label": {
        "criterion": "3.3.2 Labels or Instructions",
        "level": "A",
        "explanation": "Form controls must have associated labels.",
    },
    "vuejs-accessibility/heading-has-content": {
        "criterion": "1.3.1 Info and Relationships",
        "level": "A",
        "explanation": "Heading elements must have content for proper document structure.",
    },
    "vuejs-accessibility/iframe-has-title": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "iframes must have a title attribute for context.",
    },
    "vuejs-accessibility/interactive-supports-focus": {
        "criterion": "2.1.1 Keyboard",
        "level": "A",
        "explanation": "Interactive elements must be focusable.",
    },
    "vuejs-accessibility/label-has-for": {
        "criterion": "1.3.1 Info and Relationships",
        "level": "A",
        "explanation": "Labels must be properly associated with form controls.",
    },
    "vuejs-accessibility/media-has-caption": {
        "criterion": "1.2.2 Captions (Prerecorded)",
        "level": "A",
        "explanation": "Audio and video content must have captions.",
    },
    "vuejs-accessibility/mouse-events-have-key-events": {
        "criterion": "2.1.1 Keyboard",
        "level": "A",
        "explanation": "Mouse event handlers must have keyboard equivalents.",
    },
    "vuejs-accessibility/no-access-key": {
        "criterion": "2.4.1 Bypass Blocks",
        "level": "A",
        "explanation": "Access keys can conflict with assistive technology shortcuts.",
    },
    "vuejs-accessibility/no-autofocus": {
        "criterion": "2.4.3 Focus Order",
        "level": "A",
        "explanation": "Autofocus can disorient users relying on screen readers.",
    },
    "vuejs-accessibility/no-distracting-elements": {
        "criterion": "2.2.2 Pause, Stop, Hide",
        "level": "A",
        "explanation": "Blinking or scrolling content must be controllable.",
    },
    "vuejs-accessibility/no-onchange": {
        "criterion": "3.2.2 On Input",
        "level": "A",
        "explanation": "Form controls should not trigger context changes on input alone.",
    },
    "vuejs-accessibility/no-redundant-roles": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "Don't use ARIA roles that match the element's implicit role.",
    },
    "vuejs-accessibility/role-has-required-aria-props": {
        "criterion": "4.1.2 Name, Role, Value",
        "level": "A",
        "explanation": "ARIA roles must include all required attributes.",
    },
    "vuejs-accessibility/tabindex-no-positive": {
        "criterion": "2.4.3 Focus Order",
        "level": "A",
        "explanation": "Positive tabindex values disrupt natural tab order.",
    },
}


def _db_connect() -> sqlite3.Connection:
    """Create a database connection for reading, with WAL checkpoint to ensure
    the main .db file reflects all recent writes before any query runs.

    The old mode=ro URI connection bypassed WAL on some platforms, causing
    web-based SQLite viewers (which read the raw .db file) to see stale data.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    # Flush WAL → main .db file so the on-disk file (and its mtime) is current.
    # This means any SQLite viewer that opens the .db file directly will see fresh data.
    conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
    conn.execute("PRAGMA query_only=ON;")  # Safety: prevent accidental writes
    return conn


def _db_connect_rw() -> sqlite3.Connection:
    """Create a read-write database connection with pragmas enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _cleanup_in_progress_runs():
    """Helper to delete any audit runs that are marked 'in_progress' and clean up cascading tables."""
    try:
        conn = _db_connect_rw()
        in_progress_runs = conn.execute("SELECT id FROM audit_runs WHERE status = 'in_progress'").fetchall()
        for run in in_progress_runs:
            run_id = run["id"]
            logger.info(f"Cleaning up incomplete in_progress run ID: {run_id}")
            conn.execute("DELETE FROM audit_runs WHERE id = ?", (run_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to clean up in-progress runs: {e}")


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert sqlite3.Row to dictionary."""
    return dict(row) if row else {}


def _resolve_absolute_path(file_path: str) -> Optional[Path]:
    """
    Resolve absolute path of file dynamically across potential project bases on Windows.
    """
    # Normalize slashes
    file_path = file_path.replace("\\", "/")
    # Remove leading slashes and ../ transitions
    normalized = file_path.lstrip("/")
    while normalized.startswith("../"):
        normalized = normalized[3:]
    
    candidates = []
    
    # 1. Try absolute path directly
    candidates.append(Path(file_path))
    candidates.append(Path(normalized))
    
    # 2. Try relative to current BASE_PATH
    if BASE_PATH:
        base = Path(BASE_PATH)
        candidates.append(base / normalized)
        candidates.append(base.parent / normalized)
        candidates.append(base.parent.parent / normalized)
        
    # 3. Try relative to PROJECT_ROOT and its parent (Desktop)
    if PROJECT_ROOT:
        candidates.append(PROJECT_ROOT / normalized)
        desktop = PROJECT_ROOT.parent
        candidates.append(desktop / normalized)
        
        # Try appending starting directory segment to the desktop base path
        parts = Path(normalized).parts
        if parts:
            candidates.append(desktop / parts[0] / normalized)
            
    # Check all candidates
    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return p.resolve()
        except Exception:
            continue
            
    # 4. Walk Desktop/PROJECT_ROOT.parent defensively to resolve collisions
    if PROJECT_ROOT:
        desktop = PROJECT_ROOT.parent
        base_name = os.path.basename(normalized)
        candidates_found = []
        try:
            # Walk up to a certain depth to keep it extremely fast
            max_depth = 4
            desktop_str = str(desktop)
            desktop_depth = desktop_str.count(os.sep)
            
            for root, dirs, files in os.walk(desktop_str):
                # Prune noisy directories to keep walk lightning fast
                dirs[:] = [d for d in dirs if d.lower() not in (
                    'node_modules', 'venv', '.git', '.gemini', 'dist', 'out', 'build', 'not_important', '__pycache__'
                )]
                
                # Enforce max depth constraint
                current_depth = root.count(os.sep) - desktop_depth
                if current_depth > max_depth:
                    dirs[:] = []  # stop walking deeper in this branch
                    continue
                    
                if base_name in files:
                    full_walk_path = Path(root) / base_name
                    # Verify the tail of the walk path matches the relative file_path
                    walk_posix = str(full_walk_path).replace("\\", "/")
                    if walk_posix.endswith(normalized):
                        # Calculate score
                        score = 0
                        # Check if any path segments contain the active PROJECT_NAME
                        path_parts_lower = [p.lower() for p in full_walk_path.parts]
                        if PROJECT_NAME.lower() in path_parts_lower:
                            score += 100
                        # Also check if it's in the PROJECT_ROOT directory
                        if str(PROJECT_ROOT).lower() in str(full_walk_path).lower():
                            score += 50
                        candidates_found.append((score, full_walk_path))
        except Exception as walk_err:
            logger.warning(f"[PATH RESOLUTION] Walk fallback failed: {walk_err}")
            
        if candidates_found:
            # Sort by score desc, then by path length asc (shorter path means closer match)
            candidates_found.sort(key=lambda x: (-x[0], len(str(x[1]))))
            best_match = candidates_found[0][1]
            try:
                if best_match.exists() and best_match.is_file():
                    logger.info(f"[PATH RESOLUTION] Walk fallback resolved '{file_path}' to '{best_match}' (score: {candidates_found[0][0]})")
                    return best_match.resolve()
            except Exception:
                pass
            
    return None


def _normalize_relative_path(file_path: str) -> str:
    normalized = (file_path or "").replace("\\", "/").strip()
    normalized = re.sub(r"^[A-Za-z]:/", "", normalized)
    normalized = normalized.lstrip("/")
    parts = []
    for part in normalized.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def _get_workspace_roots() -> List[Path]:
    roots: List[Path] = []
    for raw_root in [BASE_PATH, str(PROJECT_ROOT), str(PROJECT_ROOT.parent)]:
        if not raw_root:
            continue
        try:
            root_path = Path(raw_root).resolve()
        except Exception:
            continue
        if root_path.exists() and root_path not in roots:
            roots.append(root_path)
    return roots


def _is_path_within_roots(path: Path, roots: List[Path]) -> bool:
    try:
        resolved = path.resolve()
    except Exception:
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _score_candidate_path(candidate: Path, expected_relative_path: str, search_roots: List[Path]) -> int:
    candidate_parts = [part.lower() for part in candidate.parts]
    expected_parts = [part.lower() for part in Path(expected_relative_path).parts if part]
    candidate_posix = candidate.as_posix().lower()
    expected_posix = expected_relative_path.lower()

    score = 0
    if expected_posix and candidate_posix.endswith(expected_posix):
        score += 500

    if expected_parts:
        tail = candidate_parts[-len(expected_parts):]
        if tail == expected_parts:
            score += 400

        matched_tail = 0
        for expected_part, candidate_part in zip(reversed(expected_parts), reversed(candidate_parts)):
            if expected_part != candidate_part:
                break
            matched_tail += 1
        score += matched_tail * 35

        basename = expected_parts[-1]
        if candidate.name.lower() == basename:
            score += 120

    for root in search_roots:
        try:
            candidate.relative_to(root)
            score += 80
            break
        except ValueError:
            continue

    # Priority boost for target project roots
    if BASE_PATH:
        try:
            candidate.relative_to(Path(BASE_PATH))
            score += 20000
        except ValueError:
            pass
    if PROJECT_ROOT:
        try:
            candidate.relative_to(PROJECT_ROOT)
            score += 10000
        except ValueError:
            pass

    if PROJECT_NAME and PROJECT_NAME.lower() in candidate_posix:
        score += 40

    score -= len(candidate.parts)
    return score


def _find_workspace_file(expected_relative_path: str) -> Optional[Path]:
    normalized = _normalize_relative_path(expected_relative_path)
    if not normalized:
        return None

    search_roots = _get_workspace_roots()
    direct_candidates: List[Path] = []

    raw_candidate = Path(expected_relative_path)
    if raw_candidate.is_absolute():
        direct_candidates.append(raw_candidate)

    for root in search_roots:
        direct_candidates.append(root / normalized)

    best_match: Optional[Path] = None
    best_score: Optional[int] = None

    for candidate in direct_candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if not resolved.exists() or not resolved.is_file():
            continue
        if not _is_path_within_roots(resolved, search_roots):
            continue
        score = _score_candidate_path(resolved, normalized, search_roots)
        if best_score is None or score > best_score:
            best_match = resolved
            best_score = score

    target_name = Path(normalized).name.lower()
    if target_name:
        for root in search_roots:
            try:
                for current_root, dirs, files in os.walk(root):
                    dirs[:] = [d for d in dirs if d.lower() not in PATH_WALK_SKIP_DIRS]
                    if target_name not in {name.lower() for name in files}:
                        continue
                    for file_name in files:
                        if file_name.lower() != target_name:
                            continue
                        candidate = Path(current_root) / file_name
                        try:
                            resolved = candidate.resolve()
                        except Exception:
                            continue
                        if not resolved.is_file():
                            continue
                        score = _score_candidate_path(resolved, normalized, search_roots)
                        if best_score is None or score > best_score:
                            best_match = resolved
                            best_score = score
            except Exception as walk_err:
                logger.warning(f"[AI FIX] File crawl failed under {root}: {walk_err}")

    return best_match


def _resolve_issue_file_path(run_id: Optional[int], incoming_path: str) -> tuple[Optional[Path], str]:
    normalized_incoming = _normalize_relative_path(incoming_path)
    db_path_hint = normalized_incoming

    if run_id:
        conn = None
        try:
            conn = _db_connect()
            db_path_hint = _resolve_db_file_path(conn, int(run_id), incoming_path)
        except Exception as db_err:
            logger.warning(f"[AI FIX] Failed to derive DB-backed path hint for '{incoming_path}': {db_err}")
        finally:
            if conn:
                conn.close()

    normalized_db_path = _normalize_relative_path(db_path_hint)

    # 1. Try to find if the raw path exists directly on disk
    for path_str in [incoming_path, db_path_hint, normalized_db_path, normalized_incoming]:
        if not path_str:
            continue
        try:
            p = Path(path_str)
            if p.is_absolute() and p.exists() and p.is_file():
                return p.resolve(), (normalized_db_path or normalized_incoming or path_str)
        except Exception:
            continue

    # 2. Aggressive workspace scan matching absolute structural folder layout lineage
    search_roots = _get_workspace_roots()
    
    incoming_clean = normalized_incoming.replace("\\", "/").strip("/")
    incoming_parts = [p.lower() for p in incoming_clean.split("/") if p]
    
    db_clean = normalized_db_path.replace("\\", "/").strip("/") if normalized_db_path else ""
    db_parts = [p.lower() for p in db_clean.split("/") if p] if db_clean else []

    best_match = None
    best_score = -1

    for root in search_roots:
        try:
            root_str = str(root.resolve())
            for current_root, dirs, files in os.walk(root_str):
                dirs[:] = [d for d in dirs if d.lower() not in PATH_WALK_SKIP_DIRS]
                for file_name in files:
                    full_cand = Path(current_root) / file_name
                    cand_posix = full_cand.as_posix().lower()
                    cand_parts = [p for p in cand_posix.split("/") if p]

                    score_incoming = 0
                    for idx in range(1, min(len(incoming_parts), len(cand_parts)) + 1):
                        if incoming_parts[-idx] == cand_parts[-idx]:
                            score_incoming += 10
                        else:
                            break
                    
                    score_db = 0
                    if db_parts:
                        for idx in range(1, min(len(db_parts), len(cand_parts)) + 1):
                            if db_parts[-idx] == cand_parts[-idx]:
                                    score_db += 10
                            else:
                                break

                    score = max(score_incoming, score_db)
                    if score > 0:
                        # Massive boost for matching actual BASE_PATH and PROJECT_ROOT
                        root_boost = 0
                        if BASE_PATH:
                            try:
                                full_cand.relative_to(Path(BASE_PATH))
                                root_boost += 20000
                            except ValueError:
                                pass
                        if PROJECT_ROOT:
                            try:
                                full_cand.relative_to(PROJECT_ROOT)
                                root_boost += 10000
                            except ValueError:
                                pass

                        path_len_penalty = len(cand_parts)
                        final_score = score * 100 + root_boost - path_len_penalty
                        if final_score > best_score:
                            best_score = final_score
                            best_match = full_cand
        except Exception as e:
            logger.warning(f"[PATH RESOLUTION] Error scanning workspace under {root}: {e}")

    if best_match:
        try:
            resolved_best = best_match.resolve()
            logger.info(f"[PATH RESOLUTION] Aggr structural match '{incoming_path}' to '{resolved_best}' (score: {best_score})")
            return resolved_best, (normalized_db_path or normalized_incoming or incoming_path)
        except Exception:
            pass

    # 3. Fallback to existing resolver logic
    for candidate_hint in [db_path_hint, normalized_db_path, normalized_incoming, incoming_path]:
        if not candidate_hint:
            continue
        resolved = _find_workspace_file(candidate_hint)
        if resolved:
            return resolved, (normalized_db_path or normalized_incoming or candidate_hint)

    legacy_resolved = _resolve_absolute_path(incoming_path)
    if legacy_resolved and _is_path_within_roots(legacy_resolved, _get_workspace_roots()):
        return legacy_resolved, (normalized_db_path or normalized_incoming or incoming_path)

    return None, (normalized_db_path or normalized_incoming or incoming_path)


def _build_context_window(file_lines: List[str], issue_line: int, max_context_lines: int = AI_FIX_MAX_CONTEXT_LINES) -> Dict[str, Any]:
    total_lines = len(file_lines)
    if total_lines == 0:
        return {
            "issue_line": 1,
            "issue_index": 0,
            "start_idx": 0,
            "end_idx": 0,
            "window_text": "",
            "window_line_count": 0,
        }

    clamped_line = max(1, min(issue_line, total_lines))
    issue_index = clamped_line - 1

    if total_lines > 500:
        start_idx = max(0, clamped_line - 30)
        end_idx = min(total_lines, clamped_line + 50)
    else:
        start_idx = 0
        end_idx = total_lines

    return {
        "issue_line": clamped_line,
        "issue_index": issue_index,
        "start_idx": start_idx,
        "end_idx": end_idx,
        "window_text": "".join(file_lines[start_idx:end_idx]),
        "window_line_count": end_idx - start_idx,
    }


def _build_llm_headers(api_key: str = "") -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": DEFAULT_BROWSER_USER_AGENT,
        "Origin": "http://localhost",
        "Referer": "http://localhost/",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _extract_llm_message_content(response_payload: Dict[str, Any]) -> str:
    choices = response_payload.get("choices", [])
    if not choices:
        return ""

    message = choices[0].get("message", {})
    content = message.get("content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                text_value = item.get("text") or item.get("content")
                if isinstance(text_value, str):
                    text_parts.append(text_value)
            elif isinstance(item, str):
                text_parts.append(item)
        return "\n".join(text_parts)

    return str(content or "")


def _strip_non_code_lines(lines: List[str]) -> List[str]:
    filtered: List[str] = []
    skipping_prefix = True
    explanatory_prefixes = (
        "here", "fixed", "updated", "revised", "note:", "warning:",
        "explanation:", "focus bounded window", "replacement:", "output:"
    )

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("```"):
            if skipping_prefix and stripped:
                lowered = stripped.lower()
                if lowered.startswith(explanatory_prefixes):
                    continue
        if stripped.startswith("```"):
            continue
        if stripped in {"[", "]"}:
            continue
        filtered.append(line)
        if stripped:
            skipping_prefix = False

    while filtered and not filtered[0].strip():
        filtered.pop(0)
    while filtered and not filtered[-1].strip():
        filtered.pop()

    return filtered


def _extract_snippet(file_path: str, line_number: int) -> str:
    """
    Extract a 5-line code snippet (2 lines above, target line, 2 lines below).
    Target line is marked with ► prefix.
    """
    try:
        path = _resolve_absolute_path(file_path)
        
        if not path or not path.exists():
            return f"[File not found: {file_path}]"
        
        lines = path.read_text(encoding="utf-8").splitlines()
        
        if line_number < 1 or line_number > len(lines):
            return f"[Line {line_number} out of range]"
        
        start = max(1, line_number - 2)
        end = min(len(lines), line_number + 2)
        
        snippet_lines = []
        for idx in range(start, end + 1):
            prefix = "► " if idx == line_number else "  "
            snippet_lines.append(f"{prefix}{idx}: {lines[idx - 1]}")
        
        return "\n".join(snippet_lines)
    
    except Exception as e:
        return f"[Error reading file: {e}]"


def _get_run_id(conn: sqlite3.Connection, project_name: str) -> Optional[int]:
    """Resolve run_id from query param or fall back to most recent completed run."""
    run_id_param = request.args.get("run_id")
    try:
        run_id = int(run_id_param) if run_id_param else None
    except ValueError:
        run_id = None

    if run_id is not None:
        return run_id

    # Fall back: most recent completed run globally (not filtered by project_name,
    # since the config project_name can change between runs)
    row = conn.execute(
        "SELECT id FROM audit_runs WHERE status = 'completed' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        return row["id"]

    # Last resort: any run
    row = conn.execute(
        "SELECT id FROM audit_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row:
        return row["id"]

    return None


def _resolve_db_file_path(conn: sqlite3.Connection, run_id: int, file_path: str) -> str:
    """
    Defensively normalize and map input file_path (even if absolute system path)
    to a stored workspace-relative path segment in database vue_files table.
    """
    if not file_path:
        return file_path

    # Standardize to forward slashes and strip leading/trailing slashes
    norm_path = file_path.replace("\\", "/").strip("/")

    # 1. Exact match on raw path
    row = conn.execute(
        "SELECT file_path FROM vue_files WHERE run_id = ? AND file_path = ?",
        (run_id, file_path)
    ).fetchone()
    if row:
        return row["file_path"]

    # 2. Exact match on standardized norm_path
    row = conn.execute(
        "SELECT file_path FROM vue_files WHERE run_id = ? AND file_path = ?",
        (run_id, norm_path)
    ).fetchone()
    if row:
        return row["file_path"]

    # 3. Check for suffix or parent mapping against all DB paths in the same run
    all_files = conn.execute(
        "SELECT file_path FROM vue_files WHERE run_id = ?",
        (run_id,)
    ).fetchall()

    for r in all_files:
        db_path = r["file_path"]
        db_norm = db_path.replace("\\", "/").strip("/")
        
        # Check if one path is a suffix of the other (absolute paths are longer suffixes of relative paths)
        if norm_path.endswith(db_norm) or db_norm.endswith(norm_path):
            return db_path

    # 4. Fallback case-insensitive suffix mapping
    for r in all_files:
        db_path = r["file_path"]
        db_norm = db_path.replace("\\", "/").strip("/").lower()
        if norm_path.lower().endswith(db_norm) or db_norm.endswith(norm_path.lower()):
            return db_path

    # Final resort fallback
    return file_path.replace("\\", "/")


@app.route("/api/recent-audits/<int:run_id>", methods=["DELETE"])
def delete_recent_audit(run_id):
    """
    DELETE /api/recent-audits/<int:run_id>
    Deletes the audit run and all cascading dependency tables.
    """
    try:
        conn = _db_connect_rw()
        
        # Check if the audit run exists
        run = conn.execute("SELECT id FROM audit_runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            conn.close()
            return jsonify({"error": f"Audit run with ID {run_id} not found"}), 404
            
        # Execute the delete statement
        conn.execute("DELETE FROM audit_runs WHERE id = ?", (run_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"message": f"Successfully deleted audit run {run_id} and all related records."}), 200
        
    except Exception as e:
        logger.error(f"Error during deletion of run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/recent-audits", methods=["GET"])
def get_recent_audits():
    """
    GET /api/recent-audits
    Returns list of recent audits from audit_runs table with their actual metrics.
    """
    try:
        conn = _db_connect()
        runs = conn.execute(
            """
            SELECT id, project_name, started_at, status, completed_at
            FROM audit_runs
            ORDER BY started_at DESC
            """
        ).fetchall()
        
        recent_audits = []
        for run in runs:
            proj_name = run["project_name"]
            r_id = run["id"]
            
            total_files = conn.execute(
                "SELECT COUNT(*) as count FROM vue_files WHERE run_id = ?",
                (r_id,)
            ).fetchone()["count"]
            
            total_eslint = conn.execute(
                "SELECT COALESCE(SUM(eslint_flag_count), 0) as count FROM vue_files WHERE run_id = ?",
                (r_id,)
            ).fetchone()["count"]
            
            total_accessibility = conn.execute(
                "SELECT COUNT(*) as count FROM accessibility_defects WHERE run_id = ?",
                (r_id,)
            ).fetchone()["count"]
            
            total_ai = conn.execute(
                "SELECT COUNT(*) as count FROM ai_issues WHERE run_id = ? AND phase = 'file_analysis'",
                (r_id,)
            ).fetchone()["count"]
            
            total_issues = total_eslint + total_accessibility + total_ai
            
            display_name = proj_name if proj_name else PROJECT_ROOT.name
            
            recent_audits.append({
                "id": r_id,
                "project_name": display_name,
                "started_at": run["started_at"],
                "status": run["status"],
                "completed_at": run["completed_at"],
                "total_files": total_files,
                "total_issues": total_issues
            })
        # If audit_runs is empty, but vue_files has data
        if not recent_audits:
            # Check if there are files in vue_files
            distinct_projects = conn.execute("SELECT DISTINCT project_name FROM vue_files").fetchall()
            for row in distinct_projects:
                proj_name = row["project_name"]
                # Count total files
                total_files = conn.execute(
                    "SELECT COUNT(*) as count FROM vue_files WHERE project_name = ?",
                    (proj_name,)
                ).fetchone()["count"]
                if total_files > 0:
                    # Count ESLint, Accessibility, AI
                    total_eslint = conn.execute(
                        "SELECT COALESCE(SUM(eslint_flag_count), 0) as count FROM vue_files WHERE project_name = ?",
                        (proj_name,)
                    ).fetchone()["count"]
                    total_accessibility = conn.execute(
                        "SELECT COUNT(*) as count FROM accessibility_defects WHERE project_name = ?",
                        (proj_name,)
                    ).fetchone()["count"]
                    total_ai = conn.execute(
                        "SELECT COUNT(*) as count FROM ai_issues WHERE project_name = ? AND phase = 'file_analysis'",
                        (proj_name,)
                    ).fetchone()["count"]
                    total_issues = total_eslint + total_accessibility + total_ai
                    
                    display_name = proj_name if proj_name else PROJECT_ROOT.name
                    recent_audits.append({
                        "project_name": display_name,
                        "started_at": None,
                        "status": "completed",
                        "completed_at": None,
                        "total_files": total_files,
                        "total_issues": total_issues
                    })
                    
        conn.close()
        return jsonify(recent_audits)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/summary", methods=["GET"])
def get_summary():
    """
    GET /api/summary
    Returns aggregate project statistics.
    """
    try:
        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify({"error": "No audit runs found"}), 404
        
        # Total files
        total_files = conn.execute(
            "SELECT COUNT(*) as count FROM vue_files WHERE run_id = ? AND file_path LIKE '%.vue'",
            (run_id,)
        ).fetchone()["count"]
        
        # Total ESLint flags
        total_eslint = conn.execute(
            "SELECT COALESCE(SUM(eslint_flag_count), 0) as count FROM vue_files WHERE run_id = ? AND file_path LIKE '%.vue'",
            (run_id,)
        ).fetchone()["count"]
        
        # AI issues by severity
        ai_issues = conn.execute(
            """
            SELECT severity, COUNT(*) as count
            FROM ai_issues
            WHERE run_id = ? AND phase = 'file_analysis'
            GROUP BY severity
            """,
            (run_id,)
        ).fetchall()
        
        issues_by_severity = {"High": 0, "Medium": 0, "Low": 0}
        for row in ai_issues:
            severity = row["severity"] or "Low"
            if severity in issues_by_severity:
                issues_by_severity[severity] = row["count"]
        
        # Average complexity
        avg_complexity = conn.execute(
            """
            SELECT AVG(COALESCE(cyclomatic_complexity, 0)) as avg_complexity
            FROM vue_files
            WHERE run_id = ? AND file_path LIKE '%.vue'
            """,
            (run_id,)
        ).fetchone()["avg_complexity"] or 0
        
        # Total accessibility defects
        total_accessibility = conn.execute(
            "SELECT COUNT(*) as count FROM accessibility_defects WHERE run_id = ?",
            (run_id,)
        ).fetchone()["count"]
        
        conn.close()
        
        return jsonify({
            "run_id": run_id,
            "project_name": PROJECT_NAME,
            "total_files": total_files,
            "total_eslint_flags": total_eslint,
            "total_accessibility_defects": total_accessibility,
            "ai_issues_by_severity": issues_by_severity,
            "ai_issues_total": sum(issues_by_severity.values()),
            "average_complexity": round(avg_complexity, 2)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/worst-offenders", methods=["GET"])
def get_worst_offenders():
    """
    GET /api/worst-offenders?limit=10
    Returns top N files by composite score.
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        
        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify([])

        rows = conn.execute(
            """
            SELECT
                vf.file_path,
                vf.script_lines,
                vf.methods,
                vf.api_total,
                vf.api_in_loop,
                vf.max_nesting_depth,
                vf.cyclomatic_complexity,
                COALESCE(vf.eslint_flag_count, 0) as eslint_flag_count,
                COALESCE(ai.cnt, 0) as ai_issue_count,
                (COALESCE(vf.eslint_flag_count, 0) + 
                 COALESCE(ai.cnt, 0) + 
                 COALESCE(vf.api_in_loop, 0) * 2 +
                 COALESCE(vf.max_nesting_depth, 0)) as composite_score
            FROM vue_files vf
            LEFT JOIN (
                SELECT file_path, COUNT(*) as cnt
                FROM ai_issues
                WHERE run_id = ? AND phase = 'file_analysis'
                GROUP BY file_path
            ) ai ON ai.file_path = vf.file_path
            WHERE vf.run_id = ? AND vf.file_path LIKE '%.vue'
            ORDER BY composite_score DESC
            LIMIT ?
            """,
            (run_id, run_id, limit)
        ).fetchall()
        
        conn.close()
        
        offenders = [_row_to_dict(row) for row in rows]
        return jsonify(offenders)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/files", methods=["GET"])
def get_files():
    """
    GET /api/files
    Returns list of all scanned files with issue counts.
    """
    try:
        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify([])

        rows = conn.execute(
            """
            SELECT
                vf.file_path,
                vf.script_lines,
                vf.template_lines,
                COALESCE(vf.eslint_flag_count, 0) as eslint_flag_count,
                COALESCE(acc.cnt, 0) as accessibility_count,
                COALESCE(ai.cnt, 0) as ai_issue_count,
                COALESCE(ai.high_cnt, 0) as high_severity_count,
                COALESCE(ai.medium_cnt, 0) as medium_severity_count,
                COALESCE(ai.low_cnt, 0) as low_severity_count
            FROM vue_files vf
            LEFT JOIN (
                SELECT file_path, COUNT(*) as cnt
                FROM accessibility_defects
                WHERE run_id = ?
                GROUP BY file_path
            ) acc ON acc.file_path = vf.file_path
            LEFT JOIN (
                SELECT 
                    file_path,
                    COUNT(*) as cnt,
                    SUM(CASE WHEN severity = 'High' THEN 1 ELSE 0 END) as high_cnt,
                    SUM(CASE WHEN severity = 'Medium' THEN 1 ELSE 0 END) as medium_cnt,
                    SUM(CASE WHEN severity = 'Low' THEN 1 ELSE 0 END) as low_cnt
                FROM ai_issues
                WHERE run_id = ? AND phase = 'file_analysis'
                GROUP BY file_path
            ) ai ON ai.file_path = vf.file_path
            WHERE vf.run_id = ? AND vf.file_path LIKE '%.vue'
            ORDER BY vf.file_path
            """,
            (run_id, run_id, run_id)
        ).fetchall()
        
        conn.close()
        
        files = [_row_to_dict(row) for row in rows]
        return jsonify(files)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-metrics", methods=["GET"])
@app.route("/api/file-metrics/<path:file_path>", methods=["GET"])
def get_file_metrics(file_path: str = None):
    """
    GET /api/file-metrics/<path:file_path>
    Returns full metrics row for a file.
    """
    file_path = request.args.get("file_path") or file_path
    if not file_path:
        return jsonify({"error": "Missing file_path"}), 400
    file_path = file_path.replace("\\", "/")
    
    run_id_arg = request.args.get('run_id')
    try:
        run_id = int(run_id_arg) if run_id_arg else None
    except ValueError:
        run_id = None

    try:
        conn = _db_connect()
        if run_id is None:
            run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify({"error": "No audit runs found"}), 404
            
        file_path = _resolve_db_file_path(conn, run_id, file_path)

        row = conn.execute(
            """
            SELECT * FROM vue_files
            WHERE run_id = ? AND file_path = ?
            """,
            (run_id, file_path)
        ).fetchone()
        
        conn.close()
        
        if not row:
            return jsonify({"error": "File not found"}), 404
        
        return jsonify(_row_to_dict(row))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-api-calls", methods=["GET"])
@app.route("/api/file-api-calls/<path:file_path>", methods=["GET"])
def get_file_api_calls(file_path: str = None):
    """
    GET /api/file-api-calls/<path:file_path>
    Returns all API calls for a file with dynamically generated code snippets.
    """
    file_path = request.args.get("file_path") or file_path
    if not file_path:
        return jsonify({"error": "Missing file_path"}), 400
    file_path = file_path.replace("\\", "/")
    
    run_id_arg = request.args.get('run_id')
    try:
        run_id = int(run_id_arg) if run_id_arg else None
    except ValueError:
        run_id = None

    try:
        conn = _db_connect()
        if run_id is None:
            run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify([])
            
        file_path = _resolve_db_file_path(conn, run_id, file_path)

        rows = conn.execute(
            """
            SELECT id, file_path, api_type, method_name, endpoint,
                   in_mounted, in_loop, line_number
            FROM api_calls
            WHERE run_id = ? AND file_path = ?
            ORDER BY line_number
            """,
            (run_id, file_path)
        ).fetchall()

        conn.close()

        api_calls = []
        for row in rows:
            call = _row_to_dict(row)
            call["code_snippet"] = _extract_snippet(file_path, call.get("line_number", 0))
            api_calls.append(call)

        return jsonify(api_calls)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-accessibility", methods=["GET"])
@app.route("/api/file-accessibility/<path:file_path>", methods=["GET"])
def get_file_accessibility(file_path: str = None):
    """
    GET /api/file-accessibility/<path:file_path>
    Returns accessibility defects with WCAG metadata and code snippets.
    """
    file_path = request.args.get("file_path") or file_path
    if not file_path:
        return jsonify({"error": "Missing file_path"}), 400
    file_path = file_path.replace("\\", "/")
    
    run_id_arg = request.args.get('run_id')
    try:
        run_id = int(run_id_arg) if run_id_arg else None
    except ValueError:
        run_id = None

    try:
        conn = _db_connect()
        if run_id is None:
            run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify([])
            
        file_path = _resolve_db_file_path(conn, run_id, file_path)

        rows = conn.execute(
            """
            SELECT id, file_path, rule, message, wcag_criterion, wcag_level, line_number, column_number
            FROM accessibility_defects
            WHERE run_id = ? AND file_path = ?
            ORDER BY line_number
            """,
            (run_id, file_path)
        ).fetchall()

        conn.close()

        defects = []
        for row in rows:
            defect = _row_to_dict(row)
            rule = defect.get("rule", "")

            # Enrich with WCAG metadata if not already in DB
            if not defect.get("wcag_criterion"):
                metadata = WCAG_METADATA.get(rule, {
                    "criterion": "Unknown",
                    "level": "A",
                    "explanation": "No metadata available for this rule."
                })
                defect["wcag_criterion"] = metadata["criterion"]
                defect["wcag_level"] = metadata["level"]
                defect["wcag_explanation"] = metadata["explanation"]

            defect["code_snippet"] = _extract_snippet(file_path, defect.get("line_number", 0))
            defects.append(defect)

        return jsonify(defects)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-eslint", methods=["GET"])
@app.route("/api/file-eslint/<path:file_path>", methods=["GET"])
def get_file_eslint(file_path: str = None):
    """
    GET /api/file-eslint/<path:file_path>
    Returns ESLint flags (non-accessibility) with code snippets.
    """
    file_path = request.args.get("file_path") or file_path
    if not file_path:
        return jsonify({"error": "Missing file_path"}), 400
    file_path = file_path.replace("\\", "/")
    
    run_id_arg = request.args.get('run_id')
    try:
        run_id = int(run_id_arg) if run_id_arg else None
    except ValueError:
        run_id = None

    try:
        conn = _db_connect()
        if run_id is None:
            run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify([])
            
        file_path = _resolve_db_file_path(conn, run_id, file_path)

        rows = conn.execute(
            """
            SELECT id, file_path, category, rule, message, severity, line_number, column_number
            FROM file_flags
            WHERE run_id = ? AND file_path = ? AND category = 'eslint'
            ORDER BY line_number
            """,
            (run_id, file_path)
        ).fetchall()

        conn.close()

        flags = []
        for row in rows:
            flag = _row_to_dict(row)
            flag["code_snippet"] = _extract_snippet(file_path, flag.get("line_number", 0))
            flags.append(flag)

        return jsonify(flags)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file-ai-issues", methods=["GET"])
@app.route("/api/file-ai-issues/<path:file_path>", methods=["GET"])
def get_file_ai_issues(file_path: str = None):
    """
    GET /api/file-ai-issues/<path:file_path>
    Returns LLM-generated issues (code snippets already in database).
    """
    file_path = request.args.get("file_path") or file_path
    if not file_path:
        return jsonify({"error": "Missing file_path"}), 400
    file_path = file_path.replace("\\", "/")
    
    run_id_arg = request.args.get('run_id')
    try:
        run_id = int(run_id_arg) if run_id_arg else None
    except ValueError:
        run_id = None

    try:
        conn = _db_connect()
        if run_id is None:
            run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify([])
            
        file_path = _resolve_db_file_path(conn, run_id, file_path)

        rows = conn.execute(
            """
            SELECT id, file_path, phase, issue_category, title as issue_title,
                   description, severity, line_number, code_snippet, recommendation
            FROM ai_issues
            WHERE run_id = ? AND file_path = ? AND phase = 'file_analysis'
            ORDER BY severity DESC, line_number
            """,
            (run_id, file_path)
        ).fetchall()

        conn.close()

        return jsonify([_row_to_dict(row) for row in rows])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/executive-summary", methods=["GET"])
def get_executive_summary():
    """
    GET /api/executive-summary
    Returns the synthesis text from the most recent completed audit run.
    """
    try:
        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify({"error": "No audit runs found"}), 404

        row = conn.execute(
            "SELECT id, project_name, synthesis_text, completed_at FROM audit_runs WHERE id = ?",
            (run_id,)
        ).fetchone()

        conn.close()

        if not row or not row["synthesis_text"]:
            return jsonify({
                "synthesis_text": "No executive summary available. Run the full AI audit pipeline first.",
                "completed_at": None
            })

        return jsonify(_row_to_dict(row))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/run-status", methods=["GET"])
def get_run_status():
    """
    GET /api/run-status
    Returns status of the most recent audit run.
    """
    try:
        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify({"status": "no_runs", "message": "No audit runs found."})

        row = conn.execute(
            "SELECT id, project_name, status, started_at, completed_at, total_files, last_completed_file FROM audit_runs WHERE id = ?",
            (run_id,)
        ).fetchone()

        conn.close()

        if not row:
            return jsonify({"status": "no_runs", "message": "No audit runs found for this project."})

        return jsonify(_row_to_dict(row))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _get_dynamic_graph_data(conn: sqlite3.Connection, run_id: int) -> Optional[dict]:
    """Helper to reconstruct the dependency graph data dynamically from the database."""
    # Check if there are dependency metrics for this run_id
    count = conn.execute(
        "SELECT COUNT(*) as count FROM dependency_metrics WHERE run_id = ?", (run_id,)
    ).fetchone()["count"]
    
    if count == 0:
        return None
        
    rows = conn.execute(
        "SELECT * FROM dependency_metrics WHERE run_id = ?", (run_id,)
    ).fetchall()
    
    nodes = []
    orphans = []
    cycles = []
    seen_cycles = set()
    most_critical = None
    most_critical_in = 0
    max_impact_score = -1.0
    max_depth = 0
    
    for row in rows:
        file_path = row["file_path"]
        category = row["node_category"]
        in_deg = row["in_degree"]
        out_deg = row["out_degree"]
        depth = row["depth"]
        impact = row["impact_score"]
        is_cycle = bool(row["is_in_cycle"])
        
        nodes.append({
            "id": file_path,
            "category": category,
            "in_degree": in_deg,
            "out_degree": out_deg,
            "depth": depth,
            "impact_score": impact,
            "is_in_cycle": is_cycle
        })
        
        if category == "orphan":
            orphans.append(file_path)
            
        if is_cycle and row["cycle_members"]:
            try:
                members = json.loads(row["cycle_members"])
                if isinstance(members, list):
                    c_tuple = tuple(sorted(members))
                    if c_tuple not in seen_cycles:
                        seen_cycles.add(c_tuple)
                        cycles.append(members)
            except Exception:
                pass
                
        if depth > max_depth:
            max_depth = depth
            
        if impact > max_impact_score:
            max_impact_score = impact
            most_critical = file_path
            most_critical_in = in_deg
            
    edge_rows = conn.execute(
        "SELECT parent_file, child_file, relationship_type FROM component_relationships WHERE run_id = ?",
        (run_id,)
    ).fetchall()
    
    edges = []
    for er in edge_rows:
        edges.append({
            "source": er["parent_file"],
            "target": er["child_file"],
            "relationship_type": er["relationship_type"] or "utility"
        })
        
    summary = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "orphan_count": len(orphans),
        "cycle_count": len(cycles),
        "max_depth": max_depth,
        "most_critical_file": most_critical,
        "most_critical_file_in_degree": most_critical_in
    }
    
    return {
        "nodes": nodes,
        "edges": edges,
        "summary": summary,
        "cycles": cycles,
        "orphans": orphans
    }


@app.route("/api/dependency-graph", methods=["GET"])
def get_dependency_graph():
    """
    GET /api/dependency-graph?run_id=X
    Returns the dependency graph for a specific run_id from the database.
    If run_id is explicitly provided but has no graph data (graph phase didn't run),
    returns an empty graph — never falls back to another run's stale data.
    If no run_id is provided at all, falls back to static graph.json (legacy mode).
    """
    try:
        # Check if run_id was EXPLICITLY requested in the URL
        explicit_run_id = request.args.get("run_id")
        
        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)

        if run_id is not None:
            dynamic_data = _get_dynamic_graph_data(conn, run_id)
            conn.close()
            if dynamic_data:
                return jsonify(dynamic_data)
            elif explicit_run_id:
                # run_id was explicitly requested but has no graph data (graph phase skipped)
                # Return empty graph — do NOT fall back to another run's stale data
                return jsonify({
                    "nodes": [], "edges": [], "cycles": [], "orphans": [],
                    "summary": {
                        "total_nodes": 0, "total_edges": 0, "orphan_count": 0,
                        "cycle_count": 0, "max_depth": 0,
                        "most_critical_file": None, "most_critical_file_in_degree": 0,
                        "message": "No dependency graph was generated for this audit run. The graph phase may have been skipped."
                    }
                })
        else:
            conn.close()

        # Only fall back to static graph.json when no run_id was specified at all (legacy mode)
        graph_path = PROJECT_ROOT / "report" / "frontend" / "public" / "graph.json"
        if not graph_path.exists():
            return jsonify({"error": "graph.json not found"}), 404
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dependency-summary", methods=["GET"])
def get_dependency_summary():
    """
    GET /api/dependency-summary?run_id=X
    Returns only the summary block, dynamically resolved per run_id.
    Returns empty summary if run_id was explicitly given but has no graph data.
    """
    try:
        explicit_run_id = request.args.get("run_id")

        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)

        if run_id is not None:
            dynamic_data = _get_dynamic_graph_data(conn, run_id)
            conn.close()
            if dynamic_data:
                return jsonify(dynamic_data.get("summary", {}))
            elif explicit_run_id:
                return jsonify({
                    "total_nodes": 0, "total_edges": 0, "orphan_count": 0,
                    "cycle_count": 0, "max_depth": 0,
                    "most_critical_file": None, "most_critical_file_in_degree": 0,
                    "message": "No dependency graph was generated for this audit run."
                })
        else:
            conn.close()

        graph_path = PROJECT_ROOT / "report" / "frontend" / "public" / "graph.json"
        if not graph_path.exists():
            return jsonify({"error": "graph.json not found"}), 404
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data.get("summary", {}))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _is_vue_project(path: Path) -> bool:
    """Helper to check if a directory looks like a Vue/Node project."""
    return (path / "package.json").exists() or (path / "src").exists() or (path / "vite.config.js").exists()


def _resolve_project_path(input_path: str) -> str:
    """
    Smart-resolves a directory path if it is relative or selected via web browser folder picker.
    Examines known base directories (Desktop, Users, Home) up to 2 levels deep to find matches,
    and handles double-nested structures (e.g. StudentManagement/StudentManagement) automatically.
    """
    if not input_path:
        return input_path
        
    norm_path = input_path.replace("\\", "/")
    
    # 1. If it's absolute or exists directly, return it
    try:
        p = Path(norm_path)
        if p.exists() and p.is_dir():
            # Check for double nested folder matching same name with Vue structure
            nested = p / p.name
            if nested.exists() and nested.is_dir() and _is_vue_project(nested):
                return str(nested.resolve())
            return str(p.resolve())
    except Exception:
        pass
        
    # 2. Try relative to known base directories
    base_dirs = []
    if PROJECT_ROOT:
        base_dirs.append(PROJECT_ROOT.parent)
        base_dirs.append(PROJECT_ROOT.parent.parent)
    try:
        base_dirs.append(Path.home())
        base_dirs.append(Path.home() / "Desktop")
    except Exception:
        pass
        
    seen = set()
    unique_base_dirs = []
    for d in base_dirs:
        try:
            d_resolved = d.resolve()
            if d_resolved.exists() and d_resolved.is_dir() and d_resolved not in seen:
                seen.add(d_resolved)
                unique_base_dirs.append(d_resolved)
        except Exception:
            continue
            
    norm_path_parts = [part for part in norm_path.split("/") if part]
    if not norm_path_parts:
        return input_path
        
    target_leaf = norm_path_parts[-1]
    
    # Prioritize exact path joins on candidates
    for base in unique_base_dirs:
        candidate = base / norm_path
        if candidate.exists() and candidate.is_dir():
            nested = candidate / candidate.name
            if nested.exists() and nested.is_dir() and _is_vue_project(nested):
                return str(nested.resolve())
            return str(candidate.resolve())
            
    # Fallback to searching subdirectories up to 2 levels deep
    for base in unique_base_dirs:
        try:
            for child in base.iterdir():
                if child.is_dir():
                    # Skip system/hidden folders
                    if child.name.startswith('.'):
                        continue
                    
                    # Direct check child/input_path
                    candidate = child / norm_path
                    if candidate.exists() and candidate.is_dir():
                        nested = candidate / candidate.name
                        if nested.exists() and nested.is_dir() and _is_vue_project(nested):
                            return str(nested.resolve())
                        return str(candidate.resolve())
                        
                    # Check child name match
                    if child.name.lower() == target_leaf.lower():
                        nested = child / child.name
                        if nested.exists() and nested.is_dir() and _is_vue_project(nested):
                            return str(nested.resolve())
                        return str(child.resolve())
                        
                    # Grandchild check
                    try:
                        for grandchild in child.iterdir():
                            if grandchild.is_dir():
                                if grandchild.name.startswith('.'):
                                    continue
                                candidate = grandchild / norm_path
                                if candidate.exists() and candidate.is_dir():
                                    nested = candidate / candidate.name
                                    if nested.exists() and nested.is_dir() and _is_vue_project(nested):
                                        return str(nested.resolve())
                                    return str(candidate.resolve())
                                if grandchild.name.lower() == target_leaf.lower():
                                    nested = grandchild / grandchild.name
                                    if nested.exists() and nested.is_dir() and _is_vue_project(nested):
                                        return str(nested.resolve())
                                    return str(grandchild.resolve())
                    except Exception:
                        continue
        except Exception:
            continue
            
    return input_path


@app.route("/api/scan", methods=["POST"])
def scan_project():
    """
    POST /api/scan
    Executes the main analysis pipeline (run_audit.py) on the given path.
    Body: { "path": "/absolute/path/to/project" }
    """
    global active_scan_process
    try:
        data = request.json
        if not data or "path" not in data:
            logger.error("Scan API called with missing 'path' in body.")
            return jsonify({"error": "Missing 'path' in request body"}), 400
        
        project_path = data["path"]
        logger.info(f"Received scan request for path: {project_path}")
        
        # Smart path resolution for web browsers selecting relative folders
        resolved_path = _resolve_project_path(project_path)
        logger.info(f"Smart resolved path '{project_path}' to: '{resolved_path}'")
        
        if not os.path.exists(resolved_path):
            logger.error(f"Resolved path does not exist: {resolved_path}")
            return jsonify({"error": f"Path does not exist: {resolved_path}"}), 400

        # Update project_config.yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            
        config["base_path"] = resolved_path
        config["project_name"] = os.path.basename(os.path.normpath(resolved_path))
        
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, sort_keys=False)

        # Run the pipeline
        run_audit_script = PROJECT_ROOT / "audit_tool" / "run_audit.py"
        python_exe = PROJECT_ROOT / "audit_tool" / "venv" / "Scripts" / "python.exe"
        
        # Determine python executable to use
        exe = str(python_exe) if python_exe.exists() else sys.executable
        
        logger.info(f"Executing pipeline: {exe} {run_audit_script} --no-report")
        
        with active_scan_lock:
            # Check if another process is active
            if active_scan_process is not None and active_scan_process.poll() is None:
                return jsonify({"error": "Another scan is already in progress"}), 400
                
            # Spawn process using subprocess.Popen, redirecting stderr to stdout to stream all messages
            active_scan_process = subprocess.Popen(
                [exe, str(run_audit_script), "--no-report"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(PROJECT_ROOT),
                bufsize=1
            )

        def generate_logs():
            global active_scan_process
            try:
                # Read stdout line by line in real-time
                for line in iter(active_scan_process.stdout.readline, ''):
                    yield line
                
                active_scan_process.stdout.close()
                returncode = active_scan_process.wait()
                
                if returncode == 0:
                    logger.info("Pipeline execution completed successfully.")
                    yield "\n[API_SERVER] Analysis complete!\n"
                elif returncode in [-9, 9, 15, -15]:
                    logger.info("Pipeline execution was cancelled by the user.")
                    yield "\n[API_SERVER] Scan cancelled by the user.\n"
                else:
                    logger.error(f"Pipeline execution finished with exit code {returncode}")
                    yield f"\n[API_SERVER] Analysis failed with exit code {returncode}.\n"
            except Exception as e:
                logger.error(f"Error in scan streaming: {e}")
                yield f"\n[API_SERVER] Error: {str(e)}\n"
            finally:
                with active_scan_lock:
                    active_scan_process = None

        return app.response_class(generate_logs(), mimetype="text/plain")
            
    except Exception as e:
        logger.exception("An unexpected error occurred during scan execution.")
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan/cancel", methods=["POST"])
def cancel_scan():
    """
    POST /api/scan/cancel
    Cancels the active scan subprocess and purges any temporary 'in_progress' database rows.
    """
    global active_scan_process
    try:
        with active_scan_lock:
            if active_scan_process is not None and active_scan_process.poll() is None:
                logger.info("Cancelling active scan subprocess...")
                active_scan_process.kill()  # Force kill the process
                active_scan_process = None
                
                # Perform DB purge of in_progress runs
                _cleanup_in_progress_runs()
                
                return jsonify({"status": "cancelled", "message": "Scan cancelled successfully and partial database results deleted."}), 200
            else:
                # Defensively clear out any stranded runs with status 'in_progress'
                _cleanup_in_progress_runs()
                return jsonify({"status": "idle", "message": "No active scan was running, but database was verified and cleared."}), 200
    except Exception as e:
        logger.exception("Error during scan cancellation:")
        return jsonify({"error": str(e)}), 500


def get_transitive_dependents(run_id: int, file_path: str) -> list:
    """Helper to compute transitive dependents dynamically via BFS on component_relationships"""
    conn = _db_connect()
    rows = conn.execute("SELECT parent_file, child_file FROM component_relationships WHERE run_id = ?", (run_id,)).fetchall()
    conn.close()
    
    # build reverse adjacency list (child -> list of parents)
    adj = {}
    for r in rows:
        p, c = r["parent_file"], r["child_file"]
        if c not in adj:
            adj[c] = []
        adj[c].append(p)
        
    visited = set()
    queue = [file_path]
    while queue:
        curr = queue.pop(0)
        for p in adj.get(curr, []):
            if p not in visited:
                visited.add(p)
                queue.append(p)
    return list(visited)


@app.route("/api/file-dependencies", methods=["GET"])
@app.route("/api/file-dependencies/<path:file_path>", methods=["GET"])
def get_file_dependencies(file_path: str = None):
    """
    GET /api/file-dependencies/<path:file_path>
    Returns dependency metrics for one specific file, including transitive impact.
    """
    file_path = request.args.get("file_path") or file_path
    if not file_path:
        return jsonify({"error": "Missing file_path"}), 400
    file_path = file_path.replace("\\", "/")
    
    run_id_arg = request.args.get('run_id')
    try:
        run_id = int(run_id_arg) if run_id_arg else None
    except ValueError:
        run_id = None

    try:
        conn = _db_connect()
        if run_id is None:
            run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify({"error": "No audit runs found"}), 404
            
        file_path = _resolve_db_file_path(conn, run_id, file_path)

        row = conn.execute(
            """
            SELECT * FROM vue_files
            WHERE run_id = ? AND file_path = ?
            """,
            (run_id, file_path)
        ).fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "File not found in dependency metrics"}), 404
            
        data = _row_to_dict(row)
        
        # Format exactly as requested
        result = {
            "file_path": data["file_path"],
            "category": data["node_category"],
            "in_degree": data["in_degree"],
            "out_degree": data["out_degree"],
            "impact_score": data["impact_score"],
            "is_in_cycle": bool(data["is_in_cycle"]),
            "dependencies": json.loads(data["dependencies"] or "[]"),
            "dependents": json.loads(data["dependents"] or "[]"),
            "transitive_impact": get_transitive_dependents(run_id, data["file_path"]),
            "cycle": json.loads(data["cycle_members"] or "[]") if data["is_in_cycle"] else None
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orphans", methods=["GET"])
def get_orphans():
    """
    GET /api/orphans
    Returns list of all files that have no parent component (in_degree = 0, out_degree > 0).
    """
    try:
        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)
        if run_id is None:
            return jsonify([])

        rows = conn.execute(
            """
            SELECT file_path, script_lines, template_lines,
                   COALESCE(eslint_flag_count, 0) as eslint_flag_count
            FROM vue_files
            WHERE run_id = ?
              AND file_path NOT IN (
                  SELECT DISTINCT child_file FROM component_relationships WHERE run_id = ?
              )
            ORDER BY file_path
            """,
            (run_id, run_id)
        ).fetchall()
        conn.close()

        return jsonify([_row_to_dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cycles", methods=["GET"])
def get_cycles():
    """
    GET /api/cycles?run_id=X
    Returns all detected cycles, dynamically resolved per run_id.
    Returns empty list if run_id was explicitly given but has no graph data.
    """
    try:
        explicit_run_id = request.args.get("run_id")

        conn = _db_connect()
        run_id = _get_run_id(conn, PROJECT_NAME)

        if run_id is not None:
            dynamic_data = _get_dynamic_graph_data(conn, run_id)
            conn.close()
            if dynamic_data:
                return jsonify(dynamic_data.get("cycles", []))
            elif explicit_run_id:
                # Explicitly requested run has no graph data — return empty, not stale data
                return jsonify([])
        else:
            conn.close()

        graph_path = PROJECT_ROOT / "report" / "frontend" / "public" / "graph.json"
        if not graph_path.exists():
            return jsonify([])
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data.get("cycles", []))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _load_env_file():
    """Safely load key-value pairs from .env into os.environ."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            k, v = line.split("=", 1)
                            os.environ[k.strip()] = v.strip()
            logger.info("Successfully loaded environment configuration from workspace .env file.")
        except Exception as e:
            logger.error(f"Error loading environment file: {e}")


def _resolve_base_url(base_url: str) -> str:
    if not base_url:
        raise ValueError("OPENWEBUI_BASE_URL is required")
    # Return as-is if already ends with /api/v1 or /openai/v1 (Groq format)
    if base_url.endswith("/api/v1") or base_url.endswith("/openai/v1"):
        return base_url
    # Convert /v1 to /api/v1 for OpenWebUI/Ollama compatibility
    if base_url.endswith("/v1"):
        return base_url[: -len("/v1")] + "/api/v1"
    return base_url.rstrip("/") + "/api/v1"


def _assemble_chat_context(conn: sqlite3.Connection, run_id: int, message: str):
    """
    Dynamically compile context from database tables based on run_id and case-insensitive keywords in message.
    Returns a tuple of (context_str, sources_list) where sources_list documents which DB tables were queried.
    """
    # --- Source citation tracker: appended for each triggered query branch ---
    sources = []

    # 1. Always Fetch: General audit run stats
    run_row = conn.execute(
        "SELECT id, project_name, started_at, status, completed_at, total_files, synthesis_text FROM audit_runs WHERE id = ?",
        (run_id,)
    ).fetchone()
    
    if not run_row:
        return "No audit run details found for this run_id.", []
        
    proj_name = run_row["project_name"]
    started_at = run_row["started_at"]
    completed_at = run_row["completed_at"]
    total_files = run_row["total_files"]
    
    # Query summary counts
    eslint_flag_count = conn.execute(
        "SELECT COALESCE(SUM(eslint_flag_count), 0) as count FROM vue_files WHERE run_id = ?",
        (run_id,)
    ).fetchone()["count"]
    
    accessibility_flag_count = conn.execute(
        "SELECT COUNT(*) as count FROM accessibility_defects WHERE run_id = ?",
        (run_id,)
    ).fetchone()["count"]
    
    ai_issue_count = conn.execute(
        "SELECT COUNT(*) as count FROM ai_issues WHERE run_id = ? AND phase = 'file_analysis'",
        (run_id,)
    ).fetchone()["count"]

    # Core tables are always queried
    sources.append("Table: audit_runs (Run Metadata & Status)")
    sources.append("Table: vue_files (Aggregate ESLint Flag Counts)")
    sources.append("Table: accessibility_defects (Aggregate WCAG Defect Counts)")
    sources.append("Table: ai_issues (Aggregate AI Issue Counts)")
    
    context_parts = [
        f"CURRENT ACTIVE VIEW CONTEXT: The user is looking at audit run ID: {run_id}. Project name: {proj_name}, analyzed on {started_at}.",
        "",
        "=== CORE AUDIT RUN DETAILS (Always Fetched) ===",
        f"Run ID: {run_id}",
        f"Project Name: {proj_name}",
        f"Started At: {started_at}",
        f"Completed At: {completed_at}",
        f"Total Scanned Files: {total_files}",
        "Aggregate Issue Metrics:",
        f"  - Total ESLint Flags: {eslint_flag_count}",
        f"  - Total Accessibility (WCAG) Defects: {accessibility_flag_count}",
        f"  - Total AI Code Quality Issues: {ai_issue_count}",
        ""
    ]
    
    message_lower = message.lower()
    
    # 2. File mentions: Search for words matching custom components
    # Gather all file paths in this run
    all_files_rows = conn.execute(
        "SELECT file_path FROM vue_files WHERE run_id = ?",
        (run_id,)
    ).fetchall()
    file_paths = [r["file_path"] for r in all_files_rows]
    
    extracted_words = []
    # Scan for expressions containing explicit extensions (e.g. '.vue', '.js', '.ts')
    words = re.findall(r'[\w\.\-/]+', message_lower)
    has_ext = False
    for w in words:
        if any(ext in w for ext in ('.vue', '.js', '.ts')):
            has_ext = True
            cleaned_w = w.strip("./- ")
            if cleaned_w:
                extracted_words.append(cleaned_w)
                
    # If no exact extension is found, check if any unique alphanumeric words longer than 3 characters match
    if not has_ext:
        raw_words = re.findall(r'[a-zA-Z0-9]{4,}', message_lower)
        for rw in raw_words:
            for fp in file_paths:
                filename_lower = os.path.basename(fp).lower()
                if rw in filename_lower or rw in fp.lower():
                    if rw not in extracted_words:
                        extracted_words.append(rw)
                        
    # Execute database lookup using wildcard approach
    matched_files = []
    seen_paths = set()
    for clean_name in extracted_words:
        file_rows = conn.execute(
            """
            SELECT file_path, script_lines, template_lines, eslint_flag_count, cyclomatic_complexity 
            FROM vue_files 
            WHERE run_id = ? AND LOWER(file_path) LIKE ?
            """,
            (run_id, f"%{clean_name}%")
        ).fetchall()
        
        for row in file_rows:
            fp = row["file_path"]
            if fp not in seen_paths:
                seen_paths.add(fp)
                matched_files.append(row)
            
    if matched_files:
        sources.append("Table: vue_files (Targeted File Data Scan)")
        sources.append("Table: file_flags (ESLint Flags per Mentioned File)")
        sources.append("Table: accessibility_defects (WCAG Defects per Mentioned File)")
        sources.append("Table: ai_issues (AI Issues per Mentioned File)")
        context_parts.append("=== SPECIFIC FILE DETAILS (Triggered by File Mentions) ===")
        for f in matched_files:
            fp = f["file_path"]
            context_parts.extend([
                f"File: {fp}",
                f"  - Script Lines: {f['script_lines']}",
                f"  - Template Lines: {f['template_lines']}",
                f"  - Cyclomatic Complexity: {f['cyclomatic_complexity']}",
                f"  - ESLint Flags Count: {f['eslint_flag_count']}"
            ])
            
            # Fetch ESLint flags for this file
            flags = conn.execute(
                "SELECT rule, message, line_number FROM file_flags WHERE run_id = ? AND file_path = ? AND category = 'eslint' LIMIT 5",
                (run_id, fp)
            ).fetchall()
            if flags:
                context_parts.append("  - Sample ESLint Flags:")
                for fl in flags:
                    context_parts.append(f"    * Line {fl['line_number']}: [{fl['rule']}] {fl['message']}")
            
            # Fetch Accessibility defects for this file
            acc = conn.execute(
                "SELECT rule, message, line_number FROM accessibility_defects WHERE run_id = ? AND file_path = ? LIMIT 5",
                (run_id, fp)
            ).fetchall()
            if acc:
                context_parts.append("  - Sample Accessibility Defects:")
                for ac in acc:
                    context_parts.append(f"    * Line {ac['line_number']}: [{ac['rule']}] {ac['message']}")
                    
            # Fetch AI issues for this file
            ai_issues = conn.execute(
                "SELECT issue_category, title, description, severity, line_number FROM ai_issues WHERE run_id = ? AND file_path = ? AND phase = 'file_analysis' LIMIT 5",
                (run_id, fp)
            ).fetchall()
            if ai_issues:
                context_parts.append("  - Sample AI Issues:")
                for ai in ai_issues:
                    context_parts.append(f"    * Line {ai['line_number']} [{ai['severity']}]: {ai['title']} - {ai['description']}")
            context_parts.append("")
            
    # 3. Severity/Worst metrics: Triggered by keywords: 'worst', 'most', 'high', 'critical'
    worst_keywords = ["worst", "most", "high", "critical"]
    worst_triggered = any(kw in message_lower for kw in worst_keywords)
    
    if worst_triggered:
        sources.append("Table: vue_files (Worst Offenders by Composite Score)")
        sources.append("Table: ai_issues (Critical & High Severity Ranking)")
        context_parts.append("=== WORST OFFENDERS & CRITICAL RISKS (Triggered by Severity Keywords) ===")
        # Top 5 worst offenders in vue_files (highest ESLint flags or complexity)
        worst_files = conn.execute(
            """
            SELECT file_path, eslint_flag_count, cyclomatic_complexity, max_nesting_depth
            FROM vue_files
            WHERE run_id = ?
            ORDER BY (COALESCE(eslint_flag_count, 0) + COALESCE(cyclomatic_complexity, 0)) DESC
            LIMIT 5
            """,
            (run_id,)
        ).fetchall()
        
        context_parts.append("Top 5 Worst Code Files:")
        for idx, wf in enumerate(worst_files, 1):
            context_parts.append(f"  {idx}. {wf['file_path']} (ESLint Flags: {wf['eslint_flag_count']}, Complexity: {wf['cyclomatic_complexity']}, Max Nesting Depth: {wf['max_nesting_depth']})")
            
        # Top 5 critical/high severity AI issues
        critical_ai = conn.execute(
            """
            SELECT file_path, issue_category, title, severity, line_number
            FROM ai_issues
            WHERE run_id = ? AND severity IN ('High', 'Medium') AND phase = 'file_analysis'
            ORDER BY CASE severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
            LIMIT 5
            """,
            (run_id,)
        ).fetchall()
        
        if critical_ai:
            context_parts.append("\nTop Critical/High AI Issues:")
            for idx, ca in enumerate(critical_ai, 1):
                context_parts.append(f"  {idx}. {ca['file_path']} [Line {ca['line_number']}] [{ca['severity']} - {ca['issue_category']}]: {ca['title']}")
        context_parts.append("")
        
    # 4. Fallback context: Pull executive summary if no exact keywords match
    if not matched_files and not worst_triggered:
        sources.append("Table: audit_runs (Executive Synthesis Summary)")
        context_parts.append("=== HIGH-LEVEL EXECUTIVE SUMMARY (Fallback Context) ===")
        synthesis_text = run_row["synthesis_text"]
        if synthesis_text:
            context_parts.append(synthesis_text)
        else:
            context_parts.append("No executive synthesis was generated for this audit run yet.")
        context_parts.append("")

    logger.info(f"Chat context assembled. Active source citations: {sources}")
    return "\n".join(context_parts), sources


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    POST /api/chat
    Streams chatbot completions using Server-Sent Events (SSE).
    Payload: { "run_id": int, "message": str, "history": List[dict] }
    """
    try:
        data = request.get_json(silent=True)
        logger.info(f"Incoming Chat Request Payload: {data}")
        if not data:
            logger.error("Chat API called with empty or invalid JSON payload.")
            return jsonify({"error": "Invalid JSON payload"}), 400
            
        run_id = data.get("run_id")
        message = data.get("message")
        history = data.get("history", [])
        
        if run_id is None or message is None:
            logger.error("Chat API missing required fields 'run_id' or 'message'.")
            return jsonify({"error": "Missing 'run_id' or 'message' in payload"}), 400
            
        try:
            run_id = int(run_id)
        except ValueError:
            logger.error(f"Chat API received invalid non-integer run_id: {run_id}")
            return jsonify({"error": "run_id must be an integer"}), 400
            
        # Limit history to the last 6 items (rolling history limit of max 3 turns)
        history = history[-6:]
        
        # Pull facts from the local database
        conn = _db_connect()
        
        # Fallback to the latest run ID if run_id is 0 or None
        if not run_id:
            resolved_id = _get_run_id(conn, PROJECT_NAME)
            if resolved_id is not None:
                run_id = resolved_id
        try:
            context, sources = _assemble_chat_context(conn, run_id, message)
        finally:
            conn.close()
            
        # Load environment configuration
        _load_env_file()
        
        raw_base_url = os.getenv("OPENWEBUI_BASE_URL", "")
        api_key = os.getenv("OPENWEBUI_API_KEY", "")
        model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        timeout_val = os.getenv("LLM_TIMEOUT_SECONDS", "120")
        
        try:
            timeout = int(timeout_val)
        except ValueError:
            timeout = 120
            
        if not raw_base_url:
            logger.error("OPENWEBUI_BASE_URL is not configured in the environment.")
            return jsonify({"error": "OPENWEBUI_BASE_URL environment variable is not configured"}), 500
            
        resolved_base_url = _resolve_base_url(raw_base_url)
        url = f"{resolved_base_url}/chat/completions"
        
        # Build LLM Messages payload
        system_prompt = (
            "You are the Expert Code Audit Librarian Assistant, a specialized chatbot designed to answer questions "
            "about the static analysis and AI audit metrics of the loaded codebase. "
            "Below is the verified context and metrics pulled directly from our local database for this specific audit run:\n\n"
            f"{context}\n\n"
            "STRICT CONSTRAINTS:\n"
            "- Answer questions strictly using the injected database metrics.\n"
            "- Do not invent or guess information.\n"
            "- If data is omitted or unknown, explicitly state that the context lacks these metrics.\n"
            "- Guardrail: If the question is completely unrelated to the audit findings or metrics, "
            "you MUST output exactly: \"I can only answer questions about this audit.\" and say nothing else."
        )
        
        llm_messages = [{"role": "system", "content": system_prompt}]
        
        # Enforce history role consistency and append history
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("system", "user", "assistant") and content:
                llm_messages.append({"role": role, "content": content})
                
        # Append the new user message
        llm_messages.append({"role": "user", "content": message})
        
        # Build outbound streaming request
        post_data = {
            "model": model,
            "messages": llm_messages,
            "stream": True,
            "temperature": 0.2
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

            
        logger.info(f"Initiating streaming chat completions request to LLM URL: {url} with model: {model}")
        
        req = urllib.request.Request(
            url,
            data=json.dumps(post_data).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        def stream_generator():
            # Dispatch source citations meta-event as the very first SSE frame
            yield f"data: {json.dumps({'sources': sources})}\n\n"
            logger.info(f"SSE sources meta-event dispatched with {len(sources)} citation(s).")
            try:
                # Direct streaming read from urllib standard library
                response = urllib.request.urlopen(req, timeout=timeout)
                for line in response:
                    line_decoded = line.decode("utf-8").strip()
                    if not line_decoded:
                        continue
                    if line_decoded.startswith("data:"):
                        data_part = line_decoded[5:].strip()
                        if data_part == "[DONE]":
                            break
                        try:
                            data_json = json.loads(data_part)
                            choices = data_json.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    yield f"data: {json.dumps({'token': token})}\n\n"
                        except Exception as e:
                            logger.error(f"Error parsing SSE chunk: {line_decoded} - Error: {e}")
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8")
                except Exception:
                    pass
                logger.error(f"HTTPError connecting to LLM endpoint: Status {e.code} - {e.reason} - Body: {err_body}")
                yield f"data: {json.dumps({'error': f'LLM API HTTP Error: {e.code} - {e.reason}'})}\n\n"
            except Exception as e:
                logger.exception(f"Unexpected connection or streaming failure in chat completion endpoint: {e}")
                yield f"data: {json.dumps({'error': f'Unexpected streaming exception: {str(e)}'})}\n\n"
            finally:
                yield "data: [DONE]\n\n"
                logger.info("Streaming chatbot completed response.")
                
        return app.response_class(stream_generator(), mimetype="text/event-stream")
        
    except Exception as e:
        logger.exception("An unexpected error occurred during chat endpoint initialization.")
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "project_name": PROJECT_NAME,
        "database": str(DB_PATH),
        "database_exists": DB_PATH.exists()
    })


def _sanitize_llm_code(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    blocks = re.findall(r"```[a-zA-Z0-9_-]*\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if not blocks:
        blocks = re.findall(r"```[a-zA-Z0-9_-]*\s*(.*?)\s*```", text, re.DOTALL)

    if blocks:
        best_block = ""
        best_score = -1
        for block in blocks:
            lines = block.splitlines()
            cleaned = "\n".join(_strip_non_code_lines(lines))
            score = len(cleaned)
            if score > best_score:
                best_score = score
                best_block = cleaned
        if best_block:
            return best_block

    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.endswith("```"):
            continue
        cleaned_lines.append(line)

    cleaned_lines = _strip_non_code_lines(cleaned_lines)
    return "\n".join(cleaned_lines).strip()


def _validate_syntax(file_path: str, code_content: str) -> tuple[bool, str]:
    suffix = Path(file_path).suffix.lower()
    
    try:
        from tree_sitter import Parser
        from tree_sitter_language_pack import get_language
        
        lang_name = 'vue' if suffix == '.vue' else ('javascript' if suffix in ['.js', '.jsx'] else 'typescript' if suffix in ['.ts', '.tsx'] else None)
        if not lang_name:
            raise ValueError(f"Unsupported suffix for tree-sitter: {suffix}")
            
        lang = get_language(lang_name)
        parser = Parser(lang)
        tree = parser.parse(code_content.encode("utf-8"))
        
        if tree.root_node is None:
            return False, "Parser produced None root node"
            
        if tree.root_node.type == "ERROR":
            return False, f"Catastrophic parsing error at root: tree-sitter {lang_name}"
            
        # Vue tag-balance safeguard (even if tree-sitter parses successfully)
        if suffix == '.vue':
            tags = ['template', 'script', 'style']
            for tag in tags:
                open_tag = f"<{tag}"
                close_tag = f"</{tag}>"
                open_count = code_content.lower().count(open_tag)
                close_count = code_content.lower().count(close_tag)
                if open_count != close_count:
                    return False, f"Mismatched tag counts for <{tag}>: {open_count} open vs {close_count} close"
        elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
            if tree.root_node.has_error:
                return False, f"Syntax errors detected in tree-sitter {lang_name} AST"
            
        return True, f"Syntax validated via Tree-sitter ({lang_name})"
        
    except (ImportError, Exception) as e:
        logger.warning(f"Tree-sitter unavailable or failed; falling back to lightweight syntax check: {e}")
        
        if suffix == '.vue':
            tags = ['template', 'script', 'style']
            for tag in tags:
                open_tag = f"<{tag}"
                close_tag = f"</{tag}>"
                open_count = code_content.lower().count(open_tag)
                close_count = code_content.lower().count(close_tag)
                if open_count != close_count:
                    return False, f"Mismatched tag counts for <{tag}>: {open_count} open vs {close_count} close"
            return True, "Syntax validated via lightweight layout checker (Vue tags balanced)"
        else:
            braces = 0
            parens = 0
            brackets = 0
            for char in code_content:
                if char == '{': braces += 1
                elif char == '}': braces -= 1
                elif char == '(': parens += 1
                elif char == ')': parens -= 1
                elif char == '[': brackets += 1
                elif char == ']': brackets -= 1
                
                if braces < 0 or parens < 0 or brackets < 0:
                    return False, "Unbalanced braces, parentheses, or brackets detected early"
            
            if braces != 0 or parens != 0 or brackets != 0:
                return False, f"Unbalanced braces ({braces}), parentheses ({parens}), or brackets ({brackets})"
                
            return True, "Syntax validated via lightweight layout checker (braces/brackets balanced)"


# ─── Deterministic Fix Engine ────────────────────────────────────────────────

def _try_deterministic_fix(file_lines, issue_line, issue_type, issue_message,
                           code_snippet, recommendation, file_path_str):
    """
    For well-known issue patterns, apply a surgical deterministic fix.
    Returns a dict with fix details, or None if no handler matches.
    """
    combined_text = f"{issue_type} {issue_message} {recommendation}".lower()

    # Pattern 1: Multi-word component names (vue/multi-word-component-names)
    if "multi-word" in combined_text and ("component" in combined_text or "name" in combined_text):
        result = _fix_multi_word_component(file_lines, issue_line, issue_type, issue_message, file_path_str)
        if result:
            return result

    # Pattern 2: Click events must have key events
    if "click" in combined_text and "key" in combined_text and "event" in combined_text:
        result = _fix_click_missing_key_event(file_lines, issue_line)
        if result:
            return result

    return None


def _fix_multi_word_component(file_lines, issue_line, issue_type, issue_message, file_path_str):
    """
    Deterministic fix for vue/multi-word-component-names.
    Renames single-word component name by prepending 'App'.
    Handles: name: "Header", name: '', and missing name fields.
    """
    combined = f"{issue_type} {issue_message}"

    # Step 1: Extract the expected component name from the issue text
    expected_name = None
    m = re.search(r'[\u201c\u201d"\u2018\u2019\'`](\w+)[\u201c\u201d"\u2018\u2019\'`]', combined)
    if m:
        expected_name = m.group(1)

    # If we can't determine the name from the issue, derive from filename
    if not expected_name:
        filename = os.path.basename(file_path_str)
        if filename.endswith('.vue'):
            expected_name = filename[:-4]  # "Header.vue" → "Header"

    if not expected_name:
        logger.warning("[DETERMINISTIC FIX] Could not determine component name")
        return None

    # Skip if already multi-word
    if re.search(r'[a-z][A-Z]', expected_name) or '-' in expected_name or '_' in expected_name:
        logger.info(f"[DETERMINISTIC FIX] '{expected_name}' is already multi-word, skipping")
        return None

    new_name = "App" + expected_name

    # Step 2: Find the name: declaration in the code
    # Search the entire file for `name:` patterns in the script section
    fixed_lines = list(file_lines)
    changed = False
    target_line_idx = None

    # Priority 1: Search near the issue line (±15 lines)
    search_ranges = [
        (max(0, issue_line - 15), min(len(file_lines), issue_line + 15)),
        (0, len(file_lines)),  # Fallback: entire file
    ]

    for search_start, search_end in search_ranges:
        if changed:
            break
        for i in range(search_start, search_end):
            line = file_lines[i]

            # Case A: name: "Header" or name: 'Header' (non-empty, matches expected)
            m = re.search(r'''(name\s*:\s*['"])''' + re.escape(expected_name) + r'''(['"])''', line)
            if m:
                new_line = re.sub(
                    r'''(name\s*:\s*['"])''' + re.escape(expected_name) + r'''(['"])''',
                    r'\g<1>' + new_name + r'\g<2>',
                    line
                )
                if new_line != line:
                    fixed_lines[i] = new_line
                    target_line_idx = i
                    changed = True
                    break

            # Case B: name: "" or name: '' (empty name — inject the correct name)
            m_empty = re.search(r'''(name\s*:\s*)(['"])(['"])''', line)
            if m_empty:
                quote = m_empty.group(2)
                new_line = re.sub(
                    r'''(name\s*:\s*)(['"])(['"])''',
                    r'\g<1>' + quote + new_name + quote,
                    line
                )
                if new_line != line:
                    fixed_lines[i] = new_line
                    target_line_idx = i
                    changed = True
                    break

            # Case C: name: "SomeOtherSingleWord" (any single-word name on a name: line)
            m_any = re.search(r'''name\s*:\s*['"](\w+)['"]''', line)
            if m_any:
                current_name = m_any.group(1)
                # Only fix if it's a single-word name (no camelCase)
                if not re.search(r'[a-z][A-Z]', current_name) and '-' not in current_name and '_' not in current_name:
                    fix_name = "App" + current_name
                    new_line = re.sub(
                        r'''(name\s*:\s*['"])''' + re.escape(current_name) + r'''(['"])''',
                        r'\g<1>' + fix_name + r'\g<2>',
                        line
                    )
                    if new_line != line:
                        fixed_lines[i] = new_line
                        target_line_idx = i
                        new_name = fix_name  # Update for the response
                        changed = True
                        break

    if not changed:
        # Case D: No name: field at all — try to add one after "export default {"
        for i in range(len(file_lines)):
            if re.search(r'export\s+default\s*\{', file_lines[i]):
                line_ending = "\r\n" if file_lines[i].endswith("\r\n") else "\n"
                indent = "  "
                m_indent = re.match(r'^(\s*)', file_lines[i])
                if m_indent:
                    indent = m_indent.group(1) + "  "
                name_line = f'{indent}name: "{new_name}",{line_ending}'
                fixed_lines.insert(i + 1, name_line)
                target_line_idx = i + 1
                changed = True
                break

    if not changed:
        logger.warning(f"[DETERMINISTIC FIX] Could not apply fix for component name in {file_path_str}")
        return None

    # Step 3: Find connected references in other files
    connected = _find_component_references(expected_name, file_path_str)

    warnings = [
        f"Component renamed: '{expected_name}' -> '{new_name}' (deterministic fix applied)"
    ]
    if connected:
        ref_names = [os.path.basename(c["file"]) for c in connected[:5]]
        warnings.append(
            f"Found {len(connected)} file(s) that reference '{expected_name}' and may need updating: "
            + ", ".join(ref_names)
        )

    logger.info(f"[DETERMINISTIC FIX] Renamed '{expected_name}' -> '{new_name}' in {file_path_str}")
    return {
        "fixed_lines": fixed_lines,
        "description": f"Renamed component '{expected_name}' -> '{new_name}'",
        "old_name": expected_name,
        "new_name": new_name,
        "warnings": warnings,
        "connected_changes": connected,
    }


def _fix_click_missing_key_event(file_lines, issue_line):
    """
    Deterministic fix for vuejs-accessibility/click-events-have-key-events.
    Adds @keydown.enter alongside @click.
    """
    target_idx = max(0, issue_line - 1)
    if target_idx >= len(file_lines):
        return None

    line = file_lines[target_idx]
    if "@click" not in line and "v-on:click" not in line:
        # Search nearby lines
        for i in range(max(0, target_idx - 3), min(len(file_lines), target_idx + 4)):
            if "@click" in file_lines[i] or "v-on:click" in file_lines[i]:
                target_idx = i
                line = file_lines[i]
                break
        else:
            return None

    # Check if already has a key event
    if "@keydown" in line or "@keyup" in line or "@keypress" in line:
        return None

    fixed_lines = list(file_lines)

    # Add @keydown.enter after @click="..."
    m = re.search(r'(@click(?:\.\w+)*="[^"]*")', line)
    if m:
        click_attr = m.group(1)
        # Extract the handler: @click="handler" → @keydown.enter="handler"
        handler_match = re.search(r'="([^"]*)"', click_attr)
        handler = handler_match.group(1) if handler_match else ""
        keydown_attr = f' @keydown.enter="{handler}"'
        new_line = line.replace(click_attr, click_attr + keydown_attr)
        fixed_lines[target_idx] = new_line

        # Also add tabindex="0" if not present and element is not inherently focusable
        if 'tabindex' not in new_line and '<button' not in new_line and '<a ' not in new_line and '<input' not in new_line:
            fixed_lines[target_idx] = fixed_lines[target_idx].replace(
                keydown_attr,
                keydown_attr + ' tabindex="0"'
            )

        return {
            "fixed_lines": fixed_lines,
            "description": f"Added @keydown.enter handler and tabindex for keyboard accessibility",
            "warnings": ["Added @keydown.enter event handler for keyboard accessibility"],
            "connected_changes": [],
        }

    return None


def _find_component_references(component_name, source_file_path):
    """Scan workspace for files that import or use the given component name."""
    references = []
    search_roots = _get_workspace_roots()
    source_abs = None
    try:
        source_abs = str(Path(source_file_path).resolve()).lower()
    except Exception:
        pass

    for root in search_roots:
        try:
            root_str = str(root)
            for current_root, dirs, files in os.walk(root_str):
                dirs[:] = [d for d in dirs if d.lower() not in PATH_WALK_SKIP_DIRS]
                for fname in files:
                    if not fname.endswith(('.vue', '.js', '.ts', '.jsx', '.tsx')):
                        continue
                    full_path = os.path.join(current_root, fname)
                    try:
                        if source_abs and str(Path(full_path).resolve()).lower() == source_abs:
                            continue
                    except Exception:
                        pass
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        if re.search(r'\b' + re.escape(component_name) + r'\b', content):
                            references.append({
                                "file": full_path.replace("\\", "/"),
                                "type": "reference",
                            })
                    except Exception:
                        continue
        except Exception:
            continue

    return references


def _build_surgical_window(file_lines, issue_line, radius=15):
    """Build a small focused context window around the issue line for AI fix."""
    total = len(file_lines)
    if total == 0:
        return 0, 0, ""
    clamped = max(1, min(issue_line, total))
    start_idx = max(0, clamped - 1 - radius)
    end_idx = min(total, clamped + radius)
    window_text = "".join(file_lines[start_idx:end_idx])
    return start_idx, end_idx, window_text


@app.route('/api/ai-fix', methods=['POST'])
def ai_fix_endpoint():
    """
    POST /api/ai-fix
    Surgically fixes code issues using deterministic handlers for known patterns
    and LLM-based fixes for unknown patterns. Includes verification and
    connected-changes detection.
    """
    try:
        data = request.get_json(silent=True) or {}
        run_id = data.get("run_id")
        incoming_path = (data.get("file_path") or "").strip()
        issue_type = (data.get("issue_type") or "").strip()
        issue_message = (data.get("issue_message") or "").strip()
        code_snippet = (data.get("code_snippet") or "").strip()
        recommendation = (data.get("recommendation") or "").strip()

        try:
            issue_line = int(data.get("issue_line", 1))
        except (TypeError, ValueError):
            issue_line = 1

        logger.info(
            f"[AI FIX] Request: path={incoming_path!r} line={issue_line} "
            f"type={issue_type[:80]!r} snippet_len={len(code_snippet)}"
        )

        # ── Step 1: Resolve file path ──
        target_path_obj, normalized_incoming = _resolve_issue_file_path(run_id, incoming_path)
        if not target_path_obj:
            logger.error(f"[AI FIX] File not found on disk: {incoming_path}")
            return jsonify({"error": f"Source file not found: {incoming_path}"}), 400

        target_path = str(target_path_obj)
        logger.info(f"[AI FIX] Resolved: {incoming_path} \u2192 {target_path}")

        # ── Step 2: Read file ──
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                file_lines = f.readlines()
        except Exception as exc:
            logger.error(f"[AI FIX] Read failure: {exc}")
            return jsonify({"error": f"Failed to read file: {exc}"}), 500

        total_lines = len(file_lines)
        issue_line = max(1, min(issue_line, total_lines))

        # ── Step 3: Try deterministic fix first ──
        det_result = _try_deterministic_fix(
            file_lines, issue_line, issue_type, issue_message,
            code_snippet, recommendation, target_path
        )

        if det_result:
            logger.info(f"[AI FIX] Deterministic fix applied: {det_result['description']}")
            fixed_lines = det_result["fixed_lines"]
            full_file_reconstructed = "".join(fixed_lines)

            # Build focused display window around the change
            start_idx, end_idx, _ = _build_surgical_window(file_lines, issue_line, radius=15)
            original_window = "".join(file_lines[start_idx:end_idx])
            fixed_window = "".join(fixed_lines[start_idx:end_idx])

            # Validate syntax of the full fixed file
            syntax_valid = True
            validation_note = "Deterministic fix applied"
            try:
                syntax_valid, validation_note = _validate_syntax(normalized_incoming, full_file_reconstructed)
            except Exception as val_err:
                logger.warning(f"[AI FIX] Syntax validation error: {val_err}")
                validation_note = f"Validation unavailable: {val_err}"

            import difflib
            diff_lines = list(difflib.unified_diff(
                file_lines,
                fixed_lines,
                fromfile=normalized_incoming,
                tofile=normalized_incoming,
                lineterm=""
            ))

            logger.info(
                f"[AI FIX] Deterministic fix complete. Syntax={syntax_valid}. "
                f"Window: lines {start_idx + 1}-{end_idx}."
            )

            return jsonify({
                "original_text": original_window,
                "fixed_text": fixed_window,
                "full_fixed_content": full_file_reconstructed,
                "full_fixed_text": full_file_reconstructed,
                "full_original_text": "".join(file_lines),
                "diff_text": "\n".join(diff_lines),
                "diff_fragments": diff_lines,
                "window_start": start_idx + 1,
                "window_end": end_idx,
                "file_path": normalized_incoming,
                "resolved_file_path": target_path,
                "syntax_valid": syntax_valid,
                "validation_note": validation_note,
                "warnings": det_result.get("warnings", []),
                "connected_changes": det_result.get("connected_changes", []),
                "fix_type": "deterministic",
                "fix_description": det_result["description"],
            }), 200

        # ── Step 4: LLM-based fix (fallback) ──
        logger.info("[AI FIX] No deterministic handler matched, falling back to LLM")

        # Use a small surgical window (±15 lines) instead of the whole file
        start_idx, end_idx, original_window_text = _build_surgical_window(
            file_lines, issue_line, radius=15
        )

        logger.info(
            f"[AI FIX] Surgical context window: lines {start_idx + 1}-{end_idx} "
            f"(issue at line {issue_line}, total {total_lines} lines)"
        )

        # Build a highly focused prompt
        problem_parts = []
        if issue_type:
            problem_parts.append(f"Issue: {issue_type}")
        if issue_message:
            problem_parts.append(f"Description: {issue_message}")
        if recommendation:
            problem_parts.append(f"Recommended fix: {recommendation}")
        combined_problem = "\n".join(problem_parts) if problem_parts else "General code quality issue"

        snippet_context = ""
        if code_snippet:
            snippet_context = (
                f"\n\nThe exact code snippet flagged by the analyzer (with \u25ba marking the issue line):\n"
                f"{code_snippet}\n"
            )

        system_instruction = (
            "You are a surgical source-code correction engine.\n"
            f"File: {normalized_incoming}\n"
            f"Context window: lines {start_idx + 1} to {end_idx}.\n"
            f"The issue is at or near line {issue_line}.\n\n"
            f"PROBLEM:\n{combined_problem}\n"
            f"{snippet_context}\n"
            "RULES:\n"
            "1. Output the ENTIRE context window with the fix applied.\n"
            "2. You MUST change the specific lines causing the issue. If you return unchanged code, you FAILED.\n"
            "3. Change ONLY the minimum lines needed to fix this specific issue.\n"
            "4. Do NOT change unrelated code, do NOT add comments, do NOT refactor.\n"
            "5. For naming rules (e.g. multi-word-component-names): rename the identifier "
            "(e.g. 'Header' \u2192 'AppHeader').\n"
            "6. For accessibility rules: add the missing attribute/handler.\n"
            "7. Output raw source code ONLY. No markdown fences, no explanations, no labels.\n"
            "8. Preserve exact indentation and whitespace."
        )

        _load_env_file()
        raw_base_url = os.getenv("OPENWEBUI_BASE_URL", "")
        api_key = os.getenv("OPENWEBUI_API_KEY", "")
        model_name = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        timeout_val = os.getenv("LLM_TIMEOUT_SECONDS", "120")

        try:
            timeout = int(timeout_val)
        except ValueError:
            timeout = 120

        if not raw_base_url:
            logger.error("[AI FIX] OPENWEBUI_BASE_URL is not configured.")
            return jsonify({"error": "OPENWEBUI_BASE_URL environment variable is not configured"}), 500

        resolved_base_url = _resolve_base_url(raw_base_url)
        api_url = f"{resolved_base_url}/chat/completions"

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Source code (lines {start_idx + 1}-{end_idx}):\n{original_window_text}"}
            ],
            "temperature": 0.1,
            "stream": False
        }

        headers = _build_llm_headers(api_key)
        logger.info(f"[AI FIX] LLM request to {api_url} model={model_name}")

        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                llm_output = _extract_llm_message_content(res_data)
                if not llm_output.strip():
                    logger.error(f"[AI FIX] Empty LLM response: {res_data}")
                    return jsonify({"error": "LLM returned an empty response."}), 500
        except urllib.error.HTTPError as http_err:
            err_body = ""
            try:
                err_body = http_err.read().decode("utf-8")
            except Exception:
                pass
            logger.error(
                f"[AI FIX] HTTPError: {http_err.code} {http_err.reason} - {err_body[:500]}"
            )
            return jsonify({"error": f"LLM API Error: {http_err.code} - {http_err.reason}"}), 500
        except Exception as api_err:
            logger.error(f"[AI FIX] LLM connection failure: {api_err}")
            return jsonify({"error": f"LLM connection failure: {api_err}"}), 500

        # ── Step 5: Sanitize and process LLM output ──
        llm_cleaned = _sanitize_llm_code(llm_output)
        cleaned_lines = _strip_non_code_lines(llm_cleaned.splitlines())
        fixed_window_text = "\n".join(cleaned_lines)
        if fixed_window_text and llm_cleaned.endswith(("\n", "\r")):
            fixed_window_text += "\n"

        if not fixed_window_text.strip():
            logger.error("[AI FIX] Sanitization removed entire LLM response.")
            return jsonify({"error": "AI proposal could not be sanitized into valid source text."}), 500

        # Normalize line endings to match the original file
        fixed_window_lines = fixed_window_text.splitlines()
        line_ending = "\r\n" if (file_lines and file_lines[0].endswith("\r\n")) else "\n"
        fixed_window_text = "".join(line + line_ending for line in fixed_window_lines)

        # ── Step 6: Reconstruct full file ──
        full_file_reconstructed = (
            "".join(file_lines[:start_idx]) +
            fixed_window_text +
            "".join(file_lines[end_idx:])
        )

        # ── Step 7: Verify the fix ──
        response_warnings = []

        # Check if fix is actually different
        if original_window_text.strip() == fixed_window_text.strip():
            response_warnings.append(
                "Warning: The AI returned code identical to the original. "
                "The model may not have understood the required fix."
            )
            logger.warning("[AI FIX] LLM returned identical code - fix may not be effective")

        # Validate syntax
        syntax_valid = True
        validation_note = "Syntax check skipped"
        try:
            syntax_valid, validation_note = _validate_syntax(normalized_incoming, full_file_reconstructed)
        except Exception as val_err:
            logger.warning(f"[AI FIX] Syntax validation error: {val_err}")
            validation_note = f"Validation unavailable: {val_err}"

        if not syntax_valid:
            response_warnings.append(f"Syntax validation failed: {validation_note}")

        import difflib
        reconstructed_lines = full_file_reconstructed.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            file_lines,
            reconstructed_lines,
            fromfile=normalized_incoming,
            tofile=normalized_incoming,
            lineterm=""
        ))

        logger.info(
            f"[AI FIX] LLM fix generated. Syntax={syntax_valid}. "
            f"Window: lines {start_idx + 1}-{end_idx}. "
            f"Diff lines: {len(diff_lines)}."
        )

        return jsonify({
            "original_text": original_window_text,
            "fixed_text": fixed_window_text,
            "full_fixed_content": full_file_reconstructed,
            "full_fixed_text": full_file_reconstructed,
            "full_original_text": "".join(file_lines),
            "diff_text": "\n".join(diff_lines),
            "diff_fragments": diff_lines,
            "window_start": start_idx + 1,
            "window_end": end_idx,
            "file_path": normalized_incoming,
            "resolved_file_path": target_path,
            "syntax_valid": syntax_valid,
            "validation_note": validation_note,
            "warnings": response_warnings,
            "fix_type": "llm",
        }), 200

    except Exception as exc:
        logger.exception("[AI FIX] Unexpected error inside /api/ai-fix route:")
        return jsonify({"error": str(exc)}), 500



@app.route("/api/ai-fix/apply", methods=["POST"])
def ai_fix_apply():
    """
    POST /api/ai-fix/apply
    Surgically writes the approved fixed_content to active file path,
    retaining a single .audit-backup rollback option on disk.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            logger.error("AI Fix Apply called with invalid JSON.")
            return jsonify({"error": "Invalid JSON payload"}), 400

        file_path = data.get("file_path")
        fixed_content = data.get("fixed_content")

        if not file_path or fixed_content is None:
            logger.error("AI Fix Apply missing 'file_path' or 'fixed_content'.")
            return jsonify({"error": "Missing required 'file_path' or 'fixed_content'"}), 400

        abs_path, _ = _resolve_issue_file_path(None, file_path)
        if not abs_path:
            logger.error(f"Unable to resolve file path for apply: {file_path}")
            return jsonify({"error": f"File path could not be resolved: {file_path}"}), 404

        # Read current content to ensure it exists
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                current_content = f.read()
        except Exception as e:
            logger.error(f"Unable to read file before backup for apply: {file_path} - {e}")
            return jsonify({"error": f"Unable to read file before backup: {str(e)}"}), 500

        # Step A: Copy exact current contents to backup file
        backup_path = abs_path.with_suffix(abs_path.suffix + ".audit-backup")
        try:
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(current_content)
        except Exception as e:
            logger.error(f"Failed to write audit-backup for {file_path}: {e}")
            return jsonify({"error": f"Failed to create file backup: {str(e)}"}), 500

        # Step B: Write the fixed_content surgically to active path
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
        except Exception as e:
            logger.error(f"Failed to write fixed content to {file_path}: {e}")
            # Try to restore backup
            try:
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(current_content)
                logger.info(f"Successfully restored original content to {file_path} after write failure.")
            except Exception as restore_err:
                logger.error(f"CRITICAL: Failed to restore original content to {file_path} after write failure: {restore_err}")
            return jsonify({"error": f"Failed to write fixed content to active file: {str(e)}"}), 500

        logger.info(f"Successfully applied AI fix to file: {file_path}. Backup stored at: {backup_path.name}")
        return jsonify({
            "success": True,
            "message": f"Successfully applied AI fix to {file_path}.",
            "backup_path": backup_path.name
        }), 200

    except Exception as e:
        logger.exception("Unexpected error inside /api/ai-fix/apply route:")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai-fix/undo", methods=["POST"])
def ai_fix_undo():
    """
    POST /api/ai-fix/undo
    Restores the original file contents from the active .audit-backup file.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        file_path = data.get("file_path")
        if not file_path:
            return jsonify({"error": "Missing 'file_path' in payload"}), 400

        abs_path, _ = _resolve_issue_file_path(None, file_path)
        if not abs_path:
            return jsonify({"error": f"File path could not be resolved: {file_path}"}), 404

        backup_path = abs_path.with_suffix(abs_path.suffix + ".audit-backup")
        if not backup_path.exists():
            logger.warning(f"Undo requested for {file_path} but no backup file exists.")
            return jsonify({"error": "No backup file found for this file. Undo not possible."}), 404

        # Read backup content
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read backup file {backup_path}: {e}")
            return jsonify({"error": f"Failed to read backup file: {str(e)}"}), 500

        # Write original content back
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(backup_content)
        except Exception as e:
            logger.error(f"Failed to write backup content to {abs_path}: {e}")
            return jsonify({"error": f"Failed to restore original file content: {str(e)}"}), 500

        # Delete backup
        try:
            os.remove(backup_path)
        except Exception as e:
            logger.warning(f"Failed to delete backup file {backup_path} after successful restore: {e}")

        logger.info(f"Successfully rolled back and removed backup for: {file_path}")
        return jsonify({
            "success": True,
            "message": f"Successfully restored {file_path} from backup."
        }), 200

    except Exception as e:
        logger.exception("Unexpected error inside /api/ai-fix/undo route:")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Defensively clear out any incomplete in_progress runs from previous crashes on startup
    _cleanup_in_progress_runs()

    parser = argparse.ArgumentParser(description="Code Audit Librarian API Server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the API server on")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Code Audit Librarian ? Flask API Server (Stage 6)")
    logger.info("=" * 60)
    logger.info(f"Project: {PROJECT_NAME}")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Base Path: {BASE_PATH}")
    logger.info("=" * 60)
    logger.info(f"Starting server on http://localhost:{args.port}")
    logger.info(f"API endpoints available at http://localhost:{args.port}/api/*")
    logger.info("=" * 60)
    
    app.run(host="0.0.0.0", port=args.port, debug=False)
