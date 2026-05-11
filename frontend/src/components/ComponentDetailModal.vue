<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps({
  filePath: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close'])

const loading = ref(true)
const details = ref(null)

onMounted(async () => {
  try {
    const res = await fetch(`http://127.0.0.1:5000/api/file/${encodeURIComponent(props.filePath)}`)
    if (!res.ok) throw new Error('Network response was not ok')
    details.value = await res.json()
  } catch (error) {
    console.error("Failed to load details:", error)
  } finally {
    loading.value = false
  }

  // Handle escape key to close
  const handleKeydown = (e) => {
    if (e.key === 'Escape') emit('close')
  }
  window.addEventListener('keydown', handleKeydown)
  onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
})

// HTMLEncode utility
function escapeHtml(unsafe) {
  if (!unsafe) return ''
  return unsafe
       .replace(/&/g, "&amp;")
       .replace(/</g, "&lt;")
       .replace(/>/g, "&gt;")
       .replace(/"/g, "&quot;")
       .replace(/'/g, "&#039;");
}

function renderSnippet(snippet, targetLine) {
  if (!snippet) return '';
  const lines = snippet.split('\n');
  const targetRe = new RegExp(`^\\s*${targetLine}\\s+\\|`, 'i');

  return lines.map(line => {
    // Escape unsafe HTML
    let safeLine = escapeHtml(line);
    
    // Check if this line is the target line (e.g. starts with "42 |")
    // or if we fallback to the middle line if exact matching fails
    if (targetLine && targetRe.test(line)) {
      return `<span class="bg-red-500/20 text-red-300 block -mx-2 px-2 rounded border-l-2 border-red-400">${safeLine}</span>`;
    }
    // Alternatively, if lines don't have number prefixes, just highlight the 3rd line (middle of 5)
    // For safety, we will just use the literal checking if it starts with number matching the DB or just length checking.
    // Spec: "Highlight the middle line (or the line that matches the issue’s line number if line numbers are embedded)"
    return safeLine;
  }).map((lineStr, idx) => {
      // Fallback: If no lines matched the targetRe but we have 5 lines, highlight the middle (idx 2)
      if (targetLine && !lines.some(l => targetRe.test(l)) && lines.length >= 3) {
          const middle = Math.floor(lines.length / 2);
          if (idx === middle) {
              return `<span class="bg-red-500/20 text-red-300 block -mx-2 px-2 rounded border-l-2 border-red-400">${lineStr}</span>`;
          }
      }
      return lineStr;
  }).join('\n');
}

</script>

<template>
  <Teleport to="body">
    <!-- Overlay -->
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm sm:p-6" @click.self="emit('close')">
      <!-- Modal Box -->
      <div class="bg-gray-900 border border-gray-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-900 sticky top-0 shrink-0">
          <h2 class="text-lg font-semibold text-white truncate pr-4 font-mono">{{ filePath }}</h2>
          <button @click="emit('close')" aria-label="Close modal" class="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition shadow-none cursor-pointer flex-shrink-0">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>

        <!-- Body -->
        <div class="px-6 py-6 overflow-y-auto flex-1 text-gray-100">
          
          <!-- Loading -->
          <div v-if="loading" class="flex justify-center items-center py-20">
            <svg class="animate-spin h-8 w-8 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>

          <div v-else-if="details" class="space-y-8 tracking-wide">
            
            <!-- Scout Metrics -->
            <section>
              <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">SCOUT METRICS</h3>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div v-for="(val, key) in details.metrics" :key="key" 
                     v-show="key !== 'id' && key !== 'file_path' && key !== 'project_name' && key !== 'file_hash' && key !== 'last_modified'"
                     class="bg-gray-800/20 border border-gray-800 rounded-lg p-3">
                  <div class="text-xs font-medium text-gray-500 mb-1 capitalize">{{ String(key).replace(/_/g, ' ') }}</div>
                  <div class="text-xl font-mono text-white">{{ val }}</div>
                </div>
              </div>
            </section>

            <!-- ESLint Flags -->
            <section v-if="details.flags && details.flags.length > 0">
              <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">ESLINT FLAGS</h3>
              <div class="space-y-2">
                <div v-for="flag in details.flags" :key="flag.id" class="flex items-center bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                  <span 
                    class="px-2 py-0.5 rounded text-xs font-mono mr-3"
                    :class="flag.severity === 2 || flag.severity === 'error' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'"
                  >
                    {{ flag.severity === 2 || flag.severity === 'error' ? 'error' : 'warn' }}
                  </span>
                  <span class="text-sm text-gray-300">{{ flag.message }} <span class="text-gray-500">({{ flag.rule_id }})</span></span>
                  <span class="text-xs font-mono text-gray-500 ml-auto pl-4">L{{ flag.line }}</span>
                </div>
              </div>
            </section>

            <!-- AI Architectural Issues -->
            <section v-if="details.issues && details.issues.length > 0">
              <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">ARCHITECTURAL FINDINGS</h3>
              <div class="space-y-6">
                <div v-for="issue in details.issues" :key="issue.id" class="bg-gray-800/50 rounded-xl border border-gray-700 p-5">
                  <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center space-x-3">
                      <span 
                        class="px-2 py-0.5 rounded text-xs font-mono"
                        :class="[
                          issue.severity === 'High' ? 'bg-red-500/20 text-red-400' : '',
                          issue.severity === 'Medium' ? 'bg-amber-500/20 text-amber-400' : '',
                          issue.severity === 'Low' ? 'bg-emerald-500/20 text-emerald-400' : ''
                        ]"
                      >
                        {{ issue.severity }}
                      </span>
                      <span class="font-medium text-white">{{ issue.issue_category }}</span>
                    </div>
                    <span v-if="issue.line_number" class="text-xs text-gray-500 font-mono">L{{ issue.line_number }}</span>
                  </div>

                  <p class="text-sm text-gray-300 mb-4 leading-relaxed">{{ issue.description }}</p>

                  <!-- Snippet -->
                  <div v-if="issue.code_snippet" class="bg-gray-950 rounded-lg border border-gray-700 overflow-hidden mb-4">
                    <div class="bg-gray-900 border-b border-gray-700 px-4 py-2 flex justify-between items-center">
                      <span class="text-xs text-gray-400 font-medium">Code snippet</span>
                      <span class="text-xs text-gray-600">~ L{{ issue.line_number }}</span>
                    </div>
                    <pre class="p-4 text-sm leading-relaxed text-gray-200 font-mono overflow-x-auto"><code v-html="renderSnippet(issue.code_snippet, issue.line_number)"></code></pre>
                  </div>

                  <!-- Recommendation -->
                  <div v-if="issue.recommendation" class="mt-3 text-sm text-indigo-400 flex items-start bg-indigo-500/10 p-3 rounded-lg border border-indigo-500/20">
                    <svg class="w-5 h-5 mr-2 shrink-0 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                    <span class="leading-relaxed">{{ issue.recommendation }}</span>
                  </div>

                </div>
              </div>
            </section>
            
            <div v-if="(!details.flags || details.flags.length === 0) && (!details.issues || details.issues.length === 0)" class="py-10 text-center text-gray-400 text-sm border border-gray-800 rounded-xl bg-gray-800/20">
              No issues or flags found for this component.
            </div>

          </div>
        </div>

      </div>
    </div>
  </Teleport>
</template>