/**
 * Icon registry: vendor badges + technology glyphs for diagram nodes.
 *
 * Vendor badges (top-right corner of nodes):
 *   - iconPath present → render simple-icons SVG path on colored circle
 *   - iconPath absent  → render a colored pill with text abbreviation (AWS, AZ)
 *
 * Technology glyphs (small icon centered on node, shown alongside label):
 *   - simple-icons paths where available, keyed by technology string from DIR
 */

import {
  siGooglecloud,
  siCloudflare,
  siVercel,
  siHashicorp,
  siFastapi,
  siDjango,
  siSpring,
  siRedis,
  siApachekafka,
  siRabbitmq,
  siPostgresql,
  siMysql,
  siNginx,
  siDocker,
  siKubernetes,
  siMongodb,
  siElasticsearch,
} from 'simple-icons'

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
  /** Recommended fill color (brand hex) */
  fill: string
  title: string
}

export const TECH_ICONS: Record<string, TechIcon> = {
  // APIs / frameworks
  fastapi:        { path: siFastapi.path,       fill: `#${siFastapi.hex}`,       title: 'FastAPI' },
  django:         { path: siDjango.path,        fill: `#${siDjango.hex}`,        title: 'Django' },
  'spring-boot':  { path: siSpring.path,        fill: `#${siSpring.hex}`,        title: 'Spring Boot' },
  spring:         { path: siSpring.path,        fill: `#${siSpring.hex}`,        title: 'Spring' },
  // Databases
  postgres:       { path: siPostgresql.path,    fill: `#${siPostgresql.hex}`,    title: 'PostgreSQL' },
  postgresql:     { path: siPostgresql.path,    fill: `#${siPostgresql.hex}`,    title: 'PostgreSQL' },
  mysql:          { path: siMysql.path,         fill: `#${siMysql.hex}`,         title: 'MySQL' },
  mongodb:        { path: siMongodb.path,       fill: `#${siMongodb.hex}`,       title: 'MongoDB' },
  elasticsearch:  { path: siElasticsearch.path, fill: `#${siElasticsearch.hex}`, title: 'Elasticsearch' },
  // Caches / queues / streams
  redis:          { path: siRedis.path,         fill: `#${siRedis.hex}`,         title: 'Redis' },
  kafka:          { path: siApachekafka.path,   fill: `#${siApachekafka.hex}`,   title: 'Apache Kafka' },
  rabbitmq:       { path: siRabbitmq.path,      fill: `#${siRabbitmq.hex}`,      title: 'RabbitMQ' },
  // Infrastructure
  nginx:          { path: siNginx.path,         fill: `#${siNginx.hex}`,         title: 'Nginx' },
  docker:         { path: siDocker.path,        fill: `#${siDocker.hex}`,        title: 'Docker' },
  kubernetes:     { path: siKubernetes.path,    fill: `#${siKubernetes.hex}`,    title: 'Kubernetes' },
  k8s:            { path: siKubernetes.path,    fill: `#${siKubernetes.hex}`,    title: 'Kubernetes' },
}

// ── Lookups ──────────────────────────────────────────────────────────────────

export function getVendorBadge(vendor: string | null | undefined): VendorBadge | null {
  if (!vendor) return null
  return VENDOR_BADGES[vendor] ?? null
}

export function getTechIcon(technology: string | null | undefined): TechIcon | null {
  if (!technology) return null
  return TECH_ICONS[technology.toLowerCase()] ?? null
}
