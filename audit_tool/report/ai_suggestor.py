"""
AI Suggestor v2 — generates intelligent suggestions for ALL defect categories.
Uses qwen-2.5-coder:3b model via local Ollama HTTP API.
Falls back to Google Gemini API if configured.
Caches all results to ai_suggestions_cache.json.
"""
import json
import os
import hashlib
import sys
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:3b"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "ai_suggestions_cache.json")


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _defect_hash(defect, file_context=""):
    """Create a unique hash key for a defect."""
    key_parts = [
        defect.get("defect_type", defect.get("name", "")),
        defect.get("trigger_text", ""),
        defect.get("expected_text", ""),
        defect.get("element", defect.get("element_type", "")),
        defect.get("rule", ""),
        defect.get("category", ""),
        str(defect.get("line_number", "")),
        file_context,
    ]
    key = "|".join(str(p) for p in key_parts)
    return hashlib.md5(key.encode()).hexdigest()


# =====================================================================
# PROMPT BUILDERS — one per defect category
# =====================================================================

def _build_spelling_prompt(defect):
    trigger = defect.get("trigger_text", "")
    expected = defect.get("expected_text", "")
    fname = defect.get("basename", defect.get("file", ""))
    return f"""You are a code audit expert. Analyze this spelling defect found in a Vue.js component.

Flagged text: "{trigger}"
Spell-checker suggested: "{expected}"
File: {fname}

Determine if this is a FALSE POSITIVE. Common false positives include:
- File extensions (xlsx, csv, pdf, json)
- Technical abbreviations (Prev, Nav, Btn, Msg, Config)
- Environment/variable names (csdev, cstest, localhost)
- HTTP/API terms (multipart, formdata, webhook)
- Code identifiers (uploadsinglefile, testcdncs)
- CSS class names or framework terms

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{"is_false_positive": true/false, "confidence": 0.0-1.0, "suggestion": "Your explanation here"}}"""


def _build_css_prompt(defect):
    trigger = defect.get("trigger_text", "")
    expected = defect.get("expected_text", "")
    fname = defect.get("basename", defect.get("file", ""))
    return f"""You are a UI consistency expert. Analyze this CSS class inconsistency in a Vue.js component.

Current CSS class usage: "{trigger}"
Expected standard pattern: "{expected}"
Element type: {defect.get("element_type", "unknown")}
File: {fname}

Explain why this is inconsistent and provide a specific fix (what CSS class(es) should be used instead).

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{"is_false_positive": false, "confidence": 0.9, "suggestion": "Your specific fix suggestion here"}}"""


def _build_placeholder_prompt(defect):
    trigger = defect.get("trigger_text", "")[:300]
    fname = defect.get("basename", defect.get("file", ""))
    return f"""You are a code quality expert. This Vue.js component contains placeholder/dummy text left in production code.

Placeholder text found: "{trigger}..."
File: {fname}

Explain why this is a problem and suggest what should replace it.

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{"is_false_positive": false, "confidence": 1.0, "suggestion": "Your suggestion here"}}"""


def _build_a11y_prompt(defect):
    element = defect.get("element", "")
    line = defect.get("line_number", "?")
    rule = defect.get("rule", "")
    dtype = defect.get("defect_type", "")
    fname = defect.get("basename", defect.get("file", ""))
    return f"""You are an accessibility expert. Suggest a fix for this accessibility defect in a Vue.js component.

Defect: {dtype}
Rule: {rule}
Element: {element}
Line: {line}
File: {fname}

Provide a specific, actionable HTML fix (show the corrected element).

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{"is_false_positive": false, "confidence": 1.0, "suggestion": "Your specific fix suggestion with corrected HTML element"}}"""


def _build_complexity_prompt(defect):
    flag_name = defect.get("name", "")
    fname = defect.get("basename", defect.get("file", ""))
    return f"""You are a code quality expert. Analyze this complexity flag in a Vue.js component.

Flag: {flag_name}
Category: {defect.get("category", "complexity")}
File: {fname}

Provide a brief, actionable refactoring suggestion to reduce this complexity.

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{"is_false_positive": false, "confidence": 0.9, "suggestion": "Your refactoring suggestion here"}}"""


def _build_prompt(defect, defect_category="generic"):
    """Route to the correct prompt builder based on category."""
    if defect_category == "spelling":
        return _build_spelling_prompt(defect)
    elif defect_category == "css":
        return _build_css_prompt(defect)
    elif defect_category == "placeholder":
        return _build_placeholder_prompt(defect)
    elif defect_category == "a11y":
        return _build_a11y_prompt(defect)
    elif defect_category == "complexity":
        return _build_complexity_prompt(defect)
    else:
        return f"""Analyze this code defect and provide a suggestion:
Details: {json.dumps(defect, default=str)[:500]}

Respond with ONLY valid JSON:
{{"is_false_positive": false, "confidence": 0.5, "suggestion": "Your suggestion here"}}"""


# =====================================================================
# LLM RESPONSE PARSER
# =====================================================================

def _parse_llm_response(text):
    """Parse LLM response, extracting JSON from potentially messy output."""
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    import re
    patterns = [
        r'```json\s*\n?(.*?)\n?```',
        r'```\s*\n?(.*?)\n?```',
        r'(\{[^{}]*"is_false_positive"[^{}]*\})',
        r'(\{[^{}]*"suggestion"[^{}]*\})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    return {
        "is_false_positive": False,
        "confidence": 0.5,
        "suggestion": text[:500] if text else "Unable to parse AI response."
    }


# =====================================================================
# LLM QUERY FUNCTIONS
# =====================================================================

def _query_ollama(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 300}
            },
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("response", "")
        return None
    except Exception:
        return None


def _query_gemini(prompt):
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        return model.generate_content(prompt).text
    except Exception:
        return None


def _get_single_suggestion(defect, defect_category, cache):
    """Get AI suggestion for a single defect. Uses cache, Ollama, or Gemini."""
    file_ctx = defect.get("basename", defect.get("file", ""))
    key = _defect_hash(defect, file_ctx)

    if key in cache:
        return key, cache[key]

    prompt = _build_prompt(defect, defect_category)

    raw = _query_ollama(prompt)
    if raw:
        result = _parse_llm_response(raw)
        return key, result

    raw = _query_gemini(prompt)
    if raw:
        result = _parse_llm_response(raw)
        return key, result

    return key, {
        "is_false_positive": False,
        "confidence": 0.0,
        "suggestion": "AI unavailable — Ollama offline, no Gemini key."
    }


# =====================================================================
# BATCH GENERATOR — processes all defects with progress
# =====================================================================

def generate_all_suggestions(data):
    """
    Generate AI suggestions for ALL defect categories.
    Args: data dict from load_all_data()
    Returns: cache dict {hash: suggestion}
    """
    cache = _load_cache()

    # Build a flat list of (defect, category) tuples
    all_tasks = []
    for defect in data.get("complexity_flags", []):
        all_tasks.append((defect, "complexity"))
    for defect in data.get("spelling_defects", []):
        all_tasks.append((defect, "spelling"))
    for defect in data.get("css_defects", []):
        all_tasks.append((defect, "css"))
    for defect in data.get("placeholder_defects", []):
        all_tasks.append((defect, "placeholder"))
    for defect in data.get("a11y_defects", []):
        all_tasks.append((defect, "a11y"))

    total = len(all_tasks)
    if total == 0:
        print("[AI] No defects to analyze.")
        return cache

    # Check uncached
    uncached = []
    for defect, cat in all_tasks:
        file_ctx = defect.get("basename", defect.get("file", ""))
        key = _defect_hash(defect, file_ctx)
        if key not in cache:
            uncached.append((defect, cat))

    cached_count = total - len(uncached)
    if cached_count > 0:
        print(f"[AI] {cached_count}/{total} suggestions loaded from cache.")
    if len(uncached) == 0:
        print("[AI] All suggestions cached. Skipping LLM queries.")
        return cache

    print(f"[AI] Generating {len(uncached)} AI suggestions...")

    # Check Ollama availability
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code != 200:
            print("[AI] ⚠ Ollama is offline. Trying Gemini fallback...")
    except Exception:
        print("[AI] ⚠ Ollama is offline. Trying Gemini fallback...")

    for idx, (defect, cat) in enumerate(uncached):
        label = defect.get("name", defect.get("defect_type", defect.get("trigger_text", "?")[:30]))
        sys.stdout.write(f"\r[AI] [{idx + 1}/{len(uncached)}] [{cat.upper():>12}] {label:<40}")
        sys.stdout.flush()

        key, result = _get_single_suggestion(defect, cat, cache)
        cache[key] = result

    _save_cache(cache)
    print(f"\n[AI] ✓ All {len(uncached)} suggestions generated and cached.")
    return cache


def get_suggestion(cache, defect):
    """Look up a cached suggestion for a specific defect."""
    file_ctx = defect.get("basename", defect.get("file", ""))
    key = _defect_hash(defect, file_ctx)
    return cache.get(key, {
        "is_false_positive": False,
        "confidence": 0.0,
        "suggestion": "No AI suggestion available."
    })
