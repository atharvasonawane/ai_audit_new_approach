import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any


def run_eslint_scan(target_dir: str, dirty_files: List[str] = None) -> bool:
    """
    Run ESLint scan on target directory and generate a JSON report.
    Can target specific files (dirty_files) or entire directory.
    
    Args:
        target_dir: Path to directory to scan
        dirty_files: List of specific file paths to scan (for incremental auditing)
        
    Returns:
        True if scan completed successfully and report was generated, False otherwise
    """
    try:
        # Get the audit_tool directory
        audit_tool_dir = Path(__file__).parent.parent.parent
        report_path = audit_tool_dir / "eslint_report.json"
        
        # Build base ESLint command
        base_cmd = [
            "npx", "eslint",
            "--no-eslintrc",
            "--config", str(audit_tool_dir / ".eslintrc.js"),
            "--format", "json",
            "-o", "eslint_report.json"
        ]
        
        # If no dirty_files is provided, scan entire directory (original behavior)
        if not dirty_files:
            cmd = base_cmd + [target_dir, "--ext", ".vue,.js"]
            print(f"[DEBUG] Executing ESLint on entire directory...")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=audit_tool_dir, shell=True)
            return report_path.exists()
            
        # Filter to only .vue and .js files from dirty_files
        target_files = []
        for file_path in dirty_files:
            file_path = Path(file_path)
            if file_path.suffix in ['.vue', '.js']:
                target_files.append(str(file_path))
        
        if not target_files:
            # No .vue/.js files in dirty_files, nothing to scan
            return True
            
        # Chunk the target files to avoid Windows command line length limits
        chunk_size = 30
        chunks = [target_files[i:i + chunk_size] for i in range(0, len(target_files), chunk_size)]
        
        all_json_results = []
        print(f"[DEBUG] Executing ESLint in {len(chunks)} chunks for {len(target_files)} files...")
        
        for i, chunk in enumerate(chunks):
            cmd = base_cmd + chunk
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=audit_tool_dir,
                    shell=True
                )
                
                if result.returncode != 0:
                    print(f"[DEBUG] ESLint chunk {i+1} returned non-zero exit code: {result.returncode}")
                    if result.stderr:
                        print(f"[DEBUG] ESLint STDERR:\n{result.stderr}")
                        
                if report_path.exists():
                    with open(report_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content and content not in ("[]", "{}"):
                            chunk_data = json.loads(content)
                            if isinstance(chunk_data, list):
                                all_json_results.extend(chunk_data)
                else:
                    print(f"[DEBUG] ESLint report file was NOT generated for chunk {i+1}!")
                    
            except Exception as e:
                print(f"[DEBUG] Error running ESLint chunk {i+1}: {e}")
                
        # Write the aggregated results back to the single report file for the parser to read
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(all_json_results, f, indent=2)
            
        # Also return True if we have the file
        return report_path.exists()
            
    except Exception as e:
        print(f"Error preparing ESLint scan: {e}")
        return False


def parse_eslint_results(json_path: str = "eslint_report.json") -> List[Dict[str, Any]]:
    """
    Parse ESLint JSON report and extract linting issues.
    
    Args:
        json_path: Path to the ESLint JSON report file
        
    Returns:
        A flat list of dictionaries containing file_path, rule_id, line, message, and severity
        Returns an empty list if the file is missing or empty
    """
    try:
        # Get the audit_tool directory
        audit_tool_dir = Path(__file__).parent.parent.parent
        report_path = audit_tool_dir / json_path
        
        # Check if file exists
        if not report_path.exists():
            print(f"ESLint report not found: {report_path}")
            return []
        
        # Read and parse JSON
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Handle empty data
        if not data:
            return []
        
        # Extract issues from each file
        results = []
        a11y_defects = 0
        for file_result in data:
            file_path = file_result.get("filePath", "")
            messages = file_result.get("messages", [])
            
            for msg in messages:
                # Only keep severity >= 2 (Errors), ignore stylistic Warnings
                if msg.get("severity", 0) >= 2:
                    rule_id = msg.get("ruleId", "")
                    if rule_id and str(rule_id).startswith("vuejs-accessibility"):
                        a11y_defects += 1
                        
                    results.append({
                        "file_path": file_path,
                        "rule_id": rule_id,
                        "line": msg.get("line", 0),
                        "message": msg.get("message", ""),
                        "severity": msg.get("severity", 0)
                    })
        
        print(f"[DEBUG] Extracted {a11y_defects} accessibility issues from ESLint JSON.")
        return results
        
    except json.JSONDecodeError as e:
        print(f"Error parsing ESLint JSON: {e}")
        return []
    except Exception as e:
        print(f"Error reading ESLint report: {e}")
        return []
