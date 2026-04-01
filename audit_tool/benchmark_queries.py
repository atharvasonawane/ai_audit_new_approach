# benchmark_queries.py

BENCHMARK_QUERIES = [
    {
        "id": 1,
        "query": "Which files in the codebase are the most dangerous to refactor?",
        "expected_route": "summary",
        "notes": "Tests basic summary routing using 'most dangerous' keyword."
    },
    {
        "id": 2,
        "query": "Can you give me an overview of the overall health of our Vue files?",
        "expected_route": "summary",
        "notes": "Tests summary routing using 'overview' and 'health' concepts."
    },
    {
        "id": 3,
        "query": "What are the worst files we have right now in terms of risk?",
        "expected_route": "summary",
        "notes": "Tests summary routing using 'worst files' terminology."
    },
    {
        "id": 4,
        "query": "Show me the summary statistics for the latest static analysis run.",
        "expected_route": "summary",
        "notes": "Tests summary routing with explicit 'summary statistics' request."
    },
    {
        "id": 5,
        "query": "Which files have the highest number of issues overall?",
        "expected_route": "summary",
        "notes": "Tests summary routing focusing on issue counts."
    },
    {
        "id": 6,
        "query": "How risky is RoleMgt.vue? I need to make some changes to it.",
        "expected_route": "file",
        "notes": "Tests file routing with exact filename and 'how risky' pattern."
    },
    {
        "id": 7,
        "query": "Tell me about LoginPage.vue. What issues does it have?",
        "expected_route": "file",
        "notes": "Tests file routing with 'tell me about' phrase."
    },
    {
        "id": 8,
        "query": "I'm looking at Dashboard.vue, can you give me its metrics and risk level?",
        "expected_route": "file",
        "notes": "Tests file routing embedded naturally in a conversational sentence."
    },
    {
        "id": 9,
        "query": "Are there any accessibility defects in UserProfile.vue?",
        "expected_route": "file",
        "notes": "Tests file routing focusing on a specific defect type."
    },
    {
        "id": 10,
        "query": "Give me the full report for AdminPanel.vue please.",
        "expected_route": "file",
        "notes": "Tests file routing with a direct report request."
    },
    {
        "id": 11,
        "query": "What's the severity summary for Settings.vue?",
        "expected_route": "file",
        "notes": "Tests file routing asking for specific JSON keys (severity_summary)."
    },
    {
        "id": 12,
        "query": "Does ReportView.vue have any excessive API usage flags?",
        "expected_route": "file",
        "notes": "Tests file routing asking about specific flag names."
    },
    {
        "id": 13,
        "query": "Show me the details on DataTable.vue.",
        "expected_route": "file",
        "notes": "Tests file routing using 'show me' pattern."
    },
    {
        "id": 14,
        "query": "Can you verify if the MQL flags in RoleMgt.vue are actually false positives?",
        "expected_route": "verify",
        "notes": "Tests verify routing prioritizing 'false positive' and 'verify' over the filename."
    },
    {
        "id": 15,
        "query": "I see some API issues in LoginPage.vue, can you confirm if they are real?",
        "expected_route": "verify",
        "notes": "Tests verify routing using the 'confirm' keyword."
    },
    {
        "id": 16,
        "query": "Are these accessibility flags in Dashboard.vue false positives?",
        "expected_route": "verify",
        "notes": "Tests verify routing with 'false positives' keyword."
    },
    {
        "id": 17,
        "query": "Please check if the complexity warnings in RoleMgt.vue are accurate or false positives.",
        "expected_route": "verify",
        "notes": "Tests verify routing using 'check if' and 'false positives'."
    },
    {
        "id": 18,
        "query": "Verify the unlabelled input defects in LoginPage.vue for me.",
        "expected_route": "verify",
        "notes": "Tests verify routing with a direct 'Verify' command."
    },
    {
        "id": 19,
        "query": "Hey, how do I write a new Vue component from scratch?",
        "expected_route": "unknown",
        "notes": "Tests fallback routing for completely off-topic programming questions."
    },
    {
        "id": 20,
        "query": "Tell me about the login stuff.",
        "expected_route": "unknown",
        "notes": "Tests fallback routing for vague queries missing a .vue extension."
    }
]