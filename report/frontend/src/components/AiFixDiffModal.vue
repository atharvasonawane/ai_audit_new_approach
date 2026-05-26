<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 dark:bg-black/75 backdrop-blur-sm transition-opacity duration-300">
    <div class="relative w-full max-w-6xl h-[85vh] flex flex-col bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-2xl overflow-hidden transition-all transform duration-300 scale-100">
      
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 shrink-0">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-indigo-500/10 text-indigo-500 rounded-lg">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
            </svg>
          </div>
          <div>
            <h3 class="text-[15px] font-bold text-gray-900 dark:text-gray-50 font-mono leading-none">
              AI Architectural Fix Proposal
            </h3>
            <p class="text-[11px] text-gray-500 dark:text-gray-400 mt-1 font-mono leading-none">
              Target: {{ issue.file_path || issue.filePath || 'Active File' }} (Line {{ issue.line_number || issue.lineNumber || 'N/A' }})
            </p>
          </div>
        </div>
        <button @click="$emit('close')" :disabled="isLoading || isApplying || isGenerating" class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Warning/Notes Banner -->
      <div v-if="warnings.length > 0" class="flex flex-col gap-1 px-6 py-2.5 bg-amber-500/10 border-b border-amber-500/20 text-amber-700 dark:text-amber-400 shrink-0 text-[12px] font-medium leading-relaxed">
        <div class="flex items-center gap-1.5 font-bold">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          {{ warnings.length }} Warning{{ warnings.length > 1 ? 's' : '' }} Detected:
        </div>
        <ul class="list-disc pl-5 mt-1 font-mono text-[11px] space-y-0.5">
          <li v-for="(warn, idx) in warnings" :key="idx">{{ warn }}</li>
        </ul>
      </div>

      <!-- Main Content / Diff Aligner -->
      <div class="flex-1 min-h-0 overflow-y-auto bg-gray-50/30 dark:bg-gray-950/20">
        
        <!-- Loading State -->
        <div v-if="isLoading" class="h-full flex flex-col items-center justify-center gap-4 py-16 px-10 text-center text-gray-500 dark:text-gray-400">
          <div class="w-10 h-10 border-[3.5px] border-indigo-100 dark:border-indigo-950 border-t-indigo-500 rounded-full animate-spin"></div>
          <div class="text-[13px] font-medium mt-1">Analyzing issue and generating architectural fix proposal...</div>
          <p class="text-[11px] text-gray-400 max-w-[280px]">Our expert pipeline is parsing active tree-sitter tags to compute minimal changes.</p>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="h-full flex flex-col items-center justify-center gap-4 py-16 px-10 text-center text-gray-500 dark:text-gray-400">
          <div class="p-3 bg-red-100 dark:bg-red-500/10 text-red-500 rounded-2xl">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <div class="text-[14px] font-bold text-gray-800 dark:text-gray-200">Proposal Generation Failed</div>
          <p class="text-[12px] text-red-600 dark:text-red-400 max-w-[400px] leading-relaxed">{{ error }}</p>
          <button @click="$emit('close')" class="px-4 py-2 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl text-[12px] font-semibold transition cursor-pointer">
            Close Modal
          </button>
        </div>

        <!-- Diff Split Pane -->
        <div v-else class="h-full flex flex-col">
          <div class="grid grid-cols-2 bg-gray-100 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 text-[11px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider shrink-0 select-none">
            <div class="px-6 py-2 border-r border-gray-200 dark:border-gray-800 flex items-center gap-2">
              Original Source Code
              <span v-if="windowStart" class="normal-case font-normal text-indigo-500 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40 rounded px-1.5 py-0.5">Lines {{ windowStart }}–{{ windowEnd }}</span>
            </div>
            <div class="px-6 py-2 flex items-center gap-2">
              Proposed AI Fix
              <span v-if="windowStart" class="normal-case font-normal text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 rounded px-1.5 py-0.5">Focus Window</span>
            </div>
          </div>
          
          <div class="flex-1 min-h-0 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-900/40">
            <div v-for="(row, idx) in diffData.left" :key="idx" class="grid grid-cols-2 divide-x divide-gray-200 dark:divide-gray-800 text-[12px] font-mono hover:bg-gray-50/40 dark:hover:bg-gray-900/10">
              <!-- Left Side (Original) -->
              <div :class="getRowClass(diffData.left[idx].type)" class="flex py-0.5 px-4 overflow-x-auto min-w-0">
                <span class="w-8 shrink-0 text-[10px] text-gray-400 dark:text-gray-600 text-right pr-3 select-none leading-relaxed">{{ diffData.left[idx].lineNum }}</span>
                <pre class="flex-1 whitespace-pre-wrap break-all leading-relaxed">{{ diffData.left[idx].text || ' ' }}</pre>
              </div>
              <!-- Right Side (Fix) -->
              <div :class="getRowClass(diffData.right[idx].type)" class="flex py-0.5 px-4 overflow-x-auto min-w-0">
                <span class="w-8 shrink-0 text-[10px] text-gray-400 dark:text-gray-600 text-right pr-3 select-none leading-relaxed">{{ diffData.right[idx].lineNum }}</span>
                <pre class="flex-1 whitespace-pre-wrap break-all leading-relaxed">{{ diffData.right[idx].text || ' ' }}</pre>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 shrink-0 select-none">
        <div class="text-[12px] text-gray-500 dark:text-gray-400 font-mono">
          <span v-if="!isLoading && !error && validationNote" class="inline-flex items-center gap-1.5 py-1 px-2.5 rounded-md bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
            <svg class="w-3.5 h-3.5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"/>
            </svg>
            {{ validationNote }}
          </span>
        </div>
        <div class="flex gap-3">
          <button 
            @click="$emit('close')" 
            :disabled="isLoading || isApplying || isGenerating"
            class="px-4 py-2 border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl text-[12px] font-semibold transition cursor-pointer disabled:opacity-50"
          >
            Reject Fix
          </button>
          <button 
            v-if="!isLoading && !error"
            @click="applyFix" 
            :disabled="isLoading || isApplying || isGenerating"
            class="inline-flex items-center gap-2 px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-[12px] font-semibold transition shadow-md hover:shadow-indigo-500/10 cursor-pointer disabled:opacity-50"
          >
            <div v-if="isApplying" class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            {{ isApplying ? 'Applying Architectural Fix...' : 'Apply Architectural Fix' }}
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useIssueActions } from '../composables/useIssueActions.js'

const props = defineProps({
  isOpen: { type: Boolean, required: true },
  originalText: { type: String, default: '' },
  fixedText: { type: String, default: '' },
  issue: { type: Object, required: true },
  runId: { type: Number, required: true },
  filePath: { type: String, required: true }
})

const emit = defineEmits(['close', 'applied'])
const { generateAiProposal, commitAiFix, isGenerating, isApplying } = useIssueActions()

const isLoading = ref(false)
const error = ref(null)

const warnings = ref([])
const validationNote = ref('')
const activeOriginalText = ref('')
const activeFixedText = ref('')
const fullOriginalText = ref('')
const fullFixedText = ref('')
const activeResolvedFilePath = ref('')
const windowStart = ref(null)
const windowEnd = ref(null)

const diffData = computed(() => {
  const oldLines = activeOriginalText.value.split(/\r?\n/)
  const newLines = activeFixedText.value.split(/\r?\n/)

  const dp = Array(oldLines.length + 1).fill(null).map(() => Array(newLines.length + 1).fill(0))
  for (let i = 1; i <= oldLines.length; i++) {
    for (let j = 1; j <= newLines.length; j++) {
      if (oldLines[i - 1] === newLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }

  const left = []
  const right = []
  let i = oldLines.length
  let j = newLines.length

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
      left.unshift({ type: 'normal', lineNum: i + (windowStart.value ? windowStart.value - 1 : 0), text: oldLines[i - 1] })
      right.unshift({ type: 'normal', lineNum: j + (windowStart.value ? windowStart.value - 1 : 0), text: newLines[j - 1] })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      left.unshift({ type: 'empty', lineNum: '', text: '' })
      right.unshift({ type: 'added', lineNum: j + (windowStart.value ? windowStart.value - 1 : 0), text: newLines[j - 1] })
      j--
    } else {
      left.unshift({ type: 'removed', lineNum: i + (windowStart.value ? windowStart.value - 1 : 0), text: oldLines[i - 1] })
      right.unshift({ type: 'empty', lineNum: '', text: '' })
      i--
    }
  }

  return { left, right }
})

const getRowClass = (type) => {
  if (type === 'removed') return 'bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border-l-[3px] border-red-500'
  if (type === 'added') return 'bg-emerald-50 dark:bg-emerald-950/45 text-emerald-700 dark:text-emerald-300 border-l-[3px] border-emerald-500'
  if (type === 'empty') return 'bg-gray-100/30 dark:bg-gray-900/10 text-transparent select-none opacity-40'
  return 'text-gray-800 dark:text-gray-200'
}

const loadProposal = async () => {
  if (!props.isOpen || !props.issue || isLoading.value || isGenerating.value) return

  isLoading.value = true
  error.value = null
  warnings.value = []
  validationNote.value = ''
  windowStart.value = null
  windowEnd.value = null
  activeOriginalText.value = props.originalText || ''
  activeFixedText.value = props.fixedText || ''
  fullOriginalText.value = ''
  fullFixedText.value = ''
  activeResolvedFilePath.value = ''

  if (activeOriginalText.value && activeFixedText.value) {
    isLoading.value = false
    return
  }

  try {
    const data = await generateAiProposal(
      props.runId,
      props.filePath,
      props.issue.line_number || props.issue.lineNumber || 1,
      props.issue.issue_title || props.issue.title || 'Quality Issue',
      props.issue.description || props.issue.message,
      props.issue.code_snippet || '',
      props.issue.recommendation || ''
    )

    console.log('[AiFixDiffModal] Backend response:', {
      has_original: !!data.original_text,
      has_fixed: !!data.fixed_text,
      original_len: (data.original_text || '').length,
      fixed_len: (data.fixed_text || '').length,
      identical: data.original_text === data.fixed_text,
      window_start: data.window_start,
      window_end: data.window_end,
      syntax_valid: data.syntax_valid,
      validation_note: data.validation_note
    })

    activeOriginalText.value = data.original_text || ''
    activeFixedText.value = data.fixed_text || ''
    fullOriginalText.value = data.full_original_text || data.original_text || ''
    fullFixedText.value = data.full_fixed_content || data.full_fixed_text || data.fixed_text || ''
    activeResolvedFilePath.value = data.resolved_file_path || data.file_path || props.filePath
    windowStart.value = data.window_start || null
    windowEnd.value = data.window_end || null
    warnings.value = data.warnings || []
    validationNote.value = data.validation_note || 'Syntax check complete'

    // Detect if the AI returned identical code (no actual fix)
    if (activeOriginalText.value.trim() === activeFixedText.value.trim()) {
      warnings.value.push('The AI returned code identical to the original. The model may not have understood the fix required. Try re-triggering.')
    }
  } catch (err) {
    error.value = err.message || 'Could not connect to live Flask backend.'
  } finally {
    isLoading.value = false
  }
}

const applyFix = async () => {
  if (!activeFixedText.value || isLoading.value || isApplying.value) return

  error.value = null

  try {
    const targetFilePath = activeResolvedFilePath.value || props.filePath
    const data = await commitAiFix(targetFilePath, fullFixedText.value || activeFixedText.value)
    emit('applied', { backupPath: data.backup_path, filePath: targetFilePath })
  } catch (err) {
    error.value = err.message || 'Connection failure when applying proposed changes.'
  }
}

watch(
  () => [props.isOpen, props.issue],
  () => {
    if (props.isOpen) {
      loadProposal()
    }
  },
  { immediate: true }
)
</script>

<style scoped>
pre {
  margin: 0;
  padding: 0;
  font-family: inherit;
}
</style>
