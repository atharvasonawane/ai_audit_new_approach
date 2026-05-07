<script setup lang="ts">
import { RouterView } from 'vue-router'

import DashboardShell from '../components/shell/DashboardShell.vue'
</script>

<template>
  <DashboardShell title="Engineering Dashboard">
    <RouterView />
  </DashboardShell>
</template>
