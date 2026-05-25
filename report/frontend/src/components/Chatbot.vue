<template>
  <div
    :class="[
      'fixed inset-y-0 right-0 z-50 w-96 bg-white border-l border-gray-200 dark:bg-gray-900 dark:border-gray-800 shadow-2xl flex flex-col transition-all duration-300 ease-in-out transform',
      isOpen ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0 pointer-events-none'
    ]"
  >
    <!-- Header -->
    <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800/50 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-emerald-500">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
        <h3 class="text-sm font-bold text-gray-900 dark:text-gray-50 tracking-tight">Audit Librarian Chat</h3>
      </div>
      <button 
        class="p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
        @click="$emit('close')"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- Messages Container -->
    <div ref="messageContainer" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-center text-gray-400 dark:text-gray-500 gap-3 px-4">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-30">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
        <p class="text-xs">Ask questions about this code audit run. Mention file names, ask for worst offenders, or check WCAG failures.</p>
      </div>
      
      <div 
        v-for="(msg, index) in messages" 
        :key="index"
        :class="['flex flex-col max-w-[85%]', msg.role === 'user' ? 'ml-auto items-end' : 'mr-auto items-start']"
      >
        <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider mb-1 px-1">
          {{ msg.role === 'user' ? 'You' : 'Librarian' }}
        </span>
        <div 
          :class="[
            'px-4 py-3 rounded-2xl text-[13px] leading-relaxed shadow-sm font-normal break-words w-full',
            msg.role === 'user' 
              ? 'bg-emerald-600 text-white rounded-tr-none' 
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-none border border-gray-200/20'
          ]"
        >
          <!-- Streaming placeholder dots -->
          <div v-if="msg.isStreaming && !msg.content" class="flex items-center gap-1 py-1">
            <span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
            <span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
            <span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
          </div>

          <!-- Message content with inline file badges -->
          <div v-if="msg.content" class="whitespace-pre-wrap font-sans">
            <template v-for="(part, pi) in renderBadges(msg.content)" :key="pi">
              <!-- File badge: clickable token that navigates the dashboard to the file -->
              <button
                v-if="part.isFile"
                class="bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded cursor-pointer hover:underline font-mono inline-block text-[11px] mx-0.5 transition-colors"
                :title="'Jump to ' + part.text"
                @click="$emit('navigate-to-file', part.text)"
              >{{ part.text }}</button>
              <!-- Plain text span -->
              <span v-else>{{ part.text }}</span>
            </template>
          </div>
        </div>

        <!-- Sources Accordion: only shown below assistant messages with cited sources -->
        <div
          v-if="msg.role === 'assistant' && msg.sources && msg.sources.length > 0"
          class="mt-1.5 w-full border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 rounded-md text-xs overflow-hidden"
        >
          <!-- Accordion toggle header -->
          <button
            class="w-full flex items-center justify-between px-3 py-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            @click="msg.sourcesOpen = !msg.sourcesOpen"
          >
            <span class="flex items-center gap-1.5 font-semibold tracking-wide">
              <span>📂</span>
              <span>Grounded Analysis Data Sources</span>
            </span>
            <svg
              width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
              :class="['transition-transform duration-200', msg.sourcesOpen ? 'rotate-180' : '']"
            >
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>
          <!-- Accordion body -->
          <div
            v-show="msg.sourcesOpen"
            class="border-t border-gray-200 dark:border-gray-800 px-3 py-2"
          >
            <ul class="space-y-1">
              <li
                v-for="(src, si) in msg.sources"
                :key="si"
                class="flex items-start gap-1.5 text-gray-500 dark:text-gray-400"
              >
                <span class="mt-0.5 shrink-0 text-emerald-500">•</span>
                <span>{{ src }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Recommendation Chips & Input -->
    <div class="px-6 py-4 border-t border-gray-100 dark:border-gray-800/50 bg-gray-50/50 dark:bg-gray-950/20 shrink-0">
      <!-- Chips -->
      <div v-if="messages.length === 0" class="flex flex-col gap-2 mb-3">
        <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider px-0.5">Suggestions</span>
        <div class="flex flex-wrap gap-1.5">
          <button 
            v-for="(chip, i) in chips" 
            :key="i"
            class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-full px-3 py-1 hover:border-emerald-500 dark:hover:border-emerald-500 hover:text-emerald-500 dark:hover:text-emerald-500 transition-all duration-200 text-left"
            @click="selectChip(chip)"
          >
            {{ chip }}
          </button>
        </div>
      </div>

      <!-- Input Form -->
      <form @submit.prevent="submitMessage" class="flex gap-2 items-center">
        <input 
          v-model="inputMessage"
          type="text"
          placeholder="Ask about files, WCAG rules, worst complexity..."
          class="flex-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl px-4 py-2.5 text-xs text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:border-emerald-500 dark:focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/20"
          :disabled="isLoading"
        />
        <button 
          type="submit"
          class="p-2.5 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 transition-colors disabled:opacity-50"
          :disabled="isLoading || !inputMessage.trim()"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
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

const scrollToBottom = () => {
  if (messageContainer.value) {
    messageContainer.value.scrollTop = messageContainer.value.scrollHeight
  }
}

watch(messages, () => {
  nextTick(scrollToBottom)
}, { deep: true })

// ── localStorage persistence ──────────────────────────────────────────────────
// One storage slot per audit run so switching runs instantly swaps conversation
const storageKey = computed(() => `audit_chat_history_${props.runId}`)

/**
 * loadChatHistory — rehydrates messages from localStorage for the current run.
 * Strips `isStreaming` flags so stale "thinking" states never resurrect on load.
 * Strips `sourcesOpen` so accordions always start collapsed.
 * Falls back to an empty array if nothing is stored or JSON is corrupt.
 */
const loadChatHistory = () => {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        // Sanitize each rehydrated message before restoring
        messages.value = parsed.map(m => ({
          ...m,
          isStreaming: false,   // Never restore a mid-stream state
          sourcesOpen: false    // Accordions always start closed on reload
        }))
        return
      }
    }
  } catch (e) {
    console.warn('[Chat] localStorage parse error — resetting history for run', props.runId, e)
  }
  // Nothing stored or corrupt — start with a clean slate
  messages.value = []
}

// Immediately load history for the initial runId, then reload whenever it changes
watch(() => props.runId, () => {
  loadChatHistory()
}, { immediate: true })

const selectChip = (chipText) => {
  inputMessage.value = chipText
  submitMessage()
}

/**
 * renderBadges: Splits a message string into text/file-badge segments.
 * Any token ending in .vue, .js, or .ts is returned as { isFile: true, text }.
 * Plain text segments are returned as { isFile: false, text }.
 */
const FILE_TOKEN_RE = /([\w./\-]+\.(?:vue|js|ts))/g
const renderBadges = (content) => {
  if (!content) return [{ isFile: false, text: '' }]
  const parts = []
  let lastIndex = 0
  let match
  // Reset lastIndex for each call
  FILE_TOKEN_RE.lastIndex = 0
  while ((match = FILE_TOKEN_RE.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ isFile: false, text: content.slice(lastIndex, match.index) })
    }
    parts.push({ isFile: true, text: match[1] })
    lastIndex = FILE_TOKEN_RE.lastIndex
  }
  if (lastIndex < content.length) {
    parts.push({ isFile: false, text: content.slice(lastIndex) })
  }
  return parts
}

const submitMessage = async () => {
  const cleanMsg = String(inputMessage.value).trim()
  if (!cleanMsg || isLoading.value) return

  const activeRunId = Number(props.runId || (route && route.query && route.query.run_id) || 0)

  // 1. Push user message
  messages.value.push({
    role: 'user',
    content: cleanMsg,
    isStreaming: false,
    sources: [],
    sourcesOpen: false
  })
  
  inputMessage.value = ''
  isLoading.value = true

  // 2. Push streaming assistant placeholder — includes sources + accordion state
  messages.value.push({
    role: 'assistant',
    content: '',
    isStreaming: true,
    sources: [],
    sourcesOpen: false
  })

  try {
    // Slice off the placeholder assistant message when passing to history payload
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
    let isDone = false  // Outer-loop sentinel so [DONE] breaks the while, not just the for

    while (!isDone) {
      const { done, value } = await reader.read()
      if (done) break

      // Append newly decoded bytes — keep stream:true so multi-byte chars survive chunk splits
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // Retain the last (possibly incomplete) segment for the next iteration
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const cleaned = line.trim()
        // Skip blank lines (SSE uses blank lines as event separators)
        if (!cleaned) continue

        // Only process lines that carry a data payload
        if (!cleaned.startsWith('data:')) continue

        const dataStr = cleaned.slice(5).trim()

        // ── TERMINAL FRAME ─────────────────────────────────────────────────────
        if (dataStr === '[DONE]') {
          isDone = true
          break  // Exit the for-loop; the while condition will prevent re-entry
        }

        // ── STRUCTURED PAYLOAD ────────────────────────────────────────────────
        let parsed
        try {
          parsed = JSON.parse(dataStr)
        } catch (e) {
          // Malformed JSON — log and skip; never touch content
          console.warn('[SSE] Failed to parse frame payload:', dataStr, e)
          continue
        }

        // Guard: parsed must be a plain object, not an array or primitive
        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          console.warn('[SSE] Unexpected non-object frame — discarding:', parsed)
          continue
        }

        // ── BRANCH 1: sources meta-event ─────────────────────────────────────
        // This is the grounding provenance initialization packet that the backend
        // dispatches as the very first SSE frame. It must NEVER reach content.
        if ('sources' in parsed && Array.isArray(parsed.sources)) {
          messages.value[messages.value.length - 1].sources = parsed.sources
          continue  // Explicit early exit — nothing else to do for this frame
        }

        // ── BRANCH 2: token text fragment ────────────────────────────────────
        // Strictly verify token is a non-empty string primitive before appending.
        if ('token' in parsed && typeof parsed.token === 'string' && parsed.token.length > 0) {
          messages.value[messages.value.length - 1].content += parsed.token
          continue
        }

        // ── BRANCH 3: upstream error payload ─────────────────────────────────
        if ('error' in parsed && typeof parsed.error === 'string' && parsed.error.length > 0) {
          messages.value[messages.value.length - 1].content += `\n[Error: ${parsed.error}]`
          continue
        }

        // Any other unknown key structure is silently discarded — not appended
      }
    }
  } catch (err) {
    console.error('Chat error:', err)
    messages.value[messages.value.length - 1].content += `\n[System Error: Could not connect to chatbot API. Ensure backend is running. ${err.message}]`
  } finally {
    messages.value[messages.value.length - 1].isStreaming = false
    isLoading.value = false
    // ── Persist completed exchange to localStorage ────────────────────────────
    // Serialise after isStreaming is cleared so stored snapshots are always clean.
    // Drop sourcesOpen (UI-only toggle state) before writing — it's not meaningful
    // across sessions and inflates the stored payload needlessly.
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
