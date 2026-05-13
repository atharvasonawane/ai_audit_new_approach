import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
  },
  {
    path: '/analyzing',
    name: 'Analyzing',
    component: () => import('../views/Analyzing.vue'),
  },
  {
    path: '/dashboard',
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
