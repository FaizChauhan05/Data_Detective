import polars as pl


def change_data_type(df: pl.DataFrame, column: str, target_type: str) -> pl.DataFrame:
    types = {"String": pl.String, "Integer": pl.Int64, "Float": pl.Float64, "Boolean": pl.Boolean, "Date": pl.Date}
    if column not in df.columns or target_type not in types:
        raise ValueError("Invalid column or data type.")
    if target_type == "Date":
        expr = pl.col(column).cast(pl.String).str.to_date(strict=False)
    else:
        expr = pl.col(column).cast(types[target_type], strict=False)
    return df.with_columns(expr)
