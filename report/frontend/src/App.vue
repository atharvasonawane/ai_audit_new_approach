<template>
  <div class="h-screen w-screen flex relative font-sans antialiased min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-50 transition-colors duration-300 overflow-hidden">
    <Sidebar 
      v-show="!isCollapsed"
      :style="{ 
        width: sidebarWidth + 'px', 
        minWidth: sidebarWidth + 'px',
        maxWidth: sidebarWidth + 'px'
      }"
      :class="[
        isDragging ? '' : 'transition-all duration-300 ease-in-out'
      ]"
    />
    
    <!-- Drag Resizer Handle -->
    <div 
      v-show="!isCollapsed"
      class="w-[3px] hover:w-[5px] active:w-[5px] cursor-col-resize bg-gray-200 dark:bg-gray-800 hover:bg-indigo-500 active:bg-indigo-600 dark:hover:bg-indigo-500 dark:active:bg-indigo-600 transition-all duration-200 shrink-0 z-20"
      @mousedown="startDrag"
      @dblclick="resetSidebarWidth"
      title="Drag to resize, double-click to reset"
    ></div>

    <!-- Floating Expand Button (Shown only when collapsed) -->
    <button 
      v-show="isCollapsed" 
      @click="toggleSidebar" 
      class="absolute left-0 top-[10px] z-50 bg-white/95 dark:bg-gray-900/95 border border-gray-200 dark:border-gray-800 border-l-0 rounded-r-md w-8 h-9 flex items-center justify-center shadow-sm text-gray-600 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-gray-50 dark:hover:bg-gray-800 backdrop-blur-md transition-colors cursor-pointer" 
      title="Expand Sidebar"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 18l6-6-6-6"/>
      </svg>
    </button>

    <div class="app-main flex flex-col flex-1 min-w-0">
      <Navigation />
      <main class="app-content flex-1 overflow-y-auto pb-12 relative">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
    <CommandPalette />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import Navigation from './components/Navigation.vue'
import CommandPalette from './components/CommandPalette.vue'
import { useTheme } from './composables/useTheme'
import { useSidebar } from './composables/useSidebar'

// Initialize theme on app load
useTheme()

const { isCollapsed, sidebarWidth, toggleSidebar, setSidebarWidth, resetSidebarWidth } = useSidebar()
const isDragging = ref(false)

const startDrag = (e) => {
  isDragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

const onDrag = (e) => {
  if (isDragging.value) {
    setSidebarWidth(e.clientX)
  }
}

const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}
</script>



