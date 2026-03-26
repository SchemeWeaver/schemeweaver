# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
uv sync && cargo fetch && pnpm install

# Development
just dev            # FastAPI server + ARQ worker together
just dev-server     # FastAPI on :8000 with hot reload only
just dev-worker     # ARQ worker only

# Testing
just test           # all tests (Python + Rust)
just test-python    # pytest only — uv run pytest
just test-rust      # cargo test only

# Linting / formatting
just lint           # ruff check + format --check + clippy + eslint
just fix            # ruff --fix + ruff format + clippy --fix

# Building
just build-cli      # cargo build --release → target/release/schemeweaver[.exe]

# Quick smoke test (server must be running)
just generate prompt="three-tier web app"
```

**Run a single Python test file:**
```bash
uv run pytest libs/core/tests/test_pipeline.py -v
```

**Run a single Rust test:**
```bash
cargo test -p schemeweaver-cli <test_name>
```

## Architecture

### The Core Pipeline

Claude never generates SVG directly. The pipeline is:
```
Prompt → Claude (claude-sonnet-4-6) → DIR JSON → Renderer → Semantic SVG → PostProcessor
```

**DIR (Diagram Intermediate Representation)** is the source of truth — `schema/dir.schema.json` is authoritative. DIR is a structured JSON object with `nodes`, `edges`, `groups`, and `meta`. Every element carries a `complexity` field (`low | medium | high`).

### Python packages (`uv` workspace)

| Package | Path | Role |
|---|---|---|
| `schemeweaver_core` | `libs/core/` | `Pipeline` (Claude → DIR), `Renderer` (DIR → SVG), `layout.py` (BFS layered layout), Pydantic `DIR` models |
| `schemeweaver_svgkit` | `libs/svgkit/` | `PostProcessor` — ARIA/a11y validation and semantic ID enforcement |
| `schemeweaver_server` | `apis/server/` | FastAPI app — `/v1/generate`, `/v1/update`, `/health` |
| `schemeweaver_worker` | `jobs/worker/` | ARQ async worker for Redis-backed job queue |

### Key data flow in `libs/core`

1. **`Pipeline.generate(prompt)`** — calls Claude with a system prompt that instructs it to output DIR JSON only. Normalizes `from`/`to` field aliases before Pydantic validation.
2. **`Pipeline.refine(dir, feedback)`** — sends the existing DIR + feedback back to Claude for an updated DIR.
3. **`compute_layout(dir)`** (`layout.py`) — BFS topological layering (Kahn's algorithm) assigns x/y coordinates to nodes. Returns a `Layout` with `LayoutNode` positions.
4. **`Renderer.render(dir, active_complexity)`** — builds SVG via `xml.etree.ElementTree`. Renders in three layers: groups (behind), edges, nodes (front). `active_complexity=None` produces interactive SVG with CSS toggling; a specific level produces a static SVG.
5. **`PostProcessor.process(svg)`** — validates ARIA labels and `role="img"` on root.

### Rust CLI (`apps/cli/`)

The CLI is a thin HTTP client over the FastAPI server. It does not contain any AI logic. Structure:
- `client.rs` — `ApiClient` wrapping `reqwest`
- `commands/generate.rs`, `commands/update.rs` — clap subcommands
- `output.rs` — human/JSON output formatting

`SCHEMEWEAVER_API_URL` env var (default: `http://localhost:8000`) controls which server the CLI hits.

### Complexity system

Every node, edge, and group has a `complexity: low | medium | high` field.
- `low` — always visible (main services, core flow)
- `medium` — supporting infrastructure (shown by default in interactive mode)
- `high` — implementation detail (hidden by default, CSS class `complexity-high { display: none }`)

Interactive SVGs embed CSS so the browser can toggle layers. Static exports (when `active_complexity` is set) hide elements above the requested level at render time.

### SVG conventions

- Root `<svg>` has `role="img"`, `aria-label`, `data-sw-version`, `data-diagram-type`
- Node groups: `id="node-{id}"`, class `sw-node complexity-{level}`, `data-node-type`
- Edge groups: `id="edge-{id}"`, class `sw-edge complexity-{level}`
- Group bounding boxes: `id="group-{id}"`, class `sw-group complexity-{level}`
- All node IDs in DIR must be kebab-case and semantic (e.g. `api-gateway`, not `node-1`)

### DiagramEdge Pydantic alias

`DiagramEdge` uses `from_node`/`to_node` internally but `from`/`to` in JSON (because `from` is a Python keyword). The pipeline normalizes both aliases before calling `model_validate`. Always use `from_node`/`to_node` in Python code; always use `from`/`to` in JSON/DIR schema.

## Environment

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. The server reads config via `apis/server/schemeweaver_server/config.py` (Pydantic Settings).
