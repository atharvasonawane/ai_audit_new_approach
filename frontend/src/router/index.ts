import { createRouter, createWebHistory } from 'vue-router'

import DashboardLayout from '../layouts/DashboardLayout.vue'
import DashboardOverviewPage from '../pages/DashboardOverviewPage.vue'
import FileExplorerPage from '../pages/FileExplorerPage.vue'
import FileDetailPage from '../pages/FileDetailPage.vue'
import DefectsPage from '../pages/DefectsPage.vue'
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
          component: DefectsPage,
        },
        {
          path: 'files',
          name: 'files',
          component: FileExplorerPage,
        },
        {
          path: 'files/:id',
          name: 'file-detail',
          component: FileDetailPage,
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
