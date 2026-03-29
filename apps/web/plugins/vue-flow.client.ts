/**
 * Register Vue Flow as a Nuxt plugin (client-only — no SSR).
 */
import { VueFlow } from '@vue-flow/core'

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.component('VueFlow', VueFlow)
})
