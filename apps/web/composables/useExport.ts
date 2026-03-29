/**
 * Export helpers: download SVG, Mermaid, or DIR JSON.
 */
import type { DIR } from '~/types/dir'

export function useExport() {
  function downloadBlob(content: string, filename: string, mimeType: string): void {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  function exportSvg(svg: string, title?: string): void {
    const slug = title ? title.toLowerCase().replace(/\s+/g, '-') : 'diagram'
    downloadBlob(svg, `${slug}.svg`, 'image/svg+xml')
  }

  function exportMermaid(mermaid: string, title?: string): void {
    const slug = title ? title.toLowerCase().replace(/\s+/g, '-') : 'diagram'
    downloadBlob(mermaid, `${slug}.mmd`, 'text/plain')
  }

  function exportDir(dir: DIR): void {
    const slug = dir.meta.title.toLowerCase().replace(/\s+/g, '-')
    downloadBlob(JSON.stringify(dir, null, 2), `${slug}.dir.json`, 'application/json')
  }

  function copyMermaid(mermaid: string): Promise<void> {
    return navigator.clipboard.writeText(mermaid)
  }

  return { exportSvg, exportMermaid, exportDir, copyMermaid }
}
