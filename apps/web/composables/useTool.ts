export type ToolMode = 'grab' | 'lasso' | 'connect'

const tool = ref<ToolMode>('grab')

export function useTool() {
  return { tool }
}
