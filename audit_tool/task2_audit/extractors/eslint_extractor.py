import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any


def run_eslint_scan(target_dir: str) -> bool:
    """
    Run ESLint scan on the target directory and generate a JSON report.
    
    Args:
        target_dir: Path to the directory to scan
        
    Returns:
        True if the scan completed successfully and report was generated, False otherwise
    """
    try:
        # Get the audit_tool directory
        audit_tool_dir = Path(__file__).parent.parent.parent
        
        # Run ESLint command using local eslint executable
        result = subprocess.run(
            [
                str(audit_tool_dir / "node_modules" / ".bin" / "eslint.cmd"),
                target_dir,
                "--ext", ".vue,.js",
                "--format", "json",
                "-o", "eslint_report.json"
            ],
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
