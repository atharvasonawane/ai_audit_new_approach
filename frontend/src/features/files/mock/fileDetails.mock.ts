import type { AuditFileDetail } from '../types'
import { mockAuditFiles } from './files.mock'

export const mockFileDetails: Record<string, AuditFileDetail> = {
  f1: {
    ...mockAuditFiles[0], // src/components/tables/FindingsTable.vue
    last_analyzed: '2026-05-07T08:14:00Z',
    tags: ['UI Component', 'Data Grid', 'Vue'],
    findings: [
      { id: 'fn-1', line: 42, category: 'complexity', severity: 'high', message: 'Nesting depth of 6 exceeds maximum recommended depth of 4.', code_snippet: '        if (row.hasDetails) {\n          if (row.details.isExpanded) {\n            // ...' },
      { id: 'fn-2', line: 12, category: 'accessibility', severity: 'medium', message: 'Missing aria-label on interactive table header control.' },
      { id: 'fn-3', line: 85, category: 'payload', severity: 'medium', message: 'Large DOM payload detected. Consider virtual scrolling for lists over 100 items.' },
      { id: 'fn-4', line: 104, category: 'accessibility', severity: 'low', message: 'Contrast ratio of 3.14 on muted text falls below WCAG AA threshold.' },
    ]
  },
  f2: {
    ...mockAuditFiles[1], // src/features/orders/OrdersList.vue
    last_analyzed: '2026-05-07T08:15:00Z',
    tags: ['Feature', 'List', 'Heavy Payload'],
    findings: [
      { id: 'fn-5', line: 210, category: 'complexity', severity: 'critical', message: 'God component detected (1050 LOC). Split responsibilities across smaller modules.' },
      { id: 'fn-6', line: 315, category: 'architecture', severity: 'high', message: 'Direct DOM manipulation detected outside of Vue refs/directives.', code_snippet: 'document.getElementById("order-tbl").style.height = ...' },
      { id: 'fn-7', line: 84, category: 'api', severity: 'medium', message: '7 concurrent API calls fired iteratively. Suggest using Promise.all or an orchestrator.' },
      { id: 'fn-8', line: 400, category: 'complexity', severity: 'high', message: 'Cyclomatic complexity of 45 in `processOrdersData` method.' },
    ]
  },
  // Default mock for missing IDs
}

export function getMockFileDetail(id: string): AuditFileDetail | null {
  if (mockFileDetails[id]) return mockFileDetails[id]
  
  // Fallback generator for other files
  const base = mockAuditFiles.find(f => f.id === id)
  if (!base) return null
  
  return {
    ...base,
    last_analyzed: '2026-05-07T08:20:00Z',
    tags: ['Auto-Generated', 'Analyzed'],
    findings: [
      { id: 'fn-99', line: 1, category: 'info', severity: 'info', message: 'Analysis complete. File generally conforms to standards.' }
    ]
  }
}
