<template>
  <div class="dep-table-wrap">
    <!-- Controls -->
    <div class="table-controls">
      <input v-model="searchQuery" type="text" placeholder="Search files..." class="ctrl-input" />
      <select v-model="categoryFilter" class="ctrl-select">
        <option value="">All Categories</option>
        <option value="entry_point">Entry Point</option>
        <option value="shared_utility">Shared Utility</option>
        <option value="hub">Hub</option>
        <option value="orphan">Orphan</option>
        <option value="leaf">Leaf</option>
        <option value="standard">Standard</option>
      </select>
      <select v-model="cycleFilter" class="ctrl-select">
        <option value="">All Files</option>
        <option value="cycle">In Cycle Only</option>
        <option value="no_cycle">No Cycle</option>
      </select>
      <span class="table-count">{{ filteredSortedNodes.length }} / {{ allNodes.length }} files</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="state-center">
      <div class="spinner"></div>
      <span>Loading dependency data…</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-center err">
      <div class="err-ico">!</div>
      <span>{{ error }}</span>
    </div>

    <!-- Table -->
    <div v-else class="table-scroll">
      <table class="dep-table">
        <thead>
          <tr>
            <th class="col-file sortable" @click="toggleSort('id')">
              File <span class="sort-arr">{{ getSortIcon('id') }}</span>
            </th>
            <th class="col-score sortable" @click="toggleSort('impact_score')">
              Impact Score <span class="sort-arr">{{ getSortIcon('impact_score') }}</span>
            </th>
            <th class="col-num sortable" @click="toggleSort('in_degree')">
              In-Degree <span class="sort-arr">{{ getSortIcon('in_degree') }}</span>
            </th>
            <th class="col-num sortable" @click="toggleSort('out_degree')">
              Out-Degree <span class="sort-arr">{{ getSortIcon('out_degree') }}</span>
            </th>
            <th class="col-num sortable" @click="toggleSort('depth')">
              Depth <span class="sort-arr">{{ getSortIcon('depth') }}</span>
            </th>
            <th class="col-status">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="node in filteredSortedNodes"
            :key="node.id"
            class="table-row"
            @click="navigateToFile(node.id)"
            :title="node.id"
          >
            <td class="cell-file">
              <span class="file-name">{{ getBasename(node.id) }}</span>
              <span class="file-dir">{{ getDirname(node.id) }}</span>
            </td>
            <td class="cell-score">
              <span class="score-pill" :class="getScoreClass(node.impact_score)">{{ node.impact_score }}</span>
            </td>
            <td class="cell-num">{{ node.in_degree }}</td>
            <td class="cell-num">{{ node.out_degree }}</td>
            <td class="cell-num">{{ node.depth === -1 ? '—' : node.depth }}</td>
            <td class="cell-status">
              <span v-if="node.is_in_cycle" class="s-badge badge-cycle">⚠ Cycle</span>
              <span class="s-badge" :class="getCategoryBadge(node.category)">{{ formatCategory(node.category) }}</span>
            </td>
          </tr>
          <tr v-if="filteredSortedNodes.length === 0">
            <td colspan="6" class="empty-cell">No files match the current filters.</td>
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

<style scoped>
.dep-table-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-primary);
  overflow: hidden;
}

/* Controls */
.table-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.ctrl-input {
  padding: 7px 12px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-base);
  color: var(--color-text-primary);
  font-size: 13px;
  min-width: 220px;
  flex: 1;
}
.ctrl-input:focus { outline: none; border-color: var(--color-accent-primary); }

.ctrl-select {
  padding: 7px 10px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-base);
  color: var(--color-text-secondary);
  font-size: 12px;
  cursor: pointer;
}

.table-count {
  margin-left: auto;
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

/* State */
.state-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex: 1;
  color: var(--color-text-secondary);
  font-size: 13px;
}
.state-center.err { color: var(--color-status-error); }

.spinner {
  width: 28px; height: 28px;
  border: 2px solid var(--color-border-emphasis);
  border-top-color: var(--color-accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.err-ico {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: rgba(248,81,73,0.1);
  border: 1px solid rgba(248,81,73,0.3);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 16px;
  color: var(--color-status-error);
}

/* Table */
.table-scroll {
  flex: 1;
  overflow: auto;
}

.dep-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.dep-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--color-bg-secondary);
}

.dep-table th {
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.dep-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: color 120ms;
}
.dep-table th.sortable:hover { color: var(--color-text-primary); }

.sort-arr { font-size: 10px; margin-left: 4px; opacity: 0.6; }

.col-file   { width: 45%; }
.col-score  { width: 13%; }
.col-num    { width: 10%; text-align: center; }
.col-status { width: 22%; }

.table-row {
  cursor: pointer;
  border-bottom: 1px solid var(--color-border-subtle, rgba(48,54,61,0.5));
  transition: background 120ms;
}
.table-row:hover { background: var(--color-bg-hover, var(--color-bg-secondary)); }
.table-row:hover .file-name { color: var(--color-accent-hover, #58A6FF); text-decoration: underline; }

.cell-file { padding: 10px 14px; }
.file-name {
  display: block;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  transition: color 120ms;
}
.file-dir {
  display: block;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 380px;
}

.cell-score  { padding: 10px 14px; }
.cell-num    { padding: 10px 14px; text-align: center; font-family: var(--font-mono); color: var(--color-text-secondary); }
.cell-status { padding: 10px 14px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }

.score-pill {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--rounded-base);
}
.score-critical { color: #F85149; background: rgba(248,81,73,0.12); }
.score-high     { color: #F0883E; background: rgba(240,136,62,0.12); }
.score-med      { color: #D29922; background: rgba(210,153,34,0.12); }
.score-low      { color: #3FB950; background: rgba(63,185,80,0.10); }

/* Status badges */
.s-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: var(--rounded-full);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.badge-cycle   { background: rgba(248,81,73,0.15);  color: #F85149; border: 1px solid rgba(248,81,73,0.3); }
.badge-entry   { background: rgba(137,87,229,0.15); color: #8957E5; border: 1px solid rgba(137,87,229,0.3); }
.badge-shared  { background: rgba(63,185,80,0.12);  color: #3FB950; border: 1px solid rgba(63,185,80,0.25); }
.badge-hub     { background: rgba(240,136,62,0.12); color: #F0883E; border: 1px solid rgba(240,136,62,0.3); }
.badge-orphan  { background: rgba(210,153,34,0.12); color: #D29922; border: 1px solid rgba(210,153,34,0.3); }
.badge-leaf    { background: rgba(56,139,253,0.12); color: #58A6FF; border: 1px solid rgba(56,139,253,0.25); }
.badge-standard{ background: var(--color-bg-tertiary); color: var(--color-text-tertiary); border: 1px solid var(--color-border); }

.empty-cell {
  padding: 48px;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 13px;
}
</style>
