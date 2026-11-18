import polars as pl
import polars.selectors as cs


def profile_dataframe(df: pl.DataFrame):
    rows = []
    for col, dtype in zip(df.columns, df.dtypes):
        series = df[col]
        missing = series.null_count()
        rows.append({
            "Column": col,
            "Data type": str(dtype),
            "Missing": missing,
            "Missing %": round(missing / df.height * 100, 2) if df.height else 0,
            "Unique": series.n_unique(),
        })
    return rows


def dataset_summary(df: pl.DataFrame):
    cells = df.height * df.width
    missing = sum(df.null_count().row(0)) if df.width else 0
    duplicate_rows = df.filter(df.is_duplicated()).height if df.height else 0
    return {
        "rows": df.height,
        "columns": df.width,
        "cells": cells,
        "missing": missing,
        "duplicates": duplicate_rows,
        "completeness": round((cells - missing) / cells * 100, 2) if cells else 0,
    }


def numeric_profile(df: pl.DataFrame):
    numeric = df.select(cs.numeric())
    return numeric.describe().to_dicts() if numeric.width else []


def duplicate_rows(df: pl.DataFrame):
    return df.filter(df.is_duplicated()) if df.height else df.head(0)


def missing_profile(df: pl.DataFrame):
    result = []
    for col in df.columns:
        count = df[col].null_count()
        pct = count / df.height * 100 if df.height else 0
        result.append({"Column": col, "Missing": count, "Missing %": round(pct, 2)})
    return result


def outlier_profile(df: pl.DataFrame):
    result = []
    numeric = df.select(cs.numeric())
    for col in numeric.columns:
        series = numeric[col].drop_nulls()
        if series.len() == 0:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        if q1 is None or q3 is None:
            continue
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        count = series.filter((series < lower) | (series > upper)).len()
        result.append({"Column": col, "Lower bound": lower, "Upper bound": upper, "Outliers": count})
    return result


def categorical_distributions(df: pl.DataFrame, limit: int = 7):
    """Return compact top-category counts for pie-chart previews."""
    result = {}
    for col, dtype in zip(df.columns, df.dtypes):
        if dtype == pl.String or dtype == pl.Categorical or dtype == pl.Boolean:
            series = df[col].drop_nulls()
            if series.len() == 0:
                continue
            counts = (
                series.cast(pl.String).to_frame(name="value")
                .group_by("value").len()
                .sort("len", descending=True)
            )
            top = counts.head(limit)
            labels = top["value"].to_list()
            values = top["len"].to_list()
            other = series.len() - sum(values)
            if other > 0:
                labels.append("Other")
                values.append(other)
            result[col] = {"labels": labels, "values": values}
    return result
