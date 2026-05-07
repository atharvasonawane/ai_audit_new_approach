# Frontend Setup (Vue 3 + Vite + TypeScript + Tailwind v4)

This project uses the latest Tailwind approach with the Vite plugin (`@tailwindcss/vite`) and CSS import (`@import "tailwindcss"`).

## Configured

- Vite plugin enabled in `vite.config.ts`
- Tailwind imported in `src/styles/index.css`
- App entry imports only one global stylesheet in `src/main.ts`

## Recommended Folder Structure

Use this structure as the dashboard grows:

```text
src/
  app/            # app bootstrap, providers, app-level shells
  assets/         # static images, icons
  components/
    ui/           # reusable primitives (cards, badges, inputs, table)
    shared/       # shared composed components
  composables/    # reusable Composition API logic
  features/       # domain modules (overview, defects, files, trends)
  layouts/        # route/page layout containers
  pages/          # route-level pages
  router/         # vue-router setup
  stores/         # pinia stores
  styles/         # global styles, tokens, utilities
  types/          # shared TypeScript types/interfaces
  utils/          # pure helper functions
  App.vue
  main.ts
```
