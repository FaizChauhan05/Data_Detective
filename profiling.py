import polars as pl
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from sklearn.ensemble import IsolationForest

def profiling_dataframe(df):
    profile = pl.DataFrame({
        'Column': df.columns,
        'Data Types': [str(dtype) for dtype in df.dtypes],
        'Missing Values': [df[col].null_count() for col in df.columns],
        'Unique Values': [df[col].n_unique() for col in df.columns]
    
    })
    return profile

def profile_numeric(df):
    numeric_df = df.select(pl.selectors.numeric())

    return numeric_df.describe()

def profile_duplicates(df):
    df = df.drop_nulls()
    duplicates_df = df.filter(df.is_duplicated())
    dup_count = duplicates_df.height
    dup_percentage = (dup_count / df.height) * 100 if df.height > 0 else 0

    return duplicates_df, dup_count, dup_percentage

def data_structure(df):
    num_rows = df.height
    num_cols = df.width
    total_cells = num_rows * num_cols

    return num_rows, num_cols, total_cells

def unique_values(df):
    unique_counts = df.select(pl.all().drop_nulls().n_unique())
    unique_percentage = (unique_counts / df.height) * 100 if unique_counts.height > 0 else 0
    
    return unique_counts, unique_percentage

def missing_values(df):
    missing_counts = df.select(pl.all().null_count())
    non_missing_counts = df.select(pl.all().count())
    
    missing_percentage = (missing_counts / df.height) * 100 if df.height > 0 else missing_counts * 0
    
    missing_severity = missing_percentage.select(
        pl.all().map_elements(
            lambda x: "High" if x > 50 else "Medium" if x > 20 else "Low",
            return_dtype=pl.String
        )
    )

    missing_profile = pl.DataFrame({
            "Column": df.columns,
            "Missing Values": missing_counts.row(0),
            "Non-Missing Values": non_missing_counts.row(0),
            "Missing Percentage": missing_percentage.row(0),
            "Severity": missing_severity.row(0)
        })
    
    most_missing = missing_profile.sort(
        'Missing Values', descending = True
    )
    
    missing_tips = (
        "For numeric columns with high missing values, consider imputation "
        "or removing those rows. For categorical columns, consider using "
        "a placeholder or the most frequent category. If missing values "
        "are insignificant, they may be ignored."
    )
    
    return missing_counts, missing_percentage, missing_severity, most_missing, missing_profile, missing_tips

def profile_outliers(df):
    numeric_df = df.select(pl.selectors.numeric())

    outlier_profile = []

    for col in numeric_df.columns:
        q1 = numeric_df[col].quantile(0.25)
        q3 = numeric_df[col].quantile(0.75)

        iqr = q3 - q1

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 - (1.5 * iqr)

        outliers = numeric_df.filter(
            (pl.col(col) < lower_bound)
            (pl.col(col)> upper_bound)
        )

        outlier_count = outliers.height

        outlier_profile.append({
            "Column": col,
            "Lower Bound": lower_bound,
            "Upper Bound": upper_bound,
            "Outlier Count": outlier_count
        })
    return pl.DataFrame(outlier_profile)