import subprocess
from pathlib import Path


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
