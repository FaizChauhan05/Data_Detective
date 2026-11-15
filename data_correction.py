import polars as pl

def change_data_type(df, column, target_type):
    data_types = {
        "String": pl.String,
        "Integer": pl.Int64,
        "Float": pl.Float64,
        "Boolean": pl.Boolean,
        "Date": pl.Date
    }

    if target_type == "Date":
        df = df.with_columns(
            pl.col(column).str.to_date(strict = False)
        )
    else:
        df = df.with_columns(
            pl.col(column).cast(data_types[target_type], strict = False)
        )
    return df

def edit_data(df, edited_data):
    return pl.from_pandas(edited_data)