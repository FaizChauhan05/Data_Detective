import numpy as np
import polars as pl
import polars.selectors as cs
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

def detect_anomalies(df):
    numeric_df = df.select(cs.numeric())
    numeric_df = numeric_df.with_columns(cs.float().fill_nan(None))

    # Remove completely empty columns and impute remaining nulls
    for col in numeric_df.columns:
        if numeric_df[col].null_count() == numeric_df.height:
            numeric_df = numeric_df.drop(col)
        else:
            numeric_df = numeric_df.with_columns(
                pl.col(col).fill_null(numeric_df[col].median())
            )

    if numeric_df.width == 0:
        raise ValueError("No usable numerical columns found.")

    data = numeric_df.to_numpy()

    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(data)

    predictions = model.predict(data)
    decision_scores = model.decision_function(data)

    anomaly_labels = np.where(predictions == -1, "Anomaly", "Normal")

    df = df.with_columns(
        pl.Series("Anomaly", anomaly_labels),
        pl.Series("Anomaly Score", decision_scores)
    )

    return df

