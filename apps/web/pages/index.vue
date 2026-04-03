<script setup lang="ts">
import AppShell from '~/components/AppShell.vue'
import DiagramCanvas from '~/components/DiagramCanvas.vue'
import DiagramLibrary from '~/components/DiagramLibrary.vue'
import ShapePanel from '~/components/ShapePanel.vue'
import PromptBar from '~/components/PromptBar.vue'
import EmptyState from '~/components/EmptyState.vue'
import IssuesBanner from '~/components/IssuesBanner.vue'
import { useSystem } from '~/composables/useSystem'

const { dir, saving, generate, fetchList, loadSystem } = useSystem()

// Refresh the library list whenever a save completes
watch(saving, (isSaving) => { if (!isSaving) fetchList() })

const libraryOpen = ref(true)
const shapesOpen = ref(false)

function useExample(prompt: string): void {
  generate(prompt)
}

async function handleLoad(slug: string): Promise<void> {
  await loadSystem(slug)
}
</script>

<template>
  <AppShell v-model:library-open="libraryOpen" v-model:shapes-open="shapesOpen">
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

      <Transition name="shapes-slide">
        <ShapePanel v-if="shapesOpen" @close="shapesOpen = false" />
      </Transition>
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
.library-slide-leave-active,
.shapes-slide-enter-active,
.shapes-slide-leave-active {
  transition: width 0.2s ease, opacity 0.2s ease;
  overflow: hidden;
}

.library-slide-enter-from,
.library-slide-leave-to,
.shapes-slide-enter-from,
.shapes-slide-leave-to {
  width: 0 !important;
  opacity: 0;
}
</style>
