<template>
  <aside class="bg-bg-primary border-r border-border w-64 h-screen flex flex-col">
    <!-- Logo Section -->
    <div class="px-6 py-8 border-b border-border">
      <div class="flex items-center" style="gap: 8px;">
        <span class="text-2xl">📊</span>
        <span class="text-text-primary font-display font-bold text-sm">
          AUDIT
        </span>
      </div>
    </div>

    <!-- Navigation Links -->
    <nav class="flex-1 px-4 py-6 space-y-2">
      <router-link
        to="/"
        class="nav-link"
        :class="{ active: isActive('/') }"
      >
        <span class="text-lg">📈</span>
        <span>Dashboard</span>
      </router-link>

      <router-link
        to="/audit"
        class="nav-link"
        :class="{ active: isActive('/audit') }"
      >
        <span class="text-lg">🔍</span>
        <span>Audit Explorer</span>
      </router-link>
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
}

.nav-link:hover {
  color: var(--color-text-primary);
  background-color: var(--color-bg-tertiary);
}

.nav-link.active {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border-left: 3px solid var(--color-accent-primary);
  padding-left: 13px;
}
</style>
