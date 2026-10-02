# CSV Guard

[![Tests](https://github.com/XFFFK/csv-guard/actions/workflows/tests.yml/badge.svg)](https://github.com/XFFFK/csv-guard/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**CSV Guard validates CSV and JSONL files against a small JSON data contract.** It is built for the point before a spreadsheet, export or event file enters a report or pipeline: fail fast on missing fields, bad types, duplicate identifiers, invalid enum values, numeric bounds and date values.

It uses only the Python standard library, runs locally, and never uploads the data being checked.

## Quick start

```powershell
python -m pip install -e .

# Human-readable output; exit code is 1 when the data violates the contract.
csv-guard sample/orders.csv --contract sample/orders.schema.json

# Machine-readable output for a pipeline.
csv-guard sample/orders.jsonl --contract sample/orders.schema.json --format jsonl --report json > report.json

# A standalone HTML report.
csv-guard sample/orders.csv --contract sample/orders.schema.json --report html --output report.html
```

The contract declares fields and rules without requiring a schema server:

```json
{
  "name": "orders",
  "allow_extra_fields": false,
  "fields": [
    {"name": "order_id", "type": "string", "required": true, "unique": true},
    {"name": "amount", "type": "number", "required": true, "min": 0},
    {"name": "status", "type": "string", "required": true, "enum": ["pending", "paid", "cancelled"]},
    {"name": "created_at", "type": "date", "required": true}
  ]
}
```

Supported types are `string`, `integer`, `number`, `boolean`, `date` and `datetime`. A field can also use `pattern`, `min`, `max`, `enum`, `required`, `nullable` and `unique`.

## GitHub Action

Use the published tag in a workflow after checking out your repository:

```yaml
- uses: XFFFK/csv-guard@v0.1.0
  with:
    path: data/orders.csv
    contract: contracts/orders.schema.json
    report: text
```

The action uses the caller's local file paths and fails the job when the contract is violated. Pin a release tag or commit in production workflows.

## Reports and exit codes

- `text` is intended for people in terminal logs.
- `json` is a stable report with `status`, `input`, `summary` and `violations` for downstream tooling.
- `html` is a standalone report for review or an artifact upload.
- Exit `0` means all records pass; exit `1` means data violations; malformed contracts or unreadable input produce argparse error exit `2`.

The tool retains at most `--limit` violation details while keeping the total error count, so a large bad file does not flood CI logs.

## Development

```powershell
python -m unittest discover -s tests -q
```

The sample CSV intentionally fails with duplicate, range, enum and date/type violations. The sample JSONL passes. The project does not infer schemas, auto-fix data, evaluate cross-field expressions or send data over the network; those boundaries keep the first version predictable.

## License

MIT. See [LICENSE](LICENSE).
