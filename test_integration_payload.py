import os
import sys
import yaml
import json
import shutil
import subprocess
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
AUDIT_TOOL_DIR = BASE_DIR / "audit_tool"
TASK2_DIR = AUDIT_TOOL_DIR / "task2_audit"
sys.path.insert(0, str(TASK2_DIR))

from extractors.orchestrator import scan_all_vue_files

CONFIG_PATH = AUDIT_TOOL_DIR / "config" / "project_config.yaml"
TEST_FOLDER = BASE_DIR / "test_vue_codebase"


def main():
    print("=== Testing Integration of Payload Metrics ===")

    # 1. Backup original config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        original_config = f.read()

    try:
        # Create test folder and Vue file
        if TEST_FOLDER.exists():
            shutil.rmtree(TEST_FOLDER)
        TEST_FOLDER.mkdir(parents=True)

        vue_file = TEST_FOLDER / "TestPayload.vue"
        with open(vue_file, "w", encoding="utf-8") as f:
            f.write("""
<template>
  <div>Test Application</div>
</template>
<script>
export default {
  mounted() {
    this.$http.post('/api/save', {
      user: {
        name: "JaneDoe"
      },
      role: "Admin"
    });
  }
}
</script>
            """)

        # 2. Update config to point to test folder
        config_data = yaml.safe_load(original_config)
        config_data["base_path"] = str(TEST_FOLDER.absolute()).replace("\\", "/")
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f)

        # 3. Use orchestrator directly because it manages the extraction flow
        print("Running orchestrator extraction...")

        results = scan_all_vue_files(
            base_path=str(TEST_FOLDER.absolute()).replace("\\", "/"),
            cfg=config_data,
            config_path=str(CONFIG_PATH),
        )

        metrics = results[0].get("extracted_metrics", {})
        keys = metrics.get("payload_keys", 0)
        depth = metrics.get("payload_depth", 0)
        size = metrics.get("payload_size_kb", 0.0)

        print(f"\n--- Output of Extracted Metrics ---")
        print(f"Payload Keys   : {keys}")
        print(f"Payload Depth  : {depth}")
        print(f"Payload Size   : {size:.4f} KB")

        print("\n=============================================")
        if keys > 0 and depth > 0 and size > 0:
            print("INTEGRATION PASSED")
        else:
            print("INTEGRATION FAILED")
        print("=============================================")

    finally:
        # Restore configuration
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(original_config)
        if TEST_FOLDER.exists():
            try:
                shutil.rmtree(TEST_FOLDER)
            except Exception:
                pass


if __name__ == "__main__":
    main()
