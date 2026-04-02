export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  srcDir: '.',
  ssr: false,
  modules: ['@nuxtjs/tailwindcss'],
  css: [
    '~/assets/css/main.css',
  ],
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
    },
  },
})
