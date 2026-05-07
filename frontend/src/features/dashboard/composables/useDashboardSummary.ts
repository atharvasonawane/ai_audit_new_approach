import { computed, onMounted, ref } from 'vue'

import { dashboardService } from '../services/dashboard.service'
import type { ComplexitySummary, DefectPoint, KpiMetric, ScanMetadata, TrendPoint } from '../types'

export function useDashboardSummary() {
  const isLoading = ref(false)
  const kpis = ref<KpiMetric[]>([])
  const defects = ref<DefectPoint[]>([])
  const trends = ref<TrendPoint[]>([])
  const scan = ref<ScanMetadata | null>(null)
  const complexity = ref<ComplexitySummary | null>(null)

  const criticalDefects = computed(() =>
    defects.value.filter((item) => item.severity === 'critical'),
  )

  const load = async () => {
    isLoading.value = true
    try {
      ;[kpis.value, defects.value, trends.value, scan.value, complexity.value] = await Promise.all([
        dashboardService.getKpis(),
        dashboardService.getDefects(),
        dashboardService.getTrends(),
        dashboardService.getScanMetadata(),
        dashboardService.getComplexitySummary(),
      ])
    } finally {
      isLoading.value = false
    }
  }

  onMounted(load)

  return {
    isLoading,
    kpis,
    defects,
    trends,
    scan,
    complexity,
    criticalDefects,
    refresh: load,
  }
}
