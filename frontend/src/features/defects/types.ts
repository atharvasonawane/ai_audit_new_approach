export type DefectSeverity = 'critical' | 'high' | 'medium' | 'low'

export interface A11yDefect {
  id: string
  file_path: string
  line: number
  rule_name: string
  message: string
  severity: DefectSeverity
  snippet?: string
}

export interface DefectSummary {
  rule_name: string
  description: string
  count: number
  severity: DefectSeverity
}
