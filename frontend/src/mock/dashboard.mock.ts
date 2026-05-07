import type { DefectPoint, KpiMetric, TrendPoint } from '../features/dashboard/types'
import type { ComplexitySummary, ScanMetadata } from '../features/dashboard/types'

export const dashboardKpis: KpiMetric[] = [
  { label: 'Health Score', value: '82', delta: '+4.3%' },
  { label: 'Open Defects', value: '219', delta: '-12.1%' },
  { label: 'High Risk Files', value: '37', delta: '-2.4%' },
]

export const dashboardDefects: DefectPoint[] = [
  {
    id: 'd1',
    file: 'src/pages/Home.vue',
    category: 'Accessibility',
    severity: 'high',
    count: 14,
    foundAt: '2026-05-07T10:30:00.000Z',
  },
  {
    id: 'd2',
    file: 'src/components/NavBar.vue',
    category: 'UI Consistency',
    severity: 'medium',
    count: 9,
    foundAt: '2026-05-06T18:12:00.000Z',
  },
  {
    id: 'd3',
    file: 'src/features/orders/OrdersList.vue',
    category: 'Complexity',
    severity: 'critical',
    count: 5,
    foundAt: '2026-05-07T09:02:00.000Z',
  },
  {
    id: 'd4',
    file: 'src/components/tables/FindingsTable.vue',
    category: 'UI Consistency',
    severity: 'high',
    count: 11,
    foundAt: '2026-05-05T13:44:00.000Z',
  },
  {
    id: 'd5',
    file: 'src/features/dashboard/components/SeverityBreakdownCard.vue',
    category: 'Accessibility',
    severity: 'medium',
    count: 7,
    foundAt: '2026-05-07T08:40:00.000Z',
  },
  {
    id: 'd6',
    file: 'src/features/api/ApiClient.ts',
    category: 'Complexity',
    severity: 'low',
    count: 4,
    foundAt: '2026-05-04T11:20:00.000Z',
  },
]

export const dashboardTrends: TrendPoint[] = [
  { date: 'Mon', score: 74 },
  { date: 'Tue', score: 76 },
  { date: 'Wed', score: 78 },
  { date: 'Thu', score: 80 },
  { date: 'Fri', score: 82 },
]

export const scanMetadata: ScanMetadata = {
  scannedAt: '2026-05-07T10:42:12.000Z',
  filesScanned: 114,
  durationSeconds: 19,
  toolVersion: '0.3.0',
  profileName: 'vue-enterprise-default',
}

export const complexitySummary: ComplexitySummary = {
  componentsAnalyzed: 114,
  avgComplexity: 9.6,
  p95Complexity: 24.2,
  highComplexityCount: 8,
}
