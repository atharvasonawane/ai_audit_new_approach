import json
import os
import sys
import yaml

# Add task2_audit to path so we can import the shared utility
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "task2_audit"
    ),
)
from extractors.path_utils import normalize_path


def calculate_task3_flags(metrics):
    """Calculate flags based solely on Task 3 requirements."""
    flags = []

    # 1. Lines of Code
    lines = metrics["lines"]
    if lines > 800:
        flags.append("VERY_LARGE_COMPONENT")
    elif lines > 500:
        flags.append("LARGE_COMPONENT")

    # 2. Methods
    if metrics["methods"] > 15:
        flags.append("MANY_METHODS")

    # 3. Computed Properties
    if metrics["computed"] > 10:
        flags.append("MANY_COMPUTED")

    # 4. Watchers
    if metrics["watchers"] > 5:
        flags.append("MANY_WATCHERS")

    # 5. Template Size
    if metrics["templateLines"] > 200:
        flags.append("COMPLEX_TEMPLATE")

    # 6. Child Component Usage
    if metrics["childComponents"] > 5:
        flags.append("MANY_CHILDREN")

    return flags


def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_json_path = os.path.join(root_dir, "task2_db_export.json")
    output_json_path = os.path.join(root_dir, "task3", "component_complexity.json")
    config_path = os.path.join(root_dir, "config", "project_config.yaml")

    if not os.path.exists(export_json_path):
        print(f"Error: {export_json_path} not found. Ensure Task 2 has been run.")
        sys.exit(1)

    # Load base_path from config for path normalization
    base_path = ""
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as cf:
            cfg = yaml.safe_load(cf) or {}
            base_path = cfg.get("base_path", "")

    print(f"Loading data from {export_json_path}...")
    with open(export_json_path, "r", encoding="utf-8") as f:
        task2_data = json.load(f)

    vue_files = task2_data.get("vue_files", [])
    file_flags = task2_data.get("file_flags", [])

    # Map flags to file ids
    flag_map = {}
    for flag_entry in file_flags:
        f_id = flag_entry.get("file_id")
        fname = flag_entry.get("flag_name")
        if f_id not in flag_map:
            flag_map[f_id] = []
        flag_map[f_id].append(fname)

    component_complexity = []

    for f_data in vue_files:
        file_path = f_data.get("file_path", "")
        file_id = f_data.get("id", 0)

        # Calculate true total lines by reading the file if it exists
        total_lines = 0
        full_path = os.path.join(base_path, file_path) if base_path else file_path
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as src:
                total_lines = sum(1 for line in src)
        elif os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as src:
                total_lines = sum(1 for line in src)
        else:
            # Fallback approximation if file is missing (though it shouldn't be)
            total_lines = (
                f_data.get("script_lines", 0) + f_data.get("template_lines", 0) + 10
            )

        # Normalize path using shared utility (handles both absolute and relative paths)
        clean_file_path = normalize_path(file_path, base_path)

        # Gather metrics matching Task 3 & Phase 1 API requirements
        metrics = {
            "file": clean_file_path,
            "lines": total_lines,
            "methods": f_data.get("methods", 0),
            "computed": f_data.get("computed", 0),
            "watchers": f_data.get("watchers", 0),
            "templateLines": f_data.get("template_lines", 0),
            "childComponents": f_data.get("child_components", 0),
            "apiCalls": f_data.get("api_total", 0),
            "apiMounted": f_data.get("api_mounted", 0),
        }

        # Use full orchestrated flags from DB export
        metrics["flags"] = flag_map.get(file_id, [])

        component_complexity.append(metrics)

    output_data = {"componentComplexity": component_complexity}

    print(f"Writing {len(component_complexity)} records to {output_json_path}...")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print("Done! Task 3 Report Generated Successfully.")


if __name__ == "__main__":
    main()
