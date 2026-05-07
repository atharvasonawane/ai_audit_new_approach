<script setup lang="ts">
import { computed, ref } from 'vue'

import { cn } from '../../lib/utils'
import ContentContainer from './ContentContainer.vue'
import SidebarNav from './SidebarNav.vue'
import TopNav from './TopNav.vue'

const props = defineProps<{
  title?: string
  class?: string
}>()

const isMobileSidebarOpen = ref(false)
const openSidebar = () => (isMobileSidebarOpen.value = true)
const closeSidebar = () => (isMobileSidebarOpen.value = false)

const overlayClass = computed(() =>
  cn(
    'fixed inset-0 z-40 bg-black/40 backdrop-blur-[1px] transition-opacity md:hidden',
    isMobileSidebarOpen.value ? 'opacity-100' : 'pointer-events-none opacity-0',
  ),
)
</script>

<template>
  <div :class="cn('min-h-screen bg-background text-foreground', props.class)">
    <div class="hidden md:fixed md:inset-y-0 md:left-0 md:z-30 md:flex">
      <SidebarNav />
    </div>

    <div :class="overlayClass" @click="closeSidebar" />

    <div
      class="fixed inset-y-0 left-0 z-50 w-[280px] translate-x-[-100%] transition-transform md:hidden"
      :class="isMobileSidebarOpen ? 'translate-x-0' : ''"
    >
      <SidebarNav class="w-[280px]" />
    </div>

    <div class="md:pl-[260px]">
      <TopNav :title="props.title">
        <!-- reserved -->
      </TopNav>

      <ContentContainer>
        <div class="mb-4 flex items-center gap-3 md:hidden">
          <button
            type="button"
            class="inline-flex h-9 items-center rounded-lg border border-border/70 bg-card px-3 text-sm text-muted-foreground hover:text-foreground"
            @click="openSidebar"
          >
            Menu
          </button>
          <p class="text-sm text-muted-foreground">Navigate</p>
        </div>

        <slot />
      </ContentContainer>
    </div>
  </div>
</template>

