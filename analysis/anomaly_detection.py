import numpy as np
import polars as pl
import polars.selectors as cs
from sklearn.ensemble import IsolationForest


def detect_anomalies(df: pl.DataFrame, contamination: float = 0.05) -> pl.DataFrame:
    if df.height < 5:
        raise ValueError("At least 5 rows are required for anomaly detection.")

    numeric = df.select(cs.numeric())
    if numeric.width == 0:
        raise ValueError("This dataset has no numeric columns to analyse.")

    numeric = numeric.with_columns(cs.float().fill_nan(None))
    usable = []
    for col in numeric.columns:
        series = numeric[col]
        if series.null_count() < numeric.height and series.n_unique() > 1:
            median = series.median()
            numeric = numeric.with_columns(pl.col(col).fill_null(median))
            usable.append(col)

    numeric = numeric.select(usable)
    if numeric.width == 0:
        raise ValueError("No usable numeric columns remain after removing empty or constant columns.")

    values = numeric.to_numpy().astype(float)
    if not np.isfinite(values).all():
        raise ValueError("Numeric data contains infinite values. Clean these values before running detection.")

    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(values)
    predictions = model.predict(values)
    scores = model.decision_function(values)
    labels = np.where(predictions == -1, "Anomaly", "Normal")

    # Replace old result columns if the analysis is run again.
    output = df.drop([c for c in ["Anomaly", "Anomaly Score"] if c in df.columns])
    return output.with_columns(
        pl.Series("Anomaly", labels),
        pl.Series("Anomaly Score", scores)
    )
