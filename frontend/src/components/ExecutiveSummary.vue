<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true
  }
})

const healthScore = computed(() => {
  // We'll dynamically determine score based on issues (mock calculation)
  // But wait, the spec says "health score". It doesn't tell us how to calculate it from the API!
  // Ah, health score threshold: >= 70, 40-69, <40
  // "The number is text-6xl font-bold, dynamically coloured based on threshold"
  // If the API doesn't return a health score directly, how to calculate? Let's assume 100 - (High*2 + Medium + Low*0.5).
  // Or maybe it's in the API summary? Let me check api_server.py
  // the summary endpoint returns: status, synthesis_text, issues: {High, Medium, Low}. No score.
  // We'll calculate: max(0, Math.round(100 - (props.summary.issues.High * 3) - (props.summary.issues.Medium * 2) - (props.summary.issues.Low * 1)))
  // Actually, wait, let's just make it a simple calculation to get a number between 0 and 100. Let's do: 100 - (high*3 + med*2 + low). If < 0, 0.
  const issues = props.summary?.issues || { High: 0, Medium: 0, Low: 0 };
  const deduction = (issues.High * 3) + (issues.Medium * 2) + (issues.Low * 1);
  return Math.max(0, 100 - deduction);
})

const healthColor = computed(() => {
  if (healthScore.value >= 70) return 'text-emerald-400'
  if (healthScore.value >= 40) return 'text-amber-400'
  return 'text-red-400'
})
</script>

<template>
  <div class="space-y-12">
    <!-- Stat Cards Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Total -->
      <div class="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">TOTAL ISSUES</h3>
        <p class="text-3xl font-bold text-white">
          {{ (summary.issues.High || 0) + (summary.issues.Medium || 0) + (summary.issues.Low || 0) }}
        </p>
      </div>
      <!-- High -->
      <div class="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">HIGH SEVERITY</h3>
        <p class="text-3xl font-bold text-red-400">{{ summary.issues.High || 0 }}</p>
      </div>
      <!-- Medium -->
      <div class="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">MEDIUM</h3>
        <p class="text-3xl font-bold text-amber-400">{{ summary.issues.Medium || 0 }}</p>
      </div>
      <!-- Low -->
      <div class="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">LOW</h3>
        <p class="text-3xl font-bold text-emerald-400">{{ summary.issues.Low || 0 }}</p>
      </div>
    </div>

    <!-- Health Score & Synthesis -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Health Score -->
      <div class="bg-gray-900 rounded-2xl border border-gray-800 p-6 flex flex-col justify-center items-center text-center">
        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">HEALTH SCORE</h3>
        <div class="flex items-baseline">
          <span class="text-6xl font-bold tracking-tight" :class="healthColor">{{ healthScore }}</span>
          <span class="text-xl text-gray-500 font-bold ml-1">/100</span>
        </div>
      </div>

      <!-- Synthesis -->
      <div class="col-span-1 lg:col-span-2 bg-gray-900 rounded-2xl border border-gray-800 p-6">
        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">EXECUTIVE SYNTHESIS</h3>
        <div class="max-h-60 overflow-y-auto pr-2">
          <pre class="text-sm font-mono text-gray-300 leading-relaxed whitespace-pre-wrap font-sans">{{ summary.synthesis_text || 'No synthesis available.' }}</pre>
        </div>
      </div>

    </div>
  </div>
</template>