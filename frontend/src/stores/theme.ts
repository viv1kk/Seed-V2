import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'systems-v1.theme'

function initialTheme(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') {
    return stored
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * Owns the active theme. The only thing it does is set a data attribute
 * on the root element; every colour follows from the token file, so no
 * component needs to know which theme is active (NFR-V2).
 */
export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>(initialTheme())

  function apply(value: Theme): void {
    document.documentElement.dataset.theme = value
    localStorage.setItem(STORAGE_KEY, value)
  }

  function toggle(): void {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  watch(theme, apply, { immediate: true })

  return { theme, toggle }
})
