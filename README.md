
# 🧬 Candidate Transformer

**Unify candidate data from any source with a powerful, extensible pipeline.**

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/2005harsh/candidate-transformer/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Table of Contents
1. [Overview](#overview)
2. [Features](#features)
3. [System Architecture](#system-architecture)
4. [Tech Stack](#tech-stack)
5. [Getting Started](#getting-started)
   - [Clone & Install](#clone--install)
   - [Quick Start](#quick-start)
   - [Basic Usage](#basic-usage)
6. [Configuration Guide](#configuration-guide)
7. [Testing](#testing)
8. [Demo](#demo)
9. [License](#license)
10. [Contributing](#contributing)
11. [Contact](#contact)

---

## Overview

**Candidate Transformer** is a modular pipeline that ingests candidate data from **multiple sources** (ATS exports, resumes in PDF/DOCX/TXT, recruiter CSVs, even GitHub profiles), **normalises** it, **merges** duplicate records intelligently, and **projects** the unified data into any custom output format you need.

Built with **Python** and designed for **extensibility**, it's perfect for HR tech integrations, recruitment analytics, or any system that needs a single source of truth for candidate information.

---

## Features

### 🗂️ Multi‑Source Parsing
- **Seamless ingestion** – parse JSON (ATS), CSV, TXT, PDF, DOCX, and live GitHub profiles (via URL).
- **Graceful fallbacks** – handles malformed or unexpected structures without crashing.
- **Remote support** – accepts both local file paths and HTTP/HTTPS URLs.

### 🧹 Intelligent Normalisation
- **Email & phone** – normalise to canonical formats (E.164 for phones).
- **Dates & countries** – unify date representations and country names using `pycountry`.
- **Skills** – standardise skill names for easier matching.
- **Extensible** – easily add your own normalisation rules.

### 🔗 Smart Merging & Deduplication
- **Fuzzy name matching** – merge records even with slight name variations.
- **Source trust hierarchy** – assign different weights to sources (e.g., ATS > Resume > Recruiter > GitHub).
- **Provenance tracking** – keep track of which source contributed which field.
- **Confidence scoring** – optional overall confidence metric for merged records.

### 🎯 Flexible Projection
- **Custom output shapes** – map canonical fields to any output field name using a simple JSON/YAML config.
- **Fine‑grained control** – specify data types, normalisation, and missing‑value strategies (`null`, `omit`, `error`).
- **Supports dot notation** – access nested fields and array indices (e.g., `emails[0]`).

### 🧪 Developer Friendly
- **CLI entrypoint** – easy to integrate into scripts or CI/CD.
- **Unit & integration tests** – ensures reliability.
- **Debug mode** – detailed logs for troubleshooting.

---

## System Architecture

> A high‑level view of how data flows through the pipeline.

### Data Flow

```
Input Sources (JSON/CSV/PDF/DOCX/TXT/GitHub URLs)
       │
       ▼
┌──────────────┐
│   Parsers    │  → each source is parsed into a raw dictionary
└──────────────┘
       │
       ▼
┌──────────────┐
│  Normalizer  │  → standardises fields (emails, phones, dates, etc.)
└──────────────┘
       │
       ▼
┌──────────────┐
│  MergeEngine │  → deduplicates and merges records using trust weights
└──────────────┘
       │
       ▼
┌──────────────┐
│ProjectionEng.│  → maps canonical records to your custom output schema
└──────────────┘
       │
       ▼
   JSON Output
```

### Key Components

- **Parsers** – each source type has its own parser; the `ParserFactory` dynamically selects the right one.
- **CanonicalRecord** – a Pydantic model that enforces a unified internal schema.
- **MergeEngine** – uses a configurable trust hierarchy and fuzzy matching to combine records.
- **ProjectionEngine** – applies a mapping configuration to produce the final output.

### Design Decisions

- **Conservative merging** – we prioritise data quality over quantity; the default trust hierarchy is cautious (ATS is most trusted, GitHub least). You can tune this in `app/core/config.py`.
- **Heuristic extraction** – for unstructured resumes (PDF/DOCX/TXT), we use simple heuristics (e.g., first non‑empty line as name). This is not perfect but works for many common formats.
- **Extensibility** – all components are built with interfaces, so you can swap in your own parsers, normalisers, or merging strategies.

---

## Tech Stack

- **Core** – Python 3.8+
- **CLI** – Click
- **Data validation** – Pydantic
- **PDF parsing** – PyPDF2
- **DOCX parsing** – python-docx
- **YAML support** – PyYAML
- **Phone normalisation** – phonenumbers
- **Country normalisation** – pycountry (optional)
- **Testing** – pytest

---

## Getting Started

### 1. Clone & Install

```bash
git clone https://github.com/2005harsh/candidate-transformer.git
cd candidate-transformer
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Quick Start (run the example + tests)

```bash
# macOS / Linux
./run.sh
# Windows
run.bat
```

This will:
- Set up the virtual environment
- Install dependencies
- Run the pipeline twice (with default and custom configs)
- Run the test suite

Pre‑generated outputs (`sample_data/output_default.json` and `sample_data/output_custom.json`) are already committed so you can see expected results without running anything.

### 3. Basic Usage

Parse one or more input files/URLs, merge them, and project to a JSON output:

```bash
python -m app.cli -i sample_data/sample_ats.json -i sample_data/recruiter_export.csv -o output.json
```

Use a custom projection config (JSON or YAML):

```bash
python -m app.cli -i sample_data/sample_ats.json -c sample_data/config_custom.json -o out.json
```

Enable debug logging:

```bash
python -m app.cli -i sample_data/sample_ats.json --debug
```

---

## Configuration Guide

The projection config is a JSON/YAML file with a `mapping` object and optional `options`.

### `mapping`
- Maps **output field name** → **canonical source path** (dot notation, supports array indices like `emails[0]`).
- Example: `{"candidate_name": "full_name"}` → output field `candidate_name` gets value from `full_name`.
- For more control, use an object:
  ```json
  {
    "candidate_name": {
      "from": "full_name",
      "type": "string",
      "normalize": true,
      "required": true
    }
  }
  ```

### `options`
- `include_provenance` – `true`/`false` (adds source info to output)
- `include_confidence` – `true`/`false` (adds overall confidence score)
- `missing` – `null`, `omit`, or `error` (how to handle missing source values)

See `sample_data/config_custom.json` for a complete example.

---

## Testing

Run the test suite with `pytest` (from your virtual environment):

```bash
pytest -q
```

- **Unit tests** – in `tests/`
- **Integration tests** – use `sample_data/` to validate end‑to‑end behaviour

---



## License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## Contributing

Contributions are welcome! Please open an issue or pull request for any improvements, bug fixes, or new features.  
Make sure to add tests for your changes and run the test suite before submitting.

---

## Contact

- **Author** – Harshwardhan Mali ([Github](https://github.com/2005harsh))
- **Project Link** – [https://github.com/2005harsh/candidate-transformer](https://github.com/2005harsh/candidate-transformer)
- **Email** - harshwardhanmali2005@gmail.com
---




