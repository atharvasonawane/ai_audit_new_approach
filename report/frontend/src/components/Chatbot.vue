<template>
  <div
    :class="[
      'fixed inset-y-0 right-0 z-50 bg-white border-l border-gray-200 dark:bg-gray-950 dark:border-gray-800 shadow-2xl flex flex-col transform overflow-hidden',
      isOpen ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0 pointer-events-none',
      isResizing ? '' : 'transition-all duration-300 ease-in-out'
    ]"
    :style="{ width: chatbotWidthStyle }"
  >
    <!-- Resizer Handle -->
    <div
      class="absolute left-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-indigo-500/40 active:bg-indigo-600/60 transition-colors z-50 flex items-center justify-center group"
      @mousedown="startResize"
    >
      <div class="w-[2px] h-8 bg-gray-300 dark:bg-gray-700 rounded group-hover:bg-indigo-500/80 transition-colors"></div>
    </div>

    <!-- Header -->
    <div class="px-5 py-3.5 border-b border-gray-200 dark:border-gray-800/80 flex items-center justify-between shrink-0 bg-white dark:bg-gray-950 z-20 shadow-sm">
      <div class="flex items-center gap-2.5 min-w-0">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center bg-indigo-500/10 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 shrink-0 shadow-inner">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <div class="flex flex-col gap-0.5 min-w-0">
          <h3 class="text-[13px] font-bold text-gray-900 dark:text-white tracking-tight m-0 truncate">Audit Librarian</h3>
          <span class="text-[9px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest leading-none">AI Copilot</span>
        </div>
      </div>
      <button 
        class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        @click="$emit('close')"
        title="Close Sidebar"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- Messages Container -->
    <div ref="messageContainer" class="flex-1 overflow-y-auto px-4 py-5 space-y-5 bg-slate-50/50 dark:bg-gray-950/20 scrollbar-thin scrollbar-thumb-gray-200 dark:scrollbar-thumb-gray-800 scrollbar-track-transparent">
      <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-center text-gray-400 dark:text-gray-500 gap-3 px-4 py-10">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-30 text-indigo-500">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
        <p class="text-[12px] max-w-[240px] leading-relaxed">Ask questions about this code audit run. Mention file names, ask for worst offenders, or check WCAG failures.</p>
      </div>
      
      <div 
        v-for="(msg, index) in messages" 
        :key="index"
        :class="['flex flex-col max-w-[92%]', msg.role === 'user' ? 'ml-auto items-end' : 'mr-auto items-start']"
      >
        <span class="text-[9px] text-gray-400 dark:text-gray-500 font-bold uppercase tracking-wider mb-1 px-1">
          {{ msg.role === 'user' ? 'You' : 'Librarian' }}
        </span>
        <div 
          :class="[
            'px-4 py-3 rounded-2xl text-[13px] leading-relaxed shadow-sm font-normal break-words w-full',
            msg.role === 'user' 
              ? 'bg-gradient-to-br from-indigo-500 to-indigo-600 dark:from-indigo-600 dark:to-indigo-700 text-white rounded-tr-none shadow-[0_4px_12px_rgba(99,102,241,0.15)]' 
              : 'bg-white dark:bg-gray-900/80 text-gray-800 dark:text-gray-100 rounded-tl-none border border-gray-200/50 dark:border-gray-800/80 shadow-[0_2px_8px_rgba(0,0,0,0.02)]'
          ]"
        >
          <!-- Streaming placeholder dots -->
          <div v-if="msg.isStreaming && !msg.content" class="flex items-center gap-1 py-1">
            <span class="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
            <span class="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
            <span class="w-1.5 h-1.5 bg-gray-500 dark:bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
          </div>

          <!-- Message content with inline file/code badges -->
          <div v-if="msg.content" class="whitespace-pre-wrap font-sans break-words leading-relaxed text-[13px]">
            <template v-for="(part, pi) in renderBadges(msg.content)" :key="pi">
              <!-- File badge: clickable token that navigates the dashboard to the file -->
              <button
                v-if="part.isFile"
                class="max-w-full bg-indigo-50 dark:bg-indigo-950/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 border border-indigo-100/50 dark:border-indigo-800/40 hover:border-indigo-400 px-2.5 py-1 rounded-md cursor-pointer hover:underline font-mono inline-flex items-center gap-1.5 text-[11px] mx-0.5 my-0.5 transition-all shadow-sm font-semibold align-middle overflow-hidden"
                :title="'Jump to ' + part.text"
                @click="$emit('navigate-to-file', part.text)"
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="opacity-80 shrink-0">
                  <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                  <polyline points="13 2 13 9 20 9"/>
                </svg>
                <span class="truncate block max-w-[150px] sm:max-w-[260px]">{{ part.text }}</span>
              </button>
              <!-- Inline code highlight -->
              <span
                v-else-if="part.isCode"
                class="bg-amber-500/10 dark:bg-amber-400/10 text-amber-600 dark:text-amber-400 border border-amber-500/10 dark:border-amber-400/10 px-1 py-0.5 rounded font-mono text-[12px] font-semibold mx-0.5 shadow-sm break-all align-middle"
              >{{ part.text }}</span>
              <!-- Plain text span -->
              <span v-else>{{ part.text }}</span>
            </template>
          </div>
        </div>

        <!-- Sources Accordion: only shown below assistant messages with cited sources -->
        <div
          v-if="msg.role === 'assistant' && msg.sources && msg.sources.length > 0"
          class="mt-2 w-full border border-gray-200/60 dark:border-gray-800/60 bg-white/40 dark:bg-gray-900/30 rounded-xl text-xs overflow-hidden shadow-sm backdrop-blur-sm"
        >
          <!-- Accordion toggle header -->
          <button
            class="w-full flex items-center justify-between px-3 py-2 text-[10px] font-bold text-gray-500 dark:text-gray-400 bg-gray-50/50 dark:bg-gray-900/30 hover:bg-gray-100/50 dark:hover:bg-gray-900/60 hover:text-gray-700 dark:hover:text-gray-200 transition-colors cursor-pointer"
            @click="msg.sourcesOpen = !msg.sourcesOpen"
          >
            <span class="flex items-center gap-1.5 uppercase tracking-wider leading-none">
              <span>📂</span>
              <span>Grounded Analysis Data Sources</span>
            </span>
            <svg
              width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
              :class="['transition-transform duration-200', msg.sourcesOpen ? 'rotate-180' : '']"
            >
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>
          <!-- Accordion body -->
          <div
            v-show="msg.sourcesOpen"
            class="border-t border-gray-200/50 dark:border-gray-800/50 px-3 py-2 bg-white/30 dark:bg-gray-955/20"
          >
            <ul class="space-y-1 m-0 p-0 list-none">
              <li
                v-for="(src, si) in msg.sources"
                :key="si"
                class="flex items-start gap-1.5 text-gray-500 dark:text-gray-400 font-medium text-[10.5px] leading-relaxed"
              >
                <span class="mt-1 shrink-0 text-emerald-500 text-[10px] leading-none">•</span>
                <span>{{ src }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Recommendation Chips & Input -->
    <div class="px-4 py-4 border-t border-gray-200/80 dark:border-gray-800/80 bg-white dark:bg-gray-950 shrink-0 z-20">
      <!-- Chips -->
      <div v-if="messages.length === 0" class="flex flex-col gap-2 mb-3.5">
        <span class="text-[9px] text-gray-400 dark:text-gray-500 font-bold uppercase tracking-widest px-0.5">Suggestions</span>
        <div class="flex flex-wrap gap-1.5">
          <button 
            v-for="(chip, i) in chips" 
            :key="i"
            class="text-[10.5px] font-semibold text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-full px-3.5 py-1.5 hover:border-indigo-500 dark:hover:border-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all duration-200 text-left cursor-pointer shadow-sm hover:shadow hover:-translate-y-[0.5px]"
            @click="selectChip(chip)"
          >
            {{ chip }}
          </button>
        </div>
      </div>

      <!-- Input Form (Integrated Pill) -->
      <form @submit.prevent="submitMessage" class="relative flex items-center bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/10 transition-all px-3 py-1.5 shadow-inner">
        <input 
          v-model="inputMessage"
          type="text"
          placeholder="Ask about files, WCAG rules, worst complexity..."
          class="flex-1 bg-transparent text-[12px] text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none pr-9 border-none outline-none"
          :disabled="isLoading"
        />
        <button 
          type="submit"
          class="absolute right-1.5 p-1.5 bg-gradient-to-br from-indigo-500 to-indigo-600 text-white rounded-lg hover:from-indigo-600 hover:to-indigo-700 transition-all duration-200 shadow-md shadow-indigo-500/15 disabled:opacity-40 disabled:from-indigo-500/40 disabled:to-indigo-600/40 disabled:shadow-none disabled:cursor-not-allowed disabled:transform-none shrink-0"
          :disabled="isLoading || !inputMessage.trim()"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  runId: {
    type: [Number, String],
    required: true
  }
})

const emit = defineEmits(['close', 'navigate-to-file'])

const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const messageContainer = ref(null)

const chips = [
  "Show Critical Finding Summary",
  "Worst Files by Issue Counts",
  "Check Accessibility Failures"
]

// ── Resizable Chatbot Sidebar Logic ───────────────────────────────────────────
const chatbotWidth = ref(384) // Default sidebar width
const isResizing = ref(false)

const startResize = (e) => {
  isResizing.value = true
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

const onResize = (e) => {
  if (isResizing.value) {
    let newWidth = window.innerWidth - e.clientX
    const minWidth = Math.min(320, window.innerWidth)
    const maxWidth = Math.min(700, window.innerWidth)
    if (newWidth < minWidth) newWidth = minWidth
    if (newWidth > maxWidth) newWidth = maxWidth
    chatbotWidth.value = newWidth
  }
}

const stopResize = () => {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// Computes the CSS width string. If viewport is very small (e.g. extension pane < 360px), forces 100vw.
const chatbotWidthStyle = computed(() => {
  if (window.innerWidth < 360) {
    return '100vw'
  }
  return chatbotWidth.value + 'px'
})

const scrollToBottom = () => {
  if (messageContainer.value) {
    messageContainer.value.scrollTop = messageContainer.value.scrollHeight
  }
}

watch(messages, () => {
  nextTick(scrollToBottom)
}, { deep: true })

// ── localStorage persistence ──────────────────────────────────────────────────
const storageKey = computed(() => `audit_chat_history_${props.runId}`)

/**
 * loadChatHistory — rehydrates messages from localStorage for the current run.
 */
const loadChatHistory = () => {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        messages.value = parsed.map(m => ({
          ...m,
          isStreaming: false,
          sourcesOpen: false
        }))
        return
      }
    }
  } catch (e) {
    console.warn('[Chat] localStorage parse error — resetting history for run', props.runId, e)
  }
  messages.value = []
}

watch(() => props.runId, () => {
  loadChatHistory()
}, { immediate: true })

const selectChip = (chipText) => {
  inputMessage.value = chipText
  submitMessage()
}

/**
 * renderBadges: Splits a message string into segments.
 * Tokens ending in .vue, .js, or .ts are returned as { isFile: true, text }.
 * Tokens wrapped inside backticks are returned as { isCode: true, text }.
 * Standard text is returned as { isFile: false, isCode: false, text }.
 */
const renderBadges = (content) => {
  if (!content) return [{ isFile: false, isCode: false, text: '' }]
  const parts = []
  let lastIndex = 0
  let match
  // Matches `inline_code` or a file reference like client/src/App.vue
  const regex = /(`[^`]+`|[\w./\-]+\.(?:vue|js|ts))/g
  
  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        isFile: false,
        isCode: false,
        text: content.slice(lastIndex, match.index)
      })
    }
    
    const token = match[0]
    if (token.startsWith('`') && token.endsWith('`')) {
      parts.push({
        isFile: false,
        isCode: true,
        text: token.slice(1, -1)
      })
    } else {
      parts.push({
        isFile: true,
        isCode: false,
        text: token
      })
    }
    
    lastIndex = regex.lastIndex
  }
  
  if (lastIndex < content.length) {
    parts.push({
      isFile: false,
      isCode: false,
      text: content.slice(lastIndex)
    })
  }
  
  return parts
}

const submitMessage = async () => {
  const cleanMsg = String(inputMessage.value).trim()
  if (!cleanMsg || isLoading.value) return

  const activeRunId = Number(props.runId || (route && route.query && route.query.run_id) || 0)

  messages.value.push({
    role: 'user',
    content: cleanMsg,
    isStreaming: false,
    sources: [],
    sourcesOpen: false
  })
  
  inputMessage.value = ''
  isLoading.value = true

  messages.value.push({
    role: 'assistant',
    content: '',
    isStreaming: true,
    sources: [],
    sourcesOpen: false
  })

  try {
    const historyPayload = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content
    }))

    const response = await fetch('http://localhost:5000/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        run_id: activeRunId,
        message: cleanMsg,
        history: historyPayload
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status} - ${response.statusText}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let isDone = false

    while (!isDone) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const cleaned = line.trim()
        if (!cleaned) continue
        if (!cleaned.startsWith('data:')) continue

        const dataStr = cleaned.slice(5).trim()

        if (dataStr === '[DONE]') {
          isDone = true
          break
        }

        let parsed
        try {
          parsed = JSON.parse(dataStr)
        } catch (e) {
          console.warn('[SSE] Failed to parse frame payload:', dataStr, e)
          continue
        }

        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          console.warn('[SSE] Unexpected non-object frame — discarding:', parsed)
          continue
        }

        if ('sources' in parsed && Array.isArray(parsed.sources)) {
          messages.value[messages.value.length - 1].sources = parsed.sources
          continue
        }

        if ('token' in parsed && typeof parsed.token === 'string' && parsed.token.length > 0) {
          messages.value[messages.value.length - 1].content += parsed.token
          continue
        }

        if ('error' in parsed && typeof parsed.error === 'string' && parsed.error.length > 0) {
          messages.value[messages.value.length - 1].content += `\n[Error: ${parsed.error}]`
          continue
        }
      }
    }
  } catch (err) {
    console.error('Chat error:', err)
    messages.value[messages.value.length - 1].content += `\n[System Error: Could not connect to chatbot API. Ensure backend is running. ${err.message}]`
  } finally {
    messages.value[messages.value.length - 1].isStreaming = false
    isLoading.value = false
    try {
      const toStore = messages.value.map(m => {
        const { sourcesOpen, ...rest } = m
        return rest
      })
      localStorage.setItem(storageKey.value, JSON.stringify(toStore))
    } catch (e) {
      console.warn('[Chat] Failed to persist chat history to localStorage:', e)
    }
  }
}
</script>
