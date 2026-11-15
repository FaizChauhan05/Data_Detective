import polars as pl


def overview_profile(datasets):
    total_datasets = len(datasets)
    total_rows = 0
    total_columns = 0
    total_cells = 0
    total_missing = 0
    total_duplicates = 0

    dataset_summary = []

    for name, df in datasets:
        rows = df.height
        columns = df.width
        cells = rows * columns

        missing = df.null_count().sum().sum_horizontal().item()

        clean_df = df.drop_nulls()
        duplicates = clean_df.filter(clean_df.is_duplicated()).height

        total_rows += rows
        total_columns += columns
        total_cells += cells
        total_missing += missing
        total_duplicates += duplicates

        completeness = (
            ((cells - missing) / cells) * 100
            if cells > 0
            else 0
        )

        dataset_summary.append({
            "Dataset": name,
            "Rows": rows,
            "Columns": columns,
            "Total Cells": cells,
            "Missing Values": missing,
            "Completeness (%)": round(completeness, 2),
            "Duplicate Rows": duplicates
        })

    overall_completeness = (
        ((total_cells - total_missing) / total_cells) * 100
        if total_cells > 0
        else 0
    )

    summary_df = pl.DataFrame(dataset_summary)

    return {
        "Total Datasets": total_datasets,
        "Total Rows": total_rows,
        "Total Columns": total_columns,
        "Total Cells": total_cells,
        "Total Missing Values": total_missing,
        "Total Duplicate Rows": total_duplicates,
        "Overall Completeness": round(overall_completeness, 2),
        "Dataset Summary": summary_df
    }