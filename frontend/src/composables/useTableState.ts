import { computed, ref } from 'vue'

export function useTableState<T>(rows: T[]) {
  const query = ref('')

  const filteredRows = computed(() => {
    if (!query.value.trim()) {
      return rows
    }

    const normalized = query.value.toLowerCase()
    return rows.filter((row) => JSON.stringify(row).toLowerCase().includes(normalized))
  })

  return {
    query,
    filteredRows,
  }
}
