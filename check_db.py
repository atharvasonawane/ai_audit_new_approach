import sqlite3

conn = sqlite3.connect('audit_history.db')
conn.row_factory = sqlite3.Row

print('=== AUDIT RUNS ===')
rows = conn.execute('SELECT id, project_name, status, started_at, completed_at, total_files, last_completed_file FROM audit_runs ORDER BY id DESC LIMIT 10').fetchall()
for r in rows:
    print("  run_id=%s | project=%s | status=%s | started=%s | completed=%s | total_files=%s | last_file=%s" % (
        r['id'], r['project_name'], r['status'], r['started_at'], r['completed_at'], r['total_files'], r['last_completed_file']
    ))

print()
print('=== VUE FILES per run (latest 3 runs) ===')
run_ids = [r['id'] for r in rows[:3]]
for rid in run_ids:
    cnt = conn.execute('SELECT COUNT(*) FROM vue_files WHERE run_id=?', (rid,)).fetchone()[0]
    print("  run_id=%s: %s vue_files" % (rid, cnt))

print()
print('=== AI ISSUES per run (latest 3 runs) ===')
for rid in run_ids:
    cnt = conn.execute('SELECT COUNT(*) FROM ai_issues WHERE run_id=?', (rid,)).fetchone()[0]
    distinct_files = conn.execute('SELECT COUNT(DISTINCT file_path) FROM ai_issues WHERE run_id=?', (rid,)).fetchone()[0]
    print("  run_id=%s: %s ai_issues across %s distinct files" % (rid, cnt, distinct_files))

print()
print('=== DISTINCT AI ANALYSIS FILES (latest run) ===')
if run_ids:
    latest = run_ids[0]
    files = conn.execute('SELECT DISTINCT file_path FROM ai_issues WHERE run_id=? ORDER BY file_path', (latest,)).fetchall()
    for f in files:
        print("  %s" % f[0])

print()
print('=== VUE FILES LIST (latest run) ===')
if run_ids:
    latest = run_ids[0]
    vf = conn.execute('SELECT file_path, script_lines FROM vue_files WHERE run_id=? ORDER BY file_path', (latest,)).fetchall()
    for f in vf:
        print("  %s (script_lines=%s)" % (f['file_path'], f['script_lines']))

conn.close()
