import { ref } from 'vue'
import { useVsCode } from './useVsCode.js'

export function useIssueActions() {
  const { isVsCode, sendMessage } = useVsCode()
  
  const isGenerating = ref(false)
  const isApplying = ref(false)
  const isUndoing = ref(false)
  const actionError = ref(null)

  const API_BASE = 'http://localhost:5000'

  // Open the editor at specific file line
  function jumpToCode(filePath, lineNumber) {
    sendMessage('jumpToCode', { filePath, lineNumber })
  }

  // POST /api/ai-fix
  async function generateAiProposal(runId, filePath, issueLine, issueType, issueMessage) {
    isGenerating.value = true
    actionError.value = null
    try {
      const res = await fetch(`${API_BASE}/api/ai-fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: runId,
          file_path: filePath,
          issue_line: issueLine,
          issue_type: issueType,
          issue_message: issueMessage
        })
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Server error generating AI proposal.')
      }
      return data
    } catch (err) {
      actionError.value = err.message || 'Connection to backend failed.'
      throw err
    } finally {
      isGenerating.value = false
    }
  }

  // POST /api/ai-fix/apply
  async function commitAiFix(filePath, fixedContent) {
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
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Server error applying fix.')
      }
      return data
    } catch (err) {
      actionError.value = err.message || 'Failed to apply proposed fix.'
      throw err
    } finally {
      isApplying.value = false
    }
  }

  // POST /api/ai-fix/undo
  async function rollbackAiFix(filePath) {
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
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Server error undoing fix.')
      }
      return data
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
    actionError,
    jumpToCode,
    generateAiProposal,
    commitAiFix,
    rollbackAiFix
  }
}
