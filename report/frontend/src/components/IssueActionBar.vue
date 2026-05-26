<script setup>
import { useIssueActions } from '../composables/useIssueActions.js'

const props = defineProps({
  filePath: { type: String, required: true },
  lineNumber: { type: Number, default: null },
  issue: { type: Object, required: true },
  isLoadingProposal: { type: Boolean, default: false },
  isDisabled: { type: Boolean, default: false }
})

const emit = defineEmits(['trigger-ai-proposal'])

const { isVsCode, jumpToCode } = useIssueActions()

const triggerFix = () => {
  if (props.isLoadingProposal || props.isDisabled) return
  emit('trigger-ai-proposal', props.issue)
}
</script>

<template>
  <div class="flex items-center gap-2 mt-3 select-none">
    <!-- Open in Editor (Only rendered if lineNumber is valid) -->
    <button
      v-if="lineNumber"
      @click.stop="jumpToCode(filePath, lineNumber)"
      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold font-mono rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors duration-150 select-none cursor-pointer"
      title="Jump to the exact line in your editor"
    >
      <svg class="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
      </svg>
      Open in Editor
    </button>

    <!-- AI Fix Button -->
    <button
      @click.stop="triggerFix"
      :disabled="isLoadingProposal || isDisabled"
      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold font-mono rounded-lg border text-indigo-600 border-indigo-200 bg-indigo-50/50 hover:bg-indigo-50 dark:text-indigo-300 dark:border-indigo-500/20 dark:bg-indigo-500/10 dark:hover:bg-indigo-500/20 transition-all duration-150 select-none cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
      :title="isLoadingProposal ? 'Fix request in progress...' : isDisabled ? 'Another AI fix action is already running...' : 'Ask AI to generate architectural fix proposal'"
    >
      <!-- Loading spinner -->
      <svg v-if="isLoadingProposal" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
      </svg>
      <!-- Sparkling AI Icon -->
      <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
      </svg>
      {{ isLoadingProposal ? 'Analyzing...' : 'AI Fix' }}
    </button>
  </div>
</template>
