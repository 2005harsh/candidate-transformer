# Candidate Transformer

A small pipeline for parsing, normalizing, merging and projecting candidate data from multiple sources (ATS exports, resumes, recruiter CSVs, GitHub profiles, DOCX/PDF/TXT resumes).

## Features

- Parsers for JSON (ATS), CSV, TXT, PDF, DOCX, and GitHub profiles
- Normalization utilities (emails, phones -> E.164, dates, countries, skills)
- Merge engine with fuzzy name matching, source trust hierarchy, deduplication and provenance
- Projection engine to map canonical records into custom output shapes
- Output validation utilities and a Click CLI entrypoint
- Sample data and tests (unit + integration)

## Installation

1. Create a virtual environment and activate it:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

Note: some dependencies are optional (e.g. `pycountry`). Install them if you need country normalization.

## Quick start (run both default and custom-config examples + tests)

```bash
# macOS / Linux
./run.sh
# Windows
run.bat
```

This creates/activates a venv, installs dependencies, runs the pipeline once
with the default schema and once with `sample_data/config_custom.json`, and
runs the test suite. Pre-generated outputs from these exact commands are
already committed at `sample_data/output_default.json` and
`sample_data/output_custom.json` so you can see expected output without
running anything.

## Usage

Basic CLI usage (parses input files/URLs, merges, projects, writes JSON):

```bash
python -m app.cli -i sample_data/sample_ats.json -i sample_data/recruiter_export.csv -o output.json
```

Use `--config` to pass a runtime projection config (JSON or YAML):

```bash
python -m app.cli -i sample_data/sample_ats.json -c sample_data/config_custom.json -o out.json
```

Enable debug logging with `--debug`.

## Configuration guide

Projection config is a JSON/YAML file with a `mapping` and optional `options` (see `sample_data/config_custom.json`):

- `mapping`: object mapping **output field name -> canonical source path** (dot notation, supports array indices like `emails[0]`). Example: `{"candidate_name": "full_name"}` outputs a field called `candidate_name` populated from the record's `full_name`. A mapping value can also be a small object `{ "from": "...", "type": "...", "normalize": "...", "required": true|false }` for more control over a single field.
- `options.include_provenance`: `true|false` (whether to include provenance in outputs)
- `options.include_confidence`: `true|false` (whether to include overall confidence)
- `options.missing`: `null|omit|error` (how to handle missing source values during projection)

Source path examples:

- `full_name`
- `emails[0]` (first email)
- `phones[0]`
- `skills`
- `experience`

Fields are read from the `CanonicalRecord` produced by the merge engine.

## Testing

Run the test suite with `pytest` (recommended from the virtualenv):

```bash
pip install -r requirements.txt
pytest -q
```

There are unit tests in `tests/` and integration tests that use `sample_data/`.

## Edge cases handled

- Accepts both file paths and HTTP(S) URLs for inputs
- Parsers attempt graceful fallbacks for malformed or unexpected structures
- ParserFactory returns `None` for unsupported file types; CLI warns and continues
- MergeEngine adds provenance entries for merged fields and uses configurable trust weights
- Projection supports `omit`, `null`, and `error` strategies for missing values

## Assumptions & Limitations

- Parsers use heuristic extraction (e.g., first non-empty line for name in text/PDF/DOCX). They won't be perfect for all resume styles.
- Phone normalization uses `phonenumbers` with a default region; you may need to pass region-specific values for best results.
- Country normalization uses `pycountry` when available, otherwise a small fallback map is used.
- GitHub API access is unauthenticated in the simple parser; rate limits can apply for heavy usage. Consider adding authentication if needed.
- The merge heuristics are conservative (trust ATS > Resume > Recruiter > GitHub) but can be tuned via `app/core/config.py`.

## Files of interest

- `app/parsers/` — parser implementations
- `app/services/` — normalizer, merge engine, projection engine
- `app/schemas/` — canonical Pydantic models
- `app/cli.py` — command-line entrypoint
- `sample_data/` — example inputs and configs

## Next steps / TODO ideas

- Add authenticated GitHub support and caching
- Expand parser heuristics (NLP-based name/section detection)
- Add more comprehensive test fixtures and CI pipeline

---
Created by the Candidate Transformer scaffolding tool. Customize as needed.
