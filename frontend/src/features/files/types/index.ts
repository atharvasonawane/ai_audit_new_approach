export interface AuditFile {
  id: string
  file_path: string
  script_lines: number
  template_lines: number
  methods: number
  api_total: number
  max_nesting_depth: number
  payload_size_kb: number
  flag_count: number
  confidence: number
  accessibility_defects: number
  health_score: number // computed conceptually
}
