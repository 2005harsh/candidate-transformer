#!/usr/bin/env bash
set -euo pipefail

# Activate virtual environment (create if missing)
if [ -d venv ]; then
  source venv/bin/activate
else
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip
  if [ -f requirements.txt ]; then
    pip install -r requirements.txt
  fi
fi

echo "Running default-schema projection on sample data..."
python -m app.cli -i sample_data/sample_ats.json -i sample_data/recruiter_export.csv -o sample_data/output_default.json

echo "Running custom-config projection on sample data..."
python -m app.cli -i sample_data/sample_ats.json -c sample_data/config_custom.json -o sample_data/output_custom.json

echo "Running tests..."
pytest -q

echo "Done. Outputs: sample_data/output_default.json, sample_data/output_custom.json"
