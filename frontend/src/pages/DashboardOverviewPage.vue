<script setup lang="ts">
import { useDashboardSummary } from '../features/dashboard/composables/useDashboardSummary'

import HeroSummary from '../features/dashboard/components/HeroSummary.vue'
import HealthScoreCard from '../features/dashboard/components/HealthScoreCard.vue'
import SeverityBreakdownCard from '../features/dashboard/components/SeverityBreakdownCard.vue'
import TopRiskyFilesTable from '../features/dashboard/components/TopRiskyFilesTable.vue'
import RecentFindingsPanel from '../features/dashboard/components/RecentFindingsPanel.vue'
import ScanMetadataCard from '../features/dashboard/components/ScanMetadataCard.vue'
import ComplexitySummaryCard from '../features/dashboard/components/ComplexitySummaryCard.vue'
import IssueCategoryBreakdownCard from '../features/dashboard/components/IssueCategoryBreakdownCard.vue'

const { isLoading, kpis, defects, trends, scan, complexity } = useDashboardSummary()
</script>

<template>
  <section class="space-y-10 pb-10">
    <p v-if="isLoading" class="text-sm text-muted-foreground animate-pulse">Loading dashboard…</p>

    <template v-else>
      <HeroSummary :kpis="kpis" />

      <!-- Section: Audit Intelligence -->
      <div class="space-y-5">
        <h2 class="text-lg font-bold tracking-tight text-foreground border-b border-border pb-2 inline-block">Audit Intelligence</h2>
        <div class="grid gap-6 lg:grid-cols-12">
          <div class="lg:col-span-5 flex">
            <HealthScoreCard :kpis="kpis" :trends="trends" class="w-full flex-1" />
          </div>
          <div class="lg:col-span-7 grid grid-rows-2 gap-6">
            <SeverityBreakdownCard :defects="defects" class="w-full" />
            <IssueCategoryBreakdownCard :defects="defects" class="w-full" />
          </div>
        </div>
        <div class="grid gap-6 lg:grid-cols-12 mt-6">
          <div class="lg:col-span-12 flex">
            <TopRiskyFilesTable :defects="defects" class="w-full flex-1" />
          </div>
        </div>
      </div>

      <!-- Section: System Diagnostics -->
      <div class="space-y-5">
        <h2 class="text-lg font-bold tracking-tight text-foreground border-b border-border pb-2 inline-block">System Diagnostics</h2>
        <div class="grid gap-6 lg:grid-cols-12">
          <div class="lg:col-span-7">
            <RecentFindingsPanel :defects="defects" />
          </div>
          <div class="lg:col-span-5 space-y-6">
            <ComplexitySummaryCard :summary="complexity" />
            <ScanMetadataCard :scan="scan" />
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
