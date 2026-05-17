<template>
  <teleport to="body">
    <transition name="palette-fade">
      <div v-if="isOpen" class="fixed inset-0 z-[9999] bg-black/55 backdrop-blur-sm flex items-start justify-center pt-[15vh]" @click.self="close" @keydown.esc="close">
        <div class="palette-modal bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-2xl rounded-[14px] w-[560px] max-w-[calc(100vw-40px)] overflow-hidden" role="dialog" aria-label="Command Palette">
          <!-- Search Input -->
          <div class="flex items-center gap-3 py-4 px-5 border-b border-gray-200 dark:border-gray-800">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-gray-400 dark:text-gray-500 shrink-0">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              placeholder="Search pages, files..."
              class="flex-1 text-[16px] font-normal bg-transparent text-gray-900 dark:text-gray-50 border-none outline-none placeholder-gray-400 dark:placeholder-gray-500 focus:ring-0 caret-gray-900 dark:caret-white"
              @keydown.esc="close"
              @keydown.arrow-down.prevent="moveDown"
              @keydown.arrow-up.prevent="moveUp"
              @keydown.enter="selectCurrent"
            />
            <kbd class="text-[11px] font-semibold py-0.5 px-1.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700 shrink-0">Esc</kbd>
          </div>

          <!-- Results -->
          <div class="max-h-[320px] overflow-y-auto p-2">
            <div v-if="filteredItems.length === 0" class="p-8 text-center text-[13px] text-gray-500 dark:text-gray-400">
              <span>No results for "<em>{{ query }}</em>"</span>
            </div>
            <div
              v-for="(item, i) in filteredItems"
              :key="item.id"
              class="flex items-center gap-3 py-2.5 px-3 rounded-lg cursor-pointer transition-all duration-150"
              :class="i === activeIndex ? 'bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
              @click="select(item)"
              @mouseenter="activeIndex = i"
            >
              <span class="flex items-center shrink-0" :class="i === activeIndex ? 'text-indigo-500' : 'text-gray-400 dark:text-gray-500'" v-html="item.icon"></span>
              <span class="flex-1 text-[14px] font-medium">{{ item.label }}</span>
              <span class="text-[11px] font-medium" :class="i === activeIndex ? 'text-indigo-400/80' : 'text-gray-400 dark:text-gray-500'">{{ item.category }}</span>
            </div>
          </div>

          <div class="flex items-center gap-5 py-2.5 px-5 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950/50 text-[11px] text-gray-400 dark:text-gray-500">
            <span><kbd class="text-[10px] py-[1px] px-[5px] rounded-[3px] bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 mr-1">↑↓</kbd> Navigate</span>
            <span><kbd class="text-[10px] py-[1px] px-[5px] rounded-[3px] bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 mr-1">↵</kbd> Select</span>
            <span><kbd class="text-[10px] py-[1px] px-[5px] rounded-[3px] bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 mr-1">Esc</kbd> Close</span>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { filesAPI } from '../api.js'

const router = useRouter()
const isOpen = ref(false)
const query = ref('')
const activeIndex = ref(0)
const inputRef = ref(null)
const filesList = ref([])

const staticItems = [
  { id: 'home', label: 'Home', category: 'Navigation', route: '/', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>' },
  { id: 'dashboard', label: 'Dashboard', category: 'Navigation', route: '/dashboard', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>' },
  { id: 'audit', label: 'Audit Explorer', category: 'Navigation', route: '/audit', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>' },
  { id: 'graph', label: 'Dependency Graph', category: 'Navigation', route: '/graph', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>' },
]

const fetchFiles = async () => {
  try {
    const res = await filesAPI.getFiles()
    if (res.data) {
      filesList.value = res.data.map(f => ({
        id: f.file_path,
        label: f.file_path.split('/').pop(),
        category: 'File',
        route: `/audit?file=${encodeURIComponent(f.file_path)}`,
        icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>'
      }))
    }
  } catch (err) {
    console.error('Failed to load files for command palette', err)
  }
}

const allItems = computed(() => [...staticItems, ...filesList.value])

const filteredItems = computed(() => {
  if (!query.value) return staticItems
  const q = query.value.toLowerCase()
  return allItems.value.filter(i => i.label.toLowerCase().includes(q) || i.category.toLowerCase().includes(q) || (i.id && i.id.toLowerCase().includes(q))).slice(0, 15)
})

watch(filteredItems, () => { activeIndex.value = 0 })

const open = () => {
  isOpen.value = true
  query.value = ''
  activeIndex.value = 0
  nextTick(() => inputRef.value?.focus())
}

const close = () => {
  isOpen.value = false
  query.value = ''
}

const select = (item) => {
  router.push(item.route)
  close()
}

const selectCurrent = () => {
  if (filteredItems.value[activeIndex.value]) {
    select(filteredItems.value[activeIndex.value])
  }
}

const moveDown = () => {
  activeIndex.value = Math.min(activeIndex.value + 1, filteredItems.value.length - 1)
}

const moveUp = () => {
  activeIndex.value = Math.max(activeIndex.value - 1, 0)
}

const onKeydown = (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    isOpen.value ? close() : open()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  fetchFiles()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>


