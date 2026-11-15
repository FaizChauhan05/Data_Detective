
import polars as pl
import polars.selectors as cs
import streamlit as st
import altair as alt
from profiling import profiling_dataframe, profile_numeric, profile_duplicates
from overview import overview_profile

st.set_page_config(page_title="AI Data Detective", layout="wide")

st.title("AI Data Detective")

# Upload files
files_uploaded = st.file_uploader(
    "Upload CSV/Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
)

# Load uploaded files
datasets = []

if files_uploaded:
    for file in files_uploaded:
        name = file.name.lower()

        if name.endswith(".csv"):
            df = None

            for enc in ("utf8", "cp1252", "utf16", "utf8-lossy"):
                try:
                    file.seek(0)
                    df = pl.read_csv(file, encoding=enc)
                    break
                except pl.exceptions.ComputeError:
                    continue

        elif name.endswith((".xlsx", ".xls")):
            file.seek(0)
            df = pl.read_excel(file, engine="calamine")

        if df is not None:
            datasets.append((file.name, df))


if datasets:

    # Create tabs
    tabs = st.tabs(["Overview"] + [name for name, df in datasets])

    # Overview tab
    with tabs[0]:
        st.header("Dataset Overview")

        overview = overview_profile(datasets)

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Datasets", overview["Total Datasets"])
        col2.metric("Total Rows", overview["Total Rows"])
        col3.metric("Total Columns", overview["Total Columns"])
        col4.metric("Total Cells", overview["Total Cells"])

        col1, col2, col3 = st.columns(3)

        col1.metric("Missing Values", overview["Total Missing Values"])
        col2.metric("Duplicate Rows", overview["Total Duplicate Rows"])
        col3.metric(
            "Completeness",
            f'{overview["Overall Completeness"]}%'
        )

        st.subheader("Dataset Summary")

        st.dataframe(
            overview["Dataset Summary"],
            use_container_width=True
        )

    # Individual dataset tabs
    for tab, (name, df) in zip(tabs[1:], datasets):

        with tab:
            st.subheader(name)

            # Metrics
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Rows", df.height)
                st.metric(
                    "Missing Values",
                    df.null_count().sum().sum_horizontal().item()
                )

            with col2:
                st.metric("Columns", df.width)
                st.metric("Duplicate Rows", df.is_duplicated().sum())

            # Data preview
            st.subheader("Data Preview")
            st.dataframe(df, use_container_width=True)

            # General profiling
            st.subheader("General Profile")
            st.dataframe(
                profiling_dataframe(df),
                use_container_width=True
            )

            # Numeric profiling
            st.subheader("Numeric Profile")

            if len(df.select(cs.numeric()).columns) > 0:
                st.dataframe(
                    profile_numeric(df),
                    use_container_width=True
                )
            else:
                st.info("No numeric columns found.")

            # Duplicate records
            st.subheader("Duplicate Rows")
            duplicates_df, dup_count, dup_percentage = profile_duplicates(df)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Duplicate Count", dup_count)
            with col2:
                st.metric("Duplicate Percentage", f"{dup_percentage:.2f}%")

            st.dataframe(duplicates_df, use_container_width=True)
