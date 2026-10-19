import './assets/main.css'

import { createApp } from 'vue'
import PhoneBlocked from './components/PhoneBlocked.vue'
import { isUnsupportedDevice } from './utils/deviceAccess.js'

if (isUnsupportedDevice()) {
  createApp(PhoneBlocked).mount('#app')
} else {
  Promise.all([import('./App.vue'), import('./router')]).then(([{ default: App }, { default: router }]) => {
    createApp(App).use(router).mount('#app')
  })
}
