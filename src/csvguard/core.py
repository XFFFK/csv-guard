"""Validate CSV and JSONL records against a small JSON data contract."""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

SUPPORTED_TYPES = {"string", "integer", "number", "boolean", "date", "datetime"}
ViolationSink = Callable[[dict[str, Any]], None]


def load_contract(path: str | Path) -> dict[str, Any]:
    try:
        contract = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read contract: {exc}") from exc
    if not isinstance(contract, dict) or not isinstance(contract.get("fields"), list) or not contract["fields"]:
        raise ValueError("contract must contain a non-empty 'fields' list")
    names: set[str] = set()
    for field in contract["fields"]:
        if not isinstance(field, dict) or not isinstance(field.get("name"), str) or not field["name"]:
            raise ValueError("each contract field needs a name")
        if field["name"] in names:
            raise ValueError(f"duplicate contract field: {field['name']}")
        names.add(field["name"])
        if field.get("type", "string") not in SUPPORTED_TYPES:
            raise ValueError(f"unsupported field type for {field['name']}: {field.get('type')}")
        if "enum" in field and not isinstance(field["enum"], list):
            raise ValueError(f"enum must be a list for {field['name']}")
    return contract


def _violation(row: int, field: str, code: str, message: str, value: Any = None) -> dict[str, Any]:
    item: dict[str, Any] = {"row": row, "field": field, "code": code, "message": message}
    if value is not None:
        item["value"] = value
    return item


def _convert(value: Any, field: dict[str, Any]) -> Any:
    field_type = field.get("type", "string")
    if field_type == "string":
        return value if isinstance(value, str) else str(value)
    if field_type == "integer":
        if isinstance(value, bool):
            raise ValueError("expected integer")
        text = str(value).strip()
        converted = int(text)
        if str(converted) != text and not (text.startswith("+") and str(converted) == text[1:]):
            raise ValueError("expected integer")
        return converted
    if field_type == "number":
        return float(str(value).strip())
    if field_type == "boolean":
        text = str(value).strip().lower()
        if text not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValueError("expected boolean")
        return text in {"true", "1", "yes"}
    if field_type == "date":
        return date.fromisoformat(str(value).strip())
    if field_type == "datetime":
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    raise ValueError("unsupported field type")


def _check_record(row: int, record: dict[str, Any], contract: dict[str, Any], add: ViolationSink, unique_seen: dict[str, dict[str, int]], duplicate_firsts: set[tuple[str, str]]) -> None:
    field_specs = {field["name"]: field for field in contract["fields"]}
    if not contract.get("allow_extra_fields", False):
        for name in record:
            if name not in field_specs:
                add(_violation(row, name, "UNKNOWN_FIELD", "field is not declared in the contract"))
    for name, field in field_specs.items():
        value = record.get(name)
        blank = value is None or (isinstance(value, str) and not value.strip())
        if blank:
            if field.get("required", False) and not field.get("nullable", False):
                add(_violation(row, name, "MISSING_FIELD", "required value is empty"))
            continue
        try:
            converted = _convert(value, field)
        except (TypeError, ValueError) as exc:
            add(_violation(row, name, "TYPE_MISMATCH", str(exc), value))
            continue
        if "enum" in field and converted not in field["enum"] and value not in field["enum"]:
            add(_violation(row, name, "ENUM_VALUE", f"value must be one of {field['enum']}", value))
        if isinstance(converted, (int, float)) and not isinstance(converted, bool):
            if "min" in field and converted < field["min"]:
                add(_violation(row, name, "MIN_VALUE", f"value must be >= {field['min']}", value))
            if "max" in field and converted > field["max"]:
                add(_violation(row, name, "MAX_VALUE", f"value must be <= {field['max']}", value))
        if "pattern" in field and isinstance(value, str) and not re.search(field["pattern"], value):
            add(_violation(row, name, "PATTERN_MISMATCH", "value does not match pattern", value))
        if field.get("unique"):
            marker = str(value)
            first = unique_seen.setdefault(name, {}).get(marker)
            if first is None:
                unique_seen[name][marker] = row
            else:
                if (name, marker) not in duplicate_firsts:
                    add(_violation(first, name, "DUPLICATE_VALUE", "value is duplicated", value))
                    duplicate_firsts.add((name, marker))
                add(_violation(row, name, "DUPLICATE_VALUE", "value is duplicated", value))


def _csv_records(path: Path) -> tuple[list[str], Iterable[tuple[int, dict[str, Any]]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV must contain a header row")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV header contains duplicate field names")
        return list(reader.fieldnames), [(row_number, row) for row_number, row in enumerate(reader, start=2)]


def validate(path: str | Path, contract: dict[str, Any], fmt: str | None = None, limit: int = 100) -> dict[str, Any]:
    source = Path(path)
    if limit < 1:
        raise ValueError("limit must be positive")
    format_name = fmt or ("jsonl" if source.suffix.lower() in {".jsonl", ".ndjson"} else "csv")
    if format_name not in {"csv", "jsonl"}:
        raise ValueError("format must be csv or jsonl")
    errors: list[dict[str, Any]] = []
    total_errors = 0

    def add(item: dict[str, Any]) -> None:
        nonlocal total_errors
        total_errors += 1
        if len(errors) < limit:
            errors.append(item)

    rows = 0
    unique_seen: dict[str, dict[str, int]] = {}
    duplicate_firsts: set[tuple[str, str]] = set()
    if format_name == "csv":
        _, records = _csv_records(source)
        for row_number, record in records:
            rows += 1
            _check_record(row_number, record, contract, add, unique_seen, duplicate_firsts)
    else:
        try:
            handle = source.open(encoding="utf-8-sig")
        except OSError as exc:
            raise ValueError(f"cannot read input: {exc}") from exc
        with handle:
            for row_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                rows += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    add(_violation(row_number, "", "PARSE_ERROR", str(exc)))
                    continue
                if not isinstance(record, dict):
                    add(_violation(row_number, "", "PARSE_ERROR", "JSONL record must be an object"))
                    continue
                _check_record(row_number, record, contract, add, unique_seen, duplicate_firsts)
    return {
        "tool": "csvguard",
        "version": "0.1",
        "status": "pass" if total_errors == 0 else "fail",
        "exit_code": 0 if total_errors == 0 else 1,
        "input": {"path": str(source), "format": format_name, "rows": rows},
        "summary": {"errors": total_errors, "retained": len(errors), "truncated": total_errors > len(errors)},
        "violations": errors,
    }


