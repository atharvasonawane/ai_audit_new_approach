import sys
import os
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
AUDIT_TOOL_DIR = BASE_DIR / "audit_tool"
TASK2_DIR = AUDIT_TOOL_DIR / "task2_audit"
sys.path.insert(0, str(TASK2_DIR))

from extractors.script_cleaner import clean_script
from extractors.api_extractor import (
    count_payload_keys,
    calculate_payload_depth,
    calculate_payload_size_kb,
)

print("=== Testing Payload Calculation Functions ===")

samples = [
    {
        "name": "Sample 1: Simple payload with 3 keys at depth 1",
        "script": """
        export default {
            mounted() {
                this.$http.post('/api/users', {"name": "John", "email": "john@example.com", "age": 30});
            }
        }
        """,
    },
    {
        "name": "Sample 2: Nested payload at depth 3",
        "script": """
        export default {
            mounted() {
                this.$http.post('/api/data', {"user": {"profile": {"name": "Jane"}}});
            }
        }
        """,
    },
    {
        "name": "Sample 3: Multiple API calls",
        "script": """
        export default {
            mounted() {
                // Call 1: 1 key
                axios.put('/api/1', {"test": 1});
                
                // Call 2: 2 keys
                new MQL().setActivity("o.[method]").setData({"a": 1, "b": {"c": 2}}).fetch();
            }
        }
        """,
    },
    {
        "name": "Sample 4: API call with NO payload",
        "script": """
        export default {
            mounted() {
                this.$http.get('/api/users');
                axios.get('/api/data');
                fetch('/api/users');
            }
        }
        """,
    },
]

for idx, sample in enumerate(samples, 1):
    print(f"\n--- {sample['name']} ---")
    # Clean the script exactly as the orchestrator does
    cleaned = clean_script(sample["script"])

    # Run the new functions
    keys = count_payload_keys(cleaned)
    depth = calculate_payload_depth(cleaned)
    size_kb = calculate_payload_size_kb(cleaned)

    print(f"Results:")
    print(f"  - Total Keys : {keys}")
    print(f"  - Max Depth  : {depth}")
    print(f"  - Size (KB)  : {size_kb:.4f} KB")

print("\n=============================================")
