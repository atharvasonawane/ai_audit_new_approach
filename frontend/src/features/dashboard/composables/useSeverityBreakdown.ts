import { computed, type Ref } from 'vue'

import type { DefectPoint, Severity } from '../types'

const severityOrder: Severity[] = ['critical', 'high', 'medium', 'low']
const severityWeights: Record<Severity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
}

export function useSeverityBreakdown(defects: Ref<DefectPoint[]>) {
  const total = computed(() => defects.value.reduce((acc, d) => acc + d.count, 0))

  const bySeverity = computed(() => {
    const map = new Map<Severity, number>([
      ['critical', 0],
      ['high', 0],
      ['medium', 0],
      ['low', 0],
    ])

    for (const d of defects.value) {
      map.set(d.severity, (map.get(d.severity) ?? 0) + d.count)
    }

    const denom = total.value || 1
    return severityOrder.map((s) => {
      const count = map.get(s) ?? 0
      const percent = Math.round((count / denom) * 100)
      const weight = severityWeights[s]
      return { severity: s, count, percent, weight }
    })
  })

  return {
    total,
    bySeverity,
  }
}

