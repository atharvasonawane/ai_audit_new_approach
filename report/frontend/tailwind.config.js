/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary':   '#080C10',
        'bg-secondary': '#0D1117',
        'bg-tertiary':  '#161B22',
        'bg-hover':     '#1C2128',
        'bg-elevated':  '#21262D',

        'text-primary':   '#E6EDF3',
        'text-secondary': '#7D8590',
        'text-tertiary':  '#484F58',

        'border':          '#21262D',
        'border-subtle':   '#161B22',
        'border-emphasis': '#373E47',

        'severity-critical': '#FF5E5E',
        'severity-high':     '#F0883E',
        'severity-medium':   '#D29922',
        'severity-low':      '#3FB950',
        'severity-info':     '#58A6FF',

        'status-success': '#3FB950',
        'status-warning': '#D29922',
        'status-error':   '#F85149',
        'status-pending': '#484F58',

        'accent-primary':   '#388BFD',
        'accent-secondary': '#8957E5',
        'accent-hover':     '#58A6FF',

        'category-ai':     '#BC8CFF',
        'category-eslint': '#56D364',
        'category-a11y':   '#E3B341',
        'category-api':    '#58A6FF',
      },
      fontFamily: {
        display: ["'Outfit'", '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        body:    ["'Outfit'", '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono:    ["'JetBrains Mono'", "'Menlo'", "'Monaco'", 'monospace'],
      },
      fontSize: {
        '2xs': ['11px', { lineHeight: '1.4' }],
        xs:    ['12px', { lineHeight: '1.5' }],
        sm:    ['13px', { lineHeight: '1.5' }],
        base:  ['14px', { lineHeight: '1.6' }],
        lg:    ['16px', { lineHeight: '1.5' }],
        xl:    ['18px', { lineHeight: '1.4' }],
        '2xl': ['22px', { lineHeight: '1.3' }],
        '3xl': ['28px', { lineHeight: '1.25' }],
        '4xl': ['36px', { lineHeight: '1.15' }],
        '5xl': ['48px', { lineHeight: '1.1' }],
      },
      boxShadow: {
        sm:   '0 1px 3px rgba(0,0,0,0.4)',
        md:   '0 4px 12px rgba(0,0,0,0.5)',
        lg:   '0 8px 24px rgba(0,0,0,0.6)',
        glow: '0 0 0 1px rgba(56, 139, 253, 0.3), 0 0 20px rgba(56, 139, 253, 0.1)',
        focus: '0 0 0 3px rgba(56, 139, 253, 0.25)',
      },
      borderRadius: {
        sm:   '3px',
        base: '6px',
        lg:   '10px',
        xl:   '14px',
        '2xl':'20px',
        full: '9999px',
      },
    },
  },
  plugins: [],
}
