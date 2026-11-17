
import streamlit as st
import polars as pl
import plotly.express as px
from analysis.anomaly_detection import detect_anomalies

st.title("Anomaly Detection")

if "anomaly_results" not in st.session_state:
    st.session_state.anomaly_results = {}

if not st.session_state.original_datasets:
    st.info("Upload datasets from the Home page first.")
    st.stop()

dataset_name = st.selectbox(
    "Select Dataset",
    list(st.session_state.original_datasets.keys())
)

if st.button("Run Anomaly Detection"):
    df = st.session_state.original_datasets[dataset_name]
    result = detect_anomalies(df)

    st.session_state.anomaly_results[dataset_name] = result
    st.success("Anomaly detection completed.")

if dataset_name in st.session_state.anomaly_results:
    result = st.session_state.anomaly_results[dataset_name]

    total_records = result.height
    anomaly_count = result.filter(
        pl.col("Anomaly") == "Anomaly"
    ).height
    normal_count = total_records - anomaly_count

    anomaly_percentage = (
        anomaly_count / total_records * 100
        if total_records > 0 else 0
    )

    st.subheader("Anomaly Detection Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Records", total_records)
    col2.metric("Anomalies", anomaly_count)
    col3.metric("Normal Records", normal_count)
    col4.metric("Anomaly Rate", f"{anomaly_percentage:.2f}%")


    st.subheader("Anomaly Distribution")
    distribution = result.group_by("Anomaly").len()

    fig = px.pie(
        distribution.to_pandas(),
        names = "Anomaly",
        values = 'len',
        hole =0.5,
        title = "Normal vs Anomalous Records"
    )

    fig.update_traces(
        textinfo = "percent+label",
        hovertemplate = "%(label): %{value} records<extra></extra>"
    )

    st.plotly_chart(fig, width = 'stretch')


    st.subheader("Anomaly Score Distribution")

    fig = px.histogram(
        result.to_pandas(),
        x = "Anomaly Score",
        color = "Anomaly",
        nbins = 40,
        marginal = "box",
        title = "Distribution of Anomaly Scores",
        opacity = 0.75
    )

    fig.update_layout(
        xaxis_title = "Anomaly Score",
        yaxis_title = "Number of Records",
        legend_title = "Classification"
    )

    st.plotly_chart(fig, width='stretch')

    st.subheader('Feature Comparison')

    numeric_columns = result.select(pl.selectors.numeric()).columns
    numeric_columns = [
        col for col in numeric_columns
        if col != "Anomaly Score"
    ]

    if len(numeric_columns) >= 2:
        col1, col2 = st.columns(2)

        with col1:
            x_axis = st.selectbox("X_axis", numeric_columns)

        with col2:
            y_axis = st.selectbox(
                "Y Axis",
                numeric_columns,
                index = 1

            )

            fig = px.scatter(
                result.to_pandas(),
                x=x_axis,
                y=y_axis,
                color="Anomaly",
                hover_data=["Anomaly Score"],
                title=f"{x_axis} vs {y_axis}",
                opacity=0.75
            )

        st.plotly_chart(fig, width="stretch")
    else:
        st.info("At least two numerical columns are required.")


    st.subheader("Detected Anomalies")
    st.dataframe(
        result.filter(pl.col("Anomaly") == "Anomaly"),
        use_container_width=True
    )

    st.subheader("Complete Results")
    st.dataframe(result, use_container_width=True)
