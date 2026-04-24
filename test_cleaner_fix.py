import os
import sys
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
AUDIT_TOOL_DIR = BASE_DIR / "audit_tool"
TASK2_DIR = AUDIT_TOOL_DIR / "task2_audit"

# Add paths to sys.path so we can import internal modules easily
sys.path.insert(0, str(TASK2_DIR))

from extractors.script_cleaner import clean_script


def main():
    print("=== Testing Script Cleaner Fix ===")

    sample_script = """
    export default {
        mounted() {
            // This is a comment that should be removed
            let message = "Hello World"; // Random variable string, should be removed
            
            this.$http.post('/api/users', { "name": "John", "email": "test@example.com" });
            
            let payload = {
                "user": {
                    "profile": {
                        "name": "Jane"
                    }
                }
            };
            
            new MQL().setActivity('o.[LoginCopy]').setData({"action": "copy"}).fetch();
        }
    }
    """

    print("\n--- RAW INPUT ---")
    print(sample_script)

    cleaned = clean_script(sample_script)

    print("\n--- CLEANED OUTPUT ---")
    print(cleaned)

    print("\n--- VERIFICATION ---")
    passed = True

    # Check 1: Comment removed
    if "This is a comment" not in cleaned:
        print("✅ Comment removed successfully")
    else:
        print("❌ Comment NOT removed")
        passed = False

    # Check 2: Random string removed
    if "Hello World" not in cleaned:
        print("✅ Random string 'Hello World' removed successfully")
    else:
        print("❌ Random string 'Hello World' NOT removed")
        passed = False

    # Check 3: API arguments survived
    if "'o.[LoginCopy]'" in cleaned or '"o.[LoginCopy]"' in cleaned:
        print("✅ MQL string 'o.[LoginCopy]' survived")
    else:
        print("❌ MQL string 'o.[LoginCopy]' WAS REMOVED")
        passed = False

    # Check 4: Payload in API call survived
    if '"name"' in cleaned and '"John"' in cleaned and '"email"' in cleaned:
        print("✅ Inline payload keys/values ('name', 'John', 'email') survived")
    else:
        print("❌ Inline payload keys/values WERE REMOVED")
        passed = False

    # Check 5: Nested payload survived
    if '"user"' in cleaned and '"profile"' in cleaned and '"Jane"' in cleaned:
        print("✅ Nested payload keys/values ('user', 'profile', 'Jane') survived")
    else:
        print("❌ Nested payload keys/values WERE REMOVED")
        passed = False

    print("\n=============================================")
    if passed:
        print("✅ TEST PASSED: Relevant data preserved while junk is removed!")
    else:
        print("❌ TEST FAILED: Cleaner is still breaking data.")
    print("=============================================")


if __name__ == "__main__":
    main()
