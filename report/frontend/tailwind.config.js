/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Neutrals (Foundation)
        'bg-primary': 'var(--color-bg-primary)',
        'bg-secondary': 'var(--color-bg-secondary)',
        'bg-tertiary': 'var(--color-bg-tertiary)',
        'bg-hover': 'var(--color-bg-hover)',

        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-tertiary': 'var(--color-text-tertiary)',

        'border': 'var(--color-border)',
        'border-subtle': 'var(--color-border-subtle)',

        // Status & Severity Colors
        'severity-critical': 'var(--color-severity-critical)',
        'severity-high': 'var(--color-severity-high)',
        'severity-medium': 'var(--color-severity-medium)',
        'severity-low': 'var(--color-severity-low)',
        'severity-info': 'var(--color-severity-info)',

        'status-success': 'var(--color-status-success)',
        'status-warning': 'var(--color-status-warning)',
        'status-error': 'var(--color-status-error)',
        'status-pending': 'var(--color-status-pending)',

        // Accent Colors
        'accent-primary': 'var(--color-accent-primary)',
        'accent-secondary': 'var(--color-accent-secondary)',
        'accent-hover': 'var(--color-accent-hover)',

        // Category Colors
        'category-ai': 'var(--color-category-ai)',
        'category-eslint': 'var(--color-category-eslint)',
        'category-a11y': 'var(--color-category-a11y)',
        'category-api': 'var(--color-category-api)',
      },
      fontFamily: {
        display: 'var(--font-display)',
        body: 'var(--font-body)',
        mono: 'var(--font-mono)',
      },
      fontSize: {
        xs: 'var(--text-xs)',
        sm: 'var(--text-sm)',
        base: 'var(--text-base)',
        lg: 'var(--text-lg)',
        xl: 'var(--text-xl)',
        '2xl': 'var(--text-2xl)',
        '3xl': 'var(--text-3xl)',
        '4xl': 'var(--text-4xl)',
      },
      lineHeight: {
        tight: 'var(--leading-tight)',
        normal: 'var(--leading-normal)',
        relaxed: 'var(--leading-relaxed)',
      },
      letterSpacing: {
        tight: 'var(--tracking-tight)',
        normal: 'var(--tracking-normal)',
        wide: 'var(--tracking-wide)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        base: 'var(--shadow-base)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },
      borderRadius: {
        none: 'var(--rounded-none)',
        sm: 'var(--rounded-sm)',
        base: 'var(--rounded-base)',
        lg: 'var(--rounded-lg)',
        xl: 'var(--rounded-xl)',
        '2xl': 'var(--rounded-2xl)',
        full: 'var(--rounded-full)',
      },
    },
  },
  plugins: [],
}
