<template>
  <div class="app-layout">
    <Sidebar />
    <div class="app-main">
      <Navigation />
      <main class="app-content">
        <router-view />
      </main>
    </div>
    <CommandPalette />
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Navigation from './components/Navigation.vue'
import CommandPalette from './components/CommandPalette.vue'
</script>

<style scoped>
.app-layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  display: flex;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.app-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}
</style>
