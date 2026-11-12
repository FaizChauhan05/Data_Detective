import polars as pl

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
    duplicates_df = df.filter(df.is_duplicated())


    return duplicates_df