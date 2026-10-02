# Contributing to CSV Guard

Thanks for trying CSV Guard. The most useful contributions are small, reproducible improvements:

- Add a focused contract rule with a passing and failing fixture.
- Report a validation result that is misleading or hard to diagnose.
- Improve examples for CSV or JSONL workflows.

Before opening an issue, run:

```powershell
python -m unittest discover -s tests -q
```

Please keep sample data synthetic and avoid uploading private exports. Feature proposals should explain the input shape, the expected violation, and how a user would consume the result. The first version intentionally avoids schema inference, automatic repair, network lookups and cross-field expressions.
