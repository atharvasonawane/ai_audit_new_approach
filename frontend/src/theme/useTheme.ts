import { computed, ref } from 'vue'

import { applyTheme, getStoredTheme, type ThemeMode } from './theme'

export function useTheme() {
  const mode = ref<ThemeMode>(getStoredTheme() ?? 'dark')

  const isDark = computed(() => mode.value === 'dark')

  const setMode = (next: ThemeMode) => {
    mode.value = next
    applyTheme(next)
  }

  const toggle = () => setMode(mode.value === 'dark' ? 'light' : 'dark')

  return { mode, isDark, setMode, toggle }
}

