<template>
  <nav class="flex items-center justify-between px-6 h-[56px] shrink-0 gap-6 bg-white/80 dark:bg-gray-950/80 backdrop-blur-[10px] border-b border-gray-200 dark:border-gray-800">
    <div class="flex items-center gap-4 flex-1">
      <div class="flex items-center gap-2 text-[13px]">
        <span class="font-medium transition-colors duration-200 text-gray-500 dark:text-gray-400">Code Audit</span>
        <span class="text-[12px] text-gray-400 dark:text-gray-500">/</span>
        <span class="font-medium transition-colors duration-200 text-gray-900 dark:text-white">{{ pageTitle }}</span>
      </div>
    </div>

    <div class="flex items-center gap-4">
      <div class="relative flex items-center">
        <svg class="absolute left-3 w-4 h-4 text-gray-500 dark:text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input 
          v-model="searchQuery" 
          @input="onSearch"
          type="text" 
          placeholder="Search codebase..." 
          class="pl-9 pr-4 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-gray-300 dark:focus:ring-gray-600 caret-gray-900 dark:caret-white transition-all duration-300 w-48 focus:w-64 placeholder-gray-500 dark:placeholder-gray-400"
        />
      </div>

      <button class="flex items-center justify-center w-9 h-9 rounded-lg bg-transparent border border-transparent text-gray-500 dark:text-gray-400 cursor-pointer transition-all duration-200 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white" @click="toggleTheme" title="Toggle Theme">
        <svg v-if="isDark" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
          <line x1="18.36" y1="19.78" x2="19.78" y2="18.36"/>
          <line x1="1" y1="12" x2="3" y2="12"/>
          <line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
          <line x1="18.36" y1="4.22" x2="19.78" y2="5.64"/>
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      </button>

      <button class="flex items-center justify-center w-9 h-9 rounded-lg bg-transparent border border-transparent text-gray-500 dark:text-gray-400 cursor-pointer transition-all duration-200 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white" @click="handleSettings" title="Settings">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="3"/>
          <path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M4.22 19.78l4.24-4.24m4.24-4.24l4.24-4.24"/>
        </svg>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme'
import { useSearch } from '../composables/useSearch'

const route = useRoute()
const router = useRouter()
const { isDark, toggleTheme } = useTheme()
const { searchQuery } = useSearch()

const pageTitle = computed(() => {
  const titles = {
    '/': 'Home',
    '/dashboard': 'Dashboard',
    '/audit': 'Audit Explorer',
    '/analyzing': 'Analyzing'
  }
  return titles[route.path] || 'Code Audit Librarian'
})

const onSearch = () => {
  if (route.path !== '/audit') {
    router.push('/audit')
  }
}

const handleSettings = () => { console.log('Settings triggered') }
</script>
