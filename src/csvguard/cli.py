"""Command-line interface for csv-guard."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from .core import load_contract, validate


def _text_report(report: dict) -> str:
    status = "PASS" if report["status"] == "pass" else "FAIL"
    input_info = report["input"]
    lines = [f"{status}: {input_info['rows']} {input_info['format']} records checked; {report['summary']['errors']} errors"]
    for error in report["violations"]:
        location = f"row {error['row']}" + (f", field {error['field']}" if error["field"] else "")
        lines.append(f"- {location}: [{error['code']}] {error['message']}")
    if report["summary"]["truncated"]:
        lines.append("- violation list truncated; increase --limit to inspect more")
    return "\n".join(lines)


def _html_report(report: dict, source: str) -> str:
    rows = "".join(f"<tr><td>{html.escape(str(error['row']))}</td><td>{html.escape(error['field'])}</td><td>{html.escape(error['code'])}</td><td>{html.escape(error['message'])}</td></tr>" for error in report["violations"])
    color = "#e8f7ee" if report["status"] == "pass" else "#fff0f0"
    return f"<!doctype html><meta charset='utf-8'><title>csv-guard report</title><style>body{{font:16px system-ui;max-width:1000px;margin:40px auto;color:#17212b}}.status{{padding:16px;border-radius:8px;background:{color}}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}</style><h1>csv-guard report</h1><p>Source: <code>{html.escape(source)}</code></p><div class='status'><strong>{report['status'].upper()}</strong> · {report['input']['rows']} records · {report['summary']['errors']} errors</div><h2>Violations</h2><table><tr><th>Row</th><th>Field</th><th>Code</th><th>Message</th></tr>{rows}</table>"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="csv-guard", description=__doc__)
    parser.add_argument("file", type=Path, help="CSV or JSONL input file")
    parser.add_argument("--contract", "--schema", required=True, type=Path, help="JSON data contract")
    parser.add_argument("--format", choices=("csv", "jsonl"), help="input format; inferred from extension when omitted")
    parser.add_argument("--report", choices=("text", "json", "html"), default="text")
    parser.add_argument("--output", type=Path, help="write report to this file instead of stdout")
    parser.add_argument("--limit", type=int, default=100, help="maximum violation details to retain")
    args = parser.parse_args(argv)
    try:
        report = validate(args.file, load_contract(args.contract), args.format, args.limit)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.report == "json":
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
    elif args.report == "html":
        rendered = _html_report(report, str(args.file))
    else:
        rendered = _text_report(report)
    if args.output:
        args.output.write_text(rendered + ("\n" if args.report != "html" else ""), encoding="utf-8")
    else:
        print(rendered)
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
