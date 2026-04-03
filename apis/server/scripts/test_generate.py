"""
Diagram generation smoke test / dev tool.

Runs the full pipeline (LLM → DIR → SVG → PostProcess) and writes output to
{project_root}/data/out/<slug>/  (or --output-dir override)

Usage:
    uv run python apis/server/scripts/test_generate.py
    uv run python apis/server/scripts/test_generate.py --provider ollama --model qwen2.5:14b
    uv run python apis/server/scripts/test_generate.py --prompt "k8s cluster with ingress"
    uv run python apis/server/scripts/test_generate.py --suite          # run all built-in prompts
    uv run python apis/server/scripts/test_generate.py --self           # generate schemeweaver's own architecture diagram
    uv run python apis/server/scripts/test_generate.py --list-models    # check Ollama availability
"""

import argparse
import json
import re
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

# ── repo root (three levels up from apis/server/scripts/) ──────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "out"
DOCS_DIAGRAMS_DIR = REPO_ROOT / "docs" / "diagrams"

sys.path.insert(0, str(REPO_ROOT / "libs" / "core"))
sys.path.insert(0, str(REPO_ROOT / "libs" / "svgkit"))

from schemeweaver_core.exporters import MermaidExporter
from schemeweaver_core.models.dir import ComplexityLevel
from schemeweaver_core.pipeline import Pipeline
from schemeweaver_core.providers import make_provider
from schemeweaver_core.renderer import Renderer
from schemeweaver_svgkit.postprocess import PostProcessor

# ── self-diagram: schemeweaver's own architecture ───────────────────────────
SELF_DIAGRAM = {
    "slug": "schemeweaver-architecture",
    "prompt": (
        "Scheme Weaver — an AI diagramming pipeline with the following components: "
        "A FastAPI server (apis/server) exposes two REST endpoints: POST /v1/generate "
        "and POST /v1/update. "
        "The Core library (libs/core) contains: a Pipeline class that sends prompts to an "
        "LLM provider and parses the response into a DIR (Diagram Intermediate Representation) "
        "— structured JSON with nodes, edges, groups, and complexity levels; a Renderer that "
        "converts DIR into semantic SVG using a BFS topological layout engine; and pluggable "
        "LLM providers for Anthropic Claude, OpenAI, and Ollama (local models). "
        "The SVGKit library (libs/svgkit) post-processes SVG output: validating ARIA labels "
        "and enforcing semantic node IDs. "
        "A Rust CLI (apps/cli) is a thin HTTP client over the FastAPI server that ships as a "
        "single binary with generate and update subcommands. "
        "An ARQ async worker (jobs/worker) provides a Redis-backed job queue for async "
        "diagram generation, decoupling long-running LLM calls from HTTP requests. "
        "A Nuxt 4 web editor (apps/web) is planned. "
        "Data flow: user prompt enters via CLI or HTTP → FastAPI server → Core Pipeline → "
        "LLM provider → DIR JSON → Renderer → SVG → PostProcessor → response."
    ),
}

# ── built-in test suite ─────────────────────────────────────────────────────
SUITE: list[dict] = [
    {
        "slug": "aws-three-tier",
        "prompt": "AWS three-tier web app with API Gateway, Lambda, RDS, and S3",
    },
    {
        "slug": "k8s-cluster",
        "prompt": "Kubernetes cluster with ingress controller, multiple services, and a PostgreSQL statefulset",
    },
    {
        "slug": "event-driven",
        "prompt": "Event-driven microservices architecture with Kafka, producer services, consumers, and a dead-letter queue",
    },
    {
        "slug": "simple-api",
        "prompt": "Simple REST API with a single backend service and a database",
    },
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def print_header(text: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {text}")
    print(f"{'-' * 60}")


def check_ollama_models(base_url: str) -> None:
    """Print available Ollama models."""
    try:
        import urllib.request
        url = base_url.replace("/v1", "") + "/api/tags"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        if models:
            print("Available Ollama models:")
            for m in models:
                print(f"  • {m}")
        else:
            print("No models pulled yet. Run: ollama pull <model>")
    except Exception as e:
        print(f"Could not reach Ollama at {base_url}: {e}")


def run_case(
    pipeline: Pipeline,
    renderer: Renderer,
    postprocessor: PostProcessor,
    mermaid_exporter: MermaidExporter,
    slug: str,
    prompt: str,
    complexity: ComplexityLevel | None,
    out_dir: Path,
    provider: str = "",
    model: str = "",
    write_to_data_out: bool = True,
) -> dict:
    """Run one generation case. Returns a result summary dict."""
    out_path = out_dir / slug
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"\n[{slug}]")
    print(f"  Prompt : {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"  Output : {out_path}")

    result = {
        "slug": slug,
        "prompt": prompt,
        "success": False,
        "elapsed_s": 0.0,
        "nodes": 0,
        "edges": 0,
        "groups": 0,
        "complexity_counts": {},
        "issues": [],
        "error": None,
    }

    t0 = time.perf_counter()
    try:
        dir_result = pipeline.generate(prompt)
        elapsed = time.perf_counter() - t0
        result["elapsed_s"] = round(elapsed, 2)

        # ── stats ────────────────────────────────────────────────────────────
        result["nodes"] = len(dir_result.nodes)
        result["edges"] = len(dir_result.edges)
        result["groups"] = len(dir_result.groups)
        complexity_counts: Counter = Counter(
            n.complexity.value for n in dir_result.nodes
        )
        result["complexity_counts"] = dict(complexity_counts)

        # ── render ───────────────────────────────────────────────────────────
        svg = renderer.render(dir_result, active_complexity=complexity)
        svg = postprocessor.process(svg)
        issues = postprocessor.validate(svg)
        result["issues"] = issues

        # ── write outputs ────────────────────────────────────────────────────
        mermaid = mermaid_exporter.serialize(dir_result)
        (out_path / "diagram.svg").write_text(svg, encoding="utf-8")
        (out_path / "diagram.mmd").write_text(mermaid, encoding="utf-8")
        (out_path / "diagram.dir.json").write_text(
            dir_result.model_dump_json(indent=2), encoding="utf-8"
        )

        summary = {
            "slug": slug,
            "prompt": prompt,
            "title": dir_result.meta.title,
            "diagram_type": dir_result.meta.diagram_type.value,
            "elapsed_s": result["elapsed_s"],
            "nodes": result["nodes"],
            "edges": result["edges"],
            "groups": result["groups"],
            "complexity": result["complexity_counts"],
            "issues": issues,
            "provider": provider,
            "model": model,
        }
        (out_path / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

        # If writing to docs/diagrams for --self, also copy to data/out for UI access
        if write_to_data_out and out_dir != DEFAULT_OUT_DIR:
            data_out_path = DEFAULT_OUT_DIR / slug
            data_out_path.mkdir(parents=True, exist_ok=True)
            (data_out_path / "diagram.svg").write_text(svg, encoding="utf-8")
            (data_out_path / "diagram.mmd").write_text(mermaid, encoding="utf-8")
            (data_out_path / "diagram.dir.json").write_text(
                dir_result.model_dump_json(indent=2), encoding="utf-8"
            )
            (data_out_path / "summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )

        result["success"] = True

        # ── print stats ──────────────────────────────────────────────────────
        print(f"  Title  : {dir_result.meta.title}")
        print(f"  Type   : {dir_result.meta.diagram_type.value}")
        print(
            f"  Nodes  : {result['nodes']}  "
            f"(low={complexity_counts.get('low', 0)}  "
            f"med={complexity_counts.get('medium', 0)}  "
            f"high={complexity_counts.get('high', 0)})"
        )
        print(f"  Edges  : {result['edges']}   Groups: {result['groups']}")
        print(f"  Time   : {elapsed:.1f}s")
        if issues:
            print(f"  Issues : {len(issues)}")
            for iss in issues:
                print(f"    ⚠  {iss}")
        else:
            print("  Issues : none")
        print(f"  Mermaid: {(out_path / 'diagram.mmd').relative_to(REPO_ROOT)}")

    except json.JSONDecodeError as e:
        result["error"] = f"JSON parse error: {e}"
        result["elapsed_s"] = round(time.perf_counter() - t0, 2)
        (out_path / "error.txt").write_text(
            f"JSON parse error after {result['elapsed_s']}s:\n{e}\n\nTraceback:\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        print(f"  FAILED (JSON): {e}")

    except Exception as e:
        result["error"] = str(e)
        result["elapsed_s"] = round(time.perf_counter() - t0, 2)
        (out_path / "error.txt").write_text(
            f"Error after {result['elapsed_s']}s:\n{e}\n\nTraceback:\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        print(f"  FAILED: {e}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Scheme Weaver generation test tool")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "anthropic", "openai"],
                        help="LLM provider (default: ollama)")
    parser.add_argument("--model", default="qwen2.5:14b",
                        help="Model ID (default: qwen2.5:14b)")
    parser.add_argument("--base-url", default=None, help="Override provider base URL")
    parser.add_argument("--prompt", default=None, help="Single prompt to test")
    parser.add_argument("--slug", default=None, help="Output slug (default: derived from prompt)")
    parser.add_argument("--suite", action="store_true", help="Run all built-in test prompts")
    parser.add_argument(
        "--self",
        action="store_true",
        dest="self_diagram",
        help="Generate Scheme Weaver's own architecture diagram → docs/diagrams/",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Base output directory (default: data/out/ or docs/diagrams/ for --self)",
    )
    parser.add_argument(
        "--complexity",
        default=None,
        choices=["low", "medium", "high"],
        help="Render static SVG at this complexity level (default: interactive)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available Ollama models and exit",
    )
    args = parser.parse_args()

    base_url = args.base_url or ("http://localhost:11434/v1" if args.provider == "ollama" else None)

    if args.list_models:
        check_ollama_models(base_url or "http://localhost:11434/v1")
        return

    complexity = ComplexityLevel(args.complexity) if args.complexity else None

    # ── resolve output dir ────────────────────────────────────────────────────
    if args.output_dir:
        out_dir = Path(args.output_dir)
    elif args.self_diagram:
        out_dir = DOCS_DIAGRAMS_DIR
    else:
        out_dir = DEFAULT_OUT_DIR

    print_header("Scheme Weaver — generation test")
    print(f"  Provider  : {args.provider}")
    print(f"  Model     : {args.model}")
    if base_url:
        print(f"  Base URL  : {base_url}")
    print(f"  Out dir   : {out_dir}")
    print(f"  Complexity: {args.complexity or 'interactive (all levels)'}")

    import os
    if args.provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    elif args.provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
    else:
        api_key = "ollama"

    try:
        provider = make_provider(
            provider=args.provider,
            model=args.model,
            api_key=api_key,
            base_url=base_url,
        )
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    pipeline = Pipeline(provider=provider)
    renderer = Renderer()
    postprocessor = PostProcessor()
    mermaid_exporter = MermaidExporter()

    # ── determine which cases to run ─────────────────────────────────────────
    if args.self_diagram:
        cases = [SELF_DIAGRAM]
    elif args.suite:
        cases = SUITE
    elif args.prompt:
        slug = args.slug or slugify(args.prompt)
        cases = [{"slug": slug, "prompt": args.prompt}]
    else:
        # default: first suite entry as a quick smoke test
        cases = [SUITE[0]]

    # ── run ───────────────────────────────────────────────────────────────────
    results = []
    for case in cases:
        res = run_case(
            pipeline, renderer, postprocessor, mermaid_exporter,
            case["slug"], case["prompt"], complexity, out_dir,
            provider=args.provider, model=args.model,
            write_to_data_out=args.self_diagram  # Copy to data/out for UI access when using --self
        )
        results.append(res)

    # ── summary ───────────────────────────────────────────────────────────────
    if len(results) > 1:
        print_header("Summary")
        passed = sum(1 for r in results if r["success"])
        failed = len(results) - passed
        total_time = sum(r["elapsed_s"] for r in results)
        print(f"  Passed: {passed}/{len(results)}   Failed: {failed}   Total time: {total_time:.1f}s")
        for r in results:
            status = "OK" if r["success"] else "FAIL"
            err = f"  → {r['error']}" if r["error"] else ""
            print(f"  [{status}] {r['slug']} ({r['elapsed_s']}s){err}")

    if args.self_diagram and all(r["success"] for r in results):
        svg_path = out_dir / SELF_DIAGRAM["slug"] / "diagram.svg"
        print(f"\n  Diagram written to: {svg_path.relative_to(REPO_ROOT)}")
        print("  Commit it: git add docs/diagrams/ && git commit -m 'chore: regenerate architecture diagram'")

    # ── write combined run log (always to data/out/, not docs/) ──────────────
    run_log_dir = DEFAULT_OUT_DIR
    run_log_dir.mkdir(parents=True, exist_ok=True)
    (run_log_dir / "last_run.json").write_text(
        json.dumps(
            {
                "provider": args.provider,
                "model": args.model,
                "out_dir": str(out_dir),
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if any(not r["success"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
