export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  srcDir: '.',
  ssr: false,
  modules: ['@nuxtjs/tailwindcss'],
  css: [
    '@vue-flow/core/dist/style.css',
    '@vue-flow/core/dist/theme-default.css',
    '~/assets/css/main.css',
  ],
  vite: {
    optimizeDeps: {
      include: ['@vue-flow/core', '@dagrejs/dagre'],
    },
  },
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
    },
  },
})
