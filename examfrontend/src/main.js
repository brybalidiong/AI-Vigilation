import './assets/main.css'

import { createApp } from 'vue'
import PhoneBlocked from './components/PhoneBlocked.vue'
import { isPhoneDevice } from './utils/deviceAccess.js'

if (isPhoneDevice()) {
  createApp(PhoneBlocked).mount('#app')
} else {
  Promise.all([import('./App.vue'), import('./router')]).then(([{ default: App }, { default: router }]) => {
    createApp(App).use(router).mount('#app')
  })
}
