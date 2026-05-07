import { computed, type Ref } from 'vue'

import type { DefectPoint } from '../types'

function parseDate(v?: string) {
  if (!v) return 0
  const ms = Date.parse(v)
  return Number.isFinite(ms) ? ms : 0
}

export function useRecentFindings(defects: Ref<DefectPoint[]>, limit = 5) {
  const recent = computed(() => {
    return defects.value
      .slice()
      .sort((a, b) => parseDate(b.foundAt) - parseDate(a.foundAt))
      .slice(0, limit)
  })

  return { recent }
}

