<template>
  <div class="flex flex-col h-full bg-white dark:bg-gray-950 overflow-hidden">
    <!-- Controls -->
    <div class="flex items-center gap-2.5 px-4 py-3 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shrink-0 flex-wrap">
      <input v-model="searchQuery" type="text" placeholder="Search files..." class="py-1.5 px-3 bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 rounded-md text-[13px] min-w-[220px] flex-1 outline-none transition-all duration-200 focus:border-gray-400 focus:ring-2 focus:ring-gray-300 dark:focus:border-gray-600 dark:focus:ring-gray-600 caret-gray-900 dark:caret-white" />
      <select v-model="categoryFilter" class="py-1.5 px-2.5 bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-md text-[12px] cursor-pointer outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
        <option value="">All Categories</option>
        <option value="entry_point">Entry Point</option>
        <option value="shared_utility">Shared Utility</option>
        <option value="hub">Hub</option>
        <option value="orphan">Orphan</option>
        <option value="leaf">Leaf</option>
        <option value="standard">Standard</option>
      </select>
      <select v-model="cycleFilter" class="py-1.5 px-2.5 bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-md text-[12px] cursor-pointer outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
        <option value="">All Files</option>
        <option value="cycle">In Cycle Only</option>
        <option value="no_cycle">No Cycle</option>
      </select>
      <span class="ml-auto text-[11px] font-mono text-gray-500 dark:text-gray-400 whitespace-nowrap">{{ filteredSortedNodes.length }} / {{ allNodes.length }} files</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center justify-center gap-3 flex-1 text-[13px] text-gray-500 dark:text-gray-400">
      <div class="w-7 h-7 border-2 border-gray-200 dark:border-gray-800 border-t-indigo-500 dark:border-t-indigo-400 rounded-full animate-spin"></div>
      <span>Loading dependency data…</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 flex-1 text-[13px] text-red-500 dark:text-red-400">
      <div class="w-9 h-9 rounded-full bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 flex items-center justify-center font-bold text-base">!</div>
      <span>{{ error }}</span>
    </div>

    <!-- Table -->
    <div v-else class="flex-1 overflow-auto relative">
      <table class="w-full border-collapse text-[13px]">
        <thead class="sticky top-0 z-10 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
          <tr>
            <th class="w-[45%] py-2.5 px-3.5 text-left text-[11px] font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-[0.06em] whitespace-nowrap cursor-pointer select-none transition-colors duration-150 hover:text-indigo-600 dark:hover:text-indigo-400" @click="toggleSort('id')">
              File <span class="text-[10px] ml-1 opacity-60">{{ getSortIcon('id') }}</span>
            </th>
            <th class="w-[13%] py-2.5 px-3.5 text-left text-[11px] font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-[0.06em] whitespace-nowrap cursor-pointer select-none transition-colors duration-150 hover:text-indigo-600 dark:hover:text-indigo-400" @click="toggleSort('impact_score')">
              Impact Score <span class="text-[10px] ml-1 opacity-60">{{ getSortIcon('impact_score') }}</span>
            </th>
            <th class="w-[10%] py-2.5 px-3.5 text-center text-[11px] font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-[0.06em] whitespace-nowrap cursor-pointer select-none transition-colors duration-150 hover:text-indigo-600 dark:hover:text-indigo-400" @click="toggleSort('in_degree')">
              In-Degree <span class="text-[10px] ml-1 opacity-60">{{ getSortIcon('in_degree') }}</span>
            </th>
            <th class="w-[10%] py-2.5 px-3.5 text-center text-[11px] font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-[0.06em] whitespace-nowrap cursor-pointer select-none transition-colors duration-150 hover:text-indigo-600 dark:hover:text-indigo-400" @click="toggleSort('out_degree')">
              Out-Degree <span class="text-[10px] ml-1 opacity-60">{{ getSortIcon('out_degree') }}</span>
            </th>
            <th class="w-[10%] py-2.5 px-3.5 text-center text-[11px] font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-[0.06em] whitespace-nowrap cursor-pointer select-none transition-colors duration-150 hover:text-indigo-600 dark:hover:text-indigo-400" @click="toggleSort('depth')">
              Depth <span class="text-[10px] ml-1 opacity-60">{{ getSortIcon('depth') }}</span>
            </th>
            <th class="w-[22%] py-2.5 px-3.5 text-left text-[11px] font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-[0.06em] whitespace-nowrap">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="node in filteredSortedNodes"
            :key="node.id"
            class="cursor-pointer border-b border-gray-100 dark:border-gray-800/50 transition-colors duration-150 group hover:bg-blue-50/50 dark:hover:bg-blue-900/10"
            @click="navigateToFile(node.id)"
            :title="node.id"
          >
            <td class="py-2.5 px-3.5 min-w-0">
              <span class="block font-mono text-[13px] font-bold text-gray-900 dark:text-gray-100 whitespace-nowrap transition-colors duration-150 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 group-hover:underline">{{ getBasename(node.id) }}</span>
              <span class="block font-mono text-[11px] text-gray-500 dark:text-gray-500 whitespace-nowrap overflow-hidden text-ellipsis max-w-[380px]">{{ getDirname(node.id) }}</span>
            </td>
            <td class="py-2.5 px-3.5">
              <span class="inline-block font-mono text-[13px] font-bold px-2 py-0.5 rounded-md"
                    :class="{
                      'text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-500/15': getScoreClass(node.impact_score) === 'score-critical',
                      'text-orange-700 bg-orange-100 dark:text-orange-400 dark:bg-orange-500/15': getScoreClass(node.impact_score) === 'score-high',
                      'text-amber-700 bg-amber-100 dark:text-amber-400 dark:bg-amber-500/15': getScoreClass(node.impact_score) === 'score-med',
                      'text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-500/15': getScoreClass(node.impact_score) === 'score-low'
                    }">{{ node.impact_score }}</span>
            </td>
            <td class="py-2.5 px-3.5 text-center font-mono text-[13px] text-gray-600 dark:text-gray-400">{{ node.in_degree }}</td>
            <td class="py-2.5 px-3.5 text-center font-mono text-[13px] text-gray-600 dark:text-gray-400">{{ node.out_degree }}</td>
            <td class="py-2.5 px-3.5 text-center font-mono text-[13px] text-gray-600 dark:text-gray-400">{{ node.depth === -1 ? '—' : node.depth }}</td>
            <td class="py-2.5 px-3.5 flex flex-wrap gap-1.5 items-center">
              <span v-if="node.is_in_cycle" class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold tracking-[0.04em] uppercase bg-red-100 text-red-700 border border-red-200 dark:bg-red-500/15 dark:text-red-400 dark:border-red-500/30">⚠ Cycle</span>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold tracking-[0.04em] uppercase"
                    :class="{
                      'bg-purple-100 text-purple-700 border border-purple-200 dark:bg-purple-500/15 dark:text-purple-400 dark:border-purple-500/30': getCategoryBadge(node.category) === 'badge-entry',
                      'bg-green-100 text-green-700 border border-green-200 dark:bg-green-500/15 dark:text-green-400 dark:border-green-500/30': getCategoryBadge(node.category) === 'badge-shared',
                      'bg-orange-100 text-orange-700 border border-orange-200 dark:bg-orange-500/15 dark:text-orange-400 dark:border-orange-500/30': getCategoryBadge(node.category) === 'badge-hub',
                      'bg-amber-100 text-amber-700 border border-amber-200 dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/30': getCategoryBadge(node.category) === 'badge-orphan',
                      'bg-blue-100 text-blue-700 border border-blue-200 dark:bg-blue-500/15 dark:text-blue-400 dark:border-blue-500/30': getCategoryBadge(node.category) === 'badge-leaf',
                      'bg-gray-100 text-gray-600 border border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700': getCategoryBadge(node.category) === 'badge-standard'
                    }">{{ formatCategory(node.category) }}</span>
            </td>
          </tr>
          <tr v-if="filteredSortedNodes.length === 0">
            <td colspan="6" class="p-12 text-center text-[13px] text-gray-500 dark:text-gray-400">No files match the current filters.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { filesAPI } from '../api.js'

const router = useRouter()
const loading = ref(false)
const error = ref(null)
const allNodes = ref([])
const searchQuery = ref('')
const categoryFilter = ref('')
const cycleFilter = ref('')
const sortKey = ref('impact_score')
const sortDir = ref('desc')

const getBasename = (p) => (p || '').split('/').pop()
const getDirname  = (p) => { const parts = (p || '').split('/'); return parts.slice(0, -1).join('/') }

const toggleSort = (key) => {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'desc'
  }
}

const getSortIcon = (key) => {
  if (sortKey.value !== key) return '↕'
  return sortDir.value === 'asc' ? '↑' : '↓'
}

const filteredSortedNodes = computed(() => {
  let nodes = [...allNodes.value]

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    nodes = nodes.filter(n => n.id.toLowerCase().includes(q))
  }
  if (categoryFilter.value) {
    nodes = nodes.filter(n => n.category === categoryFilter.value)
  }
  if (cycleFilter.value === 'cycle') {
    nodes = nodes.filter(n => n.is_in_cycle)
  } else if (cycleFilter.value === 'no_cycle') {
    nodes = nodes.filter(n => !n.is_in_cycle)
  }

  nodes.sort((a, b) => {
    let av = a[sortKey.value]
    let bv = b[sortKey.value]
    if (sortKey.value === 'depth') {
      if (av === -1) av = 9999
      if (bv === -1) bv = 9999
    }
    if (typeof av === 'string') { av = av.toLowerCase(); bv = bv.toLowerCase() }
    if (av < bv) return sortDir.value === 'asc' ? -1 : 1
    if (av > bv) return sortDir.value === 'asc' ? 1 : -1
    return 0
  })

  return nodes
})

const getScoreClass = (score) => {
  if (score >= 50) return 'score-critical'
  if (score >= 20) return 'score-high'
  if (score >= 5)  return 'score-med'
  return 'score-low'
}

const getCategoryBadge = (cat) => ({
  entry_point:    'badge-entry',
  shared_utility: 'badge-shared',
  hub:            'badge-hub',
  orphan:         'badge-orphan',
  leaf:           'badge-leaf',
  standard:       'badge-standard',
}[cat] || 'badge-standard')

const formatCategory = (cat) => ({
  entry_point:    'Entry',
  shared_utility: 'Shared',
  hub:            'Hub',
  orphan:         'Orphan',
  leaf:           'Leaf',
  standard:       'Std',
}[cat] || cat)

const navigateToFile = (filePath) => {
  router.push({ path: '/audit', query: { file: filePath } })
}

onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    const res = await filesAPI.getDependencyGraph()
    allNodes.value = res.data?.nodes || []
  } catch (err) {
    error.value = err.response?.data?.error || err.message || 'Failed to load data'
  } finally {
    loading.value = false
  }
})
</script>
