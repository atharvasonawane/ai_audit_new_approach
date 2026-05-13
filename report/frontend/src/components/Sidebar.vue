<template>
  <aside class="bg-bg-secondary border-r border-border w-64 h-screen flex flex-col">
    <!-- Logo/Title Section -->
    <div class="px-6 py-8 border-b border-border">
      <h1 class="font-mono font-bold text-text-primary text-lg tracking-tight">
        CODE AUDIT LIBRARIAN
      </h1>
      <p class="text-text-tertiary text-xs mt-1">
        Vue.js Codebase Analysis
      </p>
    </div>

    <!-- Navigation Links -->
    <nav class="flex-1 px-4 py-6">
      <div class="space-y-1">
        <router-link
          to="/"
          class="nav-link"
          :class="{ active: isActive('/') }"
        >
          <Home :size="20" :stroke-width="2" />
          <span>Home</span>
        </router-link>

        <router-link
          to="/dashboard"
          class="nav-link"
          :class="{ active: isActive('/dashboard') }"
        >
          <LayoutDashboard :size="20" :stroke-width="2" />
          <span>Dashboard</span>
        </router-link>

        <router-link
          to="/audit"
          class="nav-link"
          :class="{ active: isActive('/audit') }"
        >
          <FolderSearch :size="20" :stroke-width="2" />
          <span>Audit Explorer</span>
        </router-link>
      </div>
    </nav>

    <!-- Footer -->
    <div class="px-6 py-4 border-t border-border">
      <p class="text-text-tertiary text-xs font-mono">
        v1.0.0
      </p>
    </div>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { Home, LayoutDashboard, FolderSearch } from 'lucide-vue-next'

const route = useRoute()

const isActive = (path) => {
  return route.path === path
}
</script>

<style scoped>
.nav-link {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-radius: var(--rounded-base);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 200ms ease-out;
  gap: 12px;
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: 500;
}

.nav-link:hover {
  color: var(--color-text-primary);
  background-color: var(--color-bg-hover);
}

.nav-link.active {
  color: var(--color-accent-primary);
  background-color: var(--color-bg-tertiary);
  border-left: 3px solid var(--color-accent-primary);
  padding-left: 13px;
}
</style>
