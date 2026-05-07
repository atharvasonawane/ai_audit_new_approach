<script setup lang="ts">
import { computed } from 'vue'

import InsightPanel from '../../../components/dashboard/InsightPanel.vue'
import type { ScanMetadata } from '../types'

const props = defineProps<{
  scan: ScanMetadata | null
}>()

const scannedAt = computed(() => {
  const raw = props.scan?.scannedAt
  if (!raw) return '—'
  const ms = Date.parse(raw)
  if (!Number.isFinite(ms)) return '—'
  return new Date(ms).toISOString().replace('T', ' ').slice(0, 19) + 'Z'
})
</script>

<template>
  <InsightPanel title="Scan metadata" description="Audit run context for traceability.">
    <div class="px-6 py-4 text-sm">
      <dl class="grid grid-cols-2 gap-x-6 gap-y-3">
        <div>
          <dt class="text-xs text-muted-foreground">Scanned at</dt>
          <dd class="mt-1 font-medium text-foreground">{{ scannedAt }}</dd>
        </div>
        <div>
          <dt class="text-xs text-muted-foreground">Files</dt>
          <dd class="mt-1 font-medium text-foreground">{{ scan?.filesScanned ?? '—' }}</dd>
        </div>
        <div>
          <dt class="text-xs text-muted-foreground">Duration</dt>
          <dd class="mt-1 font-medium text-foreground">
            {{ scan?.durationSeconds != null ? `${scan.durationSeconds}s` : '—' }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-muted-foreground">Profile</dt>
          <dd class="mt-1 font-medium text-foreground">{{ scan?.profileName ?? '—' }}</dd>
        </div>
        <div class="col-span-2">
          <dt class="text-xs text-muted-foreground">Tool version</dt>
          <dd class="mt-1 font-medium text-foreground">{{ scan?.toolVersion ?? '—' }}</dd>
        </div>
      </dl>
    </div>
  </InsightPanel>
</template>

