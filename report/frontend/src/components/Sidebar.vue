<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo">
      <div class="logo-icon">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <rect x="1" y="1" width="8" height="8" rx="1.5" fill="#388BFD" opacity="0.9"/>
          <rect x="11" y="1" width="8" height="8" rx="1.5" fill="#8957E5" opacity="0.7"/>
          <rect x="1" y="11" width="8" height="8" rx="1.5" fill="#388BFD" opacity="0.5"/>
          <rect x="11" y="11" width="8" height="8" rx="1.5" fill="#388BFD" opacity="0.3"/>
        </svg>
      </div>
      <div class="logo-text">
        <span class="logo-title">Audit Lib</span>
        <span class="logo-sub">Vue.js Codebase Analysis</span>
      </div>
    </div>

    <!-- Nav -->
    <nav class="sidebar-nav">
      <div class="nav-section-label">Navigation</div>
      <router-link to="/" class="nav-item" :class="{ active: isActive('/') }">
        <svg class="nav-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M2 6.5L8 2l6 4.5V14a1 1 0 01-1 1H3a1 1 0 01-1-1V6.5z"/>
        </svg>
        <span>Home</span>
      </router-link>

      <router-link to="/dashboard" class="nav-item" :class="{ active: isActive('/dashboard') }">
        <svg class="nav-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="1" y="1" width="6" height="6" rx="1"/>
          <rect x="9" y="1" width="6" height="6" rx="1"/>
          <rect x="1" y="9" width="6" height="6" rx="1"/>
          <rect x="9" y="9" width="6" height="6" rx="1"/>
        </svg>
        <span>Dashboard</span>
      </router-link>

      <router-link to="/audit" class="nav-item" :class="{ active: isActive('/audit') }">
        <svg class="nav-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M3 2h7l3 3v9a1 1 0 01-1 1H3a1 1 0 01-1-1V3a1 1 0 011-1z"/>
          <path d="M10 2v4h4"/>
          <path d="M5 9h6M5 12h4"/>
        </svg>
        <span>Audit Explorer</span>
      </router-link>
    </nav>

    <!-- Footer -->
    <div class="sidebar-footer">
      <div class="version-badge">
        <span class="version-dot"></span>
        <span>v1.0.0</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()
const isActive = (path) => route.path === path
</script>

<style scoped>
.sidebar {
  width: 220px;
  min-width: 220px;
  height: 100vh;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: relative;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px 16px;
  border-bottom: 1px solid var(--color-border);
}

.logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.logo-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.03em;
}

.logo-sub {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-weight: 500;
  letter-spacing: 0.02em;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-section-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0 8px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  border-radius: var(--rounded-base);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  transition: all 150ms ease;
  position: relative;
}

.nav-item:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.nav-item.active {
  background: rgba(56, 139, 253, 0.12);
  color: #58A6FF;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  background: #388BFD;
  border-radius: 0 2px 2px 0;
}

.nav-icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  opacity: 0.85;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
}

.version-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.version-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-status-success);
  box-shadow: 0 0 6px var(--color-status-success);
}
</style>
