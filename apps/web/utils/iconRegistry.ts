/**
 * Icon registry: vendor badges + technology glyphs for diagram nodes.
 *
 * Vendor badges (top-right corner of nodes):
 *   - iconPath present → render simple-icons SVG path on colored circle
 *   - iconPath absent  → render a colored pill with text abbreviation (AWS, AZ)
 *
 * Technology glyphs (small icon centered on node, shown alongside label):
 *   - Resolved in priority order: custom registry → slug aliases → simple-icons
 *
 * Adding custom icons at runtime:
 *   import { registerIcon } from '~/utils/iconRegistry'
 *   registerIcon('my-service', { path: '<svg path d>', fill: '#ff0000', title: 'My Service' })
 *
 * The `technology` field on a DIR node should match a simple-icons slug
 * (see https://simpleicons.org) or any key registered via registerIcon().
 */

import * as SimpleIcons from 'simple-icons'
import { siGooglecloud, siCloudflare, siVercel, siHashicorp } from 'simple-icons'

// ── Vendor badges ────────────────────────────────────────────────────────────

export interface VendorBadge {
  /** Short abbreviation rendered as fallback text when no iconPath */
  label: string
  /** Brand background color */
  fill: string
  /** Icon / text color */
  textColor: string
  /** simple-icons SVG path (24×24 viewBox). When absent, renders text badge. */
  iconPath?: string
}

export const VENDOR_BADGES: Record<string, VendorBadge> = {
  aws:        { label: 'AWS', fill: '#FF9900', textColor: '#232F3E' },
  azure:      { label: 'AZ',  fill: '#0078D4', textColor: '#ffffff' },
  gcp:        { label: 'GCP', fill: '#4285F4', textColor: '#ffffff', iconPath: siGooglecloud.path },
  cloudflare: { label: 'CF',  fill: '#F38020', textColor: '#ffffff', iconPath: siCloudflare.path },
  vercel:     { label: 'VC',  fill: '#000000', textColor: '#ffffff', iconPath: siVercel.path },
  hashicorp:  { label: 'HC',  fill: '#7B42BC', textColor: '#ffffff', iconPath: siHashicorp.path },
}

// ── Vendor stroke colors (applied to node border when vendor is set) ─────────

export const VENDOR_STROKE_COLORS: Record<string, string> = {
  aws:        '#FF9900',
  azure:      '#0078D4',
  gcp:        '#4285F4',
  cloudflare: '#F38020',
  vercel:     '#555555',
  hashicorp:  '#7B42BC',
}

// ── Technology glyphs ────────────────────────────────────────────────────────

export interface TechIcon {
  /** SVG path data for a 24×24 viewBox */
  path: string
  /** Recommended fill color (brand hex, with # prefix) */
  fill: string
  title: string
}

// ── Custom icon registry ─────────────────────────────────────────────────────
// Populated at runtime via registerIcon(). Takes priority over simple-icons.

const _customIcons = new Map<string, TechIcon>()

/**
 * Register a custom icon so it shows up on nodes with a matching `technology`
 * field. Custom icons take priority over simple-icons lookups.
 *
 * @param slug       The technology slug to match (case-insensitive, e.g. 'my-service')
 * @param definition Icon definition with SVG path, fill color, and display title
 *
 * @example
 * registerIcon('internal-api', {
 *   path: 'M12 2 L22 12 L12 22 L2 12 Z',  // 24×24 viewBox path
 *   fill: '#4a90d9',
 *   title: 'Internal API',
 * })
 */
export function registerIcon(slug: string, definition: TechIcon): void {
  _customIcons.set(slug.toLowerCase(), definition)
}

// ── Slug alias table ─────────────────────────────────────────────────────────
// Maps common abbreviations / alternate names → canonical simple-icons slugs.
// Add entries here for any slug that doesn't match simple-icons directly.

const SLUG_ALIASES: Record<string, string> = {
  // Abbreviations
  postgres:       'postgresql',
  k8s:            'kubernetes',
  mongo:          'mongodb',
  elastic:        'elasticsearch',
  kafka:          'apachekafka',
  // Multi-word aliases
  'spring-boot':  'spring',
  'spring boot':  'spring',
  'node':         'nodedotjs',
  'nodejs':       'nodedotjs',
  'node.js':      'nodedotjs',
  'ts':           'typescript',
  'js':           'javascript',
  'react':        'react',
  'vue':          'vuedotjs',
  'nuxt':         'nuxtdotjs',
  'next':         'nextdotjs',
  'nextjs':       'nextdotjs',
  'next.js':      'nextdotjs',
  'svelte':       'svelte',
  'tailwind':     'tailwindcss',
  'prisma':       'prisma',
  'graphql':      'graphql',
  'grpc':         'grpc',
  'go':           'go',
  'golang':       'go',
  'rust':         'rust',
  'python':       'python',
  'php':          'php',
  'java':         'java',
  'dotnet':       'dotnet',
  '.net':         'dotnet',
  'csharp':       'csharp',
  'c#':           'csharp',
  's3':           'amazons3',
  'rds':          'amazonrds',
  'lambda':       'awslambda',
  'sqs':          'amazonsqs',
  'sns':          'amazonsimpleemailservice',
  'dynamodb':     'amazondynamodb',
  'cloudwatch':   'amazoncloudwatch',
  'ec2':          'amazonec2',
  'ecs':          'amazonecs',
  'eks':          'amazoneks',
  'cognito':      'amazoncognito',
  'aurora':       'amazonrds',
}

// ── Simple Icons dynamic lookup ───────────────────────────────────────────────

/**
 * Convert a simple-icons slug to its named export key.
 * e.g. 'apache-kafka' → 'siApachekafka', 'postgresql' → 'siPostgresql'
 */
function slugToExportKey(slug: string): string {
  const stripped = slug.replace(/[^a-z0-9]/gi, '')
  return 'si' + stripped.charAt(0).toUpperCase() + stripped.slice(1)
}

function lookupSimpleIcon(slug: string): TechIcon | null {
  const key = slugToExportKey(slug)
  const icon = (SimpleIcons as Record<string, { path: string; hex: string; title: string } | undefined>)[key]
  if (!icon) return null
  return { path: icon.path, fill: `#${icon.hex}`, title: icon.title }
}

// ── Lookups ──────────────────────────────────────────────────────────────────

export function getVendorBadge(vendor: string | null | undefined): VendorBadge | null {
  if (!vendor) return null
  return VENDOR_BADGES[vendor] ?? null
}

/**
 * Resolve a technology slug to an icon definition.
 *
 * Resolution order:
 *   1. Custom registry (registered via registerIcon())
 *   2. Slug alias table (e.g. 'postgres' → 'postgresql')
 *   3. Direct simple-icons lookup by slug
 */
export function getTechIcon(technology: string | null | undefined): TechIcon | null {
  if (!technology) return null
  const slug = technology.toLowerCase().trim()

  // 1. Custom registry
  const custom = _customIcons.get(slug)
  if (custom) return custom

  // 2. Alias → canonical slug, then simple-icons
  const canonical = SLUG_ALIASES[slug] ?? slug
  return lookupSimpleIcon(canonical)
}
