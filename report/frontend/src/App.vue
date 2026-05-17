<template>
  <div class="h-screen w-screen flex font-sans antialiased min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-50 transition-colors duration-300">
    <Sidebar />
    <div class="app-main flex flex-col flex-1 min-w-0">
      <Navigation />
      <main class="app-content flex-1 overflow-y-auto pb-12 relative">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
    <CommandPalette />
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Navigation from './components/Navigation.vue'
import CommandPalette from './components/CommandPalette.vue'
import { useTheme } from './composables/useTheme'

// Initialize theme on app load
useTheme()
</script>


