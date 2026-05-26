import { computed, ref } from 'vue'
import { useVsCode } from './useVsCode.js'

const API_BASE = window.__FLASK_PORT__ ? `http://localhost:${window.__FLASK_PORT__}` : 'http://localhost:5000'

const isGenerating = ref(false)
const isApplying = ref(false)
const isUndoing = ref(false)
const actionError = ref(null)
const activeProposalKey = ref('')

function buildProposalKey(runId, filePath, issueLine, issueType, issueMessage) {
  return [runId || 0, filePath || '', issueLine || 0, issueType || '', issueMessage || ''].join('::')
}

async function parseJsonResponse(response, fallbackMessage) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.error || fallbackMessage)
  }
  return data
}

export function useIssueActions() {
  const { isVsCode, sendMessage } = useVsCode()

  const isBusy = computed(() => isGenerating.value || isApplying.value || isUndoing.value)

  function jumpToCode(filePath, lineNumber) {
    sendMessage('jumpToCode', { filePath, lineNumber })
  }

  async function generateAiProposal(runId, filePath, issueLine, issueType, issueMessage, codeSnippet, recommendation) {
    if (isGenerating.value) {
      throw new Error('An AI fix proposal is already in progress.')
    }

    isGenerating.value = true
    actionError.value = null
    activeProposalKey.value = buildProposalKey(runId, filePath, issueLine, issueType, issueMessage)

    try {
      const res = await fetch(`${API_BASE}/api/ai-fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: runId,
          file_path: filePath,
          issue_line: issueLine,
          issue_type: issueType,
          issue_message: issueMessage,
          code_snippet: codeSnippet || '',
          recommendation: recommendation || ''
        })
      })

      return await parseJsonResponse(res, 'Server error generating AI proposal.')
    } catch (err) {
      actionError.value = err.message || 'Connection to backend failed.'
      throw err
    } finally {
      isGenerating.value = false
      activeProposalKey.value = ''
    }
  }

  async function commitAiFix(filePath, fixedContent) {
    if (isApplying.value) {
      throw new Error('An AI fix is already being applied.')
    }

    isApplying.value = true
    actionError.value = null

    try {
      const res = await fetch(`${API_BASE}/api/ai-fix/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: filePath,
          fixed_content: fixedContent
        })
      })

      return await parseJsonResponse(res, 'Server error applying fix.')
    } catch (err) {
      actionError.value = err.message || 'Failed to apply proposed fix.'
      throw err
    } finally {
      isApplying.value = false
    }
  }

  async function rollbackAiFix(filePath) {
    if (isUndoing.value) {
      throw new Error('A rollback is already in progress.')
    }

    isUndoing.value = true
    actionError.value = null

    try {
      const res = await fetch(`${API_BASE}/api/ai-fix/undo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: filePath
        })
      })

      return await parseJsonResponse(res, 'Server error undoing fix.')
    } catch (err) {
      actionError.value = err.message || 'Failed to rollback fix.'
      throw err
    } finally {
      isUndoing.value = false
    }
  }

  return {
    isVsCode,
    isGenerating,
    isApplying,
    isUndoing,
    isBusy,
    actionError,
    activeProposalKey,
    buildProposalKey,
    jumpToCode,
    generateAiProposal,
    commitAiFix,
    rollbackAiFix
  }
}
