# Scheme Weaver

> **Architecture as knowledge — from prose to ontology to interactive diagrams.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What Is It

Scheme Weaver is an AI-powered architecture modelling platform. You describe a system in plain English (or point it at a git repo), and it builds a structured, persistent **System** with a living ontology and multiple diagram views.

Diagrams are derived from data, not drawn by hand. Every node, edge, and group flows from the ontology. Sync operations keep prose, ontology, and views consistent as your architecture evolves.

---

## How It Works

There are three layers, each derived from the one above:

```
Prose  ──AI sync──►  Ontology  ──deterministic──►  Views (DIR → SVG)
  ▲                     ▲                                │
  └─────────AI sync─────┘◄──────────────────────────────┘
```

| Layer | What it is |
|---|---|
| **Prose** | A 2–6 sentence plain-English description of the system |
| **Ontology** | Structured entities (services, databases, queues, …) and their relationships |
| **View** | A scoped diagram derived from the ontology — stored as a DIR (Diagram Intermediate Representation) |

Claude never generates SVG directly. It generates **DIR JSON** — a vendor-agnostic description of nodes, edges, and groups. A deterministic renderer converts DIR → clean, semantic SVG.

---

## Key Concepts

### System

A System is the top-level container. It holds:
- `prose` — plain-English description
- `ontology` — entities and relationships
- `views[]` — one or more diagram perspectives
- `log[]` — append-only action history

### Ontology

Entities have a `type` (`service`, `database`, `queue`, `storage`, `gateway`, `user`, `team`, `concept`, `data_entity`, `external_system`), a `domain` for grouping, and an optional `technology` slug (a [Simple Icons](https://simpleicons.org) identifier used for branding icons).

Relationships have a `type` (`calls`, `owns`, `depends_on`, `publishes`, `subscribes_to`, `stores_in`, `managed_by`).

### DIR (Diagram Intermediate Representation)

The source of truth for a view. A JSON object with:
- `nodes[]` — typed diagram nodes (`service`, `database`, `queue`, `gateway`, `user`, …)
- `edges[]` — directed connections with style (`solid`, `dashed`, `dotted`) and direction
- `groups[]` — bounding-box groupings, usually one per domain
- `meta` — title, diagram type, tags

### View

A named diagram derived from the ontology, optionally scoped to a subset of entities by IDs, tags, or domain.

---

## Architecture

```
schemeweaver/
├── apps/
│   ├── web/              ← Nuxt 4 + Vue 3 web editor
│   └── cli/              ← Rust CLI (single binary)
├── apis/
│   └── server/           ← FastAPI backend
├── jobs/
│   └── worker/           ← ARQ async worker (Redis-backed)
├── libs/
│   ├── core/             ← Python pipeline, DIR models, renderer, layout
│   │   └── schemeweaver_core/
│   │       ├── models/
│   │       │   ├── dir.py        ← DIR / DiagramNode / DiagramEdge / DiagramGroup
│   │       │   ├── system.py     ← System / Ontology / View / OntologyEntity
│   │       │   └── api.py        ← All HTTP request/response DTOs
│   │       ├── system_pipeline.py   ← Prompt → System (prose + ontology + default view)
│   │       ├── ontology_to_dir.py   ← Ontology → DIR (deterministic)
│   │       ├── renderer.py          ← DIR → semantic SVG
│   │       └── layout.py            ← BFS layered layout (Python, used by renderer)
│   └── svgkit/           ← a11y validation, semantic ID enforcement
├── schema/
│   └── dir.schema.json   ← DIR JSON Schema
├── justfile
├── pyproject.toml        ← uv workspace root
├── Cargo.toml            ← Cargo workspace root
└── package.json          ← pnpm workspace root
```

All Python models live in `libs/core` — one source of truth for schemas shared across the server, pipeline, and tests.

---

## Features

### Core pipeline
- **Prompt → System** — one call generates prose, ontology, and a default overview diagram
- **Repo → System** — point at a git repo; the pipeline analyses manifests, docker-compose, and code to extract the architecture
- **AI sync** — bi-directional sync between any two layers (view ↔ prose, ontology ↔ prose, ontology ↔ view)
- **Icon enrichment** — heuristic keyword matching + [Simple Icons](https://simpleicons.org) assigns `technology` slugs to entities

### Web editor
- **Interactive canvas** — pan, zoom, drag nodes, drag groups (moves all members), lasso-select, connect tool
- **Multi-objective layout engine** — force-directed with 9 built-in objectives:
  - `node-repulsion` — prevents overlap
  - `edge-attraction` — spring force toward ideal edge length
  - `group-cohesion` — pulls group members toward centroid
  - `group-separation` — pushes unrelated groups apart (skips groups sharing a member)
  - `group-alignment` — aligns members along the dominant axis (row or column)
  - `topological-order` — encourages edges to flow top-to-bottom
  - `edge-crossing` — approximate crossing penalty (O(E²))
  - `grid-alignment` — snaps nodes toward a 40 px grid
  - `boundary` — soft wall keeps nodes inside padding
- **Stable layout** — positions only re-compute when graph topology changes; dragging a node never triggers a re-layout
- **Edge collapsing** — both directions:
  - *Inbound*: external node → 2+ members of the same group → collapses to `external → group`
  - *Outbound*: 2+ members of the same group → same target → collapses to `group → target`
  - *Group-to-group*: full collapse to a single `group → group` edge with count badge
- **Technology icons** — per-node Simple Icons glyphs; dynamic lookup with alias table and custom registry
- **Vendor branding** — AWS / Azure / GCP / Cloudflare / Vercel / HashiCorp stroke colours
- **Multiple views** — create scoped views by domain, tags, or entity selection
- **Sync bar** — one-click AI sync between any two layers with diff preview before apply
- **Recalibrate** — syncs technology icons and resets the layout from scratch in one action
- **Export** — SVG, PNG, Mermaid

### Extensibility
Register custom layout objectives at runtime:
```ts
import { registerObjective } from '~/utils/layout'

registerObjective('my-force', (weight, params) => ({
  name: 'my-force',
  weight,
  forces(state) {
    // Return Record<nodeId, {x, y}> force vectors
    return {}
  },
}))
```

Register custom technology icons:
```ts
import { registerIcon } from '~/utils/iconRegistry'

registerIcon('my-tech', {
  title: 'My Technology',
  path: '<path d="..." />',
  hex: 'FF6600',
})
```

---

## Quickstart

### Prerequisites

- Python 3.12+ with [`uv`](https://docs.astral.sh/uv/) — `pip install uv`
- An Anthropic API key
- Rust + Cargo — [rustup.rs](https://rustup.rs)
- `just` — `cargo install just`
- Node.js 20+ with `pnpm` — `npm i -g pnpm`

### Setup

```bash
git clone https://github.com/SchemeWeaver/schemeweaver
cd schemeweaver

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

uv sync          # Python dependencies
cargo fetch      # Rust dependencies
pnpm install     # Node dependencies
```

### Run the full stack

```bash
just dev
# API:        http://localhost:8000
# Swagger:    http://localhost:8000/docs
# Web editor: http://localhost:3000
```

Or run components individually:

```bash
just dev-server   # FastAPI only (:8000)
just dev-worker   # ARQ worker only
just dev-web      # Nuxt editor only (:3000)
```

### Create your first system

1. Open http://localhost:3000
2. Enter a prompt in the bottom bar, e.g. `"e-commerce platform with React frontend, Node API, PostgreSQL, and Redis"`
3. The editor generates prose, builds an ontology, and opens an interactive diagram
4. Use the **Sync bar** to keep layers in sync as you edit
5. Add more **Views** (scoped diagrams) from the view bar

### Import from a git repo

1. Click **Import from repo** in the library panel
2. Paste a git URL — Scheme Weaver clones, scans manifests and docker-compose files, and builds the ontology from real code
3. Use **Recalibrate** to assign technology icons and reset the layout after import

---

## API Reference

All routes are under `/v1/`.

### Systems

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/systems` | List all systems |
| `POST` | `/v1/systems/generate` | Generate a system from a prompt |
| `POST` | `/v1/systems/from-repo` | Generate a system from a git repository |
| `GET` | `/v1/systems/{slug}` | Load a system |
| `DELETE` | `/v1/systems/{slug}` | Delete a system |
| `PATCH` | `/v1/systems/{slug}/prose` | Update prose |
| `PATCH` | `/v1/systems/{slug}/ontology` | Update ontology |
| `POST` | `/v1/systems/{slug}/views` | Add a new view |
| `GET` | `/v1/systems/{slug}/views/{view_id}/svg` | Render a view to SVG |
| `PATCH` | `/v1/systems/{slug}/views/{view_id}` | Update a view's DIR |
| `POST` | `/v1/systems/{slug}/log` | Append to the action log |
| `POST` | `/v1/systems/{slug}/enrich-icons` | Assign technology icons via heuristics |

### AI Sync

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/systems/{slug}/sync/view-to-prose` | AI: derive prose from the active view |
| `POST` | `/v1/systems/{slug}/sync/ontology-to-prose` | AI: derive prose from ontology |
| `POST` | `/v1/systems/{slug}/sync/prose-to-ontology` | AI: derive ontology from prose |
| `POST` | `/v1/systems/{slug}/sync/ontology-to-view` | Deterministic: re-derive a view from ontology |

### Knowledge Base (repo import)

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/systems/from-repo` | Clone repo, build KB, generate system |
| `GET` | `/v1/systems/{slug}/knowledge-base` | Retrieve the compiled KB markdown |
| `PUT` | `/v1/systems/{slug}/knowledge-base` | Replace the KB markdown |
| `POST` | `/v1/systems/{slug}/sync/kb-to-ontology` | Re-derive ontology from KB |

### Legacy (raw DIR generation)

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/generate` | Generate a DIR from a prompt |
| `POST` | `/v1/update` | Refine a DIR with feedback |
| `GET` | `/v1/models` | List available AI models |
| `GET` | `/health` | Health check |

### Generate a system — example

```bash
curl -s -X POST http://localhost:8000/v1/systems/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "three-tier web app with React, FastAPI, and PostgreSQL"}' \
  | jq .system.ontology.entities[].name
```

---

## SVG Output

The SVG renderer produces semantic, accessible SVGs:

```xml
<svg role="img" aria-label="Diagram: My System — Overview"
     data-sw-version="1.0" data-diagram-type="architecture">

  <metadata>
    <!-- Embedded DIR JSON (round-trip source of truth) -->
    <sw:dir xmlns:sw="https://schemeweaver.dev/ns/1.0">{ ... }</sw:dir>
  </metadata>

  <title>My System — Overview</title>

  <g id="group-payments" class="sw-group" aria-label="Group: payments">
    <rect stroke-dasharray="6,3" rx="8" />
    <text>payments</text>
  </g>

  <g id="edge-api-to-db" class="sw-edge" aria-label="stores data: api to db">
    <path marker-end="url(#sw-arrow)" />
  </g>

  <g id="node-payment-service" class="sw-node"
     data-node-type="service" data-technology="fastapi"
     aria-label="Payment Service: Handles payment processing" role="group">
    <rect rx="8" fill="#f0f4ff" stroke="#6c8ebf" />
    <text class="sw-node-label">Payment Service</text>
    <text class="sw-node-type">fastapi</text>
  </g>

</svg>
```

The DIR JSON is embedded in `<metadata>` so the SVG is self-contained and round-trippable.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI backbone | Claude (`claude-sonnet-4-6`) via Anthropic API |
| Core pipeline | Python 3.12, Pydantic v2 |
| Backend API | FastAPI + uvicorn |
| Async jobs | ARQ + Redis |
| CLI | Rust (clap, reqwest) |
| Web editor | Nuxt 4 + Vue 3 |
| Technology icons | [Simple Icons](https://simpleicons.org) (dynamic lookup + custom registry) |
| Package managers | uv (Python), Cargo (Rust), pnpm (Node) |
| Task runner | just |

---

## Development

```bash
just test          # all tests (Python + Rust)
just test-python   # pytest only
just test-rust     # cargo test only
just lint          # ruff + clippy + eslint
just fix           # auto-fix lint issues
just build-cli     # cargo build --release → target/release/schemeweaver[.exe]

# Quick smoke test (server must be running)
just generate prompt="three-tier web app"
```

Run a single Python test file:

```bash
uv run pytest libs/core/tests/test_pipeline.py -v
```

---

## Roadmap

- [x] Core pipeline: prompt → DIR → semantic SVG
- [x] REST API (`/v1/generate`, `/v1/update`)
- [x] Rust CLI
- [x] ARQ async worker
- [x] Nuxt 4 web editor
- [x] **System Ontology model** — prose + ontology + scoped views
- [x] **Repo import** — git → knowledge base → ontology
- [x] **AI sync** — bi-directional sync between all three layers
- [x] **Multi-objective layout engine** — 9 built-in forces, extensible registry
- [x] **Edge collapsing** — inbound and outbound group-level edge compression
- [x] **Technology icons** — Simple Icons integration with custom registry
- [x] **Draggable groups** — move all group members together
- [ ] Scoped views UI (filter by domain / tag in the editor)
- [ ] Collaborative editing
- [ ] GitHub Action — diagram-as-code in CI
- [ ] VS Code extension
- [ ] Figma plugin
- [ ] Community fine-tuning dataset & benchmarks

---

## Contributing

Pull requests welcome. See `CONTRIBUTING.md` for guidelines.

---

## License

MIT © 2026 Scheme Weaver contributors.
