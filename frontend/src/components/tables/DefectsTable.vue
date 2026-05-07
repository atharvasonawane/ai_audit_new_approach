<script setup lang="ts">
import BaseCard from '../ui/BaseCard.vue'
import type { DefectPoint } from '../../features/dashboard/types'

defineProps<{
  rows: DefectPoint[]
}>()
</script>

<template>
  <BaseCard>
    <div class="mb-3 flex items-center justify-between">
      <h2 class="text-sm font-medium">Top Defects</h2>
      <span class="text-xs text-zinc-500">Prioritized by severity</span>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full border-collapse text-left text-sm">
        <thead>
          <tr class="text-zinc-500">
            <th class="border-b border-zinc-100 py-2 font-medium">File</th>
            <th class="border-b border-zinc-100 py-2 font-medium">Category</th>
            <th class="border-b border-zinc-100 py-2 font-medium">Severity</th>
            <th class="border-b border-zinc-100 py-2 font-medium text-right">Count</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="text-zinc-700">
            <td class="border-b border-zinc-100 py-2">{{ row.file }}</td>
            <td class="border-b border-zinc-100 py-2">{{ row.category }}</td>
            <td class="border-b border-zinc-100 py-2 capitalize">{{ row.severity }}</td>
            <td class="border-b border-zinc-100 py-2 text-right font-medium">{{ row.count }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>
