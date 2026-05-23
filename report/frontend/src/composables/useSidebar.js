import { ref } from 'vue'

const DEFAULT_WIDTH = 240
const MIN_WIDTH = 180
const MAX_WIDTH = 400

const isCollapsed = ref(false)
const sidebarWidth = ref(DEFAULT_WIDTH)

// Initialize from localStorage on load
if (typeof window !== 'undefined') {
  const savedCollapsed = localStorage.getItem('sidebar_collapsed')
  if (savedCollapsed) {
    isCollapsed.value = savedCollapsed === 'true'
  }
  
  const savedWidth = localStorage.getItem('sidebar_width')
  if (savedWidth) {
    const widthNum = Number(savedWidth)
    if (!isNaN(widthNum) && widthNum >= MIN_WIDTH && widthNum <= MAX_WIDTH) {
      sidebarWidth.value = widthNum
    }
  }
}

export function useSidebar() {
  const toggleSidebar = () => {
    isCollapsed.value = !isCollapsed.value
    localStorage.setItem('sidebar_collapsed', String(isCollapsed.value))
  }

  const setSidebarWidth = (width) => {
    let targetWidth = width
    if (targetWidth < MIN_WIDTH) targetWidth = MIN_WIDTH
    if (targetWidth > MAX_WIDTH) targetWidth = MAX_WIDTH
    sidebarWidth.value = targetWidth
    localStorage.setItem('sidebar_width', String(targetWidth))
  }

  const resetSidebarWidth = () => {
    sidebarWidth.value = DEFAULT_WIDTH
    localStorage.setItem('sidebar_width', String(DEFAULT_WIDTH))
  }

  return {
    isCollapsed,
    sidebarWidth,
    toggleSidebar,
    setSidebarWidth,
    resetSidebarWidth,
    MIN_WIDTH,
    MAX_WIDTH,
    DEFAULT_WIDTH
  }
}
