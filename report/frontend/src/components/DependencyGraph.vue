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
      </div>
    </div>

    <div v-show="viewMode === 'graph'" class="flex-1 relative w-full h-[600px] border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 overflow-hidden" ref="graphWrapper">
      <svg ref="svgRef" class="w-full h-full block cursor-grab active:cursor-grabbing [&_.labels_text]:!fill-gray-900 dark:[&_.labels_text]:!fill-gray-100 [&_.nodes_circle]:!stroke-white dark:[&_.nodes_circle]:!stroke-gray-950"></svg>
      
      <!-- Tooltip -->
      <div v-show="tooltip.visible && viewMode === 'graph'" class="absolute bg-white/95 dark:bg-gray-950/95 border border-gray-200 dark:border-gray-800 rounded-lg p-3 text-gray-900 dark:text-gray-100 pointer-events-none z-[100] shadow-[0_4px_12px_rgba(0,0,0,0.15)] min-w-[150px] backdrop-blur-sm" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
        <div class="text-[13px] font-semibold text-gray-900 dark:text-gray-100 mb-1">{{ tooltip.data.basename }}</div>
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] mb-2" :style="{color: getNodeColor(tooltip.data)}">{{ tooltip.data.category }}</div>
        <div class="flex flex-col gap-0.5 text-[12px] text-gray-600 dark:text-gray-400">
          <div>In: <strong class="text-gray-900 dark:text-gray-100">{{ tooltip.data.in_degree }}</strong></div>
          <div>Out: <strong class="text-gray-900 dark:text-gray-100">{{ tooltip.data.out_degree }}</strong></div>
          <div>Impact: <strong class="text-gray-900 dark:text-gray-100">{{ tooltip.data.impact_score }}</strong></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'
import { filesAPI } from '../api.js'
import DependencyTable from './DependencyTable.vue'

const viewMode = ref('graph')

const svgRef = ref(null)
const graphWrapper = ref(null)

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

let rawData = { nodes: [], edges: [] }
let simulation = null
let svg = null
let g = null
let linkElements = null
let nodeElements = null
let zoom = null
let labelElements = null

const getNodeColor = (d) => {
  if (d.is_in_cycle) return '#F85149' // Red
  if (d.category === 'entry_point') return '#8957E5' // Purple
  if (d.category === 'orphan') return '#D29922' // Amber
  if (d.category === 'hub') return '#F0883E' // Orange
  if (d.category === 'shared_utility') return '#3FB950' // Green
  if (d.category === 'leaf') return '#2ea043' // Darker green
  return '#388BFD' // Blue
}

const getEdgeColor = (type) => {
  const map = {
    'component': '#388BFD', // Blue
    'composable': '#8957E5', // Purple
    'store': '#F0883E', // Orange
    'service': '#F85149', // Red
    'router': '#1f6FEB', // Dark blue
    'utility': '#8b949e' // Grey
  }
  return map[type] || '#8b949e'
}

const nodeRadius = (d) => Math.max(6, Math.min(25, 6 + (d.in_degree * 1.5)))

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
  if (!nodeElements || !linkElements) return

  linkElements.attr("d", d => {
    const dx = d.target.x - d.source.x
    const dy = d.target.y - d.source.y
    return `M${d.source.x},${d.source.y} C${d.source.x},${(d.source.y + d.target.y)/2} ${d.target.x},${(d.source.y + d.target.y)/2} ${d.target.x},${d.target.y}`
  })
  
  nodeElements.attr("cx", d => d.x).attr("cy", d => d.y)
  if (labelElements) labelElements.attr("x", d => d.x).attr("y", d => d.y)
  
  if (svg) svg.selectAll('marker').attr('refX', 22)
}

const initGraph = () => {
  const width = graphWrapper.value.clientWidth || 800
  const height = graphWrapper.value.clientHeight || 600

  svg = d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height)
    .on('click', () => {
      nodeElements.attr('opacity', 1)
      linkElements.attr('opacity', 0.6).attr('stroke-width', 1.5)
    })

  svg.append('defs').selectAll('marker')
    .data(['component', 'composable', 'store', 'service', 'router', 'utility'])
    .enter().append('marker')
    .attr('id', d => `arrow-${d}`)
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 5)
    .attr('markerHeight', 5)
    .attr('orient', 'auto')
    .append('path')
    .attr('fill', d => getEdgeColor(d))
    .attr('d', 'M0,-5L10,0L0,5')

  g = svg.append('g')
  
  g.append('g').attr('class', 'links')
  g.append('g').attr('class', 'nodes')
  g.append('g').attr('class', 'labels')

  zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })
  svg.call(zoom)

  simulation = d3.forceSimulation()
    .force("charge", d3.forceManyBody().strength(-1000))
    .on("tick", ticked)

  updateGraph()
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
  const graphNodes = filteredNodes.map(d => Object.assign(oldNodes.get(d.id) || {}, d))
  const graphLinks = filteredEdges.map(d => Object.assign({}, d))

  const maxDepth = Math.max(0, ...graphNodes.map(n => n.depth || 0))
  const bottomOffset = maxDepth * 150 + 200

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
    .attr('marker-end', d => `url(#arrow-${d.relationship_type})`)

  nodeElements = g.select('.nodes')
    .selectAll('circle')
    .data(graphNodes, d => d.id)
    .join('circle')
    .attr('r', d => nodeRadius(d))
    .attr('fill', d => getNodeColor(d))
    .attr('stroke', '#0d1117')
    .attr('stroke-width', 2)
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended)
    )
    .on('mouseover', (event, d) => {
      tooltip.value = {
        visible: true,
        x: event.pageX + 15,
        y: event.pageY - 15,
        data: {
          basename: getBasename(d.id),
          category: d.category,
          in_degree: d.in_degree,
          out_degree: d.out_degree,
          impact_score: d.impact_score,
          is_in_cycle: d.is_in_cycle
        }
      }
    })
    .on('mouseout', () => { tooltip.value.visible = false })
    .on('click', (event, d) => {
      event.stopPropagation()
      highlightNode(d)
    })

  labelElements = g.select('.labels')
    .selectAll('text')
    .data(graphNodes.filter(n => n.category === 'entry_point' || n.category === 'hub' || n.in_degree > 5), d => d.id)
    .join('text')
    .text(d => getBasename(d.id))
    .attr('font-size', '10px')
    .attr('fill', '#c9d1d9')
    .attr('dx', 12)
    .attr('dy', 4)
    .style('pointer-events', 'none')

  simulation.nodes(graphNodes)
  simulation.force("link", d3.forceLink(graphLinks).id(d => d.id))
  simulation.force("x", d3.forceX(width / 2).strength(0.05))
  simulation.force("y", d3.forceY(d => (d.depth === -1 ? bottomOffset : (d.depth || 0) * 150 + 50)).strength(1))
  simulation.force("collide", d3.forceCollide().radius(d => nodeRadius(d) + 20).iterations(3))
  simulation.force("center", null)
  
  simulation.alpha(1).restart()
}

const highlightNode = (selectedNode) => {
  const connected = new Set([selectedNode.id])
  linkElements.each(d => {
    if (d.source.id === selectedNode.id) connected.add(d.target.id)
    if (d.target.id === selectedNode.id) connected.add(d.source.id)
  })

  nodeElements.attr('opacity', d => connected.has(d.id) ? 1 : 0.1)
  linkElements
    .attr('opacity', d => (d.source.id === selectedNode.id || d.target.id === selectedNode.id) ? 1 : 0.05)
    .attr('stroke-width', d => (d.source.id === selectedNode.id || d.target.id === selectedNode.id) ? 3 : 1)
}

const highlightSearch = () => {
  const q = searchQuery.value.toLowerCase()
  if (!q) {
    nodeElements.attr('opacity', 1)
    return
  }
  
  let firstMatch = null
  nodeElements.attr('opacity', d => {
    const match = d.id.toLowerCase().includes(q)
    if (match && !firstMatch) firstMatch = d
    return match ? 1 : 0.1
  })

  if (firstMatch) {
    const width = graphWrapper.value.clientWidth
    const height = graphWrapper.value.clientHeight || 600
    svg.transition().duration(750).call(
      zoom.transform,
      d3.zoomIdentity.translate(width / 2, height / 2).scale(1.5).translate(-firstMatch.x, -firstMatch.y)
    )
  }
}

const dragstarted = (event, d) => {
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
