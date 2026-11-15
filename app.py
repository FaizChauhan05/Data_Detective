
import polars as pl
import polars.selectors as cs
import streamlit as st

from profiling import profiling_dataframe, profile_numeric, profile_duplicates
from overview import overview_profile

st.set_page_config(page_title="AI Data Detective", layout="wide")

st.title("AI Data Detective")

# Store original and cleaned datasets separately
if "original_datasets" not in st.session_state:
    st.session_state.original_datasets = {}

if "cleaned_datasets" not in st.session_state:
    st.session_state.cleaned_datasets = {}

# Upload files
files_uploaded = st.file_uploader(
    "Upload CSV/Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
)

# Load uploaded files
if files_uploaded:
    for file in files_uploaded:
        name = file.name

        if name in st.session_state.original_datasets:
            continue

        df = None

        if name.lower().endswith(".csv"):
            for enc in ("utf8", "cp1252", "utf16", "utf8-lossy"):
                try:
                    file.seek(0)
                    df = pl.read_csv(file, encoding=enc)
                    break
                except pl.exceptions.ComputeError:
                    continue

        elif name.lower().endswith((".xlsx", ".xls")):
            file.seek(0)
            df = pl.read_excel(file, engine="calamine")

        if df is not None:
            st.session_state.original_datasets[name] = df.clone()
            st.session_state.cleaned_datasets[name] = df.clone()

# Profiling datasets use the original uploaded data
datasets = list(st.session_state.original_datasets.items())

if datasets:
    tabs = st.tabs(["Overview"] + [name for name, df in datasets])

    # Overview
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

    # Individual dataset profiling
    for tab, (name, df) in zip(tabs[1:], datasets):
        with tab:
            st.subheader(name)

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

            st.subheader("Data Preview")
            st.dataframe(df, use_container_width=True)

            st.subheader("General Profile")
            st.dataframe(
                profiling_dataframe(df),
                use_container_width=True
            )

            st.subheader("Numeric Profile")

            if len(df.select(cs.numeric()).columns) > 0:
                st.dataframe(
                    profile_numeric(df),
                    use_container_width=True
                )
            else:
                st.info("No numeric columns found.")

            st.subheader("Duplicate Rows")

            duplicates_df, dup_count, dup_percentage = profile_duplicates(df)

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Duplicate Count", dup_count)

            with col2:
                st.metric("Duplicate Percentage", f"{dup_percentage:.2f}%")

            st.dataframe(duplicates_df, use_container_width=True)
