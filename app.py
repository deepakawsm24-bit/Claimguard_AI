
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ClaimGuard AI",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 ClaimGuard AI")
st.subheader("Healthcare Claims Risk Dashboard")

st.info(
    "Demo tool: Missing documents ko flag karta hai. "
    "Final claim decisions authorized staff karein."
)

REQUIRED_DOCS = [
    "Discharge Summary",
    "Final Bill",
    "Investigation Reports"
]

def assess_risk(row):
    missing = [
        doc for doc in REQUIRED_DOCS
        if not bool(row[doc])
    ]

    if len(missing) >= 2:
        risk = "HIGH"
    elif len(missing) == 1:
        risk = "MEDIUM"
    else:
        risk = "NO DOCUMENT FLAGS"

    return pd.Series([risk, ", ".join(missing) or "None"])

st.header("📂 Upload Claims File")

st.write(
    "CSV ya Excel file upload karo. File mein ye columns hone chahiye:"
)
st.code(
    "Claim ID, Discharge Summary, Final Bill, Investigation Reports"
)

uploaded_file = st.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx"]
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df.columns = df.columns.str.strip()

        required_columns = ["Claim ID"] + REQUIRED_DOCS
        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:
            st.error(
                "Missing columns: " + ", ".join(missing_columns)
            )
            st.stop()

        def to_bool(value):
            if isinstance(value, bool):
                return value
            if pd.isna(value):
                return False
            return str(value).strip().lower() in [
                "true", "yes", "1", "received"
            ]

        for col in REQUIRED_DOCS:
            df[col] = df[col].apply(to_bool)

        results = df.copy()
        results[["Risk Level", "Missing Documents"]] = (
            results.apply(assess_risk, axis=1)
        )

        total = len(results)
        high = int((results["Risk Level"] == "HIGH").sum())
        medium = int((results["Risk Level"] == "MEDIUM").sum())
        clear = int(
            (results["Risk Level"] == "NO DOCUMENT FLAGS").sum()
        )

        st.header("📊 Claims Summary")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Claims", total)
        c2.metric("High Risk", high)
        c3.metric("Medium Risk", medium)
        c4.metric("No Document Flags", clear)

        st.subheader("Claims by Risk Level")
        st.bar_chart(results["Risk Level"].value_counts())

        st.subheader("📋 Claim Review Results")

        risk_filter = st.selectbox(
            "Filter claims",
            ["ALL", "HIGH", "MEDIUM", "NO DOCUMENT FLAGS"]
        )

        if risk_filter == "ALL":
            view = results
        else:
            view = results[
                results["Risk Level"] == risk_filter
            ]

        st.dataframe(view, use_container_width=True)

        csv_data = results.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇️ Download Review Results (CSV)",
            data=csv_data,
            file_name="claim_review_results.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"File could not be processed: {e}")

else:
    st.caption(
        "Upload a test file to see the dashboard. "
        "Use synthetic data only; do not upload real patient records."
    )
