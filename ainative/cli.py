from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ainative.api.server import serve
from ainative.core.engine import default_engine
from ainative.sandbox.packaging import ExamPackageBuilder
from ainative.sandbox.scoring import AgentAnswer, DeterministicScorer
from ainative.sandbox.service import (
    GenerationFailed,
    PrivateStateMismatch,
    build_golden_scenario,
    load_generation_result,
    write_private_state,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(prog="ai-native")
    sub = parser.add_subparsers(dest="command", required=True)
    init_parser = sub.add_parser("init", help="Initialize the reference application")
    init_parser.add_argument("--reset", action="store_true", help="Reset demo state")
    serve_parser = sub.add_parser("serve", help="Run API and application shell")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", default=8000, type=int)
    sub.add_parser("demo", help="Run the reference workflow in the terminal")
    generate_parser = sub.add_parser(
        "sandbox-generate", help="Generate a validated analytics exam package"
    )
    generate_parser.add_argument("--seed", required=True, type=int)
    generate_parser.add_argument("--output", required=True, type=Path)
    score_parser = sub.add_parser(
        "sandbox-score", help="Score a structured analytics answer"
    )
    score_parser.add_argument("--benchmark", required=True, type=Path)
    score_parser.add_argument("--answer", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "sandbox-generate":
        try:
            result = build_golden_scenario(args.seed, args.output)
            archive = ExamPackageBuilder().build(result, args.output)
            write_private_state(result, args.output)
        except GenerationFailed as exc:
            print(str(exc), file=sys.stderr)
            return 3
        payload = {
            "benchmark_id": result.spec.benchmark_id,
            "archive": str(archive.resolve()),
            "validation": {
                "publishable": result.validation.publishable,
                "issues": [
                    {
                        "code": issue.code,
                        "severity": issue.severity,
                        "message": issue.message,
                    }
                    for issue in result.validation.issues
                ],
            },
            "effective_seed": result.spec.seed,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.command == "sandbox-score":
        try:
            result = load_generation_result(args.benchmark)
            payload = json.loads(args.answer.read_text(encoding="utf-8"))
            answer = AgentAnswer.from_dict(payload)
            report = DeterministicScorer().score_database(answer, result)
        except PrivateStateMismatch as exc:
            print(str(exc), file=sys.stderr)
            return 4
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"Invalid answer: {exc}", file=sys.stderr)
            return 2
        report_payload = report.to_dict()
        (args.benchmark / "score-report.json").write_text(
            json.dumps(report_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(report_payload, ensure_ascii=False))
        return 0

    engine = default_engine(ROOT)
    if args.command == "init":
        engine.seed(reset=args.reset)
        print("Initialized responsibility space and AI colleague.")
    elif args.command == "serve":
        engine.seed()
        serve(engine, ROOT / "web", host=args.host, port=args.port)
    elif args.command == "demo":
        engine.seed()
        result = engine.run_monitoring()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
