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
            'px-4 py-3 rounded-2xl text-[13px] leading-relaxed shadow-sm font-normal break-words',
            msg.role === 'user' 
              ? 'bg-emerald-600 text-white rounded-tr-none' 
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-none border border-gray-200/20'
          ]"
        >
          <!-- Handle streaming markdown-like response simply -->
          <div class="whitespace-pre-wrap font-sans">{{ msg.content }}</div>
          <div v-if="msg.isStreaming && !msg.content" class="flex items-center gap-1 py-1">
            <span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
            <span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
            <span class="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
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
import { ref, watch, nextTick } from 'vue'
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

defineEmits(['close'])

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

watch(() => props.runId, () => {
  messages.value = []
})

const selectChip = (chipText) => {
  inputMessage.value = chipText
  submitMessage()
}

const submitMessage = async () => {
  const cleanMsg = String(inputMessage.value).trim()
  if (!cleanMsg || isLoading.value) return

  const activeRunId = Number(props.runId || (route && route.query && route.query.run_id) || 0)

  // 1. Push user message
  messages.value.push({
    role: 'user',
    content: cleanMsg,
    isStreaming: false
  })
  
  inputMessage.value = ''
  isLoading.value = true

  // 2. Push streaming assistant placeholder
  messages.value.push({
    role: 'assistant',
    content: '',
    isStreaming: true
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

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // Keep the last incomplete part in the buffer

      for (const line of lines) {
        const cleaned = line.trim()
        if (!cleaned) continue
        if (cleaned.startsWith('data:')) {
          const dataStr = cleaned.slice(5).trim()
          if (dataStr === '[DONE]') {
            break
          }
          try {
            const dataJson = JSON.parse(dataStr)
            if (dataJson.token) {
              messages.value[messages.value.length - 1].content += dataJson.token
            } else if (dataJson.error) {
              messages.value[messages.value.length - 1].content += `\n[Error: ${dataJson.error}]`
            }
          } catch (e) {
            console.error('Failed to parse SSE token:', e)
          }
        }
      }
    }
  } catch (err) {
    console.error('Chat error:', err)
    messages.value[messages.value.length - 1].content += `\n[System Error: Could not connect to chatbot API. Ensure backend is running. ${err.message}]`
  } finally {
    messages.value[messages.value.length - 1].isStreaming = false
    isLoading.value = false
  }
}
</script>
