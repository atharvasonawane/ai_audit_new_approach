<template>
  <div class="flex h-screen w-screen bg-bg-primary text-text-primary">
    <!-- Sidebar -->
    <Sidebar />

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col">
      <!-- Navigation Header -->
      <Navigation />

      <!-- Router View -->
      <router-view />
    </div>
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Navigation from './components/Navigation.vue'
</script>

<style scoped>
/* Layout handled by Tailwind */
</style>
