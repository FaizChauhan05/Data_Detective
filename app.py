import polars as pl
import polars.selectors as cs
import streamlit as st
from profiling import profiling_dataframe, profile_numeric, profile_duplicates
files_uploaded = st.file_uploader(
    "Upload CSV/Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
)

if files_uploaded:
    tabs = st.tabs(['Overview'] + [file.name for file in files_uploaded])

    with tabs[0]:
        st.subheader('Uploaded Files')
        st.write(f'Total Files: {len(files_uploaded)}')

        for file in files_uploaded:
            st.write(file.name)

    for tab, file in zip(tabs[1:], files_uploaded):
        with tab:
            st.subheader(file.name)
            name_lower = file.name.lower()

            if name_lower.endswith(".csv"):
                df = None

                for enc in ("utf8", "cp1252", "utf16", "utf8-lossy"):
                    try:
                        file.seek(0)
                        df = pl.read_csv(file, encoding=enc)
                        df = df.with_columns(cs.numeric().round(2))
                        break
                    except pl.exceptions.ComputeError:
                        continue
            elif name_lower.endswith((".xlsx", ".xls")):
                df = pl.read_excel(file, engine='calamine')
                df = df.with_columns(cs.numeric().round(2))

            if df is not None:

                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Rows", df.height)
                    st.metric("Columns", df.width)

                with col2:
                    st.metric('Missing Values', df.null_count().sum().sum_horizontal().item())
                    st.metric("Duplicate Rows", df.is_duplicated().sum())

                st.subheader("Data Preview")
                st.dataframe(df, use_container_width=True)

