import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
  },
  {
    path: '/audit',
    name: 'SplitPaneExplorer',
    component: () => import('../views/SplitPaneExplorer.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
