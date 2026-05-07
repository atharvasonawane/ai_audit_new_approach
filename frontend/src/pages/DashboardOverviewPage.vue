<script setup lang="ts">
import { useDashboardSummary } from '../features/dashboard/composables/useDashboardSummary'

import HeroSummary from '../features/dashboard/components/HeroSummary.vue'
import HealthScoreCard from '../features/dashboard/components/HealthScoreCard.vue'
import SeverityBreakdownCard from '../features/dashboard/components/SeverityBreakdownCard.vue'
import TopRiskyFilesTable from '../features/dashboard/components/TopRiskyFilesTable.vue'
import RecentFindingsPanel from '../features/dashboard/components/RecentFindingsPanel.vue'
import ScanMetadataCard from '../features/dashboard/components/ScanMetadataCard.vue'
import ComplexitySummaryCard from '../features/dashboard/components/ComplexitySummaryCard.vue'

const { isLoading, kpis, defects, trends, scan, complexity } = useDashboardSummary()
</script>

<template>
  <section class="space-y-6">
    <p v-if="isLoading" class="text-sm text-muted-foreground">Loading dashboard…</p>

    <template v-else>
      <HeroSummary :kpis="kpis" />

      <div class="grid gap-6 lg:grid-cols-12">
        <div class="lg:col-span-4">
          <HealthScoreCard :kpis="kpis" :trends="trends" />
        </div>

        <div class="lg:col-span-8">
          <SeverityBreakdownCard :defects="defects" />
        </div>

        <div class="lg:col-span-7">
          <TopRiskyFilesTable :defects="defects" />
        </div>

        <div class="lg:col-span-5">
          <RecentFindingsPanel :defects="defects" />
        </div>

        <div class="lg:col-span-7">
          <ComplexitySummaryCard :summary="complexity" />
        </div>

        <div class="lg:col-span-5">
          <ScanMetadataCard :scan="scan" />
        </div>
      </div>
    </template>
  </section>
</template>
