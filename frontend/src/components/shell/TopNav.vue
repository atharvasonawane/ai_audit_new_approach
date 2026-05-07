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
        'sticky top-0 z-20 border-b border-border/70 bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/50',
        $props.class,
      )
    "
  >
    <div class="mx-auto flex h-12 max-w-[1200px] items-center gap-3 px-5 md:px-8">
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium tracking-tight text-foreground">
          {{ title ?? 'Dashboard' }}
        </p>
      </div>

      <div class="hidden items-center gap-2 md:flex">
        <div
          class="flex items-center gap-2 rounded-lg border border-border/70 bg-card px-3 py-1.5 text-muted-foreground"
        >
          <Search class="h-4 w-4" />
          <input
            class="w-[240px] bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
            placeholder="Search files, flags, APIs…"
            aria-label="Search"
          />
        </div>
      </div>

      <button
        type="button"
        class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-border/70 bg-card text-muted-foreground hover:text-foreground"
        @click="toggle"
        :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
      >
        <Moon v-if="isDark" class="h-4 w-4" />
        <Sun v-else class="h-4 w-4" />
      </button>
    </div>
  </header>
</template>

