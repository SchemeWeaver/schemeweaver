<script setup lang="ts">
import AppShell from '~/components/AppShell.vue'
import DiagramCanvas from '~/components/DiagramCanvas.vue'
import PromptBar from '~/components/PromptBar.vue'
import EmptyState from '~/components/EmptyState.vue'
import IssuesBanner from '~/components/IssuesBanner.vue'
import { useDiagram } from '~/composables/useDiagram'

const { dir, generate } = useDiagram()

function useExample(prompt: string): void {
  generate(prompt)
}
</script>

<template>
  <AppShell>
    <IssuesBanner />
    <div class="editor">
      <div class="editor__canvas">
        <EmptyState v-if="!dir" @use="useExample" />
        <DiagramCanvas v-else />
      </div>
      <PromptBar />
    </div>
  </AppShell>
</template>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.editor__canvas {
  flex: 1;
  overflow: hidden;
  position: relative;
}
</style>
