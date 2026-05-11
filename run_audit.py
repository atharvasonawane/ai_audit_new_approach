import os
import sys
import argparse
import subprocess
import sqlite3
import yaml
from pathlib import Path

# Add audit_tool to sys.path so we can import internal modules
SCRIPT_DIR = Path(__file__).parent.resolve()
AUDIT_TOOL_DIR = SCRIPT_DIR / "audit_tool"
if str(AUDIT_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIT_TOOL_DIR))

from utils.logger import get_logger

logger = get_logger(__name__)


def load_config(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        sys.exit(1)


def run_module(module_name: str):
    """Helper to run a module cleanly via subprocess."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", module_name], cwd=str(SCRIPT_DIR), check=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Execution of {module_name} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        logger.error(f"Failed to run {module_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Code Audit Librarian - Orchestrator")
    parser.add_argument(
        "--project", required=True, type=str, help="Project name to audit"
    )
    parser.add_argument(
        "--scout-only", action="store_true", help="Run only the Scout phase"
    )
    parser.add_argument(
        "--ai-only", action="store_true", help="Run only the AI pipeline phase"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume an interrupted audit run"
    )
    parser.add_argument(
        "--report-only", action="store_true", help="Run only the Report phase"
    )

    args = parser.parse_args()

    # 1. Load project_config.yaml
    config_file = AUDIT_TOOL_DIR / "project_config.yaml"
    config = load_config(config_file)
    project_config_name = config.get("project", {}).get("name")

    if args.project != project_config_name:
        logger.error(
            f"Provided project name '{args.project}' does not match config '{project_config_name}'"
        )
        sys.exit(1)

    # 2. Initialize SQLite and check audit_runs
    DB_PATH = AUDIT_TOOL_DIR / "audit_history.db"

    # Run db_init to ensure tables exist
    db_init_script = AUDIT_TOOL_DIR / "db" / "db_init.py"
    if db_init_script.exists():
        run_module("audit_tool.db.db_init")
    else:
        logger.warning(
            f"Could not find {db_init_script}, assuming DB handles its own init."
        )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check for in_progress runs
    cursor.execute(
        "SELECT id, current_phase FROM audit_runs WHERE project_name=? AND status='in_progress'",
        (args.project,),
    )
    existing_run = cursor.fetchone()

    if existing_run:
        run_id, current_phase = existing_run
        resume = args.resume
        if not resume:
            sys.stdout.write(
                f"An interrupted run (Phase: {current_phase}) exists for project '{args.project}'. Resume? (y/n): "
            )
            sys.stdout.flush()
            choice = input().strip().lower()
            if choice == "y":
                resume = True
            else:
                cursor.execute("DELETE FROM audit_runs WHERE id=?", (run_id,))
                conn.commit()
                logger.info("Deleted previous interrupted run. Starting fresh.")
    else:
        if args.resume:
            logger.info("No interrupted run found to resume. Starting fresh.")

    # Start or update run tracking (unless report only)
    if not args.report_only and not args.ai_only:
        if existing_run and resume:
            cursor.execute(
                "UPDATE audit_runs SET current_phase='scout' WHERE id=?", (run_id,)
            )
        else:
            cursor.execute(
                "INSERT INTO audit_runs (project_name, current_phase, status) VALUES (?, 'scout', 'in_progress')",
                (args.project,),
            )
        conn.commit()

    try:
        # 3. PHASE 1: SCOUT
        if not args.ai_only and not args.report_only:
            logger.info("── PHASE 1: SCOUT ──────────────────────────────────────")

            # Execute scanner
            if not run_module("audit_tool.scout.scanner"):
                sys.exit(1)

            # Execute skeleton builder
            if not run_module("audit_tool.scout.skeleton_builder"):
                sys.exit(1)

            logger.info("Scout phase complete.")

        # 4. PHASE 2: AI PIPELINE
        if not args.scout_only and not args.report_only:
            # Update phase
            cursor.execute(
                "UPDATE audit_runs SET current_phase='ai_pipeline' WHERE project_name=? AND status='in_progress'",
                (args.project,),
            )
            conn.commit()

            logger.info("── PHASE 2: AI PIPELINE ────────────────────────────────")

            # Execute ai_dependency_builder
            if not run_module("ai_pipeline.ai_dependency_builder"):
                sys.exit(1)

            # Execute ai_reporter
            if not run_module("ai_pipeline.ai_reporter"):
                sys.exit(1)

            # Execute ai_architecture_analyzer
            if not run_module("ai_pipeline.ai_architecture_analyzer"):
                sys.exit(1)

            # Mark complete
            cursor.execute(
                "UPDATE audit_runs SET status='complete', completed_at=CURRENT_TIMESTAMP WHERE project_name=? AND status='in_progress'",
                (args.project,),
            )
            conn.commit()

        # 5. PHASE 3: REPORT
        logger.info("── PHASE 3: REPORT ─────────────────────────────────────")
        logger.info("Report generation pending Stage 9 implementation.")

    except Exception as e:
        logger.error(f"Audit pipeline encountered an error: {e}")
        # Optionally update db to status='failed'
    finally:
        conn.close()


if __name__ == "__main__":
    main()
