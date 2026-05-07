import { computed, type Ref } from 'vue'

import type { DefectPoint, Severity } from '../types'

const severityWeights: Record<Severity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
}

function riskScore(defects: DefectPoint[]) {
  // Weighted by severity count contribution.
  return defects.reduce((acc, d) => acc + d.count * severityWeights[d.severity], 0)
}

export function useRiskyFiles(defects: Ref<DefectPoint[]>, limit = 5) {
  const riskyFiles = computed(() => {
    const byFile = new Map<string, DefectPoint[]>()
    for (const d of defects.value) {
      const list = byFile.get(d.file) ?? []
      list.push(d)
      byFile.set(d.file, list)
    }

    const rows = Array.from(byFile.entries()).map(([file, fileDefects]) => {
      const score = riskScore(fileDefects)
      const topSeverity = fileDefects
        .slice()
        .sort((a, b) => severityWeights[b.severity] - severityWeights[a.severity])[0]?.severity

      return {
        file,
        score,
        topSeverity: topSeverity ?? 'low',
        defects: fileDefects.reduce((acc, x) => acc + x.count, 0),
      }
    })

    return rows.sort((a, b) => b.score - a.score).slice(0, limit)
  })

  return { riskyFiles }
}

