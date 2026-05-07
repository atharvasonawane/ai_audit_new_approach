<script setup lang="ts">
import { BarChart3, Files, FlagTriangleRight, LayoutDashboard, Settings, Library as LibraryIcon } from 'lucide-vue-next'
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
        'flex h-full w-[260px] flex-col border-r border-border bg-card/30',
        $props.class,
      )
    "
  >
    <div class="flex h-14 items-center px-5">
      <div class="flex h-8 w-8 items-center justify-center rounded-md bg-foreground text-background mr-3">
        <LibraryIcon class="h-4 w-4" v-if="LibraryIcon" />
      </div>
      <div class="min-w-0">
        <p class="truncate text-sm font-bold tracking-tight text-foreground">
          Audit Librarian
        </p>
      </div>
    </div>

    <nav class="flex-1 px-3 py-4 space-y-1">
      <RouterLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        active-class="bg-accent/50 text-foreground font-semibold"
      >
        <component :is="item.icon" class="h-4 w-4" />
        <span class="truncate">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="p-3">
      <RouterLink
        to="/settings"
        class="group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        active-class="bg-accent/50 text-foreground"
      >
        <Settings class="h-4 w-4" />
        <span class="truncate">Settings</span>
      </RouterLink>
    </div>
  </aside>
</template>

