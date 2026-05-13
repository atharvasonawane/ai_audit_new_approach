<template>
  <nav class="topnav">
    <div class="topnav-left">
      <div class="breadcrumb">
        <span class="breadcrumb-item muted">Code Audit</span>
        <span class="breadcrumb-sep">/</span>
        <span class="breadcrumb-item active">{{ pageTitle }}</span>
      </div>
    </div>
    <div class="topnav-right">
      <button class="cmd-pill" @click="handleSearch" title="Search (Cmd+K)">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="6.5" cy="6.5" r="5"/>
          <path d="M10.5 10.5L14 14"/>
        </svg>
        <span>Search</span>
        <kbd>⌘K</kbd>
      </button>
      <button class="icon-btn" @click="handleSettings" title="Settings">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="8" cy="8" r="2.5"/>
          <path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3.05 3.05l1.06 1.06M11.89 11.89l1.06 1.06M3.05 12.95l1.06-1.06M11.89 4.11l1.06-1.06"/>
        </svg>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageTitle = computed(() => {
  const titles = { '/': 'Home', '/dashboard': 'Dashboard', '/audit': 'Audit Explorer', '/analyzing': 'Analyzing' }
  return titles[route.path] || 'Code Audit Librarian'
})

const handleSearch = () => { console.log('Search triggered') }
const handleSettings = () => { console.log('Settings triggered') }
</script>

<style scoped>
.topnav {
  height: 48px;
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.topnav-left, .topnav-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.breadcrumb-item { color: var(--color-text-secondary); font-weight: 500; }
.breadcrumb-item.active { color: var(--color-text-primary); }
.breadcrumb-item.muted { color: var(--color-text-tertiary); }
.breadcrumb-sep { color: var(--color-text-tertiary); font-size: 12px; }

.cmd-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-base);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms;
}

.cmd-pill:hover {
  background: var(--color-bg-hover);
  border-color: rgba(56,139,253,0.4);
  color: var(--color-text-primary);
}

.cmd-pill kbd {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 4px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-emphasis);
  border-radius: 3px;
  color: var(--color-text-tertiary);
}

.icon-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--rounded-base);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 150ms;
}

.icon-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}
</style>
