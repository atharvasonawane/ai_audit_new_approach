<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
    files: {
        type: Array,
        required: true
    }
})

const emit = defineEmits(['drilldown'])

const searchQuery = ref('')

const filteredFiles = computed(() => {
    if (!searchQuery.value) return props.files
    const lowerQuery = searchQuery.value.toLowerCase()
    return props.files.filter(file =>
        file.file_path.toLowerCase().includes(lowerQuery)
    )
})
</script>

<template>
    <div class="space-y-4 text-gray-100">
        <!-- Header with Search -->
        <div class="flex flex-col sm:flex-row items-start sm:items-end justify-between mb-6 gap-4">
            <div>
                <h2 class="text-2xl font-bold tracking-tight text-white">All Scanned Files</h2>
                <p class="text-sm font-medium text-gray-400 mt-1">Browse and search every analyzed component</p>
            </div>
            <div class="relative w-full sm:w-72">
                <input v-model="searchQuery" type="text" placeholder="Search file path..."
                    class="w-full bg-gray-900 border border-gray-700/80 rounded-lg pl-10 pr-4 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors" />
                <!-- Optional search icon -->
                <svg class="w-4 h-4 text-gray-500 absolute left-3 top-2.5" fill="none" stroke="currentColor"
                    viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                </svg>
            </div>
        </div>

        <!-- Table Container overflow wrapper -->
        <div class="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div class="max-h-96 overflow-y-auto w-full relative">
                <table class="w-full text-left border-collapse">
                    <thead class="sticky top-0 z-10">
                        <tr
                            class="bg-gray-800/90 backdrop-blur-sm text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-700 shadow-sm">
                            <th class="py-4 px-6">File Path</th>
                            <th class="py-4 px-4 text-center">Script Lines</th>
                            <th class="py-4 px-4 text-center">Complexity</th>
                            <th class="py-4 px-4 text-center">High</th>
                            <th class="py-4 px-4 text-center">Medium</th>
                            <th class="py-4 px-4 text-center">Low</th>
                        </tr>
                    </thead>
                    <tbody class="text-sm">
                        <tr v-if="filteredFiles.length === 0">
                            <td colspan="6" class="py-10 text-center text-gray-500 bg-gray-900">
                                No files match your search.
                            </td>
                        </tr>
                        <tr v-else v-for="item in filteredFiles" :key="item.id || item.file_path"
                            @click="emit('drilldown', item.file_path)"
                            class="border-b border-gray-800/50 hover:bg-gray-800/40 cursor-pointer transition-colors bg-gray-900">
                            <!-- Path -->
                            <td class="py-3 px-6">
                                <div class="font-mono text-gray-200 truncate max-w-sm lg:max-w-md"
                                    :title="item.file_path">
                                    {{ item.file_path }}
                                </div>
                            </td>

                            <!-- Lines -->
                            <td class="py-3 px-4 text-center font-mono text-gray-400">
                                {{ item.script_lines ?? 0 }}
                            </td>

                            <!-- Complexity -->
                            <td class="py-3 px-4 text-center font-mono text-gray-400">
                                {{ item.cyclomatic_complexity ?? 0 }}
                            </td>

                            <!-- High -->
                            <td class="py-3 px-4 text-center">
                                <span v-if="item.high_issues > 0"
                                    class="text-red-400 font-bold px-2 py-0.5 rounded bg-red-400/10">{{ item.high_issues
                                    }}</span>
                                <span v-else class="text-gray-600 font-medium">0</span>
                            </td>

                            <!-- Medium -->
                            <td class="py-3 px-4 text-center">
                                <span v-if="item.medium_issues > 0"
                                    class="text-amber-400 font-bold px-2 py-0.5 rounded bg-amber-400/10">{{
                                    item.medium_issues }}</span>
                                <span v-else class="text-gray-600 font-medium">0</span>
                            </td>

                            <!-- Low -->
                            <td class="py-3 px-4 text-center">
                                <span v-if="item.low_issues > 0"
                                    class="text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-400/10">{{
                                    item.low_issues }}</span>
                                <span v-else class="text-gray-600 font-medium">0</span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>