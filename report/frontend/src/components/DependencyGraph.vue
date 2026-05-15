<template>
  <div class="dependency-graph-container">
    <div class="graph-controls">
      <input type="text" v-model="searchQuery" placeholder="Search files..." class="search-box" @input="highlightSearch" />
      <div class="toggles">
        <label><input type="checkbox" v-model="filters.component" /> Component</label>
        <label><input type="checkbox" v-model="filters.composable" /> Composable</label>
        <label><input type="checkbox" v-model="filters.store" /> Store</label>
        <label><input type="checkbox" v-model="filters.service" /> Service</label>
        <label><input type="checkbox" v-model="filters.router" /> Router</label>
        <label><input type="checkbox" v-model="filters.utility" /> Utility</label>
        
        <button class="btn-toggle" :class="{active: showOrphansOnly}" @click="toggleOrphans">Show Orphans Only</button>
        <button class="btn-toggle" :class="{active: showCyclesOnly}" @click="toggleCycles">Show Cycles Only</button>
      </div>
    </div>
    
    <div class="graph-wrapper" ref="graphWrapper">
      <svg ref="svgRef" class="d3-svg"></svg>
      
      <!-- Tooltip -->
      <div v-if="tooltip.visible" class="d3-tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
        <div class="tt-title">{{ tooltip.data.basename }}</div>
        <div class="tt-cat" :style="{color: getNodeColor(tooltip.data)}">{{ tooltip.data.category }}</div>
        <div class="tt-metrics">
          <div>In: <strong>{{ tooltip.data.in_degree }}</strong></div>
          <div>Out: <strong>{{ tooltip.data.out_degree }}</strong></div>
          <div>Impact: <strong>{{ tooltip.data.impact_score }}</strong></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'
import { filesAPI } from '../api.js'

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

<style scoped>
.dependency-graph-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  overflow: hidden;
}

.graph-controls {
  padding: 16px;
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
}

.search-box {
  padding: 8px 12px;
  border-radius: var(--rounded-base);
  border: 1px solid var(--color-border-emphasis);
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  min-width: 250px;
}

.toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.toggles label {
  font-size: 12px;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.btn-toggle {
  padding: 6px 12px;
  border-radius: var(--rounded-full);
  border: 1px solid var(--color-border-emphasis);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 150ms;
}

.btn-toggle.active {
  background: var(--color-accent-primary);
  color: white;
  border-color: var(--color-accent-primary);
}

.graph-wrapper {
  flex: 1;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 600px;
}

.d3-svg {
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
}
.d3-svg:active { cursor: grabbing; }

.d3-tooltip {
  position: absolute;
  background: rgba(13, 17, 23, 0.95);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-base);
  padding: 12px;
  pointer-events: none;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  min-width: 150px;
}

.tt-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.tt-cat {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.tt-metrics {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.tt-metrics strong { color: var(--color-text-primary); }
</style>
