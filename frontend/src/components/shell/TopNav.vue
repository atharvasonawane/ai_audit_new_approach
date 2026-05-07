<script setup lang="ts">
import { Search, Sun, Moon } from 'lucide-vue-next'

import { cn } from '../../lib/utils'
import { useTheme } from '../../theme/useTheme'

defineProps<{
  title?: string
  class?: string
}>()

const { isDark, toggle } = useTheme()
</script>

<template>
  <header
    :class="
      cn(
        'sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60',
        $props.class,
      )
    "
  >
    <div class="mx-auto flex h-14 max-w-[1200px] items-center gap-4 px-6 md:px-8">
      <div class="min-w-0 flex-1">
        <p class="truncate text-base font-semibold tracking-tight text-foreground">
          {{ title ?? 'Dashboard' }}
        </p>
      </div>

      <div class="hidden items-center gap-3 md:flex">
        <div
          class="flex items-center gap-2 rounded-md border border-border/80 bg-background px-3 py-1.5 text-muted-foreground shadow-sm focus-within:border-ring focus-within:ring-1 focus-within:ring-ring"
        >
          <Search class="h-4 w-4" />
          <input
            class="w-[260px] bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            placeholder="Search projects, files…"
            aria-label="Search"
          />
        </div>
      </div>

      <button
        type="button"
        class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border/80 bg-background text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground"
        @click="toggle"
        :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
      >
        <Moon v-if="isDark" class="h-4 w-4" />
        <Sun v-else class="h-4 w-4" />
      </button>
    </div>
  </header>
</template>

