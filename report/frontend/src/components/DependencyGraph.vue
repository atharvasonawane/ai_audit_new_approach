<template>
  <div class="flex flex-col h-full bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
    <!-- View Mode Toggle -->
    <div class="flex gap-0.5 py-2 px-3.5 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shrink-0">
      <button class="inline-flex items-center gap-1.5 py-1.5 px-3.5 rounded-md border text-[12px] font-semibold cursor-pointer transition-all duration-150"
              :class="viewMode === 'graph' ? 'bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border-indigo-500/30' : 'border-transparent bg-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-50 hover:bg-gray-100 dark:hover:bg-gray-800'" 
              @click="viewMode = 'graph'">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="8" cy="8" r="2"/><circle cx="2" cy="2" r="1.5"/><circle cx="14" cy="14" r="1.5"/>
          <path d="M3.5 3.5l3 3M9.5 9.5l3 3"/>
        </svg>
        Graph
      </button>
      <button class="inline-flex items-center gap-1.5 py-1.5 px-3.5 rounded-md border text-[12px] font-semibold cursor-pointer transition-all duration-150"
              :class="viewMode === 'table' ? 'bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border-indigo-500/30' : 'border-transparent bg-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-50 hover:bg-gray-100 dark:hover:bg-gray-800'" 
              @click="viewMode = 'table'">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="1" y="1" width="14" height="14" rx="1"/>
          <path d="M1 5h14M1 9h14M1 13h14M5 1v14"/>
        </svg>
        Table
      </button>
    </div>

    <!-- Table View -->
    <DependencyTable v-if="viewMode === 'table'" class="flex-1 overflow-hidden" />

    <!-- Graph Controls (only in graph mode) -->
    <div v-show="viewMode === 'graph'" class="flex flex-wrap items-center justify-between gap-4 p-4 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
      <input type="text" v-model="searchQuery" placeholder="Search files..." class="py-2 px-3 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 min-w-[250px] outline-none focus:border-gray-400 focus:ring-2 focus:ring-gray-300 dark:focus:border-gray-600 dark:focus:ring-gray-600 caret-gray-900 dark:caret-white" @input="highlightSearch" />
      <div class="flex flex-wrap items-center gap-3">
        <label class="flex items-center gap-1 text-[12px] text-gray-600 dark:text-gray-400 cursor-pointer"><input type="checkbox" v-model="filters.component" class="accent-indigo-500" /> Component</label>
        <label class="flex items-center gap-1 text-[12px] text-gray-600 dark:text-gray-400 cursor-pointer"><input type="checkbox" v-model="filters.composable" class="accent-indigo-500" /> Composable</label>
        <label class="flex items-center gap-1 text-[12px] text-gray-600 dark:text-gray-400 cursor-pointer"><input type="checkbox" v-model="filters.store" class="accent-indigo-500" /> Store</label>
        <label class="flex items-center gap-1 text-[12px] text-gray-600 dark:text-gray-400 cursor-pointer"><input type="checkbox" v-model="filters.service" class="accent-indigo-500" /> Service</label>
        <label class="flex items-center gap-1 text-[12px] text-gray-600 dark:text-gray-400 cursor-pointer"><input type="checkbox" v-model="filters.router" class="accent-indigo-500" /> Router</label>
        <label class="flex items-center gap-1 text-[12px] text-gray-600 dark:text-gray-400 cursor-pointer"><input type="checkbox" v-model="filters.utility" class="accent-indigo-500" /> Utility</label>
        
        <button class="py-1.5 px-3 rounded-full border text-[11px] font-semibold cursor-pointer transition-all duration-150"
                :class="showOrphansOnly ? 'bg-indigo-500 text-white border-indigo-500' : 'bg-transparent border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-400'"
                @click="toggleOrphans">Show Orphans Only</button>
        <button class="py-1.5 px-3 rounded-full border text-[11px] font-semibold cursor-pointer transition-all duration-150"
                :class="showCyclesOnly ? 'bg-indigo-500 text-white border-indigo-500' : 'bg-transparent border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-400'"
                @click="toggleCycles">Show Cycles Only</button>

        <!-- Stage 11: Heatmap Mode -->
        <button
          class="flex items-center gap-1.5 py-1.5 px-3 rounded-full border text-[11px] font-semibold cursor-pointer transition-all duration-200"
          :class="heatmapActive
            ? 'bg-gradient-to-r from-green-500 via-yellow-400 to-red-500 text-white border-transparent shadow-md'
            : 'bg-transparent border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-400'"
          @click="toggleHeatmap"
          title="Color nodes by impact score — green (safe) to red (bottleneck)"
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
            <circle cx="4" cy="8" r="3" fill="#22c55e"/>
            <circle cx="8" cy="8" r="3" fill="#eab308"/>
            <circle cx="12" cy="8" r="3" fill="#ef4444"/>
          </svg>
          Heatmap
        </button>
      </div>
    </div>

    <div v-show="viewMode === 'graph'" class="flex-1 flex flex-row border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 overflow-hidden">
      
      <!-- Stage 7: Side Panel -->
      <div class="w-[240px] shrink-0 border-r border-gray-200 dark:border-gray-800 flex flex-col z-20 bg-white dark:bg-gray-950 shadow-[4px_0_12px_rgba(0,0,0,0.02)]">
        <div class="p-3 border-b border-gray-200 dark:border-gray-800 flex flex-col gap-2 shrink-0">
           <div class="text-xs font-bold text-gray-800 dark:text-gray-200 uppercase tracking-wider">Files</div>
           <select v-model="sortOption" class="text-xs border rounded p-1.5 outline-none focus:ring-2 focus:ring-indigo-500/50 bg-gray-50 dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-gray-800 dark:text-gray-200 cursor-pointer">
             <option value="impact">Sort by Impact</option>
             <option value="in_degree">Sort by In-degree</option>
             <option value="out_degree">Sort by Out-degree</option>
             <option value="alpha">Alphabetical</option>
           </select>
        </div>
        <div class="flex-1 overflow-y-auto">
          <div v-for="node in sortedNodes" :key="node.id" 
               @click="enterFocusedMode(node)"
               class="px-3 py-2 border-b border-gray-100 dark:border-gray-800/50 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 cursor-pointer flex flex-col gap-1 transition-colors"
               :class="{ 'bg-indigo-50 dark:bg-indigo-500/10': focusedNode && focusedNode.id === node.id }">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: getNodeColor(node) }"></span>
              <span class="text-xs font-semibold text-gray-900 dark:text-gray-100 truncate flex-1" :title="node.id">{{ getBasename(node.id) }}</span>
            </div>
            <div class="flex items-center gap-3 pl-4 text-[10px] text-gray-500 dark:text-gray-400 font-medium">
              <span title="Impact Score">⭐ {{ node.impact_score || 0 }}</span>
              <span title="In-degree">In: {{ node.in_degree || 0 }}</span>
              <span title="Out-degree">Out: {{ node.out_degree || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Graph Wrapper -->
      <div class="flex-1 relative w-full h-full overflow-hidden" ref="graphWrapper">
        
        <!-- Topology Stats Bar -->
        <div v-show="viewMode === 'graph' && layoutMode === 'force'" class="absolute top-4 left-1/2 -translate-x-1/2 z-30 flex items-center gap-1 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border border-gray-200 dark:border-gray-700 rounded-full shadow-sm px-3 py-1.5 text-[11px] font-semibold text-gray-700 dark:text-gray-300 transition-all">
          <span class="px-2 border-r border-gray-300 dark:border-gray-600">Total: {{ topologyStats.total }}</span>
          
          <button @click.stop="toggleTopologyFilter('entryPoints')" 
                  class="px-2 py-0.5 transition-colors rounded-full font-bold" 
                  :class="activeTopologyFilter === 'entryPoints' ? 'bg-indigo-600 text-white dark:bg-indigo-500' : 'hover:text-indigo-600 dark:hover:text-indigo-400'">
            Entry Points: {{ topologyStats.entryPoints }}
          </button>
          
          <button @click.stop="toggleTopologyFilter('hubs')" 
                  class="px-2 py-0.5 border-l border-gray-300 dark:border-gray-600 transition-colors rounded-full font-bold" 
                  :class="activeTopologyFilter === 'hubs' ? 'bg-orange-600 text-white dark:bg-orange-500 border-l-transparent' : 'hover:text-orange-600 dark:hover:text-orange-400'">
            Hubs: {{ topologyStats.hubs }}
          </button>
          
          <button @click.stop="toggleTopologyFilter('leaves')" 
                  class="px-2 py-0.5 border-l border-gray-300 dark:border-gray-600 transition-colors rounded-full font-bold" 
                  :class="activeTopologyFilter === 'leaves' ? 'bg-teal-600 text-white dark:bg-teal-500 border-l-transparent' : 'hover:text-teal-600 dark:hover:text-teal-400'">
            Leaves: {{ topologyStats.leaves }}
          </button>
          
          <button @click.stop="toggleTopologyFilter('orphans')" 
                  class="px-2 py-0.5 border-l border-gray-300 dark:border-gray-600 transition-colors rounded-full font-bold" 
                  :class="activeTopologyFilter === 'orphans' ? 'bg-yellow-500 text-white dark:bg-yellow-500 border-l-transparent' : 'hover:text-yellow-600 dark:hover:text-yellow-400'">
            Orphans: {{ topologyStats.orphans }}
          </button>
        </div>

        <svg ref="svgRef" class="w-full h-full block cursor-grab active:cursor-grabbing [&_.labels_text]:!fill-gray-900 dark:[&_.labels_text]:!fill-gray-100 [&_.labels_text]:![text-shadow:0_1px_3px_rgba(255,255,255,0.9)] dark:[&_.labels_text]:![text-shadow:0_1px_3px_rgba(0,0,0,0.9)]"></svg>

      
      <!-- Tooltip -->
      <div v-show="tooltip.visible && viewMode === 'graph'" class="fixed bg-white/95 dark:bg-gray-950/95 border border-gray-200 dark:border-gray-800 rounded-lg p-3 text-gray-900 dark:text-gray-100 pointer-events-none z-[100] shadow-[0_4px_12px_rgba(0,0,0,0.15)] min-w-[150px] backdrop-blur-sm" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
        <div class="text-[13px] font-semibold text-gray-900 dark:text-gray-100 mb-1">{{ tooltip.data.basename }}</div>
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] mb-2" :style="{color: getNodeColor(tooltip.data)}">{{ tooltip.data.category }}</div>
        <div class="flex flex-col gap-0.5 text-[12px] text-gray-600 dark:text-gray-400">
          <div>In: <strong class="text-gray-900 dark:text-gray-100">{{ tooltip.data.in_degree }}</strong></div>
          <div>Out: <strong class="text-gray-900 dark:text-gray-100">{{ tooltip.data.out_degree }}</strong></div>
          <div>Impact: <strong class="text-gray-900 dark:text-gray-100">{{ tooltip.data.impact_score }}</strong></div>
        </div>
      </div>

      <!-- Zoom Controls -->
      <div v-show="viewMode === 'graph'" class="absolute top-4 right-4 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm flex items-center p-1 gap-1 z-10">
        <span class="text-[11px] font-mono text-gray-500 dark:text-gray-400 w-10 text-center">{{ currentZoom }}%</span>
        <div class="w-px h-4 bg-gray-200 dark:bg-gray-700 mx-1"></div>
        <button @click="zoomIn" class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-700 dark:text-gray-300" title="Zoom In">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
        </button>
        <button @click="zoomOut" class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-700 dark:text-gray-300" title="Zoom Out">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/></svg>
        </button>
        <button @click="fitGraph" class="px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-700 dark:text-gray-300 text-[11px] font-semibold" title="Fit to Screen">Fit</button>
        <button @click="resetZoom" class="px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-gray-700 dark:text-gray-300 text-[11px] font-semibold" title="Reset">Reset</button>
      </div>

      <!-- Mini-map -->
      <div v-show="viewMode === 'graph' && layoutMode === 'force'" class="absolute bottom-[20px] right-[20px] w-[160px] h-[100px] bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm border border-gray-200 dark:border-gray-800 rounded-lg shadow-sm overflow-hidden z-40">
        <svg ref="minimapSvgRef" class="w-full h-full cursor-pointer bg-transparent" @click="onMinimapClick"></svg>
      </div>

      <!-- Focused Mode Header -->
      <div v-if="layoutMode === 'radial'" class="absolute top-4 left-4 z-20">
        <button @click="exitFocusedMode" class="flex items-center gap-1.5 px-3 py-1.5 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          Back to Full Graph
        </button>
      </div>

      <!-- Focused Mode Info Card -->
      <div v-if="layoutMode === 'radial' && focusedNode" class="absolute bottom-[24px] left-1/2 -translate-x-1/2 z-50 bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl border border-gray-200 dark:border-gray-700 rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] p-4 min-w-[280px]">
        <div class="text-sm font-bold text-gray-900 dark:text-gray-100 mb-1 flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full shadow-inner" :style="{ backgroundColor: getNodeColor(focusedNode) }"></span>
          {{ getBasename(focusedNode.id) }}
        </div>
        <div class="text-[11px] font-bold uppercase tracking-wider mb-4" :style="{color: getNodeColor(focusedNode)}">{{ focusedNode.category }}</div>
        
        <div class="grid grid-cols-3 gap-2 text-center text-xs mb-3">
           <div class="bg-gray-50 dark:bg-gray-800/80 rounded-lg p-2 border border-gray-100 dark:border-gray-700/50">
             <div class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Impact</div>
             <div class="font-bold text-sm text-gray-900 dark:text-gray-100">{{ focusedNode.impact_score || 0 }}</div>
           </div>
           <div class="bg-gray-50 dark:bg-gray-800/80 rounded-lg p-2 border border-gray-100 dark:border-gray-700/50">
             <div class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">In</div>
             <div class="font-bold text-sm text-gray-900 dark:text-gray-100">{{ focusedNode.in_degree || 0 }}</div>
           </div>
           <div class="bg-gray-50 dark:bg-gray-800/80 rounded-lg p-2 border border-gray-100 dark:border-gray-700/50">
             <div class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-0.5">Out</div>
             <div class="font-bold text-sm text-gray-900 dark:text-gray-100">{{ focusedNode.out_degree || 0 }}</div>
           </div>
        </div>
        
        <div v-if="focusedNode.is_in_cycle" class="text-[11px] font-bold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 px-2 py-2 rounded-lg text-center border border-red-200 dark:border-red-500/20">
          ⚠️ Circular Dependency Detected
        </div>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount, computed, shallowRef } from 'vue'
import * as d3 from 'd3'
import { filesAPI } from '../api.js'
import DependencyTable from './DependencyTable.vue'

const viewMode = ref('graph')

const svgRef = ref(null)
const graphWrapper = ref(null)
const minimapSvgRef = ref(null)

const searchQuery = ref('')
const filters = ref({
  component: true,
  composable: true,
  store: true,
  service: true,
  router: true,
  utility: true
})
const showOrphansOnly = ref(false)
const showCyclesOnly = ref(false)

const tooltip = ref({ visible: false, x: 0, y: 0, data: {} })
const currentZoom = ref(100)

const layoutMode = ref('force')
const focusedNode = ref(null)
const sortOption = ref('impact')
const reactiveNodes = shallowRef([])

const sortedNodes = computed(() => {
  let list = [...reactiveNodes.value]
  if (sortOption.value === 'impact') {
    list.sort((a, b) => (b.impact_score || 0) - (a.impact_score || 0))
  } else if (sortOption.value === 'in_degree') {
    list.sort((a, b) => (b.in_degree || 0) - (a.in_degree || 0))
  } else if (sortOption.value === 'out_degree') {
    list.sort((a, b) => (b.out_degree || 0) - (a.out_degree || 0))
  } else if (sortOption.value === 'alpha') {
    list.sort((a, b) => getBasename(a.id).localeCompare(getBasename(b.id)))
  }
  return list
})

let rawData = { nodes: [], edges: [] }
let simulation = null
let svg = null
let g = null
let linkElements = null
let nodeElements = null
let zoom = null
let labelElements = null
let pinnedNode = null
let blastRadiusNode = null
let impactBadge = null

const heatmapActive = ref(false)
const activeTopologyFilter = ref(null)

const topologyStats = computed(() => {
  const nodes = reactiveNodes.value
  let entryPoints = 0
  let hubs = 0
  let leaves = 0
  let orphans = 0

  nodes.forEach(n => {
    const isEntry = n.id.endsWith('App.vue') || n.id.endsWith('main.js') || n.id.includes('/router/')
    if (isEntry) entryPoints++
    if (n.in_degree >= 3 && n.out_degree >= 3) hubs++
    if (n.out_degree === 0) leaves++
    if (n.in_degree === 0 && !isEntry) orphans++
  })

  return {
    total: nodes.length,
    entryPoints,
    hubs,
    leaves,
    orphans
  }
})

let minimapSvg = null
let minimapNodes = null
let minimapViewport = null
let currentTransform = d3.zoomIdentity
let graphNodes = []

const getNodeColor = (d) => {
  if (d.category === 'missing') return '#6b7280'
  if (d.category === 'entry_point') return '#8b5cf6'
  if (d.category === 'orphan') return '#f59e0b'
  if (d.category === 'hub') return '#f97316'
  if (d.category === 'shared_utility') return '#10b981'
  if (d.category === 'leaf') return '#14b8a6'
  return '#3b82f6'
}

const getEdgeColor = (type) => {
  const map = {
    'component': '#6366f1',
    'composable': '#8b5cf6',
    'store': '#f59e0b',
    'service': '#ef4444',
    'router': '#3b82f6',
    'utility': '#94a3b8'
  }
  return map[type] || '#94a3b8'
}

const nodeRadius = (d) => Math.max(6, Math.min(28, 6 + (d.in_degree || 0) * 2))

const truncateLabel = (label) => label.length > 20 ? label.substring(0, 17) + '...' : label;

const toggleOrphans = () => {
  showOrphansOnly.value = !showOrphansOnly.value
  if (showOrphansOnly.value) showCyclesOnly.value = false
  updateGraph()
}

const toggleCycles = () => {
  showCyclesOnly.value = !showCyclesOnly.value
  if (showCyclesOnly.value) showOrphansOnly.value = false
  updateGraph()
}

watch(filters, () => updateGraph(), { deep: true })

const getBasename = (path) => {
  if (!path) return ''
  const parts = path.split('/')
  return parts[parts.length - 1]
}

onMounted(async () => {
  try {
    const res = await filesAPI.getDependencyGraph()
    rawData = res.data
    initGraph()
  } catch (err) {
    console.error("Failed to load graph data", err)
  }
})

onBeforeUnmount(() => {
  if (simulation) simulation.stop()
})

const ticked = () => {
  if (layoutMode.value === 'radial') return
  if (!nodeElements || !linkElements) return

  linkElements.attr("d", d => {
    const dx = d.target.x - d.source.x
    const dy = d.target.y - d.source.y
    return `M${d.source.x},${d.source.y} C${d.source.x},${(d.source.y + d.target.y)/2} ${d.target.x},${(d.source.y + d.target.y)/2} ${d.target.x},${d.target.y}`
  })
  
  nodeElements.attr("cx", d => d.x).attr("cy", d => d.y)
  if (labelElements) labelElements.attr("x", d => d.x).attr("y", d => d.y)
  
  if (svg) svg.selectAll('marker').attr('refX', 22)
  
  updateMinimap()
}

const initGraph = () => {
  const width = graphWrapper.value.clientWidth || 800
  const height = graphWrapper.value.clientHeight || 600

  svg = d3.select(svgRef.value)
  svg.selectAll('*').remove() // CRITICAL FIX for Vue HMR duplicating elements
  
  svg.attr('width', width)
    .attr('height', height)
    .on('click', () => {
      if (layoutMode.value === 'radial') exitFocusedMode()
      else {
        pinnedNode = null
        blastRadiusNode = null
        resetHighlight()
      }
    })

  minimapSvg = d3.select(minimapSvgRef.value)
  minimapSvg.selectAll('*').remove()
  minimapSvg.append('g').attr('class', 'minimap-nodes')
  minimapViewport = minimapSvg.append('rect')
    .attr('class', 'minimap-viewport')
    .attr('fill', 'rgba(99, 102, 241, 0.1)')
    .attr('stroke', '#6366f1')
    .attr('stroke-width', 1.5)

  const defs = svg.append('defs')
  defs.append('pattern')
    .attr('id', 'missing-pattern')
    .attr('width', 8).attr('height', 8)
    .attr('patternUnits', 'userSpaceOnUse')
    .append('path')
    .attr('d', 'M-2,2 l4,-4 M0,8 l8,-8 M6,10 l4,-4')
    .attr('stroke', '#6b7280').attr('stroke-width', 2)

  defs.selectAll('marker')
    .data(['component', 'composable', 'store', 'service', 'router', 'utility'])
    .enter().append('marker')
    .attr('id', d => `arrow-${d}`)
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto-start-reverse')
    .append('path')
    .attr('fill', d => getEdgeColor(d))
    .attr('d', 'M0,-5L10,0L0,5Z')

  g = svg.append('g')
  
  g.append('g').attr('class', 'links')
  g.append('g').attr('class', 'nodes')
  g.append('g').attr('class', 'labels')
  g.append('g').attr('class', 'impact-badges')

  zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      currentTransform = event.transform
      currentZoom.value = Math.round(event.transform.k * 100)
      g.attr('transform', event.transform)
      updateMinimap()
    })
  svg.call(zoom)

  simulation = d3.forceSimulation()
    .force("charge", d3.forceManyBody().strength(-120))
    .on("tick", ticked)

  updateGraph()
}

// ─── Blast Radius Reset ───────────────────────────────────────────────────
// Uses g.select() for live DOM queries — immune to stale cached references.
const resetHighlight = () => {
  if (!g) return

  // Clear state
  blastRadiusNode = null
  activeTopologyFilter.value = null
  g.select('.impact-badges').selectAll('*').remove()
  impactBadge = null

  if (heatmapActive.value) {
    applyHeatmap()
    return
  }

  // Re-query live DOM so this always works regardless of when called
  const liveNodes = g.select('.nodes').selectAll('circle')
  const liveLinks = g.select('.links').selectAll('path')
  const liveLabels = g.select('.labels').selectAll('text')

  liveNodes
    .transition().duration(300)
    .attr('opacity', function() {
      const d = d3.select(this).datum()
      return (d && d.category === 'orphan') ? 0.5 : 1
    })
    .attr('fill', function() {
      const d = d3.select(this).datum()
      if (!d) return '#3b82f6'
      return d.category === 'missing' ? 'url(#missing-pattern)' : getNodeColor(d)
    })
    .attr('stroke', function() {
      const d = d3.select(this).datum()
      if (!d) return '#000'
      if (d.is_in_cycle) return '#dc2626'
      if (d.category === 'entry_point') return '#facc15'
      const c = d3.color(getNodeColor(d))
      return c ? c.darker(1).formatHex() : '#000'
    })
    .attr('stroke-width', function() {
      const d = d3.select(this).datum()
      if (!d) return 2
      return (d.is_in_cycle || d.category === 'entry_point') ? 3 : 2
    })

  // Filter (glow) must be set without transition to avoid stacking
  liveNodes.style('filter', function() {
    const d = d3.select(this).datum()
    if (!d) return 'none'
    return (d.category === 'shared_utility' || d.in_degree >= 5)
      ? `drop-shadow(0 0 6px ${getNodeColor(d)})`
      : 'none'
  })

  liveLinks
    .transition().duration(300)
    .attr('opacity', 0.6)
    .attr('stroke-width', 1.5)
    .attr('stroke', function() {
      const d = d3.select(this).datum()
      return d ? getEdgeColor(d.relationship_type) : '#94a3b8'
    })

  liveLabels
    .transition().duration(300)
    .style('opacity', function() {
      const d = d3.select(this).datum()
      return (d && nodeRadius(d) < 8) ? 0 : 1
    })

  // Keep cached references in sync
  nodeElements  = liveNodes
  linkElements  = liveLinks
  labelElements = liveLabels
}

// ─── Stage 10 REMOVED (Path Finder cut from scope) ───────────────────────

// ─── Stage 11: Heatmap Mode ───────────────────────────────────────────────
// Scores nodes by impact_score (or total degree as fallback).
// Uses d3.scaleSequential + interpolateRdYlGn reversed:
//   low  score → green  (healthy, low risk)
//   mid  score → yellow (moderate coupling)
//   high score → red    (bottleneck / danger)
const applyHeatmap = () => {
  if (!g) return

  // Build heat score for every visible node
  const scores = graphNodes.map(d => {
    const impact = d.impact_score || 0
    const degree = (d.in_degree || 0) + (d.out_degree || 0)
    return impact > 0 ? impact : degree
  })
  const maxScore = Math.max(...scores, 1)

  // Domain: [0, max] mapped to RdYlGn reversed (0 = green, max = red)
  const heatScale = d3.scaleSequential(d3.interpolateRdYlGn)
    .domain([maxScore, 0]) // reversed so high → red

  const liveNodes  = g.select('.nodes').selectAll('circle')
  const liveLabels = g.select('.labels').selectAll('text')
  const liveLinks  = g.select('.links').selectAll('path')

  liveNodes
    .transition().duration(500)
    .attr('fill', function() {
      const d = d3.select(this).datum()
      if (!d) return '#3b82f6'
      const score = (d.impact_score || 0) > 0
        ? d.impact_score
        : (d.in_degree || 0) + (d.out_degree || 0)
      return heatScale(score)
    })
    .attr('stroke', function() {
      const d = d3.select(this).datum()
      if (!d) return '#000'
      const score = (d.impact_score || 0) > 0
        ? d.impact_score
        : (d.in_degree || 0) + (d.out_degree || 0)
      const c = d3.color(heatScale(score))
      return c ? c.darker(0.8).formatHex() : '#000'
    })
    .attr('opacity', 1)
    .attr('stroke-width', 2)

  // Glow the hottest nodes (top 20%)
  const threshold = maxScore * 0.8
  liveNodes.style('filter', function() {
    const d = d3.select(this).datum()
    if (!d) return 'none'
    const score = (d.impact_score || 0) > 0
      ? d.impact_score
      : (d.in_degree || 0) + (d.out_degree || 0)
    if (score >= threshold) {
      const heat = heatScale(score)
      return `drop-shadow(0 0 8px ${heat})`
    }
    return 'none'
  })

  // Dim links slightly so nodes are the focal point
  liveLinks
    .transition().duration(500)
    .attr('opacity', 0.25)
    .attr('stroke-width', 1)

  // Show all labels in heatmap mode so users can read the hot spots
  liveLabels
    .transition().duration(500)
    .style('opacity', 1)

  // Keep cached refs in sync
  nodeElements  = liveNodes
  linkElements  = liveLinks
  labelElements = liveLabels
}

const toggleHeatmap = () => {
  if (heatmapActive.value) {
    // Turning OFF — restore to default appearance
    heatmapActive.value = false
    resetHighlight()
  } else {
    // Turning ON — clear blast radius first, then apply heat
    if (blastRadiusNode) {
      blastRadiusNode = null
      g.select('.impact-badges').selectAll('*').remove()
      impactBadge = null
    }
    heatmapActive.value = true
    applyHeatmap()
  }
}

// ─── Stage 14: Topology Stats & Filtering ────────────────────────────────
const toggleTopologyFilter = (type) => {
  // Toggling the same pill off — resetHighlight clears activeTopologyFilter for us
  if (activeTopologyFilter.value === type) {
    resetHighlight()
    return
  }

  // Reset all D3 visuals to baseline first (this also nullifies activeTopologyFilter)
  resetHighlight()

  // Set the active filter AFTER reset, so the pill becomes visually active
  activeTopologyFilter.value = type

  if (!g) return

  const isMatch = (n) => {
    if (!n || !n.id) return false
    const isEntry = n.id.endsWith('App.vue') || n.id.endsWith('main.js') || n.id.includes('/router/')
    if (type === 'entryPoints') return isEntry
    if (type === 'hubs') return (n.in_degree || 0) >= 3 && (n.out_degree || 0) >= 3
    if (type === 'leaves') return (n.out_degree || 0) === 0
    if (type === 'orphans') return (n.in_degree || 0) === 0 && !isEntry
    return false
  }

  const liveNodes = g.select('.nodes').selectAll('circle')
  const liveLinks = g.select('.links').selectAll('path')
  const liveLabels = g.select('.labels').selectAll('text')

  liveNodes
    .transition().duration(300)
    .attr('opacity', function() {
      const d = d3.select(this).datum()
      return isMatch(d) ? 1 : 0.1
    })
    .attr('stroke-width', function() {
      const d = d3.select(this).datum()
      return isMatch(d) ? 3 : 2
    })

  liveLinks
    .transition().duration(300)
    .attr('opacity', function() {
      const d = d3.select(this).datum()
      if (!d) return 0.1
      const src = typeof d.source === 'object' ? d.source : { id: String(d.source), in_degree: 0, out_degree: 0 }
      const tgt = typeof d.target === 'object' ? d.target : { id: String(d.target), in_degree: 0, out_degree: 0 }
      return (isMatch(src) || isMatch(tgt)) ? 0.6 : 0.1
    })

  liveLabels
    .transition().duration(300)
    .style('opacity', function() {
      const d = d3.select(this).datum()
      return isMatch(d) ? 1 : 0
    })
}


const applyHighlight = (selectedNode) => {
  if (layoutMode.value === 'radial' || !nodeElements || !linkElements || !labelElements) return
  if (blastRadiusNode) return

  const connected = new Set([selectedNode.id])
  linkElements.each(d => {
    if (d.source.id === selectedNode.id) connected.add(d.target.id)
    if (d.target.id === selectedNode.id) connected.add(d.source.id)
  })

  nodeElements.attr('opacity', n => connected.has(n.id) ? (n.category === 'orphan' ? 0.8 : 1) : 0.1)
  linkElements
    .attr('opacity', d => (d.source.id === selectedNode.id || d.target.id === selectedNode.id) ? 1.0 : 0.1)
    .attr('stroke-width', d => (d.source.id === selectedNode.id || d.target.id === selectedNode.id) ? 2.5 : 1.5)
  labelElements.style('opacity', n => connected.has(n.id) ? 1 : (nodeRadius(n) < 8 ? 0 : 0.1))
}

const showBlastRadius = (selectedNode) => {
  if (layoutMode.value === 'radial' || !nodeElements || !linkElements || !labelElements) return

  const directDependents = new Set()
  const transitiveDependents = new Set()
  
  // Build reverse adjacency list (target -> list of sources) to find who depends on this node
  const adj = {}
  linkElements.each(d => {
    if (!adj[d.target.id]) adj[d.target.id] = []
    adj[d.target.id].push(d.source.id)
  })

  // Find direct dependents
  if (adj[selectedNode.id]) {
    adj[selectedNode.id].forEach(id => directDependents.add(id))
  }

  // BFS for transitive dependents
  const queue = [...directDependents]
  const visited = new Set(directDependents)
  while (queue.length > 0) {
    const curr = queue.shift()
    if (adj[curr]) {
      adj[curr].forEach(id => {
        if (!visited.has(id) && id !== selectedNode.id) {
          visited.add(id)
          transitiveDependents.add(id)
          queue.push(id)
        }
      })
    }
  }

  // Remove direct dependents from transitive set
  directDependents.forEach(id => transitiveDependents.delete(id))
  const totalAffected = directDependents.size + transitiveDependents.size

  nodeElements
    .attr('opacity', n => {
      if (n.id === selectedNode.id || directDependents.has(n.id)) return 1
      if (transitiveDependents.has(n.id)) return 0.6
      return 0.1
    })
    .attr('stroke', n => {
      if (n.id === selectedNode.id) return '#3b82f6' // Blue ring
      if (directDependents.has(n.id)) return '#f97316' // Orange tint
      if (transitiveDependents.has(n.id)) return '#eab308' // Yellow tint
      return (n.is_in_cycle || n.category === 'entry_point') ? (n.is_in_cycle ? '#dc2626' : '#facc15') : d3.color(getNodeColor(n)).darker(1).formatHex()
    })
    .attr('stroke-width', n => (n.id === selectedNode.id || directDependents.has(n.id) || transitiveDependents.has(n.id)) ? 3 : 2)
    .attr('fill', n => {
      if (n.id === selectedNode.id) return getNodeColor(n)
      if (directDependents.has(n.id)) return '#fdba74' // Light orange
      if (transitiveDependents.has(n.id)) return '#fde047' // Light yellow
      return n.category === 'missing' ? 'url(#missing-pattern)' : getNodeColor(n)
    })

  linkElements
    .attr('opacity', d => {
      if (d.target.id === selectedNode.id) return 1.0 
      if (transitiveDependents.has(d.source.id) && visited.has(d.target.id)) return 0.6 
      if (visited.has(d.source.id) && visited.has(d.target.id)) return 0.8
      if (visited.has(d.source.id) && d.target.id === selectedNode.id) return 1.0
      return 0.1
    })
    .attr('stroke-width', d => {
      if (d.target.id === selectedNode.id) return 2.5
      if (visited.has(d.source.id) && visited.has(d.target.id)) return 2
      return 1.5
    })
    .attr('stroke', d => {
       if (d.target.id === selectedNode.id) return '#f97316'
       if (visited.has(d.source.id) && visited.has(d.target.id)) return '#eab308'
       return getEdgeColor(d.relationship_type)
    })

  labelElements.style('opacity', n => {
    if (n.id === selectedNode.id || directDependents.has(n.id) || transitiveDependents.has(n.id)) return 1
    return nodeRadius(n) < 8 ? 0 : 0.1
  })

  // Add badge
  if (totalAffected > 0) {
    const badgeGroup = g.select('.impact-badges').selectAll('.badge').data([selectedNode], d => d.id)
    badgeGroup.exit().remove()
    
    const enter = badgeGroup.enter().append('g').attr('class', 'badge').attr('transform', d => `translate(${d.x},${d.y})`)
    enter.append('rect')
      .attr('x', 12).attr('y', -30)
      .attr('width', 96).attr('height', 18)
      .attr('rx', 4)
      .attr('fill', '#ef4444').attr('opacity', 0.95)
    enter.append('text')
      .attr('x', 60).attr('y', -17)
      .attr('fill', 'white')
      .attr('font-size', '9px')
      .attr('font-weight', 'bold')
      .attr('text-anchor', 'middle')
      .text(`Affects ${totalAffected} files`)
      .style('pointer-events', 'none')
    
    impactBadge = g.select('.impact-badges').selectAll('.badge')
  } else {
    g.select('.impact-badges').selectAll('*').remove()
    impactBadge = null
  }
}

const updateGraph = () => {
  if (!svg || !simulation) return

  const width = graphWrapper.value.clientWidth || 800
  const height = graphWrapper.value.clientHeight || 600

  let filteredNodes = rawData.nodes.filter(n => {
    if (showOrphansOnly.value) return n.category === 'orphan'
    if (showCyclesOnly.value) return n.is_in_cycle
    return true
  })

  const nodeIds = new Set(filteredNodes.map(n => n.id))

  let filteredEdges = rawData.edges.filter(e => {
    const srcId = typeof e.source === 'object' ? e.source.id : e.source
    const tgtId = typeof e.target === 'object' ? e.target.id : e.target
    if (!nodeIds.has(srcId) || !nodeIds.has(tgtId)) return false
    if (!filters.value[e.relationship_type]) return false
    return true
  })

  const oldNodes = new Map(simulation.nodes().map(d => [d.id, d]))
  graphNodes = filteredNodes.map(d => Object.assign(oldNodes.get(d.id) || {}, d))
  reactiveNodes.value = [...graphNodes]
  const graphLinks = filteredEdges.map(d => Object.assign({}, d))

  const maxDepth = Math.max(1, ...graphNodes.map(n => n.depth || 0))

  const minimapGroup = minimapSvg.select('.minimap-nodes')
  minimapNodes = minimapGroup.selectAll('circle')
    .data(graphNodes, d => d.id)
    .join('circle')
    .attr('r', 1.5)
    .attr('fill', d => getNodeColor(d))
    .attr('opacity', d => d.category === 'orphan' ? 0.5 : 0.8)

  linkElements = g.select('.links')
    .selectAll('path')
    .data(graphLinks, d => {
        const s = typeof d.source === 'object' ? d.source.id : d.source;
        const t = typeof d.target === 'object' ? d.target.id : d.target;
        return s + '-' + t;
    })
    .join('path')
    .attr('fill', 'none')
    .attr('stroke', d => getEdgeColor(d.relationship_type))
    .attr('stroke-width', 1.5)
    .attr('opacity', 0.6)
    .attr('stroke-dasharray', d => d.relationship_type === 'utility' ? '4,3' : 'none')
    .attr('marker-end', d => `url(#arrow-${d.relationship_type})`)

  nodeElements = g.select('.nodes')
    .selectAll('circle')
    .data(graphNodes, d => d.id)
    .join('circle')
    .attr('r', d => nodeRadius(d))
    .attr('fill', d => d.category === 'missing' ? 'url(#missing-pattern)' : getNodeColor(d))
    .attr('stroke', d => {
        if (d.is_in_cycle) return '#dc2626'; 
        if (d.category === 'entry_point') return '#facc15'; 
        const c = d3.color(getNodeColor(d));
        return c ? c.darker(1).formatHex() : '#000';
    })
    .attr('stroke-width', d => (d.is_in_cycle || d.category === 'entry_point') ? 3 : 2)
    .attr('stroke-dasharray', d => (d.is_in_cycle || d.category === 'orphan') ? '4,2' : 'none')
    .style('filter', d => (d.category === 'shared_utility' || d.in_degree >= 5) ? `drop-shadow(0 0 6px ${getNodeColor(d)})` : 'none')
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended)
    )
    .on('mouseover', (event, d) => {
      let tx = event.clientX + 15
      let ty = event.clientY - 15
      const w = 180, h = 100
      if (tx + w > window.innerWidth) tx = event.clientX - w - 15
      if (ty + h > window.innerHeight) ty = event.clientY - h - 15
      else if (ty < 0) ty = 15

      tooltip.value = {
        visible: true,
        x: tx,
        y: ty,
        data: {
          basename: getBasename(d.id),
          category: d.category,
          in_degree: d.in_degree,
          out_degree: d.out_degree,
          impact_score: d.impact_score,
          is_in_cycle: d.is_in_cycle
        }
      }
      if (!pinnedNode && !blastRadiusNode) applyHighlight(d)
    })
    .on('mousemove', (event) => {
      if (!tooltip.value.visible) return
      let tx = event.clientX + 15
      let ty = event.clientY - 15
      const w = 180, h = 100
      if (tx + w > window.innerWidth) tx = event.clientX - w - 15
      if (ty + h > window.innerHeight) ty = event.clientY - h - 15
      else if (ty < 0) ty = 15
      tooltip.value.x = tx
      tooltip.value.y = ty
    })
    .on('mouseout', () => {
      tooltip.value.visible = false
      if (!pinnedNode && !blastRadiusNode) resetHighlight()
    })
    .on('click', (event, d) => {
      event.stopPropagation()
      if (event.shiftKey) {
        if (blastRadiusNode && blastRadiusNode.id === d.id) {
          blastRadiusNode = null
          resetHighlight()
        } else {
          resetHighlight()
          blastRadiusNode = d
          showBlastRadius(d)
        }
      } else {
        enterFocusedMode(d)
      }
    })

  labelElements = g.select('.labels')
    .selectAll('text')
    .data(graphNodes, d => d.id)
    .join('text')
    .text(d => truncateLabel(getBasename(d.id)))
    .attr('font-size', d => (d.category === 'hub' || d.category === 'shared_utility') ? '12px' : '10px')
    .attr('fill', 'currentColor')
    .attr('text-anchor', 'middle')
    .attr('dy', d => nodeRadius(d) + 14)
    .style('opacity', d => nodeRadius(d) < 8 ? 0 : 1)
    .style('pointer-events', 'none')
    .attr('class', 'labels_text')

  simulation.nodes(graphNodes)
  simulation.force("link", d3.forceLink(graphLinks).id(d => d.id))
  simulation.force("center", d3.forceCenter(width / 2, height / 2).strength(0.08))
  simulation.force("x", d3.forceX(width / 2).strength(0.05))
  simulation.force("y", d3.forceY(height / 2).strength(0.05))
  simulation.force("layer", d3.forceY(d => {
    if (d.depth === 0 || d.category === 'entry_point') return height * 0.1
    if (d.category === 'orphan') return height * 0.9
    if (d.category === 'leaf') return height * 0.85
    return height * 0.1 + ((d.depth || 0) / maxDepth) * height * 0.7
  }).strength(0.3))
  simulation.force("collide", d3.forceCollide().radius(d => nodeRadius(d) + 12).iterations(3))
  
  resetHighlight()
  simulation.alpha(1).restart()
}

const highlightSearch = () => {
  const q = searchQuery.value.toLowerCase()
  pinnedNode = null
  if (layoutMode.value === 'radial') exitFocusedMode()
  if (!q) {
    resetHighlight()
    return
  }
  
  let firstMatch = null
  nodeElements.attr('opacity', d => {
    const match = d.id.toLowerCase().includes(q)
    if (match && !firstMatch) firstMatch = d
    return match ? (d.category === 'orphan' ? 0.8 : 1) : 0.1
  })
  linkElements.attr('opacity', 0.05).attr('stroke-width', 1.5)
  labelElements.style('opacity', d => d.id.toLowerCase().includes(q) ? 1 : 0)

  if (firstMatch) {
    const width = graphWrapper.value.clientWidth
    const height = graphWrapper.value.clientHeight || 600
    svg.transition().duration(750).call(
      zoom.transform,
      d3.zoomIdentity.translate(width / 2, height / 2).scale(1.5).translate(-firstMatch.x, -firstMatch.y)
    )
  }
}

const updateMinimap = () => {
  if (!minimapNodes || !minimapViewport || !graphNodes.length) return
  
  const width = 160; const height = 100;
  
  let xMin = d3.min(graphNodes, d => d.x) || 0
  let xMax = d3.max(graphNodes, d => d.x) || width
  let yMin = d3.min(graphNodes, d => d.y) || 0
  let yMax = d3.max(graphNodes, d => d.y) || height
  
  const pad = 40;
  xMin -= pad; xMax += pad; yMin -= pad; yMax += pad;
  
  const dx = xMax - xMin || 1
  const dy = yMax - yMin || 1
  
  const scale = Math.min(width / dx, height / dy)
  
  const ox = (width - dx * scale) / 2
  const oy = (height - dy * scale) / 2

  minimapNodes
    .attr('cx', d => ox + ((d.x || 0) - xMin) * scale)
    .attr('cy', d => oy + ((d.y || 0) - yMin) * scale)
    
  const mainW = graphWrapper.value.clientWidth || 800
  const mainH = graphWrapper.value.clientHeight || 600
  
  const top_left = currentTransform.invert([0, 0])
  const bottom_right = currentTransform.invert([mainW, mainH])
  
  const vx = ox + (top_left[0] - xMin) * scale
  const vy = oy + (top_left[1] - yMin) * scale
  const vw = (bottom_right[0] - top_left[0]) * scale
  const vh = (bottom_right[1] - top_left[1]) * scale
  
  minimapViewport
    .attr('x', vx)
    .attr('y', vy)
    .attr('width', Math.max(0, vw))
    .attr('height', Math.max(0, vh))
    
  if (minimapSvg.node()) {
    minimapSvg.node().__scale = scale
    minimapSvg.node().__ox = ox
    minimapSvg.node().__oy = oy
    minimapSvg.node().__xMin = xMin
    minimapSvg.node().__yMin = yMin
  }
}

const onMinimapClick = (event) => {
  if (!minimapSvg || !minimapSvg.node() || !minimapSvg.node().__scale || !svg) return
  
  const bounds = event.currentTarget.getBoundingClientRect()
  const clickX = event.clientX - bounds.left
  const clickY = event.clientY - bounds.top
  
  const scale = minimapSvg.node().__scale
  const ox = minimapSvg.node().__ox
  const oy = minimapSvg.node().__oy
  const xMin = minimapSvg.node().__xMin
  const yMin = minimapSvg.node().__yMin
  
  const graphX = (clickX - ox) / scale + xMin
  const graphY = (clickY - oy) / scale + yMin
  
  const mainW = graphWrapper.value.clientWidth || 800
  const mainH = graphWrapper.value.clientHeight || 600
  
  const k = currentTransform.k || 1
  const tx = mainW / 2 - graphX * k
  const ty = mainH / 2 - graphY * k
  
  svg.transition().duration(500).call(
    zoom.transform,
    d3.zoomIdentity.translate(tx, ty).scale(k)
  )
}

const zoomIn = () => {
  if (svg) svg.transition().duration(250).call(zoom.scaleBy, 1.2)
}
const zoomOut = () => {
  if (svg) svg.transition().duration(250).call(zoom.scaleBy, 0.8)
}
const fitGraph = () => {
  if (!svg || !g) return
  const bounds = g.node().getBBox()
  const fullWidth = graphWrapper.value.clientWidth || 800
  const fullHeight = graphWrapper.value.clientHeight || 600
  
  if (bounds.width === 0 || bounds.height === 0) return

  const padding = 40
  const width = bounds.width + padding * 2
  const height = bounds.height + padding * 2
  const midX = bounds.x + bounds.width / 2
  const midY = bounds.y + bounds.height / 2

  const scale = Math.max(0.1, Math.min(4, Math.min(fullWidth / width, fullHeight / height)))
  const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY]

  svg.transition().duration(750).call(
    zoom.transform,
    d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
  )
}
const resetZoom = () => {
  if (svg) {
    svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity)
  }
}

let preRadialTransform = null

const enterFocusedMode = (node) => {
  if (layoutMode.value === 'radial') {
    if (focusedNode.value?.id === node.id) return
  } else {
    preRadialTransform = currentTransform
  }
  
  layoutMode.value = 'radial'
  focusedNode.value = node
  pinnedNode = node

  simulation.stop()

  const width = graphWrapper.value.clientWidth || 800
  const height = graphWrapper.value.clientHeight || 600
  const cx = width / 2
  const cy = height / 2

  const deps = []
  const dependents = []
  
  linkElements.each(d => {
    if (d.source.id === node.id) deps.push(d.target)
    if (d.target.id === node.id) dependents.push(d.source)
  })
  
  const connectedNodes = new Set([...deps.map(n => n.id), ...dependents.map(n => n.id), node.id])

  node.fx = cx
  node.fy = cy

  const dependentRadius = Math.min(width, height) * 0.35
  dependents.forEach((n, i) => {
    const angle = dependents.length === 1 ? -Math.PI / 2 : -Math.PI + (i / (dependents.length - 1)) * Math.PI
    n.fx = cx + Math.cos(angle) * dependentRadius
    n.fy = cy + Math.sin(angle) * dependentRadius
  })

  const depRadius = Math.min(width, height) * 0.35
  deps.forEach((n, i) => {
    const angle = deps.length === 1 ? Math.PI / 2 : (i / (deps.length - 1)) * Math.PI
    n.fx = cx + Math.cos(angle) * depRadius
    n.fy = cy + Math.sin(angle) * depRadius
  })

  nodeElements.transition().duration(750)
    .attr("cx", d => d.fx !== undefined ? d.fx : d.x)
    .attr("cy", d => d.fy !== undefined ? d.fy : d.y)
    .attr('opacity', d => connectedNodes.has(d.id) ? (d.id === node.id ? 1 : 0.9) : 0)

  labelElements.transition().duration(750)
    .attr("x", d => d.fx !== undefined ? d.fx : d.x)
    .attr("y", d => d.fy !== undefined ? d.fy : d.y)
    .style('opacity', d => connectedNodes.has(d.id) ? 1 : 0)

  linkElements.transition().duration(750)
    .attr("d", d => {
       const sx = d.source.fx !== undefined ? d.source.fx : d.source.x
       const sy = d.source.fy !== undefined ? d.source.fy : d.source.y
       const tx = d.target.fx !== undefined ? d.target.fx : d.target.x
       const ty = d.target.fy !== undefined ? d.target.fy : d.target.y
       return `M${sx},${sy} L${tx},${ty}`
    })
    .attr('opacity', d => (d.source.id === node.id || d.target.id === node.id) ? 0.8 : 0)
    .attr('stroke-width', d => (d.source.id === node.id || d.target.id === node.id) ? 2.5 : 0)

  if (svg) {
    svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity)
  }
}

const exitFocusedMode = () => {
  // Switch layout state immediately so resetHighlight() guard passes
  layoutMode.value = 'force'
  focusedNode.value = null
  pinnedNode = null
  blastRadiusNode = null

  graphNodes.forEach(d => {
    d.fx = null
    d.fy = null
  })

  const finishExit = () => {
    simulation.alpha(0.3).restart()
    resetHighlight() // Safe: layoutMode is already 'force', nodeElements exist
  }

  if (svg && preRadialTransform) {
    svg.transition().duration(750).call(zoom.transform, preRadialTransform).on('end', finishExit)
  } else {
    finishExit()
  }
}

const dragstarted = (event, d) => {
  if (layoutMode.value === 'radial') return
  if (!event.active) simulation.alphaTarget(0.3).restart()
  d.fx = d.x
  d.fy = d.y
}
const dragged = (event, d) => {
  d.fx = event.x
  d.fy = event.y
}
const dragended = (event, d) => {
  if (!event.active) simulation.alphaTarget(0)
  d.fx = null
  d.fy = null
}
</script>
