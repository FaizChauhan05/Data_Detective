
import streamlit as st
import polars as pl

from data_correction import change_data_type, edit_data

st.title("Data Cleaning")

if not st.session_state.get("cleaned_datasets"):
    st.info("Upload datasets from the Home page first.")
    st.stop()

# Select dataset
dataset_name = st.selectbox(
    "Select Dataset",
    list(st.session_state.cleaned_datasets.keys()),
    key="cleaning_dataset"
)

df = st.session_state.cleaned_datasets[dataset_name]

# Data type correction
st.subheader("Change Data Type")

column = st.selectbox(
    "Select Column",
    df.columns,
    key=f"column_select_{dataset_name}"
)

target_type = st.selectbox(
    "Select Data Type",
    ["String", "Integer", "Float", "Boolean", "Date"],
    key=f"type_select_{dataset_name}"
)

if st.button("Change Data Type", key=f"change_type_{dataset_name}"):
    cleaned_df = change_data_type(df, column, target_type)

    st.session_state.cleaned_datasets[dataset_name] = cleaned_df

    st.success(f"{column} converted to {target_type}")

    st.rerun()

# Edit dataset
st.subheader("Edit Dataset")

df = st.session_state.cleaned_datasets[dataset_name]

edited_data = st.data_editor(
    df.to_pandas(),
    num_rows="dynamic",
    use_container_width=True,
    key=f"editor_{dataset_name}"
)

if st.button("Apply Edits", key=f"apply_edits_{dataset_name}"):
    cleaned_df = edit_data(edited_data)

    st.session_state.cleaned_datasets[dataset_name] = cleaned_df

    st.success("Edits applied successfully.")

    st.rerun()

# Preview cleaned dataset
st.subheader("Cleaned Dataset Preview")

st.dataframe(
    st.session_state.cleaned_datasets[dataset_name],
    use_container_width=True
)

# Reset cleaned dataset
if st.button("Reset to Original", key=f"reset_{dataset_name}"):
    st.session_state.cleaned_datasets[dataset_name] = (
        st.session_state.original_datasets[dataset_name].clone()
    )

    st.success("Dataset reset to its original version.")

    st.rerun()
