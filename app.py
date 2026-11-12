import polars as pl
import streamlit as st
from profiling import profiling_dataframe, profile_numeric, profile_duplicates
files_uploaded = st.file_uploader(
    "Upload CSV/Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
)

if files_uploaded:
    for file in files_uploaded:
        st.subheader(file.name)
        name_lower = file.name.lower()

        if name_lower.endswith(".csv"):
            df = None
            for enc in ("utf8", "cp1252", "utf16", "utf8-lossy"):
                try:
                    file.seek(0)
                    df = pl.read_csv(file, encoding = enc)
                    break
                except pl.exceptions.ComputeError:
                    continue
        elif file.name.endswith((".xlsx", ".xls")):
            df = pl.read_excel(file, engine = 'calamine')

        st.dataframe(df)

        st.subheader('Data Profiling')

        st.write('General Profile')
        st.dataframe(profiling_dataframe(df))

        st.write('Numeric Profile')
        st.dataframe(profile_numeric(df))

        st.write('Duplicate Rows')
        st.dataframe(profile_duplicates(df))
