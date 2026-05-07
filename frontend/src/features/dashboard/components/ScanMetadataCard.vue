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
  <InsightPanel title="Scan Metadata & Traces" description="Audit run context for data traceability.">
    <div class="px-8 py-6 text-sm">
      <dl class="grid grid-cols-2 gap-x-8 gap-y-6">
        <div>
          <dt class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Timestamp</dt>
          <dd class="mt-1.5 font-mono text-[13px] font-medium text-foreground bg-accent/40 rounded px-1.5 py-0.5 inline-block">{{ scannedAt }}</dd>
        </div>
        <div>
          <dt class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Files Parsed</dt>
          <dd class="mt-1.5 text-base font-semibold text-foreground">{{ scan?.filesScanned ?? '—' }}</dd>
        </div>
        <div>
          <dt class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Compute Time</dt>
          <dd class="mt-1.5 text-base font-semibold text-foreground">
            {{ scan?.durationSeconds != null ? `${scan.durationSeconds}s` : '—' }}
          </dd>
        </div>
        <div>
          <dt class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Profile</dt>
          <dd class="mt-1.5 text-base font-semibold text-foreground">{{ scan?.profileName ?? '—' }}</dd>
        </div>
        <div class="col-span-2 pt-2 border-t border-border/50">
          <dt class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Engine Version</dt>
          <dd class="mt-1.5 font-mono text-[13px] font-medium text-foreground">{{ scan?.toolVersion ?? '—' }}</dd>
        </div>
      </dl>
    </div>
  </InsightPanel>
</template>

