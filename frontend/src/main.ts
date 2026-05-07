import { createApp } from 'vue'
import './styles/index.css'
import App from './App.vue'
import router from './router'

import { initTheme } from './theme/theme'

initTheme()

createApp(App).use(router).mount('#app')
