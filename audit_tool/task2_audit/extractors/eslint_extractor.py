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
        
        # Build ESLint command
        cmd = [
            str(audit_tool_dir / "node_modules" / ".bin" / "eslint.cmd"),
            "--no-eslintrc",
            "--config", str(audit_tool_dir / ".eslintrc.js"),
            "--format", "json",
            "-o", "eslint_report.json"
        ]
        
        # If dirty_files is provided, scan only those files
        # Otherwise, scan the entire directory
        if dirty_files:
            # Filter to only .vue and .js files from dirty_files
            target_files = []
            for file_path in dirty_files:
                file_path = Path(file_path)
                if file_path.suffix in ['.vue', '.js']:
                    target_files.append(str(file_path))
            
            if not target_files:
                # No .vue/.js files in dirty_files, nothing to scan
                return True
                
            cmd.extend(target_files)
        else:
            # Scan entire directory (original behavior)
            cmd.extend([
                target_dir,
                "--ext", ".vue,.js"
            ])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=audit_tool_dir
        )
        
        # Check if the report file was generated
        report_path = Path(__file__).parent.parent.parent / "eslint_report.json"
        return report_path.exists()
            
    except subprocess.CalledProcessError as e:
        print(f"ESLint scan failed: {e}")
        return False
    except Exception as e:
        print(f"Error running ESLint scan: {e}")
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
        for file_result in data:
            file_path = file_result.get("filePath", "")
            messages = file_result.get("messages", [])
            
            for msg in messages:
                # Only keep severity >= 2 (Errors), ignore stylistic Warnings
                if msg.get("severity", 0) >= 2:
                    results.append({
                        "file_path": file_path,
                        "rule_id": msg.get("ruleId", ""),
                        "line": msg.get("line", 0),
                        "message": msg.get("message", ""),
                        "severity": msg.get("severity", 0)
                    })
        
        return results
        
    except json.JSONDecodeError as e:
        print(f"Error parsing ESLint JSON: {e}")
        return []
    except Exception as e:
        print(f"Error reading ESLint report: {e}")
        return []
