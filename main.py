from __future__ import annotations

from io import BytesIO
from uuid import uuid4
from typing import Any

import polars as pl
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from analysis.anomaly_detection import detect_anomalies
from analysis.data_correction import change_data_type
from analysis.profiling import profile_dataframe, dataset_summary, numeric_profile, duplicate_rows, missing_profile, outlier_profile, categorical_distributions

app = FastAPI(title="AI Data Detective")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# In-memory session storage: appropriate for this personal-project deployment.
SESSIONS: dict[str, dict[str, Any]] = {}


def get_session(session_id: str | None):
    if not session_id:
        raise HTTPException(400, "Missing session identifier. Refresh the page and try again.")
    return SESSIONS.setdefault(session_id, {"datasets": {}})


def get_dataset(session: dict, dataset_id: str):
    dataset = session["datasets"].get(dataset_id)
    if dataset is None:
        raise HTTPException(404, "Dataset not found. It may have expired after a server restart.")
    return dataset


def preview(df: pl.DataFrame, limit: int = 100):
    return {"columns": df.columns, "rows": df.head(limit).to_dicts(), "total_rows": df.height}


@app.get("/", response_class=HTMLResponse)
def home():
    return FileResponse("frontend/index.html")


@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...), x_session_id: str = Header(None)):
    session = get_session(x_session_id)
    added, errors = [], []
    for file in files:
        name = file.filename or "uploaded_dataset"
        raw = await file.read()
        try:
            if name.lower().endswith(".csv"):
                df = None
                last_error = None
                for encoding in ("utf8", "windows-1252", "utf16", "utf8-lossy"):
                    try:
                        df = pl.read_csv(BytesIO(raw), encoding=encoding, infer_schema_length=10000, try_parse_dates=True)
                        break
                    except Exception as exc:
                        last_error = exc
                if df is None:
                    raise ValueError(f"Could not read CSV: {last_error}")
            elif name.lower().endswith((".xlsx", ".xls")):
                df = pl.read_excel(BytesIO(raw), engine="calamine")
            else:
                raise ValueError("Only CSV, XLSX and XLS files are supported.")
            if df.width == 0:
                raise ValueError("The uploaded file has no columns.")
            dataset_id = uuid4().hex[:12]
            session["datasets"][dataset_id] = {
                "name": name, "original": df.clone(), "cleaned": df.clone(),
                "undo": [], "redo": [], "history": [], "anomaly": None,
            }
            added.append({"id": dataset_id, "name": name, **dataset_summary(df)})
        except Exception as exc:
            errors.append({"name": name, "error": str(exc)})
    return {"added": added, "errors": errors, "datasets": dataset_list(session)}


def dataset_list(session):
    result = []
    for dataset_id, item in session["datasets"].items():
        result.append({"id": dataset_id, "name": item["name"], **dataset_summary(item["original"])})
    return result


@app.get("/api/datasets")
def list_datasets(x_session_id: str = Header(None)):
    return {"datasets": dataset_list(get_session(x_session_id))}


@app.get("/api/datasets/{dataset_id}")
def dataset_detail(dataset_id: str, x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    df = item["original"]
    return {
        "id": dataset_id, "name": item["name"], "summary": dataset_summary(df),
        "profile": profile_dataframe(df), "numeric_profile": numeric_profile(df),
        "missing_profile": missing_profile(df), "distributions": categorical_distributions(df),
        "outliers": outlier_profile(df),
        "duplicates": preview(duplicate_rows(df), 50), "preview": preview(df),
    }


@app.get("/api/datasets/{dataset_id}/cleaned")
def cleaned_detail(dataset_id: str, x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    return {"preview": preview(item["cleaned"]), "history": item["history"], "undo": bool(item["undo"]), "redo": bool(item["redo"])}


def save_change(item, action: str, details: str):
    item["undo"].append(item["cleaned"].clone())
    if len(item["undo"]) > 20:
        item["undo"].pop(0)
    item["redo"].clear()
    item["history"].append({"action": action, "details": details})


@app.post("/api/datasets/{dataset_id}/type")
def update_type(dataset_id: str, payload: dict, x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    try:
        updated = change_data_type(item["cleaned"], payload.get("column", ""), payload.get("type", ""))
        save_change(item, "Change data type", f"{payload['column']} converted to {payload['type']}")
        item["cleaned"] = updated
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/datasets/{dataset_id}/edit")
def edit_dataset(dataset_id: str, payload: dict, x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    try:
        rows = payload.get("rows", [])
        current = item["cleaned"]
        if len(rows) > current.height:
            raise ValueError("The editor cannot add rows in this version.")
        expressions = []
        for col, dtype in current.schema.items():
            values = current[col].to_list()
            for index, row in enumerate(rows):
                values[index] = row.get(col)
            expressions.append(pl.Series(col, values, strict=False).cast(dtype, strict=False))
        edited = pl.DataFrame(expressions)
        if edited.equals(current):
            return {"ok": True, "changed": False}
        save_change(item, "Edit dataset", "Manual cell edits applied to the visible rows")
        item["cleaned"] = edited
        return {"ok": True, "changed": True}
    except Exception as exc:
        raise HTTPException(400, f"Could not apply edits: {exc}")


@app.post("/api/datasets/{dataset_id}/history/{direction}")
def history_action(dataset_id: str, direction: str, x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    if direction == "undo" and item["undo"]:
        item["redo"].append(item["cleaned"].clone())
        item["cleaned"] = item["undo"].pop()
    elif direction == "redo" and item["redo"]:
        item["undo"].append(item["cleaned"].clone())
        item["cleaned"] = item["redo"].pop()
    else:
        raise HTTPException(400, f"Nothing to {direction}.")
    item["history"].append({"action": direction.title(), "details": f"{direction.title()} applied"})
    return {"ok": True}


@app.post("/api/datasets/{dataset_id}/reset")
def reset_dataset(dataset_id: str, x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    save_change(item, "Reset dataset", "Restored original uploaded dataset")
    item["cleaned"] = item["original"].clone()
    return {"ok": True}


@app.get("/api/datasets/{dataset_id}/export")
def export_dataset(dataset_id: str, format: str = "csv", x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    df = item["cleaned"]
    base = item["name"].rsplit(".", 1)[0]
    if format == "csv":
        data, media, filename = df.write_csv().encode(), "text/csv", f"{base}_cleaned.csv"
    elif format == "parquet":
        buffer = BytesIO(); df.write_parquet(buffer)
        data, media, filename = buffer.getvalue(), "application/octet-stream", f"{base}_cleaned.parquet"
    elif format == "xlsx":
        buffer = BytesIO(); df.write_excel(buffer)
        data, media, filename = buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"{base}_cleaned.xlsx"
    else:
        raise HTTPException(400, "Unsupported export format.")
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/datasets/{dataset_id}/analyze")
def analyze_anomalies(dataset_id: str, x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    try:
        item["anomaly"] = detect_anomalies(item["original"])
        result = item["anomaly"]
        counts = result.group_by("Anomaly").len().to_dicts()
        anomalies = result.filter(pl.col("Anomaly") == "Anomaly")
        scores = result.select("Anomaly Score").to_series().to_list()
        score_groups = {
            label: result.filter(pl.col("Anomaly") == label).select("Anomaly Score").to_series().to_list()
            for label in ["Normal", "Anomaly"]
        }
        numeric_cols = [c for c, dtype in zip(result.columns, result.dtypes) if dtype.is_numeric() and c != "Anomaly Score"]
        return {
            "summary": {"total": result.height, "anomalies": anomalies.height, "normal": result.height - anomalies.height,
                        "rate": round(anomalies.height / result.height * 100, 2) if result.height else 0},
            "distribution": counts, "scores": scores[:20000], "score_groups": score_groups, "numeric_columns": numeric_cols,
            "anomalies": preview(anomalies, 100), "result": preview(result, 100),
        }
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Anomaly detection failed: {exc}")


@app.get("/api/datasets/{dataset_id}/anomalies")
def get_anomalies(dataset_id: str, x_session_id: str = Header(None)):
    item = get_dataset(get_session(x_session_id), dataset_id)
    if item["anomaly"] is None:
        raise HTTPException(404, "Run anomaly detection first.")
    result = item["anomaly"]
    anomalies = result.filter(pl.col("Anomaly") == "Anomaly")
    return {"summary": {"total": result.height, "anomalies": anomalies.height, "normal": result.height - anomalies.height,
                         "rate": round(anomalies.height / result.height * 100, 2) if result.height else 0},
            "anomalies": preview(anomalies), "result": preview(result)}
