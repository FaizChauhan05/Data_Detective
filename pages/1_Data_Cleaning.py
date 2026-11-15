
import streamlit as st
import polars as pl
import pandas as pd
from io import BytesIO
from datetime import datetime
from data_correction import change_data_type

st.title("Data Cleaning")

if "cleaned_datasets" not in st.session_state or not st.session_state.cleaned_datasets:
    st.info("Upload datasets from the Home page first.")
    st.stop()

# Initialize history for each dataset
if "undo_stacks" not in st.session_state:
    st.session_state.undo_stacks = {}

if "redo_stacks" not in st.session_state:
    st.session_state.redo_stacks = {}

if "cleaning_history" not in st.session_state:
    st.session_state.cleaning_history = {}

dataset_names = list(st.session_state.cleaned_datasets.keys())

for name in dataset_names:
    st.session_state.undo_stacks.setdefault(name, [])
    st.session_state.redo_stacks.setdefault(name, [])
    st.session_state.cleaning_history.setdefault(name, [])

dataset_name = st.selectbox("Select Dataset", dataset_names)
df = st.session_state.cleaned_datasets[dataset_name]

undo_stack = st.session_state.undo_stacks[dataset_name]
redo_stack = st.session_state.redo_stacks[dataset_name]
history = st.session_state.cleaning_history[dataset_name]


# Helper function to log operations
def log_action(action, details):
    history.append({
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action": action,
        "Details": details
    })


# Helper function to save state before modification
def save_state():
    undo_stack.append(st.session_state.cleaned_datasets[dataset_name].clone())
    redo_stack.clear()


# Undo and Redo controls
col1, col2 = st.columns(2)

with col1:
    if st.button("Undo", disabled=len(undo_stack) == 0, use_container_width=True):
        redo_stack.append(st.session_state.cleaned_datasets[dataset_name].clone())
        st.session_state.cleaned_datasets[dataset_name] = undo_stack.pop()
        log_action("Undo", "Reverted previous operation")
        st.rerun()

with col2:
    if st.button("Redo", disabled=len(redo_stack) == 0, use_container_width=True):
        undo_stack.append(st.session_state.cleaned_datasets[dataset_name].clone())
        st.session_state.cleaned_datasets[dataset_name] = redo_stack.pop()
        log_action("Redo", "Reapplied reverted operation")
        st.rerun()


# Change Data Type
st.subheader("Change Data Type")

column = st.selectbox(
    "Select Column",
    df.columns,
    key=f"column_{dataset_name}"
)

target_type = st.selectbox(
    "Select Data Type",
    ["String", "Integer", "Float", "Boolean", "Date"],
    key=f"type_{dataset_name}"
)

if st.button("Change Data Type"):
    save_state()

    st.session_state.cleaned_datasets[dataset_name] = change_data_type(
        st.session_state.cleaned_datasets[dataset_name],
        column,
        target_type
    )

    log_action("Change Data Type", f"{column}: converted to {target_type}")
    st.success(f"{column} converted to {target_type}")
    st.rerun()


# Edit Dataset
st.subheader("Edit Dataset")

df = st.session_state.cleaned_datasets[dataset_name]

edited_data = st.data_editor(
    df.to_pandas(),
    num_rows="dynamic",
    use_container_width=True,
    key=f"editor_{dataset_name}"
)

if st.button("Apply Edits"):
    edited_df = pl.from_pandas(edited_data)

    if not edited_df.equals(df):
        save_state()
        st.session_state.cleaned_datasets[dataset_name] = edited_df
        log_action("Edit Dataset", "Manual cell edits or row changes applied")
        st.success("Edits applied.")
        st.rerun()
    else:
        st.info("No changes detected.")


# Cleaned Dataset Preview
st.subheader("Cleaned Dataset Preview")

st.dataframe(
    st.session_state.cleaned_datasets[dataset_name],
    use_container_width=True
)


# Cleaning Summary
st.subheader("Cleaning Summary")

if history:
    history_df = pl.DataFrame(history)
    st.dataframe(history_df, use_container_width=True)
else:
    st.info("No cleaning operations recorded yet.")


# Export Dataset
st.subheader("Export Dataset")

export_format = st.selectbox(
    "Export Format",
    ["CSV", "Excel (.xlsx)", "Parquet"]
)

current_df = st.session_state.cleaned_datasets[dataset_name]

if export_format == "CSV":
    file_data = current_df.write_csv().encode("utf-8")
    file_name = f"{dataset_name}_cleaned.csv"
    mime_type = "text/csv"

elif export_format == "Excel (.xlsx)":
    buffer = BytesIO()
    current_df.to_pandas().to_excel(buffer, index=False, engine="openpyxl")
    file_data = buffer.getvalue()
    file_name = f"{dataset_name}_cleaned.xlsx"
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

else:
    buffer = BytesIO()
    current_df.write_parquet(buffer)
    file_data = buffer.getvalue()
    file_name = f"{dataset_name}_cleaned.parquet"
    mime_type = "application/octet-stream"

st.download_button(
    label="Download Cleaned Dataset",
    data=file_data,
    file_name=file_name,
    mime=mime_type,
    use_container_width=True
)


# Reset Dataset
st.subheader("Reset Dataset")

if st.button("Reset to Original"):
    original_df = st.session_state.original_datasets[dataset_name].clone()

    save_state()
    st.session_state.cleaned_datasets[dataset_name] = original_df

    log_action("Reset Dataset", "Restored original uploaded dataset")
    st.success("Dataset reset to original.")
    st.rerun()
