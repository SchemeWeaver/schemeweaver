<script setup lang="ts">
import AppShell from '~/components/AppShell.vue'
import DiagramCanvas from '~/components/DiagramCanvas.vue'
import DiagramLibrary from '~/components/DiagramLibrary.vue'
import PromptBar from '~/components/PromptBar.vue'
import EmptyState from '~/components/EmptyState.vue'
import IssuesBanner from '~/components/IssuesBanner.vue'
import { useDiagram } from '~/composables/useDiagram'
import { useLibrary } from '~/composables/useLibrary'

const { dir, generate, loadSaved } = useDiagram()
const { loadDiagram } = useLibrary()

const libraryOpen = ref(false)

function useExample(prompt: string): void {
  generate(prompt)
}

async function handleLoad(slug: string): Promise<void> {
  const res = await loadDiagram(slug)
  loadSaved(res)
}
</script>

<template>
  <AppShell v-model:library-open="libraryOpen">
    <IssuesBanner />
    <div class="editor">
      <Transition name="library-slide">
        <DiagramLibrary
          v-if="libraryOpen"
          :on-load="handleLoad"
          @close="libraryOpen = false"
        />
      </Transition>

      <div class="editor__canvas">
        <EmptyState v-if="!dir" @use="useExample" />
        <DiagramCanvas v-else />
      </div>
    </div>
    <PromptBar />
  </AppShell>
</template>

<style scoped>
.editor {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.editor__canvas {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.library-slide-enter-active,
.library-slide-leave-active {
  transition: width 0.2s ease, opacity 0.2s ease;
  overflow: hidden;
}

.library-slide-enter-from,
.library-slide-leave-to {
  width: 0 !important;
  opacity: 0;
}
</style>
