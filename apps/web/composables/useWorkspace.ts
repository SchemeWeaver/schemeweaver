/**
 * Workspace layout state — shared across all consumers in the session.
 * Controls which panel mode is active and which left-panel tab is selected.
 */

export type WorkspaceMode = 'canvas' | 'split' | 'text'
export type LeftPanelTab  = 'prose' | 'ontology' | 'log'

const mode        = ref<WorkspaceMode>('canvas')
const leftTab     = ref<LeftPanelTab>('prose')

export function useWorkspace() {
  function setMode(m: WorkspaceMode): void {
    mode.value = m
  }

  function setLeftTab(t: LeftPanelTab): void {
    leftTab.value = t
    // Opening a tab while in canvas mode auto-switches to split
    if (mode.value === 'canvas') mode.value = 'split'
  }

  return { mode, leftTab, setMode, setLeftTab }
}
