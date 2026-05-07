<script setup lang="ts">
import { BarChart3, Files, FlagTriangleRight, LayoutDashboard, Settings } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'

import { cn } from '../../lib/utils'

type NavItem = {
  label: string
  to: string
  icon: any
}

const items: NavItem[] = [
  { label: 'Overview', to: '/', icon: LayoutDashboard },
  { label: 'Defects', to: '/defects', icon: FlagTriangleRight },
  { label: 'Files', to: '/files', icon: Files },
  { label: 'Trends', to: '/trends', icon: BarChart3 },
]

defineProps<{
  class?: string
}>()
</script>

<template>
  <aside
    :class="
      cn(
        'flex h-full w-[260px] flex-col border-r border-border/70 bg-background',
        $props.class,
      )
    "
  >
    <div class="flex h-12 items-center px-4">
      <div class="min-w-0">
        <p class="truncate text-sm font-semibold tracking-tight text-foreground">
          Code Audit Librarian
        </p>
        <p class="truncate text-xs text-muted-foreground">Engineering intelligence</p>
      </div>
    </div>

    <nav class="flex-1 px-2 py-2">
      <RouterLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="group flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
        active-class="bg-accent text-foreground"
      >
        <component :is="item.icon" class="h-4 w-4 opacity-90" />
        <span class="truncate">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="border-t border-border/70 p-2">
      <RouterLink
        to="/settings"
        class="group flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
        active-class="bg-accent text-foreground"
      >
        <Settings class="h-4 w-4 opacity-90" />
        <span class="truncate">Settings</span>
      </RouterLink>
    </div>
  </aside>
</template>

