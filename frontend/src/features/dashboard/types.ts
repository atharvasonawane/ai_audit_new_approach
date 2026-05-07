export type Severity = 'critical' | 'high' | 'medium' | 'low'

export interface KpiMetric {
  label: string
  value: string
  delta?: string
}

export interface DefectPoint {
  id: string
  file: string
  category: string
  severity: Severity
  count: number
  /**
   * ISO timestamp used for "recent findings" ordering in the UI.
   * Optional because some audit outputs may not include a timestamp yet.
   */
  foundAt?: string
}

export interface TrendPoint {
  date: string
  score: number
}

export interface ScanMetadata {
  scannedAt: string
  filesScanned: number
  durationSeconds: number
  toolVersion: string
  profileName: string
}

export interface ComplexitySummary {
  componentsAnalyzed: number
  avgComplexity: number
  p95Complexity: number
  highComplexityCount: number
}
