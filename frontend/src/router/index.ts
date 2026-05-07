import { createRouter, createWebHistory } from 'vue-router'

import DashboardLayout from '../layouts/DashboardLayout.vue'
import DashboardOverviewPage from '../pages/DashboardOverviewPage.vue'
import FileExplorerPage from '../pages/FileExplorerPage.vue'
import PlaceholderPage from '../pages/PlaceholderPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: DashboardLayout,
      children: [
        {
          path: '',
          name: 'dashboard-overview',
          component: DashboardOverviewPage,
        },
        {
          path: 'defects',
          name: 'defects',
          component: PlaceholderPage,
          props: {
            title: 'Defects',
            description: 'Prioritized accessibility, Vue best-practice, and UI consistency issues.',
          },
        },
        {
          path: 'files',
          name: 'files',
          component: FileExplorerPage,
        },
        {
          path: 'trends',
          name: 'trends',
          component: PlaceholderPage,
          props: {
            title: 'Trends',
            description: 'Track health score movement and defect counts across scans.',
          },
        },
        {
          path: 'settings',
          name: 'settings',
          component: PlaceholderPage,
          props: {
            title: 'Settings',
            description: 'Configuration, data sources, and audit profile controls.',
          },
        },
      ],
    },
  ],
})

export default router
