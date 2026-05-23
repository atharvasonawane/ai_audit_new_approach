<template>
  <aside class="w-full h-screen bg-white dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800 flex flex-col relative overflow-y-auto">
    <!-- Logo Section -->
    <div class="px-4 py-5 border-b border-gray-200 dark:border-gray-800 shrink-0">
      <div class="flex items-center justify-between gap-3">
        <div class="flex flex-col gap-0.5 min-w-0">
          <div class="text-sm font-bold text-gray-900 dark:text-white tracking-tight font-sans">Audit Librarian</div>
          <div class="text-[11px] font-medium text-gray-500 dark:text-gray-400 tracking-wide font-sans">Code Intelligence</div>
        </div>
        
        <!-- Sleek Collapse Button -->
        <button 
          @click="toggleSidebar"
          class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-md cursor-pointer transition-colors shrink-0"
          title="Collapse Sidebar"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 px-2 py-5 flex flex-col gap-6 overflow-y-auto min-h-0">
      <div class="flex flex-col gap-1.5">
        <div class="text-[10px] font-bold uppercase px-3 pb-1.5 text-gray-500 dark:text-gray-400 tracking-widest">Main</div>
        
        <router-link :to="getRoute('/')" class="group flex items-center gap-3 px-3 py-2.5 rounded-lg no-underline text-sm transition-all duration-200 relative cursor-pointer border-l-2" 
                     :class="isActive('/') ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-indigo-500 font-semibold' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white hover:border-indigo-500/30 border-transparent font-medium'">
          <svg class="w-[18px] h-[18px] shrink-0 transition-colors duration-200" :class="isActive('/') ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-300'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
          <span class="flex-1 overflow-hidden overflow-ellipsis whitespace-nowrap">Home</span>
        </router-link>

        <router-link :to="getRoute('/dashboard')" class="group flex items-center gap-3 px-3 py-2.5 rounded-lg no-underline text-sm transition-all duration-200 relative cursor-pointer border-l-2" 
                     :class="isActive('/dashboard') ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-indigo-500 font-semibold' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white hover:border-indigo-500/30 border-transparent font-medium'">
          <svg class="w-[18px] h-[18px] shrink-0 transition-colors duration-200" :class="isActive('/dashboard') ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-300'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="7" height="7"/>
            <rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/>
          </svg>
          <span class="flex-1 overflow-hidden overflow-ellipsis whitespace-nowrap">Dashboard</span>
        </router-link>

        <router-link :to="getRoute('/audit')" class="group flex items-center gap-3 px-3 py-2.5 rounded-lg no-underline text-sm transition-all duration-200 relative cursor-pointer border-l-2" 
                     :class="isActive('/audit') ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-indigo-500 font-semibold' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white hover:border-indigo-500/30 border-transparent font-medium'">
          <svg class="w-[18px] h-[18px] shrink-0 transition-colors duration-200" :class="isActive('/audit') ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-300'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
            <polyline points="13 2 13 9 20 9"/>
          </svg>
          <span class="flex-1 overflow-hidden overflow-ellipsis whitespace-nowrap">Audit Explorer</span>
        </router-link>

        <router-link :to="getRoute('/graph')" class="group flex items-center gap-3 px-3 py-2.5 rounded-lg no-underline text-sm transition-all duration-200 relative cursor-pointer border-l-2" 
                     :class="isActive('/graph') ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-indigo-500 font-semibold' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white hover:border-indigo-500/30 border-transparent font-medium'">
          <svg class="w-[18px] h-[18px] shrink-0 transition-colors duration-200" :class="isActive('/graph') ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-300'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="18" cy="5" r="3"/>
            <circle cx="6" cy="12" r="3"/>
            <circle cx="18" cy="19" r="3"/>
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
          </svg>
          <span class="flex-1 overflow-hidden overflow-ellipsis whitespace-nowrap">Dependency Graph</span>
        </router-link>
      </div>
    </nav>

    <!-- Footer -->
    <div class="px-4 py-3 shrink-0 border-t border-gray-200 dark:border-gray-800">
      <div class="flex items-center gap-2 text-[11px] font-mono text-gray-500 dark:text-gray-400">
        <svg width="6" height="6" viewBox="0 0 6 6" fill="none">
          <circle cx="3" cy="3" r="3" fill="#10b981" opacity="0.9"/>
        </svg>
        <span class="font-medium">v1.0.0</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useSidebar } from '../composables/useSidebar'

const route = useRoute()
const isActive = (path) => route.path === path

const getRoute = (path) => {
  return { path, query: route.query.run_id ? { run_id: route.query.run_id } : {} }
}

const { toggleSidebar } = useSidebar()
</script>
