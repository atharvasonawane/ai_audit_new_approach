export type ThemeMode = 'dark' | 'light'

const STORAGE_KEY = 'cal.theme'

export function getStoredTheme(): ThemeMode | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === 'dark' || raw === 'light') return raw
  return null
}

export function applyTheme(mode: ThemeMode) {
  const root = document.documentElement
  root.classList.toggle('dark', mode === 'dark')
  localStorage.setItem(STORAGE_KEY, mode)
}

export function initTheme() {
  // Dark-first: default to dark unless user explicitly chose otherwise.
  const stored = getStoredTheme()
  applyTheme(stored ?? 'dark')
}

