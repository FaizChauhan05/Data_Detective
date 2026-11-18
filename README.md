# AI Data Detective

A small personal data profiling and cleaning application built with plain HTML, CSS and JavaScript, backed by Python and FastAPI.

## Stack
AI was only used for the Frontend

- Frontend: HTML, CSS, vanilla JavaScript
- Backend: FastAPI
- Data processing: Polars
- Anomaly detection: scikit-learn Isolation Forest
- Charts: Plotly.js (loaded from its CDN)

## Run locally

Python 3.11 or 3.12 is recommended

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\\Scripts\\activate    # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000.

## Features

- Upload CSV, XLSX and XLS datasets
- Dataset overview, column profiling, missing-value summary and duplicate inspection
- Manual cell editing and column type conversion
- Undo, redo, reset and export to CSV, XLSX or Parquet
- Isolation Forest anomaly detection with interactive Plotly charts

## Notes

- Data and cleaning history are held in server memory and are cleared when the server restarts. This is intentional for this personal-project version.
- The application does not currently include user accounts or persistent database storage.
- For a simple single-instance deployment, the in-memory session approach is adequate. Multiple server workers or ephemeral deployments would require shared storage.
- Plotly.js and the optional Google Fonts are loaded from external CDNs, so those visual assets require an internet connection.
- Uploaded files are processed in memory; very large files may require more server memory.
