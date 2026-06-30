@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Create venv if missing
if not exist venv\Scripts\python.exe (
  python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip and install requirements if present
python -m pip install --upgrade pip
if exist requirements.txt (
  pip install -r requirements.txt
)

echo Running default-schema projection on sample data...
python -m app.cli -i sample_data/sample_ats.json -i sample_data/recruiter_export.csv -o sample_data/output_default.json

echo Running custom-config projection on sample data...
python -m app.cli -i sample_data/sample_ats.json -c sample_data/config_custom.json -o sample_data/output_custom.json

echo Running tests...
pytest -q

echo Done. Outputs: sample_data\output_default.json, sample_data\output_custom.json
