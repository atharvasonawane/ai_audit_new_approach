"""
V3 Dual-Pass Analyzer (Corrected Architecture)
Pass 1: Verifies existing static findings against actual code
Pass 2: Uses complexity metrics to detect new architectural patterns
"""
import json
import time
import requests
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def call_groq_llm(prompt, code_content):
    """Send a prompt + code to Groq and return parsed JSON."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": code_content}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    try:
        time.sleep(3)  # Throttle for free tier
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        else:
            print(f"    API Error {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"    Exception: {e}")
        return None


def pass_1_verify_findings(code_content, static_findings):
    """
    Pass 1: Takes raw code + static findings list.
    Asks AI to verify each finding as REAL or FALSE POSITIVE.
    """
    findings_text = json.dumps(static_findings, indent=2)
    
    system_prompt = """You are an expert Vue.js code auditor. You will receive:
1. The raw Vue source code
2. A list of findings from a static analysis tool

Your job: For EACH finding, read the actual code and determine if it is a REAL issue or a FALSE POSITIVE.

Rules:
- EMPTY_LINK: Only real if the link/router-link has NO visible text or content inside it.
- UNLABELED_INPUT: Only real if the input has no associated <label>, no aria-label, and no visible label nearby.
- DEEP_NESTED_TEMPLATE: Only real if v-if is physically nested >3 levels deep in the source code.
- EXCESSIVE_API_USAGE: Only real if the component actually calls multiple APIs in a single execution path. Mutually exclusive if/else blocks do NOT count.
- PLACEHOLDER_USED_AS_LABEL: Only real if placeholder text is the ONLY label for the input.

Return ONLY valid JSON:
{
  "verified": [
    {"finding": "UNLABELED_INPUT at line 23", "reason": "Input has no label element", "confidence": 90}
  ],
  "rejected": [
    {"finding": "EMPTY_LINK at line 33", "reason": "router-link contains {{ title }} text", "confidence": 85}
  ]
}

If ALL findings are real, return empty rejected array. If ALL are false positives, return empty verified array."""

    user_content = f"""Here is the Vue source code:

```vue
{code_content}
```

Here are the static analysis findings to verify:
{findings_text}"""

    return call_groq_llm(system_prompt, user_content)


def pass_2_detect_patterns(code_content, complexity_metrics):
    """
    Pass 2: Takes raw code + complexity metrics.
    Asks AI to detect architectural patterns the static tool missed.
    """
    metrics_text = json.dumps(complexity_metrics, indent=2)
    
    system_prompt = """You are a senior Vue.js architect. You will receive:
1. The raw Vue source code
2. Complexity metrics from a static analyzer (lines, methods, watchers, etc.)

Your job: Using BOTH the metrics AND the code, identify architectural patterns or code smells that the static tool missed.

Look for:
1. God components (too many responsibilities based on method count + lines)
2. Missing error handlers on async API calls (.catch() or try/catch)
3. Tightly coupled logic (watchers triggering API calls without guards)
4. Dead code (unused data variables, methods never called)

Rules:
- Cite the exact line number and code snippet as proof.
- Do NOT hallucinate. If the code is clean, return an empty patterns array.
- Use the metrics to guide your analysis, not replace it.

Return ONLY valid JSON:
{
  "patterns": [
    {"type": "missing_error_handler", "line": 173, "description": "fetchModules() calls API without .catch()", "confidence": 75}
  ]
}"""

    user_content = f"""Here is the Vue source code:

```vue
{code_content}
```

Here are the complexity metrics:
{metrics_text}"""

    return call_groq_llm(system_prompt, user_content)


def analyze_file(filepath, static_findings, complexity_metrics):
    """
    Run both passes on a single file.
    Returns: (pass1_result, pass2_result)
    """
    import os
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = os.path.basename(filepath)
    
    print(f"  -> Pass 1 (Verify Findings) on {filename} ({len(content)} chars)...")
    pass1 = pass_1_verify_findings(content, static_findings)
    
    print(f"  -> Pass 2 (Detect Patterns) on {filename}...")
    pass2 = pass_2_detect_patterns(content, complexity_metrics)
    
    return pass1, pass2