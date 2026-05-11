<script setup>
defineProps({
  offenders: {
    type: Array,
    required: true
  }
})
const emit = defineEmits(['drilldown'])
</script>

<template>
  <div class="space-y-4 text-gray-100">
    <!-- Header -->
    <div class="flex items-end justify-between mb-6">
      <h2 class="text-2xl font-bold tracking-tight text-white">Worst Offenders</h2>
      <p class="text-sm font-medium text-gray-400">Top {{ offenders.length || 10 }} most problematic components</p>
    </div>

    <!-- Table -->
    <div class="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      <div v-if="!offenders || offenders.length === 0" class="p-8 text-center text-gray-400">
        No offenders detected.
      </div>
      <table v-else class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-gray-800/40 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-800/50">
            <th class="py-4 px-6 text-center w-16">Rank</th>
            <th class="py-4 px-6">Component</th>
            <th class="py-4 px-4 text-center">High</th>
            <th class="py-4 px-4 text-center">Medium</th>
            <th class="py-4 px-4 text-center">Low</th>
            <th class="py-4 px-6 text-right">Score</th>
          </tr>
        </thead>
        <tbody class="text-sm">
          <tr 
            v-for="(item, index) in offenders" 
            :key="item.file_path"
            @click="emit('drilldown', item.file_path)"
            class="border-b border-gray-800/50 hover:bg-gray-800/40 cursor-pointer transition-colors"
          >
            <!-- Rank -->
            <td class="py-4 px-6 text-center text-gray-400">{{ index + 1 }}</td>
            
            <!-- Component -->
            <td class="py-4 px-6">
              <div class="font-mono text-gray-200 truncate max-w-sm" :title="item.file_path.split('/').pop()">
                {{ item.file_path.split('/').pop() }}
              </div>
              <div class="font-mono text-xs text-gray-600 truncate max-w-sm mt-0.5" :title="item.file_path">
                {{ item.file_path }}
              </div>
            </td>
            
            <!-- High -->
            <td class="py-4 px-4 text-center">
              <span v-if="item.high_count > 0" class="text-red-400 font-bold">{{ item.high_count }}</span>
              <span v-else class="text-gray-600 font-medium">0</span>
            </td>
            
            <!-- Medium -->
            <td class="py-4 px-4 text-center">
              <span v-if="item.medium_count > 0" class="text-amber-400 font-bold">{{ item.medium_count }}</span>
              <span v-else class="text-gray-600 font-medium">0</span>
            </td>

            <!-- Low -->
            <td class="py-4 px-4 text-center">
              <span v-if="item.low_count > 0" class="text-emerald-400 font-bold">{{ item.low_count }}</span>
              <span v-else class="text-gray-600 font-medium">0</span>
            </td>

            <!-- Score -->
            <td class="py-4 px-6 text-right font-mono text-gray-200 font-medium">
              {{ item.score }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>