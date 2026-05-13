<template>
  <div class="code-snippet-container">
    <!-- Code Display -->
    <div class="code-display">
      <!-- Line Numbers Column -->
      <div class="line-numbers">
        <div
          v-for="(line, index) in parsedLines"
          :key="index"
          class="line-number"
          :class="{ highlighted: line.isTarget }"
        >
          {{ line.lineNumber }}
        </div>
      </div>

      <!-- Code Content Column -->
      <div class="code-content">
        <div
          v-for="(line, index) in parsedLines"
          :key="index"
          class="code-line"
          :class="{ highlighted: line.isTarget }"
        >
          <span class="code-text">{{ line.content }}</span>
        </div>
      </div>
    </div>

    <!-- Action Footer -->
    <div class="snippet-actions">
      <button
        @click="copySnippet"
        class="action-button"
        :class="{ copied: isCopied }"
      >
        <Check v-if="isCopied" :size="14" :stroke-width="2" />
        <Copy v-else :size="14" :stroke-width="2" />
        <span>{{ isCopied ? 'Copied!' : 'Copy Snippet' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Copy, Check } from 'lucide-vue-next'

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

<style scoped>
.code-snippet-container {
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  overflow: hidden;
}

.code-display {
  display: flex;
  flex-direction: row;
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}

/* Line Numbers Column */
.line-numbers {
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-tertiary);
  padding: 12px 8px;
  user-select: none;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
}

.line-number {
  text-align: right;
  color: var(--color-text-tertiary);
  padding: 0 8px;
  min-width: 40px;
  transition: all 200ms ease-out;
}

.line-number.highlighted {
  background-color: rgba(59, 130, 246, 0.15);
  color: var(--color-accent-primary);
  font-weight: 600;
  border-left: 3px solid var(--color-accent-primary);
  margin-left: -3px;
}

/* Code Content Column */
.code-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 12px;
  overflow-x: auto;
}

.code-line {
  color: var(--color-text-primary);
  white-space: pre;
  transition: all 200ms ease-out;
  padding: 0 8px;
  margin: 0 -8px;
}

.code-line.highlighted {
  background-color: rgba(59, 130, 246, 0.1);
  border-left: 3px solid var(--color-accent-primary);
  padding-left: 5px;
  font-weight: 500;
}

.code-text {
  display: inline-block;
}

/* Action Footer */
.snippet-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 8px 12px;
  background-color: var(--color-bg-secondary);
  border-top: 1px solid var(--color-border);
}

.action-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background-color: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: 500;
  cursor: pointer;
  transition: all 200ms ease-out;
}

.action-button:hover {
  background-color: var(--color-bg-tertiary);
  border-color: var(--color-accent-primary);
  color: var(--color-text-primary);
}

.action-button.copied {
  background-color: rgba(16, 185, 129, 0.1);
  border-color: var(--color-status-success);
  color: var(--color-status-success);
}

/* Scrollbar styling for code content */
.code-display::-webkit-scrollbar,
.code-content::-webkit-scrollbar {
  height: 8px;
}

.code-display::-webkit-scrollbar-track,
.code-content::-webkit-scrollbar-track {
  background: var(--color-bg-primary);
}

.code-display::-webkit-scrollbar-thumb,
.code-content::-webkit-scrollbar-thumb {
  background: var(--color-bg-tertiary);
  border-radius: var(--rounded-base);
}

.code-display::-webkit-scrollbar-thumb:hover,
.code-content::-webkit-scrollbar-thumb:hover {
  background: var(--color-bg-hover);
}
</style>
