<template>
  <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-[10px] overflow-hidden transition-all duration-200">
    <!-- Code Display -->
    <div class="flex flex-row overflow-x-auto font-mono text-[12px] leading-[1.6] bg-gray-50 dark:bg-gray-950">
      <!-- Line Numbers Column -->
      <div class="flex flex-col bg-gray-100 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 py-3 px-2 select-none shrink-0">
        <div
          v-for="(line, index) in parsedLines"
          :key="index"
          class="text-right px-2 min-w-[40px] transition-all duration-200 text-[11px]"
          :class="line.isTarget ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-500 dark:text-indigo-400 border-l-4 border-indigo-500 font-semibold -ml-1 pl-1' : 'text-gray-400 dark:text-gray-500 border-l-4 border-transparent'"
        >
          {{ line.lineNumber }}
        </div>
      </div>

      <!-- Code Content Column -->
      <div class="flex flex-col flex-1 p-3 overflow-x-auto">
        <div
          v-for="(line, index) in parsedLines"
          :key="index"
          class="whitespace-pre transition-all duration-200 px-2 -mx-2"
          :class="line.isTarget ? 'bg-indigo-50/50 dark:bg-indigo-900/20 border-l-4 border-indigo-500 text-gray-900 dark:text-white pl-1 font-medium' : 'text-gray-700 dark:text-gray-300 border-l-4 border-transparent'"
        >
          <span class="inline-block tracking-[0.5px]">{{ line.content }}</span>
        </div>
      </div>
    </div>

    <!-- Action Footer -->
    <div class="flex items-center justify-end py-2.5 px-3 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
      <button
        @click="copySnippet"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-transparent rounded-md text-[12px] font-medium cursor-pointer transition-all duration-200"
        :class="isCopied ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500' : 'border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'"
      >
        <svg v-if="isCopied" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
        </svg>
        <span>{{ isCopied ? 'Copied!' : 'Copy Snippet' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  code: {
    type: String,
    required: true
  },
  targetLine: {
    type: Number,
    default: null
  }
})

const isCopied = ref(false)

// Parse the code snippet into structured lines
const parsedLines = computed(() => {
  if (!props.code) return []

  const lines = props.code.split('\n')
  const parsed = []

  for (const line of lines) {
    // Check if line starts with ► (target marker) or spaces
    const isTarget = line.startsWith('►')
    
    // Extract line number and content
    // Format: "► 42: code content" or "  42: code content"
    const match = line.match(/^[►\s]{1,2}(\d+):\s?(.*)$/)
    
    if (match) {
      const lineNumber = parseInt(match[1], 10)
      const content = match[2]
      
      parsed.push({
        lineNumber,
        content,
        isTarget: isTarget || lineNumber === props.targetLine
      })
    } else {
      // Fallback for lines without proper format
      parsed.push({
        lineNumber: parsed.length + 1,
        content: line.replace(/^[►\s]{1,2}/, ''),
        isTarget: false
      })
    }
  }

  return parsed
})

// Copy snippet to clipboard
const copySnippet = async () => {
  try {
    // Extract just the code content without line numbers
    const codeOnly = parsedLines.value
      .map(line => line.content)
      .join('\n')
    
    await navigator.clipboard.writeText(codeOnly)
    isCopied.value = true
    
    // Reset after 2 seconds
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy code:', err)
  }
}
</script>
