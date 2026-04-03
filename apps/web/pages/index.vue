<script setup lang="ts">
import AppShell from '~/components/AppShell.vue'
import DiagramLibrary from '~/components/DiagramLibrary.vue'
import WorkspaceLayout from '~/components/WorkspaceLayout.vue'
import SyncBar from '~/components/SyncBar.vue'
import PromptBar from '~/components/PromptBar.vue'
import IssuesBanner from '~/components/IssuesBanner.vue'
import { useSystem } from '~/composables/useSystem'

const { saving, generate, fetchList, loadSystem } = useSystem()

// Refresh the library list whenever a save completes
watch(saving, (isSaving) => { if (!isSaving) fetchList() })

const libraryOpen = ref(true)
const shapesOpen = ref(false)

async function handleLoad(slug: string): Promise<void> {
  await loadSystem(slug)
}
</script>

<template>
  <AppShell v-model:library-open="libraryOpen" v-model:shapes-open="shapesOpen">
    <IssuesBanner />
    <div class="page">
      <Transition name="library-slide">
        <DiagramLibrary
          v-if="libraryOpen"
          :on-load="handleLoad"
          @close="libraryOpen = false"
        />
      </Transition>

      <WorkspaceLayout
        v-model:shapes-open="shapesOpen"
        class="page__workspace"
        @use="generate"
      />
    </div>
    <SyncBar />
    <PromptBar />
  </AppShell>
</template>

<style scoped>
.page {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.page__workspace {
  flex: 1;
  min-width: 0;
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
