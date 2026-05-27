import sqlite3, os
conn = sqlite3.connect('audit_history.db')
conn.row_factory = sqlite3.Row

print('=== AUDIT RUNS ===')
for r in conn.execute('SELECT id, project_name, status, started_at, completed_at, total_files, last_completed_file FROM audit_runs ORDER BY id DESC'):
    print('  run_id=%s | status=%s | total_files=%s | last_file=%s' % (
        r['id'], r['status'], r['total_files'], r['last_completed_file']))

print()
print('=== COUNTS ===')
print('  vue_files   :', conn.execute('SELECT COUNT(*) FROM vue_files').fetchone()[0])
print('  ai_issues   :', conn.execute('SELECT COUNT(*) FROM ai_issues').fetchone()[0])
print('  file_flags  :', conn.execute('SELECT COUNT(*) FROM file_flags').fetchone()[0])

print()
print('=== AI ANALYSIS PROGRESS ===')
for r in conn.execute("SELECT DISTINCT file_path FROM ai_issues ORDER BY file_path"):
    cnt = conn.execute('SELECT COUNT(*) FROM ai_issues WHERE file_path=?', (r['file_path'],)).fetchone()[0]
    print('  %s (%d issues)' % (r['file_path'], cnt))

conn.close()
