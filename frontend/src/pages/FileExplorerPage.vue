<script setup lang="ts">
import { mockAuditFiles } from '../features/files/mock/files.mock'
import FileExplorerTable from '../features/files/components/FileExplorerTable.vue'
import BaseCard from '../components/dashboard/BaseCard.vue'

// In a real app we would use a composable to fetch this data 
// e.g. const { data: files, isLoading } = useFileExplorer()
</script>

<template>
  <div class="h-full flex flex-col gap-6">
    <header class="flex flex-col gap-1 shrink-0">
      <h1 class="text-2xl font-bold tracking-tight text-foreground">File Explorer</h1>
      <p class="text-sm text-muted-foreground">Detailed audit metrics and signals mapped by individual source files.</p>
    </header>

    <main class="flex-1 min-h-0">
      <FileExplorerTable :files="mockAuditFiles" />
    </main>
  </div>
</template>
