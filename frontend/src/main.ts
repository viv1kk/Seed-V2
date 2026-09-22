import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import './design/tokens.css'
import './design/base.css'

createApp(App).use(createPinia()).mount('#app')
