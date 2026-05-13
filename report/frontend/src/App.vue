<template>
  <div class="h-screen w-screen overflow-hidden text-text-primary bg-bg-primary flex">
    <!-- Sidebar -->
    <Sidebar />

    <!-- Main Content Column -->
    <div class="flex-1 flex flex-col">
      <!-- Navigation Header -->
      <Navigation />

      <!-- Main Content Area with Router View -->
      <main class="flex-1 overflow-auto p-6">
        <router-view />
      </main>
    </div>

    <!-- Global Command Palette -->
    <CommandPalette />
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Navigation from './components/Navigation.vue'
import CommandPalette from './components/CommandPalette.vue'
</script>

<style scoped>
/* Layout handled by Tailwind and CSS variables */
</style>
