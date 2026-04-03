# Scheme Weaver — cross-language task runner
# Usage: just <recipe>

set shell := ["bash", "-c"]
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Default recipe: list available recipes
default:
    @just --list

# ─── Setup ──────────────────────────────────────────────────────────────────

# Install all dependencies (Python, Rust, Node)
setup:
    uv sync
    cargo fetch
    pnpm install

# ─── Development ────────────────────────────────────────────────────────────

# Start all services (FastAPI server + ARQ worker)
dev:
    Start-Process powershell -ArgumentList "-NoLogo -Command just dev-server"; just dev-worker

# Start FastAPI server + Nuxt web editor together
dev-full:
    Start-Process powershell -ArgumentList "-NoLogo -Command just dev-server"; just dev-web

# Start FastAPI server only
dev-server:
    uv run uvicorn schemeweaver_server.main:app --reload --host 0.0.0.0 --port 8000 --app-dir apis/server

# Start ARQ worker only
dev-worker:
    uv run arq schemeweaver_worker.worker.WorkerSettings --watch jobs/worker/schemeweaver_worker

# ─── Testing ────────────────────────────────────────────────────────────────

# Run all tests (Python + Rust)
test:
    just test-python
    just test-rust

# Run pytest for all Python packages
test-python:
    uv run pytest

# Run cargo tests
test-rust:
    cargo test

# ─── Linting ────────────────────────────────────────────────────────────────

# Run all linters
lint:
    uv run ruff check .
    uv run ruff format --check .
    cargo clippy -- -D warnings
    pnpm --filter schemeweaver-web exec eslint . || true

# Auto-fix lint issues
fix:
    uv run ruff check --fix .
    uv run ruff format .
    cargo clippy --fix

# ─── Building ───────────────────────────────────────────────────────────────

# Build CLI binary + web app
build:
    just build-cli
    -pnpm --filter schemeweaver-web build

# Build CLI release binary
build-cli:
    cargo build --release --bin schemeweaver
    @echo "Binary at: target/release/schemeweaver"

# ─── Local model testing ─────────────────────────────────────────────────────

# Smoke test: generate one diagram with a local model (outputs to data/out/)
# Usage: just test-local
#        just test-local model=llama3.2 prompt="k8s cluster with ingress"
test-local model="qwen2.5:14b" prompt="":
    uv run python apis/server/scripts/test_generate.py --provider ollama --model {{model}} {{ if prompt != "" { "--prompt '" + prompt + "'" } else { "" } }}

# Run the full built-in prompt suite against a local model
# Usage: just test-suite
#        just test-suite model=llama3.2
test-suite model="qwen2.5:14b":
    uv run python apis/server/scripts/test_generate.py --provider ollama --model {{model}} --suite

# List available Ollama models
list-models:
    uv run python apis/server/scripts/test_generate.py --list-models

# Generate Scheme Weaver's own architecture diagram → docs/diagrams/ (commit this)
# Usage: just diagram-self
#        just diagram-self model=llama3.2
diagram-self model="qwen2.5:14b":
    uv run python apis/server/scripts/test_generate.py --provider ollama --model {{model}} --self

# Start Nuxt 4 web editor dev server (http://localhost:3000)
dev-web:
    pnpm --filter schemeweaver-web dev

# Quick test: generate a diagram via the running server
# Usage: just generate prompt="a three-tier web architecture"
generate prompt="a simple web API with a database":
    curl -s -X POST http://localhost:8000/v1/generate \
        -H "Content-Type: application/json" \
        -d '{"prompt": "{{prompt}}"}' \
        | uv run python -c "import sys,json; d=json.load(sys.stdin); print(d['svg'][:500]+'...' if len(d['svg'])>500 else d['svg'])"
